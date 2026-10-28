from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Admin Chat Routes
"""
import uuid
import logging
from datetime import datetime


from extensions import db, socketio, emit, join_room
from models.user import User, UserRole
from models.company import Company
from models.platform_config import PlatformConfig
from models.conversation import Conversation, Message, ConversationType, MessageChannel, MessageRole
from decorators import subscription_required

logger = logging.getLogger(__name__)

chat_bp = APIRouter('chat', __name__)



def get_user_company():
    """Helper to get current user's company"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None, None
        if user.company:
            return user, user.company
        if user.role == UserRole.SUPER_ADMIN:
            from models.company import Company
            comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
            return user, comp
        return None, None
    except Exception as e:
        print(f"DEBUG: Chat - Error: {e}")
        return None, None


from sqlalchemy import or_
from services.messaging_service import messaging_service
from services.realtime_service import RealtimeService


@chat_bp.route('/conversations', methods=['GET'])
@jwt_required()
def list_conversations():
    """List all conversations with optional filters for type, channel, active, resolved, and search"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Filter parameters
    conversation_type = request.args.get('type')
    channel = request.args.get('channel')
    is_active_param = request.args.get('active')
    is_resolved_param = request.args.get('resolved')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    query = Conversation.query.filter_by(company_id=company.id)
    
    if conversation_type and conversation_type != 'all':
        try:
            query = query.filter_by(type=ConversationType(conversation_type))
        except ValueError:
            pass
    
    if channel and channel != 'all':
        try:
            query = query.filter_by(channel=MessageChannel(channel))
        except ValueError:
            pass
    
    if is_active_param is not None:
        query = query.filter_by(is_active=(is_active_param.lower() == 'true'))
        
    if is_resolved_param is not None:
        query = query.filter_by(is_resolved=(is_resolved_param.lower() == 'true'))

    handover_param = request.args.get('handover')
    if handover_param is not None and handover_param.lower() == 'true':
        query = query.filter(
            or_(
                Conversation.handover_status == 'human_taken',
                Conversation.handover_status == 'human_listening'
            )
        )

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Conversation.contact_name.ilike(search_pattern),
                Conversation.contact_phone.ilike(search_pattern),
                Conversation.contact_email.ilike(search_pattern)
            )
        )
    
    query = query.order_by(Conversation.last_message_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'conversations': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Get conversation with messages"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    conversation = Conversation.query.filter_by(
        id=conversation_id,
        company_id=company.id
    ).first()
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify({'conversation': conversation.to_dict(include_messages=True)})


@chat_bp.route('/conversations/<int:conversation_id>/reply', methods=['POST'])
@jwt_required()
def reply_conversation(conversation_id):
    """
    Send an agent/human reply to a conversation.
    Dispatches via the respective channel (WhatsApp, Telegram, etc.) and emits realtime events.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    conversation = Conversation.query.filter_by(
        id=conversation_id,
        company_id=company.id
    ).first()

    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    data = request.get_json() or {}
    content = data.get('content', '').strip()
    pause_ai = data.get('pause_ai', True)

    if not content:
        return jsonify({'error': 'Message content is required'}), 400

    # Determine channel
    channel_str = conversation.channel.value if hasattr(conversation.channel, 'value') else str(conversation.channel)

    # Dispatch to external service if appropriate
    dispatch_success = True
    if channel_str == 'whatsapp' and conversation.contact_phone:
        try:
            dispatch_success = messaging_service.send_whatsapp(
                to_phone=conversation.contact_phone,
                message=content,
                company_id=company.id
            )
        except Exception as e:
            logger.error(f"Error sending WhatsApp message in conversation {conversation_id}: {e}")
            dispatch_success = False

    elif channel_str == 'telegram' and conversation.conv_metadata and conversation.conv_metadata.get('chat_id'):
        try:
            chat_id = str(conversation.conv_metadata.get('chat_id'))
            dispatch_success = messaging_service.send_telegram(chat_id=chat_id, message=content)
        except Exception as e:
            logger.error(f"Error sending Telegram message in conversation {conversation_id}: {e}")
            dispatch_success = False

    # Save agent message in database
    message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=content,
        channel=channel_str
    )
    db.session.add(message)

    # Update conversation metadata and timestamp
    conversation.last_message_at = datetime.utcnow()
    conv_metadata = dict(conversation.conv_metadata or {})
    conv_metadata['last_reply_by'] = {
        'user_id': user.id,
        'user_name': user.name,
        'timestamp': datetime.utcnow().isoformat()
    }
    if pause_ai:
        conv_metadata['is_ai_active'] = False
        conv_metadata['ai_paused_at'] = datetime.utcnow().isoformat()

    conversation.conv_metadata = conv_metadata
    db.session.commit()

    message_dict = message.to_dict()

    # Emit realtime message event to chat room
    try:
        room = f"chat_{conversation.id}"
        socketio.emit('new_message', {
            'conversation_id': conversation.id,
            'message': message_dict,
            'sender_name': user.name
        }, room=room)
    except Exception as sock_err:
        logger.warning(f"Error emitting new_message via socketio: {sock_err}")

    # Emit realtime update to company room
    try:
        RealtimeService.publish_conversation_update(
            company_id=company.id,
            conversation_id=conversation.id,
            update_data={
                'last_message': content,
                'last_message_at': conversation.last_message_at.isoformat(),
                'conv_metadata': conversation.conv_metadata
            }
        )
    except Exception as pub_err:
        logger.warning(f"Error publishing conversation update: {pub_err}")

    return jsonify({
        'success': True,
        'message': message_dict,
        'dispatched': dispatch_success
    })


