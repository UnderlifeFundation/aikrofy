# GEMINI.md — Aikrofy AI Development Context & Guidelines (V4.0 DEFINITIVO)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.**
**Repo:** `/root/aikrofy` — rama `dev` — dominio `aikrofy.com` — copiloto **Krof**
**Fecha de consolidación:** 26-sep-2026 (auditoría real de producción, no aspiracional)
**Documentos hermanos:** `AGENTS.md` (guía operativa de agentes) · `ESTRUCTURA_PROYECTO.md` (mapa de archivos) · `COMPENDIO_MAESTRO_AIKROFY.md` (dossier técnico completo) · `README.md` (landing)

> Este archivo es la **fuente única de verdad para desarrollo con IA**. Todo agente (Gemini, Muse, GPT, Krof) DEBE adherirse a él. Las cifras aquí reflejan **código real auditado el 26-sep-2026** (PM2 online, conteos por `grep`/`rg`), no documentos antiguos. Cuando un `.md` legacy contradiga este archivo, **este archivo gana**.

---

## 1. Core Vision (qué es Aikrofy)

**Aikrofy** es un **Agentic OS B2B**: junta directiva virtual (C-Suite de 7 Chiefs + copiloto **Krof**) y fuerza laboral autónoma 360° para PyMEs y corporaciones (planes `pyme`/`enterprise` servidos en `frontend/` :3010), orquestada con **LangGraph** (`backend/services/langgraph_agent.py`, 1087 lín., grafo real de 2 nodos `agent ⇄ tools` + `should_continue`), desacoplada de prompts estáticos vía **habilidades dinámicas `CompanySkill`** (MySQL + `uploads/skills/company_<id>/<skill_name>/SKILL.md`).

- **Orquestación:** LangGraph `StateGraph` + `MemorySaver` **in-memory (volátil, no persistente)** + `llm.bind_tools` (`gpt-4o-mini` / `gpt-5-nano`, temp 0.7). Fases del nodo `agent`: Gatekeeper lead-capture → GuidedResponse match → SkillService prompt assembly → LLM.
- **Inteligencia híbrida:** RAG multi-namespace Pinecone + multi-LLM (OpenAI, Anthropic, Google, Groq, OpenRouter) + sentiment + ML scoring pipeline (`LocalPredictiveScoringEngine`).
- **Aceleración:** capa de **8 estructuras de datos** (`auth_cache <0.1ms`, heap leads, trie CRM 3ms, NumPy typed arrays 2ms/60FPS, sliding window linked-list, colas Redis 6380, stack delegación, grafos LangGraph+HNSW).
- **Objetivo:** automatizar agenda, ventas, soporte, operaciones, marketing y pagos omnicanal (WhatsApp Baileys :3011, webchat, voz LiveKit/Twilio, REST v1, MCP) con fricción → 0.

---

## 2. Stack real auditado (26-sep-2026)

### 2.1 Backend — `backend/` — FastAPI :5010 + Celery worker

