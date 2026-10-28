# 🔌 Catálogo de APIs REST V1 y Servidores Model Context Protocol (MCP) en Aikrofy

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

Para obtener una radiografía técnica exhaustiva de todo el ecosistema de software, modelos y servicios, consulte **[ANALISIS_SISTEMA_COMPLETO.md](file:///root/aikrofy/ANALISIS_SISTEMA_COMPLETO.md)**.

---

## 1. Visión y Arquitectura de Conectividad

**Aikrofy** implementa un modelo **API-First** robusto y seguro. Expone una suite de endpoints REST públicos bajo la versión `/v1/` y una integración completa con el estándar **Model Context Protocol (MCP)** de Anthropic, permitiendo que tanto desarrolladores externos como clientes de IA (Claude Desktop, agentes autónomos o IDEs) interactúen con la Junta Directiva de **7 Chiefs**, las bases de conocimiento RAG y los servidores de herramientas conectados.

---

## 2. API REST Pública V1 (`backend/routes/v1/`)

Todas las peticiones a la API V1 deben incluir la cabecera de autenticación:
```http
X-API-Key: pymai_<tu_token_publico>
```
*La autenticación se valida en memoria en **$<0.1\text{ms}$** mediante `AuthHashMapCache` (`services/auth_cache_service.py`), garantizando un aislamiento estricto por `company_id`.*

### 2.1. Invocación y Gestión de Agentes
* **`POST /v1/agents/invoke`**
  - **Propósito**: Ejecuta un prompt directamente contra un agente específico (ej. `CEO`, `CFO`, `CRO`, `CSO`).
  - **Payload**:
    ```json
    {
      "agent_name": "CFO",
      "prompt": "Genera el reporte de LTV y CAC proyectado para este trimestre.",
      "session_id": "ses_custom_9921"
    }
    ```
  - **Respuesta**: Retorna la respuesta estructurada de la IA, el desglose de herramientas invocadas y el balance de créditos restante.
* **`GET /v1/agents/list`**: Lista los agentes y Chiefs disponibles para la empresa (filtrado dinámicamente por `company.plan_type`).
* **`GET /v1/agents/skills`**: Retorna el listado de habilidades dinámicas (`CompanySkill`) activas.

### 2.2. Gestión de Base de Conocimiento (RAG)
* **`POST /v1/knowledge/ingest`**: Ingesta texto plano, documentos estructurados o URLs hacia el namespace de Pinecone de la empresa.
* **`GET /v1/knowledge/query`**: Realiza una búsqueda semántica vectorial (HNSW) sobre la base privada de la empresa y la base global de BOS-AI.
* **`DELETE /v1/knowledge/{doc_id}`**: Elimina un documento y purga sus vectores asociados en Pinecone.

---

## 3. Servidor y Adaptador Model Context Protocol (MCP) (`routes/mcp.py` & `services/mcp_service.py`)

Aikrofy permite a las empresas registrar servidores remotos de MCP (HTTP / Server-Sent Events SSE) para dotar a sus agentes de herramientas externas dinámicas:

### 3.1. Endpoints de Gestión MCP
* **`GET /api/companies/{company_id}/mcp`**: Lista todos los servidores MCP registrados para la empresa.
* **`POST /api/companies/{company_id}/mcp`**: Registra un nuevo servidor MCP.
  ```json
  {
    "name": "internal-stock-server",
    "label": "Servidor de Inventario Central",
    "description": "Herramientas para consulta de stock en tiempo real",
    "url": "https://mcp.miempresa.com/sse",
    "headers": { "Authorization": "Bearer token_secreto" },
    "is_active": true
  }
  ```
* **`PUT /api/companies/{company_id}/mcp/{server_id}`**: Actualiza URL, cabeceras o estado activo.
* **`DELETE /api/companies/{company_id}/mcp/{server_id}`**: Elimina el registro del servidor MCP.
* **`POST /api/companies/{company_id}/mcp/{server_id}/toggle`**: Activa o desactiva el servidor.
* **`POST /api/companies/{company_id}/mcp/{server_id}/test`**: Prueba la conexión HTTP/SSE, descubre las herramientas expuestas por el servidor y retorna sus esquemas JSON para validación en el Dashboard.

### 3.2. Inyección Dinámica en LangGraph
Cuando un agente procesa un mensaje, `MCPService.get_tools_for_company(company_id)` recupera las herramientas remotas cacheadas, las encapsula como objetos `StructuredTool` de LangChain y las inyecta de forma transparente al bucle ReAct de LangGraph.

---

## 4. Aislamiento y Seguridad

1. **Multi-Tenancy Garantizado**: Toda consulta a la API REST o a través de herramientas MCP se filtra estrictamente por el `company_id` autenticado.
2. **Control de Cuotas y Créditos**: Cada invocación descuenta créditos del balance de la empresa y bloquea la ejecución si el saldo llega a 0 (a menos que el plan sea ilimitado).
3. **Invalidación Inmediata de Caché**: Cualquier cambio en la configuración de la empresa o servidores MCP invalida la caché local inmediatamente.

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**
