from langgraph.types import interrupt
from src.graph.state import EmailState
from src.services.genai_service import classify_email, draft_reply
from src.services.gmail_service import extract_sender_email
from src.services.memory_store import get_profile, get_vip_contacts, is_vip_contact, log_email_action
import uuid
import logging

logger = logging.getLogger(__name__)

def node_triage(state: EmailState) -> EmailState:
    """Classify email and determine priority based on sender"""
    try:
        sender = state.get("email_sender", "")
        sender_email = extract_sender_email(sender)
        
        # Check if sender is VIP
        is_vip = is_vip_contact(state["user_id"], sender_email)
        state["is_vip"] = is_vip
        state["priority"] = 2 if is_vip else 1
        
        # Classify email with sender context
        label = classify_email(state["email_subject"], state["email_body"], sender)
        state["triage"] = label
        
        # Determine action based on classification
        if label == "needs_reply":
            state["proposed_action"] = "send_email"
        elif label == "schedule":
            state["proposed_action"] = "create_event"
        else:
            state["proposed_action"] = "none"
            
        # Log the triage action
        log_email_action(
            state["user_id"], 
            state["email_id"], 
            sender, 
            state["email_subject"], 
            label, 
            "triage"
        )
        
        logger.info("Email %s triaged as %s (VIP: %s)", state['email_id'], label, is_vip)
        return state
        
    except Exception as e:
        logger.error("Error in triage node: %s", e)
        state["triage"] = "fyi"
        state["proposed_action"] = "none"
        state["is_vip"] = False
        state["priority"] = 1
        return state

def node_agent(state: EmailState) -> EmailState:
    """Generate draft reply using AI with VIP context"""
    try:
        if state.get("triage") == "needs_reply":
            prof = get_profile(state["user_id"])
            vip_contacts = get_vip_contacts(state["user_id"])
            vip_emails = [contact["email"] for contact in vip_contacts]
            
            state["draft"] = draft_reply(
                state["email_subject"], 
                state["email_body"],
                tone=prof["tone"], 
                pref_hours=prof["preferred_meeting_hours"],
                sender=state.get("email_sender", ""),
                vip_contacts=vip_emails
            )
            
            # Log the draft generation
            log_email_action(
                state["user_id"], 
                state["email_id"], 
                state.get("email_sender", ""), 
                state["email_subject"], 
                state["triage"], 
                "draft_generated"
            )
            
            logger.info("Generated draft for email %s", state['email_id'])
        else:
            state["draft"] = "No action needed."
            
        return state
        
    except Exception as e:
        logger.error("Error in agent node: %s", e)
        state["draft"] = "Error generating reply. Please review manually."
        return state

def node_sensitive(state: EmailState) -> EmailState:
    """Handle sensitive actions with human-in-the-loop approval.

    IMPORTANT: Do not swallow the Interrupt exception. It must bubble up so the
    runtime can pause and our API can capture the interrupt payload.
    """
    if state.get("proposed_action") == "send_email" and state.get("draft"):
        sender = state.get("email_sender", "")
        sender_email = extract_sender_email(sender)

        payload = {
            "tool": "send_email",
            "allow_edit": True,
            "allow_accept": True,
            "allow_ignore": True,
            "allow_respond": False,
            "priority": state.get("priority", 1),
            "is_vip": state.get("is_vip", False),
            "proposal": {
                "to": sender_email,
                "subject": f"Re: {state['email_subject']}",
                "body": state["draft"],
                "original_sender": sender,
                "original_subject": state["email_subject"]
            }
        }

        # Log and raise interrupt for HITL
        log_email_action(
            state["user_id"],
            state["email_id"],
            sender,
            state["email_subject"],
            state["triage"],
            "awaiting_approval"
        )

        # Stash payload for API-side HITL queue (robust even if interrupt stream isn't captured)
        state["hitl_payload"] = payload
        state["hitl_thread_id"] = f"{state['email_id']}-{uuid.uuid4().hex[:8]}"

        logger.info("Interrupting for approval: email %s to %s", state['email_id'], sender_email)
        decision = interrupt(payload)
        state.setdefault("approvals", []).append(decision)

    return state
