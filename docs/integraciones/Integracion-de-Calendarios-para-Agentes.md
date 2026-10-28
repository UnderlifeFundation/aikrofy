# **Arquitectura de Integración de Agentes Autónomos con Servicios de Calendario y Videoconferencia**

La confluencia de modelos de lenguaje avanzados y arquitecturas orientadas a eventos permite la creación de plataformas agénticas capaces de coordinar agendas, programar eventos multicanal y sintetizar discusiones corporativas de forma autónoma1. El diseño de una solución de esta envergadura exige articular un backend asíncrono en FastAPI con un motor multiagente sustentado en LangGraph, gobernado a través de una interfaz moderna desarrollada en Next.js2. La interacción con los tres ecosistemas dominantes de trabajo colaborativo—Google Workspace, Microsoft 365 y Zoom—requiere un conocimiento profundo de sus modelos de recursos, esquemas de autorización OAuth 2.0 y mecanismos de notificación reactiva5.

## **Fundamentos y Topología del Sistema Multiagente**

La arquitectura se articula como un sistema distribuido y desacoplado, dividido en capas funcionales con responsabilidades operativas bien definidas. La persistencia transaccional y el aislamiento de contexto garantizan la tolerancia a fallos en flujos de larga duración, especialmente cuando se requiere intervención humana previa a la ejecución de acciones irreversibles en calendarios corporativos4.

&nbsp;

| Capa del Sistema | Módulo Tecnológico | Responsabilidad Operativa Principal | Protocolos y Mecanismos de Red |
| :---- | :---- | :---- | :---- |
| **Presentación** | Next.js (App Router, React Server Components) | Renderizado reactivo de la interfaz conversacional, recepción de streams de respuesta y presentación de interfaces de aprobación interactiva (*Human-in-the-Loop*)3. | HTTP/2, Server-Sent Events (SSE), WebSockets. |
| **API Gateway** | FastAPI (Python 3.11+) | Punto de entrada unificado, enrutamiento, terminación de sesiones autenticadas mediante JWT, renovación de credenciales OAuth y validación criptográfica de webhooks10. | HTTPS, JSON REST, firmas HMAC-SHA25611. |
| **Orquestación Agéntica** | LangGraph & LangChain Core | Definición de grafos de estados finitos cíclicos, preservación de puntos de control de ejecución, despacho de herramientas especializadas y gestión de pausas por interrupción4. | I/O asíncrono sobre event loops nativos de Python. |
| **Capa de Persistencia** | PostgreSQL con extensiones relacionales y pgvector | Almacenamiento seguro de llaves criptográficas, tokens de actualización cifrados, estados de hilos de LangGraph (AsyncPostgresSaver) y representaciones vectoriales de minutas4. | Conexiones concurrentes pooled vía SQLAlchemy / Asyncpg. |
| **Servicios Externos** | Google Workspace, Microsoft 365, Zoom API | Plataformas empresariales de calendario, gestión de salas virtuales, generación de transcripciones nativas y resúmenes estructurados mediante IA5. | REST APIs (JSON, WebVTT), Google Cloud Pub/Sub, Webhooks11. |

El flujo de control se inicia cuando una solicitud de usuario ingresa desde la capa de presentación de Next.js hacia el gateway en FastAPI. El framework de backend valida el contexto de identidad del usuario y recupera o inicializa un identificador de hilo (thread\_id), canalizando la solicitud hacia el grafo compilado de LangGraph4. Durante el recorrido del grafo, los agentes analizan la semántica de la consulta para decidir si deben invocar operaciones de consulta pasiva o mutaciones activas sobre los calendarios4.

Cuando el modelo de lenguaje planifica la programación, alteración sustancial o cancelación de una reunión existente, la ejecución del grafo se interrumpe determinísticamente mediante la invocación de la primitiva interrupt(), quedando el estado transaccional congelado en el almacenamiento persistente3. FastAPI transmite una señal estructurada hacia Next.js mediante Server-Sent Events3. Una vez que el usuario examina y aprueba la acción en la interfaz, un endpoint de FastAPI recibe la confirmación y reanuda el grafo mediante un objeto Command(resume=...), posibilitando que la herramienta ejecute la llamada final contra la API externa12.

## **Integración con Google Workspace: Google Calendar y Google Meet API**

El entorno de Google Workspace desacopla la administración de eventos temporales de la inspección de contenidos generados durante las sesiones en vivo5. La gestión de la agenda y el aprovisionamiento de salas recae en la Google Calendar API (v3), mientras que la recuperación de grabaciones, participantes y transcripciones textuales se canaliza a través de la Google Meet REST API (v2)5.

### **Autorización y Configuración de Alcances**

El acceso seguro requiere el registro de una aplicación en Google Cloud Platform con el protocolo de consentimiento OAuth 2.0 debidamente configurado18. Para la administración integral de eventos de agenda, se requiere el alcance https://www.googleapis.com/auth/calendar, el cual autoriza operaciones de lectura, inserción, actualización y borrado tanto en el calendario primario como en calendarios secundarios compartidos con el usuario autenticado5. Cuando el agente necesita inspeccionar espacios de videoconferencia y recuperar las sesiones post-reunión, deben incorporarse los alcances restringidos https://www.googleapis.com/auth/meetings.space.created o https://www.googleapis.com/auth/meetings.space.readonly14.

### **Operaciones de Calendario y Generación Dinámica de Enlaces Meet**

Para insertar un nuevo evento que incorpore una sala de Google Meet, la aplicación emite una solicitud HTTP POST contra el recurso de eventos del calendario correspondiente5. Es un requisito indispensable incluir el parámetro de consulta conferenceDataVersion=1 en la URL del endpoint; la omisión de este parámetro provoca que el motor de Google Calendar descarte silenciosamente la directiva de creación de la sala sin arrojar errores explícitos20.

&nbsp;

&nbsp;

&nbsp;

HTTP

POST https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1\&sendUpdates=all HTTP/1.1  
Authorization: Bearer \<ACCESS\_TOKEN\>  
Content-Type: application/json

{  
  "summary": "Sesión de Planificación Arquitectónica",  
  "description": "Revisión técnica de especificaciones para el backend del sistema multiagente.",  
  "start": {  
    "dateTime": "2026-05-15T09:00:00-05:00",  
    "timeZone": "America/Bogota"  
  },  
  "end": {  
    "dateTime": "2026-05-15T10:00:00-05:00",  
    "timeZone": "America/Bogota"  
  },  
  "attendees": \[  
    {"email": "arquitectura@empresa.com"},  
    {"email": "desarrollo@empresa.com", "optional": true}  
  \],  
  "conferenceData": {  
    "createRequest": {  
      "requestId": "agent-req-98234-uuid4",  
      "conferenceSolutionKey": {  
        "type": "hangoutsMeet"  
      }  
    }  
  }  
}