@chat_bp.route('/conversations/<int:conversation_id>/status', methods=['PATCH'])
@jwt_required()
def update_conversation_status(conversation_id):
    """
    Update conversation status: toggle is_resolved, is_active, is_ai_active, or tags.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    conversation = Conversation.query.filter_by(
        id=conversation_id,
        company_id=company.id
    ).first()

    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    data = request.get_json() or {}

    if 'is_resolved' in data:
        conversation.is_resolved = bool(data['is_resolved'])
        if conversation.is_resolved:
            conversation.resolved_at = datetime.utcnow()
        else:
            conversation.resolved_at = None

    if 'is_active' in data:
        conversation.is_active = bool(data['is_active'])

    if 'is_ai_active' in data:
        conv_metadata = dict(conversation.conv_metadata or {})
        conv_metadata['is_ai_active'] = bool(data['is_ai_active'])
        conversation.conv_metadata = conv_metadata
        if bool(data['is_ai_active']):
            conversation.handover_status = 'bot_active'
        else:
            conversation.handover_status = 'human_taken'

    if 'handover_status' in data:
        conversation.handover_status = str(data['handover_status'])
        conv_metadata = dict(conversation.conv_metadata or {})
        conv_metadata['is_ai_active'] = (data['handover_status'] == 'bot_active')
        conversation.conv_metadata = conv_metadata

    if 'assigned_user_id' in data:
        conversation.assigned_user_id = data['assigned_user_id']

    if 'tags' in data and isinstance(data['tags'], list):
        conversation.tags = data['tags']

    db.session.commit()

    # Emit realtime update
    try:
        RealtimeService.publish_conversation_update(
            company_id=company.id,
            conversation_id=conversation.id,
            update_data={
                'is_resolved': conversation.is_resolved,
                'is_active': conversation.is_active,
                'conv_metadata': conversation.conv_metadata,
                'tags': conversation.tags
            }
        )
    except Exception as pub_err:
        logger.warning(f"Error publishing conversation update: {pub_err}")

    return jsonify({
        'success': True,
        'conversation': conversation.to_dict(include_messages=False)
    })


@chat_bp.route('/admin', methods=['GET'])
@jwt_required()
def get_admin_chat():
    """Get or create admin chat conversation"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Find or create admin chat conversation
    conversation = Conversation.query.filter_by(
        company_id=company.id,
        type=ConversationType.ADMIN,
        channel=MessageChannel.ADMIN_CHAT,
        contact_email=user.email
    ).first()
    
    if not conversation:
        conversation = Conversation(
            company_id=company.id,
            type=ConversationType.ADMIN,
            channel=MessageChannel.ADMIN_CHAT,
            contact_name=user.name,
            contact_email=user.email
        )
        db.session.add(conversation)
        db.session.commit()
    
    return jsonify({'conversation': conversation.to_dict(include_messages=True)})


