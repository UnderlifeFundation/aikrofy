# 🔍 Radiografía Completa y Análisis del Sistema — Plataforma Aikrofy (V3.0)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

Este documento representa la radiografía técnica definitiva y exhaustiva de todo el ecosistema de software **Aikrofy** (`aikrofy.com`) y **Aikrofy Enterprise**. Cubre el 100% de los módulos, base de datos relacional (34 modelos), base de datos vectorial con namespaces jerárquicos y departamentales, servicios cognitivos (45 servicios), rutas API (32 módulos de rutas), herramientas de LangGraph, capa de aceleración de las **8 Estructuras de Datos Fundamentales**, integraciones corporativas y la infraestructura de Model Context Protocol (MCP).

---

## 🗺️ 1. Lógica General y Arquitectura Multi-Tenant

Aikrofy opera como una plataforma agéntica B2B SaaS Multi-tenant y una Junta Directiva Virtual de **7 Chiefs** coordinada por el copiloto inteligente **Krof**. Su núcleo reside en aislar lógicamente los datos de cada inquilino mediante la columna `company_id` en las bases de datos relacionales y la separación por `namespaces` en las bases vectoriales (incluyendo contención por departamento `company_{id}_dept_{dept_id}`).

* **Pila Tecnológica:**
  - **Backend**: FastAPI (Python 3.14 / ASGI) + Celery (Broker en Redis puerto `6380`) + SQLAlchemy 2.0 (MySQL/MariaDB) + Pinecone v5.0+.
  - **Canales de Entrada**: Microservicio de WhatsApp en Node.js (puerto `3011`) con `@whiskeysockets/baileys` nativo, Webchat, Telegram, Email transaccional, llamadas Twilio / LiveKit SIP.
  - **Frontends**: Next.js 16 / React 19. Aikrofy en puerto `3010` (PyME) y Aikrofy Enterprise en puerto `3012` (Dark Glassmorphism).
  - **Aceleración de Datos**: Capa in-memory de 8 estructuras de datos para resolver búsquedas, autenticación y telemetría en microsegundos ($<0.1\text{ms}$).

---

## 🗄️ 2. Directorio Exhaustivo de Modelos de Base de Datos (`backend/models/` - 34 Modelos)

Todos los modelos heredan de la configuración unificada de SQLAlchemy 2.0 y soportan relaciones directas y multi-tenancy:

1. **`agent.py`**
   - `Agent`: Identidad del agente, nombre, género (`AgentGender`), tono de voz (`AgentTone`), objetivo principal (`AgentObjective`), prompts de sistema fijos y voz neural asignada.
   - `AgentFeature`: Toggles de características vinculadas al agente (Voz, Pagos, Agenda, RAG, CRM, E-commerce).
2. **`analytics_dashboard.py`**
   - `PredefinedMetric`: Métricas del sistema con plantillas SQL nativas seguras para cálculo de CAC, LTV, MRR y conversiones.
   - `UserDashboard`: Tableros personalizados por cada administrador o usuario.
   - `DashboardWidget`: Widgets configurables en cuadrícula para telemetría y gráficos interactivos.
3. **`appointment.py`**
   - `Appointment`: Historial de citas registradas por los agentes, ligadas a un `Customer` y a un `Channel`. Contiene la URL de Google Meet generada y la zona horaria del cliente.
4. **`beta_lead.py`**
   - `BetaLead`: Registro de leads y solicitudes tempranas para el programa beta y listas de espera.
5. **`channel.py`**
   - `Channel`: Canales configurados (`ChannelType`: WhatsApp, Webchat, Telegram, LiveKit, Twilio) y su estado operacional (`ChannelStatus`).
6. **`company.py`**
   - `Company`: Entidad inquilina raíz. Define saldo de créditos (`credit_balance`), plan (`plan_type`: `pyme`, `enterprise`, `enterprise_plus`), BYOK (llaves propias), idioma por defecto, cuotas (`max_departments`, `max_employees`) y API Key pública.
7. **`company_campaign.py`**
   - `CompanyCampaign`: Promociones y campañas dinámicas temporales que se inyectan en alta prioridad en el System Prompt de los agentes.
8. **`company_skill.py`**
   - `CompanySkill`: Arquitectura de prompts modulares y habilidades dinámicas en caliente. Almacena bloques de prompts (`system_prompt_block`), versión (`version`), prioridad y herramientas requeridas.
