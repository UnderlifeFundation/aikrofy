# ESTRUCTURA_PROYECTO — Mapa Definitivo del Repositorio Aikrofy (V4.0)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.**
**Repo:** `/root/aikrofy` · rama `dev` (`897578d` al 26-sep-2026) · **Consolidado:** 26-sep-2026 desde auditoría real.
**Lectura sugerida:** `README.md` → este archivo → `GEMINI.md`/`AGENTS.md` → `COMPENDIO_MAESTRO_AIKROFY.md` → `docs/`.

> Cifras verificadas por lectura directa (`ls`, `rg`, `pm2 list`, `ss -tlnp`, grafo `root-aikrofy`: 10 598 nodos / 31 320 aristas). Lenguajes: Python 270 ficheros · TypeScript 205 · HTML 17 · JS 6 · Bash 6 · YAML 5.

---

## 1. Raíz `/root/aikrofy/` (50 entradas)

| Entrada | Qué es | Puerto / nota |
|---|---|---|
| `backend/` | API FastAPI + Celery + 57 tablas + 96 servicios + ~335 endpoints | `:5010` + worker |
| `frontend/` | App PyME Next.js 16/React 19, 52 páginas, 5 idiomas | `:3010` |
| `api-whatsapp/` | Microservicio Baileys/Venom/Twilio, 22 ficheros `src/` | `:3011` (código defaultea 3001) |
| `screenshot-to-code/` | Motor de landing pages (FastAPI sin docs) | `:5015` |
| `templates/blog-template-blank/` | Plantilla LEGO Blog Agéntico Next.js (admin, api ai/posts/webhook, `lib/license-shield.ts`, `seed_ecuador_posts.py`) | desacoplado, ref VPS cliente :3020 |
| `routes/channels.py` | Legacy (1 fichero; real en `backend/routes/`) | archivar |
| `services/{langgraph_tools,whatsapp_service}.py` | Shims legacy (real en `backend/services/`) | archivar |
| `qrcodly/` | **Vacío** — placeholder muerto | eliminar/archivar |
| `uploads/` | Skills sincronizadas `skills/company_<id>/…`, voz, media | runtime |
| `ecosystem.config.js` | **6 apps PM2** (redis, frontend, fastapi×2 workers, worker, whatsapp, landing-gen) | ver §5 |
| `deploy.sh`, `start-local.sh`, `stop-local.sh`, `fix-python.sh` | Operativa (deploy corre sync schema) | — |
| `nginx-custom-domains.conf` | Dominios custom landings (CNAME) | 80/443 |
| `.env.example`, `backend/.env(.example/.save*)` | ⚠️ obsoletos (`onepunch`, puertos viejos) | actualizar |
| `dump.rdb` | Snapshot Redis local | runtime |
| `*.md` raíz (4 definitivos) | `README.md`, `GEMINI.md`, `AGENTS.md`, `ESTRUCTURA_PROYECTO.md`, `COMPENDIO_MAESTRO_AIKROFY.md`, `ESTADO_ACTUAL_PROYECTO.md` | este orden |
| `docs/` **(nuevo)** | `planes/`, `integraciones/`, `analisis/`, `legacy/` (archivo de los 22 .md históricos) | ver §6 |

---

## 2. `backend/` (69 entradas) — núcleo `:5010`