@chat_bp.route('/admin/message', methods=['POST'])
@jwt_required()
@subscription_required
def send_admin_message():
    """Send message in admin chat"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json()
    content = data.get('content', '').strip()
    interface_language = data.get('interface_language') or 'en'
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    
    # Get or create admin chat conversation
    conversation = Conversation.query.filter_by(
        company_id=company.id,
        type=ConversationType.ADMIN,
        channel=MessageChannel.ADMIN_CHAT,
        contact_email=user.email
    ).first()
    
    if not conversation:
        conversation = Conversation(
            company_id=company.id,
            type=ConversationType.ADMIN,
            channel=MessageChannel.ADMIN_CHAT,
            contact_name=user.name,
            contact_email=user.email
        )
        db.session.add(conversation)
        db.session.flush()
    
    # Cache IDs before long AI call — session connection may expire during AI processing
    conversation_id = conversation.id

    # Create user message
    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=content,
        channel=MessageChannel.ADMIN_CHAT
    )
    db.session.add(user_message)
    conversation.last_message_at = datetime.utcnow()
    db.session.commit()

    # Cache user_message dict NOW while session is still alive
    user_message_dict = user_message.to_dict()

    # Generate AI response (this can take several seconds — DB connection may drop)
    response_data = {}
    try:
        from services.brain_events_service import BrainEventsService
        BrainEventsService.emit_thought_start(company.id, "Krof", content)

        from services.agent_service import AgentService
        agent_service = AgentService(company)
        response_data = agent_service.process_message(
            conversation=conversation,
            user_message=content,
            channel='admin_chat',
            is_employee=True,
            interface_language=interface_language,
            user_role=user.role.value if hasattr(user.role, 'value') else str(user.role)
        )
        assistant_response = response_data.get('content')

        if not assistant_response and response_data.get('tool_calls'):
            tool_names = [t.get('tool', 'unknown') for t in response_data['tool_calls']]
            assistant_response = f"I am performing the following actions: {', '.join(tool_names)}..."

        if not assistant_response:
            assistant_response = "I apologize, but I couldn't generate a verbal response."

        tokens_est = len(content.split()) * 2 + len(assistant_response.split()) * 2
        BrainEventsService.emit_response_complete(company.id, "Krof", tokens_used=tokens_est, channel="admin_chat")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: Failed to generate AI response: {e}")
        assistant_response = "I apologize, but I'm having trouble connecting to my brain right now. Please check your API configuration."

    # ── Save assistant message using a FRESH session ─────────────────────────
    # The original scoped session connection may have been dropped by MySQL during
    # the AI call. A new SessionLocal() always gets a live connection from the pool
    # (pool_pre_ping ensures the pool validates before handing it out).
    from database import SessionLocal
    from sqlalchemy import text as sa_text

    fresh_session = SessionLocal()
    assistant_message_dict = {}
    try:
        assistant_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=assistant_response,
            channel=MessageChannel.ADMIN_CHAT,
            tool_calls=response_data.get('tool_calls', [])
        )
        fresh_session.add(assistant_message)
        fresh_session.execute(
            sa_text('UPDATE conversations SET last_message_at = NOW() WHERE id = :id'),
            {'id': conversation_id}
        )
        fresh_session.commit()
        fresh_session.refresh(assistant_message)
        assistant_message_dict = assistant_message.to_dict()
    except Exception as e:
        fresh_session.rollback()
        import traceback
        traceback.print_exc()
        print(f"ERROR: Failed to save assistant message: {e}")
        assistant_message_dict = {
            'role': 'assistant',
            'content': assistant_response,
            'conversation_id': conversation_id
        }
    finally:
        fresh_session.close()
    # ─────────────────────────────────────────────────────────────────────────

    print(f"\n[AI RESPONSE] >>> {assistant_response}")
    if response_data.get('tool_calls'):
        print(f"[AI TOOLS] >>> {response_data['tool_calls']}\n")

    return jsonify({
        'user_message': user_message_dict,
        'assistant_message': assistant_message_dict,
        'action': response_data.get('action'),
        'action_data': response_data.get('action_data')
    })


@chat_bp.route('/history', methods=['GET'])
@jwt_required()
def get_chat_history():
    """Get chat history for current user"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Get admin chat history
    conversation = Conversation.query.filter_by(
        company_id=company.id,
        type=ConversationType.ADMIN,
        channel=MessageChannel.ADMIN_CHAT,
        contact_email=user.email
    ).first()
    
    if not conversation:
        return jsonify({'messages': []})
    
    messages = Message.query.filter_by(
        conversation_id=conversation.id
    ).order_by(Message.created_at).all()
    
    return jsonify({'messages': [m.to_dict() for m in messages]})


@chat_bp.route('/admin/clear', methods=['POST'])
@jwt_required()
def clear_admin_chat():
    """Clear chat history for current user's admin conversation and increment chat version"""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Get the conversation
    conversation = Conversation.query.filter_by(
        company_id=company.id,
        type=ConversationType.ADMIN,
        channel=MessageChannel.ADMIN_CHAT,
        contact_email=user.email
    ).first()
    
    if conversation:
        # Delete all message_audits associated with messages in the conversation first (FK constraint)
        from models.message_audit import MessageAudit
        msg_ids = [m.id for m in Message.query.filter_by(conversation_id=conversation.id).with_entities(Message.id).all()]
        if msg_ids:
            MessageAudit.query.filter(MessageAudit.message_id.in_(msg_ids)).delete(synchronize_session=False)
        
        # Delete all messages in the conversation
        Message.query.filter_by(conversation_id=conversation.id).delete(synchronize_session=False)
        
        # Increment chat version in metadata to reset LangGraph memory
        metadata = dict(conversation.conv_metadata or {})
        metadata['chat_version'] = metadata.get('chat_version', 0) + 1
        conversation.conv_metadata = metadata
        
        conversation.last_message_at = datetime.utcnow()
        db.session.commit()
        
    return jsonify({'success': True, 'message': 'Admin chat cleared successfully'})