| Capa | Real (verificado) |
|---|---|
| API | `fastapi==0.115.6`, `uvicorn==0.34.0`, `python-socketio==5.16.1`, `sse-starlette==2.4.1`. Título interno `PymAI Unified Gateway v2.2.0` (`fastapi_app.py:33`, renombrar pendiente) |
| Compat Flask | `app.py` es `FlaskMock` (27 lín., Flask eliminado). `routing.py` (484 lín.) shim `APIRouter.route()` + `FlaskRequestMock` + JWT + `db_session` cleanup |
| ORM/DB | `SQLAlchemy==2.0.48`, `PyMySQL==1.1.2`, pool `size 5/overflow 5/recycle 120/pre_ping` + `_resilient_remove()` anti "gone away". **57 tablas / 41 ficheros** en `models/` (los docs viejos dicen 34 — obsoleto) |
| IA | `langchain==1.2.10`, `langchain-core==1.2.17`, `langchain-openai==1.1.10`, `langgraph==1.0.10`, `openai==2.26.0`, `anthropic==0.84.0`, `google-generativeai==0.8.6`, `tiktoken==0.12.0`, `mcp==1.28.1` |
| Voz/Realtime | `livekit-api==1.1.0`, `livekit-agents==1.5.1`, `edge-tts==7.2.8`, `livekit-plugins-noise-cancellation==0.2.5` |
| Cola/Vector | `celery==5.6.2`, `redis==6.4.0`, `pinecone==8.1.0` (índice `aikrofy-rag`; hay triple nombre legacy `pymai-rag`/`onepunch-rag` — ver §6) |
| Integraciones | `hubspot-api-client==12.0.0`, `google-api-python-client==2.192.0`, `paypal-agent-toolkit`, `twilio>=8.0.0` |
| Rutas | **45 ficheros** en `routes/` (43 + `v1/agents.py`, `v1/knowledge.py`), **~335 endpoints** (325 legacy+v1 por `rg @*.route(` + ~10 nativos `/health`, `/api/v2/test`, webhooks async). Top: `landing_pages 24`, `channels 17`, `rag 16`, `companies 15`, `admin 15` |
| Servicios | **96 ficheros** (`ls backend/services/*.py` = 57 top-level + subpaquetes = 96). Núcleo: `LangGraphAgentService`, `AgentService`, `KrofAgentService`, `SkillService`, `GraphCompilerService`, `DynamicToolsService`, `MCPService`, `RAGService`, `LLMService`, `CacheService`, `AuthCacheService`, `TokenCreditService`, `LeadScoringService`, `LeadPriorityHeapService`, `CRMSearchTrieService`, `AnalyticsVectorService`, `AutonomousConsciousnessService`, `TrustGuardrailService`, `BrainEventsService`, `HandoverService`, `VoiceService`, `LiveKitService`, `MessagingService`, `WhatsAppBaileysService`, `MetaWhatsAppService`, `TwilioService`, `EmailService`, `GoogleService`, `HubSpotSyncService`, `DLocalGoService`, `PaddleService`, `PayPalService` + `crm/` 9 + `erp/` 5 + `drivers/` 6 + `ecommerce/` 7 + `payment_gateways/adapters/` 8 |
| Celery | `tasks.py` (1038 lín.) **12 tasks** + **4 beats**: `generate_pdf_report`, `index_document_rag`, `process_webhook_message` (principal), `reset_monthly_credits` (día 1), `calculate_lead_score_task`, `lead_score_decay_task`, `train_company_ml_model_task`, `cleanup_voice_files`, `generate_landing_page` (refund 50/10), `process_agentic_blog_content`, `autonomous_pulse_check`, `process_whatsapp_webhook` (legacy). Beats: reset 00:00, decay 01:00, cleanup 02:00, pulse cada 900s |

### 2.2 Frontends

| App | Puerto PM2 | Real |
|---|---|---|
| **PyME** `frontend/` (`name:pymai-frontend`, renombrar pendiente) | `3010` `next start` | `next:16.1.6`, `react:19.2.3`, TS5, Tailwind4, shadcn/Radix, zustand5, react-query5, axios, RHF+zod, framer-motion, lucide, recharts, d3, leaflet, grid-layout, xyflow, qr-code-styling, sonner, next-themes, markdown, google-oauth, js-cookie, **i18n 5 idiomas `locales/{de,en,es,fr,pt}`** (docs viejos dicen 3 — obsoleto), socket.io-client, livekit-client, paypal-react. **52 `page.tsx`**: `(auth) login/register`, `(dashboard) dashboard/chat/agents/admin/billing/campaigns/channels/contacts/departments/developer/documents/employees/funnel/landing-pages/marketplace/media/pricing/settings/subscribe/templates/wellness`, `(public) beta-register/chat/[slug]/evaluate/privacy/refunds/terms`. `components/` 66 ficheros, `lib/api-client.ts` (axios `NEXT_PUBLIC_API_URL‖http://localhost:5010/api`, `Bearer access_token`, `X-Company-Context`, device-telemetry), `proxy.ts` guards, `providers.tsx` (QueryClient 60s + Themes + Sonner + GoogleOAuth + i18n + ChunkLoadError auto-reload), `next.config.ts` (`ignoreBuildErrors:true`) |
| **WhatsApp** `api-whatsapp/` (`name:whatsapp-api-yt`, genérico) | `3011` `dist/app.js` (código defaultea 3001) | `express 4.18`, `@whiskeysockets/baileys ^6.7.8` + `venom-bot` + `whatsapp-web.js` + `twilio ^3.80.1`, `mysql2`, DI. `src/` 22 ficheros, router con carga dinámica |
| **Landing-gen** `screenshot-to-code/backend` | `5015` `uvicorn main:app` | FastAPI sin docs (`openapi_url=None`), routers `screenshot/generate_code/home/evals`, hereda `OPENAI/ANTHROPIC/GEMINI/REPLICATE` + `AIKROFY_BACKEND_URL=http://localhost:5010` |

