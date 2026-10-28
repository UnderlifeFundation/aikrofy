# PLAN DE IMPLEMENTACIÓN 0 → 100 — Interfaces-Para-Agentic-OS.md vs Estado Real Aikrofy

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.**
**Fecha:** 2026-10-01 · **Rev.2:** 2026-10-01 (revisión anti-ruptura, 0 cambios código) · **Repo:** `/Users/jonnathan/AI_LAB-WLT/aikrofy` · **Rama:** `dev`
**Fuente objetivo:** `aikrofy/Interfaces-Para-Agentic-OS.md` (156+ líneas, 4 fases)
**Fuentes de verdad:** `AGENTS.md` · `GEMINI.md` · `ESTRUCTURA_PROYECTO.md` · `ESTADO_ACTUAL_PROYECTO.md` · `COMPENDIO_MAESTRO_AIKROFY.md`
**Método auditoría Rev.1+Rev.2:** `codebase-memory-mcp` (proyecto `Users-jonnathan-AI_LAB-WLT-aikrofy` — 33.370 nodos / 86.776 aristas, status `ready`) + `search_graph` (14 queries) + `search_code` (10 patrones) + `get_architecture(hotspots)` + `query_graph complexity>=20/transitive_loop_depth` (30 hotspots) + `trace_path deduct/get_tools/webhook` + verificación directa `grep`/`read` archivo-por-archivo (`fastapi_app.py:42,205-461`, `celery_app.py:24`, `tasks.py:30-120`, `database.py`, `token_credit_service.py:172-206`, `api-client.ts`, `proxy.ts`, `next.config.ts`, `ecosystem.config.js`, `sync_db_schema.py`). Reglas vinculantes `GEMINI.md §3` + `AGENTS.md §4` respetadas en todo el plan.

---

## 0. Veredicto ejecutivo (validación / contraste)

> El documento `Interfaces-Para-Agentic-OS.md` describe el **estado objetivo Agentic-OS**, no el estado actual. ~55% ya existe como base sólida. ~45% falta y es el objeto de este plan. Nada del documento está implementado como lo describe en GenUI/Entitlements/RedisSaver/3D-GPU.

### 0.1 Matriz de contraste (existe / parcial / falta)

| Dominio del doc (sección) | Estado real verificado | Evidencia código | Gap |
|---|---|---|---|
| **3 estratos:** Intent / Orchestration / Direct-Manipulation | **PARCIAL** — chat + canvas + Kanban existen pero no separados por estratos ni progressive disclosure por rol | `frontend/app/(dashboard)/chat` · `frontend/components/chat/KrofStudioCanvas.tsx:89-544` (viewer estático markdown/export, sin GenUI) · `frontend/components/features/agents/VisualFlowBuilder.tsx` | Falta `IntentSurface` bimodal + `OrchestrationSurface` auditoría/autorización + `DirectSurface` tablas/Kanban + `ProgressiveDisclosure` por `role` |
| **GenUI declarativa** (agente emite params, dev renderiza catálogo auditado, sin HTML/JS del LLM) | **FALTA** — 0 hits `copilotkit\|useCoAgent\|AG-UI` fuera del .md | `frontend/package.json:11-55` sin `@copilotkit/*`, sin `three`, sin `openai` client; `KrofStudioCanvas` no bindea tools | Implementar catálogo `GenUI Registry` + `AG-UI SSE` + `useCoAgent` |
| **Confidence viz + mixed-initiative + approval-first / undo-first** | **FALTA** — 0 hits `interrupt\|HumanInTheLoop` en backend | `backend/services/langgraph_agent.py:16,44-50,499-500` solo `MemorySaver`; `brain_events_service.py:27` menciona “interrupt” solo en comentario | Implementar `interrupt()` + tarjetas decisión + undo window |
| **Onboarding adaptativo + Índices Amplitud / Profundidad + Núcleo Fijo vs Desbloqueables** | **PARCIAL** — wizard 8 pasos estático, sin índices ni topología dinámica | `frontend/app/(public)/beta-register/page.tsx:43-80` (`localStorage aikrofy_beta_form`, steps fijos) · `backend/routes/beta.py` validación solo contacto · `frontend/store/use-onboarding-store` + `frontend/hooks/use-plan-features.ts:1-119` (solo `billing/my-subscription`, sin add-ons/onboarding) | Falta motor `OnboardingProfiler` + `I_AO / I_PT` + `Entitlements` + nav lateral dinámica |
| **Entitlements Runtime <0.1ms (Stigg/Schematic-like): plan+add-ons+promo+onboarding, bitmap Redis 6380, código upgrade sin romper flujo** | **FALTA** — `auth_guard.py` solo jerarquía, no derechos comerciales | `backend/services/auth_guard.py:1-168` solo `SUPER_ADMIN/owner/delegated/manager/employee`, sin `plan_type`, sin Redis | Crear `backend/services/entitlements_service.py` + Redis bitmap/hash + middleware FastAPI + hook `useEntitlements()` |
| **Monetización 5 niveles (ingesta idempotente, medición, verificación sync, ledger, facturación externa) + fórmula `MRR = base + Σ add-ons + Σ overage`** | **PARCIAL** — créditos + factory + licencias ZIP, sin 5 niveles ni add-ons SaaS | `backend/services/token_credit_service.py:63,173 deduct_company_credits` · `backend/models/company.py:65 credit_balance` · `backend/services/payment_gateways/factory.py:19-50` 8 adapters OK · `backend/models/modular_asset.py:19-170` `ModularAsset/AssetLicense` HMAC `AKF-` solo para ZIP marketplace, no para módulos SaaS · `backend/routes/marketplace.py`, `billing 12/payments 6/payment_gateways 7` dispersos · `seed_plans.py:70`, `sync_plans_dlocal.py:60` solo `channels` genéricos | Falta `BillingEvents` idempotentes + `UsageAggregator` Celery + `CreditLedger` inmutable + `SubscriptionAddon` + webhooks purga Redis <5ms |
| **Pricing Jab $29 / Uppercut $99 / Knockout $299 + Add-ons ERP $35/$60, LiveKit $20/300min, enterprise_plus 20/200** | **FALTA** como modelo | No hay `Jab/Uppercut/Knockout` en `models/subscription.py:23,94` ni `seed_*`; `EnterpriseLimits pyme 1/10 enterprise 5/50 plus 20/200` citado en docs pero sin modelo `EnterpriseLimits` encontrado en `models/` | Crear `Plan` seed + `ModularAsset` tipo `saas_addon` + `AssetLicense` SaaS + UI pricing/add-ons |
| **Bio-3D R3F + THREE.Points + BufferGeometry + shaders GLSL (<5% GPU, 60FPS) + tabla estados Idle/thought/tool/handoff/HITL/guardrail** | **FALTA** — `LivingBrainCanvas` es 2D Canvas, no WebGL | `frontend/components/features/brain/LivingBrainCanvas.tsx:1-395` Canvas2D `arc/bezier/photon`, sin `three` · `frontend/lib/use-living-brain.ts:190` hook SSE/polling simulado · `backend/routes/brain_events.py` `simulate/get_brain_status` mock | Instalar `three/@react-three/fiber/@react-three/drei` + `Brain3D` + `useBrainState(langgraph events)` + mapeo tabla §Interfaces |
| **XYFlow axones bio + vesículas SVG/Web Animations + mapeo 8 estructuras** | **PARCIAL** — XYFlow base sin bio | `frontend/components/features/agents/VisualFlowBuilder.tsx:23-24,187,362,495` + `WorkflowNode.tsx:4` + `DeletableEdge.tsx:9` con `@xyflow/react ^12.11.6` OK, pero edges rígidos | Crear `AxonEdge` animado + `useFlowTelemetry()` desde `brain_events` + leyenda 8 estructuras |
| **RedisSaver `langgraph-checkpoint-redis` :6380, thread `(company,user,channel_session)`, 0.34ms, sobrevive PM2** | **FALTA** — volátil confirmado | `backend/services/langgraph_agent.py:16 MemorySaver`, `44-50 get_checkpointer()`, `500 compile(checkpointer)` · `backend/requirements.txt:20 langgraph==1.0.10` sin `langgraph-checkpoint-redis` · `backend/services/langgraph_state.py:14,33 channel telegram/whatsapp/webchat` sin thread canónico | Migrar a `RedisSaver` + `requirements` + `docker/redis 6380` + migración threads + tests reinicio |
| **Omnicanal unificado Celery+Redis 4 etapas (dedup 2s, Trie 3ms, ReAct thread, dispatch SSE/Baileys/Meta/Twilio/Telegram) + CopilotKit web + botones/Flows/InlineKeyboards + deep-link canvas firmado** | **PARCIAL** — WhatsApp sólido, Telegram/Web mínimos, sin bus unificado | `backend/fastapi_app.py` webhook WhatsApp async (filtros `@g.us/@newsletter`, dedup, LID→phone, typing, `process_webhook_message`) OK · `api-whatsapp/src/` Baileys 6.7.8 OK · `backend/services/messaging_service.py:78,328 send_telegram` solo outbound · `backend/routes/webhooks.py:1003 telegram_webhook` básico sin aiogram, sin `InlineKeyboard`, sin HITL callback · `backend/tasks.py:522 telegram` dispatch puntual, sin bus 4 etapas · `sse-starlette==2.4.1` instalado pero sin endpoint `AG-UI SSE` agéntico | Crear `OmniBus` Celery + `ThreadResolver` + `DedupService` + `TelegramService (aiogram)` + `WhatsApp Flows` + `AG-UI SSE` + `SignedCanvasLink` |
| **Multi-tenant 4 niveles Holding>Company>Dept>Employee + Pinecone `company_{id}_dept_{dept_id}` + `has_web_access` + MessageAudit** | **PARCIAL-ALTO** — falta Holding | `backend/models/department.py:31,53,95-116 get_pinecone_namespace()` OK · `backend/models/company.py:39 pinecone_namespace` OK · `backend/services/rag_service.py _get_namespace/query_multi_namespace/get_context_multi_namespace` OK · `backend/models/employee.py:57 has_web_access` OK · `MessageAudit` existe · **No** `Holding/Organization` ni bolsa créditos consolidada | Crear `Holding` + `Company.holding_id` + `CreditPool` + panel auditoría vectorial |
| **8 estructuras <0.1ms-3ms (hash auth, heap O(1), trie O(L), numpy 60FPS, linked-list 20, FIFO, LIFO routing.py, graph HNSW) + scoring `S = α·P_ML + β·Q`** | **EXISTE** — base más sólida, solo cablear a UI | `auth_cache_service` · `lead_heap_service: rebuild/get_top/pop` · `crm_trie_service` · `analytics_vector_service` · `langgraph_agent sliding window` · `tasks.py/Celery Redis 6380` · `routing.py stack` · `Pinecone HNSW` verificados en docs + graph `search_graph lead heap trie auth cache` hits | Solo observabilidad: exponer `/telemetry/structures` + vesículas XYFlow + badge latencia |
| **LLM agnóstico `llm_service.py` (4o-mini/5-nano rápido, Claude 3.5 Sonnet GenUI, Gemini Flash docs, Groq Whisper LPU, MCP privado)** | **PARCIAL** — solo OpenAI cableado | `backend/services/llm_service.py:10 LLMService` existe pero `_get_llm langgraph_agent.py:56-70` solo `ChatOpenAI gpt-4o-mini/5-nano 0.7` · `requirements anthropic==0.84.0 google-generativeai==0.8.6` instalados sin ruteo · `MCPService.get_tools_for_company()` OK inyecta `StructuredTool` | Implementar `LLMRouter` por tarea + fallback + pricing por modelo en `TokenCreditService` |
| **Fase 1 doc: fix PM2 restarts (248/138/849) + renombrar PymAI/onepunch + `.env.example` obsoleto + `celery 6379 vs 6380` + Flask mock** | **DEUDA CONFIRMADA** | `ecosystem.config.js` 6 apps · `fastapi_app.py:33 PymAI Unified Gateway v2.2.0` · `frontend/package.json:2 pymai-frontend` · `api-whatsapp package whatsapp-api-yt` · `Pinecone aikrofy-rag + pymai-rag/onepunch-rag` triple · `celery_app.py default 6379` · `tasks.py from app import create_app` con `app.py FlaskMock 27 lín.` · `qrcodly/` vacío · `routes/channels.py + services/*.py` raíz shims | P0 obligatorio antes de F1-F4 |

