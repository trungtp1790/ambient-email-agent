import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from typing import Dict
from pydantic import BaseModel, Field

from langgraph.checkpoint.memory import MemorySaver
from .graph.build import build_graph
from .services.memory_store import init_db
from .services.gmail_service import extract_sender_email
from .services import gmail_service as gm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI(title="Ambient Email Agent")
app.mount("/static", StaticFiles(directory="src/web"), name="static")

checkpointer = MemorySaver()
graph = build_graph().with_config(checkpointer=checkpointer)

PENDING: Dict[str, Dict] = {}


class RunEmailRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    email_id: str = Field(..., description="Gmail message id or local id")
    email_subject: str
    email_body: str
    email_sender: str
    email_recipient: str | None = None


class ApproveRequest(BaseModel):
    thread_id: str
    approved: bool = True
    edits: Dict[str, str] | None = None

@app.on_event("startup")
def _startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    with open("src/web/index.html","r",encoding="utf-8") as f:
        return f.read()

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/run-email")
async def run_email(item: RunEmailRequest):
    try:
        payload = item.model_dump()
        thread = {"user_id": payload["user_id"], **payload}
        logger.info("Processing email %s", payload.get('email_id', 'unknown'))
        
        # stream to catch interrupt payload
        events = graph.stream(thread, stream_mode="values")
        last = {}
        for step in events:
            last = step
            if "__interrupt__" in step:
                intr = step["__interrupt__"][0]
                thread_id = intr["thread_id"]
                # enrich interrupt with metadata for filtering in UI
                intr["triage"] = last.get("triage")
                intr["priority"] = last.get("priority")
                intr["is_vip"] = last.get("is_vip")
                PENDING[thread_id] = intr
                logger.info("Email %s requires approval: %s", payload.get('email_id'), thread_id)
                return {"status":"INTERRUPTED","thread_id":thread_id,"payload":intr["value"]}
        # Fallback: if node stored a hitl payload without interrupt surfacing (edge cases)
        if last.get("hitl_payload") and last.get("hitl_thread_id"):
            thread_id = last["hitl_thread_id"]
            PENDING[thread_id] = {
                "thread_id": thread_id,
                "value": last["hitl_payload"],
                "triage": last.get("triage"),
                "priority": last.get("priority"),
                "is_vip": last.get("is_vip")
            }
            logger.info("Email %s queued for approval (fallback): %s", payload.get('email_id'), thread_id)
            return {"status":"INTERRUPTED","thread_id":thread_id,"payload":last["hitl_payload"]}

        # Fallback 2: if graph finished but indicates send_email action with a draft
        if last.get("proposed_action") == "send_email" and last.get("draft"):
            to_email = extract_sender_email(last.get("email_sender",""))
            payload = {
                "tool": "send_email",
                "allow_edit": True,
                "allow_accept": True,
                "allow_ignore": True,
                "allow_respond": False,
                "priority": last.get("priority", 1),
                "is_vip": last.get("is_vip", False),
                "proposal": {
                    "to": to_email or last.get("email_sender",""),
                    "subject": "Re: %s" % (last.get('email_subject','')),
                    "body": last.get("draft",""),
                    "original_sender": last.get("email_sender",""),
                    "original_subject": last.get("email_subject","")
                }
            }
            import uuid
            thread_id = "%s-%s" % (last.get('email_id','unknown'), uuid.uuid4().hex[:8])
            PENDING[thread_id] = {
                "thread_id": thread_id,
                "value": payload,
                "triage": last.get("triage"),
                "priority": last.get("priority"),
                "is_vip": last.get("is_vip")
            }
            logger.info("Email %s queued for approval (final-state fallback): %s", payload.get('email_id'), thread_id)
            return {"status":"INTERRUPTED","thread_id":thread_id,"payload":payload}
        
        logger.info("Email %s processed successfully", payload.get('email_id'))
        return {"status":"DONE","state": last}
        
    except Exception as e:
        logger.error("Error processing email: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/pending")
def pending():
    # lightweight queue for HITL UI
    return [{"thread_id":k,"payload":v["value"]} for k,v in PENDING.items()]

@app.post("/approve")
async def approve(req: Request, body: ApproveRequest):
    secret = req.headers.get("x-hitl-secret")
    if secret != os.getenv("HITL_SECRET"):
        # Let 403 propagate as-is
        raise HTTPException(403, "Forbidden")

    try:
        data = body.model_dump()
        thread_id = data["thread_id"]
        if thread_id not in PENDING:
            raise HTTPException(404, "No such interrupt")

        intr = PENDING.pop(thread_id)
        payload = intr["value"].get("proposal", {})
        edits = data.get("edits", {}) or {}
        approved = data.get("approved", True)

        if not approved:
            logger.info("Email action denied for thread %s", thread_id)
            return {"status":"DENIED"}

        # merge and send email immediately (simpler than fully resuming the graph)
        to = edits.get("to", payload.get("to"))
        subject = edits.get("subject", payload.get("subject"))
        content = edits.get("body", payload.get("body",""))
        
        msg_id = gm.send_email(to, subject, content)
        if msg_id:
            logger.info("Email sent successfully: %s", msg_id)
            return {"status":"SENT", "message_id": msg_id}
        else:
            logger.error("Failed to send email to %s", to)
            return {"status":"ERROR", "message": "Failed to send email"}
            
    except HTTPException:
        # Preserve FastAPI-intended HTTP errors (e.g., 404)
        raise
    except Exception as e:
        logger.error("Error in approve endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