### 2.3 Producción PM2 (verificado `pm2 list` 26-sep-2026, todo `online`)

| PM2 | Puerto | Notas |
|---|---|---|
| `aikrofy-redis` | `6380` | `redis-server --port 6380 --bind 127.0.0.1` |
| `aikrofy-frontend` | `3010` | ⚠️ **849 restarts / 6D** — investigar (ver §7) |
| `aikrofy-fastapi` | `5010` `--workers 2` | ⚠️ **248 restarts / 2D** — inestable, `max_memory_restart 500M` activo |
| `aikrofy-worker` | broker `6380/0` | ⚠️ **138 restarts / 2D** |
| `aikrofy-api-whatsapp` | `3011` | 80 restarts / 2D |
| `aikrofy-landing-gen` | `5015` `--workers 2` | estable |
| Extra | `3306 mariadbd`, `80/443 nginx` | cohabita `enpiai-*` (5000,3000,3001,6381) |

---

## 3. Reglas críticas (tolerancia cero)

### A. Estabilidad DB ("Gone Away", lazy-load, invarianza de scope)
1. **`db.session.rollback()` (vía `db_session.rollback()`) al inicio absoluto** de toda Tool/Service entry-point.
2. **Eager loading + primitivización:** antes de cualquier llamada LLM/Tool larga, extraer todo lo necesario a primitivas (str/int/list/dict). **Prohibido** acceder relaciones SQLAlchemy (`agent.company.name`) después de un LLM call (sesión cerrada / hilo bloqueado).
3. **Imports DB solo a nivel módulo:** `from extensions import db` arriba. **NUNCA** re-importar dentro de `try/except` (reescoping → `UnboundLocalError`).
4. **Pre-alocar filepaths multimedia** antes de invocar síntesis (`output_path = os.path.join(UPLOAD_VOICE_DIR, ...)` antes de `VoiceService.synthesize`).
5. **Cleanup explícito:** middleware FastAPI ejecuta `db_session.remove()` al final de cada request.

### B. i18n
- Sin texto hardcodeado: todo UI con `t('key')` de `react-i18next`.
- Locales sincronizados en `frontend/locales/{de,en,es,fr,pt}/translation.json` (**5 idiomas**, no 3).

### C. Env & seguridad
- Secretos solo en `.env` (backend) / `.env.local` (frontend). Críticos: `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PADDLE_API_KEY`, `PADDLE_WEBHOOK_SECRET`, `DATABASE_URL`, más `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `EXTERNAL_API_KEY`, `HUBSPOT_*`, `CELERY_BROKER_URL=redis://localhost:6380/0`.
- ⚠️ `.env.example` (raíz y `backend/`) **obsoleto**: menciona `onepunch`, puertos `5000/5001/3001`, sin `GROQ/OPENROUTER/MEDIA_MICRO/PADDLE/LANGCHAIN/CELERY 6380`. Actualizar antes de onboardear.

### D. Lógica de negocio (LangGraph)
1. Aislamiento de flujos: Payment / Agenda / E-commerce separados.
2. **Créditos:** toda respuesta IA valida `Company.credit_balance`; `0` y no `-1` → bloquear. Costes: landing crear 50 / update 10 (`tasks.py:291`).
3. Agenda consensual: sin booking sin confirmación explícita del usuario.
4. Pagos: `lookup_customer` obligatorio antes de mostrar precios.

### E. Skills dinámicas (desacople de prompts)
1. **Nunca hardcodear** instrucciones/flujos en Python. Todo va a registros `CompanySkill`.
2. **Sync híbrido obligatorio:** todo create/update de skill sincroniza MySQL + `uploads/skills/company_<id>/<skill_name>/SKILL.md` vía `SkillService`.
3. Agentes auto-mejorables: exponer `agent_list_skills` + `agent_create_or_update_skill`.

### F. Sync universal DB + RAG (regla cero-Error-1054)
1. **Fuente única:** modelos SQLAlchemy en `models/`.
2. Tras añadir/cambiar modelos → correr **`backend/scripts/sync_db_schema.py`** (o `python sync_db.py`): `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE` aditivo sin borrar datos. Corre en `deploy.sh`, `start-local.sh` y background al arrancar FastAPI.
3. El protocolo re-verifica planes por defecto, configs y re-indexa manuales BOS-AI en RAG.

---

## 4. Multi-tenant, RAG, departamentos

