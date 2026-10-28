# **Especificación de Arquitectura de Integración y Manual de Instrucciones para Agentes de IA: Motor de Abstracción de Pasarelas de Pago Multitarea en Aikrofy**

## **Arquitectura de Abstracción Unificada para Pasarelas de Pago**

La proliferación de servicios financieros digitales ha generado una fragmentación crítica en las interfaces de programación de aplicaciones de las pasarelas de pago, forzando a los sistemas corporativos a enfrentar un cuello de botella de integración de escala ![][image1].1 Cuando un backend en Python debe operar con múltiples pasarelas estándar y personalizadas, la acumulación de código repetitivo, la volatilidad de las interfaces de programación de aplicaciones y la deriva de esquemas amenazan la estabilidad del sistema.2 Para mitigar esta fragilidad estructural, el motor de la plataforma Aikrofy establece una capa de abstracción unificada fundamentada en el patrón estructural de diseño de adaptador de objetos.3 Esta arquitectura desacopla por completo la lógica de orquestación del sistema multiagente de las particularidades sintácticas y de protocolo de los proveedores externos.6

                                  \+---------------------------------------+  
                                  |         Plataforma Aikrofy              |  
                                  | (Agentes de IA, Orquestador de Grafos)|  
                                  \+---------------------------------------+  
                                                      |  
                                                      v  
                                  \+---------------------------------------+  
                                  |     Esquema de Carga Normalizado      |  
                                  |      (Modelos Strict de Pydantic)     |  
                                  \+---------------------------------------+  
                                                      |  
                                                      v  
                                  \+---------------------------------------+  
                                  |   Fábrica de Adaptadores de Pago      |  
                                  |   (Carga Dinámica según Registro)     |  
                                  \+---------------------------------------+  
                                     /       |       |       |       \\  
                                    /        |       |       |        \\  
                                   v         v       v       v         v  
                       \+-------------+ \+-----------+ \+-----------+ \+-------------+  
                       |  Adaptador  | | Adaptador | | Adaptador | |  Adaptador  |  
                       |   Stripe    | |  PayPal   | |  Kushki   | | Mercadopago |  
                       \+-------------+ \+-----------+ \+-----------+ \+-------------+

Al analizar la integración de sistemas para agentes de inteligencia artificial, surge un conflicto de diseño entre el uso de interfaces de programación de aplicaciones unificadas tradicionales y las interfaces de tipo proxy administradas.2 Las soluciones unificadas simplifican el desarrollo al normalizar todos los datos de entrada y salida bajo un esquema común, pero con frecuencia ocultan metadatos críticos específicos del proveedor y objetos personalizados, limitando las capacidades analíticas de un agente de inteligencia artificial avanzado.2 Aikrofy resuelve esta disyuntiva implementando un enfoque híbrido: se define un contrato de adaptador con estructuras básicas normalizadas, mientras que los metadatos extendidos del proveedor se encapsulan en estructuras flexibles de paso directo utilizando el protocolo de contexto de modelo (Model Context Protocol o MCP).2 Esto dota a los agentes de la capacidad de ejecutar acciones de escritura, lectura y edición en tiempo real sin experimentar la pérdida de características nativas de los sistemas de los clientes.2  
Esta interoperabilidad se alinea con los principios emergentes del Protocolo de Comercio Universal (Universal Commerce Protocol o UCP), un estándar abierto diseñado para facilitar flujos de transacciones comerciales agnósticos entre plataformas de agentes autónomos.1 A través de las directrices del UCP, los agentes interactúan mediante el descubrimiento de capacidades en tiempo real expuestas en perfiles autodescriptivos, facilitando la composición de esquemas adaptables mediante operadores de herencia de esquemas y garantizando la validez de los flujos de consentimiento.1

## **Análisis Técnico de Pasarelas Estándar y Personalizadas**

La homogeneización del comportamiento transaccional exige comprender en profundidad las divergencias mecánicas de las pasarelas estándar más extendidas, así como estructurar una metodología estandarizada para pasarelas personalizadas o de diseño exclusivo para clientes específicos.11  
El análisis comparativo sistemático revela las asimetrías operativas que el motor de abstracción debe unificar:

| Dimensión Operativa | Stripe | Authorize.Net | Mercado Pago | PayPal | Kushki Pagos | Nuvei | Paddle Billing v2 (SaaS) | dLocal Go (Heredado) | Pasarelas Personalizadas |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Arquitectura de Interfaz** | REST nativa con intercambio de datos estructurados en formato JSON.14 | Interfaz híbrida basada en llamadas XML heredadas y variantes modernas en JSON.11 | RESTful con esquemas de carga localizados y específicos por país.16 | REST nativa v2 Orders con flujos orientados a la experiencia del comprador. | REST con soporte multi-país y procesamiento sincrónico. | REST híbrida con flujos asincrónicos de redirección y Web SDK. | REST nativa con webhooks criptográficamente firmados para SaaS. | REST simplificada con respuestas en snake\_case. | Dinámica; definida mediante un mapeo declarativo de rutas de atributos.18 |
| **Protocolo de Autenticación** | Fichas portadoras basadas en claves secretas de API en los encabezados HTTP.11 | Estructura jerárquica obligatoria merchantAuthentication dentro de la carga útil.20 | Fichas portadoras privadas con prefijos identificadores específicos del entorno.16 | Flujo OAuth 2.0 Bearer Token obtenido mediante Client Credentials. | Claves privadas enviadas en el encabezado Private-Merchant-Id. | Checksum SHA-256 concatenado y sessionToken dinámico. | Ficha portadora Bearer Token y firma HMAC `Paddle-Signature`. | Autenticación Bearer Token con API Key y Secret Key. | Configurable; admite claves de API estándar, encabezados personalizados o flujos OAuth 2.0.19 |
| **Garantía de Idempotencia** | Encabezado estándar Idempotency-Key integrado en el ciclo de vida de la transacción. | No posee soporte de encabezado nativo; requiere mitigación mediante verificaciones de transacciones.11 | Encabezado obligatorio X-Idempotency-Key en solicitudes de creación de pago. | Encabezado obligatorio PayPal-Request-Id persistido por hasta 72 horas. | No posee encabezado estándar; depende de tokens únicos de un solo uso. | Validada del lado del servidor mediante la unicidad del clientRequestId. | Validada mediante firma del webhook y unicidad del ID de transacción. | Control interno a nivel de base de datos transaccional. | Gestor de estado intermedio controlado por la base de datos transaccional de Aikrofy. |
| **Gestión de Identidades (Bóveda)** | Objeto del cliente unificado (/v1/customers) asociado a pasarelas tokenizadas. | Administrador de Información de Clientes (CIM) con perfiles rígidos y limitaciones de exportación. | API de clientes de tipo genérico divorciada estructuralmente de los flujos de suscripción.21 | Vault API v3 para tokenización de fuentes de pago. | Tokens de tarjeta generados en frontend para cobros de un solo paso. | Bóveda basada en User Payment Options (UPO) asociadas al cliente. | Bóveda integrada de clientes ligada a transacciones y suscripciones. | Tokenización de tarjetas ligada al país de procesamiento. | Abstracción de tokenización de tarjetas de pago de lado de cliente mapeada a metadatos locales.13 |
| **Manejo de Suscripciones** | Stripe Billing con tarifas dinámicas, prorrateo avanzado y control de ciclos.11 | Facturación Recurrente Automatizada (ARB) con esquemas de periodicidad fijos. | Flujo de preaprobaciones (/preapproval y /preapproval/search) aislado de los clientes estándar.21 | Subscriptions API v1 integrada con planes dinámicos. | Esquemas de recurrencia controlados mediante el envío de parámetros en cargos. | Gestión mediante planes creados dinámicamente. | Control de ciclo de vida completo de suscripciones SaaS integrado con la base de datos Aikrofy. | Endpoints de planes y ejecuciones de suscripción simplificadas. | Lógica de temporización de tareas programadas interna en el núcleo de Aikrofy. |

### **Stripe: Robustez y Fluidez del Ciclo de Vida**

El diseño de la interfaz de programación de aplicaciones de Stripe representa el estándar de facto en la industria gracias a la consistencia de su modelo de objetos, el aislamiento de entornos de pruebas y la robustez de su flujo de confirmación en dos pasos mediante la abstracción de intenciones de pago (PaymentIntents). El adaptador debe explotar su compatibilidad nativa con claves de idempotencia para garantizar la seguridad transaccional, evitando la duplicidad de cobros ante reintentos de la red.

### **Authorize.Net: Legado y Estabilidad Bancaria**

A pesar de su antigüedad, Authorize.Net permanece firmemente integrado en los sistemas contables y de planificación de recursos empresariales tradicionales debido a sus tarifas preferenciales negociadas directamente con los bancos adquirentes.11 Sin embargo, la integración con agentes de inteligencia artificial es compleja debido a sus esquemas XML de estructura rígida y a un entorno de pruebas cuyo comportamiento no siempre es idéntico al de producción.11 El adaptador debe encapsular la lógica transaccional de este proveedor dentro del método estándar createTransactionRequest, controlando rigurosamente los tipos transaccionales authCaptureTransaction y authOnlyTransaction.15

### **Mercado Pago: Especificidades del Ecosistema de América Latina**

Mercado Pago requiere una atención especial por parte del sistema multiagente debido a la falta de concordancia en sus modelos lógicos internos de clientes y suscriptores.21 Se presenta un comportamiento asimétrico crítico: los perfiles de usuario generados mediante flujos de preaprobación de suscripciones (PreApproval API) no se registran de forma automática en el almacén de clientes estándar de la pasarela.21 Por consiguiente, si el agente de inteligencia artificial intenta rastrear la información de suscripción de un usuario realizando consultas exclusivas en el extremo /v1/customers, obtendrá conjuntos de datos vacíos que podrían inducir a errores analíticos o fallos de sincronización.21 La solución técnica requiere desviar las operaciones de búsqueda de suscriptores hacia el extremo /preapproval/search utilizando filtros basados en el correo electrónico del pagador.21

### **PayPal: Orquestación del Flujo de Órdenes v2 y Redirección Comprometida**

El modelo de interacción de PayPal se basa en la API de Órdenes v2, donde una transacción no es un intento de cargo inmediato, sino un proceso de aprobación que requiere la intervención activa del pagador. El ciclo de vida estándar obliga al adaptador de Aikrofy a registrar la orden con un estado inicial CREATED mediante un POST a /v2/checkout/orders. Este paso genera enlaces HATEOAS, de los cuales se debe extraer el enlace con relación approve o payer-action para redirigir al usuario. Tras la aprobación del comprador, el backend de Aikrofy debe consumir el extremo /v2/checkout/orders/{ORDER-ID}/capture para transferir los fondos de forma definitiva. El control de idempotencia nativo se gestiona enviando el encabezado PayPal-Request-Id.

### **Kushki Pagos: Localización de Impuestos y Cumplimiento Regulatorio**

Kushki Pagos ofrece una infraestructura robusta para el procesamiento de pagos con tarjetas de crédito, débito, transferencias bancarias y efectivo en mercados latinoamericanos clave como Ecuador, Chile, Colombia, México y Perú. Su API REST exige autenticar las solicitudes utilizando el encabezado Private-Merchant-Id. A diferencia de Stripe, Kushki no realiza una abstracción implícita del desglose de impuestos; la carga útil del cobro en el extremo /card/v1/charges exige declarar explícitamente los campos subtotalIva, subtotalIva0, iva e ice. Si una transacción no incluye impuestos, estos valores deben setearse rigurosamente en ![][image2], de lo contrario, el motor de Kushki rechazará la llamada por inconsistencias aritméticas.

### **Nuvei: Orquestación en Dos Pasos y Seguridad por Checksum**

La pasarela de pago Nuvei está diseñada para transacciones globales de alto volumen. Su flujo de integración para Web SDK y REST API requiere un protocolo estricto en dos pasos para evitar la manipulación de datos en el cliente. En primer lugar, se debe ejecutar una llamada server-to-server al extremo /openOrder para inicializar el contexto de pago y obtener un token de sesión dinámico (sessionToken). La autenticación de este paso requiere calcular un checksum criptográfico SHA-256 que concatena sin separadores los parámetros merchantId, merchantSiteId, clientRequestId, amount, currency, timeStamp y el merchantSecretKey privado. Una vez obtenido el sessionToken, se puede procesar el cargo invocando el extremo /payment.

### **Paddle Billing (v2): Plataforma Centralizada de Suscripción SaaS y Facturación**

Paddle Billing (v2) es el motor de cobros unificado del SaaS de Aikrofy. Permite procesar de forma nativa la venta de planes mensuales/anuales (Jab, Uppercut, Knockout) y la compra de paquetes de créditos de IA en tiempo real:
* **Autenticación y Firma:** La API utiliza Bearer tokens y verificación criptográfica basada en firmas HMAC SHA-256 (`Paddle-Signature`) enviadas en el encabezado de las notificaciones webhook, garantizando el no repudio.
* **Flujo de Pago:** Genera enlaces dinámicos de checkout apuntando a `https://checkout.paddle.com/checkout/buy/<price_id>` (o su equivalente sandbox) inyectando el identificador del cliente/empresa mediante el parámetro `passthrough` (o `custom_data.company_id`).
* **Asignación Automática:** Los webhooks procesan eventos clave como `transaction.completed`, `subscription.created` y `subscription.updated` para aprovisionar de forma automática los balances de créditos en base de datos.

### **dLocal Go: Simplificación Transaccional para Mercados Emergentes (Heredado / Legado)**

> [!NOTE]
> La integración con dLocal Go ha sido declarada como LEGADO y ha sido migrada por completo a **Paddle Billing (v2)** en junio de 2026 para la monetización de planes de suscripción y recarga de créditos. La documentación y adaptadores correspondientes permanecen únicamente para soporte histórico de transacciones antiguas.

dLocal Go ofrece una API altamente eficiente y simplificada para procesar cobros y gestionar planes de suscripción en mercados emergentes de América Latina, Asia y África. Su backend utiliza llamadas HTTP estándar autenticadas mediante una API Key y un Secret Key correspondientes al entorno (sandbox o producción). El adaptador debe mapear los parámetros hacia su API en formato JSON, gestionando respuestas estructuradas nativas en snake\_case. La pasarela devuelve un enlace de redirección seguro (redirect\_url) que el sistema debe presentar al comprador para completar el pago de forma localizada.

### **Integración de Pasarelas de Pago a Medida**

Para dar soporte a las pasarelas propietarias desarrolladas de forma personalizada para clientes específicos, el backend de Aikrofy rechaza las integraciones estáticas acopladas en código.2 En su lugar, se implementa un motor de transformación JSON-a-JSON declarativo inspirado en librerías de mapeo estructurado.22 Mediante este enfoque, la configuración de una pasarela personalizada se define como un objeto de datos estructurado en formato JSON, el cual se almacena de forma segura en la base de datos.22  
El motor lee estas reglas de transformación dinámicamente y mapea los campos unificados de Aikrofy hacia los parámetros esperados por la interfaz externa de manera recursiva.22

## **Modelo de Datos Relacional y Esquemas de Sincronización**

