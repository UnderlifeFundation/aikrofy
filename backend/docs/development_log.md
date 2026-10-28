# Development Log

**Copyright © 2025 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.**

This document tracks the development progress, major changes, and feature implementations of the Aikrofy project. It serves as a historical record of the workflow across different branches.

---

## 🚀 Initial State Report
**Date:** December 12, 2025
**Branch:** `dev`

### Project Status Overview
The Aikrofy Multi-Agent System has established its core foundation. The initial phase focused on setting up the Flask architecture, database models, authentication system, and the primary dashboard UI.

### Completed Components
1.  **Core Framework**: Flask application factory pattern established with Blueprints.
2.  **Database**:
    *   SQLAlchemy models defined (User, Company, Agent, etc.).
    *   Remote MySQL Integration verified.
3.  **Authentication**: JWT-based auth fully functional.
4.  **Frontend**: Dashboard UI implemented.
5.  **RAG System (Integration Complete)**: Pinecone RAG system active.

### Current Workflow Strategy
The project follows a feature-branch workflow:
*   `main`: Stable production code.
*   `dev`: Main development integration branch.
*   `feature/*`: Feature-specific branches.

---

## 🌿 Feature Branch Logs

### Critical Fixes: MySQL Stability & Agent Behavior Refinement
**Branch:** `dev` (Direct commits)
**Date:** January 3-4, 2026
**Status:** ✅ Completed

**Problem Statement:**
After extended conversation sessions (10+ hours), the system experienced "MySQL server has gone away" errors during tool execution. Additionally, the agent exhibited two behavioral issues:
1. Scheduling appointments without user confirmation when preferred time was unavailable.
2. Failing to execute `send_email` when explicitly requested by users post-payment.

**Root Causes Identified:**
1. **MySQL Connection Timeouts**: ORM lazy-loading of `agent.features` after long periods triggered queries on expired DB sessions.
2. **Ambiguous Scheduling Prompt**: Agent interpreted "offer alternatives" as permission to auto-schedule.
3. **Weak Email Prompt**: Agent responded in chat instead of executing `send_email` tool when user requested email delivery.

**Actions Taken:**

**A. MySQL Connection Robustness (Critical)**
*   **Decoupled Tool Loading from ORM** (`services/langgraph_tools.py`, `services/langgraph_agent.py`):
    *   Modified `get_tools_for_agent()` to accept pre-computed `enabled_features` list (strings) instead of querying `agent.features` dynamically.
    *   Extract feature names **before** any rollback operations, eliminating lazy-load vulnerabilities.
    *   Result: ZERO ORM queries during long-running agent operations.
*   **Preventive Rollbacks in Critical Tools**:
    *   Added `db.session.rollback()` at the start of `send_email`, `lookup_customer`, `register_customer`, `paypal_create_order` to handle stale connections.
*   **Fixed Python Import Bug**:
    *   Corrected `datetime` module shadowing in `langgraph_agent.py` that caused `cannot access local variable 'datetime'` errors.

**B. Agent Behavior Improvements**
*   **Scheduling Confirmation Rule** (`services/langgraph_agent.py`):
    *   Added explicit instruction: "**ESPERA LA RESPUESTA DEL USUARIO. NO PROCEDAS HASTA QUE EL USUARIO ELIJA.**"
    *   Agent now **must** wait for user's explicit choice before scheduling when preferred time is unavailable.
*   **Payment Email Flow** (`services/langgraph_agent.py`):
    *   Strengthened prompt with: "**REGLA DE ORO**: Cuando el usuario pide 'envíame por correo', SIEMPRE debes ejecutar `send_email`. NO es opcional."
    *   Agent now reliably executes `send_email` when user requests post-payment summary.

**Technical Details:**
*   **Files Modified**:
    *   `services/langgraph_agent.py`: Import fix, feature extraction logic, prompt refinements.
    *   `services/langgraph_tools.py`: `get_tools_for_agent()` signature update, tool rollbacks.
    *   `services/email_service.py`: Preventive rollback before channel query.
*   **Database Access Pattern**: Tools maintain full DB access for business operations (customer lookup, appointments, transactions). Only configuration loading (agent features) was optimized.

**Verification:**
*   ✅ 10+ hour conversation sessions complete without MySQL errors.
*   ✅ Agent correctly presents scheduling options and waits for user confirmation.
*   ✅ Email delivery works reliably post-payment when user requests it.
*   ✅ All payment, calendar, and RAG integrations function normally.