- **Pinecone namespaces:** `company_{id}` (privado) · `company_{id}_dept_{dept_id}` (Enterprise, `models/department.py:105`, override `Company.pinecone_namespace`) · global BOS-AI (`company_id=None`, handbooks C-Suite en paralelo). Auditoría de chunks en `MessageAudit`.
- **RAG:** `rag_service.py` (394 lín.), `chunk 1000/200`, `upsert_document` vía Celery `index_document_rag`. `routes/rag.py` 16 endpoints.
- **Cuotas (`EnterpriseLimits`):** `pyme 1 dept/10 emps` · `enterprise 5/50` · `enterprise_plus 20/200` · `custom` a medida. `Employee.has_web_access=True` → link `User` (login dashboard); `False` = solo mensajería.

## 5. C-Suite, voz, API-First/MCP, créditos

- **7 Chiefs + Krof:** CEO (orquestador, `gpt-4o-mini` temp 0.0) · COO (Calendar/Sheets/ERP) · CSO (cierre, triaje heap) · CMO (campañas `CompanyCampaign`, Enterprise) · CTO (MCP/skills, Enterprise) · CRO (funnel/carritos, Enterprise) · CFO (LTV/CAC/MRR/ROI NumPy 60FPS, Enterprise). ⚠️ Código: `ENTERPRISE_ONLY_ROLES={cfo,cro}` vs docs que marcan 4 enterprise — unificar.
- **Voz cascada:** STT `media.weblifetech.com/api/micro/audio/transcribe (EXTERNAL_API_KEY)` → `media STT` → Groq `whisper-large-v3` → OpenRouter `openai/whisper-1` → OpenAI `whisper-1`. TTS `edge-tts` local (ThreadPool, no bloquea event loop) → `media/api/tts/speak` → Groq `canopylabs/orpheus-v1-english` → OpenRouter `hexgrad/kokoro-82m` → HF → OpenAI `tts-1`. Voces `es-EC-*` (`tasks.py:477-479`). Detalle en `COMPENDIO §11` + `docs/integraciones/`.
- **API-First/MCP:** `POST /v1/agents/invoke`, `GET /v1/agents/list`, `GET /v1/agents/skills` (auth `X-API-Key=public_api_key`, catálogo 7, validación `<0.1ms` por `auth_cache_service`) · `POST /v1/knowledge/query`, `POST /v1/knowledge/ingest` · MCP `GET/POST /api/companies/{id}/mcp`, `PUT/DELETE …/{server_id}`, `POST …/toggle`, `POST …/test`; `MCPService.get_tools_for_company()` inyecta `StructuredTool` al ReAct loop.
- **WhatsApp:** webhook async `fastapi_app.py:205-461` (filtro `@g.us/@newsletter`, dedup msg-id + hash 2s, LID→phone, typing inmediato, `celery.send_task process_webhook_message`). `MessagingService`: `_send_via_baileys/_via_meta/_via_twilio` + fallback meta→twilio.
- **Créditos (`TokenCreditService`, `Company.credit_balance`, `-1`=ilimitado):** `deduct_company_credits`, pricing por modelo, reset día 1.

## 6. Integraciones (resumen; specs en `docs/integraciones/`)
- **Pagos (8 adapters):** `stripe`, `paypal`, `mercadopago`, `kushki`, `nuvei`, `dlocal_go`, `authorize_net`, `custom` + `PaddleService` + `DLocalGoService` + `PayPalService`. Rutas: `billing 12`, `payments 6`, `payment_gateways 7`.
- **Twilio:** `send_whatsapp/sms/make_call/list_recordings`; `routes/twilio.py` 7.
- **CRM (5 conectores `crm/factory`):** hubspot, salesforce, zoho, pipedrive, dynamics + `HubSpotSyncService`, `routes/hubspot.py` 2.
- **Google:** Calendar/Meet/Sheets (`GoogleService`, `integrations/calendar.py`, `routes/google_auth.py` 7).
- **ERP (6 drivers):** `sap_b1`, `netsuite`, `odoo`, `dynamics_bc`, `contifico`, `mysql`.
- **E-commerce (7):** `shopify`, `woocommerce`, `magento`, `bigcommerce`, `vtex`, `prestashop`.

