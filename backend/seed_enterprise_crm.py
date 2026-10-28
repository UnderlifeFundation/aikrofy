import os
import logging
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_enterprise_crm")

load_dotenv()

def seed_enterprise_crm():
    logger.info("Initializing application context...")
    from app import create_app
    from extensions import db
    from models.company import Company
    from models.funnel_stage import FunnelStage
    from models.customer import Customer
    from models.conversation import Conversation, Message, ConversationType, MessageRole
    from models.appointment import Appointment, AppointmentStatus
    from models.transaction import Transaction, TransactionStatus, TransactionType, TransactionProvider
    from services.lead_scoring_service import LeadScoringService

    app = create_app()
    with app.app_context():
        # Target companies
        target_company_ids = [1, 7, 10]
        
        # Define high-caliber corporate profiles
        corporate_leads = [
            # Stage: Nuevo / Lead
            {
                "first_name": "Elon",
                "last_name": "Musk",
                "email": "elon@tesla.com",
                "phone": "+15129990001",
                "work_company": "Tesla Inc.",
                "buying_role": "CEO",
                "country": "US",
                "city": "Austin",
                "lead_score": 45,
                "stage_name": "Lead",
                "chat": [
                    ("user", "Hello, we are looking to integrate our automated logistics system with an AI routing receptionist to scale our tracking updates."),
                    ("assistant", "Hi Elon. Our AI agents can seamlessly connect to external systems (ERP, custom APIs) and broadcast updates via WhatsApp or Webchat. Would you like to review our enterprise integration documentation?")
                ]
            },
            {
                "first_name": "Marcos",
                "last_name": "Galperin",
                "email": "marcos@mercadolibre.com",
                "phone": "+541199990002",
                "work_company": "MercadoLibre",
                "buying_role": "CEO",
                "country": "AR",
                "city": "Buenos Aires",
                "lead_score": 48,
                "stage_name": "Lead",
                "chat": [
                    ("user", "Hola, necesitamos automatizar la atención a vendedores nivel platino por WhatsApp. El volumen diario estimado es de 150k consultas. ¿Soportan ese flujo?"),
                    ("assistant", "Hola Marcos. Sí, contamos con infraestructura distribuida y colas de tareas con Celery/Redis preparadas para alta concurrencia y volumen empresarial. Podemos configurar agentes dedicados para tus vendedores VIP.")
                ]
            },
            # Stage: Contactado
            {
                "first_name": "Jeff",
                "last_name": "Bezos",
                "email": "jeff@amazon.com",
                "phone": "+12069990003",
                "work_company": "Amazon Inc.",
                "buying_role": "Executive Chairman",
                "country": "US",
                "city": "Seattle",
                "lead_score": 58,
                "stage_name": "Contactado",
                "chat": [
                    ("user", "We are testing voice AI dispatching models for our AWS customer service routing in LatAm. What are your telephony and edge-TTS capabilities?"),
                    ("assistant", "Hi Jeff. We integrate natively with Twilio (WhatsApp/Voice) and LiveKit for real-time WebRTC audio. We support premium synthesis providers such as ElevenLabs and Edge-TTS API, ensuring natural voices in Spanish and English.")
                ]
            },
            {
                "first_name": "Satya",
                "last_name": "Nadella",
                "email": "satya@microsoft.com",
                "phone": "+14259990004",
                "work_company": "Microsoft",
                "buying_role": "CEO",
                "country": "US",
                "city": "Redmond",
                "lead_score": 62,
                "stage_name": "Contactado",
                "chat": [
                    ("user", "Looking to synchronize real-time Azure RAG namespaces with customized agent memory. Can you sync memory profiles dynamically?"),
                    ("assistant", "Hi Satya. Absolutely. We support multi-namespace vector indexing using Pinecone, allowing memory profiles to sync dynamically based on company context and agent rules.")
                ]
            },
            # Stage: Calificado
            {
                "first_name": "Sam",
                "last_name": "Altman",
                "email": "sam@openai.com",
                "phone": "+14159990005",
                "work_company": "OpenAI",
                "buying_role": "CEO",
                "country": "US",
                "city": "San Francisco",
                "lead_score": 82,
                "stage_name": "Calificado",
                "chat": [
                    ("user", "We need custom mapping endpoints for our internal model routing metrics. The schema needs to match our high-priority enterprise structures."),
                    ("assistant", "Hi Sam. Our Custom CRMMappingEngine allows you to write custom mapping schemas and run them through our LLM-powered mapper to output clean JSON structures aligned to any system.")
                ]
            },
            {
                "first_name": "Sundar",
                "last_name": "Pichai",
                "email": "sundar@google.com",
                "phone": "+16509990006",
                "work_company": "Google LLC",
                "buying_role": "CEO",
                "country": "US",
                "city": "Mountain View",
                "lead_score": 85,
                "stage_name": "Calificado",
                "chat": [
                    ("user", "We are evaluating calendar-based automation for our Google Workspace enterprise users in South America. The solution must support multi-tenant token verification."),
                    ("assistant", "Hi Sundar. We offer a dedicated Google Calendar OAuth flow with multi-tenant token management, enabling AI agents to schedule, reschedule, and verify appointments on behalf of clients automatically.")
                ]
            },
            # Stage: Propuesta / Negociación
            {
                "first_name": "Mark",
                "last_name": "Zuckerberg",
                "email": "mark@meta.com",
                "phone": "+16509990007",
                "work_company": "Meta Platforms",
                "buying_role": "CEO",
                "country": "US",
                "city": "Menlo Park",
                "lead_score": 92,
                "stage_name": "Propuesta",
                "appointment_title": "Enterprise Meta-WhatsApp Partnership Alignment",
                "chat": [
                    ("user", "We want to partner for a global scale-up WhatsApp provisioning model for SMBs. Let's align on a licensing package."),
                    ("assistant", "Hi Mark. That sounds great. We have prepared an enterprise proposal covering licensing, dedicated high-concurrency API instances, and priority routing. Let's schedule a deep dive.")
                ]
            },
            {
                "first_name": "Tim",
                "last_name": "Cook",
                "email": "tim@apple.com",
                "phone": "+14089990008",
                "work_company": "Apple Inc.",
                "buying_role": "CEO",
                "country": "US",
                "city": "Cupertino",
                "lead_score": 94,
                "stage_name": "Propuesta",
                "appointment_title": "Enterprise iOS Offline-RAG App Architecture Review",
                "chat": [
                    ("user", "We require a secure, HIPAA-compliant offline fallback sync for healthcare clients. The proposal should cover data storage isolation."),
                    ("assistant", "Hi Tim. We have documented our multi-tenant database isolation, data encryption at rest, and offline synchronization protocols. We will share the official architectural proposal today.")
                ]
            },
            # Stage: Ganado (High figures!)
            {
                "first_name": "Bill",
                "last_name": "Gates",
                "email": "bill@gatesfoundation.org",
                "phone": "+12069990009",
                "work_company": "Gates Foundation",
                "buying_role": "Co-Chair",
                "country": "US",
                "city": "Seattle",
                "lead_score": 100,
                "stage_name": "Ganado",
                "deal_value": 150000.00,
                "chat": [
                    ("user", "The proposal for global health tracking system voice onboarding is approved. Processing the contract payment now."),
                    ("assistant", "Hi Bill. Thank you. We have activated your enterprise tenant. The voice RAG namespaces are fully initialized.")
                ]
            },
            {
                "first_name": "Warren",
                "last_name": "Buffett",
                "email": "warren@berkshirehathaway.com",
                "phone": "+14029990010",
                "work_company": "Berkshire Hathaway",
                "buying_role": "CEO",
                "country": "US",
                "city": "Omaha",
                "lead_score": 98,
                "stage_name": "Ganado",
                "deal_value": 350000.00,
                "chat": [
                    ("user", "Our energy division has finalized tests on the AI inventory tracking agents. Payment submitted."),
                    ("assistant", "Hi Warren. Wonderful. We have completed the ERP sync connection. Your live inventory charts are now updating in real-time.")
                ]
            },
            {
                "first_name": "Bernard",
                "last_name": "Arnault",
                "email": "bernard@lvmh.com",
                "phone": "+33199990011",
                "work_company": "LVMH Group",
                "buying_role": "Chairman",
                "country": "FR",
                "city": "Paris",
                "lead_score": 97,
                "stage_name": "Ganado",
                "deal_value": 750000.00,
                "chat": [
                    ("user", "We are deploying the personalized luxury shopper concierge agents for LVMH global portals. Transaction processed."),
                    ("assistant", "Bonjour Bernard. Fantastic news. We have provisioned the custom voice models using high-fidelity ElevenLabs voices. Concierge agents are ready for production launch.")
                ]
            },
            {
                "first_name": "Larry",
                "last_name": "Page",
                "email": "larry@google.com",
                "phone": "+16509990012",
                "work_company": "Alphabet Inc.",
                "buying_role": "Founder",
                "country": "US",
                "city": "Mountain View",
                "lead_score": 99,
                "stage_name": "Ganado",
                "deal_value": 1200000.00,
                "chat": [
                    ("user", "Excellent proof of concept. The board has approved the full scale integration license. Transfer completed."),
                    ("assistant", "Hi Larry. We are thrilled to partner. Your dedicated cluster is active and all enterprise systems are now synchronized.")
                ]
            }
        ]

        for company_id in target_company_ids:
            company = Company.query.get(company_id)
            if not company:
                logger.warning(f"Company {company_id} not found. Skipping.")
                continue
                
            logger.info(f"Processing database seeding for Company: {company.name} (ID: {company_id})")
            
            # 1. Ensure default pipeline stages exist
            stages = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).all()
            if not stages:
                logger.info(f"Seeding default pipeline stages for company {company_id}")
                default_names = ["Lead", "Contactado", "Calificado", "Propuesta", "Negociación", "Ganado", "Perdido"]
                for idx, name in enumerate(default_names):
                    stage = FunnelStage(
                        company_id=company_id,
                        name=name,
                        sort_order=idx
                    )
                    db.session.add(stage)
                db.session.commit()
                stages = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).all()
                
            # Map stages
            stage_by_name = {}
            for s in stages:
                name_norm = s.name.lower().strip()
                name_norm = name_norm.replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
                stage_by_name[name_norm] = s
                
            # Clear previous demo customers, conversations, transactions to avoid duplicate keys and clutter
            old_customers = Customer.query.filter_by(company_id=company_id).all()
            old_cust_ids = [c.id for c in old_customers if (c.customer_metadata or {}).get("is_enterprise_demo") == True]
            
            if old_cust_ids:
                logger.info(f"Purging {len(old_cust_ids)} old enterprise demo records for company {company_id}")
                from models.note import Note
                Note.query.filter(Note.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                Appointment.query.filter(Appointment.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                Transaction.query.filter(Transaction.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                
                # Delete conversations linked to these customers
                old_convs = Conversation.query.filter(Conversation.customer_id.in_(old_cust_ids)).all()
                old_conv_ids = [cv.id for cv in old_convs]
                if old_conv_ids:
                    Message.query.filter(Message.conversation_id.in_(old_conv_ids)).delete(synchronize_session=False)
                    Conversation.query.filter(Conversation.id.in_(old_conv_ids)).delete(synchronize_session=False)
                    
                Customer.query.filter(Customer.id.in_(old_cust_ids)).delete(synchronize_session=False)
                db.session.commit()
                
            # Seed new high-value leads
            now = datetime.utcnow()
            for lead in corporate_leads:
                # Map target stage
                tgt_stage_name = lead["stage_name"].lower()
                target_stage = stage_by_name.get(tgt_stage_name) or stages[0]
                
                # Create customer
                cust = Customer(
                    company_id=company_id,
                    first_name=lead["first_name"],
                    last_name=lead["last_name"],
                    email=lead["email"],
                    phone=lead["phone"],
                    country=lead["country"],
                    city=lead["city"],
                    work_company=lead["work_company"],
                    buying_role=lead["buying_role"],
                    funnel_stage_id=target_stage.id,
                    lead_score=lead["lead_score"],
                    customer_metadata={"is_enterprise_demo": True},
                    is_ai_active=True
                )
                db.session.add(cust)
                db.session.flush() # Generate ID
                
                # Create active conversation
                conv = Conversation(
                    company_id=company_id,
                    customer_id=cust.id,
                    channel="webchat",
                    contact_phone=lead["phone"],
                    contact_name=f"{lead['first_name']} {lead['last_name']}",
                    is_active=True,
                    type=ConversationType.CUSTOMER,
                    lead_score=lead["lead_score"],
                    conv_metadata={"is_enterprise_demo": True},
                    started_at=now - timedelta(days=random.randint(1, 10)),
                    last_message_at=now
                )
                db.session.add(conv)
                db.session.flush() # Generate ID
                
                # Add chat messages
                for role, text in lead["chat"]:
                    msg = Message(
                        conversation_id=conv.id,
                        role=MessageRole.USER if role == "user" else MessageRole.ASSISTANT,
                        content=text,
                        channel="webchat",
                        created_at=now - timedelta(minutes=5)
                    )
                    db.session.add(msg)
                    
                # Create appointments if applicable
                if "appointment_title" in lead:
                    appt = Appointment(
                        company_id=company_id,
                        customer_id=cust.id,
                        conversation_id=conv.id,
                        title=lead["appointment_title"],
                        description=f"Detailed review of the custom integration options with LVMH / Apple / Meta.",
                        start_time=now + timedelta(days=random.randint(1, 5), hours=random.randint(9, 17)),
                        duration_minutes=60,
                        status=AppointmentStatus.SCHEDULED.value,
                        channel_type="webchat"
                    )
                    db.session.add(appt)
                    
                # Create high-value transaction if deal is won
                if "deal_value" in lead:
                    txn = Transaction(
                        company_id=company_id,
                        customer_id=cust.id,
                        conversation_id=conv.id,
                        amount=lead["deal_value"],
                        currency="USD",
                        status=TransactionStatus.COMPLETED.value,
                        description=f"Enterprise Integration License fee - {lead['work_company']}",
                        transaction_type=TransactionType.PAYMENT.value,
                        provider=TransactionProvider.PAYPAL.value,
                        provider_order_id=f"ent_demo_{random.randint(100000, 999999)}"
                    )
                    db.session.add(txn)
                    
            db.session.commit()
            logger.info(f"Successfully seeded 12 high-caliber enterprise leads for company {company_id} ({company.name})!")

if __name__ == "__main__":
    seed_enterprise_crm()