**Impact:**
This fix ensures long-term system stability for production deployments, particularly for persistent channels (WhatsApp, Telegram) where conversations span multiple days.

---

## 🌿 Feature Branch Logs

### Feature: Pinecone Integration
**Branch:** `feature/integration-pinecone`
**Merged to `dev`:** Dec 12, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Configured `services/rag_service.py` with Pinecone & OpenAI.
*   Resolved `pinecone-client` dependency issues.
*   Verified vector embedding and retrieval.

---

### Feature: Twilio Integration (Multi-Tenant)
**Branch:** `feature/integration-twilio`
**Merged to `dev`:** Dec 12, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Implemented `TwilioService` with BYOK architecture (Company Key > Env Key).
*   Verified WhatsApp, SMS, and Voice connectivity via `test_twilio.py`.
*   Confirmed architecture scalability for SaaS tenants.

---

### Feature: Google Workspace Integration & Architecture Refactor
**Branch:** `feature/integration-google-services`
**Merged to `dev`:** Dec 12, 2025
**Status:** ✅ Completed

**Major Architecture Change:**
*   **Resolved Circular Imports**: Extracted Flask extensions (`db`, `jwt`, `migrate`, `socketio`) into a new `extensions.py` file. Refactored `app.py`, all `models/`, `services/`, and `routes/` to import extensions from this central module. This stabilizes the codebase and prevents `partially initialized module` errors.

**Actions Taken:**
*   **OAuth 2.0 Flow**: Implemented `GoogleService` and `google_auth_bp` to handle "Login with Google".
*   **Database**: Added `google_credentials` (JSON) column to `User` model.
*   **Verification**: Verified OAuth configuration and Token Flow logic via `test_google_auth.py`.

---

### Feature: PayPal Integration (Payments)
**Branch:** `feature/integration-paypal`
**Merged to `dev`:** Dec 12, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Implemented `PayPalService` using `paypalrestsdk.Api` contexts for thread-safe operation.
*   **Multi-Tenancy**: Implemented credential resolution (Company > Env) to allow tenants to receive their own payments.
---

### Feature: RAG Background Processing & Optimization
**Branch:** `feature/async-rag-processing`
**Merged to `dev`:** Dec 13, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Implemented `ThreadPoolExecutor` (3 workers) for non-blocking document uploads.
*   Added support for PDF (pdfminer.six) and DOCX (python-docx) indexing.
*   Connected RAG Service to `AgentService` for context-aware responses per company.
*   Verified MySQL reconnection handling during background tasks.

---

### Feature: BYOK (Bring Your Own Key) & Configuration
**Branch:** N/A (Directly on `dev` via multiple commits)
**Completed:** Dec 13, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Implemented UI in `settings.html` for Twilio (SID/Token) and PayPal (Client ID/Secret) keys.
*   Updated `Company` model to store encrypted API keys.
*   Added support for `gpt-4o-mini` and `gpt-5-nano` in `LLMService`.
*   Enforced `temperature=1.0` requirement for `gpt-5-nano` model.

---

### Feature: Agent Tool Integration & Twilio Validation
**Branch:** `feature/fix-ai-connections`
**Merged to `dev`:** Dec 13, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Connected `routes/chat.py` to `AgentService`, enabling real AI responses in Dashboard Admin Chat.
*   Implemented `send_whatsapp` and `make_call` tools in `AgentService` linked to `TwilioService`.
*   Fixed `IntegrityError` by handling tool-only responses (null content) with status messages.
*   **Verification**:
    *   Validated `send_whatsapp` execution (Status: Queued).
    *   Validated `make_call` execution (Handled Trial Account restriction gracefully).
    *   Confirmed separate configuration for Voice and WhatsApp numbers in Settings.

---

### Feature: LiveKit Voice Agent Integration (Real-Time Voice AI)
**Branch:** `feature/fix-ai-connections`
**Completed:** Dec 13, 2025
**Status:** ✅ Completed

**Major Achievement:**
Full real-time voice AI calling system using LiveKit + OpenAI Realtime API + Twilio SIP Trunking.

**Architecture:**
```
Admin Chat → Flask API (make_call) → LiveKit SIP → Twilio Elastic SIP Trunk → PSTN → User Phone
                                       ↓
                              Voice Agent (voice_agent.py)
                              OpenAI Realtime API (gpt-4o-realtime-preview)
```

**Actions Taken:**
*   **LiveKitService** (`services/livekit_service.py`):
    - Implemented room creation with `RoomServiceClient`.
    - SIP dialing with `SipService.create_sip_participant`.
    - Async bridge via `asyncio.run()` for Flask compatibility.
