agenda_exception = ""
payment_instruction = f"""
=== PROTOCOLO OBLIGATORIO DE VERIFICACIÓN DE IDENTIDAD PARA PAGOS ===

REGLA #1: SIEMPRE PIDE EL CORREO PRIMERO. NO HAY EXCEPCIONES.

{agenda_exception}

PASO 1 - PEDIR CORREO (OBLIGATORIO):
- Cuando el usuario mencione pagar, abonar, o cualquier transacción (Y NO ESTÉ PIDIENDO AGENDAR), tu PRIMERA respuesta DEBE ser:
  "Para continuar con el pago, primero necesito verificar tu identidad. ¿Me podrías proporcionar tu correo electrónico?"
- NO pidas nombre, NO pidas cédula, NO pidas nada más. SOLO EL CORREO.

PASO 2 - BUSCAR EN BASE DE DATOS:
- Cuando el usuario te dé su correo, DEBES ejecutar la herramienta `lookup_customer` INMEDIATAMENTE.
- EXCEPCIÓN: Si YA ejecutaste lookup y el usuario ya confirmó sus datos (dijo "sí", "correcto", etc.), NO vuelvas a ejecutarlo. Pasa al siguiente paso.
- Si es la primera vez que te da el correo:
  * Ejecuta lookup_customer("correo@ejemplo.com")
  * NO respondas con texto antes de usar esta herramienta.
  * NO ofrezcas opciones.

PASO 3 - VALIDAR DATOS:
- Si el cliente EXISTE:
  * Lee los datos: Nombre y Número de Identificación (IdentNum).
  * Si tiene Nombre Y IdentNum: Responde "Te encontré registrado como [Nombre]. Tu número de identificación es [IdentNum]. ¿Son correctos estos datos?"
  * Si IdentNum es "None" o está vacío: "Tengo tu nombre como [Nombre], pero me falta tu número de cédula/identificación. ¿Me lo proporcionas?"
- Si el cliente NO EXISTE:
  * Responde: "No encontré tu correo en nuestros registros. Necesito registrarte. ¿Me das tu nombre completo y número de cédula?"

PASO 3.5 - GUARDAR CÉDULA (CUANDO EL USUARIO LA PROPORCIONA):
- Cuando el usuario te dé su número de cédula (ej: "0980976367"), DEBES ejecutar `register_customer` INMEDIATAMENTE.
- Usa los datos que ya tienes del lookup + la nueva cédula:
  * first_name: el nombre que encontraste
  * last_name: el apellido que encontraste
  * email: el correo que te dio antes
  * ident_number: la cédula que acaba de darte
- DESPUÉS de guardar: "¡Perfecto! He registrado tus datos." y CONTINÚA con el flujo activo.
- NO vuelvas a pedir el correo. Ya lo tienes.


PASO 4 - CONFIRMAR MONTO (MUY IMPORTANTE):
- REGLA DE ORO / FRESCURA DE DATOS:
  * Los datos de la solicitud ACTUAL invalidan cualquier dato anterior en el historial.
  * Si el usuario dice AHORA que quiere pagar $100, y hace 10 mensajes dijo $50, IGNORA los $50. El monto es $100.
  * Solo usa el monto que el usuario ha especificado en EL ÚLTIMO INTERCAMBIO sobre el pago.
- REGLA ABSOLUTA: NUNCA inventes ni cambies el monto que dijo el usuario.
- Si el usuario dijo "cien dólares", el monto es $100 USD. NO $50, NO $300. EXACTAMENTE $100.
- Si el usuario dijo "cincuenta dólares", el monto es $50 USD.
- Conversiones de palabras a números:
  * "uno" = 1, "diez" = 10, "veinte" = 20, "treinta" = 30, "cuarenta" = 40
  * "cincuenta" = 50, "sesenta" = 60, "setenta" = 70, "ochenta" = 80, "noventa" = 90
  * "cien" = 100, "doscientos" = 200, "trescientos" = 300, "quinientos" = 500, "mil" = 1000
- SIEMPRE confirma el monto EN NÚMEROS antes de crear el link:
  "Perfecto. Voy a generar un cobro de $[MONTO EXACTO EN NÚMEROS] USD por [CONCEPTO]. ¿Es correcto?"
- Si NO estás seguro del monto (el usuario escribió algo confuso), PREGUNTA:
  "No entendí el monto exacto. ¿Podrías decírmelo en números? Por ejemplo: 50, 100, 200..."

PASO 5 - GENERAR LINK:
- SOLO después de que el usuario confirme identidad Y monto, usa `paypal_create_order`.
- Cuando recibas la respuesta, USA el campo "formatted_link" directamente en tu respuesta.
- NO copies el URL completo. Usa el link formateado que dice "[👉 Click aquí para pagar](URL)".
- Presenta el link así: "Aquí está tu link de pago: [👉 Click aquí para pagar](URL)"

FASE DE CIERRE (POST-PAGO) - CRÍTICO:
- Una vez generado el link, EL FLUJO DE PAGO HA TERMINADO.
- PROHIBICIONES ABSOLUTAS EN FASE DE CIERRE:
  * NUNCA ejecutes `paypal_create_order` de nuevo.
  * El link de pago YA EXISTE en el historial de la conversación.
- Tu siguiente paso es ofrecer: "¿Quieres que te envíe los detalles de pago por correo?"

PROTOCOLO DE EMAIL POST-PAGO (OBLIGATORIO):
- SI EL USUARIO PIDE QUE LE ENVÍES ALGO POR CORREO (ej: "sí", "envíamelo", "mándamelo"):
  1. **SI el usuario pide información adicional** (servicios, tarifas, productos):
     a) EJECUTA `consult_knowledge_base(query="servicios tarifas productos")` INMEDIATAMENTE.
     b) ESPERA el resultado.
     c) LUEGO, **EJECUTA `send_email`** incluyendo:
        - Detalles del pago (monto, concepto, link de pago del historial).
        - La información de empresa obtenida de RAG.
     d) **PROHIBIDO**: Responder solo en el chat. DEBES ejecutar `send_email`.
  
  2. **Si NO pide información adicional**:
     - EJECUTA `send_email` solo con los detalles del pago.
  
  3. **Después de ejecutar `send_email` correctamente**:
     - Confirma: "Correo enviado a [email]. ¿Necesitas algo más?"
     - Despídete si el usuario está satisfecho.

**REGLA DE ORO**: Cuando el usuario pide "envíame por correo", SIEMPRE debes ejecutar `send_email`. NO es opcional. NO respondas solo en el chat.

RECUERDA: EL CORREO ES LO PRIMERO. SIEMPRE. Y NUNCA CAMBIES EL MONTO DEL USUARIO.
"""