### 0.2 Qué NO hacer (para no romper prod, según `GEMINI.md §3` / `AGENTS.md §4`)

1. `db.session.rollback()` al inicio de toda Tool/Service; primitivizar antes de LLM; imports `db` solo nivel módulo; pre-alocar paths audio; `t('key')` + 5 locales `de/en/es/fr/pt`; secretos solo `.env`; validar `credit_balance (-1=ilimitado)`; agenda consensual; `lookup_customer` antes de precios; skills sin hardcode (vía `CompanySkill` + `SkillService` sync MySQL+`uploads/skills/company_<id>/…/SKILL.md`); correr `backend/scripts/sync_db_schema.py` tras cambiar modelos.
2. No dispersar `if plan==…` en componentes — todo por `Entitlements Runtime`.
3. No generar HTML/JS desde el LLM — solo directivas declarativas contra catálogo auditado.
4. No bloquear event loop con TTS — `edge-tts` en `ThreadPoolExecutor` (ya OK, mantener).

---

## 1. Arquitectura objetivo (resumen buildable)

```
[Intent Surface: webchat/Krof + voz PTT + contexto] 
  → [Entitlements Guard <0.1ms Redis] → [LangGraph ReAct (RedisSaver thread canónico) + Skills + MCP + RAG multi-ns + LLMRouter]
  → [Orchestration Surface: plan visible + provenance RAG + approval-first / undo-first + confidence]
  → [GenUI Renderer: catálogo declarativo → React nativo | WhatsApp Flows | Telegram Inline | deep-link canvas firmado]
  → [Direct Surface: Kanban/tablas/edición + XYFlow axones + Brain3D shaders]
  → [OmniBus Celery/Redis: dedup 2s → Trie 3ms → ReAct → dispatch SSE/AG-UI/Baileys/Meta/Twilio/Telegram]
  → [Billing 5 capas async (Celery) sin bloquear diálogo + purga Redis <5ms]
```

---

## 2. Plan por fases (0→100). Total: 100 ítems verificables.

> Convención: `[ID] Tarea — archivos — aceptación`. `P0` debe cerrarse antes de `P1-P4` del doc.

### FASE P0 — Estabilidad + deuda + base medible (0-15) — corresponde a Fase 1 doc (mitad)

- [00] Congelar `main/dev`, tag `agentic-os-baseline-20261001`, snapshot `dump.rdb` + `mysqldump`, `pm2 save`, documentar `pm2 list` restarts actuales — aceptación: tag + artefactos en `docs/analisis/`.
- [01] Investigar restarts PM2 (fastapi 248/worker 138/frontend 849): `pm2 logs --lines 500`, `max_memory_restart 500M`, OOM/WS leaks, `uvicorn --workers 2` vs memoria, `next start` heap — archivos: `ecosystem.config.js`, `backend/fastapi_app.py`, `frontend/next.config.ts` — aceptación: causa raíz + fix + 7 días <5 restarts/día.
- [02] Unificar Redis `6380`: `backend/celery_app.py` default `6379` → env `CELERY_BROKER_URL=redis://localhost:6380/0`, `backend/config.py`, `.env.example` — aceptación: `grep 6379` 0 hits salvo comentario.
- [03] Renombrado seguro `PymAI→Aikrofy`: `fastapi_app.py:33` título, `frontend/package.json:2`, `api-whatsapp/package.json`, índices Pinecone alias `aikrofy-rag` canónico (mantener alias legacy lectura) — aceptación: `grep -ri pymai|onepunch` solo en `docs/legacy/`.
- [04] Actualizar `.env.example` (raíz + `backend/`): agregar `GROQ/OPENROUTER/EXTERNAL_API_KEY/MEDIA/HUBSPOT/PADDLE/LANGCHAIN/CELERY 6380/TELEGRAM_BOT_TOKEN/LIVEKIT_*` — aceptación: onboarding limpio desde 0 con `diff .env.example vs GEMINI.md §3C` = 0 faltantes.
- [05] Eliminar/archivar muertos: `qrcodly/` vacío, `routes/channels.py`, `services/*.py` raíz shims, `frontend/FRONTEND_GUIDE.md` → `docs/legacy/` — aceptación: `ls` raíz sin muertos + CI verde.
- [06] Resolver deuda Flask→FastAPI en `backend/tasks.py: from app import create_app` + `app.py FlaskMock` + `routing.py 484 shim` — plan: adapter `FastAPIContext` mínimo, no reintroducir Flask — aceptación: `tasks.py` sin `from app import` + worker boot verde.
- [07] Endurecer `ENTERPRISE_ONLY_ROLES`: unificar código `{cfo,cro}` vs docs `{cmo,cto,cro,cfo}` → criterio doc: `CMO/CTO/CRO/CFO=enterprise; CEO/COO/CSO=todos` — archivos: `backend/services/*`, `frontend/hooks/*`, `seed_plans.py` — aceptación: test matriz roles × planes verde.
- [08] Instrumentar telemetría base: `/api/telemetry/structures` (latencias hash/heap/trie/numpy), `/api/telemetry/graph` (LangGraph pasos), `/health` extendido (DB/Redis/Pinecone/Celery) — aceptación: dashboard `admin/telemetry` con p50/p95.
- [09] Tests base + CI: `pytest` backend (auth/entitlements/billing/rag), `tsc --noEmit` + `eslint` frontend, `pm2 + pytest` en `.github/` — aceptación: pipeline rojo→verde, cobertura crítica >70%.
- [10] ADR inicial (`codebase-memory-mcp manage_adr`): RedisSaver, Entitlements, AG-UI/CopilotKit, R3F, Billing 5 capas — aceptación: `ADR-001..005` persistidos.
- [11] `sync_db_schema.py` verificado en `deploy.sh/start-local.sh/boot FastAPI` + re-verifica planes/BOS-AI RAG — aceptación: `Error 1054` imposible en staging.
- [12] Normalizar i18n 5 idiomas: auditar `t('key')`, sincronizar `frontend/locales/{de,en,es,fr,pt}/translation.json` — aceptación: `grep texto hardcodeado` en `app/(dashboard)` = 0.
- [13] Definir `thread_id` canónico `(company_id,user_id,channel_session_id)` + `ChannelSession` tabla si falta — aceptación: doc + migración + helper `ThreadResolver`.
- [14] Benchmarks base: medir `<0.1ms auth`, `3ms trie`, `2ms numpy`, `0.34ms Redis checkpointer (tras P1)`, SSE p95 — aceptación: `docs/analisis/BENCHMARKS_BASELINE.md`.
- [15] Gate P0: checklist 00-14 verde + demo `pm2 status` estable + `อ่าน` de este plan aprobado por owner.

