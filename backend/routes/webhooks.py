from routing import APIRouter, g, jsonify, request
"""
Webhook Routes for External Services
Handles incoming webhooks from Twilio, etc.
"""
import logging

from extensions import db

logger = logging.getLogger(__name__)
from models.channel import Channel, ChannelType, ChannelStatus
from models.conversation import Conversation, Message, ConversationType, MessageChannel, MessageRole
from services.customer_service import CustomerService
from services.google_risc_service import GoogleRiscService

# Optional Twilio imports
try:
    from twilio.twiml.messaging_response import MessagingResponse
    from twilio.twiml.voice_response import VoiceResponse
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    MessagingResponse = None
    VoiceResponse = None

import requests
import json

def send_meta_message(token, phone_id, to_phone, text):
    """Send WhatsApp message via Meta Graph API v21.0"""
    url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text}
    }
    try:
        res = requests.post(url, headers=headers, json=data, timeout=10)
        logger.info(f"[Meta Outbound Response] Status: {res.status_code}, Body: {res.text}")
    except Exception as e:
        logger.error(f"Error sending Meta message: {e}")

def _get_or_create_customer_for_conv(company_id, phone=None, email=None, name=None):
    """Internal helper to ensure a conversation is linked to a CRM contact"""
    if not phone and not email:
        return None
        
    data = {
        'phone': phone,
        'email': email
    }
    if name:
        # Try to parse name into first/last
        parts = name.split(' ', 1)
        data['first_name'] = parts[0]
        if len(parts) > 1:
            data['last_name'] = parts[1]
            
    try:
        customer = CustomerService.upsert_customer(company_id, data)
        return customer
    except Exception as e:
        print(f"Error auto-capturing customer in webhook: {e}")
        return None

webhooks_bp = APIRouter('webhooks', __name__)


@webhooks_bp.route('/google-risc', methods=['POST'])
def google_risc_webhook():
    """Handle incoming Google Cross-Account Protection (RISC) security events"""
    # Google posts the token as a raw body or data
    token = request.get_data(as_text=True)
    if not token:
        return jsonify({'error': 'Missing token'}), 400
        
    # Validate and process payload
    payload = GoogleRiscService.validate_risc_token(token)
    if not payload:
        # Status 400 is recommended in RISC docs for validation failures
        return jsonify({'error': 'Invalid or malformed token'}), 400
        
    # Handle the event internally (revoke sessions/tokens)
    GoogleRiscService.handle_event(payload)
    
    # RISC protocol requires 202 Accepted
    return jsonify({'status': 'accepted'}), 202


