# Aikrofy - Multi-Agent System Implementation Plan

> A comprehensive, easy-to-use multi-agent platform with configurable channels, RAG-based memory, and modern admin dashboard.

---

## User Review Required

> [!IMPORTANT]
> **API Keys & External Services Required**
> 
> This implementation requires credentials for:
> - MySQL database (local or cloud)
> - Pinecone for vector memory/RAG
> - LLM Providers (OpenAI, Anthropic, Google, etc.)
> - Communication Channels (Twilio for WhatsApp/Calls, SendGrid/SMTP for Email, Google Calendar API)

> [!WARNING]
> **WhatsApp Business API Considerations**
> 
> WhatsApp integration requires either Twilio WhatsApp API or Meta Business API approval. For development, we can use Twilio Sandbox or mock the integration.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  Modern Web Interface | Analytics Dashboard | Admin Chat        │
│  Agent Configuration Panel | Checkbox-based Feature Toggles    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND                               │
│  REST API | Authentication | Agent Orchestrator                 │
│  Channel Manager | RAG Engine                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  LLM Layer   │     │   Channels   │     │   Storage    │
│  OpenAI      │     │  WhatsApp    │     │  MySQL DB    │
│  Anthropic   │     │  Voice       │     │  Pinecone    │
│  Google AI   │     │  Email/SMS   │     │  File Store  │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## Proposed Changes

### 1. Project Structure

#### [NEW] Project Root Files

```
Aikrofy/
├── app.py                      # Flask application entry point
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── README.md                  # Project documentation
└── venv/                      # Virtual environment
```

---

### 2. Backend Structure

#### [NEW] `models/`

Database models using SQLAlchemy:

| File | Purpose |
|------|---------|
| `__init__.py` | Models package initialization |
| `user.py` | Admin user accounts |
| `company.py` | Company/tenant management |
| `agent.py` | Agent configurations |
| `channel.py` | Channel settings & credentials |
| `conversation.py` | Conversation history |
| `document.py` | RAG documents metadata |

#### [NEW] `services/`

Business logic layer:

| File | Purpose |
|------|---------|
| `llm_service.py` | Multi-provider LLM handling |
| `rag_service.py` | Pinecone RAG operations |
| `agent_service.py` | Agent orchestration logic |

#### [NEW] `integrations/`

External service integrations:

| File | Purpose |
|------|---------|
| `google_sheets.py` | Google Sheets inventory API |
| `paypal.py` | PayPal payment processing |
| `calendar.py` | Google Calendar API |

#### [NEW] `routes/`

API endpoints organized by domain:

| File | Purpose |
|------|---------|
| `auth.py` | Login, register, token refresh |
| `companies.py` | Company CRUD operations |
| `agents.py` | Agent configuration endpoints |
| `channels.py` | Channel setup & webhooks |
| `rag.py` | Document upload & search |
| `analytics.py` | Dashboard data endpoints |
| `chat.py` | Admin chat interactions |
| `webhooks.py` | Twilio webhook handlers |

---

### 3. Database Schema

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   USERS     │       │  COMPANIES  │       │   AGENTS    │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──────▶│ id (PK)     │◀──────│ id (PK)     │
│ email (UK)  │       │ name        │       │ company_id  │
│ password    │       │ agent_name  │       │ name        │
│ role        │       │ agent_gender│       │ tone        │
│ company_id  │       │ personality │       │ system_prompt│
│ created_at  │       │ llm_config  │       │ features    │
└─────────────┘       │ api_keys    │       │ is_active   │
                      └─────────────┘       └─────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  CHANNELS   │       │  EMPLOYEES  │       │  DOCUMENTS  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │       │ id (PK)     │
│ company_id  │       │ company_id  │       │ company_id  │
│ type        │       │ name        │       │ filename    │
│ credentials │       │ email       │       │ file_type   │
│ status      │       │ phone       │       │ pinecone_ids│
│ connected_at│       │ whatsapp    │       │ status      │
└─────────────┘       │ role        │       │ uploaded_at │
                      └─────────────┘       └─────────────┘
                             
┌─────────────────────────────────────────┐
│            CONVERSATIONS                 │
├─────────────────────────────────────────┤
│ id (PK) | company_id | channel | status │
│ contact_name | contact_phone | tags     │
│ sentiment_score | lead_score            │
└─────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────┐
│               MESSAGES                   │
├─────────────────────────────────────────┤
│ id (PK) | conversation_id | role        │
│ content | channel | tool_calls          │
│ tokens_used | created_at                │
└─────────────────────────────────────────┘
```

---

### 4. Frontend Structure

#### [NEW] `static/`

```
static/
├── css/
│   └── main.css              # Core styles & design system
└── assets/
    └── icons/                # SVG icons (using Lucide)
```

#### [NEW] `templates/`

Jinja2 templates:

```
templates/
├── base.html                 # Base layout with navigation
├── auth/
│   ├── login.html
│   └── register.html
├── dashboard/
│   ├── index.html           # Main dashboard
│   ├── analytics.html       # Charts & metrics
│   └── chat.html            # Admin chat interface
└── config/
    ├── agents.html          # Agent configuration
    ├── channels.html        # Channel setup
    ├── documents.html       # RAG file management
    ├── employees.html       # Employee management
    └── settings.html        # Company & LLM config
