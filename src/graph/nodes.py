"""
LangGraph Processing Nodes
=========================

Các nodes xử lý trong LangGraph workflow:
1. node_triage: Phân loại email và xác định priority
2. node_agent: Generate draft reply sử dụng AI
3. node_sensitive: Handle HITL approval cho sensitive actions

Architecture:
- Mỗi node nhận EmailState và trả về updated state
- Error handling với fallback values
- Logging cho debugging và monitoring
- Interrupt mechanism cho HITL workflow
"""

from langgraph.types import interrupt
from src.graph.state import EmailState
from src.services.genai_service import classify_email, draft_reply
from src.services.gmail_service import extract_sender_email
from src.services.memory_store import get_profile, get_vip_contacts, is_vip_contact, log_email_action
import uuid
import logging

logger = logging.getLogger(__name__)

def node_triage(state: EmailState) -> EmailState:
    """
    Phân loại email và xác định priority dựa trên sender
    
    Workflow:
    1. Extract sender email từ header
    2. Kiểm tra VIP status
    3. Classify email sử dụng AI
    4. Xác định proposed action
    5. Log triage action
    
    Args:
        state: EmailState chứa email information
        
    Returns:
        Updated EmailState với triage, priority, is_vip, proposed_action
    """
    try:
        sender = state.get("email_sender", "")
        sender_email = extract_sender_email(sender)
        
        # Kiểm tra VIP status
        is_vip = is_vip_contact(state["user_id"], sender_email)
        state["is_vip"] = is_vip
        state["priority"] = 2 if is_vip else 1
        
        # Classify email với sender context
        label = classify_email(state["email_subject"], state["email_body"], sender)
        state["triage"] = label
        
        # Xác định action dựa trên classification
        if label == "needs_reply":
            state["proposed_action"] = "send_email"
        elif label == "schedule":
            state["proposed_action"] = "create_event"
        else:
            state["proposed_action"] = "none"
            
        # Log triage action
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
        # Fallback values khi có lỗi
        state["triage"] = "fyi"
        state["proposed_action"] = "none"
        state["is_vip"] = False
        state["priority"] = 1
        return state

def node_agent(state: EmailState) -> EmailState:
    """
    Generate draft reply sử dụng AI với VIP context
    
    Workflow:
    1. Kiểm tra nếu email cần reply (needs_reply)
    2. Lấy user profile và VIP contacts
    3. Generate draft reply với context
    4. Log draft generation action
    
    Args:
        state: EmailState với triage information
        
    Returns:
        Updated EmailState với draft content
    """
    try:
        if state.get("triage") == "needs_reply":
            # Lấy user profile và VIP contacts
            prof = get_profile(state["user_id"])
            vip_contacts = get_vip_contacts(state["user_id"])
            vip_emails = [contact["email"] for contact in vip_contacts]
            
            # Generate draft reply với context
            state["draft"] = draft_reply(
                state["email_subject"], 
                state["email_body"],
                tone=prof["tone"], 
                pref_hours=prof["preferred_meeting_hours"],
                sender=state.get("email_sender", ""),
                vip_contacts=vip_emails
            )
            
            # Log draft generation action
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
    """
    Handle sensitive actions với human-in-the-loop approval
    
    Workflow:
    1. Kiểm tra nếu có proposed action là send_email và có draft
    2. Tạo HITL payload với proposal details
    3. Log awaiting_approval action
    4. Stash payload cho API-side HITL queue
    5. Raise interrupt để pause workflow
    
    IMPORTANT: Không được catch Interrupt exception. Nó phải bubble up
    để runtime có thể pause và API capture interrupt payload.
    
    Args:
        state: EmailState với proposed_action và draft
        
    Returns:
        Updated EmailState (nếu không có interrupt)
    """
    if state.get("proposed_action") == "send_email" and state.get("draft"):
        sender = state.get("email_sender", "")
        sender_email = extract_sender_email(sender)

        # Tạo HITL payload
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

        # Log và raise interrupt cho HITL
        log_email_action(
            state["user_id"],
            state["email_id"],
            sender,
            state["email_subject"],
            state["triage"],
            "awaiting_approval"
        )

        # Stash payload cho API-side HITL queue (robust ngay cả khi interrupt stream không được capture)
        state["hitl_payload"] = payload
        state["hitl_thread_id"] = f"{state['email_id']}-{uuid.uuid4().hex[:8]}"

        logger.info("Interrupting for approval: email %s to %s", state['email_id'], sender_email)
        decision = interrupt(payload)
        state.setdefault("approvals", []).append(decision)

    return state