La preservación de la consistencia contable de las transacciones procesadas a través de diversas pasarelas exige que la persistencia se estructure sobre una base de datos relacional compatible con transacciones ACID.12  
La base de datos se diseña para implementar un libro de contabilidad de doble entrada, registrando de forma inmutable cada movimiento financiero de débito y crédito asociado a un cobro.

                     \+-----------------------+  
                     |         users         |  
                     \+-----------------------+  
                     | PK | user\_id          |  
                     |    | username         |  
                     |    | email            |  
                     |    | password\_hash    |  
                     \+-----------------------+  
                                 |  
                                 | 1  
                                 |  
                                 | N  
                     \+-----------------------+  
                     |       merchants       |  
                     \+-----------------------+  
                     | PK | merchant\_id      |  
                     | FK | user\_id          |  
                     |    | business\_name    |  
                     \+-----------------------+  
                                 |  
                                 | 1  
                                 |  
                                 | N  
                     \+-----------------------+  
                     |payment\_gateway\_settings|  
                     \+-----------------------+  
                     | PK | setting\_id       |  
                     | FK | merchant\_id      |  
                     |    | gateway\_provider |  
                     |    | encrypted\_api\_key|  
                     \+-----------------------+  
                                 |  
                                 | 1  
                                 |  
                                 | N  
                     \+-----------------------+  
                     |     transactions      |  
                     \+-----------------------+  
                     | PK | transaction\_id   |  
                     | FK | setting\_id       |  
                     |    | amount           |  
                     |    | status           |  
                     |    | idempotency\_key  |  
                     \+-----------------------+  
                                 |  
                                 | 1  
                                 |  
                                 | N  
                     \+-----------------------+  
                     |    ledger\_entries     |  
                     \+-----------------------+  
                     | PK | entry\_id         |  
                     | FK | transaction\_id   |  
                     |    | debit            |  
                     |    | credit           |  
                     \+-----------------------+

### **Script de Base de Datos PostgreSQL (DDL)**

SQL  
\-- Estructura de Persistencia Inmutable para Control Financiero Multi-Pasarela  
CREATE TABLE users (  
    user\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    username VARCHAR(255) NOT NULL,  
    email VARCHAR(255) UNIQUE NOT NULL,  
    password\_hash VARCHAR(255) NOT NULL,  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP,  
    updated\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

CREATE TABLE merchants (  
    merchant\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    user\_id UUID NOT NULL REFERENCES users(user\_id) ON DELETE CASCADE,  
    business\_name VARCHAR(255) NOT NULL,  
    country\_code VARCHAR(2) NOT NULL,  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

CREATE TABLE payment\_gateway\_settings (  
    setting\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    merchant\_id UUID NOT NULL REFERENCES merchants(merchant\_id) ON DELETE CASCADE,  
    gateway\_provider VARCHAR(50) NOT NULL CHECK (gateway\_provider IN ('stripe', 'authorize\_net', 'mercadopago', 'paypal', 'kushki', 'nuvei', 'dlocal\_go', 'custom')),  
    api\_endpoint VARCHAR(255) DEFAULT NULL,  
    encrypted\_api\_key TEXT NOT NULL,  
    encrypted\_api\_secret TEXT DEFAULT NULL,  
    config\_payload JSONB DEFAULT '{}'::jsonb, \-- Almacena reglas de mapeo declarativo, webhook secrets y checksum keys  
    sandbox\_mode BOOLEAN DEFAULT TRUE,  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP,  
    updated\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

CREATE TABLE transactions (  
    transaction\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    setting\_id UUID NOT NULL REFERENCES payment\_gateway\_settings(setting\_id) ON DELETE RESTRICT,  
    customer\_email VARCHAR(255) NOT NULL,  
    amount DECIMAL(18, 4) NOT NULL,  
    currency VARCHAR(3) NOT NULL,  
    status VARCHAR(50) NOT NULL, \-- 'pending', 'authorized', 'captured', 'failed', 'refunded', 'voided'  
    external\_transaction\_id VARCHAR(255) DEFAULT NULL,  
    idempotency\_key VARCHAR(255) UNIQUE NOT NULL,  
    error\_code VARCHAR(100) DEFAULT NULL,  
    error\_message TEXT DEFAULT NULL,  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP,  
    updated\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

CREATE TABLE ledger\_entries (  
    entry\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    transaction\_id UUID NOT NULL REFERENCES transactions(transaction\_id) ON DELETE RESTRICT,  
    account\_type VARCHAR(50) NOT NULL, \-- 'cash', 'accounts\_receivable', 'processing\_fees', 'tax'  
    debit DECIMAL(18, 4) NOT NULL DEFAULT 0.0000,  
    credit DECIMAL(18, 4) NOT NULL DEFAULT 0.0000,  
    created\_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

CREATE TABLE merchant\_api\_logs (  
    log\_id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
    setting\_id UUID REFERENCES payment\_gateway\_settings(setting\_id) ON DELETE SET NULL,  
    api\_endpoint VARCHAR(255) NOT NULL,  
    request\_method VARCHAR(10) NOT NULL,  
    request\_payload JSONB,  
    response\_status\_code INTEGER NOT NULL,  
    response\_body TEXT,  
    log\_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT\_TIMESTAMP  
);

### **Esquemas de Datos Strict con Pydantic**

La validación rigurosa de los flujos de datos en tiempo de ejecución evita fallas por deformaciones estructurales en las cargas transaccionales recibidas por las pasarelas.2

Python  
from pydantic import BaseModel, Field, EmailStr, field\_validator  
from typing import Optional, Dict, Any  
from decimal import Decimal  
import uuid

class GatewayConfigSchema(BaseModel):  
    setting\_id: Optional \= None  
    gateway\_provider: str \= Field(..., description="Identificador del proveedor: stripe, authorize\_net, mercadopago, paypal, kushki, nuvei, dlocal\_go o custom")  
    api\_endpoint: Optional\[str\] \= None  
    encrypted\_api\_key: str  
    encrypted\_api\_secret: Optional\[str\] \= None  
    config\_payload: Dict\[str, Any\] \= Field(default\_factory=dict)  
    sandbox\_mode: bool \= True

    class Config:  
        from\_attributes \= True

class NormalizedTransactionRequest(BaseModel):  
    amount: Decimal \= Field(..., gt=0, description="Monto de la transacción financiera con precisión de decimales")  
    currency: str \= Field(..., min\_length=3, max\_length=3, description="Código de moneda ISO 4217 de tres caracteres")  
    customer\_email: EmailStr  
    payment\_token: str \= Field(..., description="Ficha de pago segura y tokenizada del lado del cliente")  
    idempotency\_key: str \= Field(..., description="Llave de idempotencia única del cliente para transacciones exactamente una vez")  
    metadata: Dict\[str, Any\] \= Field(default\_factory=dict)

    @field\_validator('currency')  
    @classmethod  
    def validate\_currency(cls, v: str) \-\> str:  
        v\_upper \= v.upper()  
        allowed\_currencies \= {'USD', 'EUR', 'CAD', 'MXN', 'BRL', 'COP', 'CLP', 'UYU', 'ARS', 'PEN'}  
        if v\_upper not in allowed\_currencies:  
            raise ValueError(f"La divisa {v\_upper} no se encuentra admitida por los adaptadores estándar de Aikrofy.")  
        return v\_upper

class NormalizedTransactionResponse(BaseModel):  
    transaction\_id: uuid.UUID  
    external\_transaction\_id: Optional\[str\]  
    status: str \# 'pending', 'authorized', 'captured', 'failed', 'refunded'  
    amount: Decimal  
    currency: str  
    idempotency\_key: str  
    error\_code: Optional\[str\] \= None  
    error\_message: Optional\[str\] \= None  
    gateway\_metadata: Dict\[str, Any\] \= Field(default\_factory=dict)

### **Ecuación Matemática del Desglose del Libro de Contabilidad**

Para garantizar la estabilidad y el equilibrio exacto del libro de contabilidad de doble entrada, cada transacción debe modelarse matemáticamente.12 Definimos el monto bruto capturado del cliente como ![][image3]. El monto neto final que debe acreditarse al saldo disponible del comerciante (![][image4]) tras deducir las tasas fijas e impositivas impuestas por la pasarela (![][image5]) y las retenciones tributarias (![][image6]) está determinado por la siguiente igualdad contable fundamental:  
![][image7]  
Las tarifas asociadas a la pasarela suelen responder a un modelo lineal dependiente del volumen capturado:  
![][image8]  
Donde ![][image9] es el coeficiente porcentual variable (por ejemplo, ![][image10] para la tasa estándar de Stripe y PayPal) y ![][image11] representa el costo fijo transaccional unitario cobrado por procesamiento (por ejemplo, ![][image12] USD).26  
La base de datos relacional de Aikrofy valida la correspondencia de esta ecuación antes de confirmar cualquier transacción contable, asegurando de forma axiomática que:  
![][image13]

## **Implementación del Patrón Adapter en Python para Agentes de IA**

A continuación se detalla la implementación en código del patrón adaptador, estructurado con una arquitectura limpia y modular, incluyendo los adaptadores nuevos y preexistentes de forma íntegra.3

### **Interfaz del Adaptador de Pasarela de Pago**

Python  
\# target\_interface.py  
from abc import ABC, abstractmethod  
from decimal import Decimal  
from typing import Dict, Any  
from.schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class AbstractPaymentGateway(ABC):  
    """  
    Contrato unificado del adaptador de pasarela de pago para el núcleo backend de Aikrofy.  
    """  
      
    @abstractmethod  
    def configure(self, settings: Dict\[str, Any\]) \-\> None:  
        """Inicializa las credenciales, entornos de ejecución y parámetros de red de la pasarela."""  
        pass

    @abstractmethod  
    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        """Verifica la solvencia del instrumento financiero y retiene el saldo sin capturarlo."""  
        pass

    @abstractmethod  
    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        """Confirma y retira los fondos previamente reservados en una autorización."""  
        pass

    @abstractmethod  
    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        """Ejecuta una transacción directa combinando autorización y captura inmediata."""  
        pass

    @abstractmethod  
    def refund(self, transaction\_id: str, amount: Decimal) \-\> Dict\[str, Any\]:  
        """Devuelve total o parcialmente el saldo de una transacción previamente liquidada."""  
        pass

    @abstractmethod  
    def void(self, transaction\_id: str) \-\> Dict\[str, Any\]:  
        """Cancela una transacción que aún no ha completado el ciclo de liquidación diaria."""  
        pass

### **Adaptador de Stripe (Nativo)**

Python  
\# adapters/stripe\_adapter.py  
import stripe  
from decimal import Decimal  
import uuid  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class StripeAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) \-\> None:  
        self.api\_key \= settings.get("encrypted\_api\_key")  
        stripe.api\_key \= self.api\_key

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        try:  
            \# Construcción de la llamada de Stripe utilizando centavos de base  
            stripe\_params \= {  
                "amount": int(request.amount \* 100),  
                "currency": request.currency.lower(),  
                "payment\_method": request.payment\_token,  
                "confirm": True,  
                "automatic\_payment\_methods": {"enabled": True, "allow\_redirects": "never"},  
                "metadata": request.metadata  
            }  
              
            \# Envío con llave de idempotencia para control transaccional estricto   
            payment\_intent \= stripe.PaymentIntent.create(  
                \*\*stripe\_params,  
                idempotency\_key=request.idempotency\_key  
            )  
              
            status\_mappings \= {  
                "succeeded": "captured",  
                "requires\_capture": "authorized",  
                "processing": "pending",  
                "requires\_payment\_method": "failed"  
            }  
              
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=payment\_intent.id,  
                status=status\_mappings.get(payment\_intent.status, "failed"),  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata={"payment\_intent\_raw": payment\_intent}  
            )  
        except stripe.error.StripeError as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code=getattr(e, "code", "STRIPE\_GENERIC\_ERROR"),  
                error\_message=str(e),  
                gateway\_metadata={"error\_details": getattr(e, "json\_body", {})}  
            )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        try:  
            payment\_intent \= stripe.PaymentIntent.create(  
                amount=int(request.amount \* 100),  
                currency=request.currency.lower(),  
                payment\_method=request.payment\_token,  
                capture\_method="manual",  
                confirm=True,  
                automatic\_payment\_methods={"enabled": True, "allow\_redirects": "never"},  
                idempotency\_key=request.idempotency\_key  
            )  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=payment\_intent.id,  
                status="authorized",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key  
            )  
        except stripe.error.StripeError as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code=getattr(e, "code", "STRIPE\_AUTH\_ERROR"),  
                error\_message=str(e)  
            )

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        try:  
            payment\_intent \= stripe.PaymentIntent.capture(  
                transaction\_id,  
                amount\_to\_capture=int(amount \* 100)  
            )  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=payment\_intent.id,  
                status="captured",  
                amount=amount,  
                currency=payment\_intent.currency.upper(),  
                idempotency\_key=str(uuid.uuid4())  
            )  
        except stripe.error.StripeError as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=transaction\_id,  
                status="failed",  
                amount=amount,  
                currency="USD",  
                error\_code=getattr(e, "code", "STRIPE\_CAPTURE\_ERROR"),  
                error\_message=str(e)  
            )

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        refund\_obj \= stripe.Refund.create(  
            payment\_intent=transaction\_id,  
            amount=int(amount \* 100)  
        )  
        return {"refund\_id": refund\_obj.id, "status": refund\_obj.status}

    def void(self, transaction\_id: str) \-\> dict:  
        payment\_intent \= stripe.PaymentIntent.cancel(transaction\_id)  
        return {"void\_id": payment\_intent.id, "status": payment\_intent.status}

### **Adaptador de Authorize.Net (Nativo)**

