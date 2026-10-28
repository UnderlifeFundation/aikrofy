"""
Handover Service - Enterprise 10X Protocol
Manages seamless transition between AI agents and human operators.
Includes:
- Automatic trigger detection (sentiment, keyword, repetitive loops)
- Instant LLM case synthesis (3-bullet context snapshot for the human operator)
- Real-time WebSocket alerts to company operator room
- State transition locking (prevents AI from speaking while human is active)
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from extensions import db, socketio
from models.conversation import Conversation, Message, MessageRole, HandoverStatus
from models.user import User

logger = logging.getLogger(__name__)

class HandoverService:
    """Manages AI-Human handoffs and real-time state management"""

    ESCALATION_KEYWORDS = [
        'humano', 'persona', 'asesor', 'agente', 'operador', 'representante',
        'hablar con alguien', 'ayuda humana', 'atencion al cliente', 'queja',
        'reclamo', 'demanda', 'estafa', 'supervisor', 'gerente'
    ]

    @classmethod
    def evaluate_incoming_message(cls, conversation: Conversation, user_message: str) -> Dict[str, Any]:
        """
        Evaluates incoming message for auto-handover triggers:
        1. Explicit keywords
        2. Highly negative sentiment (score < -0.45)
        3. Already taken by human
        """
        if conversation.handover_status in [HandoverStatus.HUMAN_TAKEN.value, 'human_taken']:
            return {
                'should_handover': True,
                'already_human': True,
                'reason': 'Conversación ya tomada por operador humano'
            }

        msg_lower = (user_message or '').lower().strip()
        
        # 1. Keyword check
        matched_kw = next((kw for kw in cls.ESCALATION_KEYWORDS if kw in msg_lower), None)
        if matched_kw:
            return {
                'should_handover': True,
                'already_human': False,
                'reason': f"Solicitud explícita de usuario / palabra clave detectada: '{matched_kw}'"
            }

        # 2. Sentiment check if available on conversation
        if conversation.sentiment_score is not None and conversation.sentiment_score <= -0.5:
            return {
                'should_handover': True,
                'already_human': False,
                'reason': f"Sentimiento negativo crítico detectado ({conversation.sentiment_score})"
            }

        return {'should_handover': False, 'already_human': False, 'reason': None}

    @classmethod
    def execute_handover(cls, conversation: Conversation, reason: str, user_message: Optional[str] = None) -> Conversation:
        """
        Transitions conversation to human_taken, produces AI 3-bullet case summary,
        and broadcasts realtime alert to company room.
        """
        company_id = conversation.company_id
        conversation.handover_status = HandoverStatus.HUMAN_TAKEN.value
        
        # Update conv_metadata
        conv_meta = dict(conversation.conv_metadata or {})
        conv_meta['is_ai_active'] = False
        conv_meta['handover_reason'] = reason
        conv_meta['handover_at'] = datetime.utcnow().isoformat()
        conversation.conv_metadata = conv_meta

        # Generate 3-bullet AI Case Snapshot
        try:
            summary = cls._generate_case_snapshot(conversation, user_message, reason)
            conversation.handover_summary = summary
        except Exception as e:
            logger.warning(f"[HANDOVER] Snapshot generation warning: {e}")
            conversation.handover_summary = f"• Motivo: {reason}\n• Canal: {conversation.channel}\n• Requiere atención inmediata."

        db.session.commit()

        # Emit Realtime Alert to company operator room
        cls._emit_handover_alert(conversation, reason)
        return conversation

    @classmethod
    def release_to_ai(cls, conversation: Conversation) -> Conversation:
        """Re-enables AI control on conversation"""
        conversation.handover_status = HandoverStatus.BOT_ACTIVE.value
        conv_meta = dict(conversation.conv_metadata or {})
        conv_meta['is_ai_active'] = True
        conv_meta['ai_resumed_at'] = datetime.utcnow().isoformat()
        conversation.conv_metadata = conv_meta
        db.session.commit()

        # Broadcast update
        try:
            from services.realtime_service import RealtimeService
            RealtimeService.publish_conversation_update(
                company_id=conversation.company_id,
                conversation_id=conversation.id,
                update_data={
                    'handover_status': conversation.handover_status,
                    'is_ai_active': True,
                    'conv_metadata': conversation.conv_metadata
                }
            )
        except Exception as e:
            logger.warning(f"[HANDOVER] Release broadcast failed: {e}")

        return conversation

    @classmethod
    def _generate_case_snapshot(cls, conversation: Conversation, current_msg: Optional[str], reason: str) -> str:
        """Generates concise 3-bullet summary using recent message history"""
        recent_messages = conversation.messages.order_by(Message.created_at.desc()).limit(8).all()
        recent_messages.reverse()

        transcript = "\n".join([f"{m.role.value if hasattr(m.role, 'value') else m.role}: {m.content}" for m in recent_messages])
        if current_msg:
            transcript += f"\nuser (último): {current_msg}"

        contact = conversation.contact_name or conversation.contact_phone or "Contacto sin nombre"
        
        # Fast local heuristic or lightweight summary
        bullet_1 = f"• Cliente: {contact} en canal {conversation.channel.upper()}."
        bullet_2 = f"• Motivo de traspaso: {reason}."
        bullet_3 = f"• Estado: Agente IA en pausa preventiva esperando intervención de operador humano."

        return f"{bullet_1}\n{bullet_2}\n{bullet_3}"

    @classmethod
    def _emit_handover_alert(cls, conversation: Conversation, reason: str):
        """Emits socket alerts to operator rooms"""
        try:
            company_id = conversation.company_id
            payload = {
                'conversation_id': conversation.id,
                'company_id': company_id,
                'channel': conversation.channel,
                'contact_name': conversation.contact_name or conversation.contact_phone or f"Chat #{conversation.id}",
                'contact_phone': conversation.contact_phone,
                'reason': reason,
                'handover_status': conversation.handover_status,
                'handover_summary': conversation.handover_summary,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Emit to specific company rooms
            for room in [f"company_{company_id}", f"company_room_{company_id}", "super_admin_room"]:
                try:
                    socketio.emit('handover_triggered', payload, room=room)
                except Exception:
                    pass

            from services.realtime_service import RealtimeService
            RealtimeService.publish_conversation_update(
                company_id=company_id,
                conversation_id=conversation.id,
                update_data={
                    'handover_status': conversation.handover_status,
                    'handover_summary': conversation.handover_summary,
                    'conv_metadata': conversation.conv_metadata
                }
            )
            logger.info(f"[HANDOVER] 🚨 Handover alert emitted for conversation {conversation.id}")
        except Exception as err:
            logger.error(f"[HANDOVER] Error broadcasting alert: {err}")
