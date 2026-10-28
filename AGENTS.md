# AGENTS.md — Guía Operativa de Agentes Aikrofy (V4.0 DEFINITIVO)

**App:** Aikrofy (SaaS PyME) & Aikrofy Enterprise (SaaS Corporativo) · **Dominio:** `aikrofy.com`
**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.**
**Consolidado:** 26-sep-2026 desde auditoría real de producción. Hermanos: `GEMINI.md` (contexto y reglas) · `ESTRUCTURA_PROYECTO.md` (mapa) · `COMPENDIO_MAESTRO_AIKROFY.md` (dossier) · Detalle histórico de herramientas en `docs/analisis/ANALISIS_SISTEMA_COMPLETO.md`.

**Valor central:** C-Suite de 7 Chiefs + copiloto **Krof**, RAG dual (BOS-AI global + privada empresa/departamento), 8 estructuras de aceleración (`<0.1ms` auth heap/trie), API-First + MCP, voz STT/TTS en cascada.

---

## 1. Cómo operar (estrategia funcional y arquitectura)

Aikrofy es una junta directiva virtual persistente orquestada con **LangGraph** (`backend/services/langgraph_agent.py`, 1087 lín.), sin prompts estáticos: comportamientos en registros **`CompanySkill`** (MySQL) sincronizados a `uploads/skills/company_<id>/<skill_name>/SKILL.md` vía `SkillService`.

### 1.1 Los 7 Chiefs + Krof (capacidades modulares)

| Chief | Rol | Plan | Clave real |
|---|---|---|---|
| **CEO** Orquestador | clasifica intención, delega subgrafos | todos | `gpt-4o-mini` temp 0.0 |
| **COO** Operaciones | agenda Google Calendar/Meet, Sheets/ERP | todos | `GoogleService`, `integrations/calendar.py` |
| **CSO** Ventas | cierre, triaje leads Max-Heap | todos | `lead_heap_service` |
| **CMO** Marketing | demanda, copy, campañas efímeras `CompanyCampaign` | enterprise | `routes/enterprise.py` |
| **CTO** Tecnología | MCP remotos, sync skills, telemetría | enterprise | `MCPService`, `routes/mcp.py` 6 + `routes/skills.py` 9 |
| **CRO** Ingresos | funnel, carritos abandonados, conversión | enterprise | scoring + billing |
| **CFO** Finanzas | LTV/CAC/MRR/ROI realtime 60FPS NumPy | enterprise | `analytics_vector_service` |

> ⚠️ Desfase a unificar: `ENTERPRISE_ONLY_ROLES={cfo,cro}` en código vs 4 roles enterprise en docs. Criterio vigente: CMO/CTO/CRO/CFO = enterprise; CEO/COO/CSO = todos.

### 1.2 Omnicanal & API-First
- **WhatsApp multi-tenant:** `@whiskeysockets/baileys` en `api-whatsapp/` (:3011). Webhook async `fastapi_app.py:205-461` (filtros `@g.us/@newsletter`, dedup, LID→phone, typing, Celery `process_webhook_message`). Envío `_via_baileys/_via_meta/_via_twilio` + fallback meta→twilio.
- **REST V1:** `POST /v1/agents/invoke`, `GET /v1/agents/list`, `GET /v1/agents/skills`, `POST /v1/knowledge/query`, `POST /v1/knowledge/ingest`. Auth `X-API-Key: public_api_key`, validación `<0.1ms` (`auth_cache_service`).
- **MCP:** `GET/POST /api/companies/{id}/mcp`, `PUT/DELETE …/{server_id}`, `POST …/toggle`, `POST …/test`. `MCPService.get_tools_for_company()` → `StructuredTool` al loop ReAct.

### 1.3 Voz (cascada híbrida)
- **STT:** `media.weblifetech.com/api/micro/audio/transcribe` (`EXTERNAL_API_KEY`) → `media STT` → Groq `whisper-large-v3` → OpenRouter `openai/whisper-1` → OpenAI `whisper-1`. Normalización FFmpeg 16kHz mono MP3.
- **TTS:** `edge-tts` local en `ThreadPoolExecutor` (no bloquea event loop) → `media/api/tts/speak` → Groq `canopylabs/orpheus-v1-english` → OpenRouter `hexgrad/kokoro-82m` → HF → OpenAI `tts-1`. Voces `es-EC-*`.

### 1.4 Departamentos (contención Enterprise)
Namespaces Pinecone `company_{id}_dept_{dept_id}` · `Employee.has_web_access` (True→link `User`, False→solo mensajería) · cuotas `EnterpriseLimits` (pyme 1/10, enterprise 5/50, enterprise_plus 20/200).