```

---

### 5. Core Features Implementation

#### Agent Configuration Checkbox System

```
┌─────────────────────────────────────────────────────┐
│  🤖 Agent Capabilities                              │
├─────────────────────────────────────────────────────┤
│  📞 Communication Channels                          │
│  ├── □ WhatsApp     □ Voice Calls                   │
│  ├── □ Email        □ SMS                           │
│  └── (Enabling opens credential setup modal)        │
├─────────────────────────────────────────────────────┤
│  📅 Integrations                                    │
│  ├── □ Calendar (Schedule meetings)                 │
│  ├── □ Google Sheets (Inventory)                    │
│  └── □ PayPal (Payments)                            │
├─────────────────────────────────────────────────────┤
│  🎭 Agent Tone & Personality                        │
│  ├── ○ Professional  ○ Friendly  ○ Formal           │
│  ├── ○ Receptionist  ○ Sales     ○ Support          │
│  └── (Pre-qualified call scheduling)                │
├─────────────────────────────────────────────────────┤
│  🧠 AI Features                                     │
│  ├── □ RAG Memory (Use uploaded documents)          │
│  ├── □ Conversation History                         │
│  └── □ Sentiment Analysis                           │
└─────────────────────────────────────────────────────┘
```

#### LLM Provider Configuration

| Category | Providers |
|----------|-----------|
| Text/Chat | OpenAI GPT-4, Claude 3, Gemini Pro |
| Voice | OpenAI Whisper, ElevenLabs |
| Embeddings | OpenAI Ada-002 |

---

### 6. API Endpoints

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/auth/me` | Get current user |

#### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents` | List agents |
| POST | `/api/agents` | Create agent |
| PUT | `/api/agents/:id` | Update agent |
| GET | `/api/agents/:id/features` | Get features |
| PUT | `/api/agents/:id/features/:fid` | Toggle feature |

#### Channels

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/channels` | List channels |
| POST | `/api/channels/connect` | Initiate connection |
| POST | `/api/webhooks/whatsapp` | WhatsApp incoming |
| POST | `/api/webhooks/voice` | Voice call handler |

#### RAG/Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rag/upload` | Upload document |
| GET | `/api/rag/documents` | List documents |
| DELETE | `/api/rag/documents/:id` | Delete document |
| POST | `/api/rag/query` | Search memory |

---

### 7. Key Dependencies

```txt
# Core
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-JWT-Extended==4.6.0
Flask-CORS==4.0.0
Flask-SocketIO==5.3.6
python-dotenv==1.0.0
gunicorn==21.2.0

# Database
PyMySQL==1.1.0

# Vector DB & AI
pinecone-client==3.0.0
openai==1.6.1
anthropic==0.8.1
google-generativeai==0.3.2

# Communication
twilio==8.10.0
sendgrid==6.11.0
google-api-python-client==2.111.0
paypalrestsdk==1.13.1
gspread==5.12.0

# Document Processing
pdfplumber==0.10.3
python-docx==1.1.0
```

---

### Design System

#### Color Palette

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--primary` | `#6366f1` | `#818cf8` | Primary actions |
| `--secondary` | `#f59e0b` | `#fbbf24` | Secondary actions |
| `--success` | `#10b981` | `#34d399` | Success states |
| `--danger` | `#ef4444` | `#f87171` | Destructive actions |
| `--surface` | `#ffffff` | `#1e1e2e` | Card backgrounds |
| `--background` | `#f8fafc` | `#0f0f17` | Page background |

#### UI Features

- 🌓 Dark/Light mode toggle
- 📱 Fully responsive (mobile-first)
- ✨ Glassmorphism effects for cards
- 🎯 Micro-animations on interactions
- 📊 Chart.js for analytics visualization

---

## Verification Plan

### Automated Tests

```bash
# Run unit tests
python -m pytest tests/ -v

# Test API endpoints
python -m pytest tests/test_api.py -v

# Test database models
python -m pytest tests/test_models.py -v
```

### Manual Verification

1. **Authentication Flow**
   - Register new company/user
   - Login and verify JWT tokens
   - Test protected routes

2. **Agent Configuration**
   - Toggle checkboxes and verify state persistence
   - Test channel connection modals
   - Verify personality/tone affects responses

3. **Channel Integration**
   - Connect WhatsApp via credentials
   - Send/receive test messages
   - Test calendar integration

4. **RAG System**
   - Upload PDF/DOCX files
   - Query uploaded documents
   - Verify context injection in responses

5. **Dashboard**
   - Verify analytics charts render correctly
   - Test admin chat functionality
   - Check responsive design on mobile

---

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Project Setup & DB | ✅ Complete | Flask, SQLAlchemy, migrations |
| 2. Auth & Company CRUD | ✅ Complete | JWT, user registration |
| 3. Agent Config UI | ✅ Complete | Checkbox system, features |
| 4. Channel Framework | ✅ Complete | Twilio webhook structure |
| 5. RAG Integration | ✅ Complete | Pinecone service, upload API |
| 6. Dashboard & Analytics | ✅ Complete | Charts, funnel, stats |
| 7. Communication Channels | ✅ Complete | WhatsApp, Voice, SMS handlers |
| 8. Frontend Templates | ✅ Complete | All pages implemented |

---

## Questions Addressed

| Question | Answer |
|----------|--------|
| Database preference | SQLite for dev, MySQL for production |
| Primary LLM | OpenAI GPT-4 (configurable) |
| WhatsApp approach | Twilio integration (optional) |
| Hosting plans | Local development ready |
