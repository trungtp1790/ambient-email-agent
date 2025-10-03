# 🤖 Ambient Email Agent

An intelligent email assistant that runs in the background, automatically triages emails, drafts contextual replies using **Gemini AI**, and provides **Human-in-the-Loop (HITL)** approval for sensitive actions. Built with LangGraph, FastAPI, and modern web technologies.

## ✨ Features

- **🧠 AI-Powered**: Smart email classification (needs_reply, schedule, fyi, spam) and contextual draft generation
- **🔄 HITL Workflow**: Human approval for sensitive actions with edit capabilities
- **👑 VIP Recognition**: Special handling for important contacts with priority processing
- **💾 Memory Learning**: Learns from user preferences and email patterns
- **🛡️ Enterprise-Ready**: Free-tier friendly, comprehensive logging, robust error handling

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Gmail API credentials
- Gemini API key

### Setup
```bash
# 1. Clone and install
git clone https://github.com/trungtp1790/ambient-email-agent.git
cd ambient-email-agent
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Setup Gmail API
# - Go to Google Cloud Console
# - Enable Gmail API
# - Create OAuth 2.0 credentials
# - Download as credentials/credentials.json

# 4. Generate Gmail token
python -c "from src.services.gmail_service import bootstrap_token; bootstrap_token()"

# 5. Run the system
python start_dev.py
# Or manually:
# uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
# python -m src.ambient_loop
```

## 🏗️ Architecture

### Core Components
- **FastAPI Server**: REST API + web dashboard
- **Background Worker**: Gmail polling + email processing
- **LangGraph Pipeline**: AI-powered workflow (Triage → Agent → Sensitive)
- **Services**: Gmail API, Gemini AI, SQLite storage

### Data Flow
```
Gmail API → Polling → Filtering → LangGraph → HITL Queue → User Approval → Send Email
```

### LangGraph Pipeline
```
Email Input → Triage → Agent → Sensitive → Output/Interrupt
```

- **Triage**: Classify email + check VIP status + set priority
- **Agent**: Generate draft reply with user context
- **Sensitive**: Create HITL payload + interrupt for approval

## 📁 Project Structure

```
src/
├── app.py                 # FastAPI application
├── ambient_loop.py        # Background worker
├── services/
│   ├── gmail_service.py   # Gmail API integration
│   ├── genai_service.py   # Gemini AI integration
│   └── memory_store.py    # SQLite database
├── graph/
│   ├── state.py           # LangGraph state definition
│   ├── nodes.py           # Processing nodes
│   └── build.py           # Graph construction
└── web/
    ├── index.html         # HITL dashboard
    └── styles.css         # UI styles
```

## 🔧 Configuration

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | ✅ | - | Gemini API key |
| `HITL_SECRET` | ✅ | - | HITL approval secret |
| `LABELS_TO_WATCH` | ❌ | `INBOX,IMPORTANT` | Gmail labels to monitor |
| `POLL_INTERVAL_SECONDS` | ❌ | `15` | Polling frequency |
| `DB_PATH` | ❌ | `./data/memory.sqlite` | Database path |

### User Profile
```python
{
    "tone": "polite, concise, friendly",
    "preferred_meeting_hours": "Tue–Thu 09:00–11:30",
    "vip_contacts": ["boss@company.com"],
    "auto_cc": ["assistant@company.com"]
}
```

## 🎯 Usage

### Dashboard Features
- **Email Queue**: View pending approvals
- **VIP Indicators**: Special badges for important contacts
- **Priority Filtering**: Sort by priority and status
- **Edit Capability**: Modify drafts before sending
- **Real-time Updates**: Auto-refresh with configurable intervals

### API Endpoints

#### `POST /run-email`
Process email through AI pipeline
```json
{
    "user_id": "u_local",
    "email_id": "msg_123",
    "email_subject": "Meeting Request",
    "email_body": "Can we meet tomorrow?",
    "email_sender": "colleague@company.com"
}
```

#### `GET /pending`
Get all pending email actions

#### `POST /approve`
Approve, edit, or deny pending action
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
- **needs_reply**: Requires immediate response
- **schedule**: Meeting requests, calendar invitations
- **fyi**: Informational emails, no action needed
- **spam**: Unsolicited or suspicious emails

### Draft Generation
AI considers user tone preferences, VIP status, meeting hours, and email context.

### Memory Learning
System learns from approval patterns, response preferences, and VIP interactions.

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
  -d '{"user_id": "test_user", "email_id": "test_123", "email_subject": "Test", "email_body": "Test email", "email_sender": "test@example.com"}'
```

## 🚀 Deployment

### Cloud Platforms
- **Railway**: Connect repo + set env vars + deploy
- **Render**: Web Service + build command + start command
- **Fly.io**: `fly launch` + `fly deploy`

### Production Setup
```bash
# Build command
pip install -r requirements.txt

# Start command
uvicorn src.app:app --host 0.0.0.0 --port $PORT
```

## 🔒 Security

- **OAuth 2.0**: Secure Gmail API authentication
- **HITL Secret**: Protect approval endpoints
- **Input Validation**: Sanitize all user inputs
- **Error Handling**: Prevent information leakage
- **Rate Limiting**: Respect API quotas

## 📊 Monitoring

### Real-time Features
- Email queue with live updates
- Processing statistics
- VIP indicators
- Error tracking

### Health Checks
- `GET /health` for API status
- Database connectivity monitoring
- External API health checks

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for workflow orchestration
- [Gemini AI](https://ai.google.dev/) for intelligent email processing
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Gmail API](https://developers.google.com/gmail) for email integration

## 📞 Support

- 📧 Email: ambient-email-agent@gmail.com
- 🐛 Issues: [GitHub Issues](https://github.com/trungtp1790/ambient-email-agent/issues)

---

**Made with ❤️ for productivity enthusiasts**