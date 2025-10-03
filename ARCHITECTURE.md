# Ambient Email Agent - Architecture Documentation

## Tổng quan

Ambient Email Agent là một hệ thống AI-powered email assistant chạy trong background, tự động phân loại email, tạo draft reply, và cung cấp Human-in-the-Loop (HITL) approval cho các hành động nhạy cảm.

## Kiến trúc hệ thống

### 1. Core Components

#### 1.1 FastAPI Application (`src/app.py`)
- **Chức năng**: REST API server và web dashboard
- **Endpoints**:
  - `POST /run-email`: Xử lý email qua LangGraph workflow
  - `GET /pending`: Lấy danh sách email chờ approval
  - `POST /approve`: Xử lý approval/denial cho email
  - `GET /`: Web dashboard HITL
- **Features**:
  - LangGraph integration với memory checkpointing
  - In-memory queue cho pending approvals
  - Static file serving cho web UI

#### 1.2 Background Worker (`src/ambient_loop.py`)
- **Chức năng**: Poll Gmail API và xử lý email mới
- **Workflow**:
  1. Poll Gmail API mỗi 15 giây (configurable)
  2. Lọc email không cần xử lý (spam, automated)
  3. Gửi email đến API server để xử lý
  4. Log statistics và errors
- **Features**:
  - Email filtering để giảm noise
  - Error handling và retry logic
  - Configurable polling interval

#### 1.3 Development Startup (`start_dev.py`)
- **Chức năng**: Script khởi động development environment
- **Features**:
  - Environment validation
  - Gmail credentials checking
  - Process monitoring
  - Graceful shutdown

### 2. Services Layer

#### 2.1 Gmail Service (`src/services/gmail_service.py`)
- **Chức năng**: Gmail API integration
- **Features**:
  - OAuth2 authentication với auto-refresh
  - Email listing và retrieval
  - Content extraction (subject, body, sender)
  - Email sending
  - Bootstrap token cho development

#### 2.2 GenAI Service (`src/services/genai_service.py`)
- **Chức năng**: Google Gemini AI integration
- **Features**:
  - Email classification (needs_reply, schedule, fyi, spam)
  - Draft reply generation với context awareness
  - VIP contact recognition
  - Fallback heuristics khi AI fails
- **Model**: Gemini 2.5 Flash

#### 2.3 Memory Store (`src/services/memory_store.py`)
- **Chức năng**: SQLite database operations
- **Features**:
  - User profiles và preferences
  - VIP contacts management
  - Email processing history
  - Statistics và analytics
- **Tables**:
  - `profile`: User profiles với JSON data
  - `vip_contacts`: VIP contacts với priority
  - `email_history`: Processing history
  - `prefs`: User preferences (unused)

### 3. LangGraph Workflow

#### 3.1 State Definition (`src/graph/state.py`)
- **EmailState**: TypedDict chứa tất cả thông tin email
- **Fields**:
  - `user_id`, `email_id`, `email_subject`, `email_body`, `email_sender`
  - `triage`: Classification result
  - `draft`: AI-generated reply
  - `proposed_action`: Suggested action
  - `is_vip`, `priority`: VIP status và priority

#### 3.2 Processing Nodes (`src/graph/nodes.py`)
- **node_triage**: Phân loại email và xác định priority
- **node_agent**: Generate draft reply với AI
- **node_sensitive**: Handle HITL approval cho sensitive actions

#### 3.3 Graph Builder (`src/graph/build.py`)
- **Workflow**: START → triage → agent → sensitive → END
- **Features**: Linear flow với interrupt handling

### 4. Web Interface

#### 4.1 Dashboard (`src/web/index.html`)
- **Chức năng**: HITL approval interface
- **Features**:
  - Real-time email queue
  - VIP indicators và priority filtering
  - Edit capabilities cho drafts
  - Bulk operations
  - Auto-refresh với configurable intervals

## Data Flow

### 1. Email Processing Flow

```
Gmail API → ambient_loop → API Server → LangGraph → HITL Queue → User Approval → Gmail API
```

