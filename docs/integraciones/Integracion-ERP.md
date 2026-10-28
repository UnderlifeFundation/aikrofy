# **Directiva Maestra de Programación y Arquitectura de Integración para el Módulo de ERPs en Aikrofy: Especificación de Modelos Canónicos, Protocolos Estándar y Motor de Adaptación para Sistemas a Medida**

La arquitectura de integración de sistemas de planificación de recursos empresariales (ERP) en la plataforma backend de Python de Aikrofy requiere una abstracción robusta que unifique la heterogeneidad de los protocolos de comunicación empresariales.1 Al igual que se ha implementado con éxito para las plataformas de comercio electrónico, el objetivo fundamental consiste en dotar a un sistema multiagente de inteligencia artificial de la capacidad de analizar, editar, actualizar y crear datos en cualquier ERP estándar o personalizado sin requerir reescrituras de código o adaptaciones manuales por cliente.3  
La consolidación de flujos de datos financieros, operativos e inventarios mediante agentes autónomos exige un acoplamiento laxo entre la lógica cognitiva de los modelos de lenguaje y los sistemas transaccionales subyacentes.3 Mediante el diseño de un middleware estandarizado y el uso de modelos canónicos de datos, se garantiza una interfaz de ejecución homogénea capaz de aislar los detalles de bajo nivel de cada ERP conectado por los usuarios.4

## **Arquitectura de Estandarización de Datos y Modelos Canónicos**

Para interactuar con múltiples sistemas contables y operativos de forma transparente, el backend de Python de Aikrofy debe implementar un patrón de diseño basado en Modelos Canónicos.1 Este enfoque resuelve el crecimiento exponencial de código que ocurriría si se crearan conectores específicos uno a uno.1 En su lugar, el sistema multiagente interactúa exclusivamente con esquemas normalizados construidos mediante Pydantic V2, que representan las entidades del negocio independientemente del ERP de origen.7  
La normalización conceptual debe mitigar las diferencias en la forma en que cada ERP procesa la misma entidad de negocio.2 Por ejemplo, mientras que ciertas plataformas como Odoo y Xero tratan las facturas de proveedores (Bills) y las facturas de clientes (Invoices) bajo un mismo modelo base con tipos diferenciados, otros sistemas como QuickBooks Online o SAP Business One las modelan como entidades independientes.9 El mapeador de Aikrofy reconcilia de manera automática estas inconsistencias estructurales.9

### **Matriz de Mapeo de Entidades Canónicas y Sistemas ERP**

La siguiente tabla describe la relación de mapeo entre los esquemas de datos normalizados dentro de Aikrofy y las entidades nativas correspondientes en los cuatro principales entornos estándar de la industria.

| Entidad Canónica de Aikrofy | SAP Business One (OData v4) | Oracle NetSuite (SuiteTalk REST) | Odoo ERP (ORM Models) | Microsoft Dynamics 365 BC |
| :---- | :---- | :---- | :---- | :---- |
| **Invoices (Facturas Emitidas)** | Invoices 11 | invoice 12 | account.move (move\_type='out\_invoice') 14 | salesInvoices 15 |
| **Customers (Clientes)** | BusinessPartners (CardType='C') 11 | customer 13 | res.partner (is\_company=True/False) 14 | customers 17 |
| **Vendors (Proveedores)** | BusinessPartners (CardType='S') 11 | vendor 12 | res.partner 14 | vendors 17 |
| **Journal Entries (Asientos Contables)** | JournalEntries 11 | journalEntry 12 | account.move (move\_type='entry') 14 | journalLines 15 |
| **Items (Productos e Inventario)** | Items 11 | item 18 | product.product 14 | items 19 |
| **Purchase Invoices (Facturas de Proveedor)** | PurchaseInvoices 11 | vendorBill 12 | account.move (move\_type='in\_invoice') 14 | purchaseInvoices 15 |

### **Flexibilidad de Esquema y Datos Suplementarios (Passthrough)**

La rigidez de un modelo canónico representa un obstáculo para clientes corporativos que emplean campos personalizados en sus ERPs.6 Para solventar este problema, el middleware de integración de Aikrofy debe incorporar un motor de datos suplementarios y solicitudes de paso directo (*passthrough requests*).10  
Cuando el sistema multiagente requiere acceder a atributos específicos no definidos en el modelo común, puede invocar un método passthrough que redirige la consulta directamente a la API nativa del ERP.10 La respuesta nativa se procesa recursivamente agregando los valores personalizados bajo la propiedad custom\_fields del payload canónico.6 Esto permite al agente de IA analizar variables complejas de negocio (como el nivel de prioridad de un cliente, clasificaciones fiscales regionales o códigos de proyectos internos) sin romper las restricciones de validación estricta del esquema canónico.6

## **Especificaciones Técnicas de los Protocolos ERP Estándar**

### **SAP Business One Service Layer (OData v4)**

La Service Layer de SAP Business One representa una API REST basada en el estándar OData.11 A partir del Feature Pack 2405, SAP ha declarado obsoleta la versión OData v3, consolidando OData v4 como el protocolo primordial bajo la ruta base /b1s/v2/.11 La arquitectura interna de esta capa consta de cuatro componentes clave: el analizador OData, la biblioteca DI Core (que expone de manera exacta los mismos metadatos que la biblioteca DI API de escritorio), el gestor de sesiones y el motor OBServer, responsable de la lógica empresarial pesada, como cálculos fiscales y validaciones financieras en tiempo real.11

Estructura de la URL Base: https://{sap-server-instance}:50000/b1s/v2/

#### **Flujo de Autenticación y Conservación de la Sesión**

SAP Business One se desvía de los esquemas convencionales de tokens portadores estáticos u OAuth 2.0 en su Service Layer clásica, recurriendo a una autenticación basada en sesiones por cookies.11

* **Protocolo de Inicio de Sesión:** Se envía una solicitud HTTP POST al endpoint /b1s/v2/Login con las credenciales del inquilino.11  
* **Cuerpo de la Solicitud (JSON):**  
  JSON  
  {  
    "CompanyDB": "SBO\_DEMO\_US",  
    "UserName": "manager",  
    "Password": "your-secure-password"  
  }

* **Persistencia del Contexto:** Al procesar con éxito las credenciales, el servidor devuelve un código de estado 200 OK junto con un payload que incluye un identificador SessionId y cookies de sesión (B1SESSION y ROUTEID) en las cabeceras de respuesta.11 Es imperativo que el driver de Python almacene estas cookies en un gestor de caché centralizado y las reutilice mediante un objeto requests.Session().11 La llamada inicial de login conlleva una penalización de rendimiento de aproximadamente 5 segundos debido al inicio de componentes del DI Core, mientras que las solicitudes subsiguientes utilizando la cookie activa se procesan en un promedio de 20 milisegundos.11 Las sesiones expiran automáticamente tras 30 minutos de inactividad.11

#### **Consultas Avanzadas y Navegación de Datos**

El lenguaje de consulta OData permite realizar peticiones estructuradas directamente desde la llamada de red.11 El driver de Aikrofy debe traducir los parámetros canónicos a filtros OData equivalentes.11

* **Selección, Ordenación y Filtrado:**  
  HTTP  
  GET /b1s/v2/BusinessPartners?$select=CardCode,CardName,U\_CustomerTier&$filter=CardType eq 'cCustomer' and U\_CustomerTier eq 'Gold'&$orderby=CardCode&$top=50

* **Control de Paginación:** Por defecto, el servidor limita la respuesta a 20 registros por página.11 El driver debe inyectar la cabecera Prefer: odata.maxpagesize=100 o aplicar paginación controlada por el cliente mediante el uso de $top y $skip.11 Al recibir respuestas paginadas, el driver debe analizar la propiedad @odata.nextLink para extraer de forma recursiva los bloques subsiguientes de información.19  
* **Campos de Usuario (UDF):** Los campos personalizados se identifican por llevar siempre el prefijo U\_.11 El mapeador dinámico debe preservar este prefijo al interactuar con atributos extendidos.11

### **Oracle NetSuite SuiteTalk (REST y SuiteQL)**

La plataforma NetSuite de Oracle ofrece múltiples superficies de comunicación, siendo la API REST de SuiteTalk y el motor de consultas SuiteQL las alternativas preferidas sobre las interfaces SOAP históricas para implementaciones modernas de integración.13

Estructura de la URL Base: https://{accountId}.suitetalk.api.netsuite.com/services/rest/record/v1/

#### **Autenticación Segura mediante OAuth 2.0 (Flujo de Credenciales de Cliente)**

Para garantizar la operación desatendida del sistema multiagente en tareas de segundo plano, se debe emplear el flujo de credenciales de cliente bajo OAuth 2.0.24

* **Endpoint de Token:** POST https://{accountId}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token 13  
* **Cuerpo de la Solicitud (Form URL Encoded):**  
  HTTP  
  grant\_type=client\_credentials\&client\_id={your\_client\_id}\&client\_secret={your\_client\_secret}