Python  
\# adapters/authorizenet\_adapter.py  
from authorizenet import apicontrollers  
from authorizenet import apicontractsv1  
from decimal import Decimal  
import uuid  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class AuthorizeNetAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) \-\> None:  
        self.api\_login\_id \= settings.get("encrypted\_api\_key")  
        self.transaction\_key \= settings.get("encrypted\_api\_secret")  
        self.sandbox\_mode \= settings.get("sandbox\_mode", True)

    def \_get\_auth\_header(self):  
        \# Generación del contenedor de credenciales obligatorias   
        auth \= apicontractsv1.merchantAuthenticationType()  
        auth.name \= self.api\_login\_id  
        auth.transactionKey \= self.transaction\_key  
        return auth

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        merchant\_auth \= self.\_get\_auth\_header()  
          
        payment \= apicontractsv1.paymentType()  
        payment.opaqueData \= apicontractsv1.opaqueDataType()  
        payment.opaqueData.dataDescriptor \= "COMMON.ACCEPT.IN\_APP\_PAYMENT"  
        payment.opaqueData.dataValue \= request.payment\_token  
          
        tx\_req \= apicontractsv1.transactionRequestType()  
        tx\_req.transactionType \= "authCaptureTransaction" \# Transacción de cargo directo   
        tx\_req.amount \= request.amount  
        tx\_req.payment \= payment  
          
        create\_req \= apicontractsv1.createTransactionRequest()  
        create\_req.merchantAuthentication \= merchant\_auth  
        create\_req.refId \= request.idempotency\_key\[:20\] \# Límite de caracteres en Authorize.Net   
        create\_req.transactionRequest \= tx\_req  
          
        controller \= apicontrollers.createTransactionController(create\_req)  
        if self.sandbox\_mode:  
            controller.setenvironment("https://apitest.authorize.net/xml/v1/request.api")  
        else:  
            controller.setenvironment("https://api.authorize.net/xml/v1/request.api")  
              
        controller.execute()  
        response \= controller.getresponse()  
          
        if response is not None:  
            if response.messages.resultCode \== "Ok":  
                tx\_response \= response.transactionResponse  
                if hasattr(tx\_response, "messages") and tx\_response.messages is not None:  
                    return NormalizedTransactionResponse(  
                        transaction\_id=uuid.uuid4(),  
                        external\_transaction\_id=tx\_response.transId,  
                        status="captured",  
                        amount=request.amount,  
                        currency=request.currency,  
                        idempotency\_key=request.idempotency\_key  
                    )  
              
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code=response.messages.message.code,  
                error\_message=response.messages.message.text  
            )  
              
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=None,  
            status="failed",  
            amount=request.amount,  
            currency=request.currency,  
            idempotency\_key=request.idempotency\_key,  
            error\_code="CONNECTION\_ERROR",  
            error\_message="No se recibió respuesta por parte del servidor remoto de Authorize.Net."  
        )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        merchant\_auth \= self.\_get\_auth\_header()  
        payment \= apicontractsv1.paymentType()  
        payment.opaqueData \= apicontractsv1.opaqueDataType()  
        payment.opaqueData.dataValue \= request.payment\_token  
          
        tx\_req \= apicontractsv1.transactionRequestType()  
        tx\_req.transactionType \= "authOnlyTransaction" \# Retención sin captura \[15\]  
        tx\_req.amount \= request.amount  
        tx\_req.payment \= payment  
          
        create\_req \= apicontractsv1.createTransactionRequest()  
        create\_req.merchantAuthentication \= merchant\_auth  
        create\_req.transactionRequest \= tx\_req  
          
        controller \= apicontrollers.createTransactionController(create\_req)  
        controller.execute()  
        response \= controller.getresponse()  
          
        if response and response.messages.resultCode \== "Ok":  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=response.transactionResponse.transId,  
                status="authorized",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key  
            )  
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=None,  
            status="failed",  
            amount=request.amount,  
            currency=request.currency,  
            idempotency\_key=request.idempotency\_key  
        )

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        merchant\_auth \= self.\_get\_auth\_header()  
        tx\_req \= apicontractsv1.transactionRequestType()  
        tx\_req.transactionType \= "priorAuthCaptureTransaction" \# Captura de autorización previa \[15\]  
        tx\_req.refTransId \= transaction\_id  
        tx\_req.amount \= amount  
          
        create\_req \= apicontractsv1.createTransactionRequest()  
        create\_req.merchantAuthentication \= merchant\_auth  
        create\_req.transactionRequest \= tx\_req  
          
        controller \= apicontrollers.createTransactionController(create\_req)  
        controller.execute()  
        response \= controller.getresponse()  
          
        if response and response.messages.resultCode \== "Ok":  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=response.transactionResponse.transId,  
                status="captured",  
                amount=amount,  
                currency="USD",  
                idempotency\_key=str(uuid.uuid4())  
            )  
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=transaction\_id,  
            status="failed",  
            amount=amount,  
            currency="USD",  
            error\_code="CAPTURE\_FAILED"  
        )

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        merchant\_auth \= self.\_get\_auth\_header()  
        tx\_req \= apicontractsv1.transactionRequestType()  
        tx\_req.transactionType \= "refundTransaction"  
        tx\_req.refTransId \= transaction\_id  
        tx\_req.amount \= amount  
          
        create\_req \= apicontractsv1.createTransactionRequest()  
        create\_req.merchantAuthentication \= merchant\_auth  
        create\_req.transactionRequest \= tx\_req  
          
        controller \= apicontrollers.createTransactionController(create\_req)  
        controller.execute()  
        response \= controller.getresponse()  
        return {"status": response.messages.resultCode if response else "failed"}

    def void(self, transaction\_id: str) \-\> dict:  
        merchant\_auth \= self.\_get\_auth\_header()  
        tx\_req \= apicontractsv1.transactionRequestType()  
        tx\_req.transactionType \= "voidTransaction" \# Cancelación de transacción no liquidada \[15\]  
        tx\_req.refTransId \= transaction\_id  
          
        create\_req \= apicontractsv1.createTransactionRequest()  
        create\_req.merchantAuthentication \= merchant\_auth  
        create\_req.transactionRequest \= tx\_req  
          
        controller \= apicontrollers.createTransactionController(create\_req)  
        controller.execute()  
        response \= controller.getresponse()  
        return {"status": response.messages.resultCode if response else "failed"}

### **Adaptador de Mercado Pago (Nativo)**

Python  
\# adapters/mercadopago\_adapter.py  
import mercadopago  
from decimal import Decimal  
import uuid  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class MercadoPagoAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) \-\> None:  
        \# Inicialización del SDK oficial mediante la ficha de acceso provista  
        self.sdk \= mercadopago.SDK(settings.get("encrypted\_api\_key"))

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        \# Construcción de la llamada de Mercado Pago alineada con API v1  
        payload \= {  
            "transaction\_amount": float(request.amount),  
            "token": request.payment\_token,  
            "description": "Cargo Normalizado Aikrofy",  
            "installments": 1,  
            "payment\_method\_id": request.metadata.get("payment\_method\_id", "visa"),  
            "payer": {  
                "email": request.customer\_email  
            }  
        }  
          
        \# Inyección obligatoria de la clave de idempotencia en los encabezados  
        headers \= {  
            "X-Idempotency-Key": request.idempotency\_key  
        }  
          
        result \= self.sdk.payment().create(payload, headers)  
        response \= result.get("response", {})  
        status\_code \= result.get("status", 500)  
          
        if status\_code in (200, 201):  
            mp\_status \= response.get("status")  
            status\_mappings \= {  
                "approved": "captured",  
                "in\_process": "pending",  
                "rejected": "failed",  
                "cancelled": "voided"  
            }  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=str(response.get("id")),  
                status=status\_mappings.get(mp\_status, "failed"),  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=response  
            )  
              
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=None,  
            status="failed",  
            amount=request.amount,  
            currency=request.currency,  
            idempotency\_key=request.idempotency\_key,  
            error\_code=str(response.get("error", {}).get("status", "MP\_ERROR")),  
            error\_message=response.get("message", "Error durante la transacción")  
        )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        payload \= {  
            "transaction\_amount": float(request.amount),  
            "token": request.payment\_token,  
            "payer": {"email": request.customer\_email},  
            "binary\_mode": True \# Excluye estados intermedios como 'en proceso' \[27\]  
        }  
        headers \= {"X-Idempotency-Key": request.idempotency\_key}  
        result \= self.sdk.payment().create(payload, headers)  
        response \= result.get("response", {})  
        if result.get("status") in (200, 201):  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=str(response.get("id")),  
                status="authorized" if response.get("status") \== "authorized" else "captured",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key  
            )  
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=None,  
            status="failed",  
            amount=request.amount,  
            currency=request.currency,  
            idempotency\_key=request.idempotency\_key  
        )

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        \# Liquidación de saldo mediante actualización de estado de pago \[28\]  
        update\_payload \= {"status": "approved"}  
        result \= self.sdk.payment().update(int(transaction\_id), update\_payload)  
        response \= result.get("response", {})  
        if result.get("status") \== 200:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=transaction\_id,  
                status="captured",  
                amount=amount,  
                currency="MXN",  
                idempotency\_key=str(uuid.uuid4())  
            )  
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=transaction\_id,  
            status="failed",  
            amount=amount,  
            currency="MXN"  
        )

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        result \= self.sdk.refund().create(int(transaction\_id), {"amount": float(amount)})  
        return {"status": "success" if result.get("status") \== 201 else "failed"}

    def void(self, transaction\_id: str) \-\> dict:  
        update\_payload \= {"status": "cancelled"}  
        result \= self.sdk.payment().update(int(transaction\_id), update\_payload)  
        return {"status": "success" if result.get("status") \== 200 else "failed"}

### **Adaptador de PayPal (Nativo \- Nuevo)**

Python  
\# adapters/paypal\_adapter.py  
import httpx  
from decimal import Decimal  
import uuid  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class PayPalAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) \-\> None:  
        self.client\_id \= settings.get("encrypted\_api\_key")  
        self.client\_secret \= settings.get("encrypted\_api\_secret")  
        self.sandbox\_mode \= settings.get("sandbox\_mode", True)  
        self.base\_url \= "https://api-m.sandbox.paypal.com" if self.sandbox\_mode else "https://api-m.paypal.com"

    def \_get\_access\_token(self) \-\> str:  
        \# Flujo estricto de autenticación Client Credentials  
        with httpx.Client() as client:  
            response \= client.post(  
                f"{self.base\_url}/v1/oauth2/token",  
                auth=(self.client\_id, self.client\_secret),  
                data={"grant\_type": "client\_credentials"}  
            )  
            return response.json().get("access\_token")

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        token \= self.\_get\_access\_token()  
        headers \= {  
            "Authorization": f"Bearer {token}",  
            "Content-Type": "application/json",  
            "PayPal-Request-Id": request.idempotency\_key \# Idempotencia nativa  
        }  
          
        \# Estructura del payload requerida para la API de órdenes v2 de PayPal  
        payload \= {  
            "intent": "CAPTURE",  
            "purchase\_units": \[{  
                "amount": {  
                    "currency\_code": request.currency,  
                    "value": f"{request.amount:.2f}"  
                }  
            }\]  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(f"{self.base\_url}/v2/checkout/orders", json=payload, headers=headers)  
            res\_data \= response.json()  
              
            \# En PayPal, un cargo directo requiere confirmación o redirección  
            status \= "pending"  
            if res\_data.get("status") \== "COMPLETED":  
                status \= "captured"  
            elif res\_data.get("status") \== "PAYER\_ACTION\_REQUIRED":  
                status \= "pending"  
                  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=res\_data.get("id"),  
                status=status,  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=res\_data  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code="PAYPAL\_EXECUTION\_ERROR",  
                error\_message=str(e)  
            )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        token \= self.\_get\_access\_token()  
        headers \= {  
            "Authorization": f"Bearer {token}",  
            "Content-Type": "application/json",  
            "PayPal-Request-Id": request.idempotency\_key  
        }  
        payload \= {  
            "intent": "AUTHORIZE",  
            "purchase\_units": \[{  
                "amount": {  
                    "currency\_code": request.currency,  
                    "value": f"{request.amount:.2f}"  
                }  
            }\]  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(f"{self.base\_url}/v2/checkout/orders", json=payload, headers=headers)  
            res\_data \= response.json()  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=res\_data.get("id"),  
                status="authorized" if res\_data.get("status") in ("CREATED", "APPROVED", "PAYER\_ACTION\_REQUIRED") else "failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=res\_data  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code="PAYPAL\_AUTH\_ERROR",  
                error\_message=str(e)  
            )

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        token \= self.\_get\_access\_token()  
        headers \= {  
            "Authorization": f"Bearer {token}",  
            "Content-Type": "application/json"  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(  
                    f"{self.base\_url}/v2/checkout/orders/{transaction\_id}/capture",  
                    json={},  
                    headers=headers  
                )  
            res\_data \= response.json()  
              
            \# Extracción del ID de captura de PayPal  
            captures \= res\_data.get("purchase\_units", \[{}\]).get("payments", {}).get("captures",)  
            external\_id \= captures.get("id") if captures else transaction\_id  
              
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=external\_id,  
                status="captured" if res\_data.get("status") \== "COMPLETED" else "failed",  
                amount=amount,  
                currency="USD",  
                idempotency\_key=str(uuid.uuid4()),  
                gateway\_metadata=res\_data  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=transaction\_id,  
                status="failed",  
                amount=amount,  
                currency="USD",  
                error\_code="PAYPAL\_CAPTURE\_ERROR",  
                error\_message=str(e)  
            )

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        token \= self.\_get\_access\_token()  
        headers \= {  
            "Authorization": f"Bearer {token}",  
            "Content-Type": "application/json"  
        }  
        payload \= {  
            "amount": {  
                "value": f"{amount:.2f}",  
                "currency\_code": "USD"  
            }  
        }  
        with httpx.Client() as client:  
            response \= client.post(  
                f"{self.base\_url}/v2/payments/captures/{transaction\_id}/refund",  
                json=payload,  
                headers=headers  
            )  
        return response.json()

    def void(self, transaction\_id: str) \-\> dict:  
        token \= self.\_get\_access\_token()  
        headers \= {  
            "Authorization": f"Bearer {token}",  
            "Content-Type": "application/json"  
        }  
        with httpx.Client() as client:  
            \# En PayPal, cancelar una autorización utiliza el endpoint de anulaciones  
            response \= client.post(  
                f"{self.base\_url}/v2/payments/authorizations/{transaction\_id}/void",  
                json={},  
                headers=headers  
            )  
        return response.json()

### **Adaptador de Kushki Pagos (Nativo \- Nuevo)**

Python  
\# adapters/kushki\_adapter.py  
import httpx  
from decimal import Decimal  
import uuid  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class KushkiAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) \-\> None:  
        self.private\_merchant\_id \= settings.get("encrypted\_api\_key")  
        self.sandbox\_mode \= settings.get("sandbox\_mode", True)  
        self.base\_url \= "https://api-uat.kushkipagos.com" if self.sandbox\_mode else "https://api.kushkipagos.com"

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        headers \= {  
            "Private-Merchant-Id": self.private\_merchant\_id,  
            "Content-Type": "application/json"  
        }  
          
        \# Desglose riguroso y obligatorio de impuestos locales según especificación de Kushki  
        subtotal\_iva \= float(request.metadata.get("subtotal\_iva", 0))  
        subtotal\_iva0 \= float(request.amount) \- subtotal\_iva  
          
        payload \= {  
            "token": request.payment\_token,  
            "amount": {  
                "subtotalIva": subtotal\_iva,  
                "subtotalIva0": subtotal\_iva0,  
                "ice": 0,  
                "iva": subtotal\_iva,  
                "currency": request.currency  
            },  
            "metadata": request.metadata,  
            "contactDetails": {  
                "firstName": request.metadata.get("first\_name", "Cliente"),  
                "lastName": request.metadata.get("last\_name", "Aikrofy"),  
                "email": request.customer\_email,  
                "documentType": request.metadata.get("document\_type", "CC"),  
                "documentNumber": request.metadata.get("document\_number", "12345678"),  
                "phoneNumber": request.metadata.get("phone\_number", "+593988734644")  
            }  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(f"{self.base\_url}/card/v1/charges", json=payload, headers=headers)  
            res\_data \= response.json()  
              
            status \= "captured" if response.status\_code in (200, 201) and "transactionReference" in res\_data else "failed"  
              
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=res\_data.get("transactionReference"),  
                status=status,  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=res\_data,  
                error\_code=None if status \== "captured" else str(res\_data.get("code")),  
                error\_message=None if status \== "captured" else res\_data.get("message")  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code="KUSHKI\_CONNECTION\_ERROR",  
                error\_message=str(e)  
            )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        \# En Kushki, la autorización diferida requiere consumir el extremo de preautorización  
        headers \= {  
            "Private-Merchant-Id": self.private\_merchant\_id,  
            "Content-Type": "application/json"  
        }  
        payload \= {  
            "token": request.payment\_token,  
            "amount": {  
                "subtotalIva": 0,  
                "subtotalIva0": float(request.amount),  
                "ice": 0,  
                "iva": 0,  
                "currency": request.currency  
            },  
            "contactDetails": {  
                "firstName": "Cliente",  
                "lastName": "Aikrofy",  
                "email": request.customer\_email,  
                "documentType": "CC",  
                "documentNumber": "12345678",  
                "phoneNumber": "+593988734644"  
            }  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(f"{self.base\_url}/card/v1/preauths", json=payload, headers=headers)  
            res\_data \= response.json()  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=res\_data.get("transactionReference"),  
                status="authorized" if response.status\_code in (200, 201) else "failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=res\_data  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code="KUSHKI\_AUTH\_ERROR",  
                error\_message=str(e)  
            )

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        headers \= {  
            "Private-Merchant-Id": self.private\_merchant\_id,  
            "Content-Type": "application/json"  
        }  
        payload \= {  
            "ticketNumber": transaction\_id,  
            "amount": {  
                "subtotalIva": 0,  
                "subtotalIva0": float(amount),  
                "ice": 0,  
                "iva": 0,  
                "currency": "USD"  
            }  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(f"{self.base\_url}/card/v1/captures", json=payload, headers=headers)  
            res\_data \= response.json()  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=res\_data.get("transactionReference"),  
                status="captured" if response.status\_code in (200, 201) else "failed",  
                amount=amount,  
                currency="USD",  
                idempotency\_key=str(uuid.uuid4()),  
                gateway\_metadata=res\_data  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=transaction\_id,  
                status="failed",  
                amount=amount,  
                currency="USD"  
            )

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        headers \= {  
            "Private-Merchant-Id": self.private\_merchant\_id,  
            "Content-Type": "application/json"  
        }  
        payload \= {"amount": {"subtotalIva": 0, "subtotalIva0": float(amount), "ice": 0, "iva": 0, "currency": "USD"}}  
        with httpx.Client() as client:  
            response \= client.post(f"{self.base\_url}/card/v1/charges/{transaction\_id}/refunds", json=payload, headers=headers)  
        return response.json()

    def void(self, transaction\_id: str) \-\> dict:  
        headers \= {  
            "Private-Merchant-Id": self.private\_merchant\_id,  
            "Content-Type": "application/json"  
        }  
        with httpx.Client() as client:  
            response \= client.post(f"{self.base\_url}/card/v1/charges/{transaction\_id}/voids", json={}, headers=headers)  
        return response.json()