1. **Polling**: `ambient_loop.py` poll Gmail API
2. **Filtering**: Lọc email không cần xử lý
3. **API Call**: Gửi email đến `/run-email` endpoint
4. **LangGraph**: Chạy qua workflow (triage → agent → sensitive)
5. **Interrupt**: Nếu cần approval, tạo interrupt
6. **HITL Queue**: Lưu vào PENDING queue
7. **User Review**: User xem và approve/deny/edit
8. **Send**: Gửi email qua Gmail API

### 2. LangGraph Workflow

```
Email Input → Triage → Agent → Sensitive → Output/Interrupt
```

1. **Triage Node**:
   - Extract sender email
   - Check VIP status
   - Classify email với AI
   - Determine proposed action
   - Log triage action

2. **Agent Node**:
   - Check nếu cần reply
   - Get user profile và VIP contacts
   - Generate draft reply với AI
   - Log draft generation

3. **Sensitive Node**:
   - Check nếu có proposed action
   - Create HITL payload
   - Log awaiting approval
   - Raise interrupt cho approval

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | ✅ | - | Gemini API key |
| `HITL_SECRET` | ✅ | - | Secret cho HITL approval |
| `LABELS_TO_WATCH` | ❌ | `INBOX` | Gmail labels để monitor |
| `POLL_INTERVAL_SECONDS` | ❌ | `15` | Polling frequency |
| `DB_PATH` | ❌ | `./data/memory.sqlite` | SQLite database path |
| `API_BASE` | ❌ | `http://127.0.0.1:8000` | API server URL |

### User Profile Structure

```json
{
    "tone": "polite, concise, friendly",
    "preferred_meeting_hours": "Tue–Thu 09:00–11:30",
    "vip_contacts": ["boss@company.com", "client@important.com"],
    "auto_cc": ["assistant@company.com"]
}
```

## Security

### 1. Authentication
- **Gmail API**: OAuth2 với auto-refresh
- **HITL Endpoints**: Secret header validation
- **API Keys**: Environment variable storage

### 2. Data Protection
- **Input Validation**: Pydantic models
- **Error Handling**: Graceful degradation
- **Logging**: Comprehensive audit trail

## Monitoring & Logging

### 1. Logging Levels
- **INFO**: Normal operations
- **WARNING**: Fallback scenarios
- **ERROR**: Exceptions và failures

### 2. Metrics
- Email processing rate
- AI classification accuracy
- User approval patterns
- System performance

## Deployment

### 1. Local Development
```bash
# Start API server
uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

# Start background worker
python -m src.ambient_loop

# Or use development script
python start_dev.py
```

### 2. Production
- **API Server**: Deploy FastAPI app
- **Background Worker**: Run as separate process
- **Database**: SQLite file hoặc external database
- **Monitoring**: Process manager (PM2, systemd)

## Error Handling

### 1. API Errors
- **Gmail API**: Retry với exponential backoff
- **Gemini AI**: Fallback sang heuristic rules
- **Database**: Transaction rollback

### 2. User Experience
- **Graceful Degradation**: System continues với limited functionality
- **Clear Error Messages**: User-friendly error reporting
- **Fallback Actions**: Default behaviors khi AI fails

## Future Enhancements

### 1. Planned Features
- **Calendar Integration**: Tự động tạo events
- **Advanced Filtering**: ML-based email filtering
- **Multi-language Support**: Internationalization
- **Analytics Dashboard**: Detailed metrics và insights

### 2. Scalability
- **Database Migration**: PostgreSQL cho production
- **Queue System**: Redis cho HITL queue
- **Load Balancing**: Multiple worker instances
- **Caching**: Response caching cho performance

## Troubleshooting

### 1. Common Issues
- **Gmail API Quota**: Check API usage limits
- **Gemini API Errors**: Verify API key và quota
- **Database Locks**: Check concurrent access
- **Memory Issues**: Monitor PENDING queue size

### 2. Debug Tools
- **Logs**: Comprehensive logging system
- **Health Check**: `/health` endpoint
- **Integration Tests**: `test_integration.py`
- **Demo Mode**: Send test emails

---

**Made with ❤️ for productivity enthusiasts**