* **Rotación de Credenciales:** Aunque NetSuite soporta OAuth 2.0 estándar, la vigencia del token de refresco por defecto está limitada a 7 días, lo que exigiría la intervención recurrente de un operador humano para otorgar consentimientos en la interfaz gráfica.12 Para evitar interrupciones de sincronización, la arquitectura de Aikrofy debe gestionar el almacenamiento seguro de la clave privada e implementar la firma JWT para solicitar tokens de acceso asíncronos bajo demanda en cada ciclo de ejecución, o apoyarse en Autenticación Basada en Tokens (TBA) firmada con HMAC-SHA256 para llamadas directas sin vencimiento de sesión.13

#### **Extracción con SuiteQL (Consultas SQL Relacionales)**

Las lecturas mediante endpoints de registro estáticos (/services/rest/record/v1/{recordType}/{id}) resultan ineficientes para la IA debido a que NetSuite ejecuta flujos de trabajo, secuencias de comandos de usuario y validaciones síncronas en cada petición de lectura, lo que degrada drásticamente la latencia.12 Para optimizar la lectura masiva de datos y realizar uniones complejas, el backend de Aikrofy debe canalizar las solicitudes de lectura a través del endpoint de SuiteQL.13

HTTP  
POST https://{accountId}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql  
Authorization: Bearer {access\_token}  
Content-Type: application/json  
Prefer: transient

JSON  
{  
  "q": "SELECT t.id, t.tranid, t.trandate, c.companyname, t.total FROM transaction t JOIN customer c ON t.entity \= c.id WHERE t.type \= 'SalesOrd' AND t.trandate \>= '2026-01-01' ORDER BY t.trandate DESC"  
}

### **Odoo ERP External API (XML-RPC, JSON-RPC, y JSON-2)**

Odoo expone la totalidad de su capa lógica y su base de datos Postgres a través de llamadas de procedimiento remoto que interactúan con su Framework de ORM nativo.14

Endpoint XML-RPC: http://{odoo-instance-domain}/xmlrpc/2/object  
Endpoint JSON-RPC: http://{odoo-instance-domain}/jsonrpc

#### **Estrategia de Transición de Protocolos (Odoo 19/20)**

* **Advertencia de Depreciación:** Odoo ha anunciado de manera oficial la eliminación completa de las interfaces XML-RPC y JSON-RPC para la futura versión Odoo 20 (proyectada para otoño de 2026).14 En su lugar, a partir de Odoo 19, se introduce la API "JSON-2", que opera bajo convenciones REST estándar y tokens portadores (*bearer tokens*).14  
* **Diseño del Driver Adaptable:** El backend de Aikrofy debe implementar un despachador dinámico que identifique la versión de la instancia del cliente. Si la versión es inferior a Odoo 19, canalizará los comandos a través de llamadas RPC tradicionales 14; si es superior o igual, empleará las rutas de la API JSON-2, manteniendo así la interoperabilidad del sistema multiagente.14

#### **Flujo de Autenticación de Dos Pasos**

La seguridad transaccional prohíbe el uso de la contraseña maestra del usuario en llamadas recurrentes de API.14 Se requiere configurar claves de API dedicadas (*API Keys*) en Odoo y gestionar la sesión en dos pasos.14

1. **Solicitud de Identificador (UID):** Se realiza una llamada inicial al servicio común para validar la base de datos y obtener el identificador de usuario estable (uid).14  
2. **Llamada de Datos Contables:** El uid y la clave de API (empleada como contraseña) se inyectan en cada invocación del método de objetos execute\_kw.14

#### **Ejecución de Consultas mediante execute\_kw**

Cualquier interacción con la base de datos en Odoo se ejecuta mapeando métodos del ORM sobre el controlador execute\_kw.16 Los parámetros de entrada deben estructurarse de acuerdo con el siguiente formato posicional:  
![][image1]

* **Creación de un Registro:** El método create toma una lista con un diccionario que define las propiedades iniciales del objeto y devuelve el entero único asignado como clave primaria en la base de datos.16  
* **Lectura de Registros con Filtros (Domain):** Se debe emplear la función search\_read para aplicar operadores lógicos y recuperar únicamente los atributos que requiere el agente de IA, optimizando la ventana de contexto de los modelos LLM.3  
  Python  
  \# Ejemplo de extracción optimizada de facturas posted en los últimos 30 días  
  invoices \= models.execute\_kw(  
      db, uid, api\_key, 'account.move', 'search\_read',  
      \[\['move\_type', '=', 'out\_invoice'\],  
          \['state', '=', 'posted'\],  
          \['invoice\_date', '\>=', '2026-04-01'\]\],  
      {'fields': \['name', 'partner\_id', 'amount\_total', 'invoice\_date'\], 'limit': 100}  
  )

### **Microsoft Dynamics 365 Business Central (OData v4)**

Business Central expone sus datos financieros a través de endpoints REST basados en el protocolo OData v4, organizados jerárquicamente bajo un sistema multi-entorno y multi-compañía.15

Estructura de la URL Cloud: https://api.businesscentral.dynamics.com/v2.0/{tenantId}/{environmentName}/api/v2.0/

#### **Integración de Autenticación S2S en Microsoft Entra ID**

Para habilitar la sincronización desatendida entre el backend de Python de Aikrofy y Business Central, se debe registrar una aplicación multitenant o single-tenant en el portal de Microsoft Entra ID.25

* **Flujo OAuth 2.0:** Credenciales de cliente (client\_credentials) contra el directorio activo de Microsoft Azure.17  
* **Petición de Acceso:**  
  HTTP  
  POST https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token  
  Content-Type: application/x-www-form-urlencoded

  grant\_type=client\_credentials\&client\_id={clientId}\&client\_secret={clientSecret}\&scope=https://api.businesscentral.dynamics.com/.default

* **Aprovisionamiento Interno:** La aplicación registrada debe configurarse dentro de la consola administrativa de Business Central como un usuario de aplicación, vinculándole los conjuntos de permisos específicos correspondientes a las acciones que los agentes de IA ejecutarán sobre el entorno operativo.25

#### **Optimización y Mitigación de Cuotas de Servicio (Rate Limiting)**

* **Restricciones de Cuota:** Microsoft impone un límite de servicio estricto de aproximadamente 6,000 solicitudes por cada 5 minutos por usuario de API.27 Si el sistema multiagente realiza consultas frecuentes para validar estados de facturas u órdenes, este límite puede agotarse rápidamente.27  
* **Remediación mediante Consultas $batch:** Para reducir las solicitudes de red, el middleware de integración debe agrupar operaciones transaccionales relacionadas dentro del endpoint $batch de OData.27 De este modo, múltiples escrituras o consultas se empaquetan en una única petición HTTP síncrona que consume únicamente una unidad en el contador de la cuota de rate-limiting.27  
* **Funciones Especiales de Fecha en Filtros:** Para evitar inconsistencias horarias debido a diferencias de zona horaria entre la base de datos de Dynamics 365 y el backend de Aikrofy, se debe estructurar las consultas utilizando la función OData date() nativa del motor de base de datos.19  
  HTTP  
  GET /api/v2.0/companies({companyId})/salesInvoices?$filter=date(postingDate) eq 2026-05-15

## **Motor de Adaptación para ERPs Personalizados y a Medida**

Cuando un cliente empresarial conecta un sistema ERP propietario o altamente personalizado, el backend de Aikrofy no cuenta con una especificación predefinida.6 Para solucionar esto, el sistema utiliza un **Motor de Adaptación Dinámica de Esquemas**.7 Este motor permite estandarizar APIs desconocidas o personalizadas mediante metadatos almacenados en base de datos bajo formato JSON Schema.7

### **Arquitectura de Mapeo Basada en Sobrescrituras de Tres Niveles**

Para acomodar las variaciones que cada organización introduce en sus instancias del ERP, el motor aplica una jerarquía de transformación de datos estructurada en tres niveles lógicos de sobrescritura progresiva.6 Esta jerarquía de mapeo procesa recursivamente las propiedades del JSON de respuesta antes de entregarlo a la capa cognitiva del agente de IA 6:

1. **Mapeo de Nivel de Plataforma (Platform-level):** Define las transformaciones generales aplicables a un motor ERP específico.6 Utiliza expresiones JSONata o plantillas de transformación de diccionarios para estructurar el payload inicial del proveedor hacia el formato canónico.6  
2. **Sobrescritura de Nivel de Entorno (Environment override):** Aplica reglas específicas para diferenciar entornos de staging, sandbox o producción del cliente, ajustando parámetros de direccionamiento, claves personalizadas de negocio o tratamientos fiscales específicos.6  
3. **Sobrescritura de Nivel de Cuenta (Account override):** Resuelve el mapeo de campos a nivel de inquilino específico.6 Si una organización concreta posee 47 campos personalizados en sus tablas transaccionales, las reglas de este nivel extraen dinámicamente dichos atributos y los inyectan en el bloque común de datos suplementarios, garantizando compatibilidad absoluta sin alterar la base del código.6

                  \+-----------------------------------+  
                  |   Respuesta Nativa del ERP        |  
                  |   (Estructura heterogénea)        |  
                  \+-----------------------------------+  
                                    |  
                                    v  
                  \+-----------------------------------+  
                  | 1\. Mapeo a Nivel de Plataforma    |  
                  |    (Reglas estándar del driver)   |  
                  \+-----------------------------------+  
                                    |  
                                    v  
                  \+-----------------------------------+  
                  | 2\. Sobrescritura de Entorno       |  
                  |    (Ajustes de sandbox o prod)    |  
                  \+-----------------------------------+  
                                    |  
                                    v  
                  \+-----------------------------------+  
                  | 3\. Sobrescritura de Cuenta        |  
                  |    (Inyección de campos a medida) |  
                  \+-----------------------------------+  
                                    |  
                                    v  
                  \+-----------------------------------+  
                  |    Payload Canónico Normalizado   |  
                  |    (Consumido por el agente)      |  
                  \+-----------------------------------+

### **Motor Dinámico de Compilación de Modelos Pydantic V2**

El backend de Python de Aikrofy lee la configuración del ERP del cliente, compila en memoria un modelo de validación utilizando create\_model de Pydantic y valida las entradas de forma dinámica.7 El siguiente fragmento describe la lógica central que ejecuta el motor de adaptación para registrar y validar un ERP a medida a partir de un esquema JSON definido en tiempo de ejecución 7:

Python  
import json  
from typing import Any, Dict, Type, Union  
from pydantic import BaseModel, create\_model, Field

class CustomERPAdapeationEngine:  
    """Compila dinámicamente modelos de Pydantic V2 a partir de esquemas JSON Schemas  
    almacenados en base de datos para validar flujos de datos de ERPs personalizados.  
    """  
      
    @staticmethod  
    def compile\_schema(schema\_name: str, json\_schema\_dict: Dict\[str, Any\]) \-\> Type:  
        properties \= json\_schema\_dict.get("properties", {})  
        required \= json\_schema\_dict.get("required",)  
          
        type\_mapping \= {  
            "string": str,  
            "integer": int,  
            "number": float,  
            "boolean": bool,  
            "object": dict,  
            "array": list  
        }  
          
        dynamic\_fields: Dict\[str, Any\] \= {}  
        for field\_name, metadata in properties.items():  
            json\_type \= metadata.get("type", "string")  
            python\_type \= type\_mapping.get(json\_type, Any)  
              
            \# Gestionar campos opcionales o con tipos combinados  
            if metadata.get("nullable", False):  
                python\_type \= Union\[python\_type, None\]  
                  
            field\_description \= metadata.get("description", f"Atributo dinámico {field\_name}")  
            is\_required \= field\_name in required  
              
            \# Instanciar el campo con metadatos descriptivos que consumirá el agente de IA  
            default\_val \=... if is\_required else metadata.get("default", None)  
            dynamic\_fields\[field\_name\] \= (  
                python\_type,  
                Field(default=default\_val, description=field\_description)  
            )  
              
        \# Retornar el modelo compilado dinámicamente en tiempo de ejecución  
        return create\_model(schema\_name, \_\_base\_\_=BaseModel, \*\*dynamic\_fields)

Este motor permite estandarizar APIs propietarias.7 Cuando el sistema multiagente interactúa con un "ERP a medida", el middleware carga su esquema correspondiente, compila la estructura de validación en tiempo de ejecución, procesa el payload de entrada y valida los campos dinámicos antes de enviarlos al sistema de destino, garantizando la consistencia de los datos.7

## **Protocolo de Invocación de Herramientas y Orquestación Multi-Agente**

Para que el sistema de inteligencia artificial ejecute lecturas y modificaciones en los entornos ERP, no se le debe dar acceso directo a llamadas de red HTTP o scripts SQL arbitrarios.5 En su lugar, el backend de Aikrofy expone una colección dinámica de herramientas (*Tools*) integradas bajo el estándar de LangChain y LangGraph.3 Esto permite al agente comprender las capacidades disponibles, generar argumentos estructurados y realizar un seguimiento de los cambios aplicados en los sistemas transaccionales.3

### **Control Dinámico de Herramientas en el Bucle de Razonamiento (ReAct)**

El agente de programación opera bajo un bucle ReAct (Reasoning and Acting), evaluando de manera secuencial el estado de la conversación y seleccionando las herramientas necesarias para resolver el objetivo.3  
Para proteger los datos de negocio y optimizar el uso de tokens en el contexto, el sistema implementa una lógica de registro dinámico de herramientas (*dynamic tool selection*).3 Las herramientas transaccionales críticas (como el borrado de registros, la edición de asientos contables o la actualización de existencias de almacén) se retienen y no se exponen al agente de IA hasta que este complete los pasos previos requeridos o reciba la debida validación de permisos en el contexto de ejecución.3