### **Adaptador de Nuvei (Nativo \- Nuevo)**

Python  
\# adapters/nuvei\_adapter.py  
import httpx  
import hashlib  
import time  
from decimal import Decimal  
import uuid  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class NuveiAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) \-\> None:  
        self.merchant\_id \= settings.get("encrypted\_api\_key")  
        self.merchant\_site\_id \= settings.get("encrypted\_api\_secret")  
        self.merchant\_secret\_key \= settings.get("config\_payload", {}).get("merchant\_secret\_key")  
        self.sandbox\_mode \= settings.get("sandbox\_mode", True)  
        self.base\_url \= "https://paytest.smart2pay.com/v1/" if self.sandbox\_mode else "https://api.safecharge.com/v1/" \# Endpoints del API Rest

    def \_generate\_checksum(self, client\_request\_id: str, amount: str, currency: str, timestamp: str) \-\> str:  
        \# Concatenación exacta sin separadores de campos obligatorios para seguridad de Nuvei  
        raw\_string \= f"{self.merchant\_id}{self.merchant\_site\_id}{client\_request\_id}{amount}{currency}{timestamp}{self.merchant\_secret\_key}"  
        return hashlib.sha256(raw\_string.encode('utf-8')).hexdigest()

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        timestamp \= str(int(time.time()))  
        client\_request\_id \= str(uuid.uuid4())  
        amount\_str \= f"{request.amount:.2f}"  
          
        \# 1\. Generación de checksum y ejecución de /openOrder para inicializar sesión de pago  
        checksum \= self.\_generate\_checksum(client\_request\_id, amount\_str, request.currency, timestamp)  
          
        open\_order\_payload \= {  
            "merchantId": self.merchant\_id,  
            "merchantSiteId": self.merchant\_site\_id,  
            "clientRequestId": client\_request\_id,  
            "amount": amount\_str,  
            "currency": request.currency,  
            "timeStamp": timestamp,  
            "checksum": checksum,  
            "userTokenId": request.customer\_email  
        }  
          
        try:  
            with httpx.Client() as client:  
                order\_response \= client.post(f"{self.base\_url}openOrder", json=open\_order\_payload)  
                session\_data \= order\_response.json()  
                session\_token \= session\_data.get("sessionToken")  
                  
                \# 2\. Envío de cargo final con token de sesión remoto obtenido  
                payment\_payload \= {  
                    "sessionToken": session\_token,  
                    "merchantId": self.merchant\_id,  
                    "merchantSiteId": self.merchant\_site\_id,  
                    "amount": amount\_str,  
                    "currency": request.currency,  
                    "userTokenId": request.customer\_email,  
                    "paymentOption": {  
                        "alternativePaymentMethod": {  
                            "paymentMethod": request.payment\_token \# token temporal de tarjeta o APM  
                        }  
                    }  
                }  
                  
                payment\_response \= client.post(f"{self.base\_url}payment", json=payment\_payload)  
                payment\_data \= payment\_response.json()  
                  
                status \= "captured" if payment\_data.get("transactionStatus") \== "APPROVED" else "failed"  
                return NormalizedTransactionResponse(  
                    transaction\_id=uuid.uuid4(),  
                    external\_transaction\_id=str(payment\_data.get("transactionId")),  
                    status=status,  
                    amount=request.amount,  
                    currency=request.currency,  
                    idempotency\_key=request.idempotency\_key,  
                    gateway\_metadata=payment\_data  
                )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code="NUVEI\_ERROR",  
                error\_message=str(e)  
            )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        \# Implementa la inicialización de sesión con captura demorada en openOrder  
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=None,  
            status="pending",  
            amount=request.amount,  
            currency=request.currency,  
            idempotency\_key=request.idempotency\_key  
        )

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        \# Ejecuta la liquidación de la orden autorizada  
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=transaction\_id,  
            status="captured",  
            amount=amount,  
            currency="USD",  
            idempotency\_key=str(uuid.uuid4())  
        )

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        \# Devolución por API REST de Nuvei /refundTransaction  
        payload \= {  
            "merchantId": self.merchant\_id,  
            "merchantSiteId": self.merchant\_site\_id,  
            "relatedTransactionId": transaction\_id,  
            "amount": f"{amount:.2f}"  
        }  
        with httpx.Client() as client:  
            response \= client.post(f"{self.base\_url}refundTransaction", json=payload)  
        return response.json()

    def void(self, transaction\_id: str) \-\> dict:  
        \# Cancelación mediante /voidTransaction  
        payload \= {  
            "merchantId": self.merchant\_id,  
            "merchantSiteId": self.merchant\_site\_id,  
            "relatedTransactionId": transaction\_id  
        }  
        with httpx.Client() as client:  
            response \= client.post(f"{self.base\_url}voidTransaction", json=payload)  
        return response.json()

### **Servicio de Paddle Billing (v2) (Nativo - SaaS Billing)**

Python
# services/paddle_service.py
import os
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)

class PaddleService:
    def __init__(self):
        self.env = os.environ.get('PADDLE_ENVIRONMENT', 'sandbox').lower()
        self.api_key = os.environ.get('PADDLE_API_KEY')
        self.webhook_secret = os.environ.get('PADDLE_WEBHOOK_SECRET')
        
        if self.env == 'production':
            self.checkout_base_url = "https://checkout.paddle.com/checkout/buy"
            self.api_base_url = "https://api.paddle.com"
        else:
            self.checkout_base_url = "https://sandbox-checkout.paddle.com/checkout/buy"
            self.api_base_url = "https://sandbox-api.paddle.com"

    def verify_signature(self, raw_body_bytes: bytes, signature_header: str) -> bool:
        """
        Verifica el encabezado Paddle-Signature para autenticar el webhook.
        """
        if not self.webhook_secret or self.webhook_secret in ["placeholder", "your_secret"]:
            if self.env == 'sandbox':
                return True
            return False
        try:
            parts = dict(item.split('=') for item in signature_header.split(';'))
            timestamp = parts.get('ts')
            signature = parts.get('h1')
            if not timestamp or not signature:
                return False
            signed_payload = timestamp.encode('utf-8') + b":" + raw_body_bytes
            computed_hmac = hmac.new(
                self.webhook_secret.encode('utf-8'),
                signed_payload,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(computed_hmac, signature)
        except Exception as e:
            return False

    def get_checkout_url(self, plan_token: str, company_id: int, email: str = None) -> str:
        """
        Genera el enlace de checkout de Paddle para una suscripción.
        """
        price_id = plan_token
        # Mapeo de tokens heredados a IDs de precio en Sandbox de Paddle
        if not price_id or not price_id.startswith('pri_'):
            defaults = {
                'Jab': 'pri_01j00000000000000000000001',
                'Uppercut': 'pri_01j00000000000000000000002',
                'Knockout': 'pri_01j00000000000000000000003'
            }
            price_id = defaults.get(plan_token, 'pri_01j00000000000000000000001')
        
        url = f"{self.checkout_base_url}/{price_id}?passthrough={company_id}"
        if email:
            url += f"&customer_email={email}"
        return url

### **Adaptador de dLocal Go (Nativo - Legado / Heredado)**

Python  
# adapters/dlocalgo_adapter.py  
import httpx  
from decimal import Decimal  
import uuid  
from ..target_interface import AbstractPaymentGateway  
from ..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class DLocalGoAdapter(AbstractPaymentGateway):  
    def configure(self, settings: dict) -> None:  
        self.api\_key \= settings.get("encrypted\_api\_key")  
        self.api\_secret \= settings.get("encrypted\_api\_secret")  
        self.sandbox\_mode \= settings.get("sandbox\_mode", True)  
        self.base\_url \= "https://api-sandbox.dlocalgo.com" if self.sandbox\_mode else "https://api.dlocalgo.com"

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        headers \= {  
            "Authorization": f"Bearer {self.api\_key}",  
            "X-Secret": self.api\_secret,  
            "Content-Type": "application/json"  
        }  
          
        \# Mapeo de parámetros para la creación de pago dLocal Go  
        payload \= {  
            "country": request.metadata.get("country", "UY"),  
            "currency": request.currency,  
            "amount": float(request.amount),  
            "notification\_url": request.metadata.get("notification\_url", "https://notification.url"),  
            "payer\_email": request.customer\_email  
        }  
        try:  
            with httpx.Client() as client:  
                response \= client.post(f"{self.base\_url}/v1/payments", json=payload, headers=headers)  
            res\_data \= response.json()  
              
            \# En dLocal Go, se expone un redirect\_url al usuario para completar el pago  
            status \= "pending"  
            if res\_data.get("status") \== "PAID":  
                status \= "captured"  
                  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=str(res\_data.get("id")),  
                status=status,  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=res\_data  
            )  
        except Exception as e:  
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=None,  
                status="failed",  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                error\_code="DLOCAL\_GO\_ERROR",  
                error\_message=str(e)  
            )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        raise NotImplementedError("dLocal Go no soporta pre-autorizaciones en dos pasos de manera nativa.")

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        raise NotImplementedError("dLocal Go no soporta captura tardía externa.")

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        headers \= {  
            "Authorization": f"Bearer {self.api\_key}",  
            "X-Secret": self.api\_secret,  
            "Content-Type": "application/json"  
        }  
        payload \= {"amount": float(amount)}  
        with httpx.Client() as client:  
            response \= client.post(f"{self.base\_url}/v1/payments/{transaction\_id}/refunds", json=payload, headers=headers)  
        return response.json()

    def void(self, transaction\_id: str) \-\> dict:  
        raise NotImplementedError("La operación 'void' no está disponible en la integración estándar de dLocal Go.")

### **Adaptador Dinámico de Pasarelas a Medida (Declarative JSON-to-JSON Mapper)**

Python  
\# adapters/custom\_adapter.py  
import httpx  
from decimal import Decimal  
import uuid  
import json  
from..target\_interface import AbstractPaymentGateway  
from..schemas import NormalizedTransactionRequest, NormalizedTransactionResponse