---

## 2. Grafo LangGraph real (`langgraph_agent.py:477-497`)

Solo **2 nodos**: `agent ⇄ tools`, condicional `should_continue` → `END`. `MemorySaver` **volátil** (no persistente).

1. **Nodo `agent`:** Gatekeeper (`require_lead_capture` → pide contacto) → GuidedResponse (`trigger_phrases` → respuesta aprobada + acciones, p.ej. links de pago, sin LLM) → Prompt assembly (`SkillService` + directrices Krof + contexto departamental + `CompanyCampaign` vigentes) → LLM (`gpt-4o-mini`/`gpt-5-nano` 0.7, `bind_tools`).
2. **Nodo `tools`:** fija `g.current_company`, ejecuta `tool_calls`, devuelve `ToolMessage(content, tool_call_id)`.
3. **`should_continue`:** si hay `tool_calls` pendientes → `"tools"`; si no → `"end"`.

---

## 3. Arquitectura técnica y requisitos (cifras reales 26-sep-2026)

- **Cognición:** LangGraph + `CompanySkill` (MySQL + filesystem). Catálogo V1 expone 7 roles; el grafo es genérico con ruteo por prompt/skills.
- **DB:** MariaDB/MySQL (`127.0.0.1:3306`, pool 5/5/120s/pre-ping) — **57 tablas / 41 ficheros** en `models/` (ver `COMPENDIO §4`; los "34 modelos" de docs viejos están obsoletos) + Pinecone (`aikrofy-rag`; alias legacy `pymai-rag`/`onepunch-rag`) + Redis `:6380` (⚠️ `celery_app.py` defaultea 6379 — usar env 6380).
- **Créditos:** `Company.credit_balance` (`-1`=ilimitado), `TokenCreditService.deduct_company_credits`, pricing por modelo, landing 50/10, reset día 1.
- **Sync cero-Error-1054:** modelos = fuente única. `backend/scripts/sync_db_schema.py` (o `python sync_db.py`) crea tablas/columnas faltantes (`ALTER TABLE` aditivo). Corre en `deploy.sh`, `start-local.sh` y background al arrancar FastAPI. Re-verifica planes y manuales BOS-AI en RAG.
- **Procesos PM2 (6, todos online):** `6380 redis` · `3010 frontend PyME` · `5010 fastapi --workers 2` · `worker celery` · `3011 whatsapp` · `5015 landing-gen`. ⚠️ Restarts anómalos: fastapi 248, worker 138 (2D), frontend 849 (6D) — investigar antes del release.
- **Frontends:** `frontend/` `:3010` (52 páginas, 5 idiomas `de/en/es/fr/pt`, RBAC, billing/dev; sirve planes `pyme` y `enterprise` por `plan_type`). La app enterprise separada (`:3012`) se **eliminó el 26-sep-2026** (sin tráfico: nginx no exponía el puerto, sin DNS).

## 4. Reglas de contribución (resumen; detalle vinculante en `GEMINI.md §3` y `§8`)
Rollback DB al inicio de cada tool · primitivizar antes de LLM · imports `db` solo a nivel módulo · pre-alocar paths de audio · `t('key')` + 5 locales · secretos en `.env` · validar `credit_balance` · agenda consensual · `lookup_customer` antes de precios · skills sin hardcode · sync híbrido MySQL+filesystem · correr sync schema tras cambiar modelos.

## 5. Operación Dual-Repo (Cloud Privado vs. Open-Core Público)
- **Repo Cloud Privado (`origin` — `jonnathanypg/aikrofy.git`):** Push normal a `dev` o `main` (`git push origin dev` / `git push origin main`). Dispara `.github/workflows/deploy.yml` hacia el VPS. Los binarios compilados LEM (`.so`/`.dylib`) viven instalados en el VPS (`/opt/lem-api/liblemops.so`); jamás se comitean al repo, solo el puente `lem_guardrail_service.py`.
- **Repo Open-Core Público (`public` — `UnderlifeFundation/aikrofy.git`):** **PROHIBIDO** hacer `git push public` directo. Siempre usar **`./scripts/sync-opencore.sh`**, el cual elimina `.github/workflows/` (sin GitHub Actions), excluye `lem_guardrail_service.py`, `deploy.sh` y `ecosystem.config.js`, audita que no existan secretos y publica un árbol limpio para la comunidad.

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH. Auditoría real: 26-oct-2026.**
