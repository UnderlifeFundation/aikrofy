from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Customer CRM Routes
Manages leads, contacts, notes, timeline and AI toggle.
"""
import logging
from sqlalchemy import or_


from extensions import db
from models.user import User, UserRole
from models.customer import Customer
from models.note import Note
from models.conversation import Conversation, Message
from services.customer_service import CustomerService

logger = logging.getLogger(__name__)

customers_bp = APIRouter('customers', __name__)

def get_user_company():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return None, None
    if user.company:
        return user, user.company
    if user.role == UserRole.SUPER_ADMIN:
        from models.company import Company
        comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
        return user, comp
    return user, None


@customers_bp.route('', methods=['GET'])
@jwt_required()
def list_customers():
    """List all customers/leads for the company"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    
    query = Customer.query.filter_by(company_id=company.id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Customer.first_name.ilike(search_filter),
                Customer.last_name.ilike(search_filter),
                Customer.email.ilike(search_filter),
                Customer.phone.ilike(search_filter)
            )
        )
        
    pagination = query.order_by(Customer.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    customers = [c.to_dict() for c in pagination.items]
    
    return jsonify({
        'data': customers,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@customers_bp.route('', methods=['POST'])
@jwt_required()
def create_customer():
    """Manually create a new customer/lead for the company"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip() or None
    phone = data.get('phone', '').strip() or None
    country = data.get('country', '').strip() or None
    city = data.get('city', '').strip() or None
    ident_number = data.get('ident_number', '').strip() or None
    work_company = data.get('work_company', '').strip() or None
    buying_role = data.get('buying_role', 'End User').strip()

    if not first_name:
        return jsonify({'error': 'First name is required.'}), 400

    # Uniqueness checks within company
    if email:
        existing_email = Customer.query.filter_by(company_id=company.id, email=email).first()
        if existing_email:
            return jsonify({'error': f'The email {email} is already registered.'}), 400

    if phone:
        existing_phone = Customer.query.filter_by(company_id=company.id, phone=phone).first()
        if existing_phone:
            return jsonify({'error': f'The phone {phone} is already registered.'}), 400

    funnel_stage_id = data.get('funnel_stage_id')
    if not funnel_stage_id:
        from models.funnel_stage import FunnelStage
        first_st = FunnelStage.query.filter_by(company_id=company.id).order_by(FunnelStage.sort_order.asc()).first()
        if not first_st:
            default_names = ["Lead", "Contactado", "Calificado", "Propuesta", "Negociación", "Ganado", "Perdido"]
            for idx, name in enumerate(default_names):
                st = FunnelStage(company_id=company.id, name=name, sort_order=idx)
                db.session.add(st)
                if idx == 0:
                    first_st = st
            db.session.flush()
        if first_st:
            funnel_stage_id = first_st.id

    new_customer = Customer(
        company_id=company.id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        country=country,
        city=city,
        ident_number=ident_number,
        work_company=work_company,
        buying_role=buying_role,
        funnel_stage_id=funnel_stage_id,
        is_ai_active=bool(data.get('is_ai_active', True)),
        lead_score=int(data.get('lead_score', 0))
    )

    db.session.add(new_customer)
    db.session.commit()

    logger.info(f"User {user.email} manually created contact {new_customer.id} ({first_name} {last_name})")

    return jsonify({
        'message': 'Contact created successfully',
        'data': new_customer.to_dict()
    }), 201


@customers_bp.route('/<int:customer_id>', methods=['GET'])
@jwt_required()
def get_customer(customer_id):
    """Get full CRM contact sheet with timeline"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
        
    # --- SELF-HEALING: Backfill orphan conversations ---
    # Find any unlinked conversations that belong to this contact's phone or email
    orphan_query = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.customer_id == None
    )
    
    filters = []
    if customer.email:
        filters.append(Conversation.contact_email == customer.email)
    if customer.phone:
        filters.append(Conversation.contact_phone == customer.phone)
        
    if filters:
        orphans = orphan_query.filter(or_(*filters)).all()
        if orphans:
            for conv in orphans:
                conv.customer_id = customer.id
            db.session.commit()
            logger.info(f"Self-healed {len(orphans)} conversations for customer {customer.id}")
    # ---------------------------------------------------
        
    data = customer.to_dict()
    
    # Timeline
    data['timeline'] = CustomerService.get_timeline(customer_id)
    
    # Activity stats & multi-channel touchpoints
    convs = Conversation.query.filter_by(customer_id=customer_id).order_by(Conversation.started_at.asc()).all()
    
    channels_used = []
    touchpoints = []
    for c in convs:
        ch_name = c.channel.value if hasattr(c.channel, 'value') else str(c.channel)
        if ch_name not in channels_used:
            channels_used.append(ch_name)
        touchpoints.append({
            'conversation_id': c.id,
            'channel': ch_name,
            'started_at': c.started_at.isoformat() if c.started_at else None,
            'last_message_at': c.last_message_at.isoformat() if c.last_message_at else None,
            'contact_phone': c.contact_phone,
            'contact_email': c.contact_email,
            'total_messages': c.messages.count() if hasattr(c.messages, 'count') else len(c.messages.all())
        })

    data['activity'] = {
        'total_conversations': len(convs),
        'last_active': convs[-1].last_message_at.isoformat() if (convs and convs[-1].last_message_at) else (convs[-1].started_at.isoformat() if convs else None),
        'first_contact_channel': touchpoints[0]['channel'] if touchpoints else None,
        'first_contact_at': touchpoints[0]['started_at'] if touchpoints else None,
        'latest_contact_channel': touchpoints[-1]['channel'] if touchpoints else None,
        'channels_used': channels_used,
        'touchpoints': touchpoints
    }
    
    return jsonify({'data': data}), 200


@customers_bp.route('/<int:customer_id>/toggle-ai', methods=['PATCH'])
@jwt_required()
def toggle_ai(customer_id):
    """Toggle automated AI responses for a specific customer"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
        
    req_data = request.get_json()
    
    if 'is_ai_active' not in req_data:
        return jsonify({'error': 'is_ai_active boolean is required'}), 400
        
    customer.is_ai_active = bool(req_data['is_ai_active'])
    db.session.commit()
    
    status = "enabled" if customer.is_ai_active else "disabled"
    logger.info(f"User {user.email} {status} AI for customer {customer.id}")
    
    return jsonify({
        'message': f'AI responses {status} successfully',
        'data': customer.to_dict()
    }), 200


@customers_bp.route('/<int:customer_id>', methods=['PATCH'])
@jwt_required()
def update_customer(customer_id):
    """Manually update customer details (name, email, phone, etc.)"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
        
    req_data = request.get_json()
    
    # 1. Uniqueness Validation
    # If the user is changing email or phone, check if it's already used by ANOTHER customer
    email = req_data.get('email')
    phone = req_data.get('phone')
    
    if email:
        collision = Customer.query.filter(
            Customer.email == email, 
            Customer.company_id == company.id,
            Customer.id != customer_id
        ).first()
        if collision:
            return jsonify({'error': f'The email {email} is already used by another contact.'}), 400
            
    if phone:
        collision = Customer.query.filter(
            Customer.phone == phone, 
            Customer.company_id == company.id,
            Customer.id != customer_id
        ).first()
        if collision:
            return jsonify({'error': f'The phone {phone} is already used by another contact.'}), 400
            
    # 2. Update fields
    if 'first_name' in req_data: customer.first_name = req_data['first_name']
    if 'last_name' in req_data: customer.last_name = req_data['last_name']
    if 'email' in req_data: customer.email = req_data['email']
    if 'phone' in req_data: customer.phone = req_data['phone']
    if 'ident_number' in req_data: customer.ident_number = req_data['ident_number']
    if 'city' in req_data: customer.city = req_data['city']
    if 'country' in req_data: customer.country = req_data['country']
    
    # AI toggle also included if present
    if 'is_ai_active' in req_data: customer.is_ai_active = bool(req_data['is_ai_active'])
    
    db.session.commit()
    
    logger.info(f"User {user.email} updated contact {customer.id} info.")
    
    return jsonify({
        'message': 'Contact updated successfully',
        'data': customer.to_dict()
    }), 200


# ============================================================
# Notes CRUD
# ============================================================

@customers_bp.route('/<int:customer_id>/notes', methods=['GET'])
@jwt_required()
def list_notes(customer_id):
    """Get all notes for a customer"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    notes = Note.query.filter_by(
        customer_id=customer_id, company_id=company.id
    ).order_by(Note.created_at.desc()).all()
    
    return jsonify({'data': [n.to_dict() for n in notes]}), 200


@customers_bp.route('/<int:customer_id>/notes', methods=['POST'])
@jwt_required()
def create_note(customer_id):
    """Add a note to a customer"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    note = Note(
        company_id=company.id,
        customer_id=customer_id,
        user_id=user.id,
        content=content,
        author_name=user.name or user.email
    )
    db.session.add(note)
    db.session.commit()
    
    return jsonify({'data': note.to_dict()}), 201


@customers_bp.route('/<int:customer_id>/notes/<int:note_id>', methods=['DELETE'])
@jwt_required()
def delete_note(customer_id, note_id):
    """Delete a note"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    note = Note.query.filter_by(
        id=note_id, customer_id=customer_id, company_id=company.id
    ).first()
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    db.session.delete(note)
    db.session.commit()
    
    return jsonify({'message': 'Note deleted'}), 200


@customers_bp.route('/<int:customer_id>', methods=['DELETE'])
@jwt_required()
def delete_customer(customer_id):
    """Delete a customer and all its data (Conversations, Messages, Notes, Appointments, Transactions)"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    success, message = CustomerService.delete_customer(customer_id, company.id)
    
    if not success:
        return jsonify({'error': message}), 404 if "not found" in message.lower() else 500
        
    logger.info(f"User {user.email} DELETED customer {customer_id} and all related data.")
    
    return jsonify({
        'message': message,
        'id': customer_id
    }), 200