*   **Voice Agent** (`voice_agent.py`):
    - OpenAI Realtime API (`gpt-4o-realtime-preview`) for low-latency speech-to-speech.
    - BVCTelephony noise cancellation for SIP audio quality.
    - Spanish greeting and conversational persona.
*   **Settings UI** (`settings.html`, `channels.html`, `agents.html`):
    - LiveKit configuration fields (URL, API Key, Secret, Caller ID).
    - Telephony provider switch (Twilio vs LiveKit).
    - [x] Agents: Show/Hide toggles and persistence
    - [x] Smart save logic to prevent masked secrets override.
*   **AgentService** (`services/agent_service.py`):
    - Added `make_call` tool with provider switching logic.
    - Injected user context from conversation for dynamic calling.

**Verification:**
*   ✅ Outbound call initiated from Admin Chat.
*   ✅ LiveKit SIP dispatched to Twilio Elastic SIP Trunk.
*   ✅ Phone rang and connected successfully.
*   ✅ Voice Agent spoke greeting in real-time (OpenAI Realtime API).
*   ✅ Full audio roundtrip verified (user heard AI voice).

**Dependencies Added:**
*   `livekit-agents==1.3.6`
*   `livekit-plugins-openai==1.3.6`
*   `livekit-plugins-silero==1.3.6`
*   `livekit-plugins-noise-cancellation==0.2.5`
*   `livekit-api==1.1.0`

---

### Feature: Platform-Wide Credential UI/UX Fix
**Branch:** `feature/fix-ai-connections`
**Completed:** Dec 13, 2025
**Status:** ✅ Completed

**Actions Taken:**
*   Added Show/Hide (👁️) toggles for all password fields across Settings, Channels, and Agents.
*   Implemented smart save logic (`getSecretValue` helper) to prevent masked `********` from overwriting real secrets.
*   Fixed backend to return actual secret values for display (instead of booleans).
*   Ensured dropdown selections (Telephony Provider, LLM Provider, etc.) persist correctly.

---

### Feature: Dynamic Voice Agent Personalization
**Branch:** `feature/fix-ai-connections`
**Completed:** Dec 13, 2025
**Status:** ✅ Completed

**Major Achievement:**
Voice Agent now dynamically loads personality, voice, tools, and background knowledge (RAG) based on the specific company and agent configuration in the database.

**Features:**
*   **Dynamic Context**: Agent reads room metadata to fetch its specific configuration from the internal API.
*   **Voice Matching**: Automatically maps Agent Gender defined in Company settings to OpenAI Realtime voices (Female → `coral`, Male → `echo`, Neutral → `alloy`).
*   **Tool Integration**: Enabled features (WhatsApp, Email, etc.) are dynamically loaded as function tools for the model.
*   **RAG Awareness**: Company knowledge base context is injected into the agent's system instructions.

**Technical Implementation:**
*   **Internal API**: Created `routes/voice_agent_api.py` (`/api/internal/voice-context/*`) to serve context securely to the local voice agent process.
*   **Architecture**:
    *   `LiveKitService` passes `agent_id` & `company_id` in Room Metadata.
    *   `voice_agent.py` fetches context from Flask API before starting the session.
    *   `voice_tools.py` allows the agent to execute actions (like `send_whatsapp`) by calling back to `AgentService` via the internal API.

**Verification:**
*   ✅ Verified context fetching from API.
*   ✅ Verified voice selection based on gender.
*   ✅ Verified tool loading based on enabled features.

---

### Feature: Configuration UI Persistence & Stabilization
**Branch:** `feature/fix-ai-connections`
**Completed:** Dec 15, 2025
**Status:** ✅ Completed

**Key Improvements:**
*   **Comprehensive Settings Hub**: Refactored `settings.html` to serve as the central source of truth for all integrations.
    *   Added full configuration forms for Email (SMTP/IMAP), Google Service Account, Twilio, and LiveKit.
    *   Implemented robust `loadSettings` logic to pre-fill all domains from the database.
*   **Credential Management**:
    *   **Separation of Concerns**: Split Twilio configuration into distinct "WhatsApp" and "Voice" sections to prevent credential overwrites between services.
    *   **Security UI**: Implemented "Show/Hide" toggles and defensive merge logic to ensure masked secrets (`********`) are never saved back to the database, preserving actual values.
    *   **SendGrid Removal**: Fully deprecated SendGrid in favor of a unified Custom SMTP/IMAP email channel.
