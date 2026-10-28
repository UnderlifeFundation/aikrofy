# **Diseño de Arquitectura para un CRM Conversacional Multi-Tenant con Automatización Agéntica de Ventas, Atribución Omnicanal y Analítica Personalizable**

## **Análisis de Plataformas Líderes en Comercio Conversacional**

El mercado del comercio conversacional y los sistemas de relación con clientes (CRM) basados en mensajería está liderado por plataformas como ATOM Chat, Kommo CRM, Interakt y Zoko.1 Estos sistemas han transformado la interacción comercial tradicional al centralizar flujos omnicanal procedentes de WhatsApp, Facebook Messenger, Instagram DM y Telegram en una bandeja de entrada única y colaborativa.5 El análisis de sus capacidades operativas proporciona un plano de referencia para el desarrollo de soluciones de software empresarial de alto rendimiento.  
ATOM Chat destaca por su suite de Inteligencia Artificial multimodal que permite automatizar hasta el 80% de las interacciones típicas que anteriormente requerían intervención humana.6 Esto reduce los costos de soporte en un 50% y aumenta las tasas de conversión de ventas en aproximadamente un 30%.6 A diferencia de los chatbots tradicionales basados exclusivamente en árboles de decisión de texto, las arquitecturas modernas como la de ATOM integran agentes de IA capaces de procesar notas de voz mediante transcripción automática (Speech-to-Text) e interpretar imágenes para extraer información clave, como facturas, comprobantes de pago o documentos de identidad.5 Estas capacidades habilitan flujos de automatización complejos como estrategias de cobro automático, reactivación de clientes inactivos, calificación autónoma de prospectos para instituciones educativas o asignación de citas en sectores de salud y automotriz, operando ininterrumpidamente las 24 horas del día, los 7 días de la semana.8  
La integración bidireccional de datos con herramientas externas como HubSpot, Salesforce o Zoho CRM representa otra de las capacidades críticas de estas plataformas.1 El flujo continuo de información garantiza que cualquier acción ocurrida en la ventana de chat actualice de inmediato el estado del cliente en el CRM central, asegurando la trazabilidad de los esfuerzos de marketing y el control operativo del equipo de ventas.1 No obstante, el costo por conversación (impuesto principalmente por las tarifas oficiales de Meta) se mantiene como una barrera económica relevante, lo que subraya la necesidad de diseñar arquitecturas de filtrado eficientes para procesar únicamente leads de alta calidad antes de escalar las conversaciones pagas.  
Adicionalmente, herramientas como Dashly complementan este ecosistema mediante el despliegue de agentes especializados.9 Su enfoque se centra en resolver la pérdida de prospectos causada por demoras en los tiempos de respuesta humana (que en entornos B2B tradicionales promedian cinco horas).9 Dashly utiliza cuatro agentes de inteligencia artificial especializados para automatizar por completo el embudo de ventas entrante 9:

| Agente de IA | Función Operativa Principal | Impacto en el Embudo de Ventas |
| :---- | :---- | :---- |
| **AI Lead Insight** | Enriquecimiento de datos en tiempo real (perfiles de LinkedIn, historial de navegación, uso de productos).9 | Construcción instantánea de perfiles de clientes detallados sin entrada de datos manual.9 |
| **AI Engagement Agent** | Iniciación autónoma de conversaciones en momentos óptimos de navegación.9 | Maximiza la tasa de contacto activo de los visitantes del sitio web.9 |
| **AI Qualifier** | Execution de calificación de leads mediante diálogo natural.9 | Automatiza el triaje de prospectos basándose en criterios de valor para el negocio.9 |
| **AI Nurturing Agent** | Agendamiento autónomo de reuniones y seguimiento de asistencia.9 | Asegura que los representantes de ventas solo inviertan tiempo en llamadas confirmadas.9 |

## **Mecanismos de Atribución y Captura de UTM en Canales Conversacionales**

La atribución de campañas de marketing digital en canales conversacionales presenta un desafío estructural conocido como la "ruptura de sesión de navegador".10 Cuando un usuario hace clic en un anuncio o enlace dentro de su navegador web y se le redirige para abrir la aplicación nativa de WhatsApp o Instagram, el contexto tradicional de seguimiento web (cookies, almacenamiento local, estado de la sesión) deja de funcionar.10 Para resolver esta desconexión y atribuir con precisión el origen de la conversación, se implementan varias estrategias técnicas según el canal de origen.2

### **Atribución en Anuncios Click-to-WhatsApp (CTWA)**

Para las campañas pagas dentro del ecosistema de Meta que dirigen tráfico directamente a WhatsApp, la API de Cloud WhatsApp proporciona una solución nativa mediante el objeto referral incrustado en el primer webhook de mensaje enviado por el usuario.10 Cuando el usuario inicia el chat desde un anuncio de Facebook o Instagram, Meta genera un identificador único de clic de anuncio (ctwa\_clid).10 El webhook enviado por Meta al servidor del CRM estructurará estos metadatos exclusivamente en el primer mensaje de la conversación 11:

JSON  
{  
  "object": "whatsapp\_business\_account",  
  "entry":,  
        "messages":  
      },  
      "field": "messages"  
    }\]  
  }\]  
}

Este objeto contiene parámetros de atribución críticos como el source\_id (ID del anuncio), headline, body del anuncio, source\_url y el identificador de clic ctwa\_clid.11 Es una restricción de la plataforma de Meta que este objeto referral se transmita únicamente en el primer mensaje.11 El sistema receptor debe guardar estos datos inmediatamente; los mensajes posteriores vendrán sin este objeto, impidiendo su recuperación retrospectiva.11 Una vez extraído el ctwa\_clid, el CRM puede enviar eventos de conversión del embudo de vuelta a Meta mediante la API de Conversiones (CAPI) utilizando el canal de mensajería correspondiente, cerrando el bucle de optimización de las campañas de marketing.10  
En sistemas integrados como Kommo CRM, la recuperación de estos datos requiere que el número de WhatsApp Business y la cuenta de Meta Ads compartan el mismo Meta Business Manager.3 Esto permite que el CRM consulte de forma automatizada las estadísticas de atribución y muestre la información detallada de la campaña dentro de la tarjeta del prospecto en una sección dedicada a datos de seguimiento, facilitando la filtración de leads por campaña.3

### **Atribución mediante Enlaces Inteligentes (Smart Links) y WhatsApp Templates**

Para la atribución de tráfico proveniente de campañas de difusión saliente (outbound broadcasts), automatizaciones de carritos abandonados o enlaces externos, plataformas como Zoko e Interakt utilizan estructuras parametrizadas 2:

