# Plan de Implementación de Innovaciones para Aikrofy (Inspirado en Clonify)

Este plan de implementación está diseñado específicamente para la arquitectura actual de **Aikrofy** (FastAPI, Next.js, LangGraph, Pinecone, MySQL, WhatsApp vía Baileys). 

El objetivo es integrar las mejores prácticas de UX/UI y control de IAs (inspiradas en Clonify) **sin alterar ni romper** las integraciones actuales (RAG, ERPs, CRMs, Pasarelas de Pago), sino potenciándolas para ofrecer una experiencia B2B de nivel Enterprise.

---

## 1. Sistema de "Respuestas Guiadas" (Literal Overrides & Action Triggers)

**Propósito:** Prevenir alucinaciones críticas (ej. inventar descuentos o políticas de devolución falsas) mediante reglas estrictas (Guardrails) que eviten (hagan *bypass*) el razonamiento del LLM.

### Cambios Arquitectónicos:
1. **Base de Datos (MySQL / SQLAlchemy):**
   - Crear el modelo `GuidedResponse` (asociado a `Company`).
   - Columnas: `id`, `company_id`, `trigger_phrases` (JSON o texto separado por comas), `literal_response` (Text), `action_to_trigger` (Enum: `NONE`, `PAYMENT_LINK`, `HUMAN_ESCALATION`, `SEND_AUDIO`).
2. **Backend (FastAPI & LangGraph - `services/langgraph_agent.py`):**
   - **Nodo de Pre-Procesamiento:** Antes de entrar al nodo `agent` (LLM), añadir una función de similitud semántica rápida o coincidencia de intenciones. 
   - Si el último mensaje del usuario coincide (>85% similitud o keyword match exacto) con una frase en `GuidedResponse`, el grafo salta el nodo del LLM y va directo a un nodo `guided_response_node`.
   - Este nodo inyecta el `literal_response` en el estado y ejecuta la herramienta asociada en `action_to_trigger` (ej. enviar el link de PayPal sin preguntarle a la IA).
3. **Frontend (Next.js):**
   - Nuevo módulo en `/settings/guided-responses` para que las empresas configuren "Qué responder exactamente cuando el cliente pregunte X".

---

## 2. Campañas Dinámicas Efímeras (Dynamic Context Injection)

**Propósito:** Permitir a los negocios lanzar promociones de fin de semana (Black Friday) sin tener que reentrenar el RAG, ni modificar los skills estáticos en `CompanySkill`.

### Cambios Arquitectónicos:
1. **Base de Datos:**
   - Crear el modelo `CompanyCampaign`. Columnas: `id`, `company_id`, `name`, `description` (Contexto a inyectar), `is_active` (Booleano), `start_date`, `end_date`.
2. **Backend (Sistema de Prompts dinámicos - `services/skill_service.py`):**
   - Modificar `_build_system_prompt()`. Al ensamblar el prompt basado en los `CompanySkill` activos, verificar si hay una campaña activa para la empresa (`is_active=True` y dentro de fecha).
   - Si la hay, inyectar un bloque de muy alta prioridad al principio del System Prompt:
     `[ALERTA DE CAMPAÑA ACTIVA]: Actualmente tenemos la promoción "{name}". Instrucciones: {description}. Ignora cualquier precio anterior en tu base de conocimiento.`
3. **Frontend (Next.js):**
   - Panel `/marketing/campaigns` con un switch (Toggle) rápido para activar/desactivar ofertas en tiempo real.

---

## 3. Auditoría de Cerebro (Transparent RAG Auditing)

**Propósito:** Darle poder al usuario B2B para entender *por qué* el Krof respondió lo que respondió y corregirlo.

### Cambios Arquitectónicos:
1. **Backend (Pinecone & LangGraph):**
   - Modificar `rag_service.py` y `langgraph_agent.py` para que cuando el agente llame a la herramienta `query_knowledge_base`, los metadatos de los *chunks* obtenidos de Pinecone (IDs de los fragmentos, fuente original) se guarden en una tabla de auditoría `MessageAudit` en MySQL vinculada al ID del mensaje generado.
   - Añadir una lista negra de *chunks* a `rag_service.py` por empresa, para que Pinecone ignore fragmentos vetados por el usuario.
2. **Frontend (Next.js - Historial de Chat):**
   - En `/chat/history`, al hacer clic en un mensaje enviado por la IA, desplegar un panel lateral: "Fragmentos utilizados para esta respuesta".
   - Añadir un botón rojo: **"Excluir este fragmento"**. Al pulsarlo, el Backend añade ese Chunk ID a la lista negra, evitando futuras alucinaciones.

---

## 4. Omnicanalidad y "Conversational Landing Pages" (Captación de Leads)

**Propósito:** Aikrofy no es solo WhatsApp; funciona en la Web y Telegram. Inspirado en las "páginas de clon" de Clonify, crearemos Landing Pages Conversacionales Dinámicas por empresa (ej. `pym.ai/c/empresa123`). Estas páginas tendrán un diseño hermoso, dinámico y premium (glassmorphism, animaciones) y actuarán como un embudo (Gated Access) para captar nombre y correo antes de permitir chatear con la IA, integrando la data directo en el CRM.