- **Entry:** `fastapi_app.py` (título interno `PymAI Unified Gateway v2.2.0`, monta 38 routers legacy + `attributions/skills/mcp/v1/agents/v1/knowledge`, webhook WhatsApp async :205-461, `/health`, `/api/v2/test`) · `fastapi_routes_loader.py:59-99` (38 routers `/api/*`) · `fastapi_routers.py` (377 lín.: auth register/login/me + ERP platforms/config/test/disconnect) · `routing.py` (484 lín. shim) · `app.py` (`FlaskMock` 27 lín.) · `config.py` (DATABASE_URL>MYSQL_*>sqlite, Pinecone `aikrofy-rag`, Redis 6380, Paddle/Media/Celery) · `database.py` (pool + `_resilient_remove`) · `extensions.py`, `decorators.py` · `celery_app.py` (beat 4) · `tasks.py` (1038 lín., 12 tasks) · `requirements.txt` (ver `GEMINI.md §2.1`) · `sync_db.py` + `scripts/sync_db_schema.py` · `seed_*.py` (crm_metrics, enterprise_crm×2, paddle_tokens, paypal_plans, plans, platform_agent, dlocal) · `migrate_*/upgrade_*/setup_*/check_*` · `voice_agent.py`, `voice_tools.py` · `aIkb.db` residual 12KB + `instance/` (solo fallback dev) · `BOS-AI/` handbooks · `static/`, `templates/`, `uploads/`, `docs/`, `scratch/`, `migrations/`, `alembic.ini`.
- **`models/` — 41 ficheros / 57 tablas:** `AgencyCompanyAccess`, `Agent`, `AgentFeature`, `PredefinedMetric`, `UserDashboard`, `DashboardWidget`, `Appointment`, `BetaLead`, `CampaignQRCode`, `QRCodeScanEvent`, `Channel`, `Company`, `CompanyAgentGraph`, `CompanyCampaign`, `CompanySkill`, `ContactAttribution`, `WebReferralSession`, `Conversation`, `Message`, `CRMConfig`, `Customer`, `Department`, `Document`, `DynamicAction`, `EcommerceConfig`, `EmailLog`, `Employee`, `ERPConfig`, `FunnelStage`, `GuidedResponse(+Action)`, `UserIpLog`, `BlockedIp`, `UserDevice`, `LandingPage(+Version/Visit/Element/CustomDomain)`, `CompanyMCPServer`, `CompanyMediaAsset`, `MessageAudit`, `ModularAsset`, `AssetLicense`, `Note`, `PaymentGatewayConfig`, `PaymentTransaction`, `PlatformConfig`, `PurchasedNumber`, `Plan`, `Subscription`, `TenantScoringConfig`, `Transaction`, `TrustGuardrail`, `User`, `WhatsAppTemplate`, `WhatsAppLidMapping`.
- **`routes/` — 45 ficheros / ~335 endpoints:** `admin, agency, auth, beta, billing, chat, companies, crm, departments, ecommerce, employees, enterprise, funnel_live, hubspot, knowledge_graph, landing_pages (24), media, meetings, marketplace, mcp (6), payment_gateways (7), payments (6), rag (16), skills (9), telemetry, twilio (7), v1/agents, v1/knowledge, voice, webhooks (13), whatsapp_templates, channels (17), agents (11), campaigns_qr (11)` + nativos.
- **`services/` — 96 ficheros (57 top-level):** `langgraph_agent` (1087), `agent_service`, `krof_agent`, `skill_service`, `graph_compiler`, `dynamic_tools`, `mcp_service`, `rag_service` (394), `llm_service`, `cache_service`, `auth_cache_service`, `token_credit_service`, `lead_scoring`, `lead_heap`, `crm_trie`, `analytics_vector`, `autonomous_consciousness`, `trust_guardrail`, `brain_events`, `handover`, `escalation`, `employee_detection`, `ip_security`, `customer`, `transaction`, `attribution`, `geo_analytics`, `sentiment`, `voice_service`, `livekit`, `realtime`, `meeting`, `media`, `pdf`, `landing_generation`, `website_crawler`, `ingestion`, `dlocal_go`, `paddle`, `paypal`×2, `messaging`, `whatsapp_baileys`, `meta_whatsapp`, `meta_template`, `twilio`, `email`, `google`, `google_risc`, `hubspot_sync` + `crm/` 9 (base, factory, hubspot, salesforce, zoho, pipedrive, dynamics, mapper, canonical) + `erp/` 5 + `drivers/` 6 (sap_b1, netsuite, odoo, dynamics_bc, contifico, mysql) + `ecommerce/` 7 (shopify, woocommerce, magento, bigcommerce, vtex, prestashop) + `payment_gateways/adapters/` 8 (stripe, paypal, mercadopago, kushki, nuvei, dlocal_go, authorize_net, custom).
- **`integrations/` — 2:** `calendar.py` (`GoogleCalendarIntegration`), `google_sheets.py`.

## 3. `frontend/` (:3010) — app PyME operativa

- **Raíz:** `package.json` (`pymai-frontend 0.1.0`, ~44 deps: next 16.1.6, react 19.2.3, tailwind4, shadcn/radix, zustand5, react-query5, axios, RHF+zod, framer-motion, lucide, recharts, d3, leaflet, grid-layout, xyflow, qr-code-styling, sonner, next-themes, markdown, google-oauth, js-cookie, i18next, socket.io-client, livekit, paypal) · `next.config.ts` (`ignoreBuildErrors:true`, webp/avif, cache headers) · `proxy.ts` (guard `access_token`, split `app.aikrofy.com`/`aikrofy.com`) · `.env*` (`NEXT_PUBLIC_API_URL=https://api.aikrofy.com/api`, alt `aikrofy.weblifetech.com/api`).
- **`app/` — 52 `page.tsx`:** `(auth)/login,register` · `(dashboard)/dashboard,chat,agents/{page,org,playground},admin/{dashboard,beta,billing,documents,geo-analytics,platform-agent},admin-chat,agency,analytics,campaigns,channels,contacts/{page,[id]},departments,developer,documents/{page,brain},employees,feedback,funnel,landing-pages/{page,[id]},livekit-test,marketplace,media,onboarding,pricing,settings/{page,crm,ecommerce,erp,mcp,payments},subscribe,templates,wellness,activate-trial` · `(public)/beta-register,chat/[slug],evaluate/[company_id],privacy,refunds,terms` · `agency/authorize,api/credits/capture,layout,page,providers,globals.css,error/global-error/loading`.
- **`components/` 66:** `HubSpotChatWidget`, `admin/AdminGeoMap`, `analytics/`, `campaigns/`, `chat/{ChatChartWidget,KrofStudioCanvas,omnichannel/}`, `features/`, `onboarding/`, `shared/`, `ui/` (24 shadcn) · **`store/` 2** (`use-auth-store`, `use-onboarding-store`) · **`services/` 2** (`channels-service`, `whatsapp-templates-service`) · **`lib/` 5** (`api-client`, `device-telemetry`, `i18n`, `use-living-brain`, `utils`) · **`hooks/` 2** (`use-permissions`, `use-plan-features`) · **`types/index.ts`** · **`locales/{de,en,es,fr,pt}/`** (5 idiomas) · `FRONTEND_GUIDE.md` obsoleto (PunchAI/Next14) → `docs/legacy/`.

