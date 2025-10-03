# seed_data.py
from src.services.memory_store import upsert_profile, add_vip_contact

def main():
    # seed user profile
    upsert_profile("u_local", {
        "tone": "polite, concise, friendly",
        "preferred_meeting_hours": "Tue–Thu 09:00–11:30",
        "auto_cc": ["assistant@company.com"]
    })

    # seed VIP contact
    add_vip_contact("u_local", "boss@company.com", "My Boss", priority=2)

    print("✅ Seeded profile and VIP contact.")

if __name__ == "__main__":
    main()
