# 🎙️ Documentación de Arquitectura e Implementación de Voz y Audio - Aikrofy (V3.0)

**Proyecto:** Multi-agent SaaS Ecosystem (Aikrofy)  
**Dominio:** `aikrofy.com`  
**Tecnología:** FastAPI (ASGI) + LangGraph + Celery + Next.js 16 (React 19) + edge-tts + Whisper-1 + Groq + OpenRouter  
**Estado:** **[100% IMPLEMENTADO, BLINDADO Y EN PRODUCCIÓN - SEPTIEMBRE 2026]**  
**Derechos de Autor:** Copyright © 2026 WEBLIFETECH (Jonnathan Peña). Todos los derechos reservados.

---

## 1. Visión y Resiliencia del Subsistema de Audio y Voz

El subsistema de voz de **Aikrofy** está diseñado bajo una arquitectura de alta disponibilidad, tolerancia a fallos y cero fricción ($Friccion \to 0$). Administra el ciclo completo de:
1. **Recepción Omnicanal:** Entrada de notas de voz desde WhatsApp (vía microservicio Baileys Node.js), Widget Webchat y Chat Playground (WebM Opus / Safari AAC).
2. **Normalización de Formatos de Audio:** Conversión automática vía FFmpeg a 16kHz mono MP3.
3. **Cascada Speech-To-Text (STT):** Transcripción multinivel con 4 proveedores jerarquizados.
4. **Razonamiento Cognitivo (LangGraph / AgentService):** Ingesta del texto transcrito en el estado conversacional, persistencia en base de datos (`messages`), resolución de herramientas y generación de respuesta ejecutiva.
5. **Cascada Text-To-Speech (TTS):** Síntesis de voz neural multilingüe con detección de género (`AgentGender`), limpieza de texto para TTS y prevención de bloqueos de Event Loop en FastAPI.
6. **Tarificación y Balance de Créditos:** Deducción atómica con margen bruto del ~85% mediante `TokenCreditService`.

---

## 2. Arquitectura de Backend (`backend/services/voice_service.py`)

La gestión de voz está encapsulada en la clase [VoiceService](file:///root/aikrofy/backend/services/voice_service.py):

### A. Normalización de Audio (`_normalize_audio`)
- Convierte cualquier formato de audio de entrada (`.webm`, `.ogg`, `.opus`, `.m4a`, `.wav`, `.aac`) a **16kHz mono MP3** utilizando `ffmpeg` (`libmp3lame`, 64k) antes de enviarlo a los motores de transcripción.
- Si FFmpeg no está disponible o el archivo ya es compatible, retorna el archivo original de forma segura.

### B. Cascada de Transcripción STT (`VoiceService.transcribe`)
El método procesa el audio probando secuencialmente cada motor en orden de costo y velocidad:
1. **Prioridad 0 — Micro-Engine Privado (`media.weblifetech.com`):**
   - URL: `https://media.weblifetech.com/api/micro/audio/transcribe` (o `MEDIA_MICRO_STT_URL`).
   - Autenticación: `EXTERNAL_API_KEY` (Bearer / X-API-Key).
   - Motor dedicado sin carga de CPU local en el VPS.
2. **Prioridad 0.5 — API Externa de Transcripción:**
   - URL: `https://media.weblifetech.com/api/external/transcribe` (o `MEDIA_STT_URL`).
3. **Prioridad 1 — Groq Whisper (`whisper-large-v3`):**
   - Transcripción ultra-rápida en hardware LPU (~300ms).
   - Autenticación: `GROQ_API_KEY`.
4. **Prioridad 2 — OpenRouter Whisper (`openai/whisper-1`):**
   - Transcripción base64 mediante `https://openrouter.ai/api/v1/audio/transcriptions`.
   - Autenticación: `OPENROUTER_API_KEY`.
5. **Prioridad 3 — OpenAI Whisper (`whisper-1`):**
   - SDK oficial de OpenAI `client.audio.transcriptions.create`.
   - Autenticación: `OPENAI_API_KEY`.

### C. Limpieza y Normalización para TTS (`VoiceService.clean_text_for_tts`)
Antes de sintetizar la voz, el texto se prepara meticulosamente para evitar pronunciaciones robóticas:
- Reemplaza slugs técnicos por etiquetas legibles: `core_identity` $\to$ *"Identidad Core"*, `payment_protocol` $\to$ *"Protocolo de Pagos"*.
- Sustituye símbolos: guiones bajos (`_`) por espacios, barras (`/`) por *" o "*.
- Remueve enlaces HTTP, marcas de Markdown (`**`, `__`, `` ` ``, `#`).
- Mantiene acrónimos estándar (USA, RUC, PDF, URL, API, DNI, IVA, USD, EUR, GPS, CRM, ERP, FAQ, SMS, HTML, CSS, SQL) y convierte palabras en mayúsculas sostenidas a formato Capitalizado para que el TTS las lea como palabras en lugar de deletrearlas letra por letra.

### D. Cascada de Síntesis TTS (`VoiceService.synthesize`)
1. **Prioridad 0 — Local Edge-TTS (Zero Latency & Alta Fidelidad):**
   - Utiliza la librería `edge_tts`.
   - **Prevención de Conflictos de Event Loop:** Si el event loop de FastAPI está en ejecución, delega la tarea a un `concurrent.futures.ThreadPoolExecutor` aislado con `asyncio.run()` local, evitando excepciones de `RuntimeError: This event loop is already running`.
2. **Prioridad 0.5 — API Remota Edge-TTS (`media.weblifetech.com/api/tts/speak`):**
   - Petición HTTP POST autenticada para respaldo en caso de fallos locales.
3. **Prioridad 1 — Groq TTS (`canopylabs/orpheus-v1-english`):**
   - Si está configurado `GROQ_API_KEY`.
4. **Prioridad 2 — OpenRouter TTS (`hexgrad/kokoro-82m`):**
   - Si está configurado `OPENROUTER_API_KEY`.
5. **Prioridad 3 — HuggingFace TTS (`facebook/mms-tts-spa`):**
   - Si está configurado `HUGGINGFACE_API_KEY`.
6. **Prioridad 4 — OpenAI TTS (`tts-1`):**
   - Voces neurales `nova` (femenino) y `onyx` (masculino).

### E. Resolución Inteligente de Voces (`VoiceService.resolve_smart_voice`)
- Analiza el género asignado al agente (`female`, `male`, `neutral`) y el idioma de interfaz (`es`, `en`, `pt`).
- Voces recomendadas:
  - Español Femenino: `es-MX-DaliaNeural`
  - Español Masculino: `es-MX-JorgeNeural`
  - Inglés Femenino: `en-US-AriaNeural` / `en-US-JennyNeural`
  - Inglés Masculino: `en-US-GuyNeural` / `en-US-ChristopherNeural`
  - Portugués Femenino: `pt-BR-FranciscaNeural`
  - Portugués Masculino: `pt-BR-AntonioNeural`

---

## 3. Endpoints API de Audio y Voz (`backend/routes/voice.py`)

Todos los endpoints residen bajo el prefijo `/api/voice`:

| Método | Endpoint | Autenticación | Rol y Descripción |
|---|---|---|---|
| **`POST`** | `/api/voice/interact` | `@jwt_required()`, `@subscription_required` | **Endpoint central de notas de voz en chat.** Recibe `file` (WebM/MP3) + `channel` (`admin_chat` o `playground`) + `interface_language`. Transcribe con Whisper, persiste mensaje `USER` en base de datos, procesa con `AgentService` / LangGraph, genera respuesta `ASSISTANT`, sintetiza audio MP3 con Edge-TTS, deduce créditos con `TokenCreditService` y retorna JSON con transcripción, respuesta y `audio_url`. |
| **`POST`** | `/api/voice/synthesize` | `@jwt_required()`, `@subscription_required` | Síntesis bajo demanda de cualquier texto arbitrario para empresas autenticadas. Recibe `{text, interface_language, gender, voice}`. |
| **`POST`** | `/api/voice/synthesize-public` | Pública | Síntesis para el widget webchat público con soporte de `widget_id` para heredar las preferencias de voz de la empresa cliente. |
| **`POST`** | `/api/voice/transcribe-public` | Pública | Transcripción de audio pública para visitantes web. |
| **`GET`** | `/api/voice/voices` | `@jwt_required()` | Listado de voces neurales disponibles categorizadas por idioma y género. |
| **`GET`** | `/api/voice/audio/<filename>` | Pública | Sirve archivos de audio generados (`FileResponse`) con tipo MIME `audio/mpeg`. |

---

## 4. Reglas Estrictas de Programación y Base de Datos en Rutas de Voz

Para evitar fallos en tiempo de ejecución o regresiones futuras:
1. **Regla de Ámbito de Importación de Base de Datos:**
   - `db` se importa estrictamente a nivel de módulo (`from extensions import db`). **PROHIBIDO** reimportar `from extensions import db` dentro de bloques `try/except` internos de funciones, ya que causa `UnboundLocalError: cannot access local variable 'db' where it is not associated with a value` en los accesos previos.
2. **Definición de Rutas de Salida de Archivos:**
   - Antes de invocar a `VoiceService.synthesize(text, voice_name, output_path)`, `output_path` **DEBE** estar explícitamente definido:
     ```python
     output_filename = f"out_{uuid.uuid4().hex}.mp3"
     output_path = os.path.join(UPLOAD_VOICE_DIR, output_filename)
     ```
3. **Aislamiento de Sesión para Asistente:**
   - Las escrituras concurrentes del mensaje de respuesta utilizan `SessionLocal()` independiente para garantizar persistencia inmediata incluso si la conexión HTTP principal sufre micro-cortes.
4. **Deducción de Créditos con Margen:**
   - Toda interacción de voz calcula el costo real de STT y TTS (por minuto y por 1,000 caracteres) y descuenta del `credit_balance` de la empresa vía `TokenCreditService.deduct_company_credits`.

---

## 5. Integración con Canales Omnicanal (WhatsApp & LiveKit)

### A. WhatsApp Asíncrono (`api-whatsapp` + Celery + Redis Puerto 6380)
1. **Recepción en Node.js:** Microservicio con `@whiskeysockets/baileys` (`BaileysTransporter`) detecta `audioMessage`, descarga los bytes a disco y despacha el payload vía POST al webhook de FastAPI (`/api/webhooks/whatsapp`).
2. **Encolamiento Celery:** FastAPI delega el procesamiento a la tarea `process_whatsapp_audio_message` en Celery.
3. **Transcripción y Respuesta:** Celery ejecuta `VoiceService.transcribe`, consulta a LangGraph, genera el audio de respuesta con `VoiceService.synthesize` y despacha el audio a WhatsApp mediante `MessagingService.send_whatsapp_media`.

### B. Telefonía Realtime LiveKit WebRTC
- Módulo `livekit_service.py` y rutas `routes/livekit_routes.py`.
- Genera tokens SIP/WebRTC para interacción por voz en tiempo real con latencias inferiores a **300ms**, compartiendo las directrices del modelo `Agent`.

---

## 6. Frontend y Componentes de Voz (Next.js 16 / React 19)

1. **`AIChatSidebar.tsx` & `chat-widget.tsx`:**
   - Grabación mediante `navigator.mediaDevices.getUserMedia({ audio: true })` y `MediaRecorder`.
   - Empaquetado en `Blob` tipo `audio/webm`.
   - Envío mediante `FormData` con claves `file`, `channel: 'admin_chat'`, `interface_language: i18n.language`.
   - Reproducción automática mediante elemento `new Audio(fullAudioUrl).play()`.
   - Manejo de excepciones visual en burbujas de chat ante errores HTTP 500 o fallos de conexión.
2. **Configuración de Agentes (`/settings/agents`):**
   - Selector dinámico de voces neurales y prueba de muestra de audio interactiva.

---
**Desarrollado y certificado por Jonnathan Peña para WEBLIFETECH.**
