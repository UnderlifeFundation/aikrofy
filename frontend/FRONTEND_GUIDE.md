# Guía Maestra de Desarrollo Frontend - PunchAI (Next.js 14+)

**Versión:** 1.0 (Handoff Production Ready)
**Fecha:** 13 de Febrero de 2026
**Filosofía:** Fricción Cero, Intuitivo, Responsivo, Ultra-Rápido.

Este documento es la referencia definitiva para construir el frontend de PunchAI, diseñado para integrarse al 100% con el backend internacionalizado y asíncrono.

---

## 1. 🎯 Visión y Principios

El frontend de PunchAI no es solo una interfaz; es el panel de control de una fuerza laboral virtual. Debe transmitir **confianza, modernidad y eficiencia**.

### Principios Fundamentales:
*   **Fricción Cero**: El usuario debe realizar tareas comunes (ver un lead, agendar una cita) con el mínimo de clicks posible.
*   **Inteligencia Proactiva**: Mostrar sugerencias del sistema (Sentiment Analysis, Lead Scoring) de forma visual.
*   **Velocidad Extrema**: Carga instantánea de datos mediante React Query y estados optimistas.
*   **Responsividad Total**: Experiencia perfecta en móviles (el 80% de los distribuidores operan desde su teléfono).

---

## 2. 🛠️ Stack Tecnológico Recomendado

Para integrarse perfectamente con el backend actual, se debe utilizar:

