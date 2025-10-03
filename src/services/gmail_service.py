"""
Gmail Service - Gmail API Integration
====================================

Service này cung cấp các chức năng:
- OAuth2 authentication với Gmail API
- Lấy danh sách email từ Gmail
- Extract nội dung email (subject, body, sender)
- Gửi email qua Gmail API
- Bootstrap token cho development

Architecture:
- Sử dụng Google API Client Library
- OAuth2 flow cho authentication
- Error handling cho API calls
- Base64 encoding/decoding cho email content
"""

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

# Gmail API scopes
SCOPES_SEND = ["https://www.googleapis.com/auth/gmail.send"]
SCOPES_READ = ["https://www.googleapis.com/auth/gmail.readonly"]

def _load_creds(scopes: List[str]) -> Credentials:
    """
    Load hoặc tạo OAuth2 credentials cho Gmail API
    
    Workflow:
    1. Kiểm tra token.json có tồn tại không
    2. Nếu có, load credentials từ file
    3. Nếu credentials expired, refresh token
    4. Nếu không có hoặc invalid, chạy OAuth flow
    5. Lưu credentials vào token.json
    
    Args:
        scopes: List các Gmail API scopes cần thiết
        
    Returns:
        Valid Credentials object để sử dụng với Gmail API
    """
    token_path = "token.json"
    creds = None
    
    # Load existing credentials nếu có
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    
    # Kiểm tra và refresh credentials nếu cần
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # Chạy OAuth flow để tạo credentials mới
            flow = InstalledAppFlow.from_client_secrets_file("credentials/credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        
        # Lưu credentials vào file
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    
    return creds

def list_recent_messages(label_ids: List[str], max_results=10) -> List[str]:
    """
    Lấy danh sách message IDs từ Gmail theo labels
    
    Args:
        label_ids: List các Gmail labels để filter (e.g., ["INBOX", "IMPORTANT"])
        max_results: Số lượng messages tối đa cần lấy
        
    Returns:
        List các message IDs, empty list nếu có lỗi
    """
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
    """
    Lấy full message content từ Gmail theo message ID
    
    Args:
        msg_id: Gmail message ID
        
    Returns:
        Dict chứa full message data, None nếu có lỗi
    """
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
    """
    Extract subject, body, sender, và recipient từ Gmail message
    
    Workflow:
    1. Parse headers để lấy subject, from, to
    2. Tìm text/plain part trong message payload
    3. Nếu không có plain text, fallback sang HTML và strip tags
    4. Decode base64 content
    
    Args:
        msg: Gmail message dict từ API
        
    Returns:
        Tuple (subject, body, sender, recipient)
    """
    # Parse headers
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    subject = headers.get("subject", "(no subject)")
    sender = headers.get("from", "unknown@example.com")
    to = headers.get("to", "")
    
    # Extract body từ message parts
    body = ""
    payload = msg.get("payload", {})
    parts = [payload] + (payload.get("parts") or [])
    
    for p in parts:
        if p.get("mimeType", "").startswith("text/plain"):
            # Ưu tiên plain text
            data = p.get("body", {}).get("data")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                break
        elif p.get("mimeType", "").startswith("text/html") and not body:
            # Fallback sang HTML nếu không có plain text
            data = p.get("body", {}).get("data")
            if data:
                html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                # Simple HTML to text conversion
                import re
                body = re.sub(r'<[^>]+>', '', html_body)
                break
    
    return subject, body, sender, to

def extract_sender_email(sender: str) -> str:
    """
    Extract plain email address từ RFC5322 From header value
    
    Xử lý các format khác nhau của From header:
    - 'Alice <alice@example.com>' -> 'alice@example.com'
    - 'bob@example.com' -> 'bob@example.com'
    - '"Carol Doe" <carol.d@example.com>' -> 'carol.d@example.com'
    
    Args:
        sender: From header string từ Gmail
        
    Returns:
        Plain email address, hoặc original string nếu không match
    """
    try:
        match = re.search(r"[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}", sender or "")
        return match.group(0) if match else (sender or "")
    except Exception:  # be resilient
        return sender or ""

def send_email(to_addr: str, subject: str, body: str) -> Optional[str]:
    """
    Gửi email qua Gmail API
    
    Workflow:
    1. Load credentials với SEND scope
    2. Tạo MIMEText message
    3. Encode thành base64
    4. Gửi qua Gmail API
    
    Args:
        to_addr: Địa chỉ người nhận
        subject: Tiêu đề email
        body: Nội dung email
        
    Returns:
        Message ID nếu thành công, None nếu có lỗi
    """
    try:
        creds = _load_creds(SCOPES_SEND)
        service = build("gmail", "v1", credentials=creds)
        
        # Tạo MIME message
        msg = MIMEText(body, _charset="utf-8")
        msg["to"] = to_addr
        msg["subject"] = subject
        
        # Encode và gửi
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
    """
    Helper function để tạo token.json cho development
    
    Chạy OAuth flow để tạo credentials cho cả READ và SEND scopes
    """
    _load_creds(list(set(SCOPES_READ + SCOPES_SEND)))
