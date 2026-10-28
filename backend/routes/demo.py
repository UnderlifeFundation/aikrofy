import logging
import threading
import time
import random
from datetime import datetime, timedelta

from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from extensions import db
from models.user import User
from models.customer import Customer
from models.conversation import Conversation, Message, ConversationType, MessageRole
from models.appointment import Appointment
from models.transaction import Transaction, TransactionStatus
from models.crm_config import CRMConfig, CRMPlatform
from models.erp_config import ERPConfig, ERPPlatform
from models.ecommerce_config import EcommerceConfig
from models.payment_gateway import PaymentGatewayConfig
from services.lead_scoring_service import LeadScoringService
from services.realtime_service import RealtimeService

logger = logging.getLogger(__name__)
demo_bp = APIRouter('demo', __name__)

# Global trackers for background simulation threads
active_simulation_threads = {}
stop_simulation_flags = {}

@demo_bp.route('/status', methods=['GET'])
@jwt_required()
def get_demo_status():
    """Check if the demo simulation is currently running for this company."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user or user.email != "test@weblifetech.com":
        return jsonify({'error': 'Unauthorized demo user'}), 403
        
    company_id = user.company_id
    is_running = bool(
        active_simulation_threads.get(company_id) and 
        active_simulation_threads[company_id].is_alive()
    )
    
    return jsonify({
        'running': is_running,
        'email': user.email
    }), 200

@demo_bp.route('/toggle', methods=['POST'])
@jwt_required()
def toggle_demo():
    """Start or stop the live dashboard and CRM sales simulation."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user or user.email != "test@weblifetech.com":
        return jsonify({'error': 'Unauthorized demo user'}), 403
        
    company_id = user.company_id
    data = request.get_json() or {}
    action = data.get('action', 'start')
    
    if action == 'start':
        logger.info(f"Starting demo simulation for company {company_id}")
        stop_simulation_flags[company_id] = False
        
        # Stop any existing thread if running
        if company_id in active_simulation_threads and active_simulation_threads[company_id].is_alive():
            stop_simulation_flags[company_id] = True
            active_simulation_threads[company_id].join(timeout=2)
            
        # Spawn thread
        thread = threading.Thread(target=run_simulation, args=(company_id,))
        thread.daemon = True
        active_simulation_threads[company_id] = thread
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Demo simulation started successfully. Data is populating live.'
        }), 200
        
    else:
        logger.info(f"Stopping demo simulation and cleaning up for company {company_id}")
        stop_simulation_flags[company_id] = True
        
        # Trigger DB cleanup immediately
        cleanup_demo(company_id)
        
        return jsonify({
            'success': True,
            'message': 'Demo simulation stopped. Mock data cleared successfully.'
        }), 200

# ── Simulation Engine ──────────────────────

def run_simulation(company_id):
    """Executes step-by-step CRM updates to simulate growth."""
    try:
        # 1. Clear database of any stale demo data
        cleanup_demo(company_id)
        
        # 2. Fake connections for Integrations display
        logger.info(f"Activating mock integrations for demo on company {company_id}")
        setup_mock_integrations(company_id)
        
        # 3. Populate past transactions and conversations for Analytics display
        logger.info(f"Seeding historical analytics charts on company {company_id}")
        seed_past_analytics_data(company_id)
        
        # 4. Sequential live customer journey simulation
        # We execute database insertions, score updates, and WS updates with time sleeps
        run_live_leads_journey(company_id)
        
    except Exception as e:
        logger.error(f"Error running demo simulation: {e}", exc_info=True)
    finally:
        from database import db_session
        db_session.remove()

def setup_mock_integrations(company_id):
    """Configures system integrations as connected for visual feedback."""
    crm_cfg = CRMConfig.query.filter_by(company_id=company_id).first()
    if not crm_cfg:
        crm_cfg = CRMConfig(company_id=company_id, platform=CRMPlatform.HUBSPOT, credentials={"access_token": "demo"}, is_connected=True, crm_url="https://api.hubapi.com")
        db.session.add(crm_cfg)
    else:
        crm_cfg.is_connected = True
        
    erp_cfg = ERPConfig.query.filter_by(company_id=company_id).first()
    if not erp_cfg:
        erp_cfg = ERPConfig(company_id=company_id, platform=ERPPlatform.SAP_B1, erp_url="https://sap.weblifetech.com", credentials={"username": "demo"})
        erp_cfg.is_connected = True
        db.session.add(erp_cfg)
    else:
        erp_cfg.is_connected = True
        
    pay_cfg = PaymentGatewayConfig.query.filter_by(company_id=company_id).first()
    if not pay_cfg:
        pay_cfg = PaymentGatewayConfig(company_id=company_id, gateway_provider="paypal", is_connected=True, credentials={"client_id": "demo"})
        db.session.add(pay_cfg)
    else:
        pay_cfg.is_connected = True
        
    db.session.commit()
    
    # Broadcast connections change to UI
    RealtimeService.publish_lead_update(company_id, 0, {"refresh_integrations": True})