# WebSocket events for real-time chat
@socketio.on('join_chat')
def handle_join_chat(data):
    """Join a chat room"""
    room = f"chat_{data.get('conversation_id')}"
    join_room(room)
    emit('joined', {'room': room})


@socketio.on('join_company')
def handle_join_company(data):
    """Join the company's real-time pipeline room (joins both naming conventions for compatibility)"""
    company_id = data.get('company_id')
    if company_id:
        room_a = f"company_room_{company_id}"
        room_b = f"company_{company_id}"
        join_room(room_a)
        join_room(room_b)
        emit('company_joined', {'room': room_a, 'room_alt': room_b})


@socketio.on('send_message')
def handle_send_message(data):
    """Handle real-time message sending"""
    conversation_id = data.get('conversation_id')
    content = data.get('content')
    
    if not conversation_id or not content:
        return
    
    room = f"chat_{conversation_id}"
    
    # Emit to all clients in the room
    emit('new_message', {
        'conversation_id': conversation_id,
        'content': content,
        'role': 'user',
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


@chat_bp.route('/platform', methods=['POST'])
def platform_chat():
    """
    Public endpoint for the platform's brand agent (Web Chat).
    Uses the platform_company_id configured in PlatformConfig.
    """
    db.session.rollback()
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        conv_id = data.get('conversation_id')
        interface_language = data.get('interface_language') or 'en'
        scope = (data.get('scope') or '').strip().lower()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Context-aware resolution: If request comes from Underlife Community, route to Company 5
        origin_header = (request.headers.get('origin') or request.headers.get('referer') or '').lower()
        is_community_context = (
            scope == 'community' or 
            'fundacionunderlife.org' in origin_header or 
            '/community' in origin_header
        )

        if is_community_context:
            comp_id = 5  # Fundación Underlife Company
            company = Company.query.get(comp_id)
            if not company:
                config = PlatformConfig.get_config()
                comp_id = config.platform_company_id
                company = Company.query.get(comp_id)
        else:
            config = PlatformConfig.get_config()
            comp_id = config.platform_company_id
            if not comp_id:
                return jsonify({'error': 'Platform agent not configured'}), 503
            company = Company.query.get(comp_id)

        if not company:
            return jsonify({'error': 'Platform company not found'}), 503

        # Resolve or Create Conversation
        conversation = None
        if conv_id:
            conversation = Conversation.query.get(conv_id)
            
        if not conversation or conversation.company_id != company.id:
            # Create a transient conversation for the web user
            conversation = Conversation(
                company_id=company.id,
                contact_phone=f"web_{uuid.uuid4().hex[:8]}",
                contact_name="Visitante Web",
                channel=MessageChannel.WEBCHAT,
                type=ConversationType.CUSTOMER
            )
            db.session.add(conversation)
            db.session.commit()

        # Save human message
        user_msg = Message(
            conversation_id=conversation.id,
            content=message,
            role=MessageRole.USER,
            channel=MessageChannel.WEBCHAT
        )
        db.session.add(user_msg)
        conversation.last_message_at = datetime.utcnow()
        db.session.commit()
        conv_id_safe = conversation.id
        
        # Set Context for Tools
        from routing import g
        g.current_conversation = conversation
        g.current_company = company

        # Invoke Agent Service
        from services.agent_service import AgentService
        agent_service = AgentService(company)
        result = agent_service.process_message(
            conversation=conversation,
            user_message=message,
            channel='webchat',
            interface_language=interface_language
        )

        # Save AI response
        content = result.get('content')
        if content:
            ai_msg = Message(
                conversation_id=conv_id_safe,
                content=content,
                role=MessageRole.ASSISTANT,
                channel=MessageChannel.WEBCHAT
            )
            db.session.add(ai_msg)
            
            # Update conversation timestamp
            conv_obj = Conversation.query.get(conv_id_safe)
            if conv_obj:
                conv_obj.last_message_at = datetime.utcnow()
            db.session.commit()

        return jsonify({
            'data': {
                'content': content,
                'conversation_id': conv_id_safe,
                'action': result.get('action'),
                'action_data': result.get('action_data')
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Platform chat error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