### FASE P1 — Persistencia + OmniBus core (16-35) — corresponde a Fase 1 doc (núcleo) + parte Fase 4

- [16] Añadir `langgraph-checkpoint-redis>=0.1.0` a `backend/requirements.txt` (fijar versión compatible `langgraph==1.0.10`) + `pip install` + `poetry` si aplica `screenshot-to-code/` — aceptación: `import langgraph_checkpoint_redis` OK en Python 3.14.
- [17] Migrar `backend/services/langgraph_agent.py:16,44-50,500`: `MemorySaver` → `RedisSaver(redis://localhost:6380/0, prefix=aikrofy:checkpoint:)` con `TTL` + `serializer msgpack` — mantener `get_checkpointer()` API — aceptación: reinicio FastAPI conserva hilo (test: 2 msgs → restart → 3er msg con contexto).
- [18] Implementar `ThreadResolver`: `canonical_thread(company_id,user_id,channel_session_id)` + normalización `LID→phone (WhatsApp)`, `chat_id (Telegram)`, `sessionId (web)` — archivos: `backend/services/thread_resolver.py` + `models/channel_session.py` — aceptación: mismo usuario web↔WhatsApp↔Telegram comparte hilo si `user_id` resuelto, si no hilos separados por canal.
- [19] `DedupService` Redis: `SET msg_id NX EX 2s` + `hash(contenido+sender+ts)` — integrar en `fastapi_app.py webhook`, `routes/webhooks.py:1003 telegram`, nuevo `routes/telegram.py` — aceptación: reintento red no duplica ReAct (test doble POST = 1 ejecución).
- [20] `IdentityResolver`: `Trie crm_trie_service` 3ms `phone/chat_id → Customer.company_id` + fallback MySQL + `Employee.has_web_access` — aceptación: p95 <5ms, sin query SQL en hot path (cache).
- [21] `OmniBus` Celery: `process_omni_message(channel,payload,thread_id)` 4 etapas doc (dedup→identidad→ReAct→dispatch) unificando `process_webhook_message`, `process_whatsapp_webhook`, `telegram_webhook` — archivos: `backend/tasks.py`, `backend/services/omni_bus.py` — aceptación: un solo entry para 3 canales + DLQ + reintentos.
- [22] Dispatch web `SSE + AG-UI` mínimo: `GET /api/companies/{id}/agent/stream?thread_id=` (`sse-starlette`) emitiendo `agent_thought/tool_call/handoff/hitl/guardrail/final` — aceptación: `curl -N` recibe eventos + `useLivingBrain` los consume.
- [23] Endurecer WhatsApp Baileys: mantener `_via_baileys/_via_meta/_via_twilio` + fallback `meta→twilio` en `MessagingService`, agregar `typing` + `read receipts` + `WhatsApp Flows` hello-world — aceptación: envío/recibo E2E en staging con 3 proveedores.
- [24] Telegram v1 (sin AI-heavy): `aiogram` o `python-telegram-bot` webhook `POST /api/channels/telegram/{channel_id}` → `OmniBus` + `send_telegram` con `InlineKeyboard` para `approval` (ver P6) — archivos: `backend/services/telegram_service.py`, `backend/routes/telegram.py` — aceptación: `/start` + eco + botón inline responde `callback_query`.
- [25] Voz sin regresión: congelar cascada `STT media→Groq whisper-large-v3→OpenRouter→OpenAI` + `TTS edge-tts ThreadPool→media→Groq orpheus→Kokoro→HF→OpenAI tts-1` (`voice_service.py`, `routes/voice.py`, `tasks.py:477-479 cleanup_voice_files`) — solo agregar `pre-alocación paths` + `créditos por segundo` hook (ver P3) — aceptación: PTT WhatsApp E2E + test `edge-tts` no bloquea loop.
- [26] `MessageAudit` + `Conversation/Message` con `thread_id` + `channel_session_id` + `provenance chunks` — migración aditiva — aceptación: auditoría por hilo muestra `chunks Pinecone` usados.
- [27] Tests P1: `test_redis_checkpoint_persistence`, `test_omnibus_dedup`, `test_thread_resolver`, `test_telegram_inline_echo`, `test_sse_stream` — aceptación: `pytest -k "p1"` verde + caos `kill -9 fastapi` sin pérdida.
- [28-35] Reservados buffer P1 (rollback plan, runbook PM2, staging `api-staging.aikrofy.com`, feature flags `REDIS_CHECKPOINT_ENABLED/OMNIBUS_ENABLED/TELEGRAM_V1_ENABLED`).

### FASE P2 — Entitlements + Onboarding adaptativo (36-55) — corresponde a Fase 2 doc