def seed_past_analytics_data(company_id):
    """Fills the database with 30 days of mock transactions and chats to generate charts."""
    now = datetime.utcnow()
    channels = ['whatsapp', 'webchat', 'voice', 'email']
    
    # Transactions seed
    for i in range(15):
        days_back = random.randint(1, 30)
        created_at = now - timedelta(days=days_back)
        txn = Transaction(
            company_id=company_id,
            amount=random.choice([99.00, 199.00, 499.00, 999.00]),
            currency="USD",
            status=TransactionStatus.COMPLETED.value,
            description=f"Simulated Sales Conversion #{i}",
            created_at=created_at,
            provider_order_id="demo_txn"
        )
        db.session.add(txn)
        
    # Conversations seed
    for i in range(25):
        days_back = random.randint(1, 30)
        created_at = now - timedelta(days=days_back)
        conv = Conversation(
            company_id=company_id,
            channel=random.choice(channels),
            type=ConversationType.CUSTOMER,
            contact_name=f"Demo Client #{i}",
            contact_phone=f"+52559999{i:04d}",
            started_at=created_at,
            last_message_at=created_at,
            sentiment_score=random.uniform(0.1, 0.8),
            lead_score=random.randint(10, 90),
            conv_metadata={"is_demo": True}
        )
        db.session.add(conv)
        
    db.session.commit()
    RealtimeService.publish_lead_update(company_id, 0, {"refresh_analytics": True})

def run_live_leads_journey(company_id):
    """Steps through the live customer journey stages in real-time."""
    
    steps = [
        # ── JUAN PEREZ (Corporate CFO) ──
        {
            "delay": 2,
            "fn": lambda: create_ephemeral_lead(company_id, "guest_juan_123", "Hola, me interesa conocer los planes de IA corporativos.")
        },
        {
            "delay": 5,
            "fn": lambda: upgrade_lead(company_id, "guest_juan_123", "Juan", "Pérez", "juan@perezcorp.com", "+525512345678", "Pérez Corp", "CFO")
        },
        {
            "delay": 5,
            "fn": lambda: create_appointment(company_id, "guest_juan_123", "Reunión de demostración técnica")
        },
        {
            "delay": 6,
            "fn": lambda: complete_payment(company_id, "guest_juan_123", 499.00)
        },
        
        # ── SOFIA GOMEZ (InovaTech CEO) ──
        {
            "delay": 4,
            "fn": lambda: create_ephemeral_lead(company_id, "guest_sofia_456", "Hola, busco integrar cobros por WhatsApp.")
        },
        {
            "delay": 5,
            "fn": lambda: upgrade_lead(company_id, "guest_sofia_456", "Sofía", "Gómez", "sofia.g@inovatech.io", "+34600123456", "InovaTech", "CEO")
        },
        {
            "delay": 5,
            "fn": lambda: create_appointment(company_id, "guest_sofia_456", "Llamada de Onboarding")
        },
        
        # ── CARLOS SLIM (Founder) ──
        {
            "delay": 5,
            "fn": lambda: create_ephemeral_lead(company_id, "guest_carlos_789", "Hola, me interesa integrar CRM con telefonía de voz.")
        },
        {
            "delay": 5,
            "fn": lambda: upgrade_lead(company_id, "guest_carlos_789", "Carlos", "Slim", "carlos@americamovil.com", "+525599998888", "América Móvil", "Founder")
        },
        {
            "delay": 5,
            "fn": lambda: create_appointment(company_id, "guest_carlos_789", "Consultoría Estratégica")
        },
        {
            "delay": 6,
            "fn": lambda: complete_payment(company_id, "guest_carlos_789", 1200.00)
        }
    ]
    
    for idx, step in enumerate(steps):
        # Graceful interruption
        if stop_simulation_flags.get(company_id, False):
            break
            
        time.sleep(step["delay"])
        step["fn"]()

# ── Simulation Actions Helpers ──────────────────────

def create_ephemeral_lead(company_id, user_id, message):
    conversation = Conversation.query.filter_by(
        company_id=company_id,
        contact_phone=user_id,
        is_active=True
    ).first()
    
    if not conversation:
        conversation = Conversation(
            company_id=company_id,
            channel="webchat",
            contact_phone=user_id,
            is_active=True,
            type=ConversationType.CUSTOMER,
            conv_metadata={"is_demo": True}
        )
        db.session.add(conversation)
        db.session.flush()
        
    customer = Customer.query.filter_by(
        company_id=company_id,
        phone=user_id
    ).first()
    
    if not customer:
        customer = Customer(
            company_id=company_id,
            first_name="Visitante Webchat",
            last_name=user_id[-6:],
            phone=user_id,
            status="new",
            is_ai_active=True,
            customer_metadata={"is_demo": True}
        )
        db.session.add(customer)
        db.session.flush()
        
    conversation.customer_id = customer.id
    
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=message,
        channel="webchat"
    )
    db.session.add(user_msg)
    db.session.commit()
    
    # Scoring calculation triggers auto-progression and socket update
    LeadScoringService.calculate_composite_score(company_id, customer.id)
    