\+------------------------------------------------------------+  
|                Bucle ReAct de Aikrofy                        |  
\+------------------------------------------------------------+  
| 1\. Razonar: "El usuario solicita registrar un nuevo        |  
|    cliente. Debo verificar si ya existe en la base         |  
|    de datos local antes de llamar al ERP".                 |  
|                                                            |  
| 2\. Actuar: Invocar la herramienta de búsqueda              |  
|    local \`erp\_query\_records\`.                              |  
|                                                            |  
| 3\. Observar: "La búsqueda local devuelve vacío".           |  
|                                                            |  
| 4\. Razonar: "Procede la creación. La herramienta de        |  
|    escritura \`erp\_create\_record\` se registra               |  
|    dinámicamente en el contexto de ejecución".             |  
\+------------------------------------------------------------+

### **Integración con MCP (Model Context Protocol)**

Para simplificar el despliegue de herramientas contables, Aikrofy soporta la conexión directa mediante servidores MCP (Model Context Protocol).27 El protocolo de comunicación MCP expone las funciones del ERP en esquemas JSON unificados que describen sus propiedades y reglas de uso, facilitando la interpretación por parte del agente de IA.34  
Cada esquema MCP define de manera explícita 34:

1. **Name (Nombre):** Identificador unificado en formato snake\_case (por ejemplo, create\_invoice\_record).34  
2. **Description (Descripción):** Descripción detallada en lenguaje natural indicando qué hace la herramienta, cuándo usarla y qué impacto tiene sobre el sistema contable.34  
3. **InputSchema (Esquema de entrada):** Estructura de argumentos JSON esperados por la herramienta, definiendo qué parámetros son obligatorios y cuáles son opcionales.34

### **Interfaz de Usuario para Streaming de Herramientas en Tiempo Real**

Durante la ejecución de tareas de backend complejas que requieren de la llamada de múltiples herramientas secuenciales, el frontend de Aikrofy utiliza el componente useStream para renderizar el progreso de las operaciones del agente en tiempo real.36 Esto evita que la interfaz del chat permanezca inactiva mientras se ejecutan llamadas de larga duración al ERP.36 El estado de cada herramienta de red pasa por tres fases que el sistema expone en su flujo de datos 36:

* **Pending (Pendiente):** La tarjeta de progreso en el cliente muestra el nombre de la herramienta y los argumentos enviados por la IA mientras se procesa la llamada de red en el backend.36  
* **Completed (Completado):** Al retornar con éxito, la tarjeta se actualiza dinámicamente en el cliente y muestra los resultados formateados en un componente visual estructurado.36  
* **Error (Error):** En caso de fallo de red, problemas de validación de negocio o expiración de tokens, la interfaz despliega de forma segura el mensaje de error capturado, ofreciendo opciones de mitigación o confirmaciones manuales al operador.36

## **Resiliencia de Middleware y Sincronización de Estado**

La integración directa de agentes con entornos de ERP requiere un middleware robusto y tolerante a fallos.2 El sistema transaccional del negocio no admite duplicidades en las transacciones de pago, cambios inconsistentes de inventario o inconsistencias contables derivadas de interrupciones de red.2

### **Algoritmo de Replenish del Token Bucket y Retroceso Exponencial con Jitter**

El middleware implementa un control de tasa de consumo por inquilino basado en el modelo de Token Bucket.2 Este algoritmo calcula de forma dinámica la disponibilidad de tokens antes de realizar llamadas a las APIs externas.27  
Si ![][image2] representa la cantidad de tokens disponibles en el balde en el tiempo ![][image3], ![][image4] la capacidad máxima autorizada de llamadas simultáneas, ![][image5] la tasa constante de recuperación de tokens por segundo y ![][image6] el lapso de tiempo transcurrido desde la última solicitud realizada, la ecuación de recarga se define mediante:  
![][image7]  
Si el balde se vacía, o si la API de destino del ERP responde con un código HTTP 429 Too Many Requests, se detiene la ejecución y se calcula un retroceso exponencial enriquecido con un componente de ruido uniforme (*jitter*) 2:  
![][image8]  
Donde:

* ![][image9] es el tiempo calculado de espera antes de reintentar la operación.37  
* ![][image10] es el factor base de penalización inicial (por ejemplo, 1.5 segundos).  
* ![][image11] es el número acumulado de intentos fallidos registrados para la misma transacción.  
* ![][image12] es la cota máxima permitida de retardo (por ejemplo, 60 segundos).37  
* ![][image13] representa una distribución uniforme que inyecta un retardo aleatorio entre 0 y ![][image14] segundos para mitigar colisiones por reintentos simultáneos (*thundering herd problem*).

### **Garantía de Idempotencia y Procesamiento Seguro de Datos**

Para evitar la duplicidad involuntaria de registros contables durante problemas de conectividad de red, se aplican los siguientes mecanismos de resiliencia 2:

* **Idempotency-Key (Claves de Idempotencia):** El middleware de Aikrofy genera un identificador UUID único para cada transacción de escritura y lo inyecta en la cabecera de las solicitudes HTTP destinadas a plataformas compatibles.20 En caso de experimentar una pérdida de conectividad durante la transmisión, los reintentos subsiguientes emplean exactamente la misma clave, garantizando que el ERP no cree registros duplicados si la petición original ya se había procesado en sus servidores.2  
* **Validaciones en Modo Dry-Run:** Antes de enviar un lote de actualización o creación a los endpoints del ERP, el middleware ejecuta una pre-validación del payload en local utilizando las reglas lógicas compiladas en los esquemas de Pydantic.2 Esto intercepta de forma temprana errores tipológicos y de formato, evitando sobrecargar de forma innecesaria la API de destino del ERP.2

## **Directiva Maestra de Codificación para Agentes de Programación de IA**

\================================================================================  
DIRECTIVA MAESTRA DE CODIFICACIÓN PARA AGENTES DE INTELIGENCIA ARTIFICIAL EN AIKROFY  
\================================================================================  
Actúa como un Arquitecto de Software Senior y Desarrollador Backend de Python.   
Tu misión consiste en implementar o ampliar el módulo de integraciones ERP del   
sistema Aikrofy (\`aikrofy\_erp\_integration\`), asegurando estricta compatibilidad con  
los modelos canónicos de datos de Aikrofy y las interfaces de los sistemas estándar   
(SAP Business One, Oracle NetSuite, Odoo ERP, y Dynamics 365 Business Central),   
así como el motor de adaptación para sistemas personalizados o a medida.

Sigue rigurosamente las siguientes directrices y requisitos de codificación:

\--------------------------------------------------------------------------------  
1\. ESTRUCTURA DE ARCHIVOS REQUERIDA  
\--------------------------------------------------------------------------------  
El módulo debe estructurarse estrictamente bajo el siguiente árbol de directorios:

aikrofy\_erp\_integration/  
├── \_\_init\_\_.py  
├── driver\_interface.py       \# Contrato abstracto base para todos los ERPs  
├── canonical\_models.py       \# Modelos Pydantic V2 de entidades canónicas  
├── mapping\_engine.py         \# Motor de compilación de esquemas dinámicos  
├── drivers/  
│   ├── \_\_init\_\_.py  
│   ├── sap\_b1.py             \# Conector SAP Business One OData v4  
│   ├── netsuite.py           \# Conector NetSuite REST/SuiteQL  
│   ├── odoo.py               \# Conector Odoo RPC & REST (JSON-2)  
│   └── dynamics\_bc.py        \# Conector Dynamics 365 Business Central  
└── agent\_tools.py            \# Orquestador de herramientas de LangChain y MCP

\--------------------------------------------------------------------------------  
2\. ESPECIFICACIÓN DE CODIFICACIÓN DE ARCHIVOS LÓGICOS  
\--------------------------------------------------------------------------------

A continuación, se presentan las plantillas y el código lógico funcional que debes  
implementar para cada componente del sistema. Queda prohibida la generación de   
placeholders o el uso de comentarios del tipo "\# implementar después". Todo el   
código debe estar completo, documentado y tipado de forma estricta.

\#\#\# ARCHIVO 2.1: \`driver\_interface.py\`  
Define el contrato abstracto base que deben implementar todos los conectores ERP.  
Este archivo garantiza que el orquestador de herramientas pueda interactuar con  
cualquier sistema de forma homogénea.

\`\`\`python  
from abc import ABC, abstractmethod  
from typing import Any, Dict, List, Optional

class BaseERPDriver(ABC):  
    """Contrato base abstracto para la implementación de drivers de ERP."""

    @abstractmethod  
    def authenticate(self) \-\> bool:  
        """Inicializa y valida el contexto de autenticación con el ERP del cliente.  
        Debe almacenar y renovar las credenciales en caché de forma transparente.  
        """  
        pass

    @abstractmethod  
    def create\_customer(self, customer\_data: Dict\[str, Any\]) \-\> Dict\[str, Any\]:  
        """Crea un registro de cliente en el ERP de destino.  
        Recibe un diccionario con formato canónico y retorna la respuesta normalizada.  
        """  
        pass

    @abstractmethod  
    def get\_invoice(self, invoice\_id: str) \-\> Dict\[str, Any\]:  
        """Recupera la información de una factura específica utilizando su ID.  
        Retorna los campos mapeados bajo el esquema canónico de datos.  
        """  
        pass

    @abstractmethod  
    def update\_invoice(self, invoice\_id: str, patch\_data: Dict\[str, Any\]) \-\> bool:  
        """Ejecuta una actualización parcial (PATCH) sobre una factura existente."""  
        pass

    @abstractmethod  
    def query\_records(self, entity\_name: str, filters: Dict\[str, Any\], limit: int \= 50\) \-\> List\]:  
        """Realiza consultas sobre una entidad, traduciendo filtros locales a   
        la sintaxis del ERP (por ejemplo, OData filter, SuiteQL o Domains de Odoo).  
        """  
        pass

### **ARCHIVO 2.2: canonical\_models.py**

Define los esquemas de datos estándar que consume la capa cognitiva de los agentes.  
Usa alias dinámicos con Pydantic V2 para procesar de forma automática nombres  
de propiedades divergentes de diferentes sistemas de origen.

Python  
from typing import List, Optional, Dict, Any  
from pydantic import BaseModel, Field, AliasChoices

class CanonicalInvoiceLine(BaseModel):  
    """Línea de detalle individual para transacciones de facturación."""  
    item\_code: str \= Field(  
        validation\_alias=AliasChoices("item\_code", "ItemCode", "item", "product\_id"),  
        description="Código único de identificación del artículo o producto"  
    )  
    quantity: float \= Field(  
        validation\_alias=AliasChoices("quantity", "Quantity", "quantity", "qty"),  
        description="Cantidad física de unidades de la transacción"  
    )  
    unit\_price: float \= Field(  
        validation\_alias=AliasChoices("unit\_price", "UnitPrice", "rate", "price\_unit"),  
        description="Precio unitario neto de la línea"  
    )

class CanonicalInvoice(BaseModel):  
    """Modelo canónico normalizado para documentos de facturación emitidos."""  
    invoice\_id: str \= Field(  
        validation\_alias=AliasChoices("invoice\_id", "DocEntry", "id", "id\_invoice"),  
        description="Clave o identificador primario del documento"  
    )  
    customer\_code: str \= Field(  
        validation\_alias=AliasChoices("customer\_code", "CardCode", "entity", "partner\_id"),  
        description="Código de asociación con el cliente"  
    )  
    document\_date: str \= Field(  
        validation\_alias=AliasChoices("document\_date", "DocDate", "trandate", "invoice\_date"),  
        description="Fecha de emisión del documento transaccional"  
    )  
    total\_amount: float \= Field(  
        validation\_alias=AliasChoices("total\_amount", "DocTotal", "total", "amount\_total"),  
        description="Importe total bruto facturado"  
    )  
    lines: List\[CanonicalInvoiceLine\] \= Field(  
        default=,  
        validation\_alias=AliasChoices("lines", "DocumentLines", "item", "invoice\_line\_ids"),  
        description="Colección de líneas de detalle asociadas a la transacción"  
    )  
    custom\_fields: Dict\[str, Any\] \= Field(  
        default={},  
        description="Almacén de campos de usuario o datos suplementarios de paso directo"  
    )

### **ARCHIVO 2.3: drivers/sap\_b1.py**

Driver de integración especializado en interactuar con la Service Layer de SAP B1.  
Implementa el protocolo OData v4 y la persistencia automatizada de cookies de sesión.

Python  
import requests  
import time  
from typing import Any, Dict, List  
from driver\_interface import BaseERPDriver

class SAPBusinessOneDriver(BaseERPDriver):  
    """Driver transaccional para la Service Layer de SAP Business One (OData v4)."""

    def \_\_init\_\_(self, config: Dict\[str, Any\]):  
        self.base\_url \= f"https://{config\['host'\]}:50000/b1s/v2"  
        self.company\_db \= config\["company\_db"\]  
        self.username \= config\["username"\]  
        self.password \= config\["password"\]  
        self.session \= requests.Session()  
        self.session.verify \= config.get("verify\_ssl", False)  
        self.session\_expiry: float \= 0.0  
        self.session\_timeout \= 1800.0  \# Vigencia estándar de 30 minutos

    def authenticate(self) \-\> bool:  
        """Establece e inicia la sesión contra el endpoint de Login corporativo."""  
        current\_time \= time.time()  
        if current\_time \< self.session\_expiry:  
            return True

        url \= f"{self.base\_url}/Login"  
        payload \= {  
            "CompanyDB": self.company\_db,  
            "UserName": self.username,  
            "Password": self.password  
        }

        try:  
            \# Los inicios de sesión asumen una latencia base de \~5 segundos  
            response \= self.session.post(url, json=payload, timeout=15.0)  
            if response.status\_code \== 200:  
                self.session\_expiry \= time.time() \+ self.session\_timeout  
                \# Requests gestionará de forma transparente las cookies B1SESSION y ROUTEID  
                return True  
            raise ConnectionError(f"Error de login en SAP B1: {response.text}")  
        except Exception as e:  
            raise ConnectionError(f"Fallo de conexión al servidor SAP Business One: {str(e)}")

    def create\_customer(self, customer\_data: Dict\[str, Any\]) \-\> Dict\[str, Any\]:  
        self.authenticate()  
        url \= f"{self.base\_url}/BusinessPartners"  
        payload \= {  
            "CardCode": customer\_data.get("customer\_code"),  
            "CardName": customer\_data.get("name"),  
            "CardType": "cCustomer"  
        }  
          
        response \= self.session.post(url, json=payload, timeout=10.0)  
        if response.status\_code \== 201:  
            return response.json()  
        raise ValueError(f"Fallo en creación de cliente SAP: {response.text}")

    def get\_invoice(self, invoice\_id: str) \-\> Dict\[str, Any\]:  
        self.authenticate()  
        \# Se solicita la proyección explícita de campos mediante select de OData  
        url \= f"{self.base\_url}/Invoices({invoice\_id})?$select=DocEntry,CardCode,DocDate,DocTotal,DocumentLines"  
        response \= self.session.get(url, timeout=10.0)  
        if response.status\_code \== 200:  
            return response.json()  
        raise KeyError(f"Factura {invoice\_id} no identificada en SAP B1: {response.text}")

    def update\_invoice(self, invoice\_id: str, patch\_data: Dict\[str, Any\]) \-\> bool:  
        self.authenticate()  
        url \= f"{self.base\_url}/Invoices({invoice\_id})"  
        response \= self.session.patch(url, json=patch\_data, timeout=10.0)  
        return response.status\_code \== 204

    def query\_records(self, entity\_name: str, filters: Dict\[str, Any\], limit: int \= 50) \-\> List\]:  
        self.authenticate()  
        \# Construcción básica del lenguaje de consultas OData a partir de filtros  
        filter\_statements \=  
        for key, value in filters.items():  
            filter\_statements.append(f"{key} eq '{value}'")  
          
        filter\_query \= " and ".join(filter\_statements)  
        url \= f"{self.base\_url}/{entity\_name}"  
        if filter\_query:  
            url \+= f"?$filter={filter\_query}&$top={limit}"  
        else:  
            url \+= f"?$top={limit}"  
              
        response \= self.session.get(url, timeout=15.0)  
        if response.status\_code \== 200:  
            return response.json().get("value",)  
        raise ValueError(f"Error al ejecutar consulta OData en SAP: {response.text}")

### **ARCHIVO 2.4: drivers/odoo.py**

Driver para interactuar con el ORM de Odoo mediante XML-RPC. Controla la autenticación  
segura por API Keys y la inyección síncrona de consultas mediante execute\_kw.

Python  
import xmlrpc.client  
from typing import Any, Dict, List  
from driver\_interface import BaseERPDriver

class OdooRPCDriver(BaseERPDriver):  
    """Driver para interactuar con Odoo ERP mediante llamadas remotas XML-RPC."""

    def \_\_init\_\_(self, config: Dict\[str, Any\]):  
        self.url \= config\["url"\]  
        self.db \= config\["db"\]  
        self.username \= config\["username"\]  
        self.api\_key \= config\["api\_key"\]  
        self.uid: Optional\[int\] \= None  
        self.models: Optional \= None

    def authenticate(self) \-\> bool:  
        """Autentica contra el servicio common para obtener el UID de sesión."""  
        if self.uid is not None:  
            return True

        try:  
            common \= xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")  
            self.uid \= common.authenticate(self.db, self.username, self.api\_key, {})  
            if self.uid:  
                self.models \= xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")  
                return True  
            raise ConnectionError("Credenciales denegadas en servidor de Odoo.")  
        except Exception as e:  
            raise ConnectionError(f"Error de comunicación en autenticación Odoo: {str(e)}")

    def create\_customer(self, customer\_data: Dict\[str, Any\]) \-\> Dict\[str, Any\]:  
        self.authenticate()  
        payload \= {  
            "name": customer\_data.get("name"),  
            "email": customer\_data.get("email"),  
            "is\_company": True  
        }  
          
        customer\_id \= self.models.execute\_kw(  
            self.db, self.uid, self.api\_key,  
            "res.partner", "create",  
            \[payload\]  
        )  
        return {"id": customer\_id, "name": customer\_data.get("name")}

    def get\_invoice(self, invoice\_id: str) \-\> Dict\[str, Any\]:  
        self.authenticate()  
        records \= self.models.execute\_kw(  
            self.db, self.uid, self.api\_key,  
            "account.move", "search\_read",  
            \[\[\["id", "=", int(invoice\_id)\]\]\],  
            {"fields": \["name", "partner\_id", "invoice\_date", "amount\_total", "invoice\_line\_ids"\]}  
        )  
        if records:  
            return records  
        raise KeyError(f"Documento contable {invoice\_id} no encontrado en Odoo.")

    def update\_invoice(self, invoice\_id: str, patch\_data: Dict\[str, Any\]) \-\> bool:  
        self.authenticate()  
        result \= self.models.execute\_kw(  
            self.db, self.uid, self.api\_key,  
            "account.move", "write",  
            \[\[int(invoice\_id)\], patch\_data\]  
        )  
        return bool(result)

    def query\_records(self, entity\_name: str, filters: Dict\[str, Any\], limit: int \= 50) \-\> List\]:  
        self.authenticate()  
        domain\_filters \=  
        for key, value in filters.items():  
            domain\_filters.append(\[key, "=", value\])  
              
        records \= self.models.execute\_kw(  
            self.db, self.uid, self.api\_key,  
            entity\_name, "search\_read",  
            \[domain\_filters\],  
            {"limit": limit}  
        )  
        return records

### **ARCHIVO 2.5: agent\_tools.py**

Módulo Middleware que expone y registra de forma dinámica las herramientas  
para LangChain y el entorno multiagente basado en LangGraph. Controla la captura y  
normalización de excepciones para evitar la interrupción del bucle cognitivo.

Python  
import json  
from typing import Any, Dict, List, Callable  
from langchain.tools import BaseTool, tool  
from langchain.messages import ToolMessage  
from langchain.agents.middleware import wrap\_tool\_call  
from drivers.sap\_b1 import SAPBusinessOneDriver  
from drivers.odoo import OdooRPCDriver

class ERPIntegrationToolsOrchestrator:  
    """Administrador centralizado de herramientas dinámicas de ERP para agentes de IA."""

    def \_\_init\_\_(self, tenant\_config: Dict\[str, Any\]):  
        self.config \= tenant\_config  
        self.driver \= self.\_resolve\_driver()

    def \_resolve\_driver(self) \-\> Any:  
        erp\_type \= self.config.get("erp\_type")  
        if erp\_type \== "sap\_b1":  
            return SAPBusinessOneDriver(self.config)  
        elif erp\_type \== "odoo":  
            return OdooRPCDriver(self.config)  
        else:  
            raise NotImplementedError(f"Driver ERP no soportado o clasificado: {erp\_type}")

    def generate\_agent\_tools(self) \-\> List:  
        """Expone dinámicamente el conjunto de herramientas autorizadas para el agente."""  
          
        @tool  
        def erp\_create\_customer(payload\_json: str) \-\> str:  
            """Crea un registro de cliente en el sistema ERP del usuario.  
            Recibe un payload JSON con formato canónico conteniendo 'name' y 'customer\_code'.  
            """  
            try:  
                data \= json.loads(payload\_json)  
                result \= self.driver.create\_customer(data)  
                return json.dumps({"status": "success", "result": result})  
            except Exception as e:  
                return json.dumps({"status": "error", "message": str(e)})

        @tool  
        def erp\_get\_invoice(invoice\_id: str) \-\> str:  
            """Recupera la información de una factura mediante su identificador único."""  
            try:  
                invoice \= self.driver.get\_invoice(invoice\_id)  
                return json.dumps({"status": "success", "invoice": invoice})  
            except Exception as e:  
                return json.dumps({"status": "error", "message": str(e)})

        return \[erp\_create\_customer, erp\_get\_invoice\]

@wrap\_tool\_call  
def handle\_agent\_tool\_exceptions(request: Any, handler: Callable) \-\> Any:  
    """Middleware de intercepción de errores en la ejecución de herramientas contables.  
    Previene la propagación de excepciones que romperían el contexto de LangGraph,  
    retornando un ToolMessage con detalles informativos para la IA.  
    """  
    try:  
        return handler(request)  
    except Exception as e:  
        \# Se captura el error y se entrega estructurado para la asimilación del agente  
        return ToolMessage(  
            content=f"Error en la llamada de red al ERP. Detalles técnicos para reintento: {str(e)}",  
            tool\_call\_id=request.tool\_call\["id"\]  
        )

3. DIRECTIVAS FINALES DE CALIDAD DE EJECUCIÓN  
* Tipado Estricto de Datos: No se permite declarar tipos genéricos o imprecisos  
  en el código de producción. Utiliza anotaciones explícitas de la biblioteca  
  typing.  
* Políticas de Reintento de Red: Toda solicitud HTTP o llamada RPC debe envolverse  
  en bloques condicionales con algoritmos de retroceso exponencial con jitter  
  para mitigar fallas transitorias de infraestructura y evitar la saturación  
  de los rate-limits del ERP.  
* Garantía de Idempotencia: Emplea cabeceras personalizadas de Idempotency-Key  
  en operaciones que alteren el estado transaccional contable (tales como la  
  creación de facturas o pagos).  
* Documentación Narrativa Completa: Conserva de forma estricta los docstrings y  
  comentarios de explicación de algoritmos dentro de las clases de ejecución.  
  \================================================================================

#### **Fuentes citadas**

1. Top Unified Accounting API Platforms of 2026 | Satva Solutions, acceso: mayo 20, 2026, [https://satvasolutions.com/blog/top-unified-accounting-api-platforms](https://satvasolutions.com/blog/top-unified-accounting-api-platforms)  
2. Accounting Software Integration: Architecture, Trade-offs, and Costs for SaaS Teams, acceso: mayo 20, 2026, [https://www.apideck.com/blog/accounting-software-integration](https://www.apideck.com/blog/accounting-software-integration)  
3. Agents \- Docs by LangChain, acceso: mayo 20, 2026, [https://docs.langchain.com/oss/python/langchain/agents](https://docs.langchain.com/oss/python/langchain/agents)  
4. The Complete Guide to Accounting API Integrations for Fintech \- Apideck, acceso: mayo 20, 2026, [https://www.apideck.com/blog/the-complete-guide-to-accounting-api-integrations-for-fintech](https://www.apideck.com/blog/the-complete-guide-to-accounting-api-integrations-for-fintech)  
5. Building AI Agents with LangChain & Tool Calling | by Sagar Sonwane \- Medium, acceso: mayo 20, 2026, [https://sagarsonwane230797.medium.com/building-ai-agents-with-langchain-tool-calling-4486a9ddac9f](https://sagarsonwane230797.medium.com/building-ai-agents-with-langchain-tool-calling-4486a9ddac9f)  
6. The Merge.dev Migration Playbook: Moving to a Flexible Unified API Without Downtime, acceso: mayo 20, 2026, [https://truto.one/blog/create-a-migration-playbook-moving-off-mergedev-without-downtime/](https://truto.one/blog/create-a-migration-playbook-moving-off-mergedev-without-downtime/)  
7. hinthornw/dydantic: Dynamically create Pydantic models from JSON schemas \- GitHub, acceso: mayo 20, 2026, [https://github.com/hinthornw/dydantic](https://github.com/hinthornw/dydantic)  
8. JSON Schema | Pydantic Docs, acceso: mayo 20, 2026, [https://pydantic.dev/docs/validation/latest/concepts/json\_schema/](https://pydantic.dev/docs/validation/latest/concepts/json_schema/)  
9. How we built Account Categorization \- Codat, acceso: mayo 20, 2026, [https://codat.io/resources/how-we-built-categories/](https://codat.io/resources/how-we-built-categories/)  
10. Merge \- Common Models, acceso: mayo 20, 2026, [https://www.merge.dev/features/common-models](https://www.merge.dev/features/common-models)  
11. SAP Business One API Integration Guide: Authentication, Endpoints ..., acceso: mayo 20, 2026, [https://www.apideck.com/blog/sap-business-one-api-integration-guide](https://www.apideck.com/blog/sap-business-one-api-integration-guide)  
12. The Final Boss of ERPs: Architecting a Reliable NetSuite API Integration | Truto Blog, acceso: mayo 20, 2026, [https://truto.one/blog/the-final-boss-of-erps-architecting-a-reliable-netsuite-api-integration/](https://truto.one/blog/the-final-boss-of-erps-architecting-a-reliable-netsuite-api-integration/)  
13. NetSuite API Guide: REST, SOAP & SuiteScript for Developers ..., acceso: mayo 20, 2026, [https://www.brokenrubik.com/blog/netsuite-api-guide-for-developers](https://www.brokenrubik.com/blog/netsuite-api-guide-for-developers)  
14. How to Integrate with the Odoo API \- Apideck, acceso: mayo 20, 2026, [https://www.apideck.com/blog/how-to-integrate-with-the-odoo-api](https://www.apideck.com/blog/how-to-integrate-with-the-odoo-api)  
15. Endpoints for the APIs for Microsoft Dynamics 365 Business Central, acceso: mayo 20, 2026, [https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/endpoints-apis-for-dynamics](https://learn.microsoft.com/en-us/dynamics365/business-central/dev-itpro/api-reference/v2.0/endpoints-apis-for-dynamics)  
16. Odoo API Guide \- XML-RPC, JSON-RPC & REST \- OEC.sh, acceso: mayo 20, 2026, [https://oec.sh/blog/odoo-api-integration](https://oec.sh/blog/odoo-api-integration)  
17. Integrating Python with Microsoft Dynamics 365 Business Central | Rupesh Bhandari, acceso: mayo 20, 2026, [https://www.rupeshbhandari.com.np/posts/Integrating-Python-with-Microsoft-Dynamics-365-Business-Central/](https://www.rupeshbhandari.com.np/posts/Integrating-Python-with-Microsoft-Dynamics-365-Business-Central/)  
18. The Users Guide to NetSuite Integration 2026: API, Tools, \+ More \- eMerge Technologies, acceso: mayo 20, 2026, [https://emergetech.com/user-guides/netsuite/integration/](https://emergetech.com/user-guides/netsuite/integration/)  
19. OData Query Builder for BC & F\&O — Free Tool | Dynamics Mobile, acceso: mayo 20, 2026, [https://www.dynamicsmobile.com/tools/odata-query-builder](https://www.dynamicsmobile.com/tools/odata-query-builder)  
20. Merge vs. Codat, acceso: mayo 20, 2026, [https://www.merge.dev/vs/codat](https://www.merge.dev/vs/codat)  
21. Custom data types | Codat Docs, acceso: mayo 20, 2026, [https://docs.codat.io/using-the-api/custom-data](https://docs.codat.io/using-the-api/custom-data)  
22. 3 newly-launched Field Mapping features that can help you sync custom data easily and effectively \- Merge.dev, acceso: mayo 20, 2026, [https://www.merge.dev/blog/field-mapping-features](https://www.merge.dev/blog/field-mapping-features)  
23. NetSuite API Integration Guide (In-Depth) : REST, SuiteQL & SuiteScript (2026), acceso: mayo 20, 2026, [https://www.getknit.dev/blog/netsuite-api-integration-guide-in-depth](https://www.getknit.dev/blog/netsuite-api-integration-guide-in-depth)  
24. Using the Oracle NetSuite REST Adapter with Oracle Integration 3, acceso: mayo 20, 2026, [https://docs.oracle.com/en/cloud/paas/application-integration/netsuite-rst-adapter/using-oracle-netsuite-rest-adapter-oracle-integration-3.pdf](https://docs.oracle.com/en/cloud/paas/application-integration/netsuite-rst-adapter/using-oracle-netsuite-rest-adapter-oracle-integration-3.pdf)  
25. Understanding Authorization When Building a Microsoft Business Central API Integration, acceso: mayo 20, 2026, [https://www.apideck.com/blog/understanding-authorization-in-microsoft-business-central-api](https://www.apideck.com/blog/understanding-authorization-in-microsoft-business-central-api)  
26. Odoo MCP: AI for Odoo partners and multi-database ERPs \- Peliqan, acceso: mayo 20, 2026, [https://peliqan.io/blog/odoo-claude-mcp/](https://peliqan.io/blog/odoo-claude-mcp/)  
27. Business Central MCP: AI agents for Dynamics 365 BC \- Peliqan, acceso: mayo 20, 2026, [https://peliqan.io/blog/business-central-mcp/](https://peliqan.io/blog/business-central-mcp/)  
28. Microsoft Dynamic 365 business Central API data fetch using Fabric note book, acceso: mayo 20, 2026, [https://community.fabric.microsoft.com/t5/Data-Engineering/Microsoft-Dynamic-365-business-Central-API-data-fetch-using/m-p/4770029](https://community.fabric.microsoft.com/t5/Data-Engineering/Microsoft-Dynamic-365-business-Central-API-data-fetch-using/m-p/4770029)  
29. Creating a dynamic Pydantic model from a JSON schema with field validators, acceso: mayo 20, 2026, [https://stackoverflow.com/questions/77967126/creating-a-dynamic-pydantic-model-from-a-json-schema-with-field-validators](https://stackoverflow.com/questions/77967126/creating-a-dynamic-pydantic-model-from-a-json-schema-with-field-validators)  
30. Creating a dynamic Pydantic model from a JSON schema with field validators \#8779, acceso: mayo 20, 2026, [https://github.com/pydantic/pydantic/discussions/8779](https://github.com/pydantic/pydantic/discussions/8779)  
31. Tool Calling with LangChain, acceso: mayo 20, 2026, [https://www.langchain.com/blog/tool-calling-with-langchain](https://www.langchain.com/blog/tool-calling-with-langchain)  
32. Dynamic tool calling in LangGraph agents \- LangChain \- Changelog, acceso: mayo 20, 2026, [https://changelog.langchain.com/announcements/dynamic-tool-calling-in-langgraph-agents](https://changelog.langchain.com/announcements/dynamic-tool-calling-in-langgraph-agents)  
33. One abstraction, 146 SaaS connectors. Agent skills for Apideck's Unified API — integrate Salesforce, QuickBooks, BambooHR, Jira, Shopify and 140+ more by changing one string. \- GitHub, acceso: mayo 20, 2026, [https://github.com/apideck-libraries/api-skills](https://github.com/apideck-libraries/api-skills)  
34. MCP tool schema: what it is, how it works, and examples \- Merge.dev, acceso: mayo 20, 2026, [https://www.merge.dev/blog/mcp-tool-schema](https://www.merge.dev/blog/mcp-tool-schema)  
35. Tools \- Docs by LangChain, acceso: mayo 20, 2026, [https://docs.langchain.com/oss/python/langchain/tools](https://docs.langchain.com/oss/python/langchain/tools)  
36. Tool calling \- Docs by LangChain, acceso: mayo 20, 2026, [https://docs.langchain.com/oss/python/langchain/frontend/tool-calling](https://docs.langchain.com/oss/python/langchain/frontend/tool-calling)  
37. QuickBooks Python API Docs | dltHub, acceso: mayo 20, 2026, [https://dlthub.com/context/source/quickbooks-financial](https://dlthub.com/context/source/quickbooks-financial)  
38. Writes \- Merge Docs, acceso: mayo 20, 2026, [https://docs.merge.dev/merge-unified/writing-data/writes/introduction](https://docs.merge.dev/merge-unified/writing-data/writes/introduction)  
39. Create, update, and delete data | Codat Docs, acceso: mayo 20, 2026, [https://docs.codat.io/using-the-api/push](https://docs.codat.io/using-the-api/push)  
40. QuickBooks Python SDK \- Build QuickBooks Integrations \- Apideck, acceso: mayo 20, 2026, [https://www.apideck.com/integrations/quickbooks/sdk/python](https://www.apideck.com/integrations/quickbooks/sdk/python)

[image1]: <data:image/png;base64,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QcDSKlnIIwHZsirUZi1F5CiBaIu9NLfrT+wQ7H1hSeJogMiz3x9DloElmg9FLp+RbVyVlZXVTMl2L3Jh6ecmXFBjnCVxtmXglDBuHxHLPzrbBJ5xMFb/b6+OBZABy+BvHI8vGbnUiZz6bS5zeXjkEv52GX8R+QKBw/Ke2J3s0l3j6PifCGPM7tlXRi77MtmcE/kjDJZIuFbms0q2e40LSz835YIa4+wDY88fTgl789r9rZtCYLYX9miRIWSvJXvryPyyT/pInVCcX/bpTW0lEZGjiDvF1k3cIiJy4YAfSpAtFRERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERGRLzz/DxYPgcq2Tvz/AAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAaCAYAAACzdqxAAAABVklEQVR4Xu2UvStGcRTHj5eBZPBSpEwmGUSRzfMnUPIysClkslgYDSabyCQDxahMFqONQVLeFpRE3ibiczq/eq7j6rlPV0o9n/oMv/P9ndN9fr/7XJECf00nnuI13uAVXuAZXuIBTmJF2J83a/iBra7eF+q7rp6YE7EnjuNQbHizD3JRL9a44QMoxQd8x1qX5aRfbPCYD2BGLJvyQRIWxZq7sAprsB1X8AhHslvzQ5vvxS5wNbiF59iDxdmtyamTn8+3TSxb9wGU+IJnQKx53AcB/TVv2BipjeJ8ZB3LstjgFh8E9BXUPDp4Bwcj61j0/b3FIh/AsNjQ7bDuxgV8EruPTKh/o0mscdPVy3ECX3EPq0NdzzWDx1gmMZeqr5J+C57FBr+IfRe0pt6J/YV1uG+exiVX+xX0fId8MS16D4/YgL3Y8TVOxz7O4awP0qJPXemLBf45n97zRx6wWS/LAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAcCAYAAACtQ6WLAAAAkklEQVR4XmNgGOTABYgXoQvCwFEgPo4uCAM4JXmA+DcQdyAL8gGxChDHAPF/IE4HYlUgZgVJZgHxTiB+xgDRCWKDsDRIEgZA9h1DFoABbiD+BcTt6BIg4MYAsc8dXQIE2hgg9oFcjAFAdp1E4s8DYhYY5wUQz4Gy04C4BCYBAhVA/B6IZwJxK7IEDIgy4LBzRAMAaC8Zom6t39QAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAaCAYAAAC+aNwHAAABA0lEQVR4Xu2SIUtDURiGP8VZFIuiE8OYi2IxOGRtdXmGpVVhYBlikRXBLDaDQZtxRfwBsjFQu0tmg+AEm/ocv3vH5d2FLcseeODe973nOwfuMfv3zOM2VnA9kS9hNvE+wipe4Cf28BLbeI5r2MXd4dfCIX7gDa5Id4SDyDnp/mjgDx5oERGO/Y33WgT2zcsrLYRnPNZwAd/Md9+QTgm7FzVsmi9+1CKFTZzRsGM+oKXFpLybD9jRYhIy5ou/tEjhFHMaBl7NhyxqkaCADxrGnJkPCFc2jVm8xZIWMcvYxxcsSxcuzx3WJR8hb/6Pw0me8ASvzRfvJb4byxZWsRY9T5kyll/XiyxRZFBdwwAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAAkUlEQVR4XmNgGAXUBCxA7ATEglC+ABB7AzE3XAUULAfieUD8CYhLgXgFELcC8U0gZoQpsgPiJiDWBuL/QLwPiDmA+DQQfwNiTpjCFCDWBOIEqEIzqHg4ELtC2SgAZPU7IGZCl0AHd4F4PbogOpBmgFibjy6BDiIZIAr10SXQQTsQ32BACgpcgBeIudAFRwH1AQBXXxRK+83PqwAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAaCAYAAABCfffNAAABbElEQVR4Xu2UvStFcRjHv8hbJBkog0EpsxRlM2AzKcXEIKVEMdgsXiZFBpkMLFbleskiUiZKXjIYDPgHhML38fzuPec8556TdGznU5+6v+f7+93nnvOce4CUBBmgbbaYJI30g17RQpMlxjp9pV+0z2RRTNApW4yigV7TIWiTC1oQ2BGmgr7ReRtEsUqHaRG9hzbqDewI0w3d12ODfNTTG1rs1tJMDp/ndgSpo010hX7SFug8Y1miI761NHtA9K9co/vQ+T3TPboZ2GGopbe0xNRHoU1OTD2LzOOdztkgHwt0zBZJKX2ENuo0mdAFzWQusdTQO1pmA8c49IuObAC9AvlPVdrAMksnbdFHOfSeS6MOk53SM1MLUQW9Crm3cUxDm+z6atl5LLp1NV32Yo8Z+kQP6QH0aZGnJGM8hjYRW39OAs1uPejWG7Tdfc4hQ32Bd/i3bsth6Jtgh17SLdrv6v+CvIrkDZGSkvIHvgEWCVFm9U4v7gAAAABJRU5ErkJggg==>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAABOUlEQVR4Xu2SPSiFURjHHx/FHe5AKYlB7qCUj0XJYjFZzBZsSmKR8jEpZWI3KFlMNopyy2ChzLeuEkqSFMnI7/ScXqfHfa+3VwZ1f/XrPef/nHM657xHpMJfMYDnCTzDPPbotPJs4SWOYBs24xF+4Cg2+XzcZzmdFk8tFrDR5Pf4KloPucMak31jGNdN1im6o0OTV+OFyUoygR0mmxJddMHkWVwyWWL2RBftt4Xf8IAvkuDuktIlussDWyjBkOhTc6+nLNOii87bQgy7OGPDkCp8lJ+PPohrOIlPovNicT/G7fLYFgJWcNW3t3E/qEW04BVei+7w3XuLRWyPRor04RtmfH8H577K6VjGk6B/g71BPxWzuOHb3fgsepKxaEQKWkXv0b2QRTzFTawPB6WlwX/dX68LCxX+EZ9jkDv9aI7ypgAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAaCAYAAADFTB7LAAACBklEQVR4Xu2WTUhUYRSGT2aKaQsFSYQCy0UQ5aYCW7nRpCDdWYvINmIImWIopQtdaenCRbmIxE1B4Q9uLLRIJdwkSNDGvwgVRNzVwmW9L+cMXE8xDHjnKjgPPMw353Bnzpz7nfuNSIoUB4NS+DUB5+BnWKKXRcdLuABvwFOwAE7CP7Aa5lv8rsWK9bJoSIeLMM/FN+Fv0XyQDXjUxZJKOexxsXOinXrv4mlw3sWSTi0862L1ogW2uvgJ+MTF9oW3ogVe8YmDwhb8JRHvtUQ5L9q9CZ8Aj+EavO4TUdIgWuAjnzBmYZUPRsmwaIGXfcL4JPtY4BG4LfH330fYDOtgLywK5Fg4J7/L1jHOwAewHQ6KPg3IJfgM3ocnLRYXTi27N+UTAVggT54c0RNlWXTfkm/wpuiP4/qqxd/B07bmtTwUKkWfs8dgGRyx/D8UwlX4U7RzO+Y6XJHdHSIs8Hbg/SvYaWs+yPl5PB55dLJrpA0uwW540WJv4Dhsgi2i351huT3hC+yHo7Zmp4bgBVs3WjwL3hEt6ofo7fwuWhw7GDMUWOC9wPsPsEJ0qHh2cx8TbpOHot0J3r4+eA12wNeBOLseSpFjol/KLvL2ciBINpyBT0UH6AX8Am/BadG9x2EYEN2jLIax56KDVSMhkyn//8W5gXXsn9Bxe+VgeTgwoey9FCkOJX8BlT9jKJfPWXYAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAbCAYAAABIpm7EAAAAzElEQVR4Xu3QLw+BURTH8eNvMDY2wcY0ZDTFBM10EwTBiDRB9RZskqAIJgiaF6HYBNMFb8D4Pu7F2dMkgt/2Cfd37nn27Ir880vxoYaUOhdQQeB5SWeJBS6oYoUhJjgj9r4qUsIIWdxwRNzOwrbr2vMjbWTQtMOymjm903VU98pUzC95VdcTs5BT3SsfLxywdnVb7FzdI0kxXxqoLoGrmNfyY6Zm0hCzkFdd3XZFtNBXMxljD4/qojhhgzmCaiYRhHRh4zxA2l3+8/3cAZ3kIwRlie28AAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAaCAYAAADFTB7LAAAB1klEQVR4Xu2WSyhEYRTHj1cekRJ5JYmFUixExJaNSEpSihJ5buSxUOy8FtizsLARskKxUArlEWUhRY0ooRDFRvifzpd7+8xk6jbXXdxf/Zpvzrl3+uZ8TyIXF2dQDA/8cBduwTx5zT5m4DGsgGkwCW7AL1gNE1S8UcWy5DV7CIXnME6L38JXkryZGxiixQJKGRzXYtkklVrX4sHwUIsFnCaYqcXaSDo4oMVj4KAW+xcWSDpYqCecwh18IZvnmr/kkFRvTU84hU6SDvbpCaewRNLBAj3hBILgA/mef81wHpbDHjgNS2Eu7CVZ4ZHq2Vg4TLIT8Ge8ilfCCSVPp344QnII/AmvWq7epp5QRMFtuAOjYT58gt0qPwfbVbsGHql2HRl7Km/8JSRFSIezsJ7kD3klBV5CD8lL78preAEzfp4UlkmqxaTCTxiuvo/BSdVmIkimyhB8NMWZLngCW7W4ZRZhh2onww9TjodqSrV56PkI5UryZYQrbYbP+3v6fRhYhivoq4OjZHRwlYxK85A+wwaYCMNILig8Oh5YpJ6zDB+BV3AfVsEV+EYy9/jWc6asJZl3fEVrIdmyTkk6xd89ZMzPPZLf5AVnO7wg+PxmvO0KLi4uVvkGBeNiBESb5f0AAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAaCAYAAAAHfFpPAAADhUlEQVR4Xu2XWahOaxjHH7NjHguRWYYbyjEnUmYZLgxlyJgLSeIcRZIbQ7jABS5kjHJBCJGSpIRCHOccsTeZhxTKPPz/PWtt6/t/a61t72/b++b71b/293/evd53Pe/7Pu+7zPLkKUtaqFEBNIRqqVkeDIEOq1kBdIUuQLU1kMYoaBt0E5omsSiToJNqgnbQE6iTBkBvaDm0AuohsdJyCroPFUIFwd+nI/GN0FGocsRLZD10ENoJfYfWZYaLaAC9h7ZrAFwx71RZAt2CJkBToP+hBRktcuOQ+ZjHil8PegbNFT+VyeYPG66BgPnm8UHiDzbvrL74Xczb94x4Q6GPFr9SSgMT+haqqgEwC3oAVddAEvugl1BNDYBK0D/QQ8teVtz3W8Ujm6A34nEw38y3Q640N08wt0McVaBP0HgNxNHIfHknLf+Z5p3pMmcyOKOLxCfXzPemwqScVbMUcEtxTMs0EIErJG5yslgKfYXaagA0hV5Z/PJvGfijxSePoP/UBC+g22qWAhZt9t1HAxFOQNfVVDiL96BjGgjYb97RO8veTwODWGfxCVdG3IuyXlC58q8l7/+QzeYJT4Wzx5cYqQEwzDxGHZcYmWG+cjQx5IP5IBW+/GM1S0hx+z9kofn4tG5lcMQ8S5pJVnWujHPmnfFhymLLLnQhLJh31DQvtDfULCHh/v9bAwLvNCy6cRNUBJeq3uCYjDPQLmileWd9ow0CwuLYRAPgkmUvdZ4m7C/uMpVGd8ucoB3m/faKeHFw7KxFqfBBeyO/q5kfiRwk/2Yi2IaXC2WMJReiVebZjx6rzSx7NfEEop9E+LITg98cE08XrjAedWnsMb8Wp8KH82FtoPbmR9QW+5lx7ldmkR3XCLyQDub/P1V8wmexSI2LeLycPLXMFy4wb5d0ObpsvmXCDy3OKs/3fkUtkrlonoRU7pq/xGfzK22YacLi8SUQr7R8YaXQfLbjGGH+jbAaWmveV7eMFmYHzBMwW/wQfn+ch+ZBu81ryPSMFsk8h/5SU+Edf47FL2PCzhj/QwMBvGjEnRAhdcxPGCajrsRCmHS+YBL8xGUbfrRxvL9CK/N6k7a9yoTW5kfeAA2UAH5gxV3CcoH3F9aycmEDdNWKOW8T+NN8sGVJf+g11FEDvwsWTF5KkvZxGtzjjdXMAU4CCye3XLnC/b1GzQqAtYynTZ48efIUyw9dbLzBL5PnagAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAbCAYAAACnZAX6AAAApElEQVR4XmNgGFlgBxA/BOIHQHwfyt6FrAAfWA3E/4HYH10CH7gFxJ+BmAVdAheQZIDYAnIq0SCSAaKpAl0CH5jBANFkgS6BD9xgoKd/ytEl8AGiNBkwoLp9FgNEkxmSGAqAKQiD8lkZIMnmCRAzwxShg9NAfAmIpaD8OiD+BcRWcBVYQDgQHwLiNCBeCMRvgDgORQUOIMgAcZ43EAugyY2CIQgA8oAivmU5zC0AAAAASUVORK5CYII=>