"""
Ambient Email Agent - FastAPI Application
========================================

Đây là file chính của ứng dụng FastAPI, cung cấp các API endpoints cho:
- Xử lý email thông qua LangGraph workflow
- Human-in-the-Loop (HITL) approval system
- Dashboard web interface cho quản lý email pending

Architecture:
- FastAPI server với static file serving
- LangGraph integration với memory checkpointing
- In-memory queue cho pending approvals
- RESTful API cho email processing và approval
"""

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

# Load environment variables
load_dotenv()

# Initialize FastAPI application
app = FastAPI(title="Ambient Email Agent")

# Mount static files for web dashboard
app.mount("/static", StaticFiles(directory="src/web"), name="static")

# Initialize LangGraph with memory checkpointing
checkpointer = MemorySaver()
graph = build_graph().with_config(checkpointer=checkpointer)

# In-memory queue for pending HITL approvals
# Key: thread_id, Value: interrupt payload with metadata
PENDING: Dict[str, Dict] = {}


class RunEmailRequest(BaseModel):
    """
    Pydantic model cho request xử lý email
    
    Attributes:
        user_id: ID của user (thường là "u_local" cho local user)
        email_id: ID của email trong Gmail hoặc local ID
        email_subject: Tiêu đề email
        email_body: Nội dung email
        email_sender: Địa chỉ người gửi
        email_recipient: Địa chỉ người nhận (optional)
    """
    user_id: str = Field(..., description="User identifier")
    email_id: str = Field(..., description="Gmail message id or local id")
    email_subject: str
    email_body: str
    email_sender: str
    email_recipient: str | None = None


class ApproveRequest(BaseModel):
    """
    Pydantic model cho request approval email
    
    Attributes:
        thread_id: ID của thread cần approval
        approved: True nếu approve, False nếu deny
        edits: Dictionary chứa các chỉnh sửa (to, subject, body)
    """
    thread_id: str
    approved: bool = True
    edits: Dict[str, str] | None = None

@app.on_event("startup")
def _startup():
    """
    Khởi tạo database khi server startup
    Tạo các bảng cần thiết cho memory store
    """
    init_db()

@app.get("/", response_class=HTMLResponse)
def home():
    """
    Trả về trang web dashboard chính
    
    Returns:
        HTML content của dashboard HITL
    """
    with open("src/web/index.html","r",encoding="utf-8") as f:
        return f.read()

@app.get("/health")
def health() -> Dict[str, str]:
    """
    Health check endpoint
    
    Returns:
        Dict với status "ok" để kiểm tra server có hoạt động
    """
    return {"status": "ok"}


@app.post("/run-email")
async def run_email(item: RunEmailRequest):
    """
    Xử lý email thông qua LangGraph workflow
    
    Workflow:
    1. Nhận email data từ request
    2. Chạy qua LangGraph pipeline (triage -> agent -> sensitive)
    3. Nếu cần approval, tạo interrupt và lưu vào PENDING queue
    4. Trả về status và thread_id cho HITL
    
    Args:
        item: RunEmailRequest chứa thông tin email
        
    Returns:
        Dict với status và thông tin cần thiết:
        - INTERRUPTED: Cần approval, trả về thread_id và payload
        - DONE: Xử lý hoàn tất, trả về final state
    """
    try:
        payload = item.model_dump()
        thread = {"user_id": payload["user_id"], **payload}
        logger.info("Processing email %s", payload.get('email_id', 'unknown'))
        
        # Stream qua LangGraph để bắt interrupt payload
        events = graph.stream(thread, stream_mode="values")
        last = {}
        for step in events:
            last = step
            if "__interrupt__" in step:
                intr = step["__interrupt__"][0]
                thread_id = intr["thread_id"]
                # Thêm metadata cho UI filtering
                intr["triage"] = last.get("triage")
                intr["priority"] = last.get("priority")
                intr["is_vip"] = last.get("is_vip")
                PENDING[thread_id] = intr
                logger.info("Email %s requires approval: %s", payload.get('email_id'), thread_id)
                return {"status":"INTERRUPTED","thread_id":thread_id,"payload":intr["value"]}
        
        # Fallback 1: Nếu node lưu hitl_payload nhưng interrupt không surface
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

        # Fallback 2: Nếu graph hoàn thành nhưng có send_email action với draft
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
    """
    Lấy danh sách email đang chờ approval
    
    Returns:
        List các email pending với metadata cho UI filtering:
        - thread_id: ID của thread
        - payload: Thông tin proposal để gửi email
        - triage: Kết quả phân loại email
        - priority: Độ ưu tiên (1=normal, 2=high/VIP)
        - is_vip: Có phải VIP contact không
    """
    return [
        {
            "thread_id": k,
            "payload": v.get("value"),
            # Surface metadata cho client-side filtering
            "triage": v.get("triage"),
            "priority": v.get("priority"),
            "is_vip": v.get("is_vip", False)
        }
        for k, v in PENDING.items()
    ]

@app.post("/approve")
async def approve(req: Request, body: ApproveRequest):
    """
    Xử lý approval/denial cho email pending
    
    Workflow:
    1. Kiểm tra HITL secret để xác thực
    2. Tìm thread_id trong PENDING queue
    3. Nếu approved: merge edits và gửi email
    4. Nếu denied: chỉ log và trả về DENIED
    5. Remove thread khỏi PENDING queue
    
    Args:
        req: FastAPI Request object (để lấy headers)
        body: ApproveRequest với thread_id, approved, edits
        
    Returns:
        Dict với status:
        - SENT: Email đã gửi thành công
        - DENIED: Email bị từ chối
        - ERROR: Có lỗi xảy ra
    """
    # Kiểm tra HITL secret để bảo mật
    secret = req.headers.get("x-hitl-secret")
    if secret != os.getenv("HITL_SECRET"):
        raise HTTPException(403, "Forbidden")

    try:
        data = body.model_dump()
        thread_id = data["thread_id"]
        if thread_id not in PENDING:
            raise HTTPException(404, "No such interrupt")

        # Lấy interrupt data và remove khỏi queue
        intr = PENDING.pop(thread_id)
        payload = intr["value"].get("proposal", {})
        edits = data.get("edits", {}) or {}
        approved = data.get("approved", True)

        if not approved:
            logger.info("Email action denied for thread %s", thread_id)
            return {"status":"DENIED"}

        # Merge edits với proposal và gửi email ngay lập tức
        # (đơn giản hơn việc resume toàn bộ graph)
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
        # Giữ nguyên FastAPI HTTP errors (404, 403, etc.)
        raise
    except Exception as e:
        logger.error("Error in approve endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