9. **`contact_attribution.py`**
   - `ContactAttribution`: Datos UTM e identificadores de campañas Click-to-WhatsApp (CTWA / `ctwa_clid`).
   - `WebReferralSession`: Mapeo para conversiones offline correlacionando el identificador `GCLID` con números telefónicos del chat.
10. **`conversation.py`**
    - `Conversation`: Sesiones de chat omnicanal con marcas de resolución (`is_resolved`), canal y cliente asignado.
    - `Message`: Transcripciones individuales de mensajes asociados a un rol (`MessageRole`: user, assistant, system, tool).
11. **`crm_config.py`**
    - `CRMConfig`: Llaves de acceso y mapeos de HubSpot, Salesforce, Zoho, Pipedrive y Dynamics.
12. **`customer.py`**
    - `Customer`: Ficha CRM del cliente. Contiene nombre, email, teléfono, rol de compra (`buying_role`) y puntuación acumulada de Lead Scoring (`lead_score`).
13. **`department.py`**
    - `Department`: Sub-contenedor organizacional para empresas Enterprise. Proporciona aislamiento RAG vectorial (`get_pinecone_namespace()`), asignación de empleados y cuotas departamentales.
14. **`document.py`**
    - `Document`: Metadatos e indexación de archivos RAG subidos para Pinecone, con soporte para `department_id`.
15. **`ecommerce_config.py`**
    - `EcommerceConfig`: URL de tienda y credenciales (Shopify, WooCommerce, VTEX, Magento, PrestaShop, BigCommerce).
16. **`email_log.py`**
    - `EmailLog`: Historial de correos transaccionales enviados por la IA.
17. **`employee.py`**
    - `Employee`: Registro de personal de la empresa inquilina. Incluye `department_id`, asignación a `user_id` y bandera `has_web_access` para control de acceso al dashboard.
18. **`erp_config.py`**
    - `ERPConfig`: API endpoints y credenciales de Odoo, SAP Business One y NetSuite.
19. **`funnel_stage.py`**
    - `FunnelStage`: Definición de etapas Kanban del CRM.
20. **`guided_response.py`**
    - `GuidedResponse`: Respuestas guiadas pre-aprobadas para interceptar alucinaciones y disparar acciones automáticas.
21. **`ip_tracking.py`**
    - `IPTracking`: Auditoría de seguridad por IP, geo-localización, detección de anomalías y consentimiento de ubicación.
22. **`landing_page.py`**
    - `LandingPage`: Metadatos del generador de landing pages por IA.
    - `LandingPageVersion`: Historial de código HTML/CSS generado para rollback.
    - `LandingPageVisit`: Eventos de telemetría (país, navegador, conversiones).
    - `LandingPageCustomDomain`: Registro de dominios corporativos vinculados por CNAME.
23. **`mcp_config.py`**
    - `CompanyMCPServer`: Direcciones HTTP/SSE de servidores MCP remotos para inyección dinámica de herramientas.
24. **`message_audit.py`**
    - `MessageAudit`: Registro contable que asocia cada mensaje de la IA con los fragmentos vectoriales exactos de Pinecone utilizados en el RAG.
25. **`note.py`**
    - `Note`: Notas internas de agentes y colaboradores sobre prospectos y clientes.
26. **`payment_gateway.py`**
    - `PaymentGatewayConfig`: Configuración multitenant de pasarelas de pago (PayPal, Stripe, dLocal, MercadoPago).
    - `PaymentTransaction`: Libro contable inmutable de transacciones conversacionales.
27. **`platform_config.py`**
    - `PlatformConfig`: Parámetros globales de la plataforma, feature flags del sistema y configuraciones maestras.
28. **`purchased_number.py`**
    - `PurchasedNumber`: Inventario y asignación de números telefónicos virtuales (Twilio/LiveKit SIP) adquiridos por la empresa.
29. **`subscription.py`**
    - `Plan`: Planes tarifarios del SaaS (`pyme`, `enterprise`, etc.) integrados con Paddle Billing v2.
    - `Subscription`: Historial y estado de facturación de cada empresa inquilina.
30. **`tenant_scoring_config.py`**
    - `TenantScoringConfig`: Ponderaciones de Lead Scoring personalizadas ($w_{\text{ML}}$ y $w_{\text{Manual}}$) por empresa.
31. **`transaction.py`**
    - `Transaction`: Transacciones financieras registradas durante los flujos de cobro en chat.
