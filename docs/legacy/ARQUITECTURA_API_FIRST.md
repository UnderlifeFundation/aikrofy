# 🏗️ Arquitectura API-First y Ecosistema Multi-Frontend en Aikrofy (V3.0)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

## 1. Visión General y Estado Actual

La plataforma **Aikrofy** (`aikrofy.com`) está construida y opera bajo una arquitectura **API-First** desacoplada. El backend FastAPI (Python 3.14 / ASGI) no está atado a una única interfaz, sino que sirve de forma simultánea e independiente a:
1. **Frontend PyME (Aikrofy)**: En puerto `3010`.
2. **Frontend Enterprise (Aikrofy Enterprise)**: En puerto `3012`.
3. **Desarrolladores Externos e Integraciones B2B**: Vía REST API Pública V1 (`/v1/`).
4. **Clientes y Asistentes MCP (Model Context Protocol)**: Vía el servidor MCP integrado (`/api/companies/<id>/mcp`).
5. **Canales de Mensajería**: WhatsApp (microservicio Node.js en puerto `3011`), Telegram y llamadas de voz en tiempo real (LiveKit).

---

## 2. Ecosistema de Frontends Desacoplados

El backend alimenta dos productos distintos según el segmento de mercado:

* **Frontend PyME (`frontend/` - Puerto 3010):** Dirigido a pequeños negocios y emprendedores. Interfaz simplificada y directa, enfocada en la configuración rápida del copiloto **Krof**, canales de chat, RAG básico y agendamiento.
* **Frontend Enterprise (`enterprise-frontend/` - Puerto 3012):** Dirigido a medianas y grandes corporaciones. Interfaz premium Dark Glassmorphism, C-Suite de **7 Chiefs**, módulo de departamentos, asignación de empleados con control de acceso web, telemetría financiera a 60 FPS (LTV, CAC, MRR, ROI) y Developer Portal para gestión de API Keys y Servidores MCP.

---

## 3. Aislamiento Estricto de Datos (Multi-Tenancy & Containment)

* **Aislamiento Relacional (MySQL / SQLAlchemy 2.0):** Los 34 modelos relacionales están estrictamente aislados por la columna `company_id`.
* **Aislamiento Vectorial RAG (Pinecone v5.0+):** Cada empresa cuenta con un namespace vectorial dedicado (`company_{id}`). Las cuentas Enterprise disponen de aislamiento adicional por departamento (`company_{id}_dept_{dept_id}`).
* **Memoria Global de Sabiduría (BOS-AI):** Namespace global (`company_id=None`) consultado en paralelo para inyectar frameworks directivos y buenas prácticas de negocio a los agentes sin mezclar datos privados.
* **Autenticación en Microsegundos ($O(1)$):** La capa `AuthHashMapCache` (`services/auth_cache_service.py`) valida las credenciales de API Key (`X-API-Key`) y permisos en **$<0.1\text{ms}$** en memoria.

---

## 4. Clasificación de Operaciones y Catálogo de Endpoints

### 4.1. Operaciones de Alto Nivel (Flujos Completos / ReAct)
* `POST /v1/agents/invoke`: Envía un prompt a un agente específico de la Junta Directiva (CEO, CMO, CFO, etc.) y ejecuta el grafo cognitivo completo con herramientas asociadas.
* `POST /api/chat/interact`: Bucle conversacional omnicanal con memoria de ventana deslizante $O(1)$.
* `POST /api/voice/interact`: Pipeline completo STT (Whisper) -> LangGraph -> TTS (Edge-TTS).

### 4.2. Operaciones Atómicas y Modulares (Microservicios)
* `POST /v1/knowledge/ingest`: Ingesta y vectorización de documentos en el namespace de la empresa.
* `GET /v1/knowledge/query`: Búsqueda semántica HNSW en base de conocimiento privada + BOS-AI.
* `GET /v1/agents/list`: Listado dinámico de agentes habilitados según `company.plan_type`.
* `GET /v1/agents/skills`: Consulta de habilidades dinámicas modulares.
* `POST /api/companies/{id}/mcp`: Registro y gestión de servidores remotos Model Context Protocol.
* `POST /api/companies/{id}/mcp/{sid}/test`: Prueba de conexión y descubrimiento de tools remotas en servidores MCP.

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**
