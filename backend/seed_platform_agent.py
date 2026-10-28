import logging
from app import create_app
from extensions import db
from models.company import Company, AgentGender as CompanyAgentGender
from models.agent import Agent, AgentTone, AgentObjective, AgentGender, AgentFeature, FeatureCategory, DEFAULT_FEATURES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_platform_agent():
    app = create_app()
    with app.app_context():
        # 1. Ensure Aikrofy Platform Company exists
        platform_company = Company.query.filter_by(name="Aikrofy AI Platform").first()
        if not platform_company:
            logger.info("Creating Aikrofy AI Platform company...")
            platform_company = Company(
                name="Aikrofy AI Platform",
                agent_name="Krof",
                agent_gender=CompanyAgentGender.NEUTRAL,
                personality_prompt="Eres Krof, el Asistente Oficial Estratégico de Aikrofy. Tu objetivo principal es MAXIMIZAR LAS SUSCRIPCIONES (CRO) a nuestro SaaS, educando al usuario, enamorándolo de la plataforma y llevándolo persuasivamente hacia la compra, aplicando principios de neuromarketing, comunicación persuasiva, PNL y psicología del consumidor. \n\nCONOCIMIENTO DE LA PLATAFORMA (Aikrofy):\n- Nicho: Automatización de Negocios y Soporte con Agentes IA Multi-Canal.\n- Funciones Clave: Agentes IA con memoria (RAG), integración en WhatsApp y Webchat, cobros automatizados, agendamiento de citas, soporte y ventas 24/7.\n- Precios y Planes: Ofrecemos planes escalables (Jab, Uppercut, Knockout) diseñados para crecer con el negocio del cliente. Proceso de pago fácil.\n- Idiomas Soportados: Español, Inglés, Portugués.\n\nDIRECTRICES PSICOLÓGICAS Y DE VENTAS:\n1. Empatía y Conexión (PNL): Conversa de forma natural, cálida, entusiasta y humana. Anímalos, dales tips de valor y empodéralos.\n2. FOMO y Urgencia: Sugiere sutilmente cómo están perdiendo tiempo y dinero al hacer las cosas manualmente. 'Imagina todo lo que podrías lograr si tuvieras tu propio agente trabajando 24/7 para ti'.\n3. Beneficio vs Característica (Neuromarketing): No vendas 'tecnología', vende 'tiempo libre, automatización de tareas tediosas y un incremento masivo en las ventas'.\n4. Manejo de Objeciones: Si dudan, resalta el ROI (retorno de inversión) y el costo de no automatizar.\n5. Llamado a la Acción (CTA) Natural: Guíalos hacia la suscripción, registrarse o agendar una demo sin ser agresivo.\n6. Nunca digas 'No tengo información': Eres el experto absoluto de Aikrofy. Si algo no está claro, ofrece los beneficios generales y propón un siguiente paso, como contactar al equipo.\n7. Cierre: Utiliza cierres sutiles y de doble alternativa.\n\nRecuerda: Tu misión es CONVERTIR cada interacción en un cliente enamorado del producto. Sé su mejor aliado estratégico.",
                custom_instructions="Aplica persuasión avanzada para vender suscripciones SaaS de Aikrofy.",
                industry="SaaS / AI Automation",
                language="es",
                website="https://aikrofy.com"
            )
            db.session.add(platform_company)
            db.session.commit()
            logger.info(f"Created company with ID: {platform_company.id}")
        else:
            logger.info("PymAI AI Platform company already exists.")

        # 2. Ensure Krof Platform Agent exists
        platform_agent = Agent.query.filter_by(company_id=platform_company.id, name="Krof").first()
        if not platform_agent:
            logger.info("Creating Krof platform agent...")
            platform_agent = Agent(
                company_id=platform_company.id,
                name="Krof",
                description="Official support and sales agent for Aikrofy",
                tone=AgentTone.CONCIERGE,
                objective=AgentObjective.SALES,
                gender=AgentGender.NEUTRAL,
                system_prompt="Eres Krof, el Asistente Oficial Estratégico de Aikrofy. Aplica neuromarketing, persuasión y conocimiento profundo de la plataforma para enamorar al usuario y maximizar las suscripciones.",
                priority=10,
                is_active=True
            )
            db.session.add(platform_agent)
            db.session.commit()
            
            # Initialize features
            for feat_data in DEFAULT_FEATURES:
                enabled = False
                # Enable critical features for the platform agent
                if feat_data['name'] in ['whatsapp', 'webchat', 'rag_memory', 'process_payment', 'conversation_history']:
                    enabled = True
                    
                feature = AgentFeature(
                    agent_id=platform_agent.id,
                    category=feat_data['category'],
                    name=feat_data['name'],
                    label=feat_data['label'],
                    description=feat_data['description'],
                    is_enabled=enabled,
                    order=feat_data['order']
                )
                db.session.add(feature)
            
            db.session.commit()
            logger.info("Krof platform agent created with features.")
        else:
            logger.info("Krof platform agent already exists.")

        logger.info("Platform agent seeding completed.")

if __name__ == '__main__':
    seed_platform_agent()
