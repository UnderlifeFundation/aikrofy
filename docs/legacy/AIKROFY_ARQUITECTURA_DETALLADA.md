# Radiografía Completa y Arquitectura Detallada de Aikrofy (WEBLIFETECH V3.0)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

Este documento es el mapa genético, exhaustivo y definitivo de la arquitectura del ecosistema **Aikrofy** (`aikrofy.com`). Para obtener un catálogo exhaustivo de todos los modelos, rutas, servicios y herramientas del sistema, consulte **[ANALISIS_SISTEMA_COMPLETO.md](file:///root/aikrofy/ANALISIS_SISTEMA_COMPLETO.md)** y la guía de audio en **[GUIA_IMPLEMENTACION_VOZ.md](file:///root/aikrofy/GUIA_IMPLEMENTACION_VOZ.md)**. Fue generado para que cualquier Inteligencia Artificial o desarrollador humano pueda comprender el 100% de la estructura, reglas y flujos de datos del sistema real en producción.

---

## 1. VISIÓN GENERAL DEL ECOSISTEMA AIKROFY

**Aikrofy** es un ecosistema SaaS (Software as a Service) multitenant diseñado para funcionar como una **fuerza laboral virtual 360°** y una **Junta Directiva Virtual (C-Suite de 7 Chiefs)** coordinada por el copiloto inteligente **Krof**. Su objetivo es permitir a las empresas (Companies) automatizar ventas, soporte, agendamiento, marketing, tecnología, ingresos y cobros de forma autónoma.

El proyecto es **altamente modular** y se compone de microservicios coordinados:
1. **El Backend (Cognitive Engine & API)**: Python 3.14 (FastAPI / Celery / SQLAlchemy 2.0 / LangGraph) corriendo en puerto `5010`.
2. **Aikrofy Frontend (PyME)**: TypeScript (Next.js 16+, React 19) corriendo en puerto `3010`.
3. **Aikrofy Enterprise Dashboard**: TypeScript (Next.js 16+, React 19) corriendo en puerto `3012` con estética Dark Glassmorphism, telemetría financiera y catálogo de APIs/MCP.
4. **WhatsApp API (api-whatsapp)**: Microservicio especializado basado en Node.js/TypeScript (`@whiskeysockets/baileys`) corriendo en puerto `3011`.
5. **Capa de Aceleración de Datos**: 8 estructuras fundamentales in-memory con latencias en microsegundos ($<0.1\text{ms}$).
6. **Módulo de Generación de Landings (Screenshot-to-Code)**: Python 3.14 / FastAPI en puerto `5015`.

---

## 2. EL BACKEND (NÚCLEO PYTHON Y ORQUESTACIÓN)

El backend es el cerebro de la operación. Está construido sobre **FastAPI** (utilizando `fastapi_app.py` y `fastapi_routers.py` como punto de entrada unificado) y utiliza **LangGraph** para la orquestación cognitiva.

### 2.1. Arquitectura Cognitiva (LangGraph & 7 Chiefs)
El archivo `backend/services/langgraph_agent.py` es el núcleo de la inteligencia.
* **Orquestación Stateful:** Utiliza `StateGraph` de LangGraph para mantener el estado de la conversación. Las conversaciones usan `MemorySaver` como checkpointer para recordar el contexto.
* **Junta Directiva de 7 Chiefs con Krof**:
  - **CEO (Orquestador)**: Delega flujos a subgrafos especializados (`gpt-4o-mini`).
  - **COO (Operaciones)**: Agendamiento Google Calendar, inventarios y procesos internos.
  - **CSO (Ventas)**: Calificación de prospectos, negociación y cierres con Max-Heap.
  - **CMO (Marketing)**: Campañas dinámicas temporales (`CompanyCampaign`) y generación de demanda *(Enterprise)*.
  - **CTO (Tecnología)**: Herramientas de conectividad, servidores MCP remotos y skills *(Enterprise)*.
  - **CRO (Ingresos)**: Embudo de conversión, carritos abandonados y optimización de ingresos *(Enterprise)*.
  - **CFO (Finanzas)**: Análisis de métricas financieras LTV, CAC, MRR, ROI a 60 FPS *(Enterprise)*.
* **Gestión de Flujos y Skills Dinámicos (Prompt Engineering Desacoplado):** El `system_prompt` es dinámico y se ensambla a través de `SkillService` cargando los registros de `CompanySkill` activos desde la base de datos MySQL y sincronizando con `uploads/skills/company_<id>/<skill_name>/SKILL.md`.
* **Reglas de Comportamiento del Agente:**
  - **Prioridad de Contextos:** El agente detecta si el usuario está en `FLUJO_PAGO`, `FLUJO_AGENDA` o `FLUJO_VENTAS`, bloqueándolo en ese flujo para evitar redundancias o saltos ilógicos.
  - **Fases de Cierre:** Implementación de una estructura de 3 actos (Recolección -> Ejecución -> Cierre) para evitar ejecuciones duplicadas de herramientas tras confirmaciones del usuario.
  - **Pagos:** Pide correo -> Ejecuta `lookup_customer` -> Confirma el monto exacto dictado por el usuario -> Genera link con `paypal_create_order` -> Manda email de confirmación (`send_email`).
  - **Agenda:** Valida correo/nombre -> Verifica disponibilidad -> Confirma -> `schedule_appointment` -> Envía `send_email`.
  - **Protección de Contexto:** Limita el historial recuperado a las últimas 24 horas y utiliza la memoria de ventana deslizante $O(1)$ (`SlidingWindowMemory`).
* **Control de Créditos:** Cada respuesta de IA descuenta 1 crédito del `credit_balance` de la empresa (excepto si el balance es `-1`, que indica "Ilimitado"). Esto ocurre *antes* de invocar a LangGraph.

### 2.2. Base de Datos Relacional (MySQL / MariaDB vía SQLAlchemy 2.0)
El esquema (`backend/models/`) consta de 34 modelos relacionales multi-tenant vinculados por `company_id`:
* `Company`, `User`, `Agent`, `AgentFeature`, `Department`, `Employee`, `Customer`, `Conversation`, `Message`, `Appointment`, `Transaction`, `Subscription`, `Plan`, `Channel`, `Document`, `CompanySkill`, `CompanyCampaign`, `ContactAttribution`, `WebReferralSession`, `CRMConfig`, `EcommerceConfig`, `ERPConfig`, `FunnelStage`, `GuidedResponse`, `IPTracking`, `LandingPage`, `LandingPageVersion`, `LandingPageVisit`, `LandingPageCustomDomain`, `CompanyMCPServer`, `MessageAudit`, `Note`, `PaymentGatewayConfig`, `PlatformConfig`, `PurchasedNumber`, `TenantScoringConfig`, `WhatsAppTemplate`.

**🛑 REGLAS CRÍTICAS DE DB (PREVENCIÓN DEL "GONE AWAY" Y UNBOUNDLOCALERROR):**
1. **Ámbito de Imports:** Importar `from extensions import db` únicamente a nivel de módulo. Jamás volver a importar `from extensions import db` dentro de funciones ni bloques `try/except`.
2. **Definición de Salidas de Archivo:** En endpoints multimedia (`/api/voice/interact`), definir `output_path` antes de ejecutar la síntesis TTS.
3. **Eager Loading:** Hacer un pre-fetch de variables a primitivos en Python antes de invocar herramientas de LangGraph.
4. **Limpieza Preventiva:** Ejecutar `db.session.rollback()` al inicio de cada función de LangGraph o Tool para limpiar sesiones atascadas.
5. **Ciclo de Vida:** El ciclo de vida de la sesión se gestiona con `db_session.remove()` en el middleware de FastAPI al final de cada petición.

### 2.3. RAG, Base de Datos Vectorial y Aislamiento por Departamentos (Pinecone v5.0+)
* **Aislamiento Multi-Tenant**: Cada empresa tiene su propio namespace vectorial (`company_{id}`).
* **Aislamiento por Departamentos (Enterprise)**: Empresas corporativas subdividen sus datos en departamentos con namespaces aislados: `company_{id}_dept_{dept_id}`.
* **Sabiduría Global (BOS-AI Handbooks)**: Namespace global (`company_id=None`) consultado en paralelo para dotar a los agentes de conocimientos directivos estándar.

### 2.4. Capa de Aceleración de las 8 Estructuras de Datos
1. **Hash Maps ($O(1)$)**: `auth_cache_service.py` valida `X-API-Key` y cuotas de empresa en $<0.1\text{ms}$.
2. **Max-Heaps ($O(1)$ Top)**: `lead_heap_service.py` gestiona la cola de prioridad de leads de alto valor.
3. **Trie ($O(L)$)**: `crm_trie_service.py` ofrece autocompletado en $3\text{ms}$ para búsquedas CRM.
4. **Typed Arrays (NumPy)**: `analytics_vector_service.py` calcula LTV, CAC, MRR, ROI a 60 FPS.
5. **Linked Lists**: `SlidingWindowMemory` en `langgraph_agent.py` mantiene la ventana de chat en tiempo constante.
6. **Queues**: Outbox de WhatsApp y Celery Worker en Redis (puerto `6380`).
7. **Stacks**: Delegation Call Stack Manager en `routing.py` para trazas de llamadas entre Chiefs.
8. **Graphs**: StateGraph de LangGraph e índice vectorial HNSW en Pinecone.

---

## 3. LOS FRONTENDS (NEXT.JS 16 / REACT 19)

### 3.1. Aikrofy Frontend (PyME - Puerto 3010)
* Interfaz minimalista orientada a autoservicio.
* Configuración de agentes, canales de WhatsApp y Webchat, RAG básico y agendamiento.

### 3.2. Aikrofy Enterprise Dashboard (Puerto 3012)
* Interfaz Dark Glassmorphism de alta gama con fuentes Outfit.
* Acceso completo a la C-Suite de 7 Chiefs.
* Módulo de Departamentos y asignación de empleados con control de acceso web.
* Telemetría financiera en tiempo real (LTV, CAC, MRR).
* Developer Portal: Sandbox interactivo para probar la API v1 (`/v1/agents/invoke`) y gestión de servidores MCP.

---

## 4. MICROSERVICIO WHATSAPP (API-WHATSAPP - Puerto 3011)

Basado en Node.js y TypeScript para gestionar WebSockets y sesiones concurrentes:
* Usa `@whiskeysockets/baileys` nativo para multi-tenancy.
* Maneja múltiples sesiones escaneando códigos QR individuales por empresa.
* Envía mensajes entrantes vía HTTP Webhooks hacia el backend (`/api/webhooks/whatsapp`) y procesa audios en segundo plano con Celery.

---

## 5. INFRAESTRUCTURA Y TOPOLOGÍA PM2

El sistema se ejecuta orquestado por PM2 (`ecosystem.config.js`):
1. `aikrofy-redis`: Broker de colas en puerto `6380`.
2. `aikrofy-frontend`: Next.js PyME en puerto `3010`.
3. `aikrofy-enterprise`: Next.js Enterprise en puerto `3012`.
4. `aikrofy-fastapi`: Backend FastAPI en puerto `5010`.
5. `aikrofy-worker`: Celery worker para tareas asíncronas de audio, RAG y ML.
6. `aikrofy-api-whatsapp`: Microservicio WhatsApp en puerto `3011`.
7. `aikrofy-landing-gen`: Motor Screenshot-to-code en puerto `5015`.

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**