# 🏗️ Estado Actual del Proyecto — Plataforma Aikrofy (V4.0, 26-sep-2026)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

> [!NOTE]
> **V4.0 auditado en producción:** 6/6 PM2 online (6380/3010/5010/worker/3011/5015). Cifras reales: **57 tablas / 41 ficheros `models/`, 96 ficheros `services/`, 45 ficheros `routes/` / ~335 endpoints**, `frontend/` :3010 con 52 páginas × 5 idiomas (planes pyme+enterprise). la app enterprise separada (:3012) eliminada el 26-sep-2026 (sin tráfico; detalle en `COMPENDIO §16`). Detalle: `COMPENDIO_MAESTRO_AIKROFY.md` · mapa: `ESTRUCTURA_PROYECTO.md` · reglas: `GEMINI.md` · operación: `AGENTS.md`.

Para un desglose pormenorizado de la estructura de código, base de datos, servicios, endpoints REST y Model Context Protocol, consulte **[ANALISIS_SISTEMA_COMPLETO.md](file:///root/aikrofy/docs/analisis/ANALISIS_SISTEMA_COMPLETO.md)** y la guía de audio en **[GUIA_IMPLEMENTACION_VOZ.md](file:///root/aikrofy/docs/legacy/GUIA_IMPLEMENTACION_VOZ.md)**.

---

## ✅ Resumen de Módulos y Capacidades en Producción

### FASE 1: Backend API-First + Multi-Tenancy
| Componente | Estado | Archivos Principales |
|---|---|---|
| 56 Modelos Relacionales SQLAlchemy 2.0 (41 ficheros) | ✅ | `backend/models/*.py` |
| 45 Módulos de Rutas FastAPI (~335 endpoints) | ✅ | `backend/routes/*.py` |
| 96 Servicios Core y Algoritmos (57 top-level) | ✅ | `backend/services/*.py` |
| 48 Herramientas LangGraph (@tool) | ✅ | `backend/services/langgraph_tools.py` |
| Endpoints API V1 Agentes y RAG | ✅ | `backend/routes/v1/agents.py`, `backend/routes/v1/knowledge.py` |
| Registro Unificado de Routers FastAPI | ✅ | `backend/fastapi_routers.py`, `backend/fastapi_app.py` |
| Autenticación por `X-API-Key` y Hash Cache | ✅ | `backend/services/auth_cache_service.py` |
| Cascada de Audio y Voz Blindada | ✅ | `backend/services/voice_service.py`, `backend/routes/voice.py` |

### FASE 2: Junta Directiva Virtual (7 Chiefs con Krof)
| Chief | Rol | Plan Requerido | Funcionalidades Clave |
|---|---|---|---|
| **CEO** | Orquestador Maestro | Todos (`pyme`, `enterprise`) | Clasificación de intenciones y delegación de subgrafos. |
| **COO** | Operaciones | Todos (`pyme`, `enterprise`) | Agendamiento Google Calendar e integraciones. |
| **CSO** | Ventas | Todos (`pyme`, `enterprise`) | Negociación y triaje de leads por Max-Heap ($O(1)$). |
| **CMO** | Marketing | Enterprise | Campañas dinámicas temporales (`CompanyCampaign`). |
| **CTO** | Tecnología | Enterprise | Gestión de conectividad y servidores MCP. |
| **CRO** | Ingresos | Enterprise | Embudo de conversión y recuperación de ventas. |
| **CFO** | Finanzas | Enterprise | Métricas financieras LTV, CAC, MRR, ROI a 60 FPS con NumPy. |

### FASE 3: RAG Multi-Namespace & Sabiduría Global (BOS-AI)
| Componente | Estado | Descripción |
|---|---|---|
| Namespaces por Empresa | ✅ | Aislamiento estricto por `company_id` en Pinecone v5.0+. |
| Namespaces por Departamento | ✅ | Aislamiento por `company_{id}_dept_{dept_id}` para Enterprise. |
| Namespace Global BOS-AI | ✅ | Handbooks directivos globales (`company_id=None`) consultados en paralelo. |
| Auditoría de Chunks | ✅ | Registro contable de fragmentos vectoriales usados en `MessageAudit`. |

### FASE 4: Frontends Desacoplados (Next.js 16+ / React 19)
| Frontend | Puerto | Rol | Características |
|---|---|---|---|
| **Aikrofy (PyME)** | `3010` | PyMEs y Emprendedores | Interfaz intuitiva, configuración de canales y agentes básicos. |
| ~~**Aikrofy Enterprise**~~ | ~~`3012`~~ | ❌ Eliminado 26-sep-2026 (sin tráfico; plan `enterprise` servido por `plan_type` en `frontend/` :3010) | — |

### FASE 5: Capa de Aceleración de las 8 Estructuras de Datos
| Estructura | Servicio / Módulo | Complejidad | Latencia Real / Estado |
|---|---|---|---|
| **Hash Map Cache** | `backend/services/auth_cache_service.py` | $O(1)$ | **$<0.1\text{ms}$** ✅ |
| **Max-Heap Priority** | `backend/services/lead_heap_service.py` | $O(1)$ Top | **$<0.1\text{ms}$** ✅ |
| **Trie Prefix Tree** | `backend/services/crm_trie_service.py` | $O(L)$ | **$3.0\text{ms}$** ✅ |
| **Typed Arrays (NumPy)** | `backend/services/analytics_vector_service.py` | $O(1)$ | **$2.0\text{ms}$** ✅ |
| **Linked List** | `services/langgraph_agent.py` | $O(1)$ | **Inmediato** ✅ |
| **Queue (FIFO)** | `api-whatsapp` / `tasks.py` (Redis `6380`) | $O(1)$ | **Background** ✅ |
| **Stack (LIFO)** | `backend/routing.py` | $O(1)$ | **Inmediato** ✅ |
| **Graph** | LangGraph & Pinecone HNSW | $O(V+E)$ | **Inmediato** ✅ |

### FASE 6: Onboarding Conversacional & Registro a Beta Privada
| Componente | Estado | Descripción & Garantía de Flujo |
|---|---|---|
| **Formulario Conversacional 8 Pasos** | ✅ | `frontend/app/(public)/beta-register/page.tsx` — Wizard interactivo con preguntas de identidad, industria, tamaño de equipo, experiencia previa en IA y contacto directo. |
| **Persistencia de Sesión Local** | ✅ | `localStorage ('aikrofy_beta_form')` para evitar pérdida de datos si el usuario recarga, retrocede o sufre interrupciones de red. |
| **Tolerancia y Fallbacks API** | ✅ | `backend/routes/beta.py` — Validación estricta solo para datos de contacto esenciales (`contact_name`, `email`, `phone`, `company_name`) y asignación de valores fallback seguros (`employee_count='1-5'`, `industry='other'`) para blindar el 100% de captación de leads. |
| **Auto-Sync CRM & Telemetría IP** | ✅ | Sincronización automática del prospecto a la tabla `customers` de la plataforma (Tenant 1) con resolución de geolocalización IP en tiempo real. |
| **Gestión y Aprobación SuperAdmin** | ✅ | `frontend/app/(dashboard)/admin/beta/page.tsx` & `/api/beta/leads` — Aprobación/rechazo en un clic con despacho de credenciales automáticas generadas por el motor Krof. |

---

### FASE 6: Tienda de Materiales & Módulos Desacoplados LEGO (Blog Agéntico & MediaSuite)
| Componente | Estado | Archivos Principales / Descripción |
|---|---|---|
| **Catálogo Modular & Licenciamiento Cifrado** | ✅ | `backend/models/modular_asset.py`, `backend/routes/marketplace.py` — Claves HMAC-SHA256 ancladas al tenant (`company_id`) y dominio del VPS para evitar uso no autorizado. |
| **Herramientas Agénticas LangGraph** | ✅ | `backend/services/langgraph_tools.py` — `blog_create_article`, `blog_modify_style`, `blog_sync_mediasuite` para creación y ajuste de diseño mediante voz o texto. |
| **Generación Celery con MediaSuite (Pexels)** | ✅ | `backend/tasks.py` — Tarea asíncrona `process_agentic_blog_content` que consulta fotos/videos HD en `media.weblifetech.com`, optimiza metadatos SEO y los despacha al VPS del cliente sin almacenar peso en la nube central. |
| **Interceptor de Comandos WhatsApp / Voz** | ✅ | `backend/tasks.py` — Detección automática de intenciones conversacionales (*"crear blog sobre..."*, *"cambiar estilo a oscuro..."*) desde notas de voz o texto en WhatsApp. |
| **Dashboard Tienda LEGO (Frontend)** | ✅ | `frontend/app/(dashboard)/marketplace/page.tsx` — Catálogo interactivo de assets, compra con combustible IA, visualización de licencias y descarga directa del ZIP preconfigurado. |
| **Plantilla Desacoplada Next.js 15 (Plantilla en Blanco)** | ✅ | `templates/blog-template-blank/` — Arquitectura natural de cola larga, navegación SPA nativa ultra-rápida, CMS Canvas con Drag & Drop (`/admin`), verificación criptográfica (`lib/license-shield.ts`) y Widget de Aikrofy para captación y ventas en frontend. |
| **Proyecto de Referencia Ecuador Life (TurismAI)** | ✅ | `templates/blog-template-blank/data/posts.json`, `seed_ecuador_posts.py` — 12 posts y guías provinciales sembradas desde el dump SQL de WordPress (`u668392243_ecuadors.sql`). |

---

### FASE 7: LEM-Ops (Latent Equilibrium Models) & Observatorio de Invariantes
| Componente | Estado | Archivos Principales / Descripción |
|---|---|---|
| **Árbitro Binario Nativo C99** | ✅ | `backend/services/lem_guardrail_service.py` — Evaluación sub-milisegundo de estabilidad latente y drift previo al despacho LLM. |
| **Auto-Ajuste & Proyección Invariante** | ✅ | `backend/services/lem_guardrail_service.py` — Proyecciones matemáticas ortogonales sobre perturbaciones del espacio latente. |
| **Interceptor Pre-LLM LangGraph** | ✅ | `backend/services/langgraph_agent.py`, `backend/services/agent_service.py` — Blindaje cognitivo contra alucinaciones destructivas y transgresión de políticas. |
| **API de Observabilidad & Métricas** | ✅ | `backend/routes/observatory.py` — Métricas de convergencia, logs de arbitraje y calibración de umbrales por tenant. |
| **Panel AI Observatory (Frontend)** | ✅ | `frontend/app/(dashboard)/observatory/page.tsx` — Dashboard interactivo con telemetría de equilibrio, gráficos de drift y consumo de créditos de seguridad. |
| **Documentación Técnica & Pruebas** | ✅ | `docs/integraciones/LEM_OPS_INTEGRACION.md`, `backend/tests/test_lem_native.py` (7/7 tests aprobados). |

---

## 🌐 Arquitectura de Puertos y Procesos PM2 (`ecosystem.config.js`)

| Proceso PM2 | Puerto | Tecnología | Función |
|---|---|---|---|
| `aikrofy-redis` | `6380` | Redis 7+ | Broker de tareas Celery y colas de mensajes. |
| `aikrofy-frontend` | `3010` | Next.js 16 / React 19 | Dashboard para PyMEs. |
| `aikrofy-fastapi` | `5010` | Python 3.14 / FastAPI | API Backend Core & Motor Cognitivo. |
| `aikrofy-worker` | — | Celery / Python 3.14 | Worker asíncrono para audio, RAG, ML y generación agéntica de blog. |
| `aikrofy-api-whatsapp` | `3011` | Node.js / TypeScript | Microservicio de WhatsApp con Baileys. |
| `aikrofy-blog-vps` (Cliente) | `3020` | Next.js 15 / React 19 | Módulo de Blog Agéntico desacoplado desplegado en VPS del cliente. |

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**