def upgrade_lead(company_id, user_id, first_name, last_name, email, phone, company_name, role):
    customer = Customer.query.filter_by(company_id=company_id, phone=user_id).first()
    if customer:
        customer.first_name = first_name
        customer.last_name = last_name
        customer.email = email
        customer.phone = phone
        customer.work_company = company_name
        customer.buying_role = role
        db.session.commit()
        
        # Scoring triggers "Contactado"/"Calificado" auto-move
        LeadScoringService.calculate_composite_score(company_id, customer.id)

def create_appointment(company_id, user_id, title):
    # Lookup upgraded customer
    customer = Customer.query.filter(
        Customer.company_id == company_id,
        (Customer.phone == user_id) | (Customer.email.ilike(f"%{user_id}%"))
    ).first()
    
    if not customer:
        first_name = "Juan" if "juan" in user_id else ("Sofía" if "sofia" in user_id else "Carlos")
        customer = Customer.query.filter_by(company_id=company_id, first_name=first_name).first()
        
    if customer:
        appt = Appointment(
            company_id=company_id,
            customer_id=customer.id,
            title=title,
            status="scheduled",
            created_at=datetime.utcnow()
        )
        db.session.add(appt)
        db.session.commit()
        
        # Scoring triggers "Propuesta" auto-move
        LeadScoringService.calculate_composite_score(company_id, customer.id)

def complete_payment(company_id, user_id, amount):
    customer = Customer.query.filter(
        Customer.company_id == company_id,
        (Customer.phone == user_id) | (Customer.email.ilike(f"%{user_id}%"))
    ).first()
    
    if not customer:
        first_name = "Juan" if "juan" in user_id else ("Sofía" if "sofia" in user_id else "Carlos")
        customer = Customer.query.filter_by(company_id=company_id, first_name=first_name).first()
        
    if customer:
        txn = Transaction(
            company_id=company_id,
            customer_id=customer.id,
            amount=amount,
            currency="USD",
            status=TransactionStatus.COMPLETED.value,
            description="Completed Demo Payment",
            created_at=datetime.utcnow(),
            provider_order_id="demo_txn"
        )
        db.session.add(txn)
        db.session.commit()
        
        # Scoring triggers "Ganado" auto-move
        LeadScoringService.calculate_composite_score(company_id, customer.id)

# ── Cleanup Helper ──────────────────────────

def cleanup_demo(company_id):
    """Purges all mock-created data from the database safely."""
    from models.note import Note
    
    # 1. Identify demo customers and conversations
    demo_customers = Customer.query.filter_by(company_id=company_id).all()
    demo_cust_ids = [c.id for c in demo_customers if (c.customer_metadata or {}).get('is_demo') == True]
    
    demo_conversations = Conversation.query.filter_by(company_id=company_id).all()
    demo_conv_ids = [c.id for c in demo_conversations if (c.conv_metadata or {}).get('is_demo') == True]
    
    # 2. Delete dependencies
    if demo_cust_ids:
        Note.query.filter(Note.customer_id.in_(demo_cust_ids)).delete(synchronize_session=False)
        Appointment.query.filter(Appointment.customer_id.in_(demo_cust_ids)).delete(synchronize_session=False)
        Transaction.query.filter(Transaction.customer_id.in_(demo_cust_ids)).delete(synchronize_session=False)
        
    if demo_conv_ids:
        Message.query.filter(Message.conversation_id.in_(demo_conv_ids)).delete(synchronize_session=False)
        Conversation.query.filter(Conversation.id.in_(demo_conv_ids)).delete(synchronize_session=False)
        
    if demo_cust_ids:
        Customer.query.filter(Customer.id.in_(demo_cust_ids)).delete(synchronize_session=False)
        
    # Delete unlinked transaction mocks
    Transaction.query.filter(
        Transaction.company_id == company_id,
        Transaction.provider_order_id == "demo_txn"
    ).delete(synchronize_session=False)
        
    # 3. Delete mock CRM, ERP and Payment configs created for the demo
    crm_cfg = CRMConfig.query.filter_by(company_id=company_id).first()
    if crm_cfg and crm_cfg.credentials == {"access_token": "demo"}:
        db.session.delete(crm_cfg)
        
    erp_cfg = ERPConfig.query.filter_by(company_id=company_id).first()
    if erp_cfg and erp_cfg.credentials == {"username": "demo"}:
        db.session.delete(erp_cfg)
        
    pay_cfg = PaymentGatewayConfig.query.filter_by(company_id=company_id).first()
    if pay_cfg and pay_cfg.credentials == {"client_id": "demo"}:
        db.session.delete(pay_cfg)
        
    db.session.commit()
    
    # Broadcast reset to UI
    try:
        RealtimeService.publish_lead_update(company_id, 0, {
            "refresh_all": True,
            "refresh_integrations": True,
            "refresh_analytics": True
        })
    except Exception as e:
        logger.warning(f"Could not emit demo cleanup WS update: {e}")
