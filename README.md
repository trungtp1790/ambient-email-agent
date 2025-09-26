# 🤖 Ambient Email Agent

An intelligent email assistant that runs in the background, automatically triages emails, drafts contextual replies using **Gemini AI**, and provides **Human-in-the-Loop (HITL)** approval for sensitive actions. Built with LangGraph, FastAPI, and modern web technologies.

## ✨ Features

### 🧠 AI-Powered Email Processing
- **Smart Triage**: Automatically classifies emails into `needs_reply`, `schedule`, `fyi`, or `spam`
- **Contextual Drafts**: Generates personalized replies using Gemini AI with user preferences
- **VIP Recognition**: Special handling for important contacts with priority processing
- **Memory System**: Learns from user preferences and email patterns

### 🔄 Human-in-the-Loop (HITL)
- **Approval Workflow**: Pauses before sending emails for human review
- **Edit Capability**: Modify drafts before sending
- **Real-time Dashboard**: Modern web interface for managing pending actions
- **Bulk Operations**: Handle multiple emails efficiently

### 🛡️ Enterprise-Ready
- **Free-tier Friendly**: Uses polling instead of webhooks to stay within free limits
- **Comprehensive Logging**: Full audit trail of all actions
- **Error Handling**: Robust error recovery and notification system

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Gmail API credentials
- Gemini API key

### 1. Clone and Setup
```bash
git clone https://github.com/trungtp1790/ambient-email-agent.git
cd ambient-email-agent
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` file:
```env
# Required
GOOGLE_GENERATIVE_AI_API_KEY=your_gemini_api_key_here
HITL_SECRET=your_secure_hitl_secret_here

# Optional
LABELS_TO_WATCH=INBOX,IMPORTANT
POLL_INTERVAL_SECONDS=45
DB_PATH=./data/memory.sqlite
```

### 3. Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create credentials (OAuth 2.0 Client ID)
5. Download credentials as `credentials.json`
6. Place in `credentials/` folder

### 4. Generate Gmail Token
```bash
# Install dependencies
pip install -r requirements.txt

# Generate token (opens browser for OAuth)
python -c "from src.services.gmail_service import bootstrap_token; bootstrap_token()"
```

### 5. Run Locally
```bash
# Start API server
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start the background worker
python -m src.ambient_loop

# Access dashboard
open http://localhost:8000
```

## 📁 Project Structure

```
ambient-email-agent/
├── README.md
├── .env.example
├── requirements.txt
├── (Docker files removed)
├── src/
│   ├── app.py                 # FastAPI application
│   ├── ambient_loop.py        # Background email polling worker
│   ├── services/
│   │   ├── genai_service.py   # Gemini AI integration
│   │   ├── gmail_service.py   # Gmail API wrapper
│   │   └── memory_store.py    # SQLite database operations
│   ├── graph/
│   │   ├── state.py           # LangGraph state definition
│   │   ├── nodes.py           # Graph processing nodes
│   │   └── build.py           # Graph construction
│   └── web/
│       ├── index.html         # HITL dashboard
│       └── styles.css         # Modern UI styles
├── credentials/               # Gmail API credentials
├── data/                     # SQLite database
└── token.json               # Gmail OAuth token
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | ✅ | - | Gemini API key from Google AI Studio |
| `HITL_SECRET` | ✅ | - | Secret for HITL approval endpoint |
| `LABELS_TO_WATCH` | ❌ | `INBOX,IMPORTANT` | Gmail labels to monitor |
| `POLL_INTERVAL_SECONDS` | ❌ | `45` | Email polling frequency |
| `DB_PATH` | ❌ | `./data/memory.sqlite` | SQLite database path |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |
| `API_HOST` | ❌ | `0.0.0.0` | API server host |
| `API_PORT` | ❌ | `8000` | API server port |
| `DEBUG` | ❌ | `false` | Enable debug mode |

### User Profile Configuration

The system learns from your preferences stored in the database:

```python
# Example profile structure
{
    "tone": "polite, concise, friendly",
    "preferred_meeting_hours": "Tue–Thu 09:00–11:30",
    "vip_contacts": ["boss@company.com", "client@important.com"],
    "auto_cc": ["assistant@company.com"]
}
```

## 🎯 Usage

### Dashboard Features

1. **Email Queue**: View all pending email actions
2. **VIP Indicators**: Special badges for important contacts
3. **Priority Filtering**: Sort by priority and status
4. **Bulk Actions**: Approve, edit, or deny multiple emails
5. **Real-time Updates**: Auto-refresh with configurable intervals

### API Endpoints

#### `POST /run-email`
Process a single email through the AI pipeline
```json
{
    "user_id": "u_local",
    "email_id": "msg_123",
    "email_subject": "Meeting Request",
    "email_body": "Can we meet tomorrow?",
    "email_sender": "colleague@company.com",
    "email_recipient": "you@company.com"
}
```

#### `GET /pending`
Get all pending email actions requiring approval

#### `POST /approve`
Approve, edit, or deny a pending action
```json
{
    "thread_id": "thread_123",
    "approved": true,
    "edits": {
        "to": "colleague@company.com",
        "subject": "Re: Meeting Request",
        "body": "Sure, let's meet at 2 PM"
    }
}
```

## 🧠 AI Capabilities

### Email Classification
The system uses Gemini AI to intelligently categorize emails:

- **needs_reply**: Requires immediate response
- **schedule**: Meeting requests, calendar invitations
- **fyi**: Informational emails, no action needed
- **spam**: Unsolicited or suspicious emails

### Draft Generation
AI-generated replies consider:
- User's communication tone preferences
- VIP contact status for priority handling
- Meeting time preferences
- Context from original email
- Professional relationship dynamics

### Memory Learning
The system continuously learns from:
- User approval patterns
- Email response preferences
- VIP contact interactions
- Meeting scheduling habits

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

# Run background worker
python -m src.ambient_loop
```

### Database Management
```python
from src.services.memory_store import *

# Add VIP contact
add_vip_contact("u_local", "boss@company.com", "My Boss", priority=2)

# Get user profile
profile = get_profile("u_local")

# Update preferences
upsert_profile("u_local", {"tone": "professional, concise"})
```

### Testing
```bash
# Test email processing
curl -X POST http://localhost:8000/run-email \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "email_id": "test_123",
    "email_subject": "Test Email",
    "email_body": "This is a test email",
    "email_sender": "test@example.com"
  }'
```

## 🚀 Deployment

### Cloud Deployment

#### Railway
1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically

#### Render
1. Create new Web Service
2. Connect repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn src.app:app --host 0.0.0.0 --port $PORT`

#### Fly.io
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy
fly launch
fly deploy
```

## 🔒 Security

- **OAuth 2.0**: Secure Gmail API authentication
- **HITL Secret**: Protect approval endpoints
- **Input Validation**: Sanitize all user inputs
- **Error Handling**: Prevent information leakage
- **Rate Limiting**: Respect API quotas

## 📊 Monitoring

### Logs
Use your process manager or run services in foreground during development.

### Metrics
- Email processing rate
- AI classification accuracy
- User approval patterns
- System performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Gemini AI](https://ai.google.dev/) for intelligent email processing
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Gmail API](https://developers.google.com/gmail) for email integration

## 📞 Support

- 📧 Email: ambient-email-agent@gmail.com
- 📖 Documentation: [Full docs](https://docs.example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/trungtp1790/ambient-email-agent/issues)

---

**Made with ❤️ for productivity enthusiasts**