- [36] Diseñar `Entitlements Schema`: `Plan(plan_type: pyme|enterprise|enterprise_plus|custom, base_credits, limits dept/emp)` + `ModularAsset(asset_type: saas_addon|blog_module|..., price_mrr, metered)` + `AssetLicense(company_id, asset_id, HMAC-SHA256, domain, status)` + `SubscriptionAddon` + `PromoGrant` + `OnboardingProfile(I_AO,I_PT,respuestas)` — archivos: `models/plan.py`, `models/modular_asset.py` (extender), `models/onboarding_profile.py` (nuevo), `scripts/sync_db_schema.py` — aceptación: migración aditiva + `to_dict()` + seed `Jab/Uppercut/Knockout`.
- [37] Implementar `EntitlementsService.evaluate(company_id,user_id,feature_key,usage_delta) -> {allowed, code, upgrade_hint, cheapest_path}` fórmula doc: `allowed = (plan ∪ addons ∪ promo ∪ onboarding) ∩ (credit_balance>0) ∩ (quotas)` + `min-cost` para overage — `<0.1ms` vía `Redis HASH company:{id}:entitlements + BITMAP features` + `auth_cache_service` — archivos: `backend/services/entitlements_service.py`, `backend/services/auth_cache_service.py` (extender) — aceptación: `pytest` matriz 4 planes × 12 features × overage verde, p95 <0.5ms (objetivo <0.1ms local).
- [38] Middleware `EntitlementsGuard`: FastAPI dependency + decorador `@require_entitlement("erp.sync")` que devuelve `402 PAYMENT_REQUIRED {code: UPGRADE_REQUIRED|CREDITS_EXHAUSTED|QUOTA_EXCEEDED, cta}` sin ejecutar LLM/tool — integrar en `routes/enterprise.py`, `routes/mcp.py`, `routes/skills.py`, `v1/agents.py` — aceptación: Krof no incurre costo si bloqueado + frontend intercepta `402` → modal (ver [42]).
- [39] `useEntitlements()` frontend: `React-Query stale 30s` + `can(feature)` + `<Gated feature=... fallback=UpgradeModal>` + `plan_type` nav dinámica (Núcleo Fijo siempre visible: Krof/chat/agentes base/métricas/identidad; Contextuales por entitlement: ERP/ecommerce/pagos/landing-gen/LiveKit/MCP/CMO-CTO-CRO-CFO) — archivos: `frontend/hooks/use-entitlements.ts`, `frontend/components/shared/Gated.tsx`, `frontend/components/layout/Sidebar.tsx` — aceptación: cambio plan en backend refleja menús <5s tras purga (ver [45]).
- [40] `OnboardingProfiler`: transformar `beta-register/page.tsx` en asistente Krof-dinámico (preguntas negocio/tamaño/stack/madurez IA) que computa `I_AO (amplitud) / I_PT (profundidad)` y sugiere `módulos inicialmente desbloqueados` tabla doc (Micro-PyME: WhatsApp+Calendar+paylink; Mediana: ecom+CRM+CMO funnel; Corp: ERP+MCP+CFO 60FPS+SIP) — archivos: `frontend/app/(public)/beta-register/page.tsx` (rewire), `frontend/app/(dashboard)/onboarding/page.tsx`, `backend/routes/onboarding.py`, `backend/services/onboarding_service.py` — aceptación: completar onboarding crea `OnboardingProfile` + pre-selecciona add-ons + configura sidebar.
- [41] Catálogo `Núcleo Fijo vs Desbloqueables` en código (no condicionales dispersos): `frontend/lib/entitlements-catalog.ts` + `backend/services/catalog_service.py` (96 servicios / 335 endpoints mapeados a `feature_key`) — aceptación: `grep "if plan ==" frontend/` = 0 (solo vía `can()`).
- [42] `UpgradeModal` + deep-link `pricing?feature=erp.sync&company=`: intercepta `402`, muestra `cheapest_path (addon $35 vs upgrade plan)`, CTA `POST /api/billing/addons` idempotente (`Idempotency-Key`) — aceptación: compra sin salir del flujo chat/canvas.
- [43] `PaymentAdapterFactory` add-ons: extender `factory.py:19-50` con `paddle_v2` (falta, hoy fuera del factory) + `subscription line items` por `AssetLicense` + `webhook confirm` → `Subscription + AssetLicense active` — archivos: `services/payment_gateways/adapters/paddle_v2_adapter.py`, `routes/billing_addons.py` — aceptación: compra `ERP Odoo $35` crea `AssetLicense HMAC(company_id,asset_slug,domain)` verificable con `verify_license_token()` ya existente.
- [44] `HMAC SaaS` reutilizar `modular_asset.py:98-156 generate/verify_license_token()` para módulos SaaS (no solo ZIP): `allowed_domains=[*.aikrofy.com, custom]` + `vps_signature` opcional — aceptación: `GET /api/marketplace/verify?token=` 200/403.
- [45] Purga reactiva `<5ms`: webhook pago → `DEL company:{id}:entitlements` + `PUBLISH entitlements:invalidate` + frontend `socket.io-client`/`SSE` refetch — aceptación: compra → menús/endpoints habilitados medido <5s E2E (objetivo doc <5ms cache + <5s UI).
- [46] `use-plan-features.ts` deprecado → wrapper sobre `useEntitlements()` para compat — aceptación: sin regresión `billing/my-subscription`.
- [47] i18n + pricing tables `Jab $29 2k créditos / Uppercut $99 10k / Knockout $299 40k + 50k recarga` en `pricing/page.tsx` 5 idiomas — aceptación: tablas doc §monetización render + `t()` completo.
- [48] Tests P2: `test_entitlements_matrix`, `test_onboarding_indices`, `test_addon_purchase_idempotent`, `test_upgrade_modal_402`, `test_sidebar_gating` — aceptación: verde + p95 entitlements reportado.
- [49-55] Buffer: `EnterpriseLimits` como tabla (si no existe, crear `pyme 1/10, enterprise 5/50, plus 20/200`), backfill `Company.plan_type`, auditoría `Stigg/Schematic` paridad, feature flags `ENTITLEMENTS_ENFORCED/ONBOARDING_V2`.

### FASE P3 — Billing 5 capas + créditos (56-68) — completa monetización doc (transversal Fase 2)

- [56] `BillingEvents`: `POST /api/billing/events` idempotente (`event_id UUID`, `company_id, feature_key, units, model, thread_id`) → `Redis Stream` → `Celery` — archivos: `models/billing_event.py`, `routes/billing_events.py` — aceptación: doble POST mismo `event_id` = 1 ledger.
- [57] `UsageAggregator` Celery beat cada 60s: agrega `BillingEvents → UsageDaily (company, feature, units, cost)` — aceptación: voz continua 10min no desborda (cap + throttle).
- [58] `CreditLedger` inmutable: `ledger(id, company_id, delta, reason, ref_event, balance_after, created_at)` + `Company.credit_balance` como caché, `-1=ilimitado` — `TokenCreditService.deduct` escribe ledger primero — aceptación: `SELECT SUM(delta)` reconcilia con `credit_balance`.
- [59] Verificación sync en hot path: `EntitlementsService` valida `credit_balance>0` antes de LLM/tool (ya [38]), tarificación async después — aceptación: diálogo p95 sin +latencia billing.
- [60] Pricing por modelo en `TokenCreditService`: `gpt-4o-mini/5-nano` barato, `claude-3.5-sonnet` GenUI caro, `gemini-flash` docs, `groq-whisper` voz/seg — tabla `ModelPricing` + `LLMRouter` (ver P5) — aceptación: misma tarea distinta ruta = distinto costo ledger.
- [61] Voz tasada: `STT seg + TTS chars + LiveKit min` → `BillingEvents` — aceptación: llamada LiveKit 5min genera 3 eventos + ledger.
- [62] Facturación externa: `Paddle v2 + Stripe` `subscription update` con `addon line items` + `DLocal/MercadoPago/Kushki/Nuvei/Authorize` según `PaymentGatewayConfig` — aceptación: factura mensual `MRR = base + Σ addons + Σ overage` conciliada en staging.
- [63] `AssetLicense` lifecycle: `trial → active → suspended (impago) → revoked` + `cron` + `TrustGuardrail` bloquea (`guardrail` rojo) — aceptación: impago bloquea ERP/MCP con `402` + UX ámbar/rojo (ver P5).
- [64] Panel `admin/billing` + `subscribe` + `marketplace` unificados: `AssetLicense` SaaS + ZIP en una vista — aceptación: owner compra/gestiona/cancela add-on sin soporte.
- [65] Tests P3: `test_billing_idempotent`, `test_ledger_reconciles`, `test_overage_blocks`, `test_voice_metered`, `test_paddle_addon_e2e` (mock) — aceptación: verde + reporte margen `Jab/Uppercut/Knockout` simulado.
- [66-68] Buffer: `reset_monthly_credits día 1` ya existe (`tasks.py`) → extender con `base_credits por plan + rollover promo`, alertas `80%/100%`, feature flag `BILLING_V2`.

### FASE P4 — GenUI + AG-UI + Orchestration Surface (69-82) — corresponde a Fase 3 doc (mitad)