32. **`user.py`**
    - `User`: Usuarios administrativos con contraseñas cifradas (bcrypt), roles (`Admin`, `Manager`, `Agent`, `Superadmin`) y tokens de sesión.
33. **`whatsapp_template.py`**
    - `WhatsAppTemplate`: Plantillas oficiales de Meta WhatsApp aprobadas para mensajes fuera de la ventana de 24 horas.

---

## ⚙️ 3. Biblioteca y Catálogo de Herramientas de IA (`backend/services/langgraph_tools.py`)

LangGraph inyecta dinámicamente estas herramientas (`@tool`) al bucle de razonamiento ReAct:

### 📖 3.1. RAG y Memoria
* **`consult_knowledge_base(query: str) -> str`**: Consulta el espacio vectorial Pinecone del inquilino (`company_id` o `company_{id}_dept_{dept_id}`) combinado con el namespace global de handbooks de BOS-AI (`company_id=None`). Realiza `db.session.rollback()` previo y audita los chunks en `MessageAudit`.

### 💡 3.2. Gestión de Habilidades y Agentes
* **`agent_list_skills() -> str`**: Retorna las habilidades dinámicas activas (`CompanySkill`) de la empresa.
* **`agent_create_or_update_skill(...) -> str`**: Inserta o actualiza un prompt modular en MySQL y sincroniza en caliente el archivo `uploads/skills/company_<id>/<skill_name>/SKILL.md`.
* **`agent_create_new_agent(...) -> str`**: Registra una nueva identidad de agente en MySQL con sus canales y características.
* **`agent_delete_agent(agent_id: int) -> str`**: Elimina el agente de la base de datos.

### 👤 3.3. CRM Interno y Registro
* **`lookup_customer(query: str) -> str`**: Busca prospectos por nombre, teléfono o email usando el acelerador de prefijos Trie ($O(L)$).
* **`register_customer(...) -> str`**: Registra o actualiza un contacto, recalcula su lead score con ML y sincroniza con HubSpot/Salesforce en tiempo real.

### 💳 3.4. Pagos y Transacciones
* **`paypal_create_order(amount: float, currency: str, description: str, customer_id: int) -> str`**: Registra la transacción pendiente en MySQL y genera la orden en la API REST v2 de PayPal.
* **`paypal_capture_order(order_id: str) -> str`**: Captura y valida fondos, actualiza a `COMPLETED` y auto-resuelve la conversación.
* **`paypal_get_order(order_id: str) -> str`**: Consulta el estado de la orden.

### 📞 3.5. Comunicaciones y Telefonía
* **`send_whatsapp(to: str, message: str) -> str`**: Despacha mensaje vía microservicio Baileys (puerto `3011`) o Twilio Messaging.
* **`send_email(to: str, subject: str, body: str) -> str`**: Envía correos Markdown a HTML, descuenta 1 crédito y registra en `EmailLog`.
* **`make_call(to: str, purpose: str) -> str`**: Dispara llamada saliente mediante LiveKit SIP o Twilio Voice.

### 📅 3.6. Calendario y Disponibilidad
* **`schedule_appointment(...) -> str`**: Conversión de zona horaria con `pytz`, creación de evento en Google Calendar con Google Meet y registro en `Appointment`.
* **`check_availability(date: str, client_timezone: str, preferred_time: str) -> str`**: Consulta bloques ocupados en Google Calendar y calcula ranuras libres sugeridas.

### ⚙️ 3.7. Integraciones Corporativas CRM y ERP
* **`crm_get_contact` / `crm_create_contact` / `crm_update_contact`**
* **`crm_get_lead` / `crm_create_lead` / `crm_create_deal`**
* **`search_ecommerce_products` / `check_ecommerce_stock` / `create_ecommerce_order`**
* **`erp_query_records` / `erp_get_invoice` / `erp_create_customer`**

### 🌐 3.8. Co-Browsing, Navegación Web y Analítica Visual
* **`navigate_website(url_path: str)`**: Dirige la vista del usuario en el frontend a una sección específica (`/agents`, `/channels`, `/pricing`).
* **`scroll_website_page(direction: str, pixels: int)`**: Realiza scroll programático guiado en la interfaz.
* **`change_language(language_code: str)`** / **`change_website_language(language_code: str)`**: Conmuta instantáneamente el idioma de la plataforma (`es`, `en`, `pt`).
* **`change_website_theme(theme: str)`**: Alterna entre tema claro (`light`) y oscuro (`dark`).
* **`highlight_website_element(selector: str, message: str)`**: Resalta elementos del DOM para guiar al usuario visualmente.
* **`get_analytics_summary` / `get_analytics_time_series` / `get_detailed_analytics_breakdown`**: Consultas analíticas y de embudo.

