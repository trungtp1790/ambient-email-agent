# 🚀 Quick Start Guide

Get your Ambient Email Agent up and running in 5 minutes!

## Prerequisites
- Python 3.11+
- Gmail account
- Gemini API key (free from [Google AI Studio](https://makersuite.google.com/app/apikey))

## 1. Setup (2 minutes)

```bash
# Clone and setup
git clone <your-repo>
cd ambient-email-agent
cp .env.example .env

# Edit .env file
# Set your GOOGLE_GENERATIVE_AI_API_KEY and HITL_SECRET
```

## 2. Gmail API Setup (2 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download as `credentials.json` → place in `credentials/` folder

## 3. Generate Gmail Token (1 minute)

```bash
# Install dependencies
pip install -r requirements.txt

# Generate token (opens browser)
python -c "from src.services.gmail_service import bootstrap_token; bootstrap_token()"
```

## 4. Start the System

```bash
# Option 1: Development mode (recommended)
python start_dev.py

# Option 2: Manual mode
uvicorn src.app:app --reload &
python -m src.ambient_loop &
```

## 5. Access Dashboard

Open http://localhost:8000 in your browser

## 🎯 First Steps

1. **Test the system**: Click "Send Demo" button
2. **Configure settings**: Click the settings gear icon
3. **Add VIP contacts**: Use the API or database directly
4. **Monitor emails**: Watch the dashboard for pending actions

## 🔧 Configuration

### User Profile
```python
# Example: Set your communication style
from src.services.memory_store import upsert_profile
upsert_profile("u_local", {
    "tone": "professional, friendly",
    "preferred_meeting_hours": "Mon-Fri 10:00-16:00"
})
```

### VIP Contacts
```python
# Example: Add important contacts
from src.services.memory_store import add_vip_contact
add_vip_contact("u_local", "boss@company.com", "My Boss", priority=2)
```

## 🧪 Test Everything

```bash
# Run integration tests
python test_integration.py
```

## 📱 Features to Try

- **Email Classification**: Send test emails and see AI categorization
- **Draft Generation**: Watch AI create contextual replies
- **VIP Handling**: See priority processing for important contacts
- **HITL Approval**: Review and edit before sending
- **Real-time Dashboard**: Monitor all email activity

## 🆘 Troubleshooting

### Common Issues

**"Gmail API error"**
- Check credentials.json is in correct location
- Verify Gmail API is enabled in Google Cloud Console
- Regenerate token if expired

**"Gemini API error"**
- Verify GOOGLE_GENERATIVE_AI_API_KEY is correct
- Check API quota limits

**"Database error"**
- Ensure data/ directory exists
- Check file permissions

**"Port already in use"**
- Change API_PORT in .env file
- Kill existing processes: `pkill -f uvicorn`

### Getting Help

- Run tests: `python test_integration.py`
- View API docs: http://localhost:8000/docs

## 🎉 You're Ready!

Your Ambient Email Agent is now running! The system will:

1. **Monitor** your Gmail inbox every 45 seconds
2. **Classify** emails using AI
3. **Generate** contextual reply drafts
4. **Pause** for your approval before sending
5. **Learn** from your preferences over time

Enjoy your new AI email assistant! 🤖📧