- [69] Instalar `CopilotKit`: `npm i @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime` + `AG-UI` endpoint `POST /api/companies/{id}/copilot` (`CopilotRuntime` Python o proxy Node) conectado a `LangGraphAgentService` — archivos: `frontend/app/(dashboard)/chat/page.tsx`, `frontend/components/chat/CopilotProvider.tsx`, `backend/routes/copilot.py` — aceptación: `useCoAgent` recibe estado LangGraph en web.
- [70] `GenUI Registry` (catálogo auditado, prohibición HTML/JS del LLM): `KpiCard, FunnelChart, QuoteEditor, LeadTable, ApprovalCard, CalendarSlotPicker, PaymentLinkCard, ErpSyncStatus` — cada uno `props zod` + `a11y` + `5 idiomas` — archivos: `frontend/components/genui/*.tsx`, `frontend/lib/genui-registry.ts` — aceptación: LLM solo emite `{component, props}` validado, nunca `dangerouslySetInnerHTML` salvo `MarkdownRenderer` sanitizado ya existente.
- [71] Rewire `KrofStudioCanvas.tsx` a `GenUI Canvas`: mantener export/doc/table/code/report + agregar `renderGenUI(msg.parts)` + `useCoAgent(state.canvasDoc, state.pendingApproval)` bidireccional — aceptación: Krof actualiza canvas sin `onAskAiRefinement` manual (hoy `page admin-chat:997` lo pasa manual).
- [72] `OrchestrationSurface`: panel `plan visible (pasos, tools, RAG provenance chunks, costo estimado créditos)` + `Progressive Disclosure` (gestión ve resultado+confirm; admin/dev expande `traza ReAct + telemetría grafo + auditoría vectorial`) — archivos: `frontend/components/chat/OrchestrationPanel.tsx` — aceptación: click `tool_call` muestra `args + latency + chunks`.
- [73] `Confidence viz`: badge `alta/media/baja` en `CFO propuesta / CRO cambio precios` con `explicación + fuentes` — datos desde `LLM logprobs / TrustGuardrail score / RAG score` — aceptación: `baja` exige `approval-first`.
- [74] `approval-first` (irreversibles: contable/bancario/DB delete, `TrustGuardrail`): `LangGraph interrupt()` → `ApprovalCard` web / botones WhatsApp-Telegram → `resume/cancel` — archivos: `backend/services/langgraph_agent.py` (añadir `interrupt` node), `backend/services/approval_service.py`, `frontend/components/genui/ApprovalCard.tsx` — aceptación: CFO no ejecuta sin `approve` firmado (`actor+ts+HMAC`).
- [75] `undo-first` (reversibles: borrador campaña, reorder leads): ejecuta + `toast Deshacer 10s` + `compensating action` — aceptación: deshacer revierte `CompanyCampaign`/`lead order`.
- [76] `SSE AG-UI` eventos `agent_thought/tool_call/handoff/hitl/guardrail/final + genui_parts` consumidos por `useLivingBrain` + `OrchestrationPanel` + `Brain3D` (ver P5) — aceptación: un solo stream alimenta 3 vistas.
- [77] WhatsApp/Telegram fallback GenUI: `component → botones/listas/Flows/InlineKeyboard/voz PTT` + `deep-link canvas firmado` (`JWT HS256 company+thread+exp 15min`) a vista móvil — archivos: `backend/services/genui_translator.py` — aceptación: `QuoteEditor` en WhatsApp = lista + link canvas.
- [78] Seguridad GenUI: `allowlist components`, `props schema validation`, `CSP`, `audit log` (`MessageAudit.genui_parts`) — aceptación: fuzz `component=evil` rechazado 400.
- [79] Tests P4: `test_genui_allowlist`, `test_approval_interrupt_resume`, `test_undo_compensate`, `test_agui_stream_parts`, `test_whatsapp_genui_fallback` — aceptación: verde + demo CFO approval E2E.
- [80-82] Buffer: `ChatChartWidget` ya existe → migrar a `GenUI Registry`, `MarkdownRenderer` mantener `DOMPurify`, flags `GENUI_ENABLED/AGUI_ENABLED/APPROVAL_ENFORCED`.

### FASE P5 — Bio-3D + XYFlow vivo + LLM agnóstico (83-90) — corresponde a Fase 3 doc (resto)

- [83] Instalar `three @react-three/fiber @react-three/drei` (fijar React 19 compat) + `Brain3D.tsx`: `THREE.Points + BufferGeometry` 3-5k partículas, `ShaderMaterial GLSL` vértice (sinusoidal `uTime/uActivity`) + fragmento (atenuación radial índigo→esmeralda/violeta, ámbar HITL, carmesí guardrail) `<5% GPU` — archivos: `frontend/components/features/brain/Brain3D.tsx`, `frontend/components/features/brain/shaders.ts` — aceptación: 60FPS en laptop corporativa (`perf HUD`), `LivingBrainCanvas 2D` queda como fallback `prefers-reduced-motion` o sin WebGL.
- [84] `useBrainState()`: mapear `SSE AG-UI` → `uniforms` (`idle: índigo baja frecuencia / thought: violeta converge / tool: pulso centro→bordes / handoff: filamento CEO→CSO / hitl: ámbar freeze / guardrail: dispersión roja`) tabla doc — aceptación: demo `tool_call` dispara pulso visible <200ms.
- [85] `AxonEdge` XYFlow: `BaseEdge + SVG animated dash / Web Animations vesículas`, props `volume/color/speed` desde `telemetría 8 estructuras` (`heap/trie/numpy/latencias`) — archivos: `frontend/components/features/agents/AxonEdge.tsx`, `useFlowTelemetry.ts` — aceptación: `VisualFlowBuilder` muestra flujo `lead_heap O(1)` como vesículas rápidas verdes.
- [86] `LLMRouter` en `backend/services/llm_service.py`: `intent rápida → gpt-4o-mini/5-nano`, `GenUI schema → claude-3.5-sonnet`, `docs masivos → gemini-flash`, `Whisper → groq LPU`, `privado → MCP local`, fallback chain + `pricing` → `BillingEvents` — aceptación: `LLM_ROUTER_ENABLED` + test `GenUI schema` usa Claude mock.
- [87] `RAG provenance`: `rag_service query_multi_namespace` ya OK → exponer `chunks {doc_id, score, ns}` al `OrchestrationPanel` + `MessageAudit` — aceptación: cada respuesta IA muestra “3 fuentes” expandible.
- [88] `CFO 60FPS NumPy`: mantener `analytics_vector_service` + endpoint `GET /api/analytics/vectors/stream` (downsample) para `FunnelChart GenUI` — aceptación: `recharts/d3` actualiza sin jank (ver `package.json d3/recharts` ya OK).
- [89-90] Buffer: `LiveKit SIP trunk` diseño (ver P6), `drei` solo lo necesario (no inflar bundle), `next/dynamic ssr:false` para `Brain3D`, flags `BRAIN3D_ENABLED/AXON_ENABLED/LLM_ROUTER_ENABLED`.

### FASE P6 — Paridad omnicanal + HITL móvil + telefonía (91-96) — corresponde a Fase 4 doc (mitad)

- [91] Unificar `ThreadResolver + OmniBus` en prod con `feature flags` + backfill `ChannelSession` + `Conversation.thread_id` — aceptación: hilo web iniciado continúa en WhatsApp/Telegram (demo owner).
- [92] `HITL móvil`: `ApprovalCard` → `WhatsApp botones/Flows` + `Telegram InlineKeyboard callback firmado` → `POST /api/approvals/{id}/resolve` → `LangGraph resume` → `SSE` actualiza web — aceptación: supervisor aprueba pago desde móvil <30s, web refleja inmediato.
- [93] `WhatsApp Flows` + `Telegram Mini Apps` hello-world para `formularios` (lead capture `require_lead_capture`, agenda consensual) — aceptación: `GuidedResponse trigger_phrases` funciona sin LLM en móvil.
- [94] Telefonía `LiveKit/Twilio`: `livekit-client/components-react` ya en `package.json:14,35` + `TwilioVoiceCard channels/page` + `livekit-test/page` existentes → cablear `SIP trunk LiveKit` + `make_call/list_recordings` (`routes/twilio.py 7`) + tasación `BillingEvents/min` — pricing doc `Jab solo web-voice, Uppercut $20+min, Knockout 300min incl, Enterprise SIP dedicado` como `saas_addon` — aceptación: llamada test `LiveKit <300ms` + ledger.
- [95] `SignedCanvasLink`: `GET /api/canvas/link?thread_id=` (`JWT 15min`) → `frontend/(public)/canvas/[token]` móvil optimizada (solo `KrofStudioCanvas + ApprovalCard`) — aceptación: usuario WhatsApp abre canvas sin login (solo token) + expira.
- [96] Tests P6: `test_hitl_mobile_approve`, `test_flow_lead_capture`, `test_livekit_metered`, `test_signed_canvas_expires` — aceptación: E2E 3 canales verde en staging.

### FASE P7 — Gobernanza corp + hardening + GA (97-100) — corresponde a Fase 4 doc (resto)