*   **UI/UX Fixes**:
    *   Fixed `channels.html` regression where "Connect" buttons were unresponsive due to syntax errors.
    *   Resolved nesting issues in Voice Modal that caused "ghost" phone number fields to appear.
    *   Restored accurate "Connected" status badges across all channels.
*   **Performance**:
    *   **Voice Agent Startup**: Fixed `TimeoutError` in `voice_agent.py` by implementing global caching for the Pinecone client in `RAGService`, reducing context load time from ~9s to <1s.

---

### Feature: Bug Fixes & Integration Improvements
**Branch:** `feature/fix-identified-issues`
**Completed:** Dec 15, 2025
**Status:** ✅ Completed

**Actions Taken:**

*   **Critical Fixes**:
    *   Removed duplicate `return jsonify(response)` statement in `routes/voice_agent_api.py`.
    *   **Security Enhancement**: Added `require_internal_token` decorator to protect internal API endpoints. Token verified via `X-Internal-Token` header against `INTERNAL_API_TOKEN` env variable.
    *   Filtered sensitive API keys from voice agent context response - now only returns `telephony_provider`, not full secrets.
    *   Implemented AgentService processing for SMS webhook (`/webhooks/sms`) - now provides AI responses instead of static text.
    *   Implemented AgentService processing for Voice webhook (`/webhooks/voice/process`) - now provides AI responses during calls.

*   **Tool Fixes & Improvements**:
    *   Fixed `send_whatsapp` tool schema - was incorrectly describing email parameters (subject, body) instead of WhatsApp (to, message).
    *   Enhanced `schedule_meeting` tool: Now integrates with `GoogleCalendarIntegration` when service account is configured. Falls back to mock with informative note.
    *   Enhanced `check_inventory` tool: Now integrates with `GoogleSheetsIntegration` when service account and `inventory_spreadsheet_id` are configured. Falls back to mock with informative note.
    *   Enhanced `create_payment_link` tool: Now integrates with `PayPalService`. Falls back to mock link on error.

*   **Codebase Cleanup**:
    *   Removed duplicate `python-docx` entry from `requirements.txt`.
    *   Added `INTERNAL_API_TOKEN` to `.env.example` with documentation.
    *   Updated `voice_agent.py` and `voice_tools.py` to include `X-Internal-Token` header in API calls.

**Verification:**
*   ✅ App imports and starts successfully.
*   ✅ All modified files have valid Python syntax.

---

### Feature: Completion & Polish (MVP 100%)
**Branch:** `feature/completion-polish`
**Completed:** Dec 15, 2025
**Status:** ✅ Completed

**Actions Taken:**

*   **Team Management System (New)**:
    *   **Backend**: Created `routes/employees.py` with full CRUD endpoints for `Employee` model.
    *   **Frontend**: Updated `employees.html` to replace placeholder logic with real API integration (Grid view, Add/Delete actions).
    *   **Config**: Registered new blueprint in `app.py`.

*   **Security Hardening**:
    *   **Voice Tools**: Updated `check_inventory` and `create_payment_link` in `voice_tools.py` to use `X-Internal-Token` header for authentication, matching the new security standard.

**Verification:**
*   ✅ `python -c "from app import create_app..."` passed successfully.
*   ✅ Employee routes are registered and active.

---

### Feature: Voice Agent Purpose Persistence Fix
**Branch:** `feature/docs`
**Completed:** Dec 15, 2025
**Status:** ✅ Completed

**Problem:**
When initiating outbound calls from the Admin Chat with a specific purpose (e.g., "Llama a X para preguntar sobre disponibilidad"), the voice agent would:
1. Say a generic greeting ("¿Hola? ¿Buenas tardes?")
2. State the purpose once
3. **But then ask "¿En qué puedo ayudarte?"** when the user responded, losing the purpose entirely.

**Root Cause:**
The `generate_reply(instructions=...)` method in LiveKit Agents only applies instructions for that **single response**. The agent's core instructions were never updated, so when the user responded, the agent reverted to its filler instructions.

**Solution:**
Added `agent.update_instructions(final_instructions)` call after loading context to **persist** the purpose into the agent's core instructions for the entire call duration.

**Actions Taken:**
*   **Modified** `voice_agent.py`:
    *   Added `agent.update_instructions(final_instructions)` after building the final instructions with purpose.
    *   Added debug logging to track instruction updates.

**Technical Reference:**
*   LiveKit GitHub Issue #4242: `update_instructions()` behavior documentation
*   LiveKit Docs: `generate_reply()` instructions are one-time, not persistent

