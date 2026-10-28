# La Biblia de Desarrollo: Proyecto Aikrofy (Documentación Técnica Maestra V3.0)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

> [!NOTE]
> **Estado Actual del Proyecto V3.0:** La plataforma ha sido unificada bajo la marca **Aikrofy** (`aikrofy.com`). El copiloto técnico integrado del sistema se denomina **Krof**. Todo el sistema cuenta con la capa de aceleración de las **8 Estructuras de Datos Fundamentales** (Hash Maps, Max-Heaps, Tries, Typed Arrays, Stacks, Queues, Linked Lists, Graphs), ofreciendo latencias en microsegundos y cero fricción ($Friccion \to 0$).

Este documento es la referencia definitiva del ecosistema Aikrofy. Para una inmersión aún más profunda en reglas de código y lógica de base de datos, consulte **[AIKROFY_ARQUITECTURA_DETALLADA.md](file:///root/aikrofy/AIKROFY_ARQUITECTURA_DETALLADA.md)**, la radiografía exhaustiva de funciones en **[ANALISIS_SISTEMA_COMPLETO.md](file:///root/aikrofy/ANALISIS_SISTEMA_COMPLETO.md)**, y el informe técnico de datos **[INFORME_ESTRUCTURAS_DATOS_AIKROFY.md](file:///root/aikrofy/INFORME_ESTRUCTURAS_DATOS_AIKROFY.md)**.

---

## I. VISIÓN ARQUITECTÓNICA Y FLUJO DE DATOS CENTRAL

### 1.1 Arquitectura de Microservicios Heterogénea
El ecosistema opera mediante servicios desacoplados y multi-tenant:
1. **Backend (Python 3.14 / FastAPI en Puerto 5010)**: Motor cognitivo Krof, junta directiva de 7 Chiefs, capa de aceleración de datos y proveedor de APIs públicas (The Brain).
2. **Aikrofy Frontend (Next.js/React - Puerto 3010)**: Interfaz administrativa simplificada para PyMEs (The Face - PyME).
3. **Aikrofy Enterprise Dashboard (Next.js/React - Puerto 3012)**: Interfaz administrativa premium con estética Dark Glassmorphism, telemetría financiera avanzada y acceso al catálogo API/MCP (The Face - Enterprise).
4. **WhatsApp API (Node.js/TypeScript - Puerto 3011)**: Microservicio en `/api-whatsapp` con `@whiskeysockets/baileys` nativo (The Messenger).
5. **Redis Broker & Celery Worker (Puerto 6380)**: Gestión asíncrona de colas, transacciones y procesamiento pesado (The Muscle).
6. **Landing Page Generator (Node.js/Express - Puerto 5015)**: Generador dinámico y publicador de páginas web comerciales optimizadas (`landing-page-generator`).

### 1.2 Micro-Orquestación con LangGraph y la Junta Directiva (7 Chiefs con Krof)
El núcleo cognitivo utiliza un `StateGraph` asíncrono (`services/langgraph_agent.py`) diseñado para administrar la junta directiva de **7 Chiefs**:
- **`CEO` (Chief Executive Officer)**: Orquestador maestro y clasificador de intenciones.
- **`COO` (Chief Operating Officer)**: Automatización de operaciones, Google Calendar e inventarios.
- **`CSO` (Chief Sales Officer)**: Conversión de leads y negociación conversacional con triaje Max-Heap.
- **`CMO` (Chief Marketing Officer)**: Generación de demanda y campañas dinámicas (`CompanyCampaign`) *(Enterprise)*.
- **`CTO` (Chief Technology Officer)**: Integración de sistemas, servidores MCP y skills *(Enterprise)*.
- **`CRO` (Chief Revenue Officer)**: Embudo de conversión y ciclo de ingresos *(Enterprise)*.
- **`CFO` (Chief Financial Officer)**: Telemetría de CAC, LTV y salud financiera con NumPy a 60 FPS *(Enterprise)*.

---

## II. FUNDAMENTOS DEL BACKEND & CAPA DE ACELERACIÓN DE DATOS

### 2.1 Ecosistema de Servicios Principales (`services/`)
- **`auth_cache_service.py`**: Hash Map Cache ($O(1)$) para validación de `X-API-Key` y permisos en **$<0.1\text{ms}$**.
- **`lead_heap_service.py`**: Max-Heap Priority Engine ($O(1)$ Top) para priorización de leads calificados para el CSO/CRO.
- **`crm_trie_service.py`**: Prefix Tree Trie ($O(L)$) para autocompletado en **$3.0\text{ms}$** de contactos CRM.
- **`analytics_vector_service.py`**: Typed Array Engine (NumPy) para gráficos financieros del CFO a 60 FPS.
- **`langgraph_agent.py`**: Orquestación de estados y flujo de herramientas con memoria deslizante $O(1)$.
- **`rag_service.py`**: Gestión de documentos, fragmentación e indexación en Pinecone (HNSW Vector Graph) con aislamiento departamental.
- **`voice_service.py`**: Gestión asíncrona de notas de voz en cascada STT de 4 niveles y TTS de 5 niveles con edge-tts y ThreadPoolExecutor.
- **`mcp_service.py`**: Adaptador y cliente para servidores Model Context Protocol remotos.
- **`enterprise_limits.py`**: Enforce de cuotas departamentales y de empleados.

---

## III. TOPOLOGÍA PM2 Y PRODUCCIÓN

| Proceso | Puerto | Rol |
|---|---|---|
| `aikrofy-redis` | `6380` | Redis Broker |
| `aikrofy-frontend` | `3010` | Next.js PyME UI |
| `aikrofy-enterprise` | `3012` | Next.js Enterprise UI |
| `aikrofy-fastapi` | `5010` | FastAPI Backend |
| `aikrofy-worker` | — | Celery Worker |
| `aikrofy-api-whatsapp` | `3011` | WhatsApp Baileys Microservice |
| `aikrofy-landing-gen` | `5015` | Landing Page Generator Microservice |

---

## IV. CONCLUSIÓN
Aikrofy consolida una plataforma agéntica B2B de nivel **Enterprise**, lista para operar como software administrativo (SaaS B2B) y como infraestructura de API/MCP de IA pagada por consumo de tokens.

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**