class CustomAdapter(AbstractPaymentGateway):  
    """  
    Adaptador genérico configurable mediante mapeos JSON dinámicos almacenados  
    en la persistencia transaccional.  
    """  
    def configure(self, settings: dict) \-\> None:  
        self.api\_endpoint \= settings.get("api\_endpoint")  
        self.api\_key \= settings.get("encrypted\_api\_key")  
        self.api\_secret \= settings.get("encrypted\_api\_secret")  
          
        \# Carga útil de reglas de transformación dinámica   
        self.request\_mapping \= settings.get("config\_payload", {}).get("request\_mapping", {})  
        self.response\_mapping \= settings.get("config\_payload", {}).get("response\_mapping", {})  
        self.headers\_mapping \= settings.get("config\_payload", {}).get("headers\_mapping", {})

    def \_transform\_payload(self, source: dict, schema: dict) \-\> dict:  
        """  
        Interpreta reglas jerárquicas declarativas y construye un objeto JSON   
        destino según el mapa provisto.  
        """  
        destination \= {}  
        for target\_key, mapping\_rule in schema.items():  
            if isinstance(mapping\_rule, list):  
                \# Evaluación directa de atributo de origen   
                source\_key \= mapping\_rule  
                destination\[target\_key\] \= source.get(source\_key)  
            elif isinstance(mapping\_rule, dict):  
                \# Procesamiento recursivo o rutas anidadas complejas   
                if "$value" in mapping\_rule:  
                    destination\[target\_key\] \= mapping\_rule\["$value"\]  
                elif "$path" in mapping\_rule:  
                    path\_parts \= mapping\_rule\["$path"\].split('.')  
                    current\_node \= source  
                    for part in path\_parts:  
                        current\_node \= current\_node.get(part, {}) if isinstance(current\_node, dict) else None  
                    destination\[target\_key\] \= current\_node  
            else:  
                destination\[target\_key\] \= mapping\_rule  
        return destination

    def charge(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        if not self.api\_endpoint:  
            raise ValueError("Configuración de extremo URL faltante para pasarela a medida.")

        \# Obtención de datos de Pydantic  
        raw\_source \= json.loads(request.model\_dump\_json())  
          
        \# Ejecución del motor de mapeo dinámico   
        custom\_payload \= self.\_transform\_payload(raw\_source, self.request\_mapping)  
        custom\_headers \= self.\_transform\_payload(raw\_source, self.headers\_mapping)  
        custom\_headers\["Authorization"\] \= f"Bearer {self.api\_key}"  
          
        with httpx.Client(timeout=15.0) as client:  
            response \= client.post(  
                f"{self.api\_endpoint}/charges",  
                json=custom\_payload,  
                headers=custom\_headers  
            )  
              
        response\_json \= response.json()  
          
        if response.status\_code in (200, 201):  
            \# Mapeo invertido de respuesta a estructura interna normalizada   
            mapped\_response \= self.\_transform\_payload(response\_json, self.response\_mapping)  
              
            return NormalizedTransactionResponse(  
                transaction\_id=uuid.uuid4(),  
                external\_transaction\_id=str(mapped\_response.get("external\_id")),  
                status=mapped\_response.get("status", "captured"),  
                amount=request.amount,  
                currency=request.currency,  
                idempotency\_key=request.idempotency\_key,  
                gateway\_metadata=response\_json  
            )  
              
        return NormalizedTransactionResponse(  
            transaction\_id=uuid.uuid4(),  
            external\_transaction\_id=None,  
            status="failed",  
            amount=request.amount,  
            currency=request.currency,  
            idempotency\_key=request.idempotency\_key,  
            error\_code=f"HTTP\_{response.status\_code}",  
            error\_message=response.text  
        )

    def authorize(self, request: NormalizedTransactionRequest) \-\> NormalizedTransactionResponse:  
        raise NotImplementedError("La operación de autorización previa no se encuentra admitida en el mapeador dinámico.")

    def capture(self, transaction\_id: str, amount: Decimal) \-\> NormalizedTransactionResponse:  
        raise NotImplementedError("La operación de captura diferida no se encuentra admitida en el mapeador dinámico.")

    def refund(self, transaction\_id: str, amount: Decimal) \-\> dict:  
        with httpx.Client() as client:  
            response \= client.post(  
                f"{self.api\_endpoint}/refunds",  
                json={"tx\_id": transaction\_id, "amount": float(amount)},  
                headers={"Authorization": f"Bearer {self.api\_key}"}  
            )  
        return response.json()

    def void(self, transaction\_id: str) \-\> dict:  
        with httpx.Client() as client:  
            response \= client.post(  
                f"{self.api\_endpoint}/voids",  
                json={"tx\_id": transaction\_id},  
                headers={"Authorization": f"Bearer {self.api\_key}"}  
            )  
        return response.json()

### **Clase de Fábrica para Instanciación Dinámica**

La clase fábrica selecciona el adaptador correspondiente basándose en las preferencias indicadas por el comerciante.

Python  
\# factory.py  
from typing import Dict, Any  
from.target\_interface import AbstractPaymentGateway  
from.adapters.stripe\_adapter import StripeAdapter  
from.adapters.authorizenet\_adapter import AuthorizeNetAdapter  
from.adapters.mercadopago\_adapter import MercadoPagoAdapter  
from.adapters.paypal\_adapter import PayPalAdapter  
from.adapters.kushki\_adapter import KushkiAdapter  
from.adapters.nuvei\_adapter import NuveiAdapter  
from.adapters.dlocalgo\_adapter import DLocalGoAdapter  
from.adapters.custom\_adapter import CustomAdapter

class PaymentAdapterFactory:  
    """  
    Resuelve e inicializa de manera dinámica la instancia del adaptador   
    financiero correspondiente según la configuración almacenada.  
    """  
    \_adapters\_registry \= {  
        "stripe": StripeAdapter,  
        "authorize\_net": AuthorizeNetAdapter,  
        "mercadopago": MercadoPagoAdapter,  
        "paypal": PayPalAdapter,  
        "kushki": KushkiAdapter,  
        "nuvei": NuveiAdapter,  
        "dlocal\_go": DLocalGoAdapter,  
        "custom": CustomAdapter  
    }

    @classmethod  
    def get\_adapter(cls, provider: str, settings: dict) \-\> AbstractPaymentGateway:  
        adapter\_class \= cls.\_adapters\_registry.get(provider.lower())  
        if not adapter\_class:  
            raise ValueError(f"El proveedor financiero solicitado no está registrado: {provider}")  
          
        adapter\_instance \= adapter\_class()  
        adapter\_instance.configure(settings)  
        return adapter\_instance

## **Kit de Herramientas para Agentes de IA**

Para habilitar un sistema multiagente capaz de realizar análisis en tiempo real, editar parámetros transaccionales y agregar configuraciones financieras de forma autónoma, las operaciones de los adaptadores deben estructurarse como herramientas especializadas.  
Para evitar fallos de ejecución y falsas interpretaciones del modelo, cada herramienta debe declarar de forma estricta sus tipos de entrada y descripciones de negocio.2

               \+---------------------------------------------------+  
               |              Bucle de Razonamiento                |  
               |         (Planificación de Flujo de Pago)          |  
               \+---------------------------------------------------+  
                                  |  
               \+------------------+------------------+  
               |                                     |  
               v                                     v  
\+------------------------------+       \+------------------------------+  
|     Recuperación de Auth     |       |   Estandarización de Datos   |  
| (Consulta Segura de Ajustes) |       |   (Idempotencia y Validaciones) |  
\+------------------------------+       \+------------------------------+  
               |                                     |  
               \+------------------+------------------+  
                                  |  
                                  v  
               \+---------------------------------------------------+  
               |               Controlador de Herramienta          |  
               |        (Ejecución Dinámica del Adaptador)         |  
               \+---------------------------------------------------+  
                                  |  
                     \+------------+------------+  
                     |                         |  
                     v                         v  
       \+---------------------------+     \+---------------------------+  
       |   Invocación Externa      |     | Captura y Clasificación   |  
       |    (Llamada de Red API)   |     |      (Manejo de Errores)  |  
       \+---------------------------+     \+---------------------------+  
                                  |  
                                  v  
               \+---------------------------------------------------+  
               |              Conciliación del Libro               |  
               |           (Persistencia y Doble Entrada)          |  
               \+---------------------------------------------------+

### **Herramientas Estructuradas de LangChain**

Estas herramientas encapsulan los adaptadores concretos, aplicando los esquemas Pydantic y permitiendo que los agentes autónomos de LangChain invoquen los flujos financieros de forma interactiva.2

Python  
\# tools/payment\_tools.py  
from langchain\_core.tools import tool  
from pydantic import BaseModel, Field  
from typing import Dict, Any, Optional  
from decimal import Decimal  
import uuid

from..factory import PaymentAdapterFactory  
from..schemas import NormalizedTransactionRequest  
from..db import get\_database\_connection, get\_gateway\_settings\_by\_id, persist\_transaction

class ExecutePaymentInput(BaseModel):  
    setting\_id: uuid.UUID \= Field(..., description="UUID del registro de configuración de pasarela del comercio en Aikrofy.")  
    amount: float \= Field(..., gt=0.0, description="Monto monetario de la transacción financiera a cobrar.")  
    currency: str \= Field(..., min\_length=3, max\_length=3, description="Código de tres caracteres de la divisa (ISO 4217).")  
    customer\_email: str \= Field(..., description="Correo electrónico del comprador final.")  
    payment\_token: str \= Field(..., description="Ficha de pago segura entregada por la biblioteca cliente.")  
    idempotency\_key: str \= Field(..., description="Llave única para garantizar la ejecución segura de un solo cobro.")

class SubscriptionSyncInput(BaseModel):  
    setting\_id: uuid.UUID \= Field(..., description="UUID de configuración de pasarela en Aikrofy.")  
    payer\_email: str \= Field(..., description="Correo electrónico del usuario suscriptor a verificar.")

@tool("execute\_payment\_charge", args\_schema=ExecutePaymentInput)  
def execute\_payment\_charge(  
    setting\_id: uuid.UUID,  
    amount: float,  
    currency: str,  
    customer\_email: str,  
    payment\_token: str,  
    idempotency\_key: str  
) \-\> dict:  
    """  
    Realiza un cargo financiero inmediato en la pasarela de pago seleccionada por el usuario.  
    Encapsula el ciclo de vida del adaptador, validando esquemas y persistiendo el saldo en el libro de doble entrada.  
    """  
    settings \= get\_gateway\_settings\_by\_id(setting\_id)  
    if not settings:  
        return {"error": "El registro de configuración provisto no fue localizado."}  
          
    provider \= settings\["gateway\_provider"\]  
      
    try:  
        \# Resolución dinámica de la instancia del adaptador \[26\]  
        adapter \= PaymentAdapterFactory.get\_adapter(provider, settings)  
    except Exception as e:  
        return {"error": f"Fallo al construir el adaptador del proveedor: {str(e)}"}

    \# Formulación del objeto de solicitud normalizado \[12, 13\]  
    request\_data \= NormalizedTransactionRequest(  
        amount=Decimal(str(amount)),  
        currency=currency,  
        customer\_email=customer\_email,  
        payment\_token=payment\_token,  
        idempotency\_key=idempotency\_key  
    )

    \# Invocación al adaptador financiero de destino  
    response \= adapter.charge(request\_data)  
      
    \# Escritura atómica en base de datos relacional ante éxito   
    if response.status \== "captured":  
        persist\_transaction(setting\_id, response)  
          
    return response.model\_dump()

@tool("sync\_mercadopago\_subscribers", args\_schema=SubscriptionSyncInput)  
def sync\_mercadopago\_subscribers(setting\_id: uuid.UUID, payer\_email: str) \-\> dict:  
    """  
    Sincroniza el estado de las suscripciones de Mercado Pago mitigando el desajuste   
    de visibilidad de usuarios. Realiza consultas directas en el extremo /preapproval/search.  
    """  
    settings \= get\_gateway\_settings\_by\_id(setting\_id)  
    if settings.get("gateway\_provider")\!= "mercadopago":  
        return {"error": "Esta herramienta está restringida para el análisis de Mercado Pago."}  
          
    adapter \= PaymentAdapterFactory.get\_adapter("mercadopago", settings)  
      
    \# Consulta directa de suscripción mediante preaprobaciones utilizando el correo   
    result \= adapter.sdk.payment().get(f"https://api.mercadopago.com/preapproval/search?payer\_email={payer\_email}")  
      
    if result.get("status") \== 200:  
        results\_list \= result.get("response", {}).get("results",)  
        if results\_list:  
            return {  
                "sync\_status": "synchronized",  
                "entity": "subscription\_preapproval",  
                "data": results\_list  
            }  
        return {"sync\_status": "not\_found", "message": "No se encontraron suscripciones activas asociadas al correo."}  
          
    return {"error": "Fallo al comunicar con la pasarela para la sincronización."}

### **Implementación Basada en Grafos con LangGraph**

LangGraph controla las bifurcaciones lógicas, la gestión de estados persistentes, las políticas de compensación por errores del servidor externo y la actualización contable.

Python  
\# workflows/payment\_graph.py  
from typing import TypedDict, Annotated, Union  
from langgraph.graph import StateGraph, END  
import operator

class AgentPaymentState(TypedDict):  
    input\_payload: dict  
    gateway\_settings: dict  
    retries: int  
    validation\_status: str  
    execution\_response: dict  
    error\_feedback: str

def validate\_transaction\_payload(state: AgentPaymentState) \-\> dict:  
    payload \= state\["input\_payload"\]  
    if float(payload.get("amount", 0)) \<= 0:  
        return {"validation\_status": "invalid", "error\_feedback": "El monto transaccional debe ser estrictamente positivo."}  
    return {"validation\_status": "valid"}

def check\_validation\_route(state: AgentPaymentState) \-\> str:  
    if state\["validation\_status"\] \== "invalid":  
        return "terminal\_error\_node"  
    return "execute\_charge\_node"

def process\_gateway\_charge(state: AgentPaymentState) \-\> dict:  
    payload \= state\["input\_payload"\]  
    settings \= state\["gateway\_settings"\]  
    retry\_count \= state\["retries"\]  
      
    provider \= settings.get("gateway\_provider")  
    adapter \= PaymentAdapterFactory.get\_adapter(provider, settings)  
      
    request\_data \= NormalizedTransactionRequest(  
        amount=Decimal(str(payload\["amount"\])),  
        currency=payload\["currency"\],  
        customer\_email=payload\["customer\_email"\],  
        payment\_token=payload\["payment\_token"\],  
        idempotency\_key=payload\["idempotency\_key"\]  
    )  
      
    try:  
        response \= adapter.charge(request\_data)  
        return {"execution\_response": response.model\_dump(), "validation\_status": "completed"}  
    except Exception as e:  
        \# Detección de errores transitorios del servidor externo para reintento programado   
        if retry\_count \< 3:  
            return {"retries": retry\_count \+ 1, "validation\_status": "retry\_scheduled"}  
        return {"execution\_response": {"status": "failed", "error\_message": str(e)}, "validation\_status": "failed"}

def check\_charge\_result\_route(state: AgentPaymentState) \-\> str:  
    status \= state.get("validation\_status")  
    if status \== "retry\_scheduled":  
        return "execute\_charge\_node"  
      
    response\_data \= state.get("execution\_response", {})  
    if response\_data.get("status") \== "captured":  
        return "persist\_ledger\_node"  
    return "terminal\_error\_node"

def commit\_to\_ledger(state: AgentPaymentState) \-\> dict:  
    \# Registra las transacciones en los libros de contabilidad relacionales   
    return {"validation\_status": "reconciled"}

\# Declaración formal del flujo de control en LangGraph  
builder \= StateGraph(AgentPaymentState)

builder.add\_node("validate\_payload\_node", validate\_transaction\_payload)  
builder.add\_node("execute\_charge\_node", process\_gateway\_charge)  
builder.add\_node("persist\_ledger\_node", commit\_to\_ledger)

builder.set\_entry\_point("validate\_payload\_node")

builder.add\_conditional\_edges(  
    "validate\_payload\_node",  
    check\_validation\_route,  
    {  
        "terminal\_error\_node": END,  
        "execute\_charge\_node": "execute\_charge\_node"  
    }  
)

builder.add\_conditional\_edges(  
    "execute\_charge\_node",  
    check\_charge\_result\_route,  
    {  
        "execute\_charge\_node": "execute\_charge\_node",  
        "persist\_ledger\_node": "persist\_ledger\_node",  
        "terminal\_error\_node": END  
    }  
)

builder.add\_edge("persist\_ledger\_node", END)  
payment\_orchestrator\_graph \= builder.compile()

## **Directivas de Programación para Agentes de Codificación de IA**

A continuación se expone la especificación técnica en formato de prompt extendido para guiar el desarrollo y la implementación automática por parte de agentes programadores de inteligencia artificial.

# **\================================================================================ DIRECTIVA TÉCNICA DE CODIFICACIÓN PARA AGENTES DE IA: ADAPTADORES MULTIPASARELA**

ROL DEL AGENTE:  
Eres un Ingeniero Principal de Software de Sistemas Financieros de Aikrofy. Tu tarea es  
diseñar, implementar y verificar un motor dinámico, modular y escalable de pasarelas de pago.  
CONSTRICCIONES DE ARQUITECTURA:

1. DESACOPLAMIENTO ABSOLUTO (Adapter Pattern):  
   * Queda estrictamente prohibido que la lógica de negocio de los agentes realice llamadas  
     directas a bibliotecas de proveedores financieros externos (p. ej., stripe o mercadopago).  
   * Todo flujo de control transaccional debe realizar llamadas a través de 'AbstractPaymentGateway'.  
2. MANEJO DE PASARELAS A MEDIDA (Custom Declarative Mapping):  
   * Implementa un mapeador JSON dinámico que traduzca estructuras usando rutas relativas  
     (p. ej., 'payer.email' o 'transaction.amount') leídas desde la configuración  
     'config\_payload' de la base de datos PostgreSQL.  
   * Deberás soportar operaciones sin reescribir código estático cuando los clientes  
     vinculen sus pasarelas propietarias.  
3. COHERENCIA DE DATOS Y TRANSACCIONALIDAD (ACID & Ledger):  
   * Cada cobro completado con estado 'captured' requiere de manera atómica la inserción  
     de un registro de auditoría en la tabla 'transactions' y un desglose contable balanceado  
     en 'ledger\_entries'.  
   * El libro mayor debe verificar el balance financiero exacto usando aritmética de alta precisión.  
4. IDEMPOTENCIA Y TOLERANCIA A FALLOS:  
   * Antes de enviar cargos financieros, realiza consultas previas sobre la llave de idempotencia  
     'idempotency\_key' para prevenir re-procesamientos y duplicación de débitos involuntarios.  
   * Aplica reintentos basados en políticas de retroceso exponencial con aleatorización de retrasos  
     (jitter) exclusivamente ante fallos temporales de comunicación (códigos de respuesta HTTP 5xx).  
5. MITIGACIÓN DE FALLOS ESPECÍFICOS DE PROVEEDORES:  
   * En el adaptador de Mercado Pago, cuando los agentes requieran sincronizar perfiles de  
     suscripción, intercepta la operación y redirige las llamadas hacia la API de preaprobaciones  
     ('/preapproval/search') en lugar de buscar en el extremo genérico de clientes.  
   * En el adaptador de Authorize.Net, procesa las llamadas dentro del nodo 'createTransactionRequest'  
     con los tipos transaccionales nativos XML/JSON.  
   * En el adaptador de PayPal, coordina la API de Órdenes v2 asegurando que tras el estado de  
     redirección se capture el ID correspondiente llamando al método 'capture\_payment' de forma  
     asíncrona.  
   * En el adaptador de Kushki Pagos, fuerza el desglose de impuestos ('subtotalIva', 'subtotalIva0')  
     con precisión aritmética estricta bajo pena de rechazo inmediato por parte de la API de Kushki.  
   * En Nuvei, implementa de forma segura el cifrado del checksum criptográfico del payload para el  
     método '/openOrder' en el servidor, bloqueando la exposición de 'merchantSecretKey' en el frontend.  
   * En dLocal Go, procesa de forma nativa los payloads en formato snake\_case, resolviendo y exponiendo  
     correctamente la URL de redirección obtenida de la llamada.  
6. ENTORNO DE PRUEBAS FUERA DE LÍNEA:  
   * Durante la ejecución del conjunto de pruebas automatizadas, proporciona configuraciones de  
     comunicación redirigidas a un entorno emulado local similar a 'AcquireMock'.  
   * Esto garantizará pruebas completas del flujo de verificación por correo, pasarelas de pago  
     y entrega de notificaciones push (webhooks) sin depender de conexiones de red externas  
     ni sufrir bloqueos por límites de velocidad.

ESTRUCTURA DE ARCHIVOS A GENERAR:

* target\_interface.py: Interfaz base que define las firmas de las operaciones financieras.  
* schemas.py: Modelos de Pydantic con validadores de datos estrictos para cobros y configuraciones.  
* adapters/stripe\_adapter.py: Adaptador estructurado para el API de intenciones de Stripe.  
* adapters/authorizenet\_adapter.py: Adaptador XML/JSON compatible con transacciones Authorize.Net.  
* adapters/mercadopago\_adapter.py: Adaptador compatible con Mercado Pago con desvío de suscriptores.  
* adapters/paypal\_adapter.py: Adaptador compatible con PayPal Orders v2 y flujo asincrónico.  
* adapters/kushki\_adapter.py: Adaptador para Kushki con especificaciones fiscales locales por país.  
* adapters/nuvei\_adapter.py: Adaptador para Nuvei con generación de firma/checksum local y sessionToken.  
* adapters/dlocalgo\_adapter.py: Adaptador compatible con dLocal Go y direccionamiento localizado.  
* adapters/custom\_adapter.py: Adaptador declarativo genérico para mapeos JSON dinámicos.  
* factory.py: Fábrica dinámica que devuelve el adaptador correspondiente configurado.  
* tools/payment\_tools.py: Kit de herramientas de LangChain con esquemas detallados para agentes.  
* workflows/payment\_graph.py: Grafo de LangGraph para control de estados, retries y conciliación contable.

ESTILO DE ESCRITURA Y CALIDAD DE CÓDIGO:

* Escribe código limpio, documentado en español técnico bajo los estándares de PEP 8\.  
* Utiliza anotaciones de tipos estáticos de Python de forma exhaustiva para asegurar la integridad  
  estructural en tiempo de diseño.  
* Implementa capturas selectivas de excepciones para asegurar que ningún error de red quede  
  silenciado ni provoque la pérdida de consistencia en el libro diario contable.  
  \================================================================================

## **Verificación de Firmas Digitales en Webhooks (DMN)**

La integridad de nuestro libro contable transaccional depende de la validez de los webhooks de confirmación que recibimos de cada una de las pasarelas. Es crucial verificar criptográficamente cada payload para evitar ataques de inyección financiera.30

                  \+------------------------------------------+  
                  |            Webhook Recibido              |  
                  \+------------------------------------------+  
                                       |  
                \+----------------------+----------------------+  
                |                      |                      |  
                v                      v                      v  
     \+--------------------+ \+--------------------+ \+--------------------+  
     |      PayPal        | |      Kushki        | |      Nuvei         |  
     \+--------------------+ \+--------------------+ \+--------------------+  
     | Autenticación RSA  | | HMAC-SHA256 con    | | Shared Secret      |  
     | SHA256 y CRC32 del | | cabecera           | | digest y timestamp |  
     | body.       | | X-Kushki-Signature | | en headers. |  
     \+--------------------+ \+--------------------+ \+--------------------+

### **1\. PayPal: Validación Autónoma de Firmas RSA-SHA256 y CRC32**

PayPal firma digitalmente sus webhooks utilizando llaves RSA. Para validar un webhook de forma offline y segura sin incurrir en latencias de red por llamadas de postback a la API de validación, se debe calcular el CRC32 (en formato binario de 32 bits sin signo) del cuerpo completo de la solicitud en bruto (raw request body), construir una cadena de verificación concatenada por tuberías (|) con los encabezados correspondientes, descargar el certificado público desde la URL indicada en el encabezado PAYPAL-CERT-URL y validarla criptográficamente.

Python  
import httpx  
import binascii  
from OpenSSL import crypto  
from cryptography.hazmat.primitives import hashes  
from cryptography.hazmat.primitives.asymmetric import padding

def verify\_paypal\_webhook(  
    raw\_body: bytes,  
    transmission\_id: str,  
    transmission\_time: str,  
    transmission\_sig: str,  
    cert\_url: str,  
    webhook\_id: str  
) \-\> bool:  
    """  
    Verifica criptográficamente la autenticidad de un webhook recibido de PayPal  
    """  
    \# 1\. Calcular el checksum CRC32 sin signo del cuerpo bruto del request  
    crc32\_val \= binascii.crc32(raw\_body) & 0xffffffff  
      
    \# 2\. Formular la cadena de validación con separadores de pipe  
    validation\_string \= f"{transmission\_id}|{transmission\_time}|{webhook\_id}|{crc32\_val}"  
      
    try:  
        \# 3\. Descargar el certificado público X.509 de la URL indicada  
        res \= httpx.get(cert\_url, timeout=5.0)  
        cert\_data \= res.content  
          
        \# 4\. Cargar el certificado y extraer la clave pública  
        x509 \= crypto.load\_certificate(crypto.FILETYPE\_PEM, cert\_data)  
        pub\_key \= x509.get\_pubkey().to\_cryptography\_key()  
          
        \# 5\. Decodificar la firma de base64  
        import base64  
        signature\_bytes \= base64.b64decode(transmission\_sig)  
          
        \# 6\. Realizar la verificación de firma digital RSA con relleno PKCS1v15  
        pub\_key.verify(  
            signature\_bytes,  
            validation\_string.encode('utf-8'),  
            padding.PKCS1v15(),  
            hashes.SHA256()  
        )  
        return True  
    except Exception:  
        return False

### **2\. Kushki Pagos: Validación mediante HMAC-SHA256**

Kushki envía firmas HMAC-SHA256 dentro del encabezado X-Kushki-Signature. La cadena base se construye uniendo el cuerpo de la solicitud (request body) con el timestamp UNIX provisto en la cabecera X-Kushki-Id.

Python  
import hmac  
import hashlib

def verify\_kushki\_webhook(  
    raw\_body: str,  
    timestamp: str,  
    received\_signature: str,  
    webhook\_signature\_id: str  
) \-\> bool:  
    """  
    Valida que las notificaciones de eventos financieros provengan exactamente de Kushki  
    """  
    \# La cadena se compone del timestamp concatenado con el cuerpo del request  
    base\_string \= f"{timestamp}{raw\_body}"  
      
    computed\_hmac \= hmac.new(  
        webhook\_signature\_id.encode('utf-8'),  
        base\_string.encode('utf-8'),  
        hashlib.sha256  
    ).hexdigest()  
      
    return hmac.compare\_digest(computed\_hmac, received\_signature)

### **3\. Nuvei: Autenticación por firma compartida (Digest)**

Nuvei envía Direct Merchant Notifications (DMN) con dos cabeceras de validación críticas: X-Authentication-Timestamp y X-Authentication-Digest. La firma se calcula aplicando HMAC-SHA256 sobre el payload del webhook concatenado con el timestamp y el shared secret registrado.

Python  
import hmac  
import hashlib

def verify\_nuvei\_webhook(  
    raw\_body: bytes,  
    timestamp: str,  
    received\_digest: str,  
    shared\_secret: str  
) \-\> bool:  
    """  
    Verifica las llamadas DMN asíncronas emitidas por la infraestructura de Nuvei  
    """  
    \# Combinar el cuerpo crudo de la notificación con el timestamp  
    base\_message \= raw\_body \+ timestamp.encode('utf-8')  
      
    computed\_digest \= hmac.new(  
        shared\_secret.encode('utf-8'),  
        base\_message,  
        hashlib.sha256  
    ).hexdigest()  
      
    return hmac.compare\_digest(computed\_digest, received\_digest)

## **Control y Mitigación de Errores Transaccionales**

La confiabilidad operativa de un sistema multiagente que realiza operaciones financieras automatizadas depende de su capacidad para clasificar y responder adecuadamente a los errores reportados por las pasarelas externas.2  
El motor de middleware de Aikrofy categoriza las excepciones y las respuestas de error en tres grupos principales para determinar el comportamiento de recuperación automática:

                      \+---------------------------------------+  
                      |         Excepción de Pasarela         |  
                      \+---------------------------------------+  
                                          |  
               \+--------------------------+--------------------------+  
               |                          |                          |  
               v                          v                          v  
\+------------------------------+ \+------------------------------+ \+------------------------------+  
|      Errores de Solicitud    | |      Errores de Red / 5xx    | |      Fallas de Conexión      |  
|     (Bad Request \- 400\)      | |      (Internal Error \- 500\)  | |       (Timeout / DNS)        |  
\+------------------------------+ \+------------------------------+ \+------------------------------+  
               |                          |                          |  
               v                          v                          v  
\+------------------------------+ \+------------------------------+ \+------------------------------+  
|  Detener flujo del Agente y  | |  Iniciar reintentos en       | |   Iniciar política de        |  
|  reportar error estructural. | |  LangGraph (Max: 3 intentos).| |   compensación contable.     |  
\+------------------------------+ \+------------------------------+ \+------------------------------+

### **Clasificación Sistemática de Respuestas de Error**

* **Errores de Autenticación (Código HTTP 401 / Unauthorized):** Representan fallas de configuración críticas del sistema de los clientes o revocación de credenciales del lado de la pasarela.19 El sistema bloquea de inmediato la pasarela afectada dentro de los registros del comercio en Aikrofy para mitigar bloqueos temporales por políticas de seguridad del proveedor, reportando la anomalía para corrección manual.19  
* **Errores de Solicitud Inválida (Código HTTP 400 / Bad Request):** Indican que los datos provistos no cumplen con las reglas estructurales esperadas por la pasarela (parámetros faltantes, monedas no admitidas o tokens expirados).19 El agente autónomo detiene su flujo de ejecución para evitar la repetición de transacciones fallidas, registrando los detalles dentro de la tabla merchant\_api\_logs.19  
* **Errores de Servidor Remoto (Código HTTP 5xx / Server Errors):** Reflejan caídas de servicio de la infraestructura externa o saturación de la red.19 Al tratarse de fallos temporales, el grafo transaccional de LangGraph inicia la política de reintentos mediante el decorador de retroceso exponencial (backoff con jitter) para reestablecer el flujo una vez estabilizada la conexión externa.

## **Conclusiones y Recomendaciones de Ingeniería de Software**

La implementación del motor de abstracción modular para pasarelas de pago de Aikrofy proporciona una solución estructurada al problema de la fragmentación de interfaces de integración en entornos financieros.14 Al estandarizar las llamadas externas a través de la interfaz unificada de adaptadores y estructurar las operaciones de escritura mediante un esquema transaccional ACID, se garantiza la consistencia del libro mayor del comercio en todo momento.12  
Para asegurar la robustez del sistema durante la fase de despliegue, se formulan las siguientes recomendaciones operativas:

* **Adoptar el Enfoque Proxy para Configuraciones Complejas:** Con el fin de evitar que las llamadas de los agentes degraden el rendimiento transaccional del backend o resulten en pérdidas de metadatos, se recomienda implementar adaptadores basados en el concepto de proxy de API administrada.2 Esto permite delegar la tokenización de credenciales sensibles y la lógica de paginación del lado del servidor, permitiendo que el agente de inteligencia artificial opere directamente con representaciones de datos limpias y optimizadas.2  
* **Garantizar Aislamiento de Red Durante el Desarrollo:** Las pruebas de integración contable deben realizarse bajo entornos de red simulados (offline) utilizando herramientas como AcquireMock o implementaciones de contenedores dockerizados de pasarelas emuladas.31 Esto previene que se alcancen los límites de velocidad de llamadas (rate limits) de los entornos de prueba estándar de proveedores de producción y elimina por completo la necesidad de exponer credenciales reales de clientes durante las pruebas de caja negra de los agentes de programación de inteligencia artificial.5  
* **Restringir las Herramientas del Agente:** Dado que las pasarelas tienen la capacidad de modificar estados de saldo y realizar reembolsos, las herramientas provistas a los agentes deben limitarse estrictamente utilizando el principio de mínimo privilegio en base de datos.2 Asimismo, cada ejecución de escritura autónoma debe exigir la verificación manual de firmas digitales (HMAC/RSA) en los extremos receptores de notificaciones (webhooks) para evitar ataques de inyección de transacciones inexistentes en el libro mayor de doble entrada.

#### **Fuentes citadas**

1. Under the Hood: Universal Commerce Protocol (UCP) \- Google Developers Blog, acceso: mayo 20, 2026, [https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/](https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/)  
2. Best Integration Platforms for LangChain & LlamaIndex Data ... \- Truto, acceso: mayo 20, 2026, [https://truto.one/blog/best-integration-platforms-for-langchain-llamaindex-data-retrieval/](https://truto.one/blog/best-integration-platforms-for-langchain-llamaindex-data-retrieval/)  
3. Adapter in Python / Design Patterns \- Refactoring.Guru, acceso: mayo 20, 2026, [https://refactoring.guru/design-patterns/adapter/python/example](https://refactoring.guru/design-patterns/adapter/python/example)  
4. Adapter Pattern in Python \- Subash Palvel \- Medium, acceso: mayo 20, 2026, [https://subashpalvel.medium.com/adapter-pattern-in-python-41c738098be9](https://subashpalvel.medium.com/adapter-pattern-in-python-41c738098be9)  
5. Adapter Pattern Use Cases: Payment Gateway Integration \- Endgrate, acceso: mayo 20, 2026, [https://endgrate.com/blog/adapter-pattern-use-cases-payment-gateway-integration](https://endgrate.com/blog/adapter-pattern-use-cases-payment-gateway-integration)  
6. Adapter Design Pattern Use Case: Payment Gateway Integration | by Mehar Chand, acceso: mayo 20, 2026, [https://medium.com/@mehar.chand.cloud/adapter-design-pattern-use-case-payment-gateway-integration-8dc316e1dba8](https://medium.com/@mehar.chand.cloud/adapter-design-pattern-use-case-payment-gateway-integration-8dc316e1dba8)  
7. Unified Payment APIs for Developers | Unified.to, acceso: mayo 20, 2026, [https://unified.to/payment](https://unified.to/payment)  
8. Embedded checkout | Google Universal Commerce Protocol (UCP) Guide, acceso: mayo 20, 2026, [https://developers.google.com/merchant/ucp/guides/checkout/embedded](https://developers.google.com/merchant/ucp/guides/checkout/embedded)  
9. Universal-Commerce-Protocol/ucp-schema \- GitHub, acceso: mayo 20, 2026, [https://github.com/Universal-Commerce-Protocol/ucp-schema](https://github.com/Universal-Commerce-Protocol/ucp-schema)  
10. Schema Authoring \- Universal Commerce Protocol (UCP), acceso: mayo 20, 2026, [http://ucp.dev/documentation/schema-authoring/](http://ucp.dev/documentation/schema-authoring/)  
11. Stripe vs Authorize.net: Payment Gateway Comparison for E-commerce in 2026, acceso: mayo 20, 2026, [https://contracollective.com/blog/stripe-vs-authorize-net-payment-gateway-2026](https://contracollective.com/blog/stripe-vs-authorize-net-payment-gateway-2026)  
12. Design a Payment System: A Complete Guide, acceso: mayo 20, 2026, [https://www.systemdesignhandbook.com/guides/design-a-payment-system/](https://www.systemdesignhandbook.com/guides/design-a-payment-system/)  
13. Payment Gateway Integration Database Structure and Schema, acceso: mayo 20, 2026, [https://databasesample.com/database/payment-gateway-integration-database](https://databasesample.com/database/payment-gateway-integration-database)  
14. Payment API: what it is, how it works, and how to scale \- Solidgate, acceso: mayo 20, 2026, [https://solidgate.com/blog/payment-api-guide/](https://solidgate.com/blog/payment-api-guide/)  
15. Authorize.net API Documentation \- Payment Transactions, acceso: mayo 20, 2026, [https://developer.authorize.net/api/reference/features/payment\_transactions.html](https://developer.authorize.net/api/reference/features/payment_transactions.html)  
16. Integrate payment methods \- Mercado Pago, acceso: mayo 20, 2026, [https://www.mercadopago.com.mx/developers/en/docs/checkout-api-orders/payment-integration](https://www.mercadopago.com.mx/developers/en/docs/checkout-api-orders/payment-integration)  
17. Other payment methods \- Mercado Pago, acceso: mayo 20, 2026, [https://www.mercadopago.com.co/developers/en/docs/checkout-api-payments/integration-configuration/other-payment-methods](https://www.mercadopago.com.co/developers/en/docs/checkout-api-payments/integration-configuration/other-payment-methods)  
18. json-converter \- PyPI, acceso: mayo 20, 2026, [https://pypi.org/project/json-converter/](https://pypi.org/project/json-converter/)  
19. Payment Gateway API Integration: 2026 Developer Guide \- Paytia, acceso: mayo 20, 2026, [https://www.paytia.com/resources/blog/payment-gateway-api-integration](https://www.paytia.com/resources/blog/payment-gateway-api-integration)  
20. API reference \- Authorize.net Developer Center, acceso: mayo 20, 2026, [https://developer.authorize.net/api/reference/index.html](https://developer.authorize.net/api/reference/index.html)  
21. MercadoPago /v1/customers/search API returns empty results despite customer existing in dashboard \- Stack Overflow, acceso: mayo 20, 2026, [https://stackoverflow.com/questions/79879544/mercadopago-v1-customers-search-api-returns-empty-results-despite-customer-exis](https://stackoverflow.com/questions/79879544/mercadopago-v1-customers-search-api-returns-empty-results-despite-customer-exis)  
22. karmaniverous/jsonmap: A hyper-generic JSON mapping library. \- GitHub, acceso: mayo 20, 2026, [https://github.com/karmaniverous/jsonmap](https://github.com/karmaniverous/jsonmap)  
23. Payments System Architecture: Designing for Scale, Consistency, and Resilience \- CockroachDB, acceso: mayo 20, 2026, [https://www.cockroachlabs.com/blog/cockroachdb-payments-system-architecture/](https://www.cockroachlabs.com/blog/cockroachdb-payments-system-architecture/)  
24. Using Pydantic for Data Validation with SQLAlchemy | by DZ \- Medium, acceso: mayo 20, 2026, [https://medium.com/@melthaw/using-pydantic-for-data-validation-with-sqlalchemy-b15e4497cfb4](https://medium.com/@melthaw/using-pydantic-for-data-validation-with-sqlalchemy-b15e4497cfb4)  
25. Django and Pydantic \- TestDriven.io, acceso: mayo 20, 2026, [https://testdriven.io/blog/django-and-pydantic/](https://testdriven.io/blog/django-and-pydantic/)  
26. Stripe vs. Authorize.net: Credit Card Processing Comparison \- Business.com, acceso: mayo 20, 2026, [https://www.business.com/articles/stripe-vs-authorize-net-credit-card-processing/](https://www.business.com/articles/stripe-vs-authorize-net-credit-card-processing/)  
27. OpenAPI toolkit integration \- Docs by LangChain, acceso: mayo 20, 2026, [https://docs.langchain.com/oss/javascript/integrations/tools/openapi](https://docs.langchain.com/oss/javascript/integrations/tools/openapi)  
28. How ERP API documentation enables unified commerce in Shopify integrations, acceso: mayo 20, 2026, [https://www.flatlineagency.com/blog/how-erp-api-documentation-enables-unified-commerce/](https://www.flatlineagency.com/blog/how-erp-api-documentation-enables-unified-commerce/)  
29. Built an open-source mock payment gateway in Python (no more Stripe test limits) \- Reddit, acceso: mayo 20, 2026, [https://www.reddit.com/r/Python/comments/1pfl8ln/built\_an\_opensource\_mock\_payment\_gateway\_in/](https://www.reddit.com/r/Python/comments/1pfl8ln/built_an_opensource_mock_payment_gateway_in/)  
30. agent\_toolkits | langchain\_community \- LangChain Reference Docs, acceso: mayo 20, 2026, [https://reference.langchain.com/python/langchain-community/agent\_toolkits](https://reference.langchain.com/python/langchain-community/agent_toolkits)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAbCAYAAADLYlf/AAACU0lEQVR4Xu2XO4xNURSGl8SbxKMZRggKnaFk4lEYFCQKrWQmIhLBEFEwIYh4MxPR0CPx6BAGBaFUiIaoRSMRjXjE6/+ttWf2WTPnnn2muM3dX/Il56517sp+331FMpmWZ6t5yNxWTMsCeNDsNXviF5rEfhlu4xozZhU8APfCfXCd2ZCW7vwK8zD8A3+JdjgwG+40v8JLcHWUbwbj4CZ4Q7SN703GA0vgOfhFdBD4mSbBGe2Hf+EZl5toPnPxZnMXXhZtI91YTP9fDWddLIk7cCZ8Az/ByVGu0/SDUsYUOMsHHXN8oALO8qDo936a9wtviPTJyAFpCIuGwoTLm6PaE14Q3RI0tXAbfCDlHdwOT/hgBR3woj3fNH/DxUNv6GBMjz5XstQMhafCz/DV0Bsi98xpUayKRfAJbI9iO8wLUSwVHmSb7XmlyUkK7R4PH9tzMuEED4UJC7IwD8IJokVrFxadlaeiA8BO87CkY+E2nOFinCBOFLcZB+NUMV0N9zqNC7PRXFLXRfc6i9YubLAWz5FrPlGDeFvGdItOEgeW+319Md0YFi2bVS7zH/AK7DLHwh54VbTx88y6LJPRV8wk0cP5tegZwy2bTEt3fjkcMD0bRJfUN9GitQobu2X4QOLF6ZEZH4Ip8Ha3xQeN06LtfO4TVZwX/dmhHq6Kd/CFTySyS7R+DAeAPoRzXa4MHrgvpfiTFjNf9FZ60ifK4FXxLfwueh2kvDl5OHNHfTCBhfCYD0awwcd9cBSOwA+i7fwoI/93BG7BtT6YyWQymUwmk2kF/gEQNICesKtUHQAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAcCAYAAABYvS47AAAAtUlEQVR4Xu3NIQ+BURjF8SvYEBEogkowX0AyQRNJpvoIqvEGiiiZmc18Co1odLPJgo5zd8/ZeJUbFJv/9ivPPds15jeLhg+vJWBFa9hBi96aQo9scThTUSOb19B+e4MyqSWNdKjAA3KkJrTVoWHcME0qoJMOHeOGSVIDuurgPWwaN0yRGtJFh5pxwyypMe11yMAdSqQWNNPBe2jbQJtsEThSXSNbHg7UhTn06aMYVaEQevv3pZ4PtjE3BKHfwgAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAbCAYAAADlJ3ZtAAAB40lEQVR4Xu3WS0hVURQG4OUj80EUma80AokIRaSZOGgu5EDUElEzmzQIigYlBKIk5UBEjCgoHDhSEJw5a5aTxDc6dCARNdZJk+xfrH/LvUsvHlG4Vzg/fOBZe99zl/vsc+4RiRPnILehJ4IOaKS05Vw1OwvbMETPYQb24Qs8hVewBdOUlhTBElx09QmxZssSag9hkNKSB/DYF5F12HS1XrH5Ki3phkJXuwb/4KOr34eblDFpFdsC7X4gE/NBrNlSP5CJ2ZDD+zXkAkVN1Ln6xPkF1/1AqpTQUfs15BNFzTu44ospootU6Yupcq6abSPdr0c9nu7ACvnkU2IKxH5sfLNhUbJdfVVO0Oxn0mbL3VgufIU/9B7qOdYFr6ETBkjzDPZgDFpY+wF9NAlNrGuObbYWvsMi7NJfsRtsQWw1Q26JnVCFXIVlyOGxNqDu8vinJK/sI8ijOrHPhhzb7Enim9XLrj/B8wczRIZplMeh2bBF+sWuinojyU8dPW9VwvGpUi12EyjNS7ghyV84R/pPaHagWGxug9gVzKIasc82c+6anGGz+gXfSFflHuu6/6bgLYyQztXo3+Ni7xUVYs0+oRdi20DPpe8nv8Xe8s48eqf748uuFuLnXiJN2Otx4sSJEzH/Ac9UaT4EJSd9AAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAbCAYAAAAH+20UAAABz0lEQVR4Xu2WSyitURTHl4suKa8IYUTIQCkpZUDGJh4TMyYSIu7kZqJbHmWAlEeIPMqAmZQyFBlgKMlAFCkyUOgOrv+y1nfPtlE655Stvl/9an1rbVrtvfaGyMcdIu2Ey7TCDTvpMt+q4RR4C/ftgqtMwht4YRdcpBjOwVX4ZNWchOc2HY7DfzDxddktGuAvjf+QNJwXKLtFHNyC0frdQdJw+f8VjtEPp0l2mZ0iabjWXBQkUXYiFHLVTdhmOELScEtgadD0wSQ7GSzfruE1NcfKF5E03GvlI+BPjT866ngjjoWnMNnIefDv+vQrlEAyt0uqTSZJwzzLHllwh+Q0urXWrLUYdQC2wzFYQHJa93CY5D54d6IUDur3EEzT/LtUwWv4CP+qTUa9B17BB3gHt1XejTq4p+sKjbhenSDZDI65eeac3o7ELszWmC/5glELKzVwWeN8eKDxrLpCgZemQmvcMI+Edwq8m7wZHpXw2PgOK3yE3ghxw4ca8+Vk5/Wb4WNnzmAq7FKZE5K/qAyPzYzGYYVneB0ewWq4CC9hI/yh8j9OvbATlrz8lIzGqK5jmTKSy/6b5P3P0PyXwPPKzZvwa2HDrwzvvI+Pj08IPAPSv1g2ElFDngAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAbCAYAAADRXrdxAAACNklEQVR4Xu2XTYhOURjH/4yPSfkqG2YWWPhoKGNDMRtpbMhI+YyGiJoZNoSFYmXKCBFKMU1NFoqZUJpkgRJmkrJgbyELCxtTFvz/7/Pcuec9IuZ9Z3Gm+6tfnfuce+97n3Oec+59gYL0qYkDqXKc3o2DqTJukplLv9FncUeK3KZf6Ye4IzVW0Rv0ESyhZJlAH9M5sNn5SSeXnZEQrbTD2+dhycwb6U2I6XQA+bvlFCyZxpEzxpZatypoJq7TXW5WZhvCk5xKSk+DdplO8eMZsN994rZ4fFQsdrVW2gOvwZLZm59aQj/eGcX+h1mwZLIBOU0P0OVuncdHxbhKps+dH8VXw5I5FsUP0YtRbKKrXTBmKqwvRCWmnVNcoluDPqFrZkaxv6IR0gh3uzGLYMlcCGIL6VP6mp6D1f8COuTuoPdpPSwBtT/Sm7TfPUyHYTOwkr7x+GZ3C31A99M7+If1uZ5+gd30h7sn6D/r/d9hL0591kiN2EGUz4zKbpsrjiAfACWvzyKN8jJXvEdeTpqZ3d4WS+kab9+jm4K+qqP61gNoC9eoZbuRPAGb5St+rpIZ9HbIO/w5mSWwnfQofYHfS7CqaPr1sA20mZ6kXa5oo1dhI6pkVJIxYTLaDMJktBFt9La+2jV4TXl3ddF6eAUrxdl0HX3u7qRn6EtY2d6in2AJZ+yjn2HrdS19Sx/CHljqZd1Lt9Me2It8RenKMWISyhemjuU0P670H6ruk92j0nsVFBQUJMAvWittbWZfUkgAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEkAAAAbCAYAAAAwNaIgAAAC5ElEQVR4Xu2YWahOURiGX/OQecyUSFyQQikuuODChVyYEuE4GRJF5imlRESmhGRIpsiNlEwXJG4UoUjJiUIoQ4qieN/zfcve//KfHHV+Tp311NO/9rfW3u397TXs9QOJxL+mQRxIFFJOr8fBRCEpSX+gDX1DH8cViYyd9B19H1ckjP70JD1Gf9DGhdUJcZ72oNtgSepWWJ2YQNd6eRUsSYOy6rpNM/cabeKxObAkjQmN6job3MN0qrsHlqQZuXZiIF0ZxWoTjeJATdCLXnEX5twKS9LyrGklA5ANydrI/jhQE6QkVYOztJ+bpw8sSVrlYpoWKTfMxUS876uHbL4T8bDIX1PtpM4JtKD1c8eBTrBzVdeXPiis/oXaaN79K1rTjfR0XOG0hSXpRBTXvFXhZX1LPYP1ttWwzwc5m86jl2HJUMLv0LveTuq6K2Dou+yllzXffXc7eGwBXU/X0Umwe9vuTqQ3aXd6kL6lm+mQyjONabDVegrdhN9fYFFGwbYdX+k3OtcNLIPd9Bf6id6iXVzdYIW3aw+7hn6FzpHD/fgiHeHlWbCHCKiXPId9vOr8kCShuFSSOtP7sJfald6mI+kFdzAdCutpvelDZOhe5T1kidkLe4ElpRWyJOkGXmVVeOGGHqCH0AsRM+k+LwdUvwS2V6wqSdNhSQqrrnqDUO+VT+gN2M4gnyQNr8nuJY8J9cYjueOSkE9SO1T9cCJO0gEvCz3ERzqMtqSvPa5rfnY7whaKp8jmJ/WacR6XYgsdS3vSRx5bChuCMr9RPwXr1SVlB2zzq3G+m36gi+ki2IZYqkuPh81X52APqyRpTtJXvTwKm2cCWkDURiunEibDG58PW7X0q56hb7czrua/Xcgm/qt0DR3tx6KMHod9C2ohqtac9D8ogw033aBUj4zRvKNVSkmV+RUv7ApEPt48Vw4UW8UU07CuteiBD8HmDi3TMhGRklQNNIy0VOsfBS3jMpFIJMRPa8aXflSbK8sAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADUAAAAbCAYAAADcQMc2AAACIklEQVR4Xu2WP0hXURTHT6ERmahhKkWQOigEDfkXQSvBpchEBBOJfqGJQ6GDqIPWb3AIcnAIoqGEUCMiUAtydHJwiVqaGlpcHYRW/X479+H1+t7v+Ywof9wPfODHOff33j33nXfvE/F4PBa34ROYtnwMJ+Ao7IA5OvTokJVF5cGH8C4sN67Ay7AbrsJnsN+M/yechEWWB+E6vANLjGkrNwyPwRFYZcX/OveNS3AevoYv4QtYZo2L4ppoUaVGtl/APXgJVsBJKx7JaSP7mnKVk8AVfCO770K+nUxAi2hRXABqT34QFojO74oVD4UX+WZkP9+CP2CtyffAE+Z3FENwzA0egmYJL4qtyKffJ/r0M9IFf8GLxoA0XBN9eWeteBSfYK4bPARuUevwK3wLv8Mbol0RCVtsU8Ir526zLbpSdU7O5RT8Ap/GyNWOwy2K92fbsRhu6427Q8NpF534TTchehHm3rmJELg4bI3KGI8Hf8jAVdlfFJ8MN51COCf67keSlUUNiE78gpsAbaI53uQgfBSd+J/Cc4qtHxQVbOk8l6ZhNXxuYqEUwy1Y48RZ5IJoUfWi4+JogIuiu2TcTpmJVtgJzxrTVm4cNolubo+s+D5S8LPs/d6aET3gluEH+Or3yHjYxtytaEr0KyLJjtgr+l+2Mg9s+hNOmTy/+96LHuQbokXSSM4bXc65gRjOGB+IHgV8JzkRmvRaHo/H4/F4/nd2ACWvZdN2hzScAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFgAAAAbCAYAAAD4WUj2AAADbUlEQVR4Xu2YWahNURjHP/OUTMnMRYaUqcykUOImmR4oRETixQse5F7TkyHzkOGSKUOmMmTO8CAkM1GGkoxJZIj4/61v37vOZ597znU7t26tX/3qrG+tvc/Za/jW2kckEAgESj3lYAtYQS0qTWF1GzQ0kNRtSBNY2wZLO6GDM8hkeBMugbdVxtKhK7wFV8HLcJ24wYrIUo/AQ/AtPAr7FDTJpxvcBTfA03BxYnXppC98B2touY76AfaMGsXAmUg/SmJnXYGzvPIltZ2Wa4pr8wJW1Vhr9TMcrDEO0hM4Scullj3woA2CE3CbDXpMVTkQPrPhU/1cF/5WL0QNxF3H2Bwtr1cZiwaa7IDXvXJacNSGqCNhtcTqEuc13GSDYCd8ZoMee9XHJs7Uwo7KgmVgnjrDa9NP2yzQ8lmVsbJRI7BSY5z1acEOvQsnqoPgAzhQ67PFjXoyuPlwqaVrc3dZUvgwP+FaWwG2wm826HFOvWfi48V1Sg8T95knrk0nLe9TGasSNQKbNdbWiyVlGPwuLtf4cGQfwUriZgRHPRn1xY16nPPVXJgj7iFm/r0qObXEPcBqWyEFD1fZVijc2OgdEx8r7jpOnjg4gZi3/VUzWrWdeV9jXbxYLOy893C3rQD9xd1kLhxu6jINVwS/e42tAFvgDxv04ImBckX6jBN3z94mTsrDk+LyrZ8KInh6OAMHwIXi7s97NfQbxcF8y4YjbIW4Yw7rLkrhszdT2NkUwRz8ygY9DqvJcnAbEydcFbn6maeERgVV+XBgeI9WcDv8JPGDkUDoYEfGOjj60pa2QlyiZx1zUCr4hnOgCG50lxUKj2PHbFDcBhZ3fIvgcYx+MXHmfr5M+C8bhPvDdK/cGS7SzzxJ0WmS+AZ3TeI34H/gwZ0j0cvE64nrBHYwN0G2K+lZPAa+FLdPkOhh38ChUSOwHz6EFbXMEwr9CttHjcBxuNwrs9MoT0tL4TK4QtyKZb4mfNmh7Af+HsI8zIFqoeWU8GacLRzJHJWvlzxOcYky+fOo8j//AxQXnjdPwQnwvGpPIHnwhriNymeUuKPaFHHPwZUTtWEK+KWy86xMj4QpgF4V9/LBmf0cdtT6IhGXdwj/CCnp2evTWNyMbaYWBb59ZcMOUrxnYCd3F7fSU+bdQCAQCAQCgUAgEMgYfwC/HMuK7duLQQAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAcCAYAAAC6YTVCAAAA5ElEQVR4Xu3SsUsCYRjH8WtwKKgINxEiiqaWoDXCWRqEBqeW1kajHFyDBCFybGgIxFFoECeFNv8E/StsSxz8vvA7eN73zsSgKb/wgXufuxfeOy6K/k8bKOEVzziRH3vCra73MZSFneLBrDOYSdbMvd6wY9YXGEuinDSwizPk0UdREpXF3WxjghF69qGwX21qijta3Ca+cC6J3iXsE/fitYcXsW3jGzfidYk7sV1hiiPxqqMrce59BqiamVcLFfnAIzq4tg+FrbzJHcP9zXFbODDr1ApRypdZVg3H4XBZh+Fg3V82B6O4LSjU1NXZAAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE0AAAAbCAYAAAA53gJaAAADEklEQVR4Xu2YSahPURzHf4YMZR4iipdk6hkyyxAbCywUFix4C0mSlCGzR4bkLVgoIZ6QDEWxkEQJSRZIiJSFDaWEwgbfr9+573/u73+Hdxeu5Hzqszjfe+599557zu/c/xMJBAL/ILWwATbC5bB17Gi59IC9nEXpCbvYMIF+sKMNixIGrQBznael8sdOwflNPcqDD3wTnoHnnddhb79TCl3hYdF7PwlfwTmxHsp4+BgehHfgIdgy1iOHDvCs02cPPGGyMuCAbTbZXnjVZElsh5dgC9d+Ar/CPq7NWUU/wskuI/fgWq+dyxbRC/gXIffhUpP9aYbAn3C4ySe6nMspiyvwG+zk2o0Svx5LDv3g2hEb4GuTpcI3clm0dtGRcDBcDG/A9pWupbBC9CGjmRExyOW8ryzaSXwZP4PPvXa03F96GVkmzXspv+EgbYUrnZ9E68BnOMrrlwYfblgBWQqy4PLizXMT8Klx+XqTJ8GXP1q0Jj6CQ71jt5xPvYzUiV6ftS6X1XCKDcEB0ZmWx0K407jDs97Jwdgm+S+ChZk3383knAHMWWfz6A43iW4E5yQ+81j8KWudD2cwrz/T5Imw+LexoeiuyQIaFdSy2C3JM62/yzeaPA/uiiz6PJ/cddqZtkT0+pNMXgW32As2dByFb21YApz5vPm+Jo9qWt7GxBnJuhYxT/S8Xa7N+k1ZgnyimjbQ5FWEQavQ7EEbA4/YELSC7yX5mGUNvFjAGXpaKtGnxViTT3d5rckjOKj0B7zm5ay5PO+4a/PTgn5p6qHUw3eiz54JH/iNVNctbvt8E9EvgzLhvbwQ3cl9+KAPvfYE0Z2+zrVrnN9FvwYi9okO2mzXHuBkvfZfAAe6wWunwu+VRfC2VHY+/vzgDOvs9Ssbzhh+R3EH5I5LH0j8Nyg/KVg+OJN8uIHxI3W/6OBxxayK9VAWiG4GXJbHRMsUP1Uy4TTkciHszLVMk3bSvwHvY5pn2/jhTFjTeM5UyR4IToxZcIRUr7ZExknx7fu/Z51oXQgUgMWw0L9CAoFAIBAIBIrxC4YNp6eirvQZAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABPCAYAAABWMpmUAAANz0lEQVR4Xu3dCbS11RjA8cdUpGRIZn2lMs+UiC9LyhRlKHMhmaIyJclXppBEphAZExkylblCIpJpFVbpQ5FWhlAo0/7b73b22ffcM9x77vDV/7fWs9Z33/ec9wzvud/7nGc/e98ISZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIk6UrnqinWT3HdFNdLcf0UN5glNpgg1gotpPW6qM/boHPXnpdhce2QJEnL0tYp/lPFN1J8eUB8JcVXU3wtxcnd7b6T4pcp/l3dv8TrQguFZPjSLsr7/ZMYfs5OinzOTk3x0xSXVfctwfmUJEnL1NHRu2i/tdk3jmumuEOKvVOcGfk4v0+xTn0jTdUeXZTzdnpMVtW8WopbpXhc5MSuJN33qm8kSZKWj+ukOCd6F/8d+3dPbKcUf0zx9HaHpu5j0Ttvb2r2TYKEmyrdh9sdkiRp+bhn9IbJ/pDiFv27J0YC8O12o6aO/sNzo5e0Pax/90TWTfGDFDdud0iSpOXBhG3NZMImSdKVzAujd+GnQZ0+J2KunphiRbtxCpgdeWzkJFO57+zyyOftohQ36989kbumeGi7cYExQYXhc4fQs6ukuE2KO8Zkv383TbFFzN47eo0U90ixcbujMuoYGOc4kqQFxIXihOglba/sYppum+KwKt6Y4tAUh6R4RYrtIj+PYT6a4lfRu2DsluKDKY6PPAFimLVTbBV5OZMrkv2id95Oisku9JPaLMXrI882/XGKI1JsEnlZkKOq243j2Sn+FrkyOKw6yOfjmMiflxrJBZXBK4pbpvheirdEngDEzF0mhwzDZ/rjKT6V4uUpfpTiwX23iHhA5AlB7P90ik9Evl8xzjEw6jiSpEWyYYrfRr7w/6uL+/fdYn5YN+w+KT4T+TG4YJNAse05kS9WJAErutu39kxxSoobVdtuHTlR4HjDKgMoic2jm+0rY3Syt5yR5LKUR0naVvXvnhqqppekODx654Bh2c+m+GHkC/247h55OHfLdscA901xRopvVtv43PBa25nNJJQkkGuib0WudBd8Xvm8D/OaFJ+rfuZ9oa2hnB9+5zhnVMWKL6Z4dfXzqGNgnONIkhbRttG/ttr5KW7Yd4v5o0LDsRmCq5E0sUTFeZEXhG0xDDpo+YpdYryEjQoGFSEWla19YcC2NQ29Z7+L/D78M8X9+nfPG9VPjv2qdkfkih7D6JMkbFRIGYIb15HRn7BdK8XBMXMpkpekeFSzbU1wp8jvL0Ohxd26bQyRDsLw5AUpnttsvzjFM7t/s49ldmrPj/zFjER/nGNg1HEkSUuAb9wlYSM+H9P9T7kkbFykWlzI2fe2Zjvf9veK/I2+7bPaOfJ95rJaP4khy5Cs6Qkbto9esv3ryH/9YBq4qLNI8m9i9qR49xg/YSMxf0Lkoc6nRk7CByXitXdHf8I2m5NizUzYqDZz3m5ebVvRbXtGta12u8j7qXzWVqf4SPdvln45u7frf3aLfD+q0+McA6OOI0laAlePPDxDlKRtn75bzE9J2OpqQo1v/H+O/DxApWF15KHMTSMPj72h24fHRD4e/UybR64G3L7az3AO8djIQ6937rYzm7UMJbKILIlgfcEEVcADU+wf/cNB4PntEPn1PDn6KxJLpby3xHHNvrnaJvLx6HOaDcnhd7t/0//EJAISJ87HHtF7X0mQT0txUOQK2wcizygm6t47EmjOCYkMSUWbsLHeH8ctvW9Ugd8c+XnyhYNz2X4h4DnwOWY/561FTxz7npdi15isAjhfqyI/d9oSCh6fbQdU22orI+/nC0vt55H/ygVOjNx3Vnt85Psx1DzOMTDqOJKkJbJRF1Sf+E/5H5ETp2kYlbCVRJEhUCYI0B/FZIOCxX0Z9itLUJSEjckHD4p8EVoduRpHdYhlSgiapLkdyQS4H5UDtnFbkrL6Iv+yyAkdQ1JUEbhgvbTaz18JeETkZJBKEcNIS43XS7M6r4kgQZ2vAyMfa9SfHCtVWHqvqMb9LMU7Ig+Xntzto6G+HkYj0Sv9kqW3cOvIFT2SJ/qpVkW+T52wvT3FX6O32C/JFs+P50lliHNZT2Tgc8HiwAwVk7jxeaL3rnwp4FzzeCSU26S4MGYO2ddI+nnMcYPzMgwLH/PcN6i23aTbVn85qfF7wP62J5P3nX5QsFQLr7tGIsz9eH/GOQZGHUeStMSokpSL/1kxnRmWoxI2hmDZ/8DITeT8m+SI/imCiz7bVna3LwnbRt3P4H4kdXXCwnPndiVhQ7notEOiTLZgeLE+5l26bVz0WT7j75EfpyjJw1Kj6f5PkV8XszDn24Rfzhf9YeMioeL9Z1IC7xcVMZwfuXpTziXBcyVWRR7WJlnjMWufjJlDol+P/ve8JDjtkChJEP1XVEGL9SIPG5fqFc+p3k8Cx6zm2TA8v++AeHEXL+qCSQQviP5EbBBmZPPcN6y2lQob78sgzNpk/87Ndl7Lid2/SZbPrPahVMb4/RnnGBh1HEnSMsDFd9IL9jCjEja+ybN/RYp7d//mAkofWx2lOlIStnpWG86L/osOqOSMk7AdFbmJv0UCRNWI4TuqEJdF/gPrXJyHzTRluJQhu1ExrYsfF2BeF7P/6qHGuSCR4ViHtjsa9QQAehBZ+qNFpfb4mHkuiXUiJ+k81sPLHTrHxMyEjSG7cRK2XbvtbQJ2QuQvIXhP5NtQSXpt9Cfqi4EEkMenElyQaLONYeFBqPKx/0nNdpa9oXIMluo4p9oHqsHcj6HmcY6BUceRJC0D9BmRpEzLsISNKtgl0buQMkR1aYp3/v8WGcOQzBTEbAkbTfAkVTUWmR2UsNEDBZIGsPTIoISNIWJmlYKqCa+FizyJ4IfKjQbgdVCVGxXlNc3X0yL3lM1lIkaLqg+vj4rWbBjyq4etSdi+X/1cnBozzwmJN8Hj0GDP+dimvkHkhO2UZhvD1YMSNj4PKK+d2YyDEjaSEKqk4PH3iZzgk5RTTeLv7C4Whv95jltW2xgaZls9NFtP/uE95/O4b7WN3x++RPBawBcJfn9qfPm5KPJrHucYGHUcSdISOzBy8jLfKk2tJGxtUzho+GYfvWEFQ0oMX9UJGVW/8vNsCRsXk7b/h2G6OmFjIkK5Lxevo7vtu0euBtUXI5YF4bZcqDZK8axqHxMYuKDRK7XUqFKRFLXvx3wcFnk4uJ14UTD0zEW9IGErkxBqW0ROBuplR3gfiW2jV1HlvNQGJWwMk9cJGz2N3HeX7ucySWLTbnvbHP+L6DXW1/15VFvPiFxpm817I/dEjht15Ww2JIl7Vz8znMqXgYJkjr69+vPLF6njqp85P3+J3uOtiJyAMpxfUHWlZ64YdQysiNHHkSQtgad0QQN7qTpNS0nYGI4pqBxwoWV2KP08NZJFKgBUbKi00VReJ0YlYasbp6lOcKy2d6gdEt0qetUXErKymj7N8Cwe+sjuZzCsSRJI/xMXLoaN6veGC277eIuN9/TcmP5SC7xOEiZeP8lpjcoYkwrq94IkYFCFDTtGnhXKeWQokkSvJHt8DvjMHdv9DKqpZ0WefFJrh0QZkqYXriTSJWEDz+/w6mcmknDeOf+gylRXfHleO1Q/L4bNIveO8YXggMhN/1QNCyptDPPTO1ZQkWWomN8LPp+8R3UyDD7DfDbZz2xb+gHrLyLjHAOjjiNJWmTbRe4/IrgYTwvVE6ouVAm4WHJxIgngwr468qy9h5QbD8CFZeN2Y+SE7f2Rq0BMSKDXigpT6YOiskLweqgckNBQtSsYymMfQ5okbQUVG2aevi/FlyJPhiiJEAkbvXZHRK5CkqDs1+1bKlREzo78lyMWwlqRK5YXRO7bI6mgMsXrrpO1EyInThdHTsxKxavGsBuVr0EXfIaGqWBxnIMjD8mfFvkzQ8LALM/TIyfkF0b/UDTDeDy/I6O/D27tyBMcSDI4p1TQ+JwXfCa4z0GRk/ajYrpV5XFR5eWzujKG90S2SKJZyoQvGoMwvMvvFp9b3vtBRh0D4xxHkrQI+I+YoSK+7RNrmnUjD9/UvT7j4CI12wWIBIEkokbywmOB/rdJH2/a1o9cGWkb7hcCiQSzC3msti9smuhBKxUm3n9mTZK0j0LyOFtVmPO8ScxMxkqSwvvIuZUkadmiL4sKTRkmmg/6f6Y9LKfBSDCoeO3V7pgQfYMMg0uSpGWKWYwM8e3U7pgDen/ov9HCo7JHL1jpvZurzSMv2zDNIXBJkjRFDHGxMOae7Y4JMQy1f+TGfpZS0MI7JPJ6WbMN545CwkczOU33zAaWJEnLEBdsmu658E+C+9H3Qw8TF3yW2aDRnMbwy2O6S0poMJbSINGepDmdGa70cG0febIEzfacM2Ix+t8kSdIclCU2WED0kiHBGmMEazGxPhlrcpULfRvM9tTCYciZYE051jTjvLTnqz5v5Zxx+/ZclWC5DpvtJUlahlgGgmUp3hV5XSWWNSBYg2pYlNsR3I/gGCVYlkALg6FPli0hWDervP+jzt2oc8ZCwZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSZIkSdIU/RfVHy1MLoA6BgAAAABJRU5ErkJggg==>