### 🛡️ 3.9. Herramientas de Administración Krof (Tier 3 Admin Copilot)
Solo ejecutables por administradores y personal autorizado (`is_employee=True` y roles de gestión):
* **`agent_create_new_agent` / `agent_delete_agent` / `agent_update_configuration` / `agent_toggle_feature`**: Control integral del ciclo de vida de los agentes.
* **`department_create_or_update` / `department_list`**: Creación y asignación de departamentos y namespaces RAG.
* **`landing_page_list` / `landing_page_create` / `landing_page_update_content` / `landing_page_modify_design` / `landing_page_publish_toggle` / `landing_page_delete` / `landing_page_seo_update`**: Generación, edición CSS/HTML y publicación de landings.
* **`blog_create_article` / `blog_modify_style` / `blog_sync_mediasuite`**: Creación agéntica de artículos de blog enriquecidos con imágenes Pexels desde `media.weblifetech.com`.
* **`channel_get_status`**: Diagnóstico de salud de canales (WhatsApp, Webchat, LiveKit).
* **`billing_get_account_balance` / `billing_create_recharge_link`**: Consulta y recarga de saldo de combustible IA.
* **`crm_pipeline_summary` / `crm_add_activity_note`**: Gestión rápida del embudo comercial.
* **`agency_list_clients`**: Supervisión de cartera de empresas para cuentas de Agencia.

---

## 🧠 4. Capa de Servicios y Algoritmos Avanzados (`backend/services/` - 48 Módulos de Servicio)

1. **`agent_service.py`**: Gestión integral del ciclo de vida de los agentes y sus configuraciones.
2. **`analytics_vector_service.py`**: Motor de aceleración con Typed Arrays (NumPy Float64) para métricas de CAC, LTV, MRR y ROI a 60 FPS.
3. **`attribution_service.py`**: Captura y análisis de atribución UTM y Click-to-WhatsApp.
4. **`auth_cache_service.py`**: In-Memory Hash Map Cache ($O(1)$) para validación de `X-API-Key` y permisos en $<0.1\text{ms}$.
5. **`auth_guard.py`**: Motor de jerarquía y autorización estricta para operaciones administrativas.
6. **`cache_service.py`**: Servicio centralizado de caché Redis / Memoria.
7. **`crm/`**: Submódulos de conectores CRM empresariales (HubSpot, Salesforce, Zoho, Pipedrive).
8. **`crm_trie_service.py`**: Prefix Tree Trie ($O(L)$) para autocompletado en $3\text{ms}$ en búsquedas de contactos y empresas.
9. **`customer_service.py`**: Operaciones CRUD y consolidación de perfiles de clientes.
10. **`dlocal_service.py`**: Integración con la pasarela de pagos dLocal Go.
11. **`email_service.py`**: Envío de correos transaccionales y resúmenes SMTP.
12. **`employee_detection_service.py`**: Detección de personal interno y resolución de namespaces RAG por departamento.
13. **`enterprise_limits.py`**: Control y cumplimiento de cuotas de departamentos y empleados según el plan de la empresa.
14. **`erp/`**: Adaptadores ERP para SAP Business One, Odoo y Oracle NetSuite.
15. **`escalation_service.py`**: Protocolo de derivación a agentes humanos y alertas de soporte.
16. **`geo_analytics_service.py`**: Análisis geográfico y telemetría de tráfico por país/región.
17. **`google_risc_service.py`**: Monitoreo de eventos de seguridad RISC de Google.
18. **`google_service.py`**: Conectores oficiales con Google Calendar API y Google Sheets API.
19. **`hubspot_sync_service.py`**: Sincronización bidireccional en tiempo real con HubSpot Conversations.
20. **`ip_security_service.py`**: Filtrado de IPs maliciosas, extracción de cliente real y telemetría geográfica.
21. **`krof_agent_service.py`**: Orquestación directa del copiloto agéntico Krof, plantillas de correo HTML dinámicas.
22. **`landing_generation_service.py`**: Generación automática de landing pages mediante IA con modelos GPT-5 Nano / personalizados.
23. **`langgraph_agent.py`**: StateGraph asíncrono ReAct con memoria de ventana deslizante $O(1)$ y ruteo entre 7 Chiefs.
24. **`langgraph_state.py`**: Esquema de estado tipado de LangGraph (`AgentState`).
25. **`langgraph_tools.py`**: Registro completo de 48 herramientas invocables por la IA con permisos por rol y plan.
26. **`lead_heap_service.py`**: Max-Heap Priority Engine ($O(1)$ Top) para priorización instantánea de leads para ventas.
27. **`lead_scoring_service.py`**: Motor de puntuación híbrido (ML + Reglas manuales) para prospectos.
28. **`livekit_service.py`**: Generación de tokens WebRTC y salas de audio en tiempo real (<300ms).
29. **`llm_service.py`**: Factoría unificada de clientes LLM (OpenAI, Groq, OpenRouter, Anthropic).
30. **`mcp_service.py`**: Cliente y adaptador de servidores Model Context Protocol remotos (HTTP/SSE).
31. **`messaging_service.py`**: Enrutador universal de mensajería omnicanal.
32. **`meta_template_service.py`**: Gestión y sincronización de plantillas oficiales de WhatsApp con Meta API.
33. **`meta_whatsapp_service.py`**: Conector directo con la API Cloud de WhatsApp de Meta.
34. **`ml_scoring_pipeline.py`**: Pipeline de re-entrenamiento ligero de modelos ML para predicción de compras.
35. **`paddle_service.py`**: Gestión de suscripciones, cobros recurrentes y validación de webhooks con Paddle Billing v2.
36. **`payment_gateways/`**: Adaptadores unificados de pasarelas de pago (PayPal, Stripe, dLocal).
37. **`paypal_service.py`**: Facturación y captura de órdenes vía PayPal REST API v2.
38. **`paypal_toolkit.py`**: Utilidades y serializadores de transacciones PayPal.
39. **`pdf_service.py`**: Extracción y parsing de documentos PDF para ingesta RAG.
40. **`permission_service.py`**: Control de acceso basado en roles (RBAC) con presets y validaciones en $O(1)$.
41. **`rag_service.py`**: Chunking, embeddings e indexación vectorial multi-namespace en Pinecone.
42. **`realtime_service.py`**: Transmisión de eventos WebSocket y Socket.io para dashboards en vivo.
43. **`sentiment_service.py`**: Análisis de sentimiento en tiempo real sobre mensajes entrantes.
44. **`skill_service.py`**: Ensamblaje dinámico de prompts en caliente y sincronización con MySQL y filesystem.
45. **`token_credit_service.py`**: Tarificación precisa de tokens LLM, minutos STT y caracteres TTS con margen del 85%.
46. **`transaction_service.py`**: Auditoría y conciliación de pagos.
47. **`twilio_service.py`**: Telefonía Twilio, búsqueda y compra de números virtuales.
48. **`voice_service.py`**: Cascada de audio multinivel (STT Whisper + TTS Edge-TTS con aislamiento de hilos).

---

## 🌐 5. Directorio de Rutas API (`backend/routes/` - 34 Módulos de Rutas)

