# Análisis de Negocio Aikrofy: GPT-5 Nano (Edición Junio 2026)

Este documento actualiza los costos y proyecciones de Aikrofy utilizando los precios oficiales de **GPT-5 Nano** vigentes a junio de 2026.

---

## 1. Costos Reales de API (OpenAI GPT-5 Nano)

A partir de agosto de 2025, OpenAI introdujo GPT-5 Nano con una estructura de costos disruptiva para el mercado de agentes de alto volumen.

### 1.1 Tarifas por 1M de Tokens
| Tipo de Token | Precio API (USD) |
| :--- | :--- |
| **Input (Entrada)** | **$0.05** |
| **Output (Salida)** | **$0.40** |
| **Cached Input (Cacheado)** | **$0.005** (90% de descuento) |

### 1.2 Costo por Mensaje (1 Crédito Aikrofy)
Considerando un uso intensivo de herramientas (RAG + LangGraph + Contexto):
- **Input promedio:** 3,000 tokens ($0.00015)
- **Output promedio:** 150 tokens ($0.00006)
- **Costo de API por respuesta:** **$0.00021 USD**

---

## 2. Costo Operativo Total y Valor del Crédito

Para calcular la rentabilidad real, sumamos el costo de API con la infraestructura (Servidores, Base de Datos, Pinecone, LiveKit).

*   **Costo API (GPT-5 Nano):** $0.00021 USD
*   **Overhead de Infraestructura:** $0.00100 USD (Servidores + Soporte)
*   **Costo Real Interno por Crédito:** **$0.00121 USD**

### 2.1 Propuesta de Precio de Venta (Créditos)
Para mantener una rentabilidad del **75% - 85%**, se sugeriría el siguiente precio de venta para recargas (Top-ups):

| Estrategia | Precio Venta Crédito | Margen Bruto | Percepción del Cliente |
| :--- | :--- | :--- | :--- |
| **Agresiva** | **$0.005 USD** | **75.8%** | "Casi gratis" ($5 por 1,000 créditos) |
| **Equilibrada** | **$0.010 USD** | **87.9%** | "Precio justo" ($10 por 1,000 créditos) |
| **Premium** | **$0.020 USD** | **93.9%** | "Calidad GPT-5" ($20 por 1,000 créditos) |

---

## 3. Estimación de Uso y Capacidad por Plan

A continuación, se detalla qué puede hacer un usuario real con los créditos incluidos en cada plan, considerando que **1 Conversación completa ≈ 8 mensajes (créditos)**.

### 🥊 Plan JAB ($29/mes)
*   **Créditos Incluidos:** **2,000 créditos**
*   **Capacidad Mensual:**
    *   **Conversaciones de Venta/Soporte:** ~250 chats completos.
    *   **Procesos de Agendamiento:** ~150 citas gestionadas de punta a punta.
    *   **Emails automáticos:** 2,000 envíos (si se usa solo para eso).
*   **Costo para nosotros:** ~$2.42 USD
*   **Rentabilidad Bruta:** **91.6%**

### 🥊 Plan UPPERCUT ($99/mes)
*   **Créditos Incluidos:** **10,000 créditos**
*   **Capacidad Mensual:**
    *   **Conversaciones Multicanal:** ~1,250 chats.
    *   **Seguimientos de CRM:** ~800 seguimientos activos automáticos.
    *   **Gestión E-commerce:** ~400 órdenes creadas y consultadas.
*   **Costo para nosotros:** ~$12.10 USD
*   **Rentabilidad Bruta:** **87.7%**

### 🥊 Plan KNOCKOUT ($299/mes)
*   **Créditos Incluidos:** **40,000 créditos**
*   **Capacidad Mensual:**
    *   **Atención Masiva:** ~5,000 conversaciones.
    *   **Flujos Complejos (Voz + Texto):** ~2,000 atenciones de voz híbridas.
    *   **Sincronización ERP/CRM Total:** Ilimitada dentro del margen de créditos.
*   **Costo para nosotros:** ~$48.40 USD
*   **Rentabilidad Bruta:** **83.8%**

---

## 4. Análisis de "Marketing vs Realidad"

### 4.1 Por qué GPT-5 Nano es la mejor opción:
1.  **Marketing:** El nombre "GPT-5" vende por sí solo. Es la frontera tecnológica. Ningún competidor ofreciendo "GPT-4" puede competir en percepción de valor.
2.  **Economía:** A $0.05/1M de tokens, el costo es insignificante comparado con el valor que aporta la automatización.
3.  **Velocidad:** La arquitectura Nano está diseñada para latencias inferiores a los 200ms, ideal para WhatsApp y Chat en vivo.

### 4.2 Métricas de Seguimiento y Atención:
- **Atención:** El agente puede mantener conversaciones de hasta 400k tokens de contexto sin perder el hilo, permitiendo un seguimiento impecable de tickets de soporte largos.
- **Procesos:** Con el ahorro en tokens de entrada (Prompt Caching al 90% de descuento), los procesos repetitivos (como el check de disponibilidad de calendario) cuestan virtualmente **$0.000005** por ejecución.

---

## 5. Conclusión Final

Aikrofy está sentado sobre una mina de oro operativa gracias a GPT-5 Nano. Al cobrar **$0.005 - $0.01 por crédito**, no solo destruyes a la competencia en precio, sino que mantienes márgenes de beneficio superiores al **80%**, permitiendo reinvertir en adquisición de clientes y desarrollo de nuevos agentes especializados.

**Acción Sugerida:** Actualizar `seed_plans.py` y `paddle_service.py` junto con los precios mapeados en el webhook de Paddle para reflejar estas nuevas cuotas de créditos y paquetes de recarga más generosos pero altamente rentables.