**Verification:**
*   ✅ Voice agent now remembers the call purpose throughout the entire conversation.
*   ✅ Agent no longer asks generic "How can I help?" after user responds.

### Feature: Call Termination & Real-Time Reporting Fixes
**Branch:** `feature/docs`
**Completed:** Dec 16, 2025
**Status:** ✅ Completed

**Problems Addressed:**
1.  **Phone Line Left Open:** `session.aclose()` terminated the AI agent but left the SIP phone call active.
2.  **Raw Transcript Report:** The call report was just a raw transcript, hard to read for admins.
3.  **No Real-Time Update:** Admin chat required manual page reload to see the call report.

**Solutions Implemented:**
1.  **SIP Hangup:** Rewrote `end_call` tool to use `RoomServiceClient.remove_participant()`, which forces the SIP disconnect.
2.  **LLM Summary:** Implemented GPT-4o-mini to generate a concise, professional executive summary of the call before reporting.
3.  **Real-Time WebSocket:** 
    *   Backend: Added `socketio.emit` broadcast on call completion.
    *   Frontend: Added `socket.io.js` library and event listeners in `chat.html`.

**Modified Files:**
*   `voice_agent.py`: New report logic with LLM summary.
*   `voice_tools.py`: New `end_call` implementation using LiveKit API.
*   `routes/voice_agent_api.py`: Added WebSocket broadcast.
*   `templates/base.html`: Added Socket.IO CDN.
*   `templates/dashboard/chat.html`: Added real-time listeners.


### Feature Branch: Project Completion (HubSpot, Sentiment, Escalation)
**Date:** December 23, 2025
**Branch:** `feature/project-completion`

**1. Branch Cleanup & Setup**
*   Deleted obsolete branches: `feature/completion-polish`, `feature/fix-identified-issues`.
*   Merged `dev` into `main` to synchronize production branch.
*   Fixed critical bugs:
    *   Removed duplicate `db.session.commit()` in `webhooks.py`.
    *   Cleaned up unused imports in `paypal_service.py`.
    *   Replaced hardcoded `localhost:5001` with `PYMAI_API_URL` env var in voice agent files.
    *   Removed fictional `gpt-5-nano` model reference.

**2. HubSpot CRM Integration**
*   Created `integrations/hubspot.py`: Full implementation of HubSpot API.
*   **[NEW] implemented OAuth 2.0 Flow**:
    *   Added `routes/hubspot_auth.py` for `/authorize` and `/callback`.
    *   Updated `services/hubspot_service.py` to handle Access Tokens.
    *   Updated `settings.html` to replace API Key input with "Connect HubSpot" button.
*   Added CRM tools to `AgentService`: `sync_to_crm`, `lookup_customer`.
*   Added `hubspot-api-client` to requirements.

**3. Sentiment Analysis & Auto-Escalation**
*   Created `services/sentiment_service.py`: Analyzes messages using GPT-4o-mini to detect sentiment (-1 to 1) and emotions.
*   Created `services/escalation_service.py`: Monitors conversations for negative sentiment or keywords ("speak to human") and triggers notifications.
*   Integrated into `AgentService.process_message`: checks run automatically if agent has capabilities enabled.
*   Implemented `transfer_call` tool to utilize escalation logic.
*   Implemented `create_task` tool to send email notifications.

**4. Configuration**
*   Updated `.env.example` with `HUBSPOT_CLIENT_ID`, `HUBSPOT_CLIENT_SECRET`.
*   Updated `requirements.txt` with `livekit-plugins-noise-cancellation` and `hubspot-api-client`.

**5. Google OAuth & Channels UI**
*   **Google Integration**:
    *   Updated `routes/google_auth.py` to support listing Calendars/Sheets and saving selection.
    *   Updated `services/google_service.py` with `list_calendars`, `list_sheets` and Company-level credential support.
    *   Promoted connected user credentials to Company settings to allow Agent access.
*   **Channels UI**:
    *   Added HubSpot CRM card to `channels.html`.
    *   Updated Google Calendar/Sheets cards to use OAuth flow with resource selection modal.
    *   Unified integration management in `channels.html`.

**Status:** Ready for testing and merge to dev.

**6. Meta WhatsApp Integration (Official Cloud API)**
*   **Provider Selection**:
    *   Updated `channels.html` and `agents.html` to allow choosing between Twilio and Meta.
    *   Updated `routes/channels.py` to handle Meta credentials logic.