- [97] `Holding` matriz: `models/holding.py (id, name, credit_pool, billing_email)` + `Company.holding_id` + consolidación `MRR/addons/overage` + `CreditPool` transfer — aceptación: conglomerado ve 3 subsidiarias en un panel.
- [98] Contención dept estricta: verificar `company_{id}_dept_{dept_id}` en `Pinecone aikrofy-rag` + `Department.get_pinecone_namespace()` + `Employee.has_web_access` + panel `MessageAudit` auditoría vectorial por dept — aceptación: Finanzas no ve chunks Soporte (test negativo).
- [99] Hardening: `TrustGuardrailService` + `rate-limit` + `BlockedIp/UserIpLog/UserDevice` + `GatewayProvider PADDLE/CUSTOM` fix (hoy `CUSTOM` ref inexistente según `GEMINI.md §7.3`) + `Paddle fuera del factory` fix ([43]) + `CORS screenshot-to-code *` restringir + `audit log` inmutable — aceptación: `pentest` básico + `zap` sin críticos.
- [100] GA checklist: P0-P7 verde + benchmarks (`<0.1ms entitlements`, `0.34ms checkpoint`, `<5ms purga`, `60FPS Brain3D`, `SSE p95`) publicados en `docs/analisis/AGENTIC_OS_GA_REPORT.md` + demo `Micro-PyME / Mediana / Corp` tabla doc + tag `agentic-os-v1.0` + `codebase-memory-mcp ingest_traces` + `manage_adr get` final.

---

## 3. Dependencias / orden / riesgos (v2 — sin ruptura)

**Orden:** `P0 → P1 → P2+P3 (paralelizables tras [37]) → P4 → P5 → P6 → P7`. `P1 [17] RedisSaver` bloquea `P4 [74] interrupt`, `P6 [91-92] HITL`, `P5 [84] Brain3D uniforms`. `P2 [37] Entitlements` bloquea `P3 billing`, `P4 approval pricing`, `P6 telefonía`.

**Riesgos (actualizado Rev.2):**
- `langgraph-checkpoint-redis` incompat Python 3.14 / `langgraph 1.0.10` → mitigar con pin + venv test + fallback `PostgresSaver` (no `MemorySaver`). Estrategia dual-run [17b]: shadow-write Redis 2 semanas, read Memory, luego flip flag.
- `CopilotKit + Next 16 / React 19` breaking → mitigar con `runtime` desacoplado + `SSE` propio como fallback (nuestro `AG-UI` mínimo ya [22]).
- `three/fiber/drei` bundle + 60FPS laptop → mitigar con `Points` (no meshes), `2-5k` partículas, `dynamic import ssr:false`, fallback 2D `LivingBrainCanvas`.
- `Paddle v2/Stripe addons` webhooks idempotencia → mitigar con `BillingEvents event_id` + `ledger` reconciliación diaria + DLQ.
- `Telegram aiogram` vs `webhook FastAPI` threading + `db rollback` (`GEMINI.md §3A`) → mitigar con `OmniBus Celery` (nunca LLM en request) + `primitivizar` antes de LLM.
- `CORS * + credentials True` (`fastapi_app.py:42-46`, `screenshot-to-code/main.py:16`) es incompatible con browsers y riesgo widget — ver §7.1, no cambiar de golpe.
- `deduct_company_credits` no-atómico (check-then-set) + webhooks concurrentes → sobregiro — ver §8 BUG-07, fix con decrement atómico en P3, mientras log-only.

---

## 7. Estrategia anti-ruptura (obligatoria — cómo implementar sin romper nada)

### 7.1 Principios transversales (valen para P1-P7)

1. **Additive-only DB:** solo `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS` vía `backend/scripts/sync_db_schema.py`. Prohibido `DROP/RENAME/ALTER MODIFY` en prod. Cada migración nueva debe ser re-ejecutable y pasar `sync_database_schema(verbose=False)` en boot (`fastapi_app.py:88-95` ya lo hace en background — mantener).
2. **Expand-contract:** primero añadir columna/tabla/servicio nuevo + backfill + dual-read, después (v1.1) deprecar viejo. Aplica a: `MemorySaver→RedisSaver`, `auth_guard→entitlements`, `use-plan-features→useEntitlements`, `billing deduct→ledger`, `LivingBrainCanvas 2D→Brain3D`.
3. **Feature flags (env, default OFF en prod hasta GA por fase):** `REDIS_CHECKPOINT_ENABLED / OMNIBUS_ENABLED / TELEGRAM_V1_ENABLED / ENTITLEMENTS_ENFORCED=log-only→enforcing / ONBOARDING_V2 / GENUI_ENABLED / AGUI_ENABLED / APPROVAL_ENFORCED / BRAIN3D_ENABLED / AXON_ENABLED / LLM_ROUTER_ENABLED / BILLING_V2`. Todo código nuevo debe bifurcar por flag con fallback al comportamiento actual.
4. **Strangler para webhooks:** no reescribir `fastapi_app.py:205-461 whatsapp_webhook_async` de golpe. Extraer `DedupService/ThreadResolver/IdentityResolver` como funciones puras + tests, luego `OmniBus` llama a las mismas. `process_webhook_message` y `process_whatsapp_webhook` (`tasks.py:80-120`) quedan como wrappers que delegan a `omni_bus.handle()` cuando `OMNIBUS_ENABLED=1`.
5. **Entitlements en modo `log-only` primero:** `EntitlementsGuard` loguea `would_block` 1-2 semanas sin devolver `402`. Solo tras matriz verde + dashboards, pasar a `enforcing` por `feature_key` (primero `erp.sync`, `mcp.*`, luego resto).
6. **Billing shadow ledger:** P3 escribe `CreditLedger` + `Company.credit_balance` en paralelo (dual-write), lee `credit_balance` (viejo) hasta reconciliación `SUM(ledger)==balance` 7 días seguidos. Nunca cambiar `deduct_company_credits` firma — añadir `deduct_atomic()` y migrar callers (`trace_path deduct_company_credits`: `agent_service.process_message`, `langgraph_agent.process_message`, `voice_interact`, `chat.*`, `webhooks.*` vía tasks) uno por uno.
7. **GenUI closed-by-default:** `allowlist` inicial = los 8 componentes [70]. Cualquier `{component}` fuera → `400 + log`. Prohibido `dangerouslySetInnerHTML`; mantener `MarkdownRenderer + DOMPurify` (`KrofStudioCanvas.tsx:142-149` ya OK).
8. **Frontend pesado tras `tsc` verde:** `next.config.ts:5 ignoreBuildErrors:true` hoy oculta errores. No quitarlo en prod hasta que `tsc --noEmit` pase en CI. `Brain3D` y `CopilotKit` siempre `next/dynamic ssr:false` + `fallback LivingBrainCanvas/chat actual`.
9. **CORS quirúrgico:** no cambiar `allow_origins=["*"]` global de golpe (rompe `widget.js` embebido `GET /widget.js:63-80` con `Access-Control-Allow-Origin:*`). Plan: mantener `*` solo para `GET /widget.js` + `/api/static/*`, restringir `/api/*` a allowlist `app.aikrofy.com/aikrofy.com/localhost` en P7 [99]. Medir primero qué orígenes reales llegan (log 1 semana).
10. **Secretos con compat:** `SECRET_LICENSE_SALT="aikrofy_asset_shield_sec_2026_wlt_v3"` (`modular_asset.py:16`), `SECRET_KEY/JWT_SECRET_KEY` fallbacks (`config.py:16,26`) → mover a env en P0 [04] pero `verify_license_token()` debe aceptar firma vieja + nueva 6 meses (rotación sin invalidar licencias ZIP ya vendidas).
11. **Redis 6380 sin downtime:** `celery_app.py:24-25` defaultea `6379` pero `ecosystem.config.js:41-42` ya inyecta `6380`. Cambiar default a `6380` es seguro (env lo overridea), pero verificar `screenshot-to-code/`, `api-whatsapp/`, `enpiai-* (6381)` no colisionen. Añadir `redis-cli -p 6380 ping` a `/health`.
12. **PM2 antes de carga nueva:** no añadir `SSE AG-UI / Brain3D stream / UsageAggregator beat 60s` hasta cerrar [01] restarts. `max_memory_restart 500M` + `--workers 2` + `voice transcribe anyio.to_thread` en request (`fastapi_app.py:310`) es sospechoso OOM — mover a Celery en P1 [21] antes de escalar.

### 7.2 Dual-run detallado por cambio riesgoso

