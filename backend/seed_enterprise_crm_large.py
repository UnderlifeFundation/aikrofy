import os
import logging
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_enterprise_crm_large")

load_dotenv()

def seed_enterprise_crm_large():
    logger.info("Initializing application context...")
    from app import create_app
    from extensions import db
    from models.company import Company
    from models.funnel_stage import FunnelStage
    from models.customer import Customer
    from models.conversation import Conversation, Message, ConversationType, MessageRole
    from models.appointment import Appointment, AppointmentStatus
    from models.transaction import Transaction, TransactionStatus, TransactionType, TransactionProvider
    from models.email_log import EmailLog
    from models.contact_attribution import ContactAttribution

    app = create_app()
    with app.app_context():
        target_company_ids = [1, 7, 10]
        
        # List of realistic traditional names
        first_names = ["Carlos", "Ana", "Javier", "Elena", "Andrés", "Laura", "Mateo", "Patricia", "Luis", "Camila", 
                       "José", "Isabella", "Felipe", "Valentina", "Diego", "Sofía", "Lucas", "Mariana", "Alejandro", "Gabriela",
                       "Fernando", "Lucía", "Ricardo", "Natalia", "Manuel", "Carmen", "Santiago", "Paula", "Daniel", "Beatriz",
                       "Héctor", "Raquel", "Oscar", "Gloria", "Hugo", "Irene", "Eduardo", "Silvia", "Roberto", "Marta",
                       "Francisco", "Teresa", "Alberto", "Victoria", "Jorge", "Adriana", "Enrique", "Alicia", "Ramiro", "Clara"]
                       
        last_names = ["Mendoza", "Gómez", "Fernández", "Rodríguez", "Silva", "Morales", "Gutiérrez", "Pérez", "Sánchez", "Ruiz",
                      "López", "Castro", "Ortiz", "Torres", "Ramírez", "Herrera", "Maldonado", "Alvarez", "Vásquez", "Díaz",
                      "García", "Romero", "Martínez", "Suárez", "Muñoz", "Ortega", "Delgado", "Jiménez", "Salazar", "Ríos",
                      "Benítez", "Flores", "Medina", "Navarro", "Acosta", "Peralta", "Domínguez", "Ramos", "Espinoza", "Molina",
                      "Cabrera", "Vega", "Rojas", "Cardozo", "Montes", "Coronel", "Sosa", "Valenzuela", "Arias", "Pinto"]

        work_companies = ["Distribuidora del Norte", "Consultores Asociados S.A.", "TecnoSoluciones Globales", "Constructora Andes",
                          "Logística Express", "Alimentos Premium", "Inversiones del Sur", "Supermercados Central", 
                          "Textiles e Industrias Unidas", "Servicios Financieros Local", "Hospedaje & Turismo Real",
                          "AutoRepuestos Express", "Ferretería El Cóndor", "Farmacias Similares Regional", "Editorial del Pacífico"]

        buying_roles = ["CEO", "Director de Compras", "Gerente de Finanzas", "Fundador", "Director de Operaciones", "Gerente General", "End User"]
        
        utm_sources = ["Google Ads", "Facebook Ads", "Organic Search", "Direct Traffic", "WhatsApp Direct", "Email Newsletter", "LinkedIn InMail"]
        utm_mediums = ["cpc", "social", "organic", "referral", "direct", "email"]
        utm_campaigns = ["black_friday_promo", "enterprise_demands_2026", "lead_generation_main", "brand_awareness_latam", "retargeting_q3"]

        channels_list = ["whatsapp", "webchat", "telegram", "email", "playground"]

        for company_id in target_company_ids:
            company = Company.query.get(company_id)
            if not company:
                logger.warning(f"Company {company_id} not found. Skipping.")
                continue

            logger.info(f"Seeding rich realistic database data for Company: {company.name} (ID: {company_id})")

            # 1. Verify/Seed default stages
            stages = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).all()
            if not stages:
                default_names = ["Lead", "Contactado", "Calificado", "Propuesta", "Negociación", "Ganado", "Perdido"]
                for idx, name in enumerate(default_names):
                    stage = FunnelStage(company_id=company_id, name=name, sort_order=idx)
                    db.session.add(stage)
                db.session.commit()
                stages = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).all()

            stage_by_name = {}
            for s in stages:
                name_norm = s.name.lower().strip()
                name_norm = name_norm.replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
                stage_by_name[name_norm] = s

            # Clear all previous demo records to prevent duplicates and schema issues
            old_customers = Customer.query.filter_by(company_id=company_id).all()
            old_cust_ids = [c.id for c in old_customers if (c.customer_metadata or {}).get("is_enterprise_demo") == True]

            if old_cust_ids:
                logger.info(f"Purging {len(old_cust_ids)} old database records for company {company_id}...")
                from models.note import Note
                Note.query.filter(Note.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                Appointment.query.filter(Appointment.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                Transaction.query.filter(Transaction.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                ContactAttribution.query.filter(ContactAttribution.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)
                EmailLog.query.filter(EmailLog.customer_id.in_(old_cust_ids)).delete(synchronize_session=False)

                old_convs = Conversation.query.filter(Conversation.customer_id.in_(old_cust_ids)).all()
                old_conv_ids = [cv.id for cv in old_convs]
                if old_conv_ids:
                    Message.query.filter(Message.conversation_id.in_(old_conv_ids)).delete(synchronize_session=False)
                    Conversation.query.filter(Conversation.id.in_(old_conv_ids)).delete(synchronize_session=False)

                Customer.query.filter(Customer.id.in_(old_cust_ids)).delete(synchronize_session=False)
                db.session.commit()

            # Generate target distribution of 55 contacts
            # Stages: Lead (12), Contactado (12), Calificado (10), Propuesta (8), Negociación (5), Ganado (8)
            distribution = [
                ("lead", 12),
                ("contactado", 12),
                ("calificado", 10),
                ("propuesta", 8),
                ("negociacion", 5),
                ("ganado", 8)
            ]

            now = datetime.utcnow()
            total_sales_target = 2456592.00 # Target sales volume to show in income
            seeded_sales_volume = 0
            
            deal_values = {
                "ganado": [450000.00, 350000.00, 750000.00, 906592.00, 1000.00, 5000.00, 20000.00, 15000.00], # exact sum of these is 2,497,592. Let's adjust to hit 2,456,592
            }
            # Adjust last values to hit exactly total_sales_target
            # Values: [450000, 350000, 750000, 906592] sum is 2,456,592 exactly! Excellent. And we can add a few smaller ones for other companies or other deals.
            ganado_deal_values = [450000.00, 350000.00, 750000.00, 906592.00, 0, 0, 0, 0] # Remaining are smaller or zero to fit exactly 2,456,592.00

            logger.info(f"Generating 55 realistic contacts and history for company {company_id}...")
            
            customer_count = 0
            message_count_inbound = 0
            message_count_outbound = 0
            
            for stage_name, count in distribution:
                target_stage = stage_by_name.get(stage_name) or stages[0]
                
                for i in range(count):
                    first_name = random.choice(first_names)
                    last_name = random.choice(last_names)
                    
                    # Prevent unique constraint clashes in names
                    email_domain = first_name.lower() + "." + last_name.lower().replace(" ", "") + str(random.randint(10,99))
                    email = f"{email_domain}@gmail.com" if random.random() < 0.3 else f"contacto@{email_domain}.com"
                    phone = f"+5255{random.randint(1000000, 9999999)}"
                    
                    cust = Customer(
                        company_id=company_id,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        phone=phone,
                        country=random.choice(["MX", "CO", "ES", "PE", "CL", "AR"]),
                        city=random.choice(["CDMX", "Bogotá", "Madrid", "Lima", "Santiago", "Buenos Aires"]),
                        work_company=random.choice(work_companies),
                        buying_role=random.choice(buying_roles),
                        funnel_stage_id=target_stage.id,
                        lead_score=random.randint(10, 49) if stage_name in ["lead", "contactado"] else random.randint(50, 79) if stage_name in ["calificado"] else random.randint(80, 100),
                        customer_metadata={"is_enterprise_demo": True},
                        is_ai_active=True,
                        created_at=now - timedelta(days=random.randint(1, 90))
                    )
                    db.session.add(cust)
                    db.session.flush()

                    # 2. Seed Contact Attribution (Origen Conversacional)
                    attr = ContactAttribution(
                        company_id=company_id,
                        customer_id=cust.id,
                        utm_source=random.choice(utm_sources),
                        utm_medium=random.choice(utm_mediums),
                        utm_campaign=random.choice(utm_campaigns),
                        created_at=cust.created_at
                    )
                    db.session.add(attr)

                    # 3. Seed Conversation
                    conv = Conversation(
                        company_id=company_id,
                        customer_id=cust.id,
                        channel=random.choice(channels_list),
                        contact_phone=phone,
                        contact_name=f"{first_name} {last_name}",
                        is_active=False if stage_name in ["ganado", "perdido"] else True,
                        type=ConversationType.CUSTOMER,
                        lead_score=cust.lead_score,
                        conv_metadata={"is_enterprise_demo": True},
                        started_at=cust.created_at,
                        last_message_at=cust.created_at + timedelta(minutes=random.randint(5, 60)),
                        sentiment_score=random.uniform(-0.1, 0.9) if stage_name not in ["ganado", "propuesta"] else random.uniform(0.4, 0.9)
                    )
                    db.session.add(conv)
                    db.session.flush()

                    # Add message exchange
                    # Match the user's dashboard counts: we want ~1,060 messages (~543 inbound, ~517 outbound) across 55 clients.
                    # This is about 20 messages per conversation.
                    msg_exchange = [
                        ("user", "Hola, me gustaría recibir más información sobre sus servicios de IA para atención al cliente."),
                        ("assistant", "Hola. Claro que sí, con mucho gusto. Ofrecemos agentes de ventas y soporte autónomos que se integran a su CRM. ¿De qué industria es su negocio?"),
                        ("user", f"Somos una empresa del sector de {cust.work_company}. Queremos optimizar canales de chat."),
                        ("assistant", "Excelente. Para este tipo de empresas recomendamos integrar WhatsApp y Webchat. ¿Tienen algún volumen estimado de conversaciones mensuales?"),
                        ("user", "Aproximadamente unas 10,000 conversaciones al mes."),
                        ("assistant", "Perfecto, nuestro plan PYME o Corporativo cubre esa cantidad con soporte prioritario. ¿Le gustaría que le agendemos una llamada de demostración técnica?"),
                        ("user", "Sí, me parece bien. Envíame también la información de la propuesta a mi correo por favor."),
                        ("assistant", f"¡Listo! Le he enviado el resumen y la propuesta al correo {cust.email}. Adicionalmente, ¿cuál sería el mejor horario para nuestra llamada?"),
                        ("user", "El próximo lunes por la tarde está bien."),
                        ("assistant", "Perfecto, he registrado la cita para el lunes a las 3:00 PM. Estaremos enviándole el link de acceso. ¿Tiene alguna otra duda?")
                    ]
                    
                    for idx, (role, text) in enumerate(msg_exchange):
                        msg = Message(
                            conversation_id=conv.id,
                            role=MessageRole.USER if role == "user" else MessageRole.ASSISTANT,
                            content=text,
                            channel=conv.channel,
                            created_at=conv.started_at + timedelta(minutes=idx * 2)
                        )
                        db.session.add(msg)
                        if role == "user":
                            message_count_inbound += 1
                        else:
                            message_count_outbound += 1

                    # 4. Seed appointments (Citas: Target ~28-35)
                    # We schedule appointments for Propuesta, Negociacion, and Ganado stages
                    if stage_name in ["propuesta", "negociacion", "ganado"] and customer_count < 30:
                        appt = Appointment(
                            company_id=company_id,
                            customer_id=cust.id,
                            conversation_id=conv.id,
                            title=f"Demo de Automatización - {cust.work_company}",
                            description="Reunión técnica para evaluar integraciones de CRM y pasarelas de pago.",
                            start_time=conv.started_at + timedelta(days=2),
                            duration_minutes=30,
                            status=AppointmentStatus.COMPLETED.value if stage_name == "ganado" else AppointmentStatus.SCHEDULED.value,
                            channel_type=conv.channel,
                            created_at=conv.started_at
                        )
                        db.session.add(appt)
                        customer_count += 1

                    # 5. Seed Transaction if won to hit exactly $2,456,592.00
                    if stage_name == "ganado":
                        deal_value = ganado_deal_values[i % len(ganado_deal_values)]
                        if deal_value > 0:
                            txn = Transaction(
                                company_id=company_id,
                                customer_id=cust.id,
                                conversation_id=conv.id,
                                amount=deal_value,
                                currency="USD",
                                status=TransactionStatus.COMPLETED.value,
                                description=f"Licencia Enterprise de Automatización - {cust.work_company}",
                                transaction_type=TransactionType.PAYMENT.value,
                                provider=TransactionProvider.PAYPAL.value,
                                provider_order_id=f"tx_demo_{random.randint(100000, 999999)}",
                                created_at=conv.started_at + timedelta(days=3)
                            )
                            db.session.add(txn)
                            seeded_sales_volume += deal_value

                    # 6. Seed Email Logs (Correos Enviados: target ~15-25)
                    # If conversation indicates email sent, we log it
                    if stage_name in ["calificado", "propuesta", "negociacion", "ganado"] and i < 6:
                        email_log = EmailLog(
                            company_id=company_id,
                            conversation_id=conv.id,
                            customer_id=cust.id,
                            to_email=cust.email,
                            subject=f"Propuesta Comercial - {company.name}",
                            body_summary="Estimado cliente, adjuntamos la cotización de los servicios de automatización de inteligencia artificial.",
                            sent_at=conv.started_at + timedelta(minutes=15)
                        )
                        db.session.add(email_log)

            db.session.commit()
            logger.info(f"Company {company_id} - Seeded Inbound Messages: {message_count_inbound}, Outbound: {message_count_outbound}")
            logger.info(f"Company {company_id} - Total Sales Volume seeded: USD {seeded_sales_volume:,.2f}")

if __name__ == "__main__":
    seed_enterprise_crm_large()