*   **Webhook Implementation**:
    *   Implemented `/webhooks/meta` in `routes/webhooks.py`.
    *   Added GET Logic for Meta Verification Challenge.
    *   Added POST Logic for processing incoming messages (JSON).
    *   Created `send_meta_message` helper for Graph API replies.
*   **Outcome**: System now fully supports Official WhatsApp Cloud API integration.

**7. UI/UX & Dashboard Enhancements**
*   **Settings Page (`settings.html`)**:
    *   Standardized **Google Services** (Calendar/Sheets) to use OAuth Card design (same as Channels).
    *   Standardized **HubSpot CRM** to use Card design with Portal ID display.
*   **Dashboard (`dashboard/index.html`)**:
    *   Added real-time status rows for **Agents** (Active/Inactive).
    *   Added real-time status rows for **Integrations** (Google, HubSpot).
*   **Employees Config (`employees.html`)**:
    *   Implemented **Edit functionality** for existing team members (previously only Delete).

**8. Conversational Payment System (PayPal + Invoicing)**
*   **Payment Flow**:
    *   Agent uses `create_payment_link` tool to generate PayPal links via `PayPalService`.
    *   Implemented `routes/payments.py` to handle Success/Cancel callbacks.
    *   Fixed `localhost` hardcoding by introducing `API_BASE_URL` in config.
    *   Added context awareness (Company ID) to callback URLs to support multi-tenancy.
*   **Automatic Invoicing**:
    *   Created `services/pdf_service.py` to generate PDF receipts/invoices using ReportLab.
    *   Updated `services/email_service.py` to support PDF attachments via both SMTP and SendGrid.
    *   **Workflow**: Payment Success -> Generate Receipt -> Email Receipt to Customer -> Show "Success" Page.

**9. Extended Channels (Telegram & Web Chat)**
*   **Telegram Integration**:
    *   Added `TELEGRAM` channel type.
    *   Implemented Bot connection flow (Token verification).
    *   Setup automated webhook registration (`routes/channels.py`) pointing to `/webhooks/telegram/<id>`.
    *   Implemented `routes/webhooks.py` handler to process Telegram messages and auto-reply via Agent.
*   **Web Chat Widget**:
    *   Created standalone embeddable widget script: `static/js/widget.js`.
    *   Added Web Chat card to `channels.html` with "Connect" workflow to generate Widgets.
    *   Added "Install Code" modal to provide the user with the HTML snippet.

**10. Refinement & Multi-Tenancy Support (Dec 24, 2025)**
*   **Agent Configuration**:
    *   Updated `DEFAULT_FEATURES` to include Telegram and Web Chat.
    *   Implemented feature backfill logic in `routes/agents.py` to auto-update existing agents.
*   **Web Chat Backend**:
    *   Implemented `POST /webhooks/webchat/message` to handle widget communication.
    *   Added logic to route messages to the correct Company using `widget_id`.
    *   Implemented persistent user sessions in `widget.js` (`op_widget_uid`).

**11. Verification & Bug Fixes (Dec 24, 2025)**
*   **System Stability**:
    *   Fixed `AttributeError` in Channel serialization that caused 500 Errors when loading Channels/Agent Config.
    *   Verified database persistence for new channels: Telegram tokens and WebChat Widget IDs are correctly saved.
*   **Web Chat Widget**:
    *   Enhanced `widget.js` script detection to be more robust for async/deferred loading.
    *   Fixed Z-Index issues to ensure the chat button is visible above other page elements.
*   **Telegram Connection**:
    *   Confirmed connection flow works even if local Webhook fails (due to lack of HTTPS), allowing credentials to be saved for production.

**12. PayPal Agentic Payments (Dec 24, 2025)**
*   **New Service**: Created `services/paypal_toolkit.py` wrapper for the official `paypal-agent-toolkit`.
*   **New Tools Added**:
    *   `paypal_create_order`: Create a PayPal order for in-conversation payment
    *   `paypal_get_order`: Check order status
    *   `paypal_capture_order`: Complete payment (with automatic PDF receipt and email)
    *   **Backward Compatible**: Original `create_payment_link` tool remains available as an alternative.
    *   **Dependencies**: Added `paypal-agent-toolkit>=1.1.0` to `requirements.txt`.
    *   **Fixes**:
        *   Resolved `ImportError` by fixing module path (`.api` instead of `.paypal_api`).
        *   Fixed `AttributeError` by using standalone handler functions instead of client methods.
        *   Fixed `ValidationError` by constructing correct Pydantic payload structure matching `CreateOrderParameters`.

---