*   **Framework**: [Next.js 14+](https://nextjs.org/) con App Router para SEO (Landing pages de evaluación) y performance.
*   **Lenguaje**: **TypeScript** (Estricto).
*   **UI/Styling**: 
    *   **Tailwind CSS**: Para un diseño rápido y responsivo.
    *   **Shadcn UI + Radix UI**: Componentes accesibles y personalizables de alto nivel.
    *   **Lucide Icons**: Iconografía moderna y ligera.
*   **Gestión de Estado**:
    *   **Zustand**: Para estado global ligero (User Auth, Settings).
    *   **React Query (TanStack)**: **OBLIGATORIO** para sincronización con el servidor, caching y manejo de errores.
*   **Formularios**: **React Hook Form** + **Zod** para validaciones robustas.

---

## 3. 📐 Arquitectura del Proyecto (Next.js App Router)

Se utilizará la estructura de directorios moderna de Next.js para maximizar el rendimiento y el SEO.

```text
/frontend
├── /app/                   # Directorio App Router
│   ├── /(auth)/            # Grupo de rutas de autenticación (Login, Register)
│   ├── /(dashboard)/       # Grupo de rutas protegidas (Panel, CRM, Config)
│   ├── /evaluate/          # Landing pública de evaluación (página dinámica)
│   ├── /api/               # Route Handlers (si se requieren proxies)
│   └── layout.tsx          # Root Layout (I18n, Theme, QueryClient)
├── /components/            # UI Components
│   ├── /ui/                # Componentes base (Shadcn UI)
│   ├── /shared/            # Componentes reutilizables (Sidebar, Navbar)
│   └── /features/          # Componentes complejos por feature (LeadTimeline, AgentToggle)
├── /hooks/                 # React Hooks personalizados (useAuth, useUnifiedContact)
├── /lib/                   # Configuraciones de librerías (Axios, Zustand, Utils)
├── /services/              # Capa de comunicación con la API (React Query Mutations/Queries)
├── /locales/               # Diccionarios de traducción (JSON)
├── /store/                 # Estado global persistente (Zustand)
├── /types/                 # Definiciones estricta de TypeScript (mapeadas a modelos Python)
└── /styles/                # CSS Global y variables de Tailwind
```

---

## 2. 🔐 Autenticación y Seguridad "Fricción Cero"

### 2.1. Gestión de Tokens (JWT)
*   **Almacenamiento**: Usar `cookies` (vía `js-cookie`) para el `access_token` para que Next.js Middleware pueda leerlas.
*   **Interceptor de Axios**: Configurar en `lib/api-client.ts`:
    *   Inyectar automáticamente `Authorization: Bearer <token>`.
    *   **Manejo de Errores**: Si el backend responde 401, redirigir automáticamente a `/login` y limpiar el store de Zustand.

### 2.2. Middleware de Next.js
*   Implementar `middleware.ts` en la raíz para:
    *   Redirigir a `/dashboard` si un usuario autenticado intenta ir a `/login`.
    *   Redirigir a `/login` si un usuario no autenticado intenta entrar a `/(dashboard)`.

---

## 3. 🌐 Internacionalización (Sincronización Total)

El backend es el **Dueño de la Verdad** sobre el idioma preferido (`company.language`).

### Flujo de I18n:
1.  **Carga Inicial**: Al hacer login, el store de Zustand guarda el `language` del distribuidor.
2.  **Cambio de Idioma**: Al cambiar el idioma en la UI, se hace un `PUT /api/companies/settings` y simultáneamente se actualiza `i18next.changeLanguage()`.
3.  **Localización de Agentes**: No traducir los nombres de los agentes en el frontend; el backend ya los entrega localizados tras el registro.

---

## 4. 🧩 Integración de Capas del Backend (El Core)

### 4.1. Perfil Unificado del Contacto (360° View)
*   **Endpoint**: `GET /api/contacts/unified/[identifier]`
*   **Implementación**:
    *   Usar un componente de **Timeline Vertical**.
    *   **Filtrado en Cliente**: Permitir al usuario filtrar el timeline por "Solo Mensajes", "Solo Citas" o "Solo Evaluaciones".
    *   **Detalle**: Si hay una `WellnessEvaluation`, mostrar un botón "Descargar Reporte PDF" que use el ID de la evaluación.

### 4.2. Seguimiento Asíncrono (Celery + UI)
*   Para tareas pesadas (Generar PDF, Subir Documento RAG):
    1.  El backend responde un `task_id` o el ID del objeto con estatus `PROCESSING`.
    2.  **UI Pattern**: Mostrar un spinner o barra de progreso infinita en el lugar del elemento.
    3.  **Polling**: Usar `refetchInterval` de **React Query** (ej. cada 3s) para actualizar el estado del objeto hasta que cambie a `COMPLETED` o `READY`.

---

## 5. 🗺️ Mapa de Vistas y UX Proactiva

### 5.1. Dashboard de Operaciones (`/dashboard`)
*   **Métricas en Vivo**: Consumir `GET /api/dashboard/metrics`.
*   **Gráficos**: Usar `Recharts`. Mostrar el "Lead Conversion Rate" como el KPI principal.
*   **Estado de WhatsApp**: Mostrar un badge visual (Verde/Rojo) basado en el estado del microservicio `api-whatsapp`.

### 5.2. CRM Dinámico (`/leads` y `/customers`)
*   **Tabla Inteligente**: Usar `TanStack Table` con:
    *   Búsqueda global reactiva.
    *   Badge de color según el `SentimentAnalysis` del último mensaje (Verde=Positivo, Rojo=Negativo).
    *   Acción rápida "Calificar Lead" con un click.

### 5.3. Configuración de Agente (`/agents`)
*   **Gestión de Características**: No programar características estáticas. Mapear dinámicamente el array `features` que responde el backend a interruptores (`Switch` de Shadcn UI).
*   **Objective/Tone**: Selectores que envíen los enums exactos del backend (`AgentTone.PROFESSIONAL`, etc.).

### 5.4. Playground de IA
*   Permitir al usuario chatear con su agente usando `/api/openai-compat/v1/chat/completions`. Esto les da confianza en su configuración antes de lanzarla a clientes reales.

---

## 6. 🚀 Rendimiento y "Wow Factor"

*   **Skeletons**: Implementar Skeletons para todas las tablas y perfiles. El usuario nunca debe ver una pantalla en blanco.
*   **Sonner Notifications**: Usar la librería `sonner` para toasts elegantes y rápidos.
*   **Dark Mode**: Soporte nativo desde el día 1 vía `next-themes`.
*   **Mobile-First**: Los formularios deben ser 100% usables en pantallas pequeñas con teclados virtuales.

---

## 📘 Checklist Final de Implementación

1.  [ ] Instalación de Next.js, Tailwind, Shadcn, React Query, Zustand.
2.  [ ] Configuración de `apiClient` con interceptores de Auth.
3.  [ ] Implementación del flujo de Login/Registro con selección de Idioma.
4.  [ ] Creación del Dashboard con consumo de métricas reales.
5.  [ ] Implementación de la vista de Contacto Unificado (Timeline).
6.  [ ] Integración de la Landing de Evaluación de Bienestar (Pública).

---

**Veredicto**: Esta guía garantiza que el frontend no sea solo una cara bonita, sino una extensión inteligente y veloz del potente motor asíncrono que hemos construido en el backend.
