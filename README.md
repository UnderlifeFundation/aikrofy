# Aikrofy — Agentic OS & Multi-Agent Workforce (V4.0)

[![License: PolyForm Noncommercial](https://img.shields.io/badge/License-PolyForm%20Noncommercial-blue.svg)](LICENSE.md)
[![Lanzador: Fundación Underlife](https://img.shields.io/badge/Lanzador-Fundación%20Underlife-10b981.svg)](OPENCORE_MANIFESTO.md)
[![Ingeniería: WEBLIFETECH](https://img.shields.io/badge/Ingeniería%20%26%20Enterprise-WEBLIFETECH-8b5cf6.svg)](https://weblifetech.com)
[![Cloud: aikrofy.com](https://img.shields.io/badge/Cloud%20Subvencionado-aikrofy.com-f59e0b.svg)](https://aikrofy.com)

**Aikrofy** es una plataforma y Sistema Operativo Agéntico (Agentic OS) que democratiza la fuerza laboral autónoma para negocios de todas las escalas. Permite a cualquier emprendedor, microempresa, PyME o corporación automatizar sus procesos, vender, agendar citas, cobrar y atender en **WhatsApp, Webchat, Voz en tiempo real, API REST y MCP**.

> 🏛️ **Lanzamiento Institucional:** Plataforma lanzada por **FUNDACIÓN UNDERLIFE** para impulsar la economía popular, el emprendimiento y la inclusión productiva digital.
> 
> ⚡ **Ingeniería, Mantenimiento & Escalamiento:** Co-desarrollada, mantenida y operada comercialmente para el sector Enterprise por **WEBLIFETECH** (Dirección: Jonnathan Peña) junto con la comunidad open-source.

---

## 🏛️ Modelo de Ecosistema: Ediciones y Escalabilidad

```
[ Community Edition (Open-Core) ] ──▶ [ Cloud Social Subvencionado ] ──▶ [ Enterprise & Scale ]
       Fundación Underlife                Fundación Underlife + WLT            WEBLIFETECH
     (Uso Libre No Comercial)           (Beca Créditos de Bienvenida)      (SLA Corp, ERPs, C-Suite)
```

| Dimensión | Community Edition (Open-Core) | Cloud Subvencionado (PyMEs / Micro) | Cloud & On-Premise Enterprise |
| :--- | :---: | :---: | :---: |
| **Gobernanza / Operación** | **Fundación Underlife** | **Fundación Underlife** (Subsidio) | **WEBLIFETECH** (Comercial / SLA) |
| **Licencia** | PolyForm Noncommercial 1.0.0 | Términos de Servicio Cloud | Licencia Comercial Enterprise |
| **Público Objetivo** | Estudiantes, comunidad, investigación, ONGs | Emprendedores, micro-negocios y PyMEs | Medianas, grandes corporaciones y agencias |
| **Créditos de Bienvenida** | N/A (Usa claves propias / local) | **5,000 - 10,000 créditos cortesía gratis** | Bolsa mensual contratada / BYOK |
| **Agotamiento de Cortesía**| N/A | Recarga On-Demand ($5, $10, $20) sin forzar suscripción | Contrato recurrente o Enterprise Tailored |
| **Capacidades Base** | Agente Krof + WhatsApp Baileys + Widget Web | Krof + WhatsApp + CRM + Micro-recargas | Krof + C-Suite (7 agentes) + Voz LiveKit |
| **Integraciones Avanzadas**| API REST local | Catálogo, Citas, Pasarelas de Pago | ERP (SAP, Dynamics), CRM (HubSpot, Salesforce) |
| **Soporte** | Comunitario / GitHub Issues | Soporte estándar vía ticket | Soporte 24/7 con SLA dedicado |

---

## 📚 Documentación Esencial
1. 📖 **[OPENCORE_MANIFESTO.md](OPENCORE_MANIFESTO.md)** — Manifiesto de impacto social y modelo de co-desarrollo Fundación Underlife & WEBLIFETECH.
2. ⚖️ **[LICENSE.md](LICENSE.md)** — Licencia PolyForm Noncommercial 1.0.0 para uso comunitario.
3. 📖 **[COMPENDIO_MAESTRO_AIKROFY.md](COMPENDIO_MAESTRO_AIKROFY.md)** — Dossier técnico definitivo (arquitectura, 57 tablas, 96 servicios, ~335 endpoints).
4. 🗺️ **[ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md)** — Mapa de archivos, puertos e integraciones.
5. 🤖 **[AGENTS.md](AGENTS.md)** & **[GEMINI.md](GEMINI.md)** — Directivas de desarrollo y operación agéntica.

---

## 🚀 Despliegue Rápido (Community Edition)

### Requisitos
- Node.js 20+ y Python 3.11+
- Redis 7+ (opcional para colas en modo ligero)

```bash
# 1. Clonar el repositorio
git clone https://github.com/UnderlifeFundation/aikrofy.git
cd aikrofy

# 2. Configurar variables de entorno comunitarias
cp .env.community.example .env

# 3. Opción A: Levantar con Docker Compose (Recomendado)
docker compose -f docker-compose.community.yml up -d

# 3. Opción B: Iniciar manualmente Backend FastAPI y Frontend Web
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn fastapi_app:app --host 0.0.0.0 --port 5010 --reload

# En otra terminal: iniciar Frontend Next.js (Puerto 3010)
cd frontend
npm install
npm run dev
```

---

## 🛠️ Desarrollo y Sincronización Dual-Repo (Cloud vs. Open-Core)

El ecosistema opera en dos repositorios sincronizados:
1. **Edición Cloud & Enterprise (Privado — WEBLIFETECH):** Despliegue continuo hacia staging (`dev`) y producción (`main`) en `aikrofy.com`.
2. **Edición Community Open-Core (Público — Fundación Underlife):** Repositorio oficial en [`UnderlifeFundation/aikrofy`](https://github.com/UnderlifeFundation/aikrofy.git). Para publicar actualizaciones desde el entorno de ingeniería hacia el repositorio público (excluyendo automáticamente CI/CD privado, conectores LEM y configuraciones internas), ejecutar:
   ```bash
   ./scripts/sync-opencore.sh
   ```

---

## 🌐 Edición Cloud Gestionada
Para acceder a la plataforma completa multi-tenant en producción con infraestructura gestionada, analíticas avanzadas, pasarelas de pago integradas y voz en tiempo real:
👉 **[Acceder a Aikrofy Cloud (aikrofy.com)](https://aikrofy.com)**

---

**© 2026 FUNDACIÓN UNDERLIFE & WEBLIFETECH.**  
*Innovación para la soberanía operativa y la equidad económica.*
