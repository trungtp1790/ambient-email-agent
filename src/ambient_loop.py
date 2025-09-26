import os, time
from dotenv import load_dotenv
from src.services import gmail_service as gm
import requests

load_dotenv()
LABELS = [s.strip() for s in os.getenv("LABELS_TO_WATCH","INBOX").split(",")]
POLL = int(os.getenv("POLL_INTERVAL_SECONDS","45"))
API_BASE = (os.getenv("API_BASE","http://127.0.0.1:8000") or "").strip()

def process_message(msg_id: str):
    msg = gm.get_message(msg_id)
    if not msg:
        print(f"Failed to get message {msg_id}")
        return

    subject, body, sender, recipient = gm.extract_subject_body(msg)
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
    except Exception as e:
        print(f"Request error for {msg_id} -> {url}: {e}")

if __name__ == "__main__":
    seen = set()
    while True:
        try:
            ids = gm.list_recent_messages(LABELS, max_results=5)
            for mid in ids:
                if mid in seen:
                    continue
                seen.add(mid)
                process_message(mid)
        except Exception as e:
            print("Loop error:", e)
        time.sleep(POLL)
