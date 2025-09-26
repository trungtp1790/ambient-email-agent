from sqlalchemy import create_engine, text
import os, json, logging
from typing import Dict, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{os.getenv('DB_PATH','./data/memory.sqlite')}", future=True)

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS profile(
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS prefs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            key TEXT,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS email_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            email_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            subject TEXT,
            triage_result TEXT,
            action_taken TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vip_contacts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            name TEXT,
            priority INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, email)
        );"""))

def get_profile(user_id: str):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT data FROM profile WHERE user_id=:u"), {"u": user_id}).fetchone()
        if row:
            try:
                return json.loads(row[0])
            except Exception:
                pass
        return {
            "tone": "polite, concise, friendly",
            "preferred_meeting_hours": "Tue–Thu 09:00–11:30",
            "vip_contacts": [],
            "auto_cc": []
        }

def upsert_profile(user_id: str, patch: dict):
    prof = get_profile(user_id)
    prof.update(patch)
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO profile(user_id, data, updated_at) VALUES(:u,:d,CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET data=:d, updated_at=CURRENT_TIMESTAMP
        """), {"u": user_id, "d": json.dumps(prof)})
    logger.info(f"Updated profile for user {user_id}")
    return prof

def add_vip_contact(user_id: str, email: str, name: str = "", priority: int = 1, notes: str = ""):
    """Add or update a VIP contact"""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
            INSERT INTO vip_contacts(user_id, email, name, priority, notes)
            VALUES(:u, :e, :n, :p, :notes)
            ON CONFLICT(user_id, email) DO UPDATE SET
            name=:n, priority=:p, notes=:notes
            """), {"u": user_id, "e": email, "n": name, "p": priority, "notes": notes})
        logger.info(f"Added VIP contact {email} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding VIP contact: {e}")
        return False

def get_vip_contacts(user_id: str) -> List[Dict]:
    """Get all VIP contacts for a user"""
    try:
        with engine.begin() as conn:
            rows = conn.execute(text("""
            SELECT email, name, priority, notes FROM vip_contacts 
            WHERE user_id=:u ORDER BY priority DESC, name
            """), {"u": user_id}).fetchall()
            return [{"email": row[0], "name": row[1], "priority": row[2], "notes": row[3]} for row in rows]
    except Exception as e:
        logger.error(f"Error getting VIP contacts: {e}")
        return []

def is_vip_contact(user_id: str, email: str) -> bool:
    """Check if an email is a VIP contact"""
    try:
        with engine.begin() as conn:
            row = conn.execute(text("""
            SELECT 1 FROM vip_contacts WHERE user_id=:u AND email=:e
            """), {"u": user_id, "e": email}).fetchone()
            return row is not None
    except Exception as e:
        logger.error(f"Error checking VIP contact: {e}")
        return False

def log_email_action(user_id: str, email_id: str, sender: str, subject: str, triage_result: str, action_taken: str):
    """Log email processing action"""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
            INSERT INTO email_history(user_id, email_id, sender, subject, triage_result, action_taken)
            VALUES(:u, :eid, :s, :subj, :triage, :action)
            """), {"u": user_id, "eid": email_id, "s": sender, "subj": subject, "triage": triage_result, "action": action_taken})
        logger.info(f"Logged email action for {email_id}: {action_taken}")
    except Exception as e:
        logger.error(f"Error logging email action: {e}")

def get_email_stats(user_id: str, days: int = 7) -> Dict:
    """Get email processing statistics"""
    try:
        with engine.begin() as conn:
            # Get triage distribution
            triage_stats = conn.execute(text("""
            SELECT triage_result, COUNT(*) as count 
            FROM email_history 
            WHERE user_id=:u AND created_at >= datetime('now', '-{} days')
            GROUP BY triage_result
            """.format(days)), {"u": user_id}).fetchall()
            
            # Get action distribution
            action_stats = conn.execute(text("""
            SELECT action_taken, COUNT(*) as count 
            FROM email_history 
            WHERE user_id=:u AND created_at >= datetime('now', '-{} days')
            GROUP BY action_taken
            """.format(days)), {"u": user_id}).fetchall()
            
            return {
                "triage_distribution": {row[0]: row[1] for row in triage_stats},
                "action_distribution": {row[0]: row[1] for row in action_stats},
                "period_days": days
            }
    except Exception as e:
        logger.error(f"Error getting email stats: {e}")
        return {"triage_distribution": {}, "action_distribution": {}, "period_days": days}