### Cambios Arquitectónicos:
1. **Frontend (Next.js - Interfaz Pública y Diseño Premium):**
   - Crear una ruta dinámica pública `/c/[companySlug]` que renderice la **Conversational Landing Page**.
   - **UI/UX:** Implementar un diseño de vanguardia (fondos oscuros vibrantes, TailwindCSS, Framer Motion para micro-animaciones, y componentes Radix UI).
   - **Gating Form (Formulario de Ingreso):** Antes de mostrar la interfaz de chat, el usuario interactúa con una presentación de alto impacto (ej. "Hola, soy el asesor experto de [Empresa]. ¿Con quién tengo el gusto?") que requiere completar Nombre y Correo electrónico.
2. **Base de Datos (MySQL / SQLAlchemy):**
   - Ampliar el modelo `Company` con un campo `public_slug` (string único).
   - En la configuración de canales, añadir `require_lead_capture` (Boolean) y `lead_capture_fields` (configuración de qué datos pedir).
3. **Backend (FastAPI & CRM Sync):**
   - Cuando el usuario llena el formulario en la Landing Page, el Frontend invoca un endpoint (ej. `/api/public/leads`) que crea o actualiza el prospecto en la tabla interna `Customer` y lo sincroniza de inmediato con CRMs externos (HubSpot, Salesforce, etc.) usando tu motor de integraciones actual.
   - Una vez registrado, se establece la sesión de WebSockets para iniciar la conversación con LangGraph.
4. **Comportamiento Homologado en WhatsApp/Telegram:**
   - Para mantener la consistencia omnicanal, si `require_lead_capture=True`, el primer nodo del `StateGraph` de LangGraph actúa como un "Gatekeeper". Si entra un número nuevo en WhatsApp que no tiene un correo registrado, el agente pausará sus funciones avanzadas (ventas, RAG) y ejecutará un sub-flujo conversacional para preguntar el nombre y correo del usuario. Una vez obtenidos, desbloquea el resto de los "Chefs".

> [!IMPORTANT]
> **Coexistencia con el Widget Actual:** Esta Landing Conversacional **NO OMITE NI REEMPLAZA** el Widget de chat web embebible que ya existe en Aikrofy. Son dos vías de entrada distintas: El Widget se usa para embeberlo en la web corporativa del cliente, mientras que la Landing Conversacional (`pym.ai/c/...`) es una URL independiente diseñada como un embudo agresivo para campañas de pauta (ads) o enlaces directos, donde el diseño premium y la captación del lead son obligatorios antes del chat.

---

## 5. Fases de Implementación y Ejecución

Basado en el `PROJECT_STATUS_REPORT.md` (y la reciente migración a FastAPI, la integración de Paddle v2, y el proxy `GProxy` para multi-tenancy seguro), el código se desarrollará en las siguientes fases escalonadas para proteger la producción:

### Fase 1: Arquitectura de Base de Datos y Modelos Base (Backend)
- Crear las clases en `backend/models/`: `GuidedResponse` y `CompanyCampaign`.
- Actualizar `Company` añadiendo `public_slug` (string único).
- Actualizar `AgentFeature` añadiendo `require_lead_capture`.
- Ejecutar migraciones con **Alembic** garantizando que no bloquee las sesiones activas de MySQL.

### Fase 2: Motor de Respuestas Guiadas y Campañas (LangGraph & FastAPI)
- Modificar `backend/services/skill_service.py` (`_build_system_prompt`) para inyectar los prompts de `CompanyCampaign` si la fecha es válida, respetando el desacoplamiento de skills logrado en el último Pull Request.
- Modificar `backend/services/langgraph_agent.py`: Implementar la evaluación rápida de intenciones para hacer el *bypass* al nodo del LLM cuando se detecte un hit en `GuidedResponse` (Prevención de alucinaciones en cobros/descuentos). Asegurar el uso de `db_session.rollback()` antes de las llamadas largas para evitar el "MySQL Gone Away".

### Fase 3: Auditoría Transparente de Cerebro (Pinecone & MySQL)
- Crear modelo `MessageAudit` en backend.
- En `rag_service.py`, capturar los UUIDs de los chunks retornados por Pinecone v5.0+ y asociarlos al mensaje generado.
- Exponer un endpoint CRUD en FastAPI para añadir chunks vetados a la "lista negra" por `company_id`.

### Fase 4: Landing Page Conversacional & Admin UI (Next.js 16+)
- **Admin Dashboard:** Construir las interfaces en `/settings/guided-responses` y `/marketing/campaigns` usando TailwindCSS, Radix UI y componentes i18n (sin textos hardcodeados).
- **Ruta Pública:** Desarrollar `frontend/app/(public)/c/[slug]/page.tsx`.
- **UI/UX Premium:** Aplicar fondos oscuros, *glassmorphism*, tipografías modernas (Inter/Outfit) y *Framer Motion* para la animación inicial del "Gating Form".
- **CRM Sync:** Conectar el formulario de captación con el endpoint `/api/public/leads`, el cual disparará tu `CustomCRMMappingEngine` existente (HubSpot/Salesforce) antes de liberar el socket.

---

## Resumen de Ejecución
Este plan respeta estrictamente tu Regla Maestra **#5** (Desacoplamiento Completo de Prompts y Skills) y **#2** (Manejo del "Gone Away" al abstraer los guardrails). Además, se asienta sobre la reciente estabilización de tu arquitectura (FastAPI nativo + Node.js Baileys).
