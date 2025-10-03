"""
Ambient Email Loop - Background Email Processing Worker
=====================================================

Đây là background worker chạy liên tục để:
- Poll Gmail API để lấy email mới
- Lọc email không cần xử lý (spam, automated)
- Gửi email đến API server để xử lý qua LangGraph
- Theo dõi và log quá trình xử lý

Architecture:
- Polling-based thay vì webhook (để tương thích free tier)
- Email filtering để giảm noise
- HTTP requests đến API server
- Error handling và retry logic
"""

import os, time
from dotenv import load_dotenv
from src.services import gmail_service as gm
import requests

# Load environment variables
load_dotenv()

# Configuration từ environment
LABELS = [s.strip() for s in os.getenv("LABELS_TO_WATCH","INBOX").split(",")]
POLL = int(os.getenv("POLL_INTERVAL_SECONDS","15"))
API_BASE = (os.getenv("API_BASE","http://127.0.0.1:8000") or "").strip()

def should_process_email(subject: str, body: str, sender: str) -> bool:
    """
    Lọc email để quyết định có nên xử lý hay không
    
    Logic filtering:
    1. Skip email có spam indicators
    2. Skip email quá ngắn (có thể là automated)
    3. Skip email chỉ có links/images
    
    Args:
        subject: Tiêu đề email
        body: Nội dung email
        sender: Địa chỉ người gửi
        
    Returns:
        True nếu nên xử lý email, False nếu skip
    """
    # Danh sách từ khóa spam/automated
    spam_indicators = [
        "unsubscribe", "no-reply", "noreply", "donotreply",
        "automated", "auto-generated", "system notification",
        "jobalerts-noreply", "newsletters", "marketing"
    ]
    
    text_to_check = f"{subject} {body} {sender}".lower()
    
    # Skip nếu chứa spam indicators
    if any(indicator in text_to_check for indicator in spam_indicators):
        return False
    
    # Skip email quá ngắn (có thể là automated)
    if len(body.strip()) < 50:
        return False
        
    # Skip email chỉ có links/images
    if len(body.strip()) < 100 and ("http" in body or "www." in body):
        return False
    
    return True

def process_message(msg_id: str):
    """
    Xử lý một email message cụ thể
    
    Workflow:
    1. Lấy message từ Gmail API
    2. Extract subject, body, sender, recipient
    3. Apply filtering logic
    4. Gửi đến API server để xử lý qua LangGraph
    
    Args:
        msg_id: Gmail message ID cần xử lý
    """
    # Lấy message từ Gmail API
    msg = gm.get_message(msg_id)
    if not msg:
        print(f"Failed to get message {msg_id}")
        return

    # Extract thông tin từ message
    subject, body, sender, recipient = gm.extract_subject_body(msg)
    
    # Apply filtering logic
    if not should_process_email(subject, body, sender):
        print(f"Skipped: {msg_id} - {subject[:50]}... (filtered out)")
        # Note: Không thể increment skipped_count ở đây vì scope khác
        return
    
    # Tạo payload để gửi đến API
    payload = {
        "user_id": "u_local",
        "email_id": msg_id,
        "email_subject": subject,
        "email_body": body,
        "email_sender": sender,
        "email_recipient": recipient
    }
    
    try:
        # Gửi đến API server để HITL interrupts được capture trong UI queue
        url = f"{API_BASE.rstrip('/')}/run-email"
        res = requests.post(url, json=payload, timeout=30)
        if res.ok:
            data = res.json()
            status = data.get("status")
            print(f"Processed: {msg_id} - {status} (from: {sender})")
        else:
            print(f"API error {res.status_code} for {msg_id} -> {url}: {res.text}")
    except (requests.RequestException, ValueError) as e:
        print(f"Request error for {msg_id} -> {url}: {e}")

if __name__ == "__main__":
    """
    Main loop cho background email processing worker
    
    Workflow:
    1. Khởi tạo tracking variables
    2. Poll Gmail API mỗi POLL seconds
    3. Lọc email mới chưa xử lý
    4. Process từng email qua process_message()
    5. Log statistics và continue loop
    6. Handle errors gracefully và continue running
    """
    # Tracking variables
    seen = set()  # Set các message ID đã xử lý
    processed_count = 0  # Số email đã process
    skipped_count = 0  # Số email đã skip (không được track chính xác)
    
    print("🤖 Starting email processing loop...")
    print(f"📧 Polling every {POLL} seconds for up to 20 emails per batch")
    print(f"🏷️  Watching labels: {LABELS}")
    print("=" * 60)
    
    while True:
        try:
            # Lấy danh sách message IDs từ Gmail
            ids = gm.list_recent_messages(LABELS, max_results=20)
            new_emails = [mid for mid in ids if mid not in seen]
            
            if new_emails:
                print(f"\n📬 Found {len(new_emails)} new emails to process...")
                
                # Process từng email mới
                for mid in new_emails:
                    seen.add(mid)
                    process_message(mid)
                    processed_count += 1
                    
                print(f"📊 Stats: Processed={processed_count}, Skipped={skipped_count}, Total seen={len(seen)}")
            else:
                print(f"⏳ No new emails found, waiting {POLL}s...")
                
        except (KeyboardInterrupt, SystemExit):
            print("\n🛑 Shutting down email processor...")
            break
        except (ValueError, OSError, RuntimeError) as e:
            print(f"❌ Loop error: {e}")
            # Continue running even if there's an error
        time.sleep(POLL)