* **Smart Links (Zoko):** Consiste en la generación de URLs de destino acortadas que llevan parámetros UTM (utm\_source, utm\_medium, utm\_campaign).4 Al hacer clic en un enlace abreviado dentro de WhatsApp (utilizando acortadores personalizados como Bitly o Rebrandly para evitar textos excesivamente largos en los mensajes), los parámetros se transmiten al sitio web de destino y se registran en la sesión del usuario en Google Analytics 4 (GA4).4 Esto vincula directamente los clics realizados dentro de la aplicación de mensajería con las compras u otras conversiones web del usuario.4  
* **Parámetros UTM en Botones CTA (Interakt):** Durante la creación de plantillas de WhatsApp aprobadas por Meta, Interakt permite inyectar parámetros UTM tanto en URLs estáticas como dinámicas vinculadas a botones de llamada a la acción (CTA).2 Esto facilita que las herramientas de analítica web mapeen las conversiones logradas a partir de las respuestas de campañas específicas, estableciendo objetivos de conversión con ventanas de atribución definidas (de hasta 30 días) desde que el cliente lee el mensaje.2

### **Enlaces de Redirección Intermedios y Mapeo de Identificadores de Clics (GCLID)**

Para campañas originadas en Google Ads, TikTok Ads u otras fuentes externas de tráfico que dirigen a los usuarios hacia WhatsApp desde un sitio web, se implementa una técnica de base de datos basada en un identificador de referencia cruzada 10:

