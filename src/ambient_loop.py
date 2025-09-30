import os, time
from dotenv import load_dotenv
from src.services import gmail_service as gm
import requests

load_dotenv()
LABELS = [s.strip() for s in os.getenv("LABELS_TO_WATCH","INBOX").split(",")]
POLL = int(os.getenv("POLL_INTERVAL_SECONDS","15"))
API_BASE = (os.getenv("API_BASE","http://127.0.0.1:8000") or "").strip()

def should_process_email(subject: str, body: str, sender: str) -> bool:
    """Filter out emails that don't need processing"""
    # Skip obvious spam/automated emails
    spam_indicators = [
        "unsubscribe", "no-reply", "noreply", "donotreply",
        "automated", "auto-generated", "system notification",
        "jobalerts-noreply", "newsletters", "marketing"
    ]
    
    text_to_check = f"{subject} {body} {sender}".lower()
    
    # Skip if contains spam indicators
    if any(indicator in text_to_check for indicator in spam_indicators):
        return False
    
    # Skip very short emails (likely automated)
    if len(body.strip()) < 50:
        return False
        
    # Skip emails with only links/images
    if len(body.strip()) < 100 and ("http" in body or "www." in body):
        return False
    
    return True

def process_message(msg_id: str):
    msg = gm.get_message(msg_id)
    if not msg:
        print(f"Failed to get message {msg_id}")
        return

    subject, body, sender, recipient = gm.extract_subject_body(msg)
    
    # Apply filtering
    if not should_process_email(subject, body, sender):
        print(f"Skipped: {msg_id} - {subject[:50]}... (filtered out)")
        # Note: We can't increment skipped_count here since it's in different scope
        return
    
    payload = {
        "user_id": "u_local",
        "email_id": msg_id,
        "email_subject": subject,
        "email_body": body,
        "email_sender": sender,
        "email_recipient": recipient
    }
    try:
        # Send to API so HITL interrupts are captured in the UI queue
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
    seen = set()
    processed_count = 0
    skipped_count = 0
    
    print("🤖 Starting email processing loop...")
    print(f"📧 Polling every {POLL} seconds for up to 20 emails per batch")
    print(f"🏷️  Watching labels: {LABELS}")
    print("=" * 60)
    
    while True:
        try:
            ids = gm.list_recent_messages(LABELS, max_results=20)
            new_emails = [mid for mid in ids if mid not in seen]
            
            if new_emails:
                print(f"\n📬 Found {len(new_emails)} new emails to process...")
                
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