## 7. Deuda técnica conocida (no ocultar)
1. Nombres legacy: título `PymAI Unified Gateway v2.2.0`, `pymai-frontend`, `whatsapp-api-yt` (más la app enterprise separada, eliminada el 26-sep-2026), índices Pinecone triples, `.env.example` con `onepunch`.
2. `tasks.py` aún `from app import create_app` + `extensions.db` aunque `app.py` es mock — deuda Flask→FastAPI.
3. `GatewayProvider` sin `PADDLE` ni `CUSTOM` (código referencia `CUSTOM` inexistente); Paddle vive fuera del factory.
4. `celery_app.py` default `6379` vs prod `6380`.
5. `MemorySaver` volátil vs "memoria persistente" de docs viejos.
6. ⚠️ Restarts anómalos PM2 (fastapi 248, worker 138 en 2D; frontend 849 en 6D) — investigar OOM/loops antes del próximo release.
7. La app enterprise separada (`:3012`) fue **eliminada el 26-sep-2026** (proceso PM2 detenido, directorio borrado del VPS, refs fuera de `ecosystem.config.js`/scripts): no tenía tráfico (nginx no exponía el puerto, sin DNS, 3 ficheros). El plan `enterprise` se sirve por `plan_type` en `frontend/` :3010.
8. `qrcodly/` vacío, `routes/channels.py` + `services/*.py` raíz legacy, `frontend/FRONTEND_GUIDE.md` (PunchAI/Next14) — archivados en `docs/legacy/`.

---

## 8. Arquitectura Dual de Repositorios: Cloud (Privado) vs. Open-Core Community (Público)

Aikrofy opera bajo un esquema **Dual-Repo Open-Core**:

### 8.1 Los Dos Repositorios (`git remote -v`)
1. **`origin` (Privado — Cloud & Enterprise):** `https://github.com/jonnathanypg/aikrofy.git`
   - Contiene el sistema completo de WEBLIFETECH Cloud (`aikrofy.com`).
   - Ramas activas: `dev` (staging) y `main` (producción VPS Contabo).
   - Incluye `.github/workflows/deploy.yml` (CI/CD automático por SSH hacia el VPS Contabo), `deploy.sh`, `ecosystem.config.js` y el puente Python FFI `backend/services/lem_guardrail_service.py`.
   - ⚠️ **REGLA CRÍTICA DE BINARIOS LEM:** Los modelos/binarios compilados de LEM (`liblemops.so`, `liblemops.dylib`, `liblemv4.so`) **NUNCA** se suben a ningún repositorio Git (ni privado ni público). Ya están instalados directamente en el VPS (`/opt/lem-api/liblemops.so` o `/root/LEMs/SDK_LEM-Ops/liblemops.so`). En el repo privado solo reside el wrapper Python (`lem_guardrail_service.py`) que los carga por FFI cuando `AIKROFY_DEPLOYMENT_MODE=cloud`.
2. **`public` (Público — Open-Core Community):** `https://github.com/UnderlifeFundation/aikrofy.git`
   - Edición comunitaria no comercial (`PolyForm Noncommercial 1.0.0`) promovida por **Fundación Underlife**.
   - Opera con `AIKROFY_DEPLOYMENT_MODE=community` (`docker-compose.community.yml` y `.env.community.example`).
   - **PROHIBIDO** incluir en este repo: `.github/workflows/` (no debe disparar GitHub Actions de deploy a Contabo), `lem_guardrail_service.py`, `test_lem_native.py`, `LEM_OPS_INTEGRACION.md`, `deploy.sh`, `ecosystem.config.js`, ni ningún `.env` o credencial.

### 8.2 Flujo de Trabajo y Comandos de Envío (Cómo trabajar y publicar)
Todo el desarrollo diario se realiza en el repositorio local (conectado a `origin`):
- **1. Enviar cambios a Aikrofy Cloud (Privado — Staging / Producción):**
  ```bash
  git add .
  git commit -m "feat: descripción del cambio"
  git push origin dev    # Despliega a Staging
  # ó git push origin main  # Despliega a Producción (Contabo VPS vía GitHub Actions)
  ```
- **2. Publicar actualización limpia a Aikrofy Open-Core (Público — Fundación Underlife):**
  **NUNCA** hacer `git push public` directo desde tu rama local (arrastraría el historial privado, `.github/workflows/deploy.yml` y el puente LEM). SIEMPRE ejecutar el script sanitizador:
  ```bash
  ./scripts/sync-opencore.sh
  ```
  Este script empaqueta el árbol en un directorio temporal aislado, purga `.github/`, `lem_guardrail_service.py`, `deploy.sh` y binarios `.so/.dylib`, ejecuta una auditoría Zero-Trust contra secretos y hace push de un commit limpio a `UnderlifeFundation/aikrofy.git` (`main`).

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH. Última auditoría real: 26-oct-2026.**
