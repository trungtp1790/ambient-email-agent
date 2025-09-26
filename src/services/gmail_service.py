from __future__ import annotations
import base64, os, logging, re
from email.mime.text import MIMEText
from typing import List, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Quiet noisy googleapiclient discovery cache logs
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

SCOPES_SEND = ["https://www.googleapis.com/auth/gmail.send"]
SCOPES_READ = ["https://www.googleapis.com/auth/gmail.readonly"]

def _load_creds(scopes: List[str]) -> Credentials:
    token_path = "token.json"
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials/credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds

def list_recent_messages(label_ids: List[str], max_results=10) -> List[str]:
    try:
        creds = _load_creds(SCOPES_READ)
        service = build("gmail", "v1", credentials=creds)
        res = service.users().messages().list(userId="me", labelIds=label_ids, maxResults=max_results).execute()
        return [m["id"] for m in res.get("messages", [])]
    except HttpError as e:
        logger.error(f"Gmail API error listing messages: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error listing messages: {e}")
        return []

def get_message(msg_id: str) -> Optional[Dict]:
    try:
        creds = _load_creds(SCOPES_READ)
        service = build("gmail", "v1", credentials=creds)
        return service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    except HttpError as e:
        logger.error(f"Gmail API error getting message {msg_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting message {msg_id}: {e}")
        return None

def extract_subject_body(msg: Dict) -> tuple[str, str, str, str]:
    """Extract subject, body, sender, and recipient from Gmail message"""
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("subject", "(no subject)")
    sender = headers.get("from", "unknown@example.com")
    to = headers.get("to", "")
    
    body = ""
    payload = msg.get("payload", {})
    parts = [payload] + (payload.get("parts") or [])
    for p in parts:
        if p.get("mimeType", "").startswith("text/plain"):
            data = p.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                break
        elif p.get("mimeType", "").startswith("text/html") and not body:
            # Fallback to HTML if no plain text
            data = p.get("body", {}).get("data")
            if data:
                html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                # Simple HTML to text conversion
                import re
                body = re.sub(r'<[^>]+>', '', html_body)
                break
    
    return subject, body, sender, to

def extract_sender_email(sender: str) -> str:
    """Extract plain email address from a RFC5322 From header value.

    Examples:
    - 'Alice <alice@example.com>' -> 'alice@example.com'
    - 'bob@example.com' -> 'bob@example.com'
    - '"Carol Doe" <carol.d@example.com>' -> 'carol.d@example.com'
    If nothing matches, returns the original string.
    """
    try:
        match = re.search(r"[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}", sender or "")
        return match.group(0) if match else (sender or "")
    except Exception:  # be resilient
        return sender or ""

def send_email(to_addr: str, subject: str, body: str) -> Optional[str]:
    try:
        creds = _load_creds(SCOPES_SEND)
        service = build("gmail", "v1", credentials=creds)
        msg = MIMEText(body, _charset="utf-8")
        msg["to"] = to_addr
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
        logger.info(f"Email sent successfully to {to_addr}: {sent.get('id', '')}")
        return sent.get("id", "")
    except HttpError as e:
        logger.error(f"Gmail API error sending email to {to_addr}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_addr}: {e}")
        return None

def bootstrap_token():
    # Helper to create token.json locally for both read & send
    _load_creds(list(set(SCOPES_READ + SCOPES_SEND)))