1. `admin.py`: Panel de superadministrador, control de licencias, monitoreo global.
2. `agency.py`: Gestión de cuentas de agencia, cartera multitenant y delegaciones.
3. `agents.py`: CRUD de identidades de agentes, configuración de tono, género y features.
4. `analytics.py`: Endpoints de telemetría, métricas de rendimiento y consultas vectorizadas.
5. `attributions.py`: Ingesta y consulta de atribución UTM y campañas de marketing.
6. `auth.py`: Autenticación de usuarios, login, registro, refresco de JWT y bcrypt.
7. `beta.py`: Captura resiliente y gestión de prospectos de lista de espera con enriquecimiento IP.
8. `billing.py`: Consultas de facturación, planes, recargas de créditos y portal de cliente.
9. `channels.py`: Configuración de canales (WhatsApp QR, Telegram Token, Webchat Embed).
10. `chat.py`: Endpoints de interacción conversacional directa vía HTTP y WebSockets.
11. `companies.py`: Configuración de la empresa, BYOK, generación de `public_api_key`.
12. `crm.py`: Operaciones CRM Kanban, contactos, empresas y etapas de funnel.
13. `customers.py`: Perfil 360° del cliente, historial de mensajes y transacciones.
14. `demo.py`: Endpoints de prueba y entornos sandbox interactivos.
15. `departments.py`: Gestión de departamentos Enterprise, cuotas y namespaces RAG aislados.
16. `ecommerce.py`: Conectividad con tiendas online, sincronización de catálogos.
17. `employees.py`: Gestión de personal, asignación departamental y acceso web (`has_web_access`).
18. `google_auth.py`: Flujo OAuth2 para integración con Google Calendar y Sheets.
19. `hubspot.py`: Webhooks y endpoints de sincronización con HubSpot Inbox.
20. `landing_pages.py`: Generación, publicación y renderizado de landings con dominios CNAME.
21. `livekit_routes.py`: Generación de tokens de sesión para llamadas de voz WebRTC.
22. `marketplace.py`: Catálogo de assets modulares, licenciamiento HMAC y descarga de templates.
23. `mcp.py`: CRUD y pruebas de conectividad de servidores Model Context Protocol (`/api/companies/<id>/mcp`).
24. `payment_gateways.py`: Configuración de pasarelas y procesamiento de pagos en chat.
25. `payments.py`: Historial de transacciones y estados de cobro.
26. `rag.py`: Subida de documentos, parsing, chunking y consultas al knowledge base.
27. `skills.py`: Gestión de habilidades dinámicas modulares (`CompanySkill`).
28. `telemetry.py`: Métricas de latencia de red, rendimiento de agentes y telemetría en vivo.
29. `twilio.py`: Webhooks de voz y SMS de Twilio, compra de números virtuales.
30. `v1/agents.py`: Rutas de la API Pública v1 para invocación de Chiefs por API Key.
31. `v1/knowledge.py`: Rutas de la API Pública v1 para consultas semánticas RAG.
32. `voice.py`: Interacción de voz multimodal blindada (STT Whisper + TTS Edge).
33. `voice_agent_api.py`: Endpoints para agentes conversacionales telefónicos.
34. `webhooks.py`: Enrutamiento maestro de webhooks entrantes (WhatsApp, Paddle, Stripe).
35. `whatsapp_templates.py`: Creación y sincronización de plantillas oficiales de Meta.

---

## ⚡ 6. Capa de Aceleración de las 8 Estructuras de Datos

| Estructura | Servicio / Módulo | Complejidad | Función en Producción |
|---|---|---|---|
| **1. Hash Map** | `auth_cache_service.py` | $O(1)$ | Validación de `X-API-Key` y multi-tenancy en **$<0.1\text{ms}$**. |
| **2. Max-Heap** | `lead_heap_service.py` | $O(1)$ Top | Triaje y priorización inmediata de leads calificados para ventas. |
| **3. Trie (Árbol)** | `crm_trie_service.py` | $O(L)$ | Autocompletado CRM en **$3.0\text{ms}$** por prefijo de texto. |
| **4. Typed Arrays** | `analytics_vector_service.py` | $O(1)$ | Cálculos financieros (CAC, LTV, MRR, ROI) a 60 FPS con NumPy Float64. |
| **5. Linked List** | `langgraph_agent.py` | $O(1)$ | Ventana de memoria deslizante del chat sin reubicación de arrays. |
| **6. Queue (FIFO)** | `api-whatsapp` / `tasks.py` | $O(1)$ | Outbox de mensajes WhatsApp y colas Celery sobre Redis (`6380`). |
| **7. Stack (LIFO)** | `routing.py` | $O(1)$ | Delegation Call Stack Manager para transferencias entre los 7 Chiefs. |
| **8. Graph** | LangGraph / Pinecone | $O(V+E)$ | Grafo de estados ReAct y búsqueda vectorial HNSW. |

---

## 🚀 7. Topología de Procesos en Producción (`ecosystem.config.js`)

```text
1. aikrofy-redis        → Puerto 6380 (Broker de tareas y colas Redis)
2. aikrofy-frontend     → Puerto 3010 (Next.js 16 - Panel PyME)
3. aikrofy-enterprise   → Puerto 3012 (Next.js 16 - Panel Enterprise Dark Glassmorphism)
4. aikrofy-fastapi      → Puerto 5010 (API Backend Python / FastAPI / Uvicorn)
5. aikrofy-worker       → Celery Worker (Tareas pesadas de audio, ML y RAG en segundo plano)
6. aikrofy-api-whatsapp → Puerto 3011 (Microservicio Node.js / Baileys WebSocket)
7. aikrofy-landing-gen  → Puerto 5015 (Motor Screenshot-to-code)
```

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**
