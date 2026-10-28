import os
import uuid
import logging
from datetime import datetime
from fastapi.responses import FileResponse

from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from extensions import db
from models.user import User, UserRole
from models.agent import Agent
from models.conversation import Conversation, ConversationType
from services.voice_service import VoiceService
from decorators import subscription_required

logger = logging.getLogger(__name__)
voice_bp = APIRouter('voice', __name__)

# Configure upload directory for voice files
UPLOAD_VOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'voice')

def ensure_voice_dir():
    if not os.path.exists(UPLOAD_VOICE_DIR):
        os.makedirs(UPLOAD_VOICE_DIR, exist_ok=True)

def get_user_company():
    """Helper to get current user's company"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None
        if user.company:
            return user.company
        if user.role == UserRole.SUPER_ADMIN:
            from models.company import Company
            return Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
        logger.warning(f"Voice API - User/Company missing for ID {user_id}")
        return None
    except Exception as e:
        logger.error(f"Voice API - Error fetching user company: {e}")
        return None

@voice_bp.route('/interact', methods=['POST'])
@jwt_required()
@subscription_required
def voice_interact():
    """
    Receives an audio blob, transcribes it, runs it through the AgentService,
    synthesizes the text response, and returns both transcription, response text, and audio URL.
    """
    try:
        ensure_voice_dir()
        company = get_user_company()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
            
        if 'file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
            
        audio_file = request.files['file']
        
        interface_language = request.form.get('interface_language') or request.values.get('interface_language') or 'en'

        # 1. Save input audio file
        input_filename = f"in_{uuid.uuid4().hex}.webm"
        input_path = os.path.join(UPLOAD_VOICE_DIR, input_filename)
        audio_file.save(input_path)
        
        # 2. Transcribe using VoiceService (Whisper)
        transcription = VoiceService.transcribe(input_path, language=interface_language)
        if not transcription or not transcription.strip():
            logger.warning(f"Transcription empty for audio file: {input_path}")
            transcription = "(Nota de voz inaudible)"
            
        # 3. Process transcription with AgentService
        channel_name = request.form.get('channel') or request.values.get('channel') or 'webchat'
        
        from models.conversation import MessageChannel, MessageRole, Message
        
        if channel_name == 'admin_chat':
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
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
        else:
            conversation = Conversation.query.filter_by(
                company_id=company.id,
                type=ConversationType.INTERNAL,
                channel='playground'
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    company_id=company.id,
                    type=ConversationType.INTERNAL,
                    channel='playground',
                    contact_name="Playground User",
                    contact_phone="playground_user"
                )
                db.session.add(conversation)
                db.session.flush()
        
        conversation.last_message_at = datetime.utcnow()
        
        # Save user message to the DB first
        user_message_db = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=transcription,
            channel=MessageChannel.ADMIN_CHAT if channel_name == 'admin_chat' else MessageChannel.PLAYGROUND
        )
        db.session.add(user_message_db)
        db.session.commit()
        
        from services.agent_service import AgentService
        agent_service = AgentService(company)
        is_employee = (channel_name == 'admin_chat')
        interface_language = request.form.get('interface_language') or request.values.get('interface_language') or 'en'
        
        agent_id = request.form.get('agent_id') or request.values.get('agent_id')
        from models.agent import AgentObjective
        
        if is_employee:
            agent = Agent.query.filter_by(
                company_id=company.id,
                is_active=True,
                objective=AgentObjective.INTERNAL
            ).first()
        elif agent_id:
            try:
                agent = Agent.query.filter_by(id=int(agent_id), company_id=company.id).first()
            except ValueError:
                agent = Agent.query.filter(
                    Agent.company_id == company.id,
                    Agent.is_active == True,
                    Agent.objective != AgentObjective.INTERNAL
                ).first()
        else:
            agent = Agent.query.filter(
                Agent.company_id == company.id,
                Agent.is_active == True,
                Agent.objective != AgentObjective.INTERNAL
            ).first()
        
        response_data = agent_service.process_message(
            conversation=conversation,
            user_message=transcription,
            agent=agent,
            channel=channel_name,
            is_employee=is_employee,
            interface_language=interface_language,
            user_role=user.role.value if hasattr(user.role, 'value') else str(user.role)
        )
        
        assistant_response = response_data.get('content')
        if not assistant_response and response_data.get('tool_calls'):
            tool_names = [t.get('tool', 'unknown') for t in response_data['tool_calls']]
            assistant_response = f"I am performing the following actions: {', '.join(tool_names)}..."
            
        if not assistant_response:
            assistant_response = "I apologize, but I couldn't generate a response."
            
        # Save assistant message using a fresh connection/session to prevent dropped connections
        from database import SessionLocal
        from sqlalchemy import text as sa_text
        
        fresh_session = SessionLocal()
        try:
            assistant_message_db = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=assistant_response,
                channel=MessageChannel.ADMIN_CHAT if channel_name == 'admin_chat' else MessageChannel.PLAYGROUND,
                tool_calls=response_data.get('tool_calls', [])
            )
            fresh_session.add(assistant_message_db)
            fresh_session.execute(
                sa_text('UPDATE conversations SET last_message_at = NOW() WHERE id = :id'),
                {'id': conversation.id}
            )
            fresh_session.commit()
        except Exception as se:
            fresh_session.rollback()
            logger.error(f"Failed to save voice interaction assistant response to DB: {se}")
        finally:
            fresh_session.close()
            
        # 4. Determine voice model/name and synthesize response (Edge-TTS)
        gender_val = company.agent_gender.value if company.agent_gender else 'neutral'
        voice_name = VoiceService.resolve_smart_voice(
            gender=gender_val,
            language=interface_language,
            preferred_voice=company.voice_model
        )
                
        output_filename = f"out_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(UPLOAD_VOICE_DIR, output_filename)
        success = VoiceService.synthesize(assistant_response, voice_name, output_path)
        
        # Deduct audio processing credits (STT reception + TTS synthesis) with 85% margin
        try:
            from services.token_credit_service import TokenCreditService
            voice_credit_calc = TokenCreditService.calculate_cost_and_credits(
                stt_requests=1,
                tts_characters=len(assistant_response or '')
            )
            v_credits = voice_credit_calc.get('credits_to_deduct', 1)
            TokenCreditService.deduct_company_credits(
                company,
                credits_to_deduct=v_credits,
                reason="voice_stt_tts_processing",
                db_session=db.session
            )
        except Exception as e_vcredits:
            logger.warning(f"Voice credit deduction error: {e_vcredits}")
        
        # Optionally clean up input file to save space
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as err:
            logger.warning(f"Failed to delete temporary input file: {err}")
            
        return jsonify({
            'transcription': transcription,
            'agent_response': assistant_response,
            'audio_url': f"/api/voice/audio/{output_filename}" if success else None,
            'action': response_data.get('action'),
            'action_data': response_data.get('action_data'),
            'success': True
        }), 200
        
    except Exception as e:
        logger.error(f"Error in voice interaction endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@voice_bp.route('/synthesize', methods=['POST'])
@jwt_required()
@subscription_required
def voice_synthesize():
    """
    Synthesize text to speech manually and return the audio file URL.
    """
    try:
        ensure_voice_dir()
        company = get_user_company()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
            
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        interface_language = data.get('interface_language') or 'es'
        gender_param = data.get('gender')
        gender_val = gender_param or (company.agent_gender.value if company.agent_gender else 'female')
        voice_name = data.get('voice')
        if not voice_name or voice_name == 'smart':
            voice_name = VoiceService.resolve_smart_voice(
                gender=gender_val,
                language=interface_language,
                preferred_voice=None if gender_param else company.voice_model
            )
            
        output_filename = f"out_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(UPLOAD_VOICE_DIR, output_filename)
        
        success = VoiceService.synthesize(text, voice_name, output_path)
        
        if success:
            return jsonify({
                'audio_url': f"/api/voice/audio/{output_filename}",
                'success': True
            }), 200
        else:
            return jsonify({'error': 'Voice synthesis failed', 'success': False}), 500
            
    except Exception as e:
        logger.error(f"Error in voice synthesis endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@voice_bp.route('/synthesize-public', methods=['POST'])
def voice_synthesize_public():
    """
    Public text to speech synthesis using intelligent gender-aware Edge-TTS voices.
    """
    try:
        ensure_voice_dir()
        data = request.get_json() or {}
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'Text is required'}), 400
            
        interface_language = data.get('interface_language') or 'es'
        widget_id = data.get('widget_id')
        gender_param = data.get('gender')
        voice_param = data.get('voice')

        voice_name = None

        # If widget_id is provided, resolve from company preferences
        if widget_id:
            try:
                from models.channel import Channel, ChannelType
                channels = Channel.query.filter(Channel.type == ChannelType.WEBCHAT).all()
                channel = next((c for c in channels if c.credentials and c.credentials.get('widget_id') == widget_id), None)
                if channel and channel.company:
                    co = channel.company
                    gender_val = co.agent_gender.value if co.agent_gender else 'female'
                    voice_name = VoiceService.resolve_smart_voice(
                        gender=gender_val,
                        language=interface_language,
                        preferred_voice=co.voice_model
                    )
            except Exception as w_err:
                logger.warning(f"Failed to lookup company for widget voice synthesis: {w_err}")

        if not voice_name:
            voice_name = VoiceService.resolve_smart_voice(
                gender=gender_param or 'female',
                language=interface_language,
                preferred_voice=voice_param
            )
        
        output_filename = f"out_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(UPLOAD_VOICE_DIR, output_filename)
        
        success = VoiceService.synthesize(text, voice_name, output_path)
        
        if success:
            return jsonify({
                'audio_url': f"/api/voice/audio/{output_filename}",
                'success': True
            }), 200
        else:
            return jsonify({'error': 'Voice synthesis failed', 'success': False}), 500
            
    except Exception as e:
        logger.error(f"Error in public voice synthesis endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@voice_bp.route('/transcribe-public', methods=['POST'])
def voice_transcribe_public():
    """
    Public audio transcription endpoint.
    """
    try:
        ensure_voice_dir()
        if 'file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
            
        audio_file = request.files['file']
        input_filename = f"in_pub_{uuid.uuid4().hex}.webm"
        input_path = os.path.join(UPLOAD_VOICE_DIR, input_filename)
        audio_file.save(input_path)
        
        interface_language = request.form.get('interface_language') or request.values.get('interface_language') or 'en'
        transcription = VoiceService.transcribe(input_path, language=interface_language)
        if not transcription or not transcription.strip():
            transcription = ""
            
        return jsonify({
            'text': transcription,
            'success': True
        }), 200
        
    except Exception as e:
        logger.error(f"Error in public transcription: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500

@voice_bp.route('/voices', methods=['GET'])
@jwt_required()
def list_voices():
    """
    Retrieve list of neural voices available for selection.
    """
    voices = VoiceService.get_voices()
    return jsonify({'voices': voices}), 200

@voice_bp.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """
    Serve generated neural audio files.
    """
    filepath = os.path.join(UPLOAD_VOICE_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Audio file not found'}), 404
    return FileResponse(filepath, media_type="audio/mpeg")