### Feature: LangGraph Integration (Dec 25, 2025)

*   **Objective**: Replace manual conversation history management with LangGraph for better memory persistence and reactive multi-agent workflows.
*   **New Files Created**:
    *   `services/langgraph_state.py` - State definitions (AgentState, ToolContext)
    *   `services/langgraph_tools.py` - 11 tools wrapped as @tool (RAG, PayPal, Email, Twilio, Calendar, HubSpot)
    *   `services/langgraph_agent.py` - Main StateGraph service with memory checkpointer
*   **Modified Files**:
    *   `services/agent_service.py` - Added LangGraph routing (default ON)
    *   `routes/webhooks.py` - Added channel parameter to all 6 `process_message` calls
    *   `routes/chat.py` - Added channel parameter to admin chat
    *   `requirements.txt` - Added `langgraph>=1.0.0`
*   **Architecture**:
    *   StateGraph with agent and tools nodes
    *   MemorySaver checkpointer for conversation persistence
    *   Fallback to legacy AgentService if LangGraph fails

### Feature: LangGraph Refinement & Payment Flow Fixes (Dec 28, 2025)

*   **Payment Flow Optimization**:
    *   **Prompt Engineering**: Implemented "Data Freshness Rule" (Regla de Frescura) to prevent the agent from using historical/stale payment amounts (e.g. confusing $100 with a past $50 transaction).
    *   **Verification Loop**: Softened PASO 2 logic to avoid infinite loops if the user has already confirmed their identity.
    *   **Clickable Links**: Enhanced `paypal_create_order` tool to return Markdown-formatted links (`[👉 Click aquí]`) for better UX in WebChat.
    *   **Widget Rendering**: Updated `widget.js` to automatically parse and render Markdown links as clickable anchors.

*   **System Stability & Database**:
    *   **MySQL Retry Logic**: Implemented robust `OperationalError` handling in `routes/webhooks.py`. The system now detects "MySQL server has gone away", performs a rollback, removes the dead session, and retries the save operation with a fresh connection.
    *   **Tool Reliability**: Added `db.session.rollback()` to `lookup_customer` and `register_customer` tools to prevent transaction blocks on error.
    *   **Bug Fix**: Fixed `DetachedInstanceError` in retry logic by capturing `conversation.id` before session usage.

*   **Customer Management**:
    *   **Model Update**: Added `@property full_name` to `Customer` model for easier template rendering.
    *   **Explicit Registration**: Added `register_customer` step in the agent prompt to ensure ID numbers are saved immediately.

*   **Status**: ✅ Tested & Verified in WebChat and Telegram.

### Feature: Robust Multi-Flow Agent & Universal Tools (Jan 03, 2026)

**Objective:**
Eliminate context confusion between Payment and Scheduling flows, fix hallucinations in RAG, and decouple tools for universal availability.

**1. Flow Context System (Anti-Hallucination/Anti-Confusion)**
*   **Prompt Engineering:** Implemented strict "Flow Context Rules" in `services/langgraph_agent.py`.
*   **Logic:**
    *   **Detection:** Agent detects keywords (`pagar`, `agendar`) and locks into `FLUJO_PAGO` or `FLUJO_AGENDA`.
    *   **Locking:** Once in a flow, cross-flow interruptions are blocked until completion.
    *   **Independence:** Instructions for disabled features are completely removed from the system prompt.

**2. The "Closing Phase" Implementation**
*   **Problem:** Agent would re-execute tasks (re-book/re-charge) when user said "Ok" to a post-transaction email offer.
*   **Solution:** Defined explicit **FASE DE CIERRE (POST-TRANSACCIÓN)** for both protocols.
    *   Once tool execution (Book/Link) succeeds, the Flow is marked as **TERMINATED**.
    *   Subsequent "Yes/Ok" confirmations are strictly routed to `send_email` or `goodbye`.
    *   **Result:** Robust 3-act structure (Collect -> Execute -> Close).

**3. Universal Tool Access & Feature Decoupling**
*   **Modified** `services/langgraph_tools.py`:
    *   **Email (`send_email`)**: Now available if `send_email` feature is ON, regardless of other flows. Usable for Payment, Agenda, or Info.
    *   **Customer Tools (`lookup`/`register`)**: Automatically injected if ANY enabled feature (Payment, Calendar, Email) requires identity.
    *   **RAG (`consult_knowledge_base`)**: Bug fix: replaced non-existent `search()` method call with correct `query()`. Now strictly prioritized for company info queries.

