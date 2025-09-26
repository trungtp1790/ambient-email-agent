from typing import TypedDict, Literal, Optional, List, Dict

class EmailState(TypedDict, total=False):
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
