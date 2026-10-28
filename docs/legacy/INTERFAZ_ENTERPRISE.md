# 🚀 Frontend Enterprise (Aikrofy Enterprise Dashboard)

**Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.**

## 1. Propósito y Audiencia

**Aikrofy Enterprise** (`enterprise-frontend/`, ejecutándose en el puerto `3012`) es la interfaz de administración web premium diseñada para medianas y grandes corporaciones. Mientras que el panel PyME (puerto `3010`) se enfoca en el autoservicio rápido para pequeños negocios, la interfaz Enterprise ofrece una experiencia completa orientada a escalar operaciones mediante la **Junta Directiva Virtual de 7 Chiefs**, contención por departamentos, telemetría financiera y acceso a herramientas de desarrollador (API REST V1 y Servidores MCP).

---

## 2. Comparativa Arquitectónica de Frontends

| Característica | Aikrofy (PyMEs - Puerto 3010) | Aikrofy Enterprise (Puerto 3012) |
|---|---|---|
| **Estilo Visual** | Clean UI, colores directos, minimalista. | **Dark Glassmorphism**, estética premium, fuentes Outfit. |
| **C-Suite de Agentes** | Copiloto Krof con Chiefs básicos (CEO, COO, CSO). | **C-Suite Completo (7 Chiefs)**: CEO, COO, CSO, CMO, CTO, CRO, CFO. |
| **Estructura Organizacional** | Nivel único de empresa. | **Módulo de Departamentos** con cuotas y aislamiento RAG. |
| **Telemetría y Analíticas** | Métricas estándar de conversaciones. | **Telemetría Financiera a 60 FPS** (CAC, LTV, MRR, ROI) con NumPy. |
| **Desarrolladores & MCP** | No disponible. | **Developer Portal**: Sandbox de API v1 y gestión de Servidores MCP. |
| **Control de Acceso** | Usuarios estándar. | Control granular de empleados con acceso web (`Employee.has_web_access`). |

---

## 3. Arquitectura Técnica de `enterprise-frontend`

* **Framework**: Next.js 16+ (App Router) con React 19.
* **Estilos y Tokens**: Tailwind CSS con `enterprise.css` (tokens de diseño Dark Glassmorphism, bordes translúcidos y micro-animaciones con Framer Motion).
* **Proxy y Conectividad**: Configurado en `next.config.ts` para reenviar peticiones API directamente al backend FastAPI (`http://127.0.0.1:5010`).
* **Internacionalización**: Soporte completo para Español (`es`), Inglés (`en`) y Portugués (`pt`).
* **Gestión de Procesos**: Administrado por PM2 bajo el nombre `aikrofy-enterprise` en el puerto `3012`.

---

**Desarrollado por Jonnathan Peña para WEBLIFETECH.**