**4. Calendar & Timezone Optimizations**
*   **Smart Suggestions**: `check_availability` now returns slots surrounding the preferred time (2 before, 2 after) instead of just the first 5.
*   **Timezone Intelligence**: Injected Company Location (`city`, `country`) into prompt. Agent now converts User Time <-> Company Time explicitly.
*   **Integration**: Fixed `sendUpdates='all'` in Google Calendar API to ensure email invites are sent to attendees.
*   **Fix**: Added missing `pytz` import to tools.

**5. UX Enhancements**
*   **Email Formatting**: Implemented `markdown_to_html` converter. Emails sent by agent now render with professional HTML (bullets, bold, headers).
*   **Continuity Rule**: Added explicit instruction allowing the agent to "reset" context after a flow ends, enabling users to chain requests (e.g., Book -> Pay -> Ask Info) in one session.

**Status:** ✅ Tested & Verified context switching, locking, and email delivery.

### Feature: HubSpot CRM Process Integration (Jan 08, 2026)

**Branch:** `feature/crm-process`

**Objective:**
Implement comprehensive, real-time CRM synchronization with HubSpot, ensuring contact properties, lifecycle stages, and lead statuses are automatically updated based on user interactions.

**1. HubSpot Token Auto-Refresh**
*   Implemented automatic token refresh when `access_token` expires.
*   Added `_refresh_token()` method in `HubSpotService`.
*   Tokens are persisted to database on refresh.

**2. Contact Owner Assignment**
*   Added `crm.objects.owners.read` scope to OAuth flow.
*   Implemented `_get_owner_id_by_email()` to match company email to HubSpot owners.
*   New contacts are automatically assigned to the matching owner.

**3. Lifecycle Stage Automation**
*   **Lead** (Default): Set on contact creation.
*   **Opportunity**: Set when appointment is scheduled (`mark_as_scheduled`).
*   **Customer**: Set when transaction is completed (`update_lifecycle_to_customer`).

**4. Lead Status (`hs_lead_status`) Sync**
*   **NEW**: Default for new contacts.
*   **IN_PROGRESS**: Set on conversation sync.
*   **OPEN_DEAL**: Set on appointment scheduling.
*   **CONNECTED**: Set on payment completion.

**5. Contact Properties Sync**
*   **Phone Number**: Now synced via `create_or_update_contact`.
*   **Buying Role** (`hs_buying_role`): Added to `Customer` model with default `'End User'`.
    *   Auto-normalized to HubSpot internal values (e.g., `DECISION_MAKER`, `END_USER`).

**6. Real-Time Sync Triggers**
*   **Payment Completion** (`routes/payments.py`): Added HubSpot lifecycle update on PayPal capture success.
*   **Appointment Creation** (`schedule_appointment` tool): Already implemented.
*   **Customer Registration** (`register_customer` tool): Updated to sync immediately to HubSpot.
    *   Only sets `lead_status='NEW'` on fresh creation (no regression on updates).

**7. Backfill Script**
*   Created `scripts/sync_existing_customers.py` for bulk sync of existing customers.
*   Logic:
    *   Customers with completed transactions → `customer` / `CONNECTED`.
    *   Customers with appointments → `opportunity` / `OPEN_DEAL`.
    *   Customers with conversations → `lead` / `IN_PROGRESS`.
    *   Default → `lead` / `NEW`.

**Files Modified:**
*   `services/hubspot_service.py`: Token refresh, owner lookup, lifecycle methods.
*   `services/langgraph_tools.py`: `register_customer` HubSpot sync logic.
*   `routes/hubspot_auth.py`: Added `crm.objects.owners.read` scope.
*   `routes/payments.py`: Added real-time HubSpot sync on payment success.
*   `integrations/hubspot.py`: Added `hs_lead_status` to default search properties.
*   `models/customer.py`: Added `buying_role` field.

**Verification:**
*   ✅ Owner assignment verified (`86906918` for `jonnathan.ypg@gmail.com`).
*   ✅ Lifecycle stage transitions verified.
*   ✅ Lead status transitions verified.
*   ✅ Buying role sync verified (`END_USER`).
*   ✅ Backfill script executed successfully for 2 customers.

**Scripts Cleanup:**
*   Deleted 10 verification/debug scripts created during development.
*   Retained 6 utility scripts: `sync_existing_customers.py`, `backfill_emails.py`, `link_and_resolve_orphans.py`, `fix_contact_info.py`, `create_email_table.py`, `resolve_old_conversations.py`.

**Status:** ✅ Complete. Ready for merge to `dev`.

