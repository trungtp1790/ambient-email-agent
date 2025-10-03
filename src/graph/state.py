"""
LangGraph State Definition
=========================

Định nghĩa state structure cho LangGraph workflow.
State này được truyền qua các nodes trong graph và chứa tất cả
thông tin cần thiết cho email processing pipeline.

Architecture:
- TypedDict để type safety
- total=False cho optional fields
- Literal types cho enum values
- Nested structures cho complex data
"""

from typing import TypedDict, Literal, Optional, List, Dict

class EmailState(TypedDict, total=False):
    """
    State structure cho LangGraph email processing workflow
    
    Fields:
        user_id: ID của user (required)
        email_id: Gmail message ID hoặc local ID (required)
        email_subject: Tiêu đề email (required)
        email_body: Nội dung email (required)
        email_sender: Địa chỉ người gửi (required)
        email_recipient: Địa chỉ người nhận (optional)
        triage: Kết quả phân loại email (needs_reply, schedule, fyi, spam)
        draft: Draft reply được generate bởi AI (optional)
        proposed_action: Hành động được đề xuất (send_email, create_event, none)
        approvals: List các approval decisions (optional)
        is_vip: Có phải VIP contact không (boolean)
        priority: Độ ưu tiên (1=normal, 2=high/VIP)
    """
    user_id: str
    email_id: str
    email_subject: str
    email_body: str
    email_sender: str
    email_recipient: str
    triage: Literal["needs_reply","schedule","fyi","spam"]
    draft: Optional[str]
    proposed_action: Optional[str]
    approvals: List[Dict]
    is_vip: bool
    priority: int