@webhooks_bp.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio — Fire-and-Forget async pattern.
    
    Immediately acknowledges Twilio (< 200ms) and enqueues AI processing to Celery
    to avoid Twilio 30s timeout that would cause message retransmission / duplicates.
    """
    # Get message details
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    body = request.values.get('Body', '')

    if not from_number or not body:
        resp = MessagingResponse()
        return str(resp)

    # Find the channel by phone number
    channel = Channel.query.filter(
        Channel.type == ChannelType.WHATSAPP,
        Channel.phone_number.like(f'%{to_number.replace("whatsapp:", "")}%')
    ).first()

    if not channel:
        logger.warning(f"[TWILIO WEBHOOK] No channel found for number {to_number}")
        resp = MessagingResponse()
        return str(resp)

    # Update channel activity
    channel.last_activity = db.func.now()

    # Deduplication — prevent Twilio retransmission creating duplicate tasks
    try:
        import hashlib
        from services.cache_service import CacheService
        twilio_msg_sid = request.values.get('MessageSid', '')
        if twilio_msg_sid:
            dedup_key = f"wa:dedup:twilio:{twilio_msg_sid}"
            if CacheService.get(dedup_key):
                logger.info(f"[TWILIO WEBHOOK] Duplicate MessageSid ignored: {twilio_msg_sid}")
                resp = MessagingResponse()
                return str(resp)
            CacheService.set(dedup_key, "1", ttl=120)
        # Content-hash fallback
        content_hash = hashlib.md5(f"{channel.company_id}:{from_number}:{body.strip().lower()}".encode()).hexdigest()
        hash_key = f"wa:dedup:hash:twilio:{content_hash}"
        if CacheService.get(hash_key):
            logger.info(f"[TWILIO WEBHOOK] Duplicate content hash ignored: {hash_key}")
            resp = MessagingResponse()
            return str(resp)
        CacheService.set(hash_key, "1", ttl=15)
    except Exception as dedup_err:
        logger.warning(f"[TWILIO WEBHOOK] Dedup check warning: {dedup_err}")

    # Normalize sender phone (remove 'whatsapp:' prefix)
    sender_phone = from_number.replace('whatsapp:', '').strip()

    # ===================================================================
    # EMPLOYEE DETECTION
    # ===================================================================
    from services.employee_detection_service import EmployeeDetectionService
    employee = EmployeeDetectionService.detect_employee(channel.company_id, from_number)
    is_employee = employee is not None
    conv_type = ConversationType.EMPLOYEE if is_employee else ConversationType.CUSTOMER

    # Find or create conversation
    conversation = Conversation.query.filter_by(
        company_id=channel.company_id,
        channel=MessageChannel.WHATSAPP,
        contact_phone=sender_phone
    ).first()

    customer = None
    if not conversation:
        if not is_employee:
            customer = _get_or_create_customer_for_conv(channel.company_id, phone=sender_phone)
        conversation = Conversation(
            company_id=channel.company_id,
            type=conv_type,
            channel=MessageChannel.WHATSAPP,
            contact_phone=sender_phone,
            contact_name=employee.name if is_employee else None,
            customer_id=customer.id if customer else None,
            conv_metadata={'is_employee': is_employee, 'employee_id': employee.id if is_employee else None}
        )
        db.session.add(conversation)
        db.session.flush()
    else:
        if is_employee and conversation.type != ConversationType.EMPLOYEE:
            conversation.type = ConversationType.EMPLOYEE
            db.session.flush()
        elif not is_employee and not conversation.customer_id:
            customer = _get_or_create_customer_for_conv(channel.company_id, phone=sender_phone)
            if customer:
                conversation.customer_id = customer.id
                db.session.flush()
        customer = conversation.customer if not is_employee else None

    # GCLID attribution — only for external customers
    if customer and body:
        try:
            from services.attribution_service import AttributionService
            AttributionService.process_message_for_reference_code(channel.company_id, customer.id, body)
        except Exception as gclid_err:
            logger.error(f"Twilio Webhook GCLID Reference Error: {gclid_err}")

    # Save incoming message
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=body,
        channel=MessageChannel.WHATSAPP
    )
    db.session.add(user_message)
    conversation.last_message_at = db.func.now()
    db.session.commit()

    # Sync User Message to HubSpot (non-blocking)
    try:
        from services.hubspot_sync_service import HubSpotSyncService
        HubSpotSyncService.sync_message_to_hubspot(channel.company_id, conversation, user_message)
    except Exception as hs_err:
        logger.error(f"HubSpot Inbound Sync Error (Twilio WA): {hs_err}")

    if is_employee:
        logger.info(f"[TWILIO WEBHOOK] 👤 Employee message from {employee.name} ({employee.role.value})")

    # ===================================================================
    # FIRE-AND-FORGET: Enqueue to Celery — respond to Twilio immediately
    # ===================================================================
    try:
        from celery_app import celery
        celery.send_task(
            'tasks.process_webhook_message',
            args=[channel.company_id, conversation.id, body, 'whatsapp', sender_phone],
            kwargs={'is_voice_input': False, 'provider': 'twilio'}
        )
        logger.info(f"[TWILIO WEBHOOK] ✅ Enqueued to Celery for conv={conversation.id}, phone={sender_phone}")
    except Exception as celery_err:
        logger.error(f"[TWILIO WEBHOOK] ❌ Celery enqueue failed: {celery_err}")

    # Return empty TwiML immediately — Twilio considers this a successful delivery
    resp = MessagingResponse()
    return str(resp)


@webhooks_bp.route('/whatsapp/baileys', methods=['POST'])
def whatsapp_baileys_webhook():
    """Handle incoming WhatsApp messages from Baileys (Node.js) — with employee detection"""
    data = request.get_json()
    
    company_id = data.get('companyId')
    msg_data = data.get('message', {})
    
    if not company_id or not msg_data:
        return jsonify({'error': 'Invalid payload'}), 400
        
    try:
        # 1. Parse Baileys Message
        key = msg_data.get('key', {})
        remote_jid = key.get('remoteJid', '')  # e.g. 1234567890@s.whatsapp.net
        remote_jid_alt = key.get('remoteJidAlt', '')
        
        if not remote_jid or 'status@broadcast' in remote_jid:
            return jsonify({'status': 'ignored'}), 200
        
        participant = key.get('participant', '') or key.get('participantAlt', '')
        participant_alt = key.get('participantAlt', '')

        # Broadcast list message support:
        # If remote_jid is a broadcast list (e.g. 1790119353@broadcast), the actual sender is in 'participant'
        if '@broadcast' in remote_jid and participant:
            target_jid = participant
            if '@lid' in participant and participant_alt and '@s.whatsapp.net' in participant_alt:
                target_jid = participant_alt
        else:
            target_jid = remote_jid
            if '@lid' in remote_jid and remote_jid_alt and '@s.whatsapp.net' in remote_jid_alt:
                target_jid = remote_jid_alt
             
        from_phone = target_jid.split('@')[0]
        
        # Extract text content
        content = ''
        w_message = msg_data.get('message', {})
        if 'conversation' in w_message:
            content = w_message['conversation']
        elif 'extendedTextMessage' in w_message:
            content = w_message['extendedTextMessage'].get('text', '')
        elif 'imageMessage' in w_message:
            img_msg = w_message['imageMessage']
            img_caption = img_msg.get('caption', '')
            content = f"[Image Message] {img_caption}".strip() if img_caption else '[Image Message]'
            logger.info(f"[WEBHOOK_BAILEYS] Received image message from {from_phone} with caption: {img_caption!r}")
        
        if not content:
            return jsonify({'status': 'ignored_no_text'}), 200

        # ─── Deduplication (WhatsApp Multi-Device / Burst protection) ───
        try:
            import hashlib
            from services.cache_service import CacheService
            msg_id = key.get('id')
            if msg_id:
                dedup_key = f"wa:dedup:msg:{company_id}:{msg_id}"
                if CacheService.get(dedup_key):
                    logger.info(f"[WEBHOOK_BAILEYS] Ignored duplicate message ID: {msg_id}")
                    return jsonify({'status': 'ignored_duplicate'}), 200
                CacheService.set(dedup_key, "1", ttl=60)
            
            content_hash = hashlib.md5(f"{company_id}:{from_phone}:{content.strip().lower()}".encode('utf-8')).hexdigest()
            hash_key = f"wa:dedup:hash:{content_hash}"
            if CacheService.get(hash_key):
                logger.info(f"[WEBHOOK_BAILEYS] Ignored duplicate message by content hash: {hash_key}")
                return jsonify({'status': 'ignored_burst'}), 200
            CacheService.set(hash_key, "1", ttl=5)
        except Exception as dedup_err:
            logger.warning(f"Dedup check warning: {dedup_err}")

        # 2. Find Channel
        channel = Channel.query.filter_by(
            company_id=company_id, 
            type=ChannelType.WHATSAPP
        ).first()
        
        if not channel:
            logger.warning(f"Baileys Webhook: Channel not found for company {company_id}")
            return jsonify({'error': 'Channel not found'}), 404

        # Update activity
        channel.last_activity = db.func.now()
        
        # ===================================================================
        # EMPLOYEE DETECTION: Check if sender is a registered team member
        # ===================================================================
        from services.employee_detection_service import EmployeeDetectionService
        employee = EmployeeDetectionService.detect_employee(int(company_id), from_phone)
        is_employee = employee is not None
        conv_type = ConversationType.EMPLOYEE if is_employee else ConversationType.CUSTOMER
        
        # 3. Conversation Management
        conversation = Conversation.query.filter_by(
            company_id=company_id,
            channel=MessageChannel.WHATSAPP,
            contact_phone=from_phone
        ).first()
        
        customer = None
        push_name = msg_data.get('pushName') or ''
        if not conversation:
            # Only create CRM contact for external clients, not employees
            if not is_employee:
                customer = _get_or_create_customer_for_conv(company_id, phone=from_phone)
            conversation = Conversation(
                company_id=company_id,
                type=conv_type,
                channel=MessageChannel.WHATSAPP,
                contact_phone=from_phone,
                contact_name=employee.name if is_employee else (push_name or None),
                customer_id=customer.id if customer else None,
                conv_metadata={
                    'is_employee': is_employee,
                    'employee_id': employee.id if is_employee else None,
                    'raw_jid': remote_jid,
                    'target_jid': target_jid,
                    'push_name': push_name
                }
            )
            db.session.add(conversation)
            db.session.flush()
        else:
            conv_meta = dict(conversation.conv_metadata or {})
            conv_meta.update({'raw_jid': remote_jid, 'target_jid': target_jid})
            if push_name:
                conv_meta['push_name'] = push_name
            # Update conversation type if employee status changed
            if is_employee and conversation.type != ConversationType.EMPLOYEE:
                conversation.type = ConversationType.EMPLOYEE
                conv_meta.update({'is_employee': True, 'employee_id': employee.id})
                db.session.flush()
            elif not is_employee:
                if not conversation.customer_id:
                    customer = _get_or_create_customer_for_conv(company_id, phone=from_phone)
                    if customer:
                        conversation.customer_id = customer.id
                        db.session.flush()
            conversation.conv_metadata = conv_meta
            customer = conversation.customer

        # Process campaign attribution — only for external customers
        if customer:
            referral_data = w_message.get('referral') or msg_data.get('referral')
            if referral_data:
                try:
                    from services.attribution_service import AttributionService
                    AttributionService.process_webhook_referral(company_id, customer.id, referral_data)
                except Exception as attr_err:
                    logger.error(f"Baileys Webhook Attribution Error: {attr_err}")

            if content:
                try:
                    from services.attribution_service import AttributionService
                    AttributionService.process_message_for_reference_code(company_id, customer.id, content)
                except Exception as gclid_err:
                    logger.error(f"Baileys Webhook GCLID Reference Error: {gclid_err}")
          # 4. Save User Message
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            channel=MessageChannel.WHATSAPP
        )
        db.session.add(user_msg)
        conversation.last_message_at = db.func.now()
        db.session.commit()

        # Sync User Message to HubSpot
        try:
            from services.hubspot_sync_service import HubSpotSyncService
            HubSpotSyncService.sync_message_to_hubspot(int(company_id), conversation, user_msg)
        except Exception as hs_err:
            logger.error(f"HubSpot Inbound Sync Error (Baileys WA): {hs_err}")
        
        if is_employee:
            logger.info(f"[WEBHOOK_BAILEYS] 👤 Employee message from {employee.name} ({employee.role.value})")
        
        # 5. Agent Processing via LangGraph (with employee context)
        from services.langgraph_agent import LangGraphAgentService
        langgraph_service = LangGraphAgentService(channel.company)
        
        employee_context_addon = None
        if is_employee:
            company_name = channel.company.name if channel.company else ''
            # Resolve department name for enriched context
            dept_name = ''
            if hasattr(employee, 'department_id') and employee.department_id:
                try:
                    from models.department import Department
                    dept_obj = Department.query.get(employee.department_id)
                    if dept_obj:
                        dept_name = dept_obj.name
                except Exception:
                    pass
            dept_name = dept_name or (employee.department or '')
            employee_context_addon = EmployeeDetectionService.get_employee_system_prompt_addon(
                employee, company_name, department_name=dept_name
            )
        
        employee_role = (employee.role.value if hasattr(employee.role, 'value') else str(employee.role)) if is_employee and employee else 'customer'
        response_data = langgraph_service.process_message(
            conversation=conversation,
            user_message=content,
            channel='whatsapp',
            is_employee=is_employee,
            user_role=employee_role if is_employee else 'customer',
            employee_context_addon=employee_context_addon
        )
        
        assistant_response = response_data.get('content')
        
        if assistant_response:
            # 1. Send Reply via Baileys (priority — do this before saving to DB)
            try:
                from services.whatsapp_service import WhatsAppBaileysService
                baileys = WhatsAppBaileysService(str(company_id))
                # FIX: Send to exact reply_jid (target_jid) so if user wrote from LID, reply targets LID
                baileys.send_message(target_jid, assistant_response)
            except Exception as send_err:
                logger.error(f"Error sending Baileys WhatsApp reply: {send_err}")
 
            # 2. Save Assistant Message to DB
            try:
                asst_msg = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=assistant_response,
                    channel=MessageChannel.WHATSAPP,
                    tool_calls=response_data.get('tool_calls', [])
                )
                db.session.add(asst_msg)
                db.session.commit()

                # Sync Assistant Message to HubSpot
                try:
                    from services.hubspot_sync_service import HubSpotSyncService
                    HubSpotSyncService.sync_message_to_hubspot(int(company_id), conversation, asst_msg)
                except Exception as hs_err:
                    logger.error(f"HubSpot Outbound Sync Error (Baileys WA): {hs_err}")
            except Exception as db_err:
                logger.error(f"DB Error saving assistant message: {db_err}")
                db.session.rollback()
            
    except Exception as e:
        logger.error(f"Baileys Webhook Error: {e}")
        return jsonify({'error': str(e)}), 500
        
    return jsonify({'status': 'ok'}), 200


@webhooks_bp.route('/voice', methods=['POST'])
def voice_webhook():
    """Handle incoming voice calls from Twilio"""
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    call_sid = request.values.get('CallSid', '')
    
    # Find the channel
    channel = Channel.query.filter(
        Channel.type == ChannelType.VOICE,
        Channel.phone_number.like(f'%{to_number}%')
    ).first()
    
    resp = VoiceResponse()
    
    if not channel:
        resp.say("This number is not configured. Goodbye.")
        resp.hangup()
        return str(resp)
    
    # Update channel activity
    channel.last_activity = db.func.now()
    
    # Create conversation for the call
    conversation = Conversation(
        company_id=channel.company_id,
        type=ConversationType.CUSTOMER,
        channel=MessageChannel.VOICE,
        contact_phone=from_number,
        conv_metadata={'call_sid': call_sid}
    )
    db.session.add(conversation)
    db.session.commit()
    
    # Get company agent name
    agent_name = channel.company.agent_name if channel.company else "the assistant"
    
    # Voice response with gather for input
    resp.say(f"Hello! You've reached {agent_name}. How can I help you today?")
    
    # Gather speech input
    gather = resp.gather(
        input='speech',
        action='/webhooks/voice/process',
        timeout=5,
        speech_timeout='auto'
    )
    gather.say("Please tell me how I can assist you.")
    
    # If no input, prompt again
    resp.say("I didn't catch that. Please try again.")
    resp.redirect('/webhooks/voice')
    
    return str(resp)


@webhooks_bp.route('/voice/process', methods=['POST'])
def voice_process():
    """Process voice input with AgentService"""
    speech_result = request.values.get('SpeechResult', '')
    call_sid = request.values.get('CallSid', '')
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    
    resp = VoiceResponse()
    
    if not speech_result:
        resp.say("I'm sorry, I couldn't understand. Let me transfer you to a team member.")
        resp.say("Thank you for calling. Goodbye!")
        resp.hangup()
        return str(resp)
    
    # Find the channel for this call
    channel = Channel.query.filter(
        Channel.type == ChannelType.VOICE,
        Channel.phone_number.like(f'%{to_number}%')
    ).first()
    
    if not channel:
        resp.say("I'm sorry, this line is not configured. Goodbye.")
        resp.hangup()
        return str(resp)
    
    try:
        # Find or create conversation for this call
        conversation = Conversation.query.filter_by(
            company_id=channel.company_id,
            channel=MessageChannel.VOICE,
            conv_metadata={'call_sid': call_sid}
        ).first()
        
        if not conversation:
            conversation = Conversation(
                company_id=channel.company_id,
                type=ConversationType.CUSTOMER,
                channel=MessageChannel.VOICE,
                contact_phone=from_number,
                conv_metadata={'call_sid': call_sid}
            )
            db.session.add(conversation)
            db.session.flush()
        
        # Save user's speech as message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=speech_result,
            channel=MessageChannel.VOICE
        )
        db.session.add(user_message)
        conversation.last_message_at = db.func.now()
        db.session.commit()
        
        # Process with AgentService
        from services.agent_service import AgentService
        agent_service = AgentService(channel.company)
        
        response_data = agent_service.process_message(
            conversation=conversation,
            user_message=speech_result,
            agent=None,
            channel='voice'
        )
        
        assistant_response = response_data.get('content')
        
        if not assistant_response:
            assistant_response = "I'm processing your request. Is there anything else I can help you with?"
        
        # Save assistant response
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=assistant_response,
            channel=MessageChannel.VOICE,
            tool_calls=response_data.get('tool_calls', [])
        )
        db.session.add(assistant_message)
        db.session.commit()
        
        # Say the response
        resp.say(assistant_response)
        
        # Gather more input
        gather = resp.gather(
            input='speech',
            action='/webhooks/voice/process',
            timeout=5,
            speech_timeout='auto'
        )
        gather.say("Is there anything else I can help you with?")
        
        # If no input, end call
        resp.say("Thank you for calling. Goodbye!")
        resp.hangup()
        
    except Exception as e:
        print(f"Error processing voice: {e}")
        resp.say("I apologize, but I'm having trouble processing your request. Let me transfer you to a team member.")
        resp.say("Thank you for calling. Goodbye!")
        resp.hangup()
    
    return str(resp)


@webhooks_bp.route('/sms', methods=['POST'])
def sms_webhook():
    """Handle incoming SMS from Twilio"""
    from_number = request.values.get('From', '')
    to_number = request.values.get('To', '')
    body = request.values.get('Body', '')
    
    # Find the channel
    channel = Channel.query.filter(
        Channel.type == ChannelType.SMS,
        Channel.phone_number.like(f'%{to_number}%')
    ).first()
    
    if not channel:
        resp = MessagingResponse()
        resp.message("This number is not configured.")
        return str(resp)
    
    # Update channel activity
    channel.last_activity = db.func.now()
    
    # Find or create conversation
    conversation = Conversation.query.filter_by(
        company_id=channel.company_id,
        channel=MessageChannel.SMS,
        contact_phone=from_number
    ).first()
    
    if not conversation:
        customer = _get_or_create_customer_for_conv(channel.company_id, phone=from_number)
        conversation = Conversation(
            company_id=channel.company_id,
            type=ConversationType.CUSTOMER,
            channel=MessageChannel.SMS,
            contact_phone=from_number,
            customer_id=customer.id if customer else None
        )
        db.session.add(conversation)
        db.session.flush()
    elif not conversation.customer_id:
        customer = _get_or_create_customer_for_conv(channel.company_id, phone=from_number)
        if customer:
            conversation.customer_id = customer.id
            db.session.flush()
    
    # Save incoming message
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=body,
        channel=MessageChannel.SMS
    )
    db.session.add(user_message)
    conversation.last_message_at = db.func.now()
    db.session.commit()
    
    # Process with AgentService
    try:
        from services.agent_service import AgentService
        agent_service = AgentService(channel.company)
        
        # Generate AI response
        response_data = agent_service.process_message(
            conversation=conversation,
            user_message=body,
            agent=None,
            channel='sms'
        )
        
        assistant_response = response_data.get('content')
        
        # Handle tool-only responses (no content)
        if not assistant_response and response_data.get('tool_calls'):
            # If agent executed tools but gave no text, give a generic confirmation
            tool_names = [t.get('tool', 'unknown') for t in response_data['tool_calls']]
            assistant_response = f"I'm processing your request: {', '.join(tool_names)}. I'll follow up shortly."
            
        if assistant_response:
            # Save assistant response to DB
            assistant_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=assistant_response,
                channel=MessageChannel.SMS,
                tool_calls=response_data.get('tool_calls', [])
            )
            db.session.add(assistant_message)
            db.session.commit()
            
            # Send response via Twilio TwiML
            resp = MessagingResponse()
            resp.message(assistant_response)
            return str(resp)
            
    except Exception as e:
        logger.error(f"Error processing SMS agent response: {e}")
        # Fallback to generic response
        resp = MessagingResponse()
        resp.message("Thank you for your message. We'll get back to you soon.")
        return str(resp)

    return str(MessagingResponse())


@webhooks_bp.route('/status', methods=['POST'])
def status_webhook():
    """Handle status callbacks from Twilio"""
    message_sid = request.values.get('MessageSid', '')
    message_status = request.values.get('MessageStatus', '')
    
    # Log status update
    # TODO: Update message status in database
    
    return jsonify({'status': 'received'})


import uuid

@webhooks_bp.route('/meta-data-deletion', methods=['POST', 'GET'])
def meta_data_deletion_webhook():
    """Handle Meta User Data Deletion Request (GDPR / Meta Compliance)"""
    confirmation_code = f"del_{uuid.uuid4().hex[:12]}"
    from config import Config
    frontend_url = getattr(Config, 'FRONTEND_URL', 'https://app.aikrofy.com').rstrip('/')
    status_url = f"{frontend_url}/privacy"
    
    return jsonify({
        'url': status_url,
        'confirmation_code': confirmation_code
    }), 200


@webhooks_bp.route('/meta', methods=['GET', 'POST'])
def meta_webhook():

    """Handle incoming WhatsApp messages from Meta (Cloud API)"""
    
    # 1. Verification Request (GET)
    if request.method == 'GET':
        mode = request.values.get('hub.mode')
        token = request.values.get('hub.verify_token')
        challenge = request.values.get('hub.challenge')
        
        if mode == 'subscribe' and token:
            # 1. Check against global fallback in config/env
            from config import Config
            global_verify_token = getattr(Config, 'META_VERIFY_TOKEN', None)
            if global_verify_token and token == global_verify_token:
                return challenge, 200

            # 2. Check against channel specific credentials
            channels = Channel.query.filter_by(type=ChannelType.WHATSAPP).all()
            for channel in channels:
                creds = channel.credentials or {}
                if creds.get('verify_token') == token:
                    return challenge, 200
            
            return 'Forbidden', 403
        return 'BadRequest', 400



    # 2. Event Notification (POST)
    data = request.get_json()
    
    try:
        entry = data.get('entry', [])[0]
        changes = entry.get('changes', [])[0]
        value = changes.get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            return jsonify({'status': 'ok'}), 200 # Likely a status update
            
        message = messages[0]
        metadata = value.get('metadata', {})
        phone_number_id = metadata.get('phone_number_id')
        
        # Find channel by phone_number_id
        # Strict matching: First check channel credentials for exact phone_number_id & active provider 'meta'
        channels = Channel.query.filter_by(type=ChannelType.WHATSAPP).all()
        channel = None
        for c in channels:
            creds = c.credentials or {}
            if str(creds.get('phone_number_id')) == str(phone_number_id) and creds.get('provider') == 'meta':
                channel = c
                break
        
        # Fallback: check other channels credentials or company api_keys only if channel's active provider is meta
        if not channel:
            for c in channels:
                creds = c.credentials or {}
                comp_keys = c.company.api_keys or {} if c.company else {}
                if str(creds.get('phone_number_id')) == str(phone_number_id):
                    channel = c
                    break
                if str(comp_keys.get('meta_phone_id')) == str(phone_number_id) and comp_keys.get('whatsapp_provider') == 'meta':
                    channel = c
                    break
        
        if not channel:
            logger.warning(f"Meta Webhook: No channel found for ID {phone_number_id}")
            return jsonify({'status': 'error', 'message': 'Channel not found'}), 404
            
        # Update activity
        channel.last_activity = db.func.now()
        
        # Extract Message Details
        from_number = message.get('from') # User's WhatsApp number
        meta_msg_id = message.get('id', '')
        body = ''
        if message.get('type') == 'text':
            body = message['text']['body']
        else:
            body = f"[{message.get('type')} message]"

        if not body or not from_number:
            return jsonify({'status': 'ok'}), 200

        # ===================================================================
        # DEDUPLICATION: Prevent Meta retransmissions from creating duplicates
        # Meta may re-send the same webhook if it doesn't receive a timely 200.
        # We use message_id as primary key and content-hash as fallback.
        # ===================================================================
        try:
            import hashlib
            from services.cache_service import CacheService
            if meta_msg_id:
                meta_dedup_key = f"wa:dedup:meta:{meta_msg_id}"
                if CacheService.get(meta_dedup_key):
                    logger.info(f"[META WEBHOOK] Duplicate Meta message_id ignored: {meta_msg_id}")
                    return jsonify({'status': 'ok'}), 200
                CacheService.set(meta_dedup_key, "1", ttl=120)
            # Content-hash fallback
            content_hash = hashlib.md5(f"{channel.company_id}:{from_number}:{body.strip().lower()}".encode()).hexdigest()
            hash_key = f"wa:dedup:hash:meta:{content_hash}"
            if CacheService.get(hash_key):
                logger.info(f"[META WEBHOOK] Duplicate content hash ignored: {hash_key}")
                return jsonify({'status': 'ok'}), 200
            CacheService.set(hash_key, "1", ttl=15)
        except Exception as dedup_err:
            logger.warning(f"[META WEBHOOK] Dedup check warning: {dedup_err}")


        # ===================================================================
        # EMPLOYEE DETECTION: Check if sender is a registered team member
        # ===================================================================
        from services.employee_detection_service import EmployeeDetectionService
        employee = EmployeeDetectionService.detect_employee(int(channel.company_id), from_phone=from_number)
        is_employee = employee is not None
        conv_type = ConversationType.EMPLOYEE if is_employee else ConversationType.CUSTOMER

        # Find/Create Conversation
        conversation = Conversation.query.filter_by(
            company_id=channel.company_id,
            channel=MessageChannel.WHATSAPP,
            contact_phone=from_number
        ).first()
        
        customer = None
        if not conversation:
            if not is_employee:
                customer = _get_or_create_customer_for_conv(channel.company_id, phone=from_number)
            conversation = Conversation(
                company_id=channel.company_id,
                type=conv_type,
                channel=MessageChannel.WHATSAPP,
                contact_phone=from_number,
                contact_name=employee.name if is_employee else None,
                customer_id=customer.id if customer else None,
                conv_metadata={'is_employee': is_employee, 'employee_id': employee.id if is_employee else None}
            )
            db.session.add(conversation)
            db.session.flush()
        else:
            if is_employee and conversation.type != ConversationType.EMPLOYEE:
                conversation.type = ConversationType.EMPLOYEE
                db.session.flush()
            elif not is_employee:
                if not conversation.customer_id:
                    customer = _get_or_create_customer_for_conv(channel.company_id, phone=from_number)
                    if customer:
                        conversation.customer_id = customer.id
                        db.session.flush()
                customer = conversation.customer

        # Process campaign attribution if customer is present
        if customer:
            referral_data = message.get('referral')
            if referral_data:
                try:
                    from services.attribution_service import AttributionService
                    AttributionService.process_webhook_referral(channel.company_id, customer.id, referral_data)
                except Exception as attr_err:
                    logger.error(f"Meta Webhook Attribution Error: {attr_err}")

            if body:
                try:
                    from services.attribution_service import AttributionService
                    AttributionService.process_message_for_reference_code(channel.company_id, customer.id, body)
                except Exception as gclid_err:
                    logger.error(f"Meta Webhook GCLID Reference Error: {gclid_err}")
            
        # Save User Message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=body,
            channel=MessageChannel.WHATSAPP
        )
        db.session.add(user_message)
        conversation.last_message_at = db.func.now()
        db.session.commit()

        # Sync User Message to HubSpot (non-blocking)
        try:
            from services.hubspot_sync_service import HubSpotSyncService
            HubSpotSyncService.sync_message_to_hubspot(int(channel.company_id), conversation, user_message)
        except Exception as hs_err:
            logger.error(f"HubSpot Inbound Sync Error (Meta WA): {hs_err}")

        if is_employee:
            logger.info(f"[META WEBHOOK] 👤 Employee message from {employee.name} ({employee.role.value})")

        # ===================================================================
        # FIRE-AND-FORGET: Enqueue to Celery — respond to Meta immediately
        # Meta requires a 200 response within 20 seconds; synchronous AI
        # processing can take 10-30s → must offload to Celery.
        # ===================================================================
        try:
            from celery_app import celery
            celery.send_task(
                'tasks.process_webhook_message',
                args=[channel.company_id, conversation.id, body, 'whatsapp', from_number],
                kwargs={'is_voice_input': False, 'provider': 'meta'}
            )
            logger.info(f"[META WEBHOOK] ✅ Enqueued to Celery for conv={conversation.id}, phone={from_number}")
        except Exception as celery_err:
            logger.error(f"[META WEBHOOK] ❌ Celery enqueue failed: {celery_err}")

    except Exception as e:
        logger.error(f"Meta Webhook Parse Error: {e}")
        return jsonify({'status': 'error'}), 500

    return jsonify({'status': 'received'}), 200



@webhooks_bp.route('/telegram/<int:channel_id>', methods=['POST'])
def telegram_webhook(channel_id):
    """Handle incoming Telegram messages"""
    channel = Channel.query.get(channel_id)
    if not channel or channel.type != ChannelType.TELEGRAM:
        return jsonify({'error': 'Invalid channel'}), 404
        
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'status': 'ok'}), 200 # Ignore non-message updates
        
    msg = data['message']
    chat_id = str(msg.get('chat', {}).get('id', ''))
    user_name = msg.get('from', {}).get('first_name', 'Unknown')
    text = msg.get('text', '')
    
    if not text or not chat_id:
        return jsonify({'status': 'ok'}), 200 # Ignore non-text updates

    # Deduplication: Prevent Telegram retransmission / burst duplicate processing
    try:
        from services.cache_service import CacheService
        update_id = data.get('update_id')
        if update_id:
            dedup_key = f"tg:dedup:upd:{channel_id}:{update_id}"
            if CacheService.get(dedup_key):
                print(f"[TELEGRAM] Ignored duplicate update_id: {update_id}")
                return jsonify({'status': 'ok'}), 200
            CacheService.set(dedup_key, "1", timeout=120)

        msg_id = msg.get('message_id')
        if msg_id:
            msg_dedup_key = f"tg:dedup:msg:{channel_id}:{chat_id}:{msg_id}"
            if CacheService.get(msg_dedup_key):
                print(f"[TELEGRAM] Ignored duplicate message_id: {msg_id} in chat: {chat_id}")
                return jsonify({'status': 'ok'}), 200
            CacheService.set(msg_dedup_key, "1", timeout=120)
    except Exception as dedup_e:
        print(f"[TELEGRAM] Dedup check warning: {dedup_e}")

    # Update Channel Activity
    channel.last_activity = db.func.now()
    
    # Conversation
    # Store Chat ID in contact_phone field for consistency
    print(f"[TELEGRAM DEBUG] Looking for conversation: company_id={channel.company_id}, channel=TELEGRAM, contact_phone={chat_id}")
    conversation = Conversation.query.filter_by(
        company_id=channel.company_id,
        channel=MessageChannel.TELEGRAM,
        contact_phone=str(chat_id) 
    ).first()
    print(f"[TELEGRAM DEBUG] Found conversation: {conversation.id if conversation else 'None'}")
    
    if not conversation:
        customer = _get_or_create_customer_for_conv(channel.company_id, phone=chat_id, name=user_name)
        conversation = Conversation(
            company_id=channel.company_id,
            type=ConversationType.CUSTOMER,
            channel=MessageChannel.TELEGRAM,
            contact_phone=str(chat_id),
            contact_name=user_name,
            customer_id=customer.id if customer else None
        )
        db.session.add(conversation)
        db.session.flush()
    elif not conversation.customer_id:
        customer = _get_or_create_customer_for_conv(channel.company_id, phone=chat_id, name=user_name)
        if customer:
            conversation.customer_id = customer.id
            db.session.flush()
        
    # User Message
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=text,
        channel=MessageChannel.TELEGRAM
    )
    db.session.add(user_message)
    conversation.last_message_at = db.func.now()
    db.session.commit()

    # Sync User Message to HubSpot
    try:
        from services.hubspot_sync_service import HubSpotSyncService
        HubSpotSyncService.sync_message_to_hubspot(channel.company_id, conversation, user_message)
    except Exception as hs_err:
        logger.error(f"HubSpot Inbound Sync Error (Telegram): {hs_err}")
    
    # Agent Processing
    try:
        from services.agent_service import AgentService
        agent_service = AgentService(channel.company)
        
        response_data = agent_service.process_message(
             conversation=conversation,
             user_message=text,
             channel='telegram'
        )
        
        assistant_response = response_data.get('content')
        
        if assistant_response:
             # Save Assistant Message
             asst_msg = Message(
                 conversation_id=conversation.id,
                 role=MessageRole.ASSISTANT,
                 content=assistant_response,
                 channel=MessageChannel.TELEGRAM,
                 tool_calls=response_data.get('tool_calls', [])
             )
             db.session.add(asst_msg)
             db.session.commit()

             # Sync Assistant Message to HubSpot
             try:
                 from services.hubspot_sync_service import HubSpotSyncService
                 HubSpotSyncService.sync_message_to_hubspot(channel.company_id, conversation, asst_msg)
             except Exception as hs_err:
                 logger.error(f"HubSpot Outbound Sync Error (Telegram): {hs_err}")
             
             # Send Reply via Telegram API
             token = channel.credentials.get('telegram_token')
             requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                 'chat_id': chat_id,
                 'text': assistant_response
             })
             
    except Exception as e:
        print(f"Telegram Agent Error: {e}")
        
    return jsonify({'status': 'ok'}), 200


@webhooks_bp.route('/webchat/message', methods=['POST'])
def webchat_webhook():
    """
    Webhook for WebChat messages
    """
    # Force clean session start
    db.session.remove()
    
    data = request.get_json()
    widget_id = data.get('widget_id')
    text = data.get('message')
    user_identifier = data.get('user_id', 'guest')
    
    if not widget_id or not text:
        return jsonify({'error': 'Missing widget_id or message'}), 400

    # Burst deduplication for WebChat (protect against rapid double-clicks)
    import hashlib
    from services.cache_service import CacheService
    content_hash = hashlib.md5(f"webchat:{widget_id}:{user_identifier}:{str(text).strip()}".encode('utf-8')).hexdigest()
    burst_cache_key = f"webchat_burst:{content_hash}"
    if CacheService.get(burst_cache_key):
        print(f"[WebChat] Ignored duplicate burst message from user {user_identifier}")
        return jsonify({'status': 'ignored', 'reason': 'duplicate_burst'}), 200
    CacheService.set(burst_cache_key, "1", timeout=5)
        
    # Find Channel by widget_id
    channels = Channel.query.filter_by(type=ChannelType.WEBCHAT).all()
    channel = None
    for c in channels:
        credentials = c.credentials if isinstance(c.credentials, dict) else {}
        if credentials.get('widget_id') == widget_id or credentials.get('legacy_widget_id') == widget_id:
            channel = c
            break
            
    if not channel:
        return jsonify({'error': 'Invalid widget_id'}), 404
        
    # Find or Create Conversation
    conversation = Conversation.query.filter_by(
        company_id=channel.company_id,
        channel=MessageChannel.WEBCHAT.value,
        contact_phone=str(user_identifier),
        is_active=True
    ).first()
    
    if not conversation:
        conversation = Conversation(
            company_id=channel.company_id,
            channel=MessageChannel.WEBCHAT.value,
            contact_phone=str(user_identifier),
            is_active=True,
            type=ConversationType.CUSTOMER
        )
        db.session.add(conversation)
        db.session.flush()
        
    # Ensure ephemeral customer/prospect is created immediately for this session
    if not conversation.customer_id:
        from models.customer import Customer
        customer = Customer.query.filter_by(
            company_id=channel.company_id,
            phone=str(user_identifier)
        ).first()
        
        if not customer:
            customer = Customer(
                company_id=channel.company_id,
                first_name="Visitante Webchat",
                last_name=str(user_identifier)[:12],
                phone=str(user_identifier),
                is_ai_active=True
            )
            db.session.add(customer)
            db.session.flush()
            
        conversation.customer_id = customer.id
        db.session.commit()
        
    # Set Context for Tools
    
    g.current_conversation = conversation
    if channel and channel.company:
        g.current_company = channel.company
    
    # Store site context and detected capabilities in conversation metadata
    current_page = data.get('current_page')
    current_url = data.get('current_url') or data.get('url')
    host_domain = data.get('host_domain') or data.get('origin')
    page_title = data.get('page_title')
    page_content = data.get('page_content')
    site_structure = data.get('site_structure')
    site_capabilities = data.get('site_capabilities') or {}
    
    meta = dict(conversation.conv_metadata or {})
    if current_page:
        meta['current_page'] = current_page
    if current_url:
        meta['current_url'] = current_url
    if host_domain:
        meta['host_domain'] = host_domain
    if page_title:
        meta['page_title'] = page_title
    if page_content:
        meta['page_content'] = page_content
    if site_structure:
        meta['site_structure'] = site_structure
    if site_capabilities:
        meta['site_capabilities'] = site_capabilities
    conversation.conv_metadata = meta
    
    # Save User Message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=text,
        channel=MessageChannel.WEBCHAT
    )
    db.session.add(user_msg)
    conversation.last_message_at = db.func.now()
    db.session.commit()
    
    # Sync User Message to HubSpot
    try:
        from services.hubspot_sync_service import HubSpotSyncService
        HubSpotSyncService.sync_message_to_hubspot(channel.company_id, conversation, user_msg)
    except Exception as hs_err:
        print(f"HubSpot Inbound Sync Error (WebChat): {hs_err}")
    
    # Process with Agent
    try:
        from services.agent_service import AgentService
        agent_service = AgentService(channel.company)
        
        response_data = agent_service.process_message(
            conversation=conversation,
            user_message=text,
            channel='webchat',
            thread_id=user_identifier # Use session ID as thread_id for exact context matching
        )
        
        assistant_text = response_data.get('content')
        if assistant_text:
             # Pre-fetch ID to avoid detached instance error during retry
             safe_conversation_id = conversation.id
             
             asst_msg = Message(
                 conversation_id=safe_conversation_id,
                 role=MessageRole.ASSISTANT,
                 content=assistant_text,
                 channel=MessageChannel.WEBCHAT,
                 tool_calls=response_data.get('tool_calls', [])
             )
             db.session.add(asst_msg)
             try:
                 db.session.commit()
             except Exception as db_err:
                 # Retry logic for "MySQL server has gone away"
                 print(f"WebChat DB Error (First Attempt): {db_err}")
                 db.session.rollback()
                 db.session.remove() # Force fresh connection
                 
                 # Re-attach/Re-create object for new session
                 asst_msg = Message(
                     conversation_id=safe_conversation_id, # Use stored ID
                     role=MessageRole.ASSISTANT,
                     content=assistant_text,
                     channel=MessageChannel.WEBCHAT,
                     tool_calls=response_data.get('tool_calls', [])
                 )
                 db.session.add(asst_msg)
                 db.session.commit()
                 
             # Sync Assistant Message to HubSpot
             try:
                 from services.hubspot_sync_service import HubSpotSyncService
                 HubSpotSyncService.sync_message_to_hubspot(channel.company_id, conversation, asst_msg)
             except Exception as hs_err:
                 print(f"HubSpot Outbound Sync Error (WebChat): {hs_err}")
             
             # Resolve agent name and branding
             agent_name = response_data.get('agent_name')
             if not agent_name:
                 try:
                     from models.agent import Agent
                     active_agent = Agent.query.filter_by(company_id=channel.company_id, is_active=True).order_by(Agent.priority.desc()).first()
                     agent_name = active_agent.name if active_agent else (getattr(channel.company, 'agent_name', None) or channel.company.name or 'Asistente')
                 except Exception:
                     agent_name = getattr(channel.company, 'agent_name', None) or (channel.company.name if channel.company else 'Asistente')
             
             company_name = channel.company.name if channel.company else 'Empresa'
             
             return jsonify({
                 'response': assistant_text,
                 'agent_name': agent_name,
                 'company_name': company_name,
                 'action': response_data.get('action'),
                 'action_data': response_data.get('action_data'),
                 'tool_calls': response_data.get('tool_calls', [])
             })
             
    except Exception as e:
        db.session.rollback()  # Limpiar transacción fallida
        print(f"WebChat Error: {e}")
        return jsonify({'error': 'Agent processing failed'}), 500
        
    return jsonify({'status': 'ok'}), 200

@webhooks_bp.route('/dlocal', methods=['POST'])
def dlocal_webhook():
    """
    Receive payment/subscription updates from dLocal Go.
    Handles:
      1. Subscription status updates (external_id = company_id)
      2. Credit Top-Up confirmations (external_id = "topup_{company_id}")
    """
    try:
        db.session.rollback()
    except:
        pass

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        print(f"dLocal Go Webhook Event: {data}")

        external_id = data.get('external_id', '')
        status = data.get('status')  # "CONFIRMED", "COMPLETED", "DECLINED", etc.
        payment_id = data.get('id') or data.get('payment_id')

        if not external_id:
            return jsonify({'status': 'ignored', 'reason': 'no external_id'}), 200

        # =============================================
        # CASE 1: Credit Top-Up Payment
        # =============================================
        if str(external_id).startswith('topup_'):
            try:
                company_id = int(str(external_id).replace('topup_', ''))
            except ValueError:
                print(f"Invalid topup external_id format: {external_id}")
                return jsonify({'status': 'ignored'}), 200

            from models.company import Company
            from models.transaction import Transaction, TransactionType, TransactionStatus
            
            company = Company.query.get(company_id)
            if not company:
                print(f"Top-up webhook: Company {company_id} not found")
                return jsonify({'status': 'ignored'}), 200

            if status in ['CONFIRMED', 'COMPLETED', 'ACTIVE', 'PAID']:
                # Find the pending transaction by provider_order_id or most recent pending top-up
                txn = None
                if payment_id:
                    txn = Transaction.query.filter_by(
                        company_id=company_id,
                        provider_order_id=str(payment_id),
                        transaction_type=TransactionType.CREDIT_TOP_UP.value
                    ).first()
                
                if not txn:
                    # Fallback: find most recent pending top-up for this company
                    txn = Transaction.query.filter_by(
                        company_id=company_id,
                        transaction_type=TransactionType.CREDIT_TOP_UP.value,
                        status=TransactionStatus.PENDING.value
                    ).order_by(Transaction.created_at.desc()).first()

                if txn and txn.status == TransactionStatus.PENDING.value:
                    # Grant the credits
                    credits_to_add = txn.credits_granted
                    company.credit_balance = (company.credit_balance or 0) + credits_to_add
                    txn.status = TransactionStatus.COMPLETED.value
                    if payment_id:
                        txn.provider_order_id = str(payment_id)
                    
                    db.session.commit()
                    print(f"✅ Top-up SUCCESS: Company {company_id} +{credits_to_add} credits. New balance: {company.credit_balance}")
                    return jsonify({'status': 'credits_granted', 'credits': credits_to_add}), 200
                else:
                    print(f"Top-up webhook: No matching pending transaction for company {company_id}")
                    return jsonify({'status': 'ignored', 'reason': 'no_pending_txn'}), 200

            elif status in ['DECLINED', 'CANCELLED', 'REJECTED']:
                # Mark transaction as failed
                txn = None
                if payment_id:
                    txn = Transaction.query.filter_by(
                        company_id=company_id,
                        provider_order_id=str(payment_id),
                        transaction_type=TransactionType.CREDIT_TOP_UP.value
                    ).first()
                if txn:
                    txn.status = TransactionStatus.FAILED.value
                    db.session.commit()
                logger.info(f"❌ Top-up FAILED: Company {company_id}. Status: {status}")
                return jsonify({'status': 'failed'}), 200

            return jsonify({'status': 'ignored'}), 200

        # =============================================
        # CASE 2: Subscription Payment (Legacy Flow)
        # =============================================
        try:
            company_id = int(external_id)
            from models.company import Company
            from models.subscription import Subscription, SubscriptionStatus
            company = Company.query.get(company_id)
            
            if company:
                print(f"dLocal Webhook -> Company {company_id}. Status: {status}")
                
                sub = Subscription.query.filter_by(company_id=company_id).first()
                if sub:
                    if status in ['CONFIRMED', 'COMPLETED', 'ACTIVE']:
                        sub.status = SubscriptionStatus.ACTIVE
                        
                        # Auto-grant base credits on subscription confirmation
                        if sub.plan and sub.plan.features:
                            base_credits = sub.plan.features.get('base_credits', 0)
                            if base_credits > 0:
                                company.credit_balance = (company.credit_balance or 0) + base_credits
                                print(f"✅ Subscription confirmed: +{base_credits} base credits for company {company_id}")
                        
                    elif status in ['DECLINED', 'CANCELLED', 'INACTIVE', 'PAST_DUE']:
                        sub.status = SubscriptionStatus.PAST_DUE
                    db.session.commit()
                    return jsonify({'status': 'processed'}), 200
                else:
                    print(f"No existing subscription found for company {company_id}")
            else:
                print(f"Company not found for external_id: {external_id}")
        except ValueError:
            print(f"Invalid external_id format: {external_id}")
                
        return jsonify({'status': 'ignored'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"dLocal Go webhook error: {e}")
        return jsonify({'error': str(e)}), 500


@webhooks_bp.route('/paddle', methods=['POST'])
def paddle_webhook():
    """
    Receive payment/subscription updates from Paddle Billing v2.
    Handles:
      - transaction.completed (for credit top-ups and subscriptions)
      - subscription.created / subscription.updated (for subscription lifecycle)
    """
    try:
        db.session.rollback()
    except:
        pass

    try:
        # Get raw body bytes and signature header for verification
        raw_body_bytes = request.get_data()
        signature_header = request.headers.get('Paddle-Signature')
        
        # Verify Paddle Signature
        from services.paddle_service import PaddleService
        paddle = PaddleService()
        
        if not paddle.verify_signature(raw_body_bytes, signature_header):
            logger.warning("Paddle webhook signature verification failed.")
            return jsonify({'error': 'Invalid signature'}), 401

        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'No data provided'}), 400

        logger.info(f"Paddle Webhook Event: {payload}")
        print(f"Paddle Webhook Event: {payload}")

        event_type = payload.get('event_type')
        data = payload.get('data', {})
        
        # In Paddle, custom values are passed via passthrough or custom_data
        passthrough = data.get('passthrough') or (data.get('custom_data', {}) if isinstance(data.get('custom_data'), dict) else {}).get('company_id')
        if not passthrough and 'custom_data' in data:
            passthrough = data.get('custom_data', {}).get('company_id')
            
        if not passthrough:
            # Check custom data in subscription or transaction object if nested
            passthrough = data.get('subscription', {}).get('custom_data', {}).get('company_id')

        if not passthrough:
            logger.info("Paddle Webhook ignored: no passthrough or company_id found")
            return jsonify({'status': 'ignored', 'reason': 'no passthrough'}), 200

        passthrough_str = str(passthrough)

        # =============================================
        # CASE 1: Credit Top-Up Payment
        # =============================================
        if passthrough_str.startswith('topup_'):
            try:
                company_id = int(passthrough_str.replace('topup_', ''))
            except ValueError:
                return jsonify({'status': 'ignored', 'reason': 'invalid topup company_id'}), 200

            from models.company import Company
            from models.transaction import Transaction, TransactionType, TransactionStatus
            
            company = Company.query.get(company_id)
            if not company:
                return jsonify({'status': 'ignored', 'reason': 'company not found'}), 200

            # If event_type is transaction.completed
            if event_type in ['transaction.completed', 'payment.succeeded']:
                # Find most recent pending transaction for this company
                txn = Transaction.query.filter_by(
                    company_id=company_id,
                    transaction_type=TransactionType.CREDIT_TOP_UP.value,
                    status=TransactionStatus.PENDING.value
                ).order_by(Transaction.created_at.desc()).first()

                if txn:
                    credits_to_add = txn.credits_granted
                    company.credit_balance = (company.credit_balance or 0) + credits_to_add
                    txn.status = TransactionStatus.COMPLETED.value
                    txn.provider_order_id = str(data.get('id', ''))
                    
                    db.session.commit()
                    print(f"✅ Paddle Top-up SUCCESS: Company {company_id} +{credits_to_add} credits. New balance: {company.credit_balance}")
                    return jsonify({'status': 'credits_granted', 'credits': credits_to_add}), 200
                else:
                    return jsonify({'status': 'ignored', 'reason': 'no pending topup txn'}), 200

        # =============================================
        # CASE 2: Subscription Payment / Update
        # =============================================
        else:
            try:
                company_id = int(passthrough_str)
            except ValueError:
                return jsonify({'status': 'ignored', 'reason': 'invalid company_id format'}), 200

            from models.company import Company
            from models.subscription import Subscription, SubscriptionStatus, Plan
            company = Company.query.get(company_id)
            
            if not company:
                return jsonify({'status': 'ignored', 'reason': 'company not found'}), 200

            # Identify the price/plan ID in Paddle
            items = data.get('items', [])
            price_id = None
            if items:
                price_id = items[0].get('price', {}).get('id') or items[0].get('price_id')

            # Find matching Plan in our DB
            plan = None
            if price_id:
                plan = Plan.query.filter((Plan.external_plan_token == price_id) | (Plan.external_plan_id == price_id)).first()
            
            # If no plan matches directly, try to map fallback sandbox price IDs
            if not plan and price_id:
                # Sandbox defaults mapping
                if price_id == 'pri_01j00000000000000000000001':
                    plan = Plan.query.filter_by(name='Jab').first()
                elif price_id == 'pri_01j00000000000000000000002':
                    plan = Plan.query.filter_by(name='Uppercut').first()
                elif price_id == 'pri_01j00000000000000000000003':
                    plan = Plan.query.filter_by(name='Knockout').first()

            if not plan:
                # If still no plan, fall back to first active plan
                plan = Plan.query.filter_by(is_active=True).first()

            # Find or create subscription for this company
            sub = Subscription.query.filter_by(company_id=company_id).first()
            if not sub:
                sub = Subscription(company_id=company_id, plan_id=plan.id if plan else 1)
                db.session.add(sub)

            status = data.get('status')
            
            if event_type in ['subscription.created', 'subscription.updated', 'transaction.completed']:
                # Update status
                sub.status = SubscriptionStatus.ACTIVE
                if plan:
                    sub.plan_id = plan.id

                # Grant base credits if active
                if plan and plan.features:
                    base_credits = plan.features.get('monthly_credits', plan.features.get('base_credits', 0))
                    if base_credits > 0:
                        company.credit_balance = (company.credit_balance or 0) + base_credits
                        print(f"✅ Paddle Subscription confirmed: +{base_credits} base credits for company {company_id}")

            elif event_type in ['subscription.canceled', 'subscription.paused']:
                sub.status = SubscriptionStatus.CANCELLED
            
            db.session.commit()
            print(f"Paddle Webhook processed for company {company_id}. Status: {sub.status.value}")
            return jsonify({'status': 'processed'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Paddle webhook error: {e}")
        return jsonify({'error': str(e)}), 500