| Cambio | Dual-run | Flip | Rollback |
|---|---|---|---|
| MemorySaver→RedisSaver [17] | `get_checkpointer()` devuelve `CompositeSaver(memory+redis shadow-write, read memory)` | `REDIS_CHECKPOINT_ENABLED=1` lee Redis, fallback Memory si miss | `=0` vuelve a Memory, checkpoints Redis quedan huérfanos con TTL 30d, sin pérdida (Memory sigue poblado en caliente) |
| OmniBus [21] | `tasks.process_webhook_message` loguea `omni_equivalent` diff, ejecuta path viejo | `OMNIBUS_ENABLED=1` ejecuta `omni_bus.handle()` | `=0`, DLQ retiene eventos 7d para replay |
| Entitlements [38] | `EntitlementsGuard` `log-only`, header `X-Entitlement-Would-Block` | `ENTITLEMENTS_ENFORCED=1` devuelve `402` | `=log-only`, frontend `UpgradeModal` sigue funcionando como info |
| Billing ledger [58] | `deduct_company_credits` + `ledger.insert` en misma transacción, `balance` sigue mandando | `BILLING_V2=1` lee `ledger` para `get_credit_balance` | `=0`, ledger sigue escribiendo (auditoría) |
| Brain3D [83] | `?brain=3d` opt-in + `prefers-reduced-motion` → 2D | `BRAIN3D_ENABLED=1` default 3D | `=0` o `WebGL fail` → 2D automático |

### 7.3 Qué NO tocar hasta su fase (para no romper)

- No tocar `auth_guard.py` (jerarquía) — crear `entitlements_service.py` aparte. No mezclar `role` con `plan`.
- No tocar `TokenCreditService.calculate_cost_and_credits` fórmula/margen 85% — solo añadir `ModelPricing` filas nuevas + `LLMRouter` que la llama.
- No tocar `CustomerService.save_lid_mapping/resolve_real_phone` ni `wa:raw_jid` cache (`fastapi_app.py:268-292`) — `ThreadResolver` los reutiliza.
- No tocar `proxy.ts` + `api-client.ts` 401-flow en P1-P4 — solo añadir interceptor `402` aparte (nuevo, no modifica `401`).
- No archivar `qrcodly/` físicamente hasta P0 [05] con `git mv` + tag — el grafo `codebase-memory` lo indexa (33k nodos incluyen `qrcodly`, hotspots `Logger/FileUpload` son ruido). Excluir de `search` con `path_filter ^backend/|^frontend/` en auditorías futuras.

---

## 8. Inventario de bugs / deudas para aprovechar (fix oportunista, sin cambiar comportamiento fuera de su fase)

> Severidad: `C`=crítico (bloquea Agentic-OS o corrompe datos), `M`=medio (deuda/observabilidad), `L`=leve. `Fix en` = fase donde se corrige como parte del trabajo ya previsto (cero scope extra).

| ID | Severidad | Dónde (`archivo:línea`) | Síntoma / riesgo | Fix oportunista (sin ruptura) | Fix en |
|---|---|---|---|---|---|
| BUG-01 | M | `backend/celery_app.py:24-25` default `6379` vs prod `6380` | Dev/staging sin env apunta a Redis equivocado; `enpiai 6381` confunde | Cambiar default a `6380`, mantener `os.getenv` override; añadir assert en `/health` | P0 [02] |
| BUG-02 | M | `backend/tasks.py:30,51,86` + `scripts/sync_db_schema.py:34,43` `from app import create_app` con `app.py FlaskMock 27 lín.` | Worker depende de mock; cualquier cambio Flask rompe Celery+RAG+billing | `FastAPIContext` mínimo (`database.engine/db_session` sin Flask), `tasks.py` importa `database`, no `app`; `sync_db_schema` igual | P0 [06] |
| BUG-03 | C | `backend/services/token_credit_service.py:172-206` `deduct_company_credits` check-then-set sin lock, `commit` opcional | Carrera webhooks paralelos → sobregiro / saldo negativo; sin ledger no auditable | Añadir `deduct_atomic(company_id, credits)` con `UPDATE companies SET credit_balance=balance-:x WHERE id=:id AND (credit_balance>=:x OR credit_balance=-1)` + `CreditLedger` shadow; migrar callers `trace_path` uno por uno | P3 [58][59] |
| BUG-04 | M | `backend/fastapi_app.py:42-46` + `screenshot-to-code/backend/main.py:16` `CORS * + allow_credentials True` | Browsers bloquean `*`+credentials; CSRF/exfiltración; `widget.js` sí necesita `*` | Separar: `*` solo `GET /widget.js`, `/api/static/*`; `/api/*` allowlist dominios; log orígenes 1 sem antes | P7 [99] |
| BUG-05 | M | `backend/models/modular_asset.py:16` salt hardcodeado; `backend/config.py:16,26` `dev-secret-key/jwt-secret-key` fallback | Filtración repo = forja licencias/JWT en staging si env falta | Mover a env (`SECRET_LICENSE_SALT`, `SECRET_KEY`, `JWT_SECRET_KEY`), `verify` acepta viejo+nuevo; rotar en prod con ventana | P0 [04] + P2 [44] |
| BUG-06 | M | `frontend/next.config.ts:5` `ignoreBuildErrors:true` | `CopilotKit/R3F/GenUI` romperán en runtime sin aviso; `tsc` hoy rojo oculto | Encender `tsc --noEmit + eslint` en CI (P0 [09]), mantener `ignore` en build prod hasta verde total | P0 [09], P4 [69], P5 [83] |
| BUG-07 | C | `backend/fastapi_app.py:331-349` dedup `content_hash=md5(company:phone:text.lower)` TTL 2s | Dos mensajes iguales legítimos seguidos (<2s, ej. “sí”, “ok”) se dropean como duplicados | Incluir `msg_id + timestamp ms` en hash; ventana 2s solo si `msg_id` igual o `hash+sender+±1500ms`; test `doble POST mismo id=1 ejecución, distinto id=2` | P1 [19] |
| BUG-08 | M | `backend/fastapi_app.py:304-326` transcribe voz `anyio.to_thread` + `os.remove` en request | Bloquea 1 de 2 workers uvicorn 5-20s por nota voz; OOM/restarts [01]; borrado en `finally` puede borrar archivo en uso | Mover `transcribe` a `OmniBus Celery` (P1 [21]); en request solo guarda `attachment.local_path` + `is_voice_pending`; `cleanup_voice_files` beat ya existe | P1 [21][25] |
| BUG-09 | M | `backend/fastapi_app.py:358-441` crea `Conversation+Message(commit)` en webhook sync antes de Celery | DB lenta → webhook timeout → Baileys reintenta → duplicado (aunque dedup ayuda); acopla HTTP a MySQL | Mantener en P1 (necesario para `conv_id`), pero añadir `try/commit` corto + `Celery` idempotente por `conv_id+msg_id`; en P6 evaluar mover a `OmniBus` con `INSERT ... ON DUPLICATE` | P1 [21], P6 [91] |
| BUG-10 | M | `except:` desnudos `decorators.py:47`, `voice_agent.py:97,174`, `voice_service.py:415`, `langgraph_tools.py:1801`, `webhooks.py:1355,1493`, `channels.py:1223` | Tragan `KeyboardInterrupt/MemoryError`, ocultan causa restarts [01] | Reemplazar por `except Exception as e: logger.exception` sin cambiar flujo; prohibir `except:` nuevo vía `rg` en CI | P0 [01][09] |
| BUG-11 | L | `TODOs` `google_service.py:147 timeMin 2020`, `webhooks.py:284 images`, `webhooks.py:766 status`, `channels.py:1318 testing` | Agenda trae 6 años, imágenes ignoradas, `channels test` fake | Fijar `timeMin=now-90d` en `LLMRouter`/`GoogleService` (P5 [86]); `images→[Image Message]` ya OK, en P4 mapear a GenUI `ImageCard`; `channels test` real con `EntitlementsGuard` | P4 [70], P5 [86] |
| BUG-12 | M | `frontend/proxy.ts:34,42 matcher` vs `frontend/lib/api-client.ts:103-120 protectedRoutes` divergentes (`/admin,/channels,/agents...` solo en client) | En `aikrofy.com` sin token, `/admin` no redirige en edge pero sí hace `401→logout` en client → flash/loop | Unificar `protectedPaths` en `lib/auth-paths.ts` único importado por `proxy.ts` + `api-client.ts`; añadir `/admin,/channels,/agents,/analytics,/contacts,/employees,/departments,/documents,/chat,/billing,/onboarding` al matcher | P0 [12] + P2 [39] |
| BUG-13 | M | `frontend/lib/api-client.ts:80-99` retry 200ms + `isRedirectingToLogin` global | Doble 401 paralelo → doble `logout()` + `window.location` race; futuro `402` puede caer en `401` handler | Añadir interceptor `402` separado (no toca `401`), `402→UpgradeModal` sin `logout`; `401` añade `mutex` por `tab_id` | P2 [42] |
| BUG-14 | M | Hotspots complejidad (`channels/page.tsx:67 WhatsAppCard`, `AIChatSidebar 59/depth5`, `langgraph_tools get_tools_for_agent 29/depth7`, `search_ecommerce 49/depth3`, `employees add/update 24/40`) — `query_graph complexity>=20` | Cualquier GenUI/Entitlements tocando esos archivos sin refactorizar propaga bugs; `transitive_loop_depth 5-7` = jank/latencia | Solo extracción pura (split components/funcs sin cambiar firma) dentro de [39][70][85]; `qrcodly/*` excluido (ruido grafo) | P2 [39], P4 [70], P5 [85] |
| BUG-15 | L | `sync_db_schema.py:4` docstring `34+ models` vs real `57/41`; `database.py:59-65 get_db() SELECT 1` + `db_session` doble sesión | Confunde onboarding; `SELECT 1` por request + `scoped_session` paralela = 2 pools | Actualizar docstring a `57/41`; documentar `get_db` (request) vs `db_session` (legacy/tools) sin unificar aún; unificar en v1.1 | P0 [11] |
| BUG-16 | M | `backend/config.py` + `.env.example` obsoletos (`onepunch`, `5000/5001/3001`, sin `GROQ/OPENROUTER/MEDIA/PADDLE/LANGCHAIN/CELERY 6380/TELEGRAM/LIVEKIT`) | Onboarding staging roto, `langgraph-checkpoint-redis` sin var, `LiveKit/SIP` sin creds | P0 [04] cierra; añadir `env doctor` script que falla si falta var por fase (`TELEGRAM_BOT_TOKEN` solo si `TELEGRAM_V1_ENABLED`) | P0 [04] |
| BUG-17 | L | `ENTERPRISE_ONLY_ROLES={cfo,cro}` vs docs 4 roles; `use-plan-features.ts:28-54 DEFAULT vs UNLIMITED` vs backend quotas | `CMO/CTO` gratis por bug o bloqueados por error; `DEFAULT max_agents 1` vs `EnterpriseLimits` inexistente como tabla | P0 [07] unifica a `CMO/CTO/CRO/CFO=enterprise`; P2 [36][46] crea `EnterpriseLimits` tabla + `useEntitlements` wrapper | P0 [07], P2 [36] |
| BUG-18 | M | Triple índice Pinecone `aikrofy-rag/pymai-rag/onepunch-rag` + títulos `PymAI Unified Gateway 2.2.0 / pymai-frontend / whatsapp-api-yt` | RAG escribe en índice equivocado según env; logs confunden depuración PM2 | Alias canónico `aikrofy-rag` lectura+escritura, legacy solo lectura 6 meses; renombrado solo títulos/package `name`, no paths | P0 [03] |