1. El usuario hace clic en el anuncio de Google y llega a la página de aterrizaje (landing page), donde la URL contiene el parámetro gclid.10  
2. Un script JS lee los parámetros UTM y el gclid, genera un identificador de referencia único (por ejemplo, un hash alfanumérico corto como REF-9821) y almacena la relación {reference\_id: REF-9821, gclid: GCLID\_VALUE, utm\_source: google,...} en la base de datos del CRM.10  
3. El script modifica dinámicamente el enlace del botón de WhatsApp en la página web para incluir este código de referencia en el texto preestablecido del mensaje (ej. https://wa.me/number?text=Hola,%20me%20interesa%20el%20servicio%20Ref:%20REF-9821).10  
4. Al enviar el mensaje, el webhook del backend recibe el texto, extrae el código de referencia con una expresión regular, busca en la base de datos la sesión web original utilizando este identificador y asocia de forma inmediata los datos de campaña de Google Ads al contacto del CRM.10

### **Atribución en Instagram DM mediante Enlaces de Referencia**

La atribución directa en Instagram funciona de manera similar mediante enlaces ig.me parametrizados con la variable ref.14 Cuando el usuario hace clic en un enlace como https://ig.me/m/nombre\_perfil?ref=campaña\_verano, Meta dispara un webhook de evento messaging\_referral 14:

JSON  
{  
  "sender": { "id": "INSTAGRAM\_USER\_ID" },  
  "recipient": { "id": "INSTAGRAM\_PAGE\_ID" },  
  "timestamp": 1458692752478,  
  "referral": {  
    "ref": "campaña\_verano",  
    "source": "SHORTLINK",  
    "type": "OPEN\_THREAD"  
  }  
}

Al implementar esta atribución en el backend, se debe considerar que, aunque la documentación oficial de Meta para desarrolladores históricamente indicaba que el campo source devolvía la cadena "SHORTLINKS", el entorno de producción real devuelve el valor en singular "SHORTLINK".14 El deserializador del webhook debe estar programado para validar correctamente esta variación estructural y evitar fallas en la captura de datos.14

## **Motor Híbrido Autónomo de Calificación de Leads (Lead Scoring)**

Para automatizar la priorización de prospectos sin requerir configuraciones complejas por parte de la empresa, el sistema debe implementar un motor híbrido de calificación de leads.16 Este motor combina algoritmos de aprendizaje automático (Machine Learning) con una capa paramétrica ajustable por el usuario para adaptar el comportamiento del modelo de predicción a las necesidades particulares del negocio.17

### **Formulación Matemática del Modelo Híbrido**

El puntaje compuesto final de un lead (representado como S\_composite) se modela mediante una combinación lineal ponderada del puntaje predictivo derivado de la inteligencia artificial (representado como P\_ML, que es un valor probabilístico entre 0.0 y 1.0) y la suma neta de las reglas de calificación manuales (representado como S\_Manual, escalado entre 0 y 100\) 20:  
S\_composite \= (w\_ML \* (P\_ML \* 100)) \+ (w\_Manual \* S\_Manual)  
Bajo la restricción de normalización de pesos del sistema:  
w\_ML \+ w\_Manual \= 1.0  
Donde w\_ML representa el coeficiente de peso relativo asignado a la inteligencia artificial autónoma (por ejemplo, 0.60) y w\_Manual representa el coeficiente de peso relativo asignado a las reglas manuales parametrizadas por el equipo de operaciones de ingresos (RevOps) (por ejemplo, 0.40).19  
El componente manual (S\_Manual) se calcula evaluando los atributos demográficos, firmográficos y las señales de comportamiento del prospecto con una puntuación acotada entre un mínimo de 0 y un máximo de 100 17:  
S\_Manual \= max(0, min(100, Sumatoria\_de\_1\_a\_n(Beta\_i \* x\_i) \- Sumatoria\_de\_1\_a\_m(Gamma\_j \* y\_j)))  
En esta estructura:

* Beta\_i representa el puntaje de incremento positivo asignado a un atributo de ajuste favorable (representado por la variable binaria x\_i), tal como la coincidencia del sector objetivo, el tamaño óptimo de la organización o un cargo directo de toma de decisiones.17  
* Gamma\_j representa el puntaje de penalización negativo asociado con un atributo desfavorable (representado por la variable binaria y\_j), como el uso de dominios de correo electrónico de consumo (e.g., Gmail), geografía fuera del área de cobertura de servicio o la inactividad prolongada del prospecto.21

### **Funcionamiento de la Inteligencia Artificial Autónoma y Calificación en Frío**

Para resolver el problema del "arranque en frío" (cold-start) cuando un inquilino (tenant) se registra por primera vez y no cuenta con datos históricos de conversión para entrenar un modelo predictivo, la plataforma aplica una plantilla de calificación preconfigurada.18 Esta plantilla preconfigurada se basa en modelos globales entrenados con metadatos agregados de la industria.18  
A medida que el inquilino interactúa con nuevos prospectos en los canales conversacionales, el sistema recopila variables de comportamiento y firmográficas.17 Cuando la base de datos registra un volumen de datos suficiente (típicamente al menos 1,000 contactos con etapas de conversión claramente marcadas como ganadas o perdidas), un pipeline de procesamiento ejecuta de manera automatizada un entrenamiento localizado utilizando clasificadores supervisados, como el algoritmo de Clasificación de Gradiente Aumentado (Gradient Boosting Classifier) o redes neuronales poco profundas.16 Este modelo calcula de manera continua el valor probabilístico de conversión (P\_ML) basado en la similitud de comportamiento y perfil del nuevo lead en comparación con las conversiones exitosas del pasado.17  
A nivel técnico, el motor gestiona de manera automática la degradación del puntaje por inactividad (score decay), reduciendo la puntuación de comportamiento si el prospecto no interactúa durante un periodo determinado.21 Esto evita que leads con interacciones antiguas y obsoletas aparezcan artificialmente como prospectos de alta prioridad en el embudo visual.21

## **Arquitectura Multi-Tenant del Backend y Modelo de Base de Datos MySQL**

Para implementar este CRM conversacional con soporte multitenant (múltiples inquilinos compartiendo la misma infraestructura tecnológica de manera aislada) utilizando Python con FastAPI en el backend y MySQL como base de datos, se adopta un diseño de aislamiento lógico a nivel de fila (Shared Database, Shared Schema).27 Este enfoque garantiza la máxima eficiencia en el uso de recursos y simplifica la gestión de migraciones del esquema de base de datos a gran escala.27

### **Modelo de Datos en MySQL**

La base de datos MySQL debe estar optimizada mediante la inclusión de columnas de identificación de inquilino (tenant\_id) en cada tabla, asegurando la integridad referencial y aplicando índices compuestos para acelerar la velocidad de consulta.27 Adicionalmente, el almacenamiento de atributos personalizados se realiza mediante una columna nativa tipo JSON.30

SQL  
\-- Tabla base de inquilinos (Tenants)  
CREATE TABLE tenants (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    uuid VARCHAR(36) NOT NULL,  
    domain VARCHAR(100) NOT NULL,  
    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,  
    PRIMARY KEY (id),  
    UNIQUE KEY uq\_uuid (uuid),  
    UNIQUE KEY uq\_domain (domain)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4 COLLATE\=utf8mb4\_unicode\_ci;

\-- Configuración personalizada del scoring por inquilino  
CREATE TABLE tenant\_scoring\_configs (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    tenant\_id INT UNSIGNED NOT NULL,  
    weight\_ml DECIMAL(3,2) NOT NULL DEFAULT 0.50, \-- Coeficiente w\_ML  
    weight\_manual DECIMAL(3,2) NOT NULL DEFAULT 0.50, \-- Coeficiente w\_Manual  
    scoring\_rules JSON NOT NULL, \-- Almacena los puntos asignados a industrias, sectores, etc.  
    updated\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP,  
    PRIMARY KEY (id),  
    FOREIGN KEY (tenant\_id) REFERENCES tenants(id) ON DELETE CASCADE,  
    UNIQUE KEY uq\_tenant\_config (tenant\_id)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

\-- Etapas dinámicas del embudo de ventas  
CREATE TABLE funnel\_stages (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    tenant\_id INT UNSIGNED NOT NULL,  
    name VARCHAR(100) NOT NULL,  
    sort\_order INT NOT NULL DEFAULT 0,  
    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,  
    PRIMARY KEY (id),  
    FOREIGN KEY (tenant\_id) REFERENCES tenants(id) ON DELETE CASCADE,  
    INDEX idx\_tenant\_order (tenant\_id, sort\_order)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

\-- Tabla principal de contactos/leads  
CREATE TABLE contacts (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    tenant\_id INT UNSIGNED NOT NULL,  
    funnel\_stage\_id INT UNSIGNED NULL,  
    full\_name VARCHAR(255) NOT NULL,  
    phone\_number VARCHAR(50) NOT NULL,  
    email VARCHAR(255) NULL,  
    company\_name VARCHAR(255) NULL,  
    industry VARCHAR(100) NULL,  
    lead\_score TINYINT UNSIGNED DEFAULT 0,  
    custom\_attributes JSON NOT NULL, \-- Campos adicionales personalizables por el cliente  
    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,  
    updated\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP,  
    PRIMARY KEY (id),  
    FOREIGN KEY (tenant\_id) REFERENCES tenants(id) ON DELETE CASCADE,  
    FOREIGN KEY (funnel\_stage\_id) REFERENCES funnel\_stages(id) ON DELETE SET NULL,  
    UNIQUE KEY uq\_tenant\_phone (tenant\_id, phone\_number),  
    INDEX idx\_tenant\_stage (tenant\_id, funnel\_stage\_id),  
    INDEX idx\_tenant\_score (tenant\_id, lead\_score)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

\-- Tabla de almacenamiento de atribución UTM  
CREATE TABLE contact\_attributions (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    tenant\_id INT UNSIGNED NOT NULL,  
    contact\_id INT UNSIGNED NOT NULL,  
    utm\_source VARCHAR(100) NULL,  
    utm\_medium VARCHAR(100) NULL,  
    utm\_campaign VARCHAR(100) NULL,  
    utm\_term VARCHAR(100) NULL,  
    utm\_content VARCHAR(100) NULL,  
    meta\_click\_id VARCHAR(255) NULL, \-- ctwa\_clid  
    referral\_data JSON NULL, \-- Guarda el dump completo del webhook de Meta  
    created\_at TIMESTAMP DEFAULT CURRENT\_TIMESTAMP,  
    PRIMARY KEY (id),  
    FOREIGN KEY (tenant\_id) REFERENCES tenants(id) ON DELETE CASCADE,  
    FOREIGN KEY (contact\_id) REFERENCES contacts(id) ON DELETE CASCADE,  
    INDEX idx\_tenant\_utm (tenant\_id, utm\_source, utm\_medium, utm\_campaign)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

### **Resolución de Inquilinos en el Backend con FastAPI**

En el backend, se utiliza un sistema de inyección de dependencias de FastAPI para interceptar cada petición HTTP, extraer la identidad del inquilino (desde un encabezado de solicitud X-Tenant-ID, un subdominio o un token JWT decodificado) y proveer el contexto de forma segura a los servicios y consultas de la base de datos.32

Python  
from fastapi import Request, Header, HTTPException, Depends  
import jwt  
from typing import Optional

SECRET\_KEY \= "super-secret-jwt-key"

class TenantContext:  
    def \_\_init\_\_(self, tenant\_id: int, uuid: str):  
        self.tenant\_id \= tenant\_id  
        self.uuid \= uuid

async def get\_current\_tenant(  
    request: Request,  
    x\_tenant\_id: Optional\[str\] \= Header(None),  
    authorization: Optional\[str\] \= Header(None)  
) \-\> TenantContext:  
    \# 1\. Intentar validar el inquilino a través del JWT de autenticación  
    if authorization and authorization.startswith("Bearer "):  
        token \= authorization.split(" ")\[1\]  
        try:  
            payload \= jwt.decode(token, SECRET\_KEY, algorithms=)  
            tenant\_id \= payload.get("tenant\_id")  
            tenant\_uuid \= payload.get("tenant\_uuid")  
            if tenant\_id and tenant\_uuid:  
                return TenantContext(tenant\_id=int(tenant\_id), uuid=tenant\_uuid)  
        except jwt.PyJWTError:  
            raise HTTPException(status\_code=401, detail="Token de seguridad inválido")

    \# 2\. Alternativa: utilizar el subdominio de la petición del cliente  
    host \= request.headers.get("host", "")  
    if "." in host:  
        subdomain \= host.split(".")  
        \# Consulta en caché o base de datos para recuperar el inquilino basado en el subdominio  
        tenant \= await get\_tenant\_by\_subdomain(subdomain)  
        if tenant:  
            return TenantContext(tenant\_id=tenant\["id"\], uuid=tenant\["uuid"\])

    \# 3\. Fallback: utilizar encabezado directo (restringido a llamadas de integración API externa)  
    if x\_tenant\_id:  
        tenant \= await get\_tenant\_by\_uuid(x\_tenant\_id)  
        if tenant:  
            return TenantContext(tenant\_id=tenant\["id"\], uuid=tenant\["uuid"\])

    raise HTTPException(  
        status\_code=400,   
        detail="No se pudo identificar el contexto del inquilino"  
    )

## **Sincronización en Tiempo Real y Pipeline Dinámico mediante WebSockets**

Para implementar un flujo visual interactivo en la interfaz del cliente (Next.js) que mueva de forma automática las tarjetas de los clientes (leads) entre las diferentes columnas del Kanban (etapas del embudo de ventas) a medida que interactúan la IA y los agentes humanos, se desarrolla un sistema basado en WebSockets coordinado por Redis Pub/Sub.34

Python  
import asyncio  
import json  
from fastapi import APIRouter, WebSocket, WebSocketDisconnect  
import aioredis

router \= APIRouter()  
REDIS\_URL \= "redis://localhost:6379"

class RealtimeConnectionManager:  
    def \_\_init\_\_(self):  
        \# Almacena las conexiones activas agrupadas por inquilino: Dict\]  
        self.connections: dict\] \= {}

    async def connect(self, websocket: WebSocket, tenant\_id: int):  
        await websocket.accept()  
        if tenant\_id not in self.connections:  
            self.connections\[tenant\_id\] \= set()  
        self.connections\[tenant\_id\].add(websocket)

    def disconnect(self, websocket: WebSocket, tenant\_id: int):  
        if tenant\_id in self.connections:  
            self.connections\[tenant\_id\].discard(websocket)  
            if not self.connections\[tenant\_id\]:  
                del self.connections\[tenant\_id\]

    async def broadcast(self, tenant\_id: int, message: dict):  
        if tenant\_id in self.connections:  
            \# Enviar el mensaje a todas las pestañas de navegador conectadas bajo este inquilino  
            disconnected \= set()  
            for connection in self.connections\[tenant\_id\]:  
                try:  
                    await connection.send\_json(message)  
                except Exception:  
                    disconnected.add(connection)  
            for ws in disconnected:  
                self.disconnect(ws, tenant\_id)

manager \= RealtimeConnectionManager()

\# Tarea de fondo ejecutada en FastAPI para escuchar eventos de base de datos desde Redis  
async def listen\_to\_redis\_channel(tenant\_id: int):  
    redis \= aioredis.from\_url(REDIS\_URL, decode\_responses=True)  
    pubsub \= redis.pubsub()  
    await pubsub.subscribe(f"tenant\_{tenant\_id}\_pipeline")  
    try:  
        async for message in pubsub.listen():  
            if message\["type"\] \== "message":  
                event\_data \= json.loads(message\["data"\])  
                \# Retransmitir el evento de Redis a los WebSockets locales de este proceso de FastAPI  
                await manager.broadcast(tenant\_id, event\_data)  
    except asyncio.CancelledError:  
        await pubsub.unsubscribe(f"tenant\_{tenant\_id}\_pipeline")  
        await pubsub.close()

@router.websocket("/ws/pipeline")  
async def websocket\_pipeline\_endpoint(  
    websocket: WebSocket,  
    tenant\_context: TenantContext \= Depends(get\_current\_tenant)  
):  
    tenant\_id \= tenant\_context.tenant\_id  
    await manager.connect(websocket, tenant\_id)  
      
    \# Iniciar el escuchador de Redis específico para el canal de este inquilino  
    listener\_task \= asyncio.create\_task(listen\_to\_redis\_channel(tenant\_id))  
      
    try:  
        while True:  
            \# Mantener la conexión abierta de forma asíncrona procesando pings preventivos  
            data \= await websocket.receive\_text()  
            payload \= json.loads(data)  
            if payload.get("type") \== "ping":  
                await websocket.send\_json({"type": "pong"})  
    except WebSocketDisconnect:  
        manager.disconnect(websocket, tenant\_id)  
        listener\_task.cancel()

### **Funcionamiento de la Transición de Estados desde la Base de Datos al Frontend**

Cuando la inteligencia artificial o un agente humano ejecuta una acción conversacional (por ejemplo, registrar una etiqueta o calificar una conversación), se desencadena el siguiente flujo secuencial 9:

1. **Persistencia en la Base de Datos:** El backend de FastAPI actualiza la tabla de base de datos contacts, cambiando el funnel\_stage\_id y calculando el nuevo lead\_score utilizando el motor híbrido.19  
2. **Publicación del Evento:** El servicio de FastAPI publica un evento de tipo LEAD\_STAGE\_UPDATED en Redis Pub/Sub con los datos de la actualización.34  
3. **Distribución Multicast:** Redis propaga el evento a todas las instancias activas de FastAPI que están conectadas detrás del balanceador de carga.34  
4. **Difusión en Tiempo Real:** Las instancias de FastAPI retransmiten el mensaje a través de WebSockets únicamente a los clientes que pertenecen al tenant\_id propietario del lead.34  
5. **Actualización Visual (Next.js):** El frontend recibe el evento e interactúa con el estado local de React, desencadenando la actualización del tablero Kanban de forma fluida y sin requerir la recarga manual de la página.38

## **Módulo de Analítica Centralizada y Constructor de Cuadros de Mando Personalizables**

Para implementar una consola de analítica personalizable que permita a las empresas predefinir y estructurar sus propios reportes de indicadores clave (KPIs), se diseña un sistema de renderizado dinámico basado en metadatos y esquemas JSON almacenados en la base de datos MySQL.40

### **Base de Datos para Dashboards Personalizables**

Para implementar esta funcionalidad a nivel multi-tenant, se introducen las siguientes estructuras relacionales:

SQL  
\-- Define los indicadores/métricas predeterminadas del sistema  
CREATE TABLE predefined\_metrics (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    metric\_key VARCHAR(100) NOT NULL, \-- Ej: 'leads\_by\_stage', 'conversations\_by\_channel'  
    display\_name VARCHAR(255) NOT NULL,  
    default\_chart\_type ENUM('card', 'bar', 'line', 'pie', 'funnel') NOT NULL,  
    aggregation\_query\_template TEXT NOT NULL, \-- Plantilla SQL estructurada para la consulta  
    PRIMARY KEY (id),  
    UNIQUE KEY uq\_key (metric\_key)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

\-- Estructura de dashboard personalizado por usuario e inquilino  
CREATE TABLE user\_dashboards (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    tenant\_id INT UNSIGNED NOT NULL,  
    user\_id INT UNSIGNED NOT NULL,  
    dashboard\_name VARCHAR(100) NOT NULL,  
    is\_default BOOLEAN NOT NULL DEFAULT FALSE,  
    PRIMARY KEY (id),  
    FOREIGN KEY (tenant\_id) REFERENCES tenants(id) ON DELETE CASCADE,  
    UNIQUE KEY uq\_user\_default (tenant\_id, user\_id, is\_default)  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

\-- Widgets del Dashboard que referencian el esquema dinámico de react-grid-layout  
CREATE TABLE dashboard\_widgets (  
    id INT UNSIGNED AUTO\_INCREMENT,  
    dashboard\_id INT UNSIGNED NOT NULL,  
    predefined\_metric\_id INT UNSIGNED NOT NULL,  
    widget\_title VARCHAR(150) NOT NULL,  
    chart\_type ENUM('card', 'bar', 'line', 'pie', 'funnel') NOT NULL,  
    grid\_layout JSON NOT NULL, \-- Coordenadas de posición x, y, ancho w, alto h para el grid  
    widget\_settings JSON NOT NULL, \-- Parámetros específicos como rango de fecha, filtros  
    PRIMARY KEY (id),  
    FOREIGN KEY (dashboard\_id) REFERENCES user\_dashboards(id) ON DELETE CASCADE,  
    FOREIGN KEY (predefined\_metric\_id) REFERENCES predefined\_metrics(id) ON DELETE CASCADE  
) ENGINE\=InnoDB DEFAULT CHARSET\=utf8mb4;

### **Generación Dinámica y Segura de Consultas Analíticas en FastAPI**

El backend expone un endpoint encargado de leer la configuración de cada widget, interpretar la consulta preconfigurada del sistema de analítica, parametrizar de forma segura el contexto del tenant\_id para evitar inyecciones de código SQL y entregar los resultados agregados 41:

Python  
from fastapi import APIRouter, Depends, HTTPException  
from pydantic import BaseModel  
import sqlalchemy as sa  
from typing import List, Dict, Any

router \= APIRouter()

class WidgetDataRequest(BaseModel):  
    widget\_id: int  
    days\_back: int \= 30

@router.post("/api/analytics/widget-data")  
async def get\_widget\_data(  
    payload: WidgetDataRequest,  
    tenant\_context: TenantContext \= Depends(get\_current\_tenant)  
):  
    \# 1\. Recuperar los metadatos del widget y su métrica asociada  
    query\_widget \= """  
        SELECT w.chart\_type, w.widget\_settings, m.aggregation\_query\_template, m.metric\_key  
        FROM dashboard\_widgets w  
        JOIN user\_dashboards d ON w.dashboard\_id \= d.id  
        JOIN predefined\_metrics m ON w.predefined\_metric\_id \= m.id  
        WHERE w.id \= :widget\_id AND d.tenant\_id \= :tenant\_id  
    """  
      
    with db\_engine.connect() as conn:  
        widget\_meta \= conn.execute(  
            sa.text(query\_widget),   
            {"widget\_id": payload.widget\_id, "tenant\_id": tenant\_context.tenant\_id}  
        ).fetchone()  
          
        if not widget\_meta:  
            raise HTTPException(status\_code=404, detail="Widget no encontrado")  
              
        \# 2\. Reemplazar y parametrizar de manera segura la consulta correspondiente  
        sql\_template \= widget\_meta.aggregation\_query\_template  
          
        \# Ejecución segura parametrizada previniendo la inyección de SQL externo  
        result \= conn.execute(  
            sa.text(sql\_template),   
            {"tenant\_id": tenant\_context.tenant\_id, "days\_back": payload.days\_back}  
        ).fetchall()  
          
        \# 3\. Formatear la respuesta según la métrica para su consumo por el frontend  
        serialized\_data \= \[{"label": row, "value": row\[1\]} for row in result\]  
          
        return {  
            "widget\_id": payload.widget\_id,  
            "chart\_type": widget\_meta.chart\_type,  
            "metric\_key": widget\_meta.metric\_key,  
            "data": serialized\_data  
        }

### **Consultas SQL para Métricas por Niveles de Embudo**

Las siguientes plantillas de consulta representan la lógica de agregación segura almacenada en predefined\_metrics para resolver el reporte de la analítica centralizada, integrando variables demográficas y de comportamiento conversacional 41:

#### **1\. Calificación de Prospectos (Leads por Nivel de Score)**

Esta consulta agrupa a los clientes del inquilino basándose en rangos de calificación predefinidos 23:

SQL  
SELECT   
    CASE   
        WHEN lead\_score \>= 80 THEN 'Caliente (80-100)'  
        WHEN lead\_score \>= 50 THEN 'Templado (50-79)'  
        ELSE 'Frío (0-49)'  
    END AS label,  
    COUNT(\*) AS value  
FROM contacts  
WHERE tenant\_id \= :tenant\_id   
  AND created\_at \>= NOW() \- INTERVAL :days\_back DAY  
GROUP BY label;

#### **2\. Distribución de Contactos por Canal de Origen Conversacional**

Permite evaluar la efectividad de los canales de adquisición integrados 5:

SQL  
SELECT   
    utm\_source AS label,  
    COUNT(\*) AS value  
FROM contact\_attributions  
WHERE tenant\_id \= :tenant\_id   
  AND created\_at \>= NOW() \- INTERVAL :days\_back DAY  
GROUP BY label;

#### **3\. Conversiones del Embudo (Proporción de Leads por Etapa de Kanban)**

Facilita la visualización agregada de la salud del pipeline dinámico 9:

SQL  
SELECT   
    fs.name AS label,  
    COUNT(c.id) AS value  
FROM funnel\_stages fs  
LEFT JOIN contacts c ON c.funnel\_stage\_id \= fs.id AND c.tenant\_id \= :tenant\_id  
WHERE fs.tenant\_id \= :tenant\_id  
GROUP BY fs.id, fs.name, fs.sort\_order  
ORDER BY fs.sort\_order ASC;

## **Interfaz de Usuario y Personalización en el Frontend (Next.js)**

Para habilitar un portal analítico modular, el frontend utiliza Next.js junto con la biblioteca react-grid-layout para la disposición interactiva de los componentes, y primitives de shadcn/ui para el diseño visual de las tarjetas y selectores de métricas.39

### **Renderizador Dinámico de Widgets de Analítica**

El siguiente componente de React en el frontend genera dinámicamente la interfaz gráfica de usuario adaptada a los metadatos guardados por cada inquilino 39:

TypeScript  
"use client";

import { useState, useEffect } from "react";  
import GridLayout, { Layout } from "react-grid-layout";  
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";  
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip } from "recharts";  
import "react-grid-layout/css/styles.css";  
import "react-resizable/css/styles.css";

interface WidgetData {  
  id: number;  
  title: string;  
  chartType: 'card' | 'bar' | 'line' | 'pie';  
  data: { label: string; value: number };  
  layout: Layout;  
}

const COLORS \=;

export default function DynamicDashboard({ tenantId, userId }: { tenantId: string; userId: string }) {  
  const \= useState\<WidgetData\>();  
  const \[isEditing, setIsEditing\] \= useState(false);

  useEffect(() \=\> {  
    // Recuperar la lista de widgets y diseños configurados desde la base de datos del inquilino  
    async function loadDashboard() {  
      const response \= await fetch(\`/api/analytics/dashboard?userId=${userId}\&tenantId=${tenantId}\`);  
      const payload \= await response.json();  
      setWidgets(payload.widgets);  
    }  
    loadDashboard();  
  }, \[userId, tenantId\]);

  const handleLayoutChange \= (currentLayout: Layout) \=\> {  
    setWidgets((prevWidgets) \=\>  
      prevWidgets.map((widget) \=\> {  
        const matchingLayout \= currentLayout.find((l) \=\> l.i \=== widget.id.toString());  
        return matchingLayout? {...widget, layout: matchingLayout } : widget;  
      })  
    );  
  };

  const saveLayout \= async () \=\> {  
    const layoutUpdates \= widgets.map((w) \=\> ({  
      widgetId: w.id,  
      grid\_layout: w.layout,  
    }));  
      
    await fetch("/api/analytics/layout/save", {  
      method: "POST",  
      headers: { "Content-Type": "application/json" },  
      body: JSON.stringify({ layouts: layoutUpdates, tenantId }),  
    });  
    setIsEditing(false);  
  };

  return (  
    \<div className\="w-full min-h-screen bg-slate-50 p-6"\>  
      \<div className\="flex justify-between items-center mb-6"\>  
        \<div\>  
          \<h1 className\="text-3xl font-bold text-slate-900 tracking-tight"\>Consola de Analítica Centralizada\</h1\>  
          \<p className\="text-sm text-slate-500"\>Gestione e integre reportes conversacionales, de adquisición y calificación en tiempo real.\</p\>  
        \</div\>  
        \<button  
          onClick\={isEditing? saveLayout : () \=\> setIsEditing(true)}  
          className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-md shadow hover:bg-primary/90 transition-colors"  
        \>  
          {isEditing? "Guardar Cambios" : "Personalizar Dashboard"}  
        \</button\>  
      \</div\>

      \<GridLayout  
        className\="layout"  
        layout\={widgets.map((w) \=\> w.layout)}  
        onLayoutChange={handleLayoutChange}  
        cols={12}  
        rowHeight={100}  
        width={1200}  
        isDraggable={isEditing}  
        isResizable={isEditing}  
        margin={\[16, 16\]}  
      \>  
        {widgets.map((widget) \=\> (  
          \<div key\={widget.id.toString()} className\="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden"\>  
            \<Card className\="h-full border-0 shadow-none"\>  
              \<CardHeader className\="p-4 border-b border-slate-100 flex flex-row items-center justify-between"\>  
                \<CardTitle className\="text-sm font-semibold text-slate-700"\>{widget.title}\</CardTitle\>  
              \</CardHeader\>  
              \<CardContent className\="p-4 h-\[calc(100%-60px)\]"\>  
                {widget.chartType \=== 'card' && (  
                  \<div className\="flex flex-col justify-center h-full"\>  
                    \<span className\="text-4xl font-bold text-primary"\>{widget.data?.value || 0}\</span\>  
                    \<span className\="text-xs text-slate-400 mt-1"\>{widget.data?.label || 'Total'}\</span\>  
                  \</div\>  
                )}

                {widget.chartType \=== 'bar' && (  
                  \<ResponsiveContainer width\="100%" height\="100%"\>  
                    \<BarChart data\={widget.data}\>  
                      \<XAxis dataKey\="label" fontSize\={11} stroke\="\#64748b" /\>  
                      \<YAxis fontSize\={11} stroke\="\#64748b" /\>  
                      \<Tooltip /\>  
                      \<Bar dataKey\="value" fill\="\#2563eb" radius\={} /\>  
                    \</BarChart\>  
                  \</ResponsiveContainer\>  
                )}

                {widget.chartType \=== 'line' && (  
                  \<ResponsiveContainer width\="100%" height\="100%"\>  
                    \<LineChart data\={widget.data}\>  
                      \<XAxis dataKey\="label" fontSize\={11} stroke\="\#64748b" /\>  
                      \<YAxis fontSize\={11} stroke\="\#64748b" /\>  
                      \<Tooltip /\>  
                      \<Line type\="monotone" dataKey\="value" stroke\="\#3b82f6" strokeWidth\={2} activeDot\={{ r: 8 }} /\>  
                    \</LineChart\>  
                  \</ResponsiveContainer\>  
                )}

                {widget.chartType \=== 'pie' && (  
                  \<ResponsiveContainer width\="100%" height\="100%"\>  
                    \<PieChart\>  
                      \<Pie  
                        data\={widget.data}  
                        dataKey\="value"  
                        nameKey\="label"  
                        cx\="50%"  
                        cy\="50%"  
                        outerRadius\="80%"  
                        label\={({ name, percent }) \=\> \`${name} ${(percent \* 100).toFixed(0)}%\`}  
                      \>  
                        {widget.data.map((\_, index) \=\> (  
                          \<Cell key\={\`cell-${index}\`} fill\={COLORS} /\>  
                        ))}  
                      \</Pie\>  
                      \<Tooltip /\>  
                    \</PieChart\>  
                  \</ResponsiveContainer\>  
                )}  
              \</CardContent\>  
            \</Card\>  
          \</div\>  
        ))}  
      \</GridLayout\>  
    \</div\>  
  );  
}

Este diseño desacopla la lógica de visualización del código de la interfaz de usuario, permitiendo que las organizaciones agreguen, eliminen o reconfiguren de forma segura las dimensiones y visualizaciones visuales basándose exclusivamente en la interpretación dinámica de metadatos de configuración en su base de datos aislada.40

## **Conclusiones y Recomendaciones de Implementación**

La implementación óptima de este sistema en el proyecto tecnológico requiere la adopción sistemática de las siguientes prácticas de ingeniería:

* **Estrategia para Evitar Fugas de Datos (Cross-Tenant Data Leaks):** Para garantizar un aislamiento total entre inquilinos sin incurrir en la sobrecarga de bases de datos individuales, se recomienda automatizar la inyección de la cláusula de seguridad tenant\_id en el ORM (como SQLAlchemy en FastAPI).27 Esto se puede lograr mediante la reescritura automática de consultas utilizando ganchos (hooks) o middlewares de base de datos que apliquen de forma obligatoria el filtro WHERE tenant\_id \= :current\_tenant\_id en cada transacción, eliminando el riesgo de errores de desarrollo humanos.27  
* **Optimización de Tráfico en WebSockets:** Para escalar el servidor de WebSockets a miles de agentes concurrentes en tiempo real, evite enviar la estructura de datos completa en cada actualización de estado.35 En su lugar, utilice un patrón de actualización por deltas (Delta Updates), enviando exclusivamente el identificador de lead modificado y la nueva columna asignada.35 El cliente en Next.js se encargará de realizar la transición visual del elemento afectado, reduciendo el consumo de ancho de banda y mitigando problemas de latencia de red.34  
* **Resguardo del Atributo de Referencia (Meta Webhook Constraint):** Se debe implementar una política de redundancia de almacenamiento de eventos de llegada inmediata (Cold Ingestion Queue) mediante un bróker de mensajería asíncrona.12 El webhook del referral de Meta solo se emite una vez 11; si el servidor de base de datos MySQL se encuentra bajo una rutina de mantenimiento o bloqueo de tablas temporal, la caída del endpoint HTTP de FastAPI provocaría la pérdida irrecuperable de la atribución del lead.11 Un buffer intermedio en Redis garantiza la persistencia segura de las tramas de atribución entrantes.12  
* **Caché para la Calificación Inteligente (Lead Scoring Engine):** El cálculo de modelos predictivos de aprendizaje automático (P\_ML) es costoso a nivel computacional si se realiza de forma sincrónica con cada mensaje recibido.17 Por lo tanto, se sugiere ejecutar el motor de calificación de forma asíncrona en tareas programadas en segundo plano (workers), o limitar su ejecución en tiempo real exclusivamente cuando el lead alcanza un cambio de etapa específico dentro de las columnas del Kanban.19 Esto mantiene la base de datos libre de sobrecargas continuas, maximizando el rendimiento general de la plataforma conversacional.

#### **Fuentes citadas**

1. AtomChat.io Reviews 2026: Details, Pricing, & Features \- G2, acceso: junio 4, 2026, [https://www.g2.com/products/atomchat-io/reviews](https://www.g2.com/products/atomchat-io/reviews)  
2. WhatsApp Campaign Conversation Tracking With Interakt, acceso: junio 4, 2026, [https://www.interakt.shop/resource-center/whatsapp-campaign-conversation-tracking/](https://www.interakt.shop/resource-center/whatsapp-campaign-conversation-tracking/)  
3. ​​Track WhatsApp ad campaigns with UTMs — Kommo, acceso: junio 4, 2026, [https://www.kommo.com/support/messenger-apps/whatsapp-analytics-utms/](https://www.kommo.com/support/messenger-apps/whatsapp-analytics-utms/)  
4. WhatsApp Smart Links Tracking for Shopify Merchants: Fix Direct Traffic and Track Sales Better \- Zoko, acceso: junio 4, 2026, [https://www.zoko.io/post/track-whatsapp-links-utm-tags](https://www.zoko.io/post/track-whatsapp-links-utm-tags)  
5. Atom Software Pricing, Alternatives & More 2026 | Capterra, acceso: junio 4, 2026, [https://www.capterra.com/p/202763/Atom/](https://www.capterra.com/p/202763/Atom/)  
6. Compare Atom vs. CSG Xponent in 2026 \- Slashdot, acceso: junio 4, 2026, [https://slashdot.org/software/comparison/Atom-Chat-vs-CSG-Xponent/](https://slashdot.org/software/comparison/Atom-Chat-vs-CSG-Xponent/)  
7. Compare Atom vs. Atomic Chat in 2026 \- Slashdot, acceso: junio 4, 2026, [https://slashdot.org/software/comparison/Atom-Chat-vs-Atomic-Chat/](https://slashdot.org/software/comparison/Atom-Chat-vs-Atomic-Chat/)  
8. Atom Website, acceso: junio 4, 2026, [https://new.atomchat.io/en](https://new.atomchat.io/en)  
9. Best AI tools for sales funnel automation in 2026: Top 10 compared \- Dashly blog, acceso: junio 4, 2026, [https://www.dashly.io/blog/best-ai-tools-for-sales-funnel-automation/](https://www.dashly.io/blog/best-ai-tools-for-sales-funnel-automation/)  
10. WhatsApp Conversion Tracking: Why Your Attribution Breaks and ..., acceso: junio 4, 2026, [https://digitalmicroenterprise.com/whatsapp-conversion-tracking](https://digitalmicroenterprise.com/whatsapp-conversion-tracking)  
11. Click-to-WhatsApp Ads (CTWA): 2026 guide \- AsisteClick, acceso: junio 4, 2026, [https://asisteclick.com/blog/click-to-whatsapp-ads-ctwa-conversion-2026/](https://asisteclick.com/blog/click-to-whatsapp-ads-ctwa-conversion-2026/)  
12. Capture Facebook Click-to-WhatsApp Ad ID / Ref and send to Chatwoot via n8n \- Questions, acceso: junio 4, 2026, [https://community.n8n.io/t/capture-facebook-click-to-whatsapp-ad-id-ref-and-send-to-chatwoot-via-n8n/284723](https://community.n8n.io/t/capture-facebook-click-to-whatsapp-ad-id-ref-and-send-to-chatwoot-via-n8n/284723)  
13. Aviators Training Centre \- Executive Summary \- Aman Suryavanshi, acceso: junio 4, 2026, [https://amansuryavanshi.me/projects/aviators-training-centre-executive-summary](https://amansuryavanshi.me/projects/aviators-training-centre-executive-summary)  
14. Instagram Referral Code not sent via Webhook (messaging\_referral event) \- Stack Overflow, acceso: junio 4, 2026, [https://stackoverflow.com/questions/74272831/instagram-referral-code-not-sent-via-webhook-messaging-referral-event](https://stackoverflow.com/questions/74272831/instagram-referral-code-not-sent-via-webhook-messaging-referral-event)  
15. creating a link that will open facebook messenger and send a message \- Stack Overflow, acceso: junio 4, 2026, [https://stackoverflow.com/questions/42683326/creating-a-link-that-will-open-facebook-messenger-and-send-a-message](https://stackoverflow.com/questions/42683326/creating-a-link-that-will-open-facebook-messenger-and-send-a-message)  
16. AI CRM With Predictive Lead Scoring for Sales Teams, acceso: junio 4, 2026, [https://www.coffee.ai/articles/ai-crm-predictive-lead-scoring/](https://www.coffee.ai/articles/ai-crm-predictive-lead-scoring/)  
17. Understanding AI lead scoring: Definition, benefits, and how to get started \- Demandbase, acceso: junio 4, 2026, [https://www.demandbase.com/blog/ai-lead-scoring/](https://www.demandbase.com/blog/ai-lead-scoring/)  
18. AI lead scoring made simple: a practical guide for 2026 \- Monday.com, acceso: junio 4, 2026, [https://monday.com/blog/crm-and-sales/ai-lead-scoring/](https://monday.com/blog/crm-and-sales/ai-lead-scoring/)  
19. What Is Predictive Lead Scoring? (& How it Helps Conversions) | Default, acceso: junio 4, 2026, [https://www.default.com/post/predictive-lead-scoring](https://www.default.com/post/predictive-lead-scoring)  
20. Lead Scoring Models Explained: Types, Comparison & How to Choose the Right One, acceso: junio 4, 2026, [https://nc-squared.com/blog/article/what-are-lead-scoring-models](https://nc-squared.com/blog/article/what-are-lead-scoring-models)  
21. Lead Scoring Software | Prioritize Your Best Prospects \- HubSpot, acceso: junio 4, 2026, [https://www.hubspot.com/products/marketing/lead-scoring](https://www.hubspot.com/products/marketing/lead-scoring)  
22. How to Build a Lead Scoring System That Actually Works \- Business.com, acceso: junio 4, 2026, [https://www.business.com/articles/build-a-lead-scoring-system/](https://www.business.com/articles/build-a-lead-scoring-system/)  
23. Dynamic Lead Scoring Models: Template Guide \- Reform.app, acceso: junio 4, 2026, [https://www.reform.app/blog/dynamic-lead-scoring-models-template-guide](https://www.reform.app/blog/dynamic-lead-scoring-models-template-guide)  
24. AI-Powered Lead Scoring in HubSpot: How Reliable is Predictive Prioritization? \- bakedwith, acceso: junio 4, 2026, [https://www.bakedwith.com/en/blog/ai-powered-lead-scoring-in-hubspot](https://www.bakedwith.com/en/blog/ai-powered-lead-scoring-in-hubspot)  
25. The relevance of lead prioritization: a B2B lead scoring model based on machine learning, acceso: junio 4, 2026, [https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1554325/full](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1554325/full)  
26. How Predictive Lead Scoring Works Inside Dynamics 365 CRM | MSDynamicsWorld.com, acceso: junio 4, 2026, [https://msdynamicsworld.com/blog/how-predictive-lead-scoring-works-inside-dynamics-365-crm](https://msdynamicsworld.com/blog/how-predictive-lead-scoring-works-inside-dynamics-365-crm)  
27. How to Design a Multi-Tenant Database in MySQL \- OneUptime, acceso: junio 4, 2026, [https://oneuptime.com/blog/post/2026-03-31-mysql-design-multi-tenant-database/view](https://oneuptime.com/blog/post/2026-03-31-mysql-design-multi-tenant-database/view)  
28. Multi-Tenant Database Architecture Patterns Explained \- Bytebase, acceso: junio 4, 2026, [https://www.bytebase.com/blog/multi-tenant-database-architecture-patterns-explained/](https://www.bytebase.com/blog/multi-tenant-database-architecture-patterns-explained/)  
29. Designing a Multi-Tenant Database Schema: Patterns and Trade-offs | ER Flow, acceso: junio 4, 2026, [https://erflow.io/en/blog/designing-multi-tenant-database-schema](https://erflow.io/en/blog/designing-multi-tenant-database-schema)  
30. Dynamic fields In a Application. 1\. Overview | by dev4naveen \- Medium, acceso: junio 4, 2026, [https://medium.com/@dev4naveen/dynamic-fields-in-a-application-efe33e4abd5a](https://medium.com/@dev4naveen/dynamic-fields-in-a-application-efe33e4abd5a)  
31. Custom Attributes in Relational Databases \- DZone, acceso: junio 4, 2026, [https://dzone.com/articles/custom-attributes-in-relational-databases](https://dzone.com/articles/custom-attributes-in-relational-databases)  
32. Multi-tenant FastAPI \- features, workflows and more, configurable per customer\! \- Reddit, acceso: junio 4, 2026, [https://www.reddit.com/r/FastAPI/comments/1rvwwbi/multitenant\_fastapi\_features\_workflows\_and\_more/](https://www.reddit.com/r/FastAPI/comments/1rvwwbi/multitenant_fastapi_features_workflows_and_more/)  
33. Building an Enterprise Chatbot: React, FastAPI, and WebSocket Architecture | Charles Sieg, acceso: junio 4, 2026, [https://charlessieg.com/articles/enterprise-chatbot-react-fastapi-websocket-architecture.html](https://charlessieg.com/articles/enterprise-chatbot-react-fastapi-websocket-architecture.html)  
34. How to Implement WebSockets in FastAPI \- OneUptime, acceso: junio 4, 2026, [https://oneuptime.com/blog/post/2026-02-02-fastapi-websockets/view](https://oneuptime.com/blog/post/2026-02-02-fastapi-websockets/view)  
35. Top 5 FastAPI WebSocket Patterns for Massive Dashboards | by Vectorlane \- Medium, acceso: junio 4, 2026, [https://medium.com/@jickpatel611/top-5-fastapi-websocket-patterns-for-massive-dashboards-ed6707001dad](https://medium.com/@jickpatel611/top-5-fastapi-websocket-patterns-for-massive-dashboards-ed6707001dad)  
36. Best sales funnel software: 15 platforms to fix pipeline blind spots, acceso: junio 4, 2026, [https://monday.com/blog/crm-and-sales/sales-funnel-software/](https://monday.com/blog/crm-and-sales/sales-funnel-software/)  
37. DigiDelight | CRM, Customer Engagement & Productivity Platform, acceso: junio 4, 2026, [https://digidelight.ai/](https://digidelight.ai/)  
38. Shadcn Admin Dashboard with Built-in AI Prompts for Faster Development, acceso: junio 4, 2026, [https://shadcnspace.com/admin-dashboard](https://shadcnspace.com/admin-dashboard)  
39. React Grid Layout in shadcn \#10466 \- GitHub, acceso: junio 4, 2026, [https://github.com/shadcn-ui/ui/discussions/10466](https://github.com/shadcn-ui/ui/discussions/10466)  
40. Dashboard JSON model \- Grafana documentation, acceso: junio 4, 2026, [https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/view-dashboard-json-model/)  
41. How to build MySQL Dashboards from MySQL data \- Draxlr, acceso: junio 4, 2026, [https://www.draxlr.com/blogs/how-to-build-dashboards-from-mysql-data/](https://www.draxlr.com/blogs/how-to-build-dashboards-from-mysql-data/)  
42. How to Generate schema.json (MySQL, Oracle) \- AI-SQL-Chat, acceso: junio 4, 2026, [https://aisql.pl/schema-to-json.html](https://aisql.pl/schema-to-json.html)  
43. Gridstack.js | Build interactive dashboards in minutes., acceso: junio 4, 2026, [https://gridstackjs.com/](https://gridstackjs.com/)  
44. Build a Dashboard with shadcn/ui: Complete Guide (2026) \- DesignRevision, acceso: junio 4, 2026, [https://designrevision.com/blog/shadcn-dashboard-tutorial](https://designrevision.com/blog/shadcn-dashboard-tutorial)