La propiedad requestId actúa como un token de idempotencia generado en el cliente que previene la asignación duplicada de salas si ocurren reintentos de red20. En la respuesta devuelta por el servidor, la propiedad conferenceData.entryPoints aloja el objeto de tipo video con la URI canónica de la reunión (https://meet.google.com/xxx-yyyy-zzz)21. El parámetro sendUpdates=all asegura la transmisión automática de invitaciones por correo electrónico a todos los participantes5.

Las operaciones complementarias siguen estrictamente las directrices REST convencionales:

* La actualización de un evento existente se ejecuta mediante PATCH https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events/{eventId}?conferenceDataVersion=1, permitiendo alterar agendas o añadir asistentes sin alterar los enlaces de conferencia previos5.  
* La cancelación se formaliza mediante DELETE https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events/{eventId}?sendUpdates=all, revocando la reserva y notificando a los convocados5.  
* La recuperación cronológica se realiza a través de GET https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events?timeMin=...\&timeMax=...\&singleEvents=true\&orderBy=startTime.

### **Análisis de Agendas y Verificación de Disponibilidad**

El análisis de conflictos de calendario antes de programar una cita se resuelve mediante el endpoint de disponibilidad horaria POST https://www.googleapis.com/calendar/v3/freeBusy. La carga útil suministra una lista de identificadores de usuario bajo el arreglo items, acotada por los parámetros de tiempo timeMin y timeMax. El motor de Google procesa la solicitud y devuelve colecciones de intervalos cerrados rotulados como busy, lo que permite al agente computar de manera matemática los espacios comunes desocupados entre calendarios de diferentes integrantes de la organización.

### **Recuperación Jerárquica de Transcripciones en Meet API**

El acceso a las transcripciones generadas en Google Meet no se produce dentro del objeto del evento del calendario, sino que demanda una navegación jerárquica y secuencial a través de los sub-recursos de la Google Meet REST API v2 (meet.googleapis.com/v2)2. Cuando una llamada concluye formalmente, la plataforma genera un registro de conferencia que debe ser localizado mediante una consulta a GET /v2/conferenceRecords para extraer su correspondiente identificador único (conferenceRecordId)2.

A partir de este identificador, el agente realiza una petición a GET /v2/conferenceRecords/{conferenceRecordId}/transcripts para obtener los metadatos de los documentos de transcripción vinculados a la llamada2. Este recurso no devuelve el texto emitido por los interlocutores, sino las referencias a los artefactos producidos2. Para extraer el cuerpo conversacional, la plataforma agéntica debe consultar el sub-recurso final mediante peticiones paginadas a GET /v2/conferenceRecords/{conferenceRecordId}/transcripts/{transcriptId}/entries2. Cada entrada individual entrega marcas temporales de emisión, el texto segmentado y la asociación con un identificador de participante (participantSession)17.

Los artefactos textuales y audiovisuales de Google Meet no están disponibles en el momento inmediato en que concluye el evento, ya que los motores de procesamiento multimedia operan de manera desacoplada y asíncrona2. Forzar al agente a realizar un sondeo repetitivo mediante bucles de espera agota las cuotas de tasa de la API y degrada el rendimiento de la aplicación2. La arquitectura óptima implementa una suscripción a temas de Google Cloud Pub/Sub que notifican al backend de FastAPI mediante eventos push, como google.workspace.meet.transcript.v2.fileGenerationEnded, indicando con exactitud matemática el momento en que las entradas de texto pueden ser consumidas2.

## **Integración con Microsoft 365: Microsoft Graph API y Microsoft Teams**

Microsoft Graph centraliza el acceso unificado a las capacidades corporativas de la plataforma Microsoft 365, combinando la gestión de eventos en Microsoft Exchange Online con el aprovisionamiento y auditoría de reuniones en Microsoft Teams7.

### **Permisos y Modelo de Acceso en Microsoft Entra ID**

Las aplicaciones agénticas registradas en Microsoft Entra ID deben operar bajo esquemas de permisos cuidadosamente acotados para salvaguardar la privacidad organizacional7. Cuando el sistema interactúa en nombre de un usuario autenticado mediante flujos delegados, se requiere el permiso Calendars.ReadWrite para la manipulación total de la agenda, complementado por OnlineMeetings.ReadWrite para la creación y configuración de instancias de videollamada7.

El consumo de las transcripciones de las conferencias celebradas en Teams demanda el permiso de alta sensibilidad OnlineMeetingTranscript.Read.All13. Si la plataforma agéntica está concebida para ejecutarse como un servicio institucional desatendido sin la presencia de una sesión interactiva humana, los mismos alcances deben asignarse como permisos de aplicación con el debido consentimiento del administrador global del inquilino (*tenant*) de Azure26.

### **Programación Unificada de Calendario y Enlaces de Teams**

La vía más eficiente para coordinar una reunión corporativa en el ecosistema Microsoft radica en el uso directo del endpoint de eventos del calendario del usuario7:

&nbsp;

&nbsp;

&nbsp;

HTTP

POST https://graph.microsoft.com/v1.0/me/events HTTP/1.1  
Authorization: Bearer \<ACCESS\_TOKEN\>  
Content-Type: application/json  
Prefer: outlook.timezone="America/Bogota"

{  
  "subject": "Revisión de Especificaciones Funcionales",  
  "body": {  
    "contentType": "HTML",  
    "content": "Reunión de alineación sobre el desarrollo de agentes con LangGraph y FastAPI."  
  },  
  "start": {  
    "dateTime": "2026-05-18T14:30:00",  
    "timeZone": "America/Bogota"  
  },  
  "end": {  
    "dateTime": "2026-05-18T15:30:00",  
    "timeZone": "America/Bogota"  
  },  
  "attendees": \[  
    {  
      "emailAddress": {  
        "address": "lider.tecnico@empresa.com",  
        "name": "Líder Técnico"  
      },  
      "type": "required"  
    }  
  \],  
  "isOnlineMeeting": true,  
  "onlineMeetingProvider": "teamsForBusiness"  
}

La presencia coordinada de las propiedades booleanas isOnlineMeeting: true y del enumerador onlineMeetingProvider: "teamsForBusiness" instruye a Microsoft Exchange a crear automáticamente una sala de Teams asociada7. La respuesta entrega la información completa del evento, incluyendo el objeto anidado onlineMeeting, cuyo atributo joinUrl expone el enlace directo para los asistentes.

La actualización de detalles se gestiona emitiendo peticiones PATCH https://graph.microsoft.com/v1.0/me/events/{id}, mientras que la baja del evento se realiza a través de DELETE https://graph.microsoft.com/v1.0/me/events/{id}7. Ambas operaciones disparan de forma automática la sincronización con los buzones de los participantes y el envío de notificaciones de cancelación mediante protocolos de mensajería empresarial de Exchange27.

### **Análisis de Agendas Mediante el Recurso getSchedule**

Para discernir la disponibilidad horaria entre múltiples miembros del personal o recursos físicos compartidos dentro de la organización, Microsoft Graph expone la operación especializada POST /me/calendar/getSchedule7:

&nbsp;

&nbsp;

&nbsp;

HTTP

POST https://graph.microsoft.com/v1.0/me/calendar/getSchedule HTTP/1.1  
Authorization: Bearer \<ACCESS\_TOKEN\>  
Content-Type: application/json  
Prefer: outlook.timezone="America/Bogota"

{  
  "schedules": \["analista@empresa.com", "gerencia@empresa.com"\],  
  "startTime": {  
    "dateTime": "2026-05-18T08:00:00",  
    "timeZone": "America/Bogota"  
  },  
  "endTime": {  
    "dateTime": "2026-05-18T18:00:00",  
    "timeZone": "America/Bogota"  
  },  
  "availabilityViewInterval": 30  
}

El parámetro availabilityViewInterval parametriza la duración en minutos de cada partición de tiempo analizada en la jornada24. En la respuesta del servidor, cada usuario se mapea a un objeto scheduleInformation cuyo componente primordial es la cadena compacta availabilityView28. Cada carácter de esta cadena representa un bloque consecutivo indexado en el tiempo y codifica el estado de disponibilidad del usuario29:

&nbsp;

| Carácter Numérico | Estado de Disponibilidad Representado | Interpretación en la Lógica Agéntica |
| :---- | :---- | :---- |
| 0 | Libre (*Free*)29 | Intervalo óptimo admisible para programar reuniones sin fricción. |
| 1 | Tentativo (*Tentative*) | El usuario tiene un compromiso preliminar no formalizado. |
| 2 | Ocupado (*Busy*)29 | Espacio bloqueado por una reunión o cita confirmada. |
| 3 | Fuera de la oficina (*Out of Office*) | El usuario no se encuentra en jornada laboral activa. |
| 4 | Trabajando en otra ubicación (*Working Elsewhere*) | El usuario está disponible de forma remota o alternativa. |

Esta estructura permite al agente evaluar compatibilidades temporales mediante algoritmos de coincidencia de cadenas, buscando secuencias contiguas de ceros entre todos los participantes requeridos sin la necesidad de transferir ni procesar los asuntos privados de sus eventos29.

### **Extracción de Transcripciones y Resúmenes en Teams**

Para recuperar las transcripciones oficiales de Microsoft Teams, el agente requiere disponer del identificador de la reunión en línea (onlineMeetingId)13. Si la sesión se programó a través del calendario de Outlook, este identificador puede obtenerse consultando GET /me/onlineMeetings?$filter=JoinWebUrl eq '{joinUrl}', pasando el enlace generado en el evento original.

Con el identificador en mano, el sistema consulta GET https://graph.microsoft.com/v1.0/me/onlineMeetings/{onlineMeetingId}/transcripts, lo cual entrega la colección de objetos callTranscript disponibles con sus respectivos metadatos de auditoría y su identificador unívoco (transcriptId)13. El contenido de la transcripción se descarga mediante una llamada a GET https://graph.microsoft.com/v1.0/me/onlineMeetings/{onlineMeetingId}/transcripts/{transcriptId}/content15.

El formato de la respuesta se determina a través del encabezado Accept de la petición HTTP: si se configura como application/vnd.microsoft.graph.transcript+text, el servidor devuelve un cuerpo estructurado con la separación explícita de participantes; si se establece en text/vtt, se obtiene un archivo estándar WebVTT con marcas cronológicas exactas apto para ser indexado por marcas de tiempo en bases de datos vectoriales13.

Para evitar llamadas iterativas innecesarias, la infraestructura en FastAPI puede registrar suscripciones a las notificaciones de cambio de Microsoft Graph en el recurso communications/onlineMeetings/getAllTranscripts, activando el procesamiento únicamente en el momento en que Microsoft confirma que la transcripción se encuentra renderizada25.

## **Integración con Zoom API: Videoconferencias, Transcripciones y Resúmenes Nativos**

La plataforma de Zoom ofrece un modelo de servicios centrado en su API REST v2 (api.zoom.us/v2) y un mecanismo de entrega de eventos en tiempo real soportado por suscripciones a webhooks6.

### **Permisos y Flujos de Autorización**

Para sistemas corporativos internos que administran recursos en un solo dominio empresarial, la integración estándar se apoya en aplicaciones de tipo *Server-to-Server OAuth*, las cuales obtienen tokens de acceso mediante el flujo grant\_type=account\_credentials sin exigir la interacción continua de usuarios finales. En contraste, cuando la plataforma agéntica atiende múltiples clientes independientes, se implementa el flujo estándar de código de autorización OAuth 2.0. Los alcances mínimos necesarios comprenden meeting:write para la creación y alteración de conferencias, meeting:read para la validación de configuraciones de sala, y cloud\_recording:read para la obtención y descarga de grabaciones y transcripciones fonéticas11.

### **Programación y CRUD de Reuniones**

La creación de una sesión de videoconferencia se tramita a través de una petición HTTP dirigida al usuario organizador6:

&nbsp;

&nbsp;

&nbsp;

HTTP

POST https://api.zoom.us/v2/users/me/meetings HTTP/1.1  
Authorization: Bearer \<ACCESS\_TOKEN\>  
Content-Type: application/json

{  
  "topic": "Sesión de Estrategia Operativa",  
  "type": 2,  
  "start\_time": "2026-05-20T16:00:00Z",  
  "duration": 60,  
  "timezone": "UTC",  
  "settings": {  
    "host\_video": true,  
    "participant\_video": true,  
    "join\_before\_host": false,  
    "mute\_upon\_entry": true,  
    "auto\_recording": "cloud"  
  }  
}

El valor type: 2 establece una reunión programada en un instante temporal puntual6. La propiedad auto\_recording: "cloud" garantiza que los servidores de Zoom registren el contenido audiovisual y activen la extracción de la pista textual34. La respuesta entrega la URL pública para invitados (join\_url) y el enlace administrativo protegido para el anfitrión (start\_url). La actualización de características o reprogramación se formaliza mediante PATCH /meetings/{meetingId}, y la eliminación se ejecuta mediante DELETE /meetings/{meetingId}6.

### **Resúmenes Nativos de Zoom AI Companion y Transcripciones**

Zoom dispone de herramientas nativas de inteligencia artificial que generan resúmenes estructurados sin requerir inferencias externas6. Cuando una cuenta posee activo el servicio Zoom AI Companion y este se habilita durante una sesión, el sistema compila automáticamente la discusión al concluir la llamada. La plataforma agéntica puede consultar este informe estructurado mediante GET https://api.zoom.us/v2/meetings/{meetingId}/meeting\_summary6. La carga útil resultante proporciona una sinopsis general de la sesión, los desgloses temáticos detallados bajo summary\_details y el conjunto de próximos pasos y compromisos identificados (next\_steps)35.

Para consumir este artefacto de manera puramente reactiva, la aplicación se suscribe al evento de webhook meeting.summary\_completed36. Cuando este evento se emite, el cuerpo del mensaje contiene los identificadores del anfitrión, la duración y la estructura semántica de la reunión, permitiendo que el backend ingeste la minuta de inmediato36.

En paralelo, si se utilizó la grabación en la nube convencional, Zoom genera los archivos de transcripción de audio en formato WebVTT34. Al terminar la conversión, la plataforma emite el evento de webhook recording.completed o recording.transcript\_completed34. En el payload del evento recording.completed, el objeto contiene una colección denominada recording\_files34. Aquel archivo cuyo atributo file\_type corresponda a "TRANSCRIPT" provee la URL de descarga directa (download\_url)34. Para acceder al contenido protegido sin requerir credenciales de usuario en el cliente, la petición HTTP de descarga debe adjuntar el parámetro temporal download\_token provisto dentro del mismo webhook, garantizando el paso a través de los firewalls de autenticación de Zoom34.

### **Validación Criptográfica de Webhooks de Zoom en FastAPI**

Cualquier servicio que reciba notificaciones de Zoom debe superar de forma obligatoria el desafío de validación de URL (*CRC Challenge*) durante el registro del endpoint y validar criptográficamente cada petición entrante para certificar su legitimidad11.

&nbsp;

&nbsp;

&nbsp;

Python

import hmac  
import hashlib  
from fastapi import FastAPI, Request, HTTPException, status  
from fastapi.responses import JSONResponse

app \= FastAPI()  
ZOOM\_SECRET\_TOKEN \= "token\_secreto\_configurado\_en\_zoom\_marketplace"

@app.post("/api/v1/webhooks/zoom")  
async def process\_zoom\_webhook(request: Request):  
    raw\_payload \= await request.body()  
    decoded\_payload \= raw\_payload.decode("utf-8")  
    json\_data \= await request.json()

    \# 1\. Validación de Desafío CRC (Endpoint URL Validation)  
    if json\_data.get("event") \== "endpoint.url\_validation":  
        plain\_token \= json\_data\["payload"\]\["plainToken"\]  
        encrypted\_token \= hmac.new(  
            key=ZOOM\_SECRET\_TOKEN.encode("utf-8"),  
            msg=plain\_token.encode("utf-8"),  
            digestmod=hashlib.sha256  
        ).hexdigest()  
        return JSONResponse(  
            content={"plainToken": plain\_token, "encryptedToken": encrypted\_token},  
            status\_code=status.HTTP\_200\_OK  
        )

    \# 2\. Verificación de Firma Criptográfica HMAC-SHA256  
    message\_timestamp \= request.headers.get("x-zm-request-timestamp")  
    received\_signature \= request.headers.get("x-zm-signature")

    if not message\_timestamp or not received\_signature:  
        raise HTTPException(  
            status\_code=status.HTTP\_401\_UNAUTHORIZED,   
            detail="Encabezados de autenticación de webhook ausentes"  
        )

    message \= f"v0:{message\_timestamp}:{decoded\_payload}"  
    computed\_signature \= "v0=" \+ hmac.new(  
        key=ZOOM\_SECRET\_TOKEN.encode("utf-8"),  
        msg=message.encode("utf-8"),  
        digestmod=hashlib.sha256  
    ).hexdigest()

    if not hmac.compare\_digest(computed\_signature, received\_signature):  
        raise HTTPException(  
            status\_code=status.HTTP\_403\_FORBIDDEN,   
            detail="Firma de verificación HMAC inválida"  
        )

    \# 3\. Enrutamiento Asíncrono de Eventos Validados  
    event\_name \= json\_data.get("event")  
    if event\_name \== "meeting.summary\_completed":  
        \# Despachar procesamiento de resumen nativo hacia la capa de persistencia  
        pass  
    elif event\_name \== "recording.completed":  
        \# Despachar tarea en segundo plano para descarga de archivo VTT  
        pass

    return JSONResponse(content={"status": "received"}, status\_code=status.HTTP\_200\_OK)

## **Análisis Técnico: Conectores Nativos versus Middleware Unificado**

Al conceptualizar la arquitectura de conectividad para plataformas agénticas, los equipos de desarrollo se enfrentan a la decisión estratégica de establecer integraciones directas con las APIs de los fabricantes o incorporar intermediarios de unificación de datos o servicios de agentes virtuales (*bots*)34.

&nbsp;

| Dimensión Técnica | Integración Directa Nativa (Google, Microsoft, Zoom) | Middleware de API Unificada (ej. Nylas, Merge) | Plataformas de Bots Virtuales (ej. Recall.ai) |
| :---- | :---- | :---- | :---- |
| **Latencia de Transcripción** | Dependiente del procesamiento nativo en la nube (5 a 30 minutos tras finalizar la llamada)2. | Idéntica a la nativa; actúa como capa de abstracción sobre los webhooks originales. | Prácticamente en tiempo real; el audio es capturado directamente mediante WebRTC34. |
| **Amplitud Funcional y Actualizaciones** | Total y directa; acceso inmediato a nuevos parámetros y capacidades anunciadas por los proveedores. | Supeditada a esquemas genéricos comunes; pérdida de soporte para campos propietarios avanzados. | Especializada de manera exclusiva en presencia en sala, streaming de audio y captura de video34. |
| **Seguridad y Residencia de Datos** | Máxima; el flujo de tokens y datos reside exclusivamente entre los inquilinos corporativos y la nube propia. | Moderada; las credenciales y el tráfico de datos corporativos transitan por infraestructura de terceros. | Requiere acuerdos estrictos de procesamiento de datos; el bot se une como un usuario participante a la llamada34. |
| **Modelo Financiero y Costo a Escala** | Sin tarifas de licenciamiento de conectividad de terceros; exclusivamente costos de cómputo propio. | Tarifas mensuales recurrentes calculadas por cada cuenta conectada o usuario activo sincronizado. | Facturación volumétrica dependiente de los minutos consumidos en llamadas o el número de bots paralelos. |
| **Experiencia del Usuario Final** | Transparente e imperceptible; la recolección de artefactos opera de fondo a nivel de API institucional. | Transparente a nivel de usuario; idéntica a la integración directa. | Intrusiva; los asistentes humanos visualizan una cuenta virtual participante ("Bot Asistente") en la sesión. |

El modelo de integración directa nativa representa la opción más adecuada para organizaciones que priorizan la gobernanza de datos, la ausencia de fricción visual durante las reuniones y el control absoluto sobre los costos operacionales a escala, justificando la inversión inicial en desarrollo mediante la eliminación de dependencias de proveedores externos34.

## **Diseño del Skill en LangGraph y FastAPI con Human-in-the-Loop**

La materialización de estas capacidades en un formato de programación agéntica demanda modelos de datos rigurosamente tipados mediante Pydantic y la implementación de puntos de control deterministas a través de la primitiva interrupt() de LangGraph, asegurando que ninguna operación sobre los calendarios se efectúe sin supervisión humana3.

### **Esquemas Estructurados de Invocación de Herramientas**

&nbsp;

&nbsp;

&nbsp;

Python

from pydantic import BaseModel, Field  
from typing import List, Optional, Literal  
from datetime import datetime

class ScheduleMeetingInput(BaseModel):  
    provider: Literal\["google", "microsoft", "zoom"\] \= Field(  
        ..., description="Plataforma tecnológica designada para alojar y registrar la reunión."  
    )  
    title: str \= Field(  
        ..., description="Título temático o asunto principal del evento en el calendario."  
    )  
    description: Optional\[str\] \= Field(  
        None, description="Descripción detallada, minuta previa o temario estructurado de la sesión."  
    )  
    start\_time: datetime \= Field(  
        ..., description="Marca de tiempo de inicio expresada en formato ISO-8601 UTC."  
    )  
    end\_time: datetime \= Field(  
        ..., description="Marca de tiempo de finalización expresada en formato ISO-8601 UTC."  
    )  
    attendees: List\[str\] \= Field(  
        default\_factory=list,  
        description="Lista de correos electrónicos corporativos correspondientes a los asistentes."  
    )

class CheckAvailabilityInput(BaseModel):  
    provider: Literal\["google", "microsoft"\] \= Field(  
        ..., description="Ecosistema corporativo sobre el cual evaluar la disponibilidad horaria."  
    )  
    emails: List\[str\] \= Field(  
        ..., description="Conjunto de direcciones de correo electrónico de los usuarios a verificar."  
    )  
    start\_time: datetime \= Field(  
        ..., description="Límite cronológico inferior del intervalo de evaluación."  
    )  
    end\_time: datetime \= Field(  
        ..., description="Límite cronológico superior del intervalo de evaluación."  
    )  
    interval\_minutes: int \= Field(  
        default=30, description="Granularidad temporal de los bloques discretos de análisis."  
    )

### **Grafo de LangGraph con Interrupción de Seguridad**

El grafo de estados garantiza que las consultas de disponibilidad y el análisis de información se ejecuten de manera totalmente autónoma, mientras que las mutaciones sobre el mundo exterior pausan la máquina de estados de forma automática4.

&nbsp;

&nbsp;

&nbsp;

Python

from typing import TypedDict, Annotated, Sequence, Optional  
import operator  
from langchain\_core.messages import BaseMessage, AIMessage  
from langchain\_core.tools import tool  
from langgraph.graph import StateGraph, START, END  
from langgraph.types import interrupt, Command  
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

class AgentSchedulingState(TypedDict):  
    messages: Annotated\[Sequence\[BaseMessage\], operator.add\]  
    user\_id: str  
    target\_action: Optional\[str\]  
    proposed\_meeting\_payload: Optional\[dict\]

@tool(args\_schema=CheckAvailabilityInput)  
def tool\_check\_availability(provider: str, emails: list\[str\], start\_time: datetime, end\_time: datetime, interval\_minutes: int \= 30) \-\> str:  
    """Inspecciona las agendas corporativas y retorna los intervalos horarios desocupados."""  
    \# Despacho interno hacia freeBusy de Google o getSchedule de Microsoft Graph  
    return f"Se analizó la disponibilidad para {len(emails)} usuarios. Franja libre común confirmada."

@tool(args\_schema=ScheduleMeetingInput)  
def tool\_execute\_booking(provider: str, title: str, description: str, start\_time: datetime, end\_time: datetime, attendees: list\[str\]) \-\> str:  
    """Invoca formalmente los endpoints de los proveedores externos para reservar el espacio."""  
    \# Despacho hacia Calendar Events insert, Microsoft Graph Events o Zoom Meetings  
    return f"Reunión '{title}' confirmada exitosamente en {provider}. Enlace de conexión generado."

def decision\_planner\_node(state: AgentSchedulingState):  
    """Nodo analítico del agente que evalúa los mensajes y determina el plan de acción."""  
    \# El LLM analiza el contexto conversacional y determina que se requiere crear una reunión  
    return {  
        "target\_action": "schedule\_meeting",  
        "proposed\_meeting\_payload": {  
            "provider": "google",  
            "title": "Alineación de Arquitectura de Software",  
            "description": "Revisión técnica de controladores FastAPI y estados de LangGraph.",  
            "start\_time": "2026-05-22T15:00:00Z",  
            "end\_time": "2026-05-22T16:00:00Z",  
            "attendees": \["director@empresa.com", "arquitecto@empresa.com"\]  
        }  
    }

def human\_verification\_gate(state: AgentSchedulingState):  
    """Punto de control estricto que interrumpe el grafo y persiste el estado hasta recibir confirmación."""  
    payload \= state.get("proposed\_meeting\_payload")  
    if not payload:  
        return {}

    \# La primitiva interrupt detiene la ejecución del hilo y envía los detalles al almacenamiento  
    decision \= interrupt({  
        "type": "PENDING\_MEETING\_CONFIRMATION",  
        "parameters": payload,  
        "prompt": "¿Autoriza la creación del evento en el calendario corporativo con los asistentes señalados?"  
    })

    \# El flujo se reanuda únicamente tras el retorno de Command(resume=...)  
    if not decision.get("approved", False):  
        return {  
            "messages": \[AIMessage(content="La solicitud de reserva fue desestimada por el usuario.")\],  
            "proposed\_meeting\_payload": None,  
            "target\_action": None  
        }

    \# Tras la aprobación explícita, se dispara la herramienta de ejecución  
    execution\_result \= tool\_execute\_booking.invoke(payload)  
    return {  
        "messages": \[AIMessage(content=execution\_result)\],  
        "proposed\_meeting\_payload": None,  
        "target\_action": None  
    }

def construct\_agent\_graph(checkpointer: AsyncPostgresSaver):  
    builder \= StateGraph(AgentSchedulingState)  
    builder.add\_node("planner", decision\_planner\_node)  
    builder.add\_node("approval\_gate", human\_verification\_gate)

    builder.add\_edge(START, "planner")  
    builder.add\_edge("planner", "approval\_gate")  
    builder.add\_edge("approval\_gate", END)

    return builder.compile(checkpointer=checkpointer)

### **Controlador en FastAPI para la Reanudación de Estados Suspendidos**

La interacción entre Next.js y el motor de LangGraph se completa a través de un endpoint en FastAPI encargado de inyectar la resolución humana en el hilo de ejecución correspondiente3:

&nbsp;

&nbsp;

&nbsp;

Python

from fastapi import APIRouter, HTTPException  
from pydantic import BaseModel

router \= APIRouter(prefix="/api/v1/agent")

class UserApprovalPayload(BaseModel):  
    thread\_id: str  
    approved: bool  
    parameter\_overrides: Optional\[dict\] \= None

@router.post("/resume-decision")  
async def resume\_agent\_thread(payload: UserApprovalPayload):  
    config \= {"configurable": {"thread\_id": payload.thread\_id}}  
    agent\_graph \= router.app.state.scheduling\_graph  
&nbsp;&nbsp;&nbsp;&nbsp;  
    try:  
        events \= \[\]  
        \# Inyección del comando de reanudación directamente en el hilo pausado  
        async for update in agent\_graph.astream(  
            Command(resume={"approved": payload.approved, "overrides": payload.parameter\_overrides}),  
            config=config,  
            stream\_mode="updates"  
        ):  
            events.append(update)  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  
        return {"status": "resumed", "execution\_log": events}  
    except Exception as exc:  
        raise HTTPException(  
            status\_code=500,   
            detail=f"Fallo crítico al reanudar la ejecución del grafo: {str(exc)}"  
        )

## **Ciclo de Ingesta Post-Reunión y Procesamiento de Lenguaje Natural**

La finalización de la videoconferencia activa una canalización asíncrona de ingestión y estructuración que convierte las transcripciones conversacionales en conocimiento accionable dentro del sistema corporativo2.

&nbsp;

| Etapa de la Canalización | Evento / Operación Técnica | Descripción del Proceso | Artefacto Generado |
| :---- | :---- | :---- | :---- |
| **1\. Conclusión de la Llamada** | Notificación externa | El servidor del proveedor emite el evento de cierre (summary\_completed, Pub/Sub o notificación de cambio de Graph)14. | Mensaje en cola o webhook recibido en FastAPI10. |
| **2\. Verificación y Descarga** | Validación HMAC y descarga I/O | FastAPI comprueba la firma criptográfica y solicita los archivos de transcripción o resúmenes nativos11. | Archivo WebVTT o documento JSON crudo15. |
| **3\. Normalización y Limpieza** | Segmentación textual | El procesador elimina encabezados, unifica marcas de tiempo y agrupa parlamentos continuos por orador. | Lista serializada de objetos con atributos speaker y text. |
| **4\. Inferencia Semántica** | Sub-grafo analítico en LangGraph | Un modelo de lenguaje con salida tipada extrae acuerdos clave, decisiones tomadas y tareas pendientes. | Objeto Pydantic MeetingMinutes validado. |
| **5\. Persistencia y Difusión** | Indexación en Base de Datos | Se almacenan las minutas en PostgreSQL, se vectorizan los segmentos en pgvector y se alerta al usuario en Next.js. | Registros relacionales, embeddings y eventos SSE. |

Para transformar transcripciones extensas con marcas de tiempo repetitivas en entradas legibles para el modelo, se utiliza un normalizador de texto específico:

&nbsp;

&nbsp;

&nbsp;

Python

import re  
from typing import List, Dict

def parse\_vtt\_transcript(vtt\_raw\_text: str) \-\> List\[Dict\[str, str\]\]:  
    """Transforma archivos estándar WebVTT en estructuras limpias de diálogo por participante."""  
    cleaned\_entries \= \[\]  
    lines \= vtt\_raw\_text.strip().splitlines()  
    time\_regex \= re.compile(r"\\d{2}:\\d{2}:\\d{2}\\.\\d{3}\\s--\>\\s\\d{2}:\\d{2}:\\d{2}\\.\\d{3}")  
    current\_speaker \= "Desconocido"

    for line in lines:  
        line \= line.strip()  
        if not line or "WEBVTT" in line or line.isdigit() or time\_regex.match(line):  
            continue

        if ":" in line:  
            speaker\_candidate, speech\_fragment \= line.split(":", 1)  
            current\_speaker \= speaker\_candidate.strip()  
            cleaned\_entries.append({"speaker": current\_speaker, "text": speech\_fragment.strip()})  
        else:  
            if cleaned\_entries:  
                cleaned\_entries\[-1\]\["text"\] \+= f" {line}"  
            else:  
                cleaned\_entries.append({"speaker": current\_speaker, "text": line})

    return cleaned\_entries

La lista unificada de intervenciones es procesada por un sub-grafo analítico que, mediante un modelo de lenguaje vinculado a esquemas estructurados (llm.with\_structured\_output), extrae los acuerdos formales, las tareas asignadas y sus respectivos responsables, vinculando estos compromisos a los eventos originales del calendario para habilitar recordatorios proactivos por parte del sistema multiagente1.

## **Consideraciones de Producción, Seguridad y Concurrencia**

El despliegue de agentes autónomos con capacidad de gestión sobre agendas corporativas introduce vectores de falla específicos relacionados con la coherencia temporal, la persistencia de credenciales y la concurrencia de eventos7.

La normalización canónica de zonas horarias representa el pilar crítico de la integridad temporal. Toda operación de cálculo, comparación de disponibilidad y almacenamiento dentro de FastAPI y los nodos de LangGraph debe ejecutarse bajo el estándar UTC en objetos nativos con información horaria explícita (timezone-aware). La conversión hacia husos horarios locales solo debe tener lugar durante la serialización final hacia las APIs de terceros mediante sus encabezados correspondientes (como Prefer: outlook.timezone en Microsoft Graph) o en el momento en que Next.js proyecta la agenda en la interfaz del cliente24.

En materia de seguridad, los tokens de actualización (*refresh tokens*) deben almacenarse cifrados en reposo dentro de PostgreSQL mediante el algoritmo de autenticación simétrica AES-GCM de 256 bits, complementado por sistemas de custodia de secretos como AWS KMS o HashiCorp Vault. El backend en FastAPI debe verificar proactivamente la caducidad del token de acceso cinco minutos antes de su expiración formal, procediendo a su rotación transparente antes de despachar cualquier comando de las herramientas.

Para mitigar los límites de tasa de peticiones impuestos por los proveedores externos, los clientes HTTP deben implementar algoritmos de reintento con retroceso exponencial (*exponential backoff*) y fluctuación aleatoria (*jitter*), interpretando rigurosamente el encabezado HTTP Retry-After ante respuestas 42914. Finalmente, para evitar bucles operacionales o condiciones de carrera provocadas por la llegada simultánea de múltiples webhooks sobre una misma reunión, el sistema debe establecer bloqueos distribuidos en Redis (Redlock) basados en el identificador de la reunión, asegurando que las actualizaciones de estado se ejecuten de manera serializada y determinista8.

## **Conclusiones e Implicaciones de Ingeniería**

La estructuración de un skill de programación integral para la gestión de calendarios y videoconferencias en una plataforma agéntica trasciende la simple emisión de peticiones HTTP5. Requiere orquestar un pipeline bidireccional que coordine la planificación temporal, la verificación de disponibilidad entre múltiples dominios y el procesamiento asíncrono de discusiones en lenguaje natural2.

La integración desacoplada entre FastAPI y LangGraph permite un balance óptimo entre autonomía operativa y seguridad mediante el uso de compuertas *Human-in-the-Loop*3. Al fundamentar la arquitectura en integraciones directas con Google Workspace, Microsoft Graph y Zoom API, la organización mantiene la custodia de sus datos, garantiza una experiencia de usuario natural y establece una infraestructura técnica robusta sobre la cual pueden orquestarse flujos de trabajo autónomos de escala empresarial5.

#### **Works cited**

> 1. Google Meet API Guide \- Bluedot AI Note Taker, [https://www.bluedothq.com/blog/google-meet-api-guide](https://www.bluedothq.com/blog/google-meet-api-guide)  
> 2. Connect Google Meet to AI Agents: Extract Meeting Insights \- Truto, [https://truto.one/blog/connect-google-meet-to-ai-agents-extract-meeting-and-user-insights/](https://truto.one/blog/connect-google-meet-to-ai-agents-extract-meeting-and-user-insights/)  
> 3. Interrupts \- CopilotKit, [https://docs.copilotkit.ai/langgraph-python/human-in-the-loop/interrupt-flow](https://docs.copilotkit.ai/langgraph-python/human-in-the-loop/interrupt-flow)  
> 4. Human-in-the-loop \- Docs by LangChain, [https://docs.langchain.com/oss/python/langchain/human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)  
> 5. Create events | Google Calendar, [https://developers.google.com/workspace/calendar/api/guides/create-events](https://developers.google.com/workspace/calendar/api/guides/create-events)  
> 6. Zoom Meeting API \- API \- Zoom Developer Docs, [https://developers.zoom.us/docs/api/rest/reference/zoom-api/methods/](https://developers.zoom.us/docs/api/rest/reference/zoom-api/methods/)  
> 7. Outlook Calendar API Integration (In-Depth): Microsoft Graph, Auth, [https://www.getknit.dev/blog/outlook-calendar-api-integration-in-depth](https://www.getknit.dev/blog/outlook-calendar-api-integration-in-depth)  
> 8. How I implemented human-in-the-loop with LangGraph's interrupt, [https://www.reddit.com/r/LangChain/comments/1s6qidj/how\_i\_implemented\_humanintheloop\_with\_langgraphs/](https://www.reddit.com/r/LangChain/comments/1s6qidj/how_i_implemented_humanintheloop_with_langgraphs/)  
> 9. Making it easier to build human-in-the-loop agents with interrupt, [https://www.langchain.com/blog/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt](https://www.langchain.com/blog/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt)  
> 10. Blog 3: Implementing Webhooks for Real-Time Event Notifications in, [https://medium.com/@harinimaruthasalam/blog-3-implementing-webhooks-for-real-time-event-notifications-in-zoom-2a79391f1faf](https://medium.com/@harinimaruthasalam/blog-3-implementing-webhooks-for-real-time-event-notifications-in-zoom-2a79391f1faf)  
> 11. Using webhooks \- API \- Zoom Developer Docs, [https://developers.zoom.us/docs/api/webhooks/](https://developers.zoom.us/docs/api/webhooks/)  
> 12. LangGraph's interrupt() Function: The Simpler Way to Build Human, [https://medium.com/@areebahmed575/langgraphs-interrupt-function-the-simpler-way-to-build-human-in-the-loop-agents-faef98891a92](https://medium.com/@areebahmed575/langgraphs-interrupt-function-the-simpler-way-to-build-human-in-the-loop-agents-faef98891a92)  
> 13. Get meeting transcripts and recordings using Graph APIs, [https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/meeting-transcripts/overview-transcripts](https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/meeting-transcripts/overview-transcripts)  
> 14. Google Meet User Management API Guide \- Stitchflow, [https://www.stitchflow.com/user-management/google-meet/api](https://www.stitchflow.com/user-management/google-meet/api)  
> 15. Get callTranscript \- Microsoft Graph v1.0, [https://learn.microsoft.com/en-us/graph/api/calltranscript-get?view=graph-rest-1.0](https://learn.microsoft.com/en-us/graph/api/calltranscript-get?view=graph-rest-1.0)  
> 16. LangGraph Uncovered:AI Agent and Human-in-the-Loop, [https://dev.to/sreeni5018/langgraph-uncoveredai-agent-and-human-in-the-loop-enhancing-decision-making-with-intelligent-3dbc](https://dev.to/sreeni5018/langgraph-uncoveredai-agent-and-human-in-the-loop-enhancing-decision-making-with-intelligent-3dbc)  
> 17. Google Meet API \- Google for Developers, [https://developers.google.com/workspace/meet/api/reference/rest/v2](https://developers.google.com/workspace/meet/api/reference/rest/v2)  
> 18. Google Calendar API \- Create Event \+ Google Meet Link, [https://stackoverflow.com/questions/75916295/google-calendar-api-create-event-google-meet-link](https://stackoverflow.com/questions/75916295/google-calendar-api-create-event-google-meet-link)  
> 19. Method: conferenceRecords.transcripts.entries.get | Google Meet, [https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords.transcripts.entries/get](https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords.transcripts.entries/get)  
> 20. Sample Scripts for Creating New Event with Google Meet Link to, [https://gist.github.com/tanaikech/94791d48823e9659aa376cf7f0161d9b](https://gist.github.com/tanaikech/94791d48823e9659aa376cf7f0161d9b)  
> 21. Create a Google Calendar event with a specified Google Meet ID, [https://stackoverflow.com/questions/75785196/create-a-google-calendar-event-with-a-specified-google-meet-id-conferencedata-c](https://stackoverflow.com/questions/75785196/create-a-google-calendar-event-with-a-specified-google-meet-id-conferencedata-c)  
> 22. Events | Google Calendar, [https://developers.google.com/workspace/calendar/api/v3/reference/events](https://developers.google.com/workspace/calendar/api/v3/reference/events)  
> 23. Method: conferenceRecords.transcripts.entries.list | Google Meet, [https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords.transcripts.entries/list](https://developers.google.com/workspace/meet/api/reference/rest/v2/conferenceRecords.transcripts.entries/list)  
> 24. calendar-getschedule.md \- microsoft-graph-docs-contrib \- GitHub, [https://github.com/microsoftgraph/microsoft-graph-docs-contrib/blob/main/api-reference/v1.0/api/calendar-getschedule.md](https://github.com/microsoftgraph/microsoft-graph-docs-contrib/blob/main/api-reference/v1.0/api/calendar-getschedule.md)  
> 25. Microsoft Graph APIs for Teams meeting transcripts now available, [https://devblogs.microsoft.com/microsoft365dev/microsoft-graph-apis-for-microsoft-teams-meeting-transcripts-now-generally-available/](https://devblogs.microsoft.com/microsoft365dev/microsoft-graph-apis-for-microsoft-teams-meeting-transcripts-now-generally-available/)  
> 26. getSchedule request from Application (not from User?) \- Microsoft Q\&A, [https://learn.microsoft.com/en-sg/answers/questions/1291607/getschedule-request-from-application-not-from-user](https://learn.microsoft.com/en-sg/answers/questions/1291607/getschedule-request-from-application-not-from-user)  
> 27. Migrate Outlook Add-Ins to Microsoft Graph by Oct 2026, [https://www.mckennaconsultants.com/ews-to-microsoft-graph-the-api-migration-every-outlook-add-in-developer-must-complete-by-october-2026/](https://www.mckennaconsultants.com/ews-to-microsoft-graph-the-api-migration-every-outlook-add-in-developer-must-complete-by-october-2026/)  
> 28. calendar: getSchedule \- Microsoft Graph v1.0, [https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0](https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0)  
> 29. Microsoft Graph API developer – Using GetSchedule API to get free, [https://lecafedeva.wordpress.com/2019/02/03/microsoft-graph-api-developer-using-getschedule-api-to-get-free-busy-availability-information/](https://lecafedeva.wordpress.com/2019/02/03/microsoft-graph-api-developer-using-getschedule-api-to-get-free-busy-availability-information/)  
> 30. Teams Graph API endpoint to get meeting transcript does not return, [https://community.powerplatform.com/forums/thread/details/?threadid=04b11235-873d-f111-88b5-6045bddc3278](https://community.powerplatform.com/forums/thread/details/?threadid=04b11235-873d-f111-88b5-6045bddc3278)  
> 31. List transcripts \- Microsoft Graph v1.0, [https://learn.microsoft.com/en-us/graph/api/onlinemeeting-list-transcripts?view=graph-rest-1.0](https://learn.microsoft.com/en-us/graph/api/onlinemeeting-list-transcripts?view=graph-rest-1.0)  
> 32. Get change notifications for transcripts and recordings using, [https://learn.microsoft.com/en-us/graph/teams-changenotifications-callrecording-and-calltranscript](https://learn.microsoft.com/en-us/graph/teams-changenotifications-callrecording-and-calltranscript)  
> 33. Issue accessing recent Teams meeting transcripts via Graph API, [https://learn.microsoft.com/en-us/answers/questions/5587670/issue-accessing-recent-teams-meeting-transcripts-v](https://learn.microsoft.com/en-us/answers/questions/5587670/issue-accessing-recent-teams-meeting-transcripts-v)  
> 34. How to retrieve Zoom recording status \- Recall.ai, [https://www.recall.ai/blog/zoom-dev-forum-figure-out-if-recording-was-enabled](https://www.recall.ai/blog/zoom-dev-forum-figure-out-if-recording-was-enabled)  
> 35. Reclaim Ai Integrations Api \- APIs.io, [https://apis.io/apis/reclaim-ai/reclaim-ai-integrations-api/](https://apis.io/apis/reclaim-ai/reclaim-ai-integrations-api/)  
> 36. Meetings Webhooks \- API \- Zoom Developer Docs, [https://developers.zoom.us/docs/api/meetings/events/](https://developers.zoom.us/docs/api/meetings/events/)  
> 37. Summary and Transcript Events Not Triggering in Event Subscription, [https://devforum.zoom.us/t/summary-and-transcript-events-not-triggering-in-event-subscription/124209](https://devforum.zoom.us/t/summary-and-transcript-events-not-triggering-in-event-subscription/124209)  
> 38. When meeting is not recorded then not getting webhook recording, [https://devforum.zoom.us/t/when-meeting-is-not-recorded-then-not-getting-webhook-recording-transcript-completed-event/133020](https://devforum.zoom.us/t/when-meeting-is-not-recorded-then-not-getting-webhook-recording-transcript-completed-event/133020)  
> 39. How to Extract Zoom Cloud Recording Transcripts via the Zoom API, [https://semarize.com/resources/blog/extract-zoom-cloud-recording-transcripts-api](https://semarize.com/resources/blog/extract-zoom-cloud-recording-transcripts-api)  
> 40. How to get Google Meet transcripts programmatically \- Recall.ai, [https://www.recall.ai/blog/how-to-get-transcripts-from-google-meet-developer-edition](https://www.recall.ai/blog/how-to-get-transcripts-from-google-meet-developer-edition)  
> 41. Calendar Automation with PowerShell | Nylas CLI, [https://cli.nylas.com/guides/email-calendar-powershell](https://cli.nylas.com/guides/email-calendar-powershell)