### 8.1 Deudas que NO son bugs (no tocar en este plan)

- `routing.py 484 shim FlaskRequestMock + JWT` — funciona, lo usa `auth_guard` y `skills rollback`. Solo documentar, no reescribir hasta v1.1.
- `database.py:78-102 _resilient_remove` + `fastapi_app.py:99-112 middleware` + `celery_app.py:90-99 task_postrun` — patrón anti-`gone away` ya correcto. Mantener tal cual, `OmniBus` lo reutiliza.
- `MessagingService _via_baileys/_via_meta/_via_twilio + fallback` — sólido, no tocar lógica, solo añadir `Flows/typing/read receipts` detrás de flag.

---

## 9. Readiness / Go-No-Go por fase (además del DoD §5)

**P0 Go:** `tag baseline + pm2 7d <5/día + tsc CI verde (aunque build ignore) + env doctor verde + ADR-001..005`. No-Go si `sync_db_schema` falla en staging o `proxy/api-client` divergen.
**P1 Go:** `kill -9 fastapi` conserva hilo (Redis), `doble POST=1 ejecución`, `Trie p95<5ms`, `SSE curl-N` estable 10min. No-Go si `langgraph-checkpoint-redis` no importa en Python 3.14 o Redis `6380` cae bajo carga voz.
**P2 Go:** `Entitlements log-only` 0 falsos bloqueos 1 sem + matriz `4 planes×12 features` verde + `402` mock → `UpgradeModal` sin `logout`. No-Go si `purga Redis` >5s E2E o sidebar parpadea (caché 30s mal).
**P3 Go:** `SUM(ledger)==balance` 7d + `doble event_id=1 ledger` + `MRR` concilia con Paddle/Stripe mock. No-Go si `deduct_atomic` deadlock bajo concurrencia (probar ` Locust 50 paralelos`).
**P4 Go:** `fuzz component=evil→400` + `CFO sin approve no ejecuta` + `undo revierte` + `SSE alimenta 3 vistas` sin +300ms p95. No-Go si `CopilotKit` rompe `next build` (mantener `SSE` propio como path).
**P5 Go:** `Brain3D 60FPS` laptop + `fallback 2D` si `WebGL fail` + `LLMRouter` usa Claude mock para GenUI. No-Go si bundle `+800KB` sin `dynamic` o GPU >15%.
**P6 Go:** `apruebo desde móvil <30s → web refleja` + `Flows/Inline` E2E + `LiveKit <300ms` tasado. No-Go si `callback_query` sin firma HMAC o `canvas token` no expira.
**P7 Go:** `Finanzas no ve Soporte` (test negativo Pinecone) + `zap` sin críticos + `GA_REPORT` + `tag v1.0`. No-Go si `Holding credit_pool` descuadra o `CORS` restringido rompe `widget.js`.

---

## 4. Estimación (equipo 2 BE + 1 FE + 1 QA, vel. docs reales 26-sep-2026)

- P0: 1.5 sem · P1: 2 sem · P2: 2.5 sem · P3: 1.5 sem · P4: 2.5 sem · P5: 2 sem · P6: 1.5 sem · P7: 1.5 sem = **~15 semanas** hasta GA (con buffers 28-35/49-55/66-68/80-82/89-90 incluidos). Recortar a 10 sem si se difieren `Brain3D shaders full` y `SIP dedicado` a v1.1.

---

## 5. Criterios de aceptación global (Definition of Done 100%)

1. `MemorySaver` 0 referencias prod (`grep` solo `docs/legacy/`).
2. `Entitlements p95 <0.5ms` medido, objetivo `<0.1ms` local, `402` estructurado + `UpgradeModal` sin romper flujo.
3. `Onboarding I_AO/I_PT` configura sidebar + pre-desbloquea módulos tabla doc.
4. `GenUI` solo catálogo auditado, `useCoAgent` bidireccional, `ApprovalCard` + `undo` operativos web/móvil.
5. `Brain3D 60FPS` + `AxonEdge` vesículas mapeadas a 8 estructuras + tabla estados doc.
6. Hilo `(company,user,session)` sobrevive restart y salta web↔WhatsApp↔Telegram + `dedup 2s` + `Trie 3ms`.
7. `MRR = base + Σ addons + Σ overage` conciliado, `AssetLicense HMAC` SaaS+ZIP, purga `<5s` UI.
8. `Holding` + `dept_{id}` aislamiento + `MessageAudit` panel verde.
9. `pm2 restarts` estables, `grep pymai|onepunch|6379` limpio, CI verde, i18n 5/5, `sync_db_schema` sin `1054`.
10. `AGENTIC_OS_GA_REPORT.md` + tag `agentic-os-v1.0`.
11. **Rev.2:** §7 anti-ruptura cumplido (flags + dual-run + additive-only), §8 BUG-01..18 cerrados o con waiver, §9 Go por fase firmado.

---

## 6. Próximo paso inmediato (para arrancar mañana — sin tocar código hoy)

1. Ejecutar `[00][01][10][14]` (baseline + PM2 + ADR + benchmarks) + `env doctor` + `rg "except:$" backend/` baseline.
2. Crear rama `feat/agentic-os-p1-redis-checkpoint` + instalar `langgraph-checkpoint-redis` en staging (`[16][17]` con `CompositeSaver` dual-run §7.2).
3. Crear rama `feat/entitlements-runtime` en paralelo (`[36][37]` en `log-only`, no tocar `auth_guard.py`).

> Este plan es el único backlog válido para Agentic-OS. Si un `.md` legacy lo contradice, este plan + `GEMINI.md` ganan. **Rev.2 2026-10-01: revisión anti-ruptura completa, 0 cambios de código, listo para ejecución.**