## 4. `api-whatsapp/` (:3011) · `screenshot-to-code/` (:5015)

- ~~**App Enterprise separada** (`:3012`):~~ **eliminada el 26-sep-2026** — era landing de 3 ficheros sin tráfico (nginx no exponía :3012, sin DNS, sin refs en backend/frontend). El plan `enterprise` se sirve por `plan_type` en `frontend/` :3010.
- **WhatsApp:** `package.json` (`whatsapp-api-yt`, baileys 6.7.8 + venom + web.js + twilio 3.80, express 4.18, mysql2, DI) · `src/` 22: `app.ts` (cors/json/static tmp, `PORT‖3001`), `application/lead.create.ts`, `domain/lead*.ts`, `infrastructure/{auth/mysql.auth,database/connection,ioc,controller/{lead,session}.ctrl,repositories/{baileys,meta,mock,twilio,venom,ws.external},router/{index (carga dinámica),lead.route,session.route}}` · `dist/`, `qr_codes/`, `tmp/`.
- **Landing-gen:** `screenshot-to-code/backend/main.py` (FastAPI sin docs, CORS `*`, routers screenshot/generate_code/home/evals) + `routes/`, `codegen/`, `prompts/`, `models/`, `llm.py`, `config.py`, `image_generation/`, `image_processing/`, `video/`, `ws/`, `evals/`, `tests/`, `pyproject/poetry.lock`.

## 5. Producción PM2 + red

`ecosystem.config.js` → 6 apps, todas `online` 26-sep-2026: `aikrofy-redis :6380` · `aikrofy-frontend :3010` (⚠️849 restarts/6D) · `aikrofy-fastapi :5010 --workers 2` (⚠️248/2D, `max_memory_restart 500M`) · `aikrofy-worker` (⚠️138/2D, broker 6380/0) · `aikrofy-api-whatsapp :3011` (80/2D) · `aikrofy-landing-gen :5015 ×2`. Red: `3306 mariadbd`, `80/443 nginx` (+`nginx-custom-domains.conf`), cohabita `enpiai-*` (5000/3000/3001/6381). Comandos: `pm2 status|logs|restart <name>`.

## 6. Documentación (`docs/` — archivo de los 22 .md históricos)

| Carpeta | Contenido (origen raíz → destino) |
|---|---|
| `docs/planes/` | `PLAN_INNOVACION_AIKROFY.md`, `PLAN_DE_INTEGRACION_HUBSPOT.md`, `ANALISIS_RENTABILIDAD_TOKENS_CREDITOS.md`, `ANALYSIS_AND_COPY_STRATEGY.md` (futuro/negocio, jul-2026) |
| `docs/integraciones/` | `Integracion-Avanzada-de-Twilio.md`, `Integracion-ERP.md`, `Integracion-Pasarelas-de-Pago.md`, `Integración-CRM.md`, `Integracion-de-Calendarios-para-Agentes.md` (specs; calendarios es la más reciente, sep-2026) |
| `docs/analisis/` | `ANALISIS_SISTEMA_COMPLETO.md` (radiografía citada por AGENTS, conservar como anexo), `INFORME_ESTRUCTURAS_DATOS_AIKROFY.md`, `AUDITORIA_FINAL_ESTRUCTURAS_Y_DATOS_AIKROFY.md` (evidencia), `Analisis_y_Diseno_CRM_Conversacional.md` (jun-2026), `research_ecommerce.md` (may-2026, previo a `services/ecommerce/`) |
| `docs/legacy/` | `PROJECT_STATUS_REPORT.md`, `AIKROFY_ARQUITECTURA_DETALLADA.md` (duplicados fusionados), `ARQUITECTURA_API_FIRST.md` (fusionado, conservar ref), `CATALOGO_API_MCP.md` (fusionado), `GUIA_IMPLEMENTACION_VOZ.md` (fusionada), `PLAN_IMPLEMENTACION_ESTRUCTURAS_AIKROFY.md` (ejecutado), `INTERFAZ_ENTERPRISE.md` (desfasada), `SKILL_Agentic-Engineering-Protocol_IAGS.md` (filosofía absorbida), `frontend/FRONTEND_GUIDE.md`, shims raíz |

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH. Auditoría real: 26-sep-2026.**
