from routing import current_app
"""
Auto-Escalation Service
Handles automatic escalation of conversations to human agents
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime



class EscalationService:
    """
    Auto-Escalation Service
    Monitors conversations and triggers escalation when needed
    """
    
    # Escalation reasons
    REASON_SENTIMENT = 'negative_sentiment'
    REASON_KEYWORD = 'escalation_keyword'
    REASON_REQUEST = 'explicit_request'
    REASON_TIMEOUT = 'no_resolution_timeout'
    REASON_COMPLEXITY = 'high_complexity'
    
    def __init__(self, company=None):
        self.company = company
        self._email_service = None
        self._twilio_service = None
        self._sentiment_service = None
    
    def _get_email_service(self):
        """Lazy load email service"""
        if not self._email_service:
            from services.email_service import EmailService
            self._email_service = EmailService(self.company)
        return self._email_service
    
    def _get_twilio_service(self):
        """Lazy load Twilio service"""
        if not self._twilio_service:
            from services.twilio_service import TwilioService
            self._twilio_service = TwilioService(self.company)
        return self._twilio_service
    
    def _get_sentiment_service(self):
        """Lazy load sentiment service"""
        if not self._sentiment_service:
            from services.sentiment_service import SentimentService
            self._sentiment_service = SentimentService(self.company)
        return self._sentiment_service
    
    def check_escalation_needed(
        self,
        conversation,
        last_message: str,
        sentiment_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Check if a conversation needs escalation
        
        Args:
            conversation: Conversation model instance
            last_message: The most recent user message
            sentiment_result: Optional pre-computed sentiment analysis
        
        Returns:
            Escalation check result with 'should_escalate' and 'reasons'
        """
        reasons = []
        score = 0  # Escalation score (higher = more urgent)
        
        # 1. Check explicit escalation request
        explicit_keywords = [
            'hablar con humano', 'persona real', 'agente real',
            'speak to human', 'real person', 'human agent',
            'gerente', 'supervisor', 'manager', 'supervisor'
        ]
        
        message_lower = last_message.lower()
        if any(kw in message_lower for kw in explicit_keywords):
            reasons.append({
                'type': self.REASON_REQUEST,
                'description': 'User explicitly requested human assistance'
            })
            score += 50
        
        # 2. Check sentiment
        if not sentiment_result:
            sentiment_service = self._get_sentiment_service()
            sentiment_result = sentiment_service.analyze_text(last_message)
        
        if sentiment_result.get('score', 0) < -0.5:
            reasons.append({
                'type': self.REASON_SENTIMENT,
                'description': f"Negative sentiment detected (score: {sentiment_result.get('score')})",
                'score': sentiment_result.get('score')
            })
            score += 30
        
        if sentiment_result.get('escalation_risk'):
            if self.REASON_KEYWORD not in [r['type'] for r in reasons]:
                reasons.append({
                    'type': self.REASON_KEYWORD,
                    'description': 'Escalation keywords detected in message'
                })
                score += 20
        
        # 3. Check conversation length (too many back-and-forths without resolution)
        from models.conversation import Message, MessageRole
        message_count = conversation.messages.count() if hasattr(conversation.messages, 'count') else len(list(conversation.messages))
        
        if message_count > 15:
            reasons.append({
                'type': self.REASON_COMPLEXITY,
                'description': f'Extended conversation ({message_count} messages) without resolution'
            })
            score += 15
        
        # Determine if escalation is needed
        should_escalate = score >= 30 or any(r['type'] == self.REASON_REQUEST for r in reasons)
        
        return {
            'should_escalate': should_escalate,
            'urgency_score': min(100, score),
            'reasons': reasons,
            'sentiment': sentiment_result
        }
    
    def get_available_employees(self, department: Optional[str] = None) -> List[Dict]:
        """
        Get available employees for escalation
        
        Args:
            department: Optional department filter
        
        Returns:
            List of available employees with contact info
        """
        from models.employee import Employee
        
        query = Employee.query.filter_by(company_id=self.company.id, is_active=True)
        
        if department:
            query = query.filter_by(department=department)
        
        # Filter by availability and preferences
        employees = query.filter(
            Employee.can_receive_escalations == True
        ).order_by(Employee.role.desc()).all()
        
        return [
            {
                'id': e.id,
                'name': e.name,
                'email': e.email,
                'phone': e.phone_number,
                'department': e.department,
                'can_receive_calls': e.can_receive_calls,
                'can_receive_messages': e.can_receive_messages
            }
            for e in employees
        ]
    
    def trigger_escalation(
        self,
        conversation,
        reason: str,
        urgency_score: int = 50,
        notify_methods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Trigger an escalation for a conversation
        
        Args:
            conversation: Conversation model instance
            reason: Reason for escalation
            urgency_score: Urgency level (0-100)
            notify_methods: Methods to use for notification ['email', 'sms', 'whatsapp']
        
        Returns:
            Escalation result
        """
        if notify_methods is None:
            notify_methods = ['email']  # Default to email only
        
        # Get available employees
        employees = self.get_available_employees()
        
        if not employees:
            return {
                'success': False,
                'error': 'No available employees for escalation',
                'conversation_id': conversation.id
            }
        
        # Select employee (first available, or could implement round-robin)
        selected_employee = employees[0]
        
        # Build escalation message
        escalation_message = self._build_escalation_message(
            conversation, reason, urgency_score
        )
        
        notifications_sent = []
        errors = []
        
        # Send notifications
        if 'email' in notify_methods and selected_employee.get('email'):
            try:
                email_service = self._get_email_service()
                email_service.send_email(
                    to=selected_employee['email'],
                    subject=f"🚨 Escalación [{urgency_score}%] - {self.company.name if self.company else 'Aikrofy'}",
                    body=escalation_message
                )
                notifications_sent.append('email')
            except Exception as e:
                errors.append(f"Email failed: {str(e)}")
        
        if 'sms' in notify_methods and selected_employee.get('phone') and selected_employee.get('can_receive_messages'):
            try:
                twilio_service = self._get_twilio_service()
                twilio_service.send_sms(
                    to=selected_employee['phone'],
                    body=f"🚨 Escalación [{urgency_score}%]: {reason[:100]}... Ver email para detalles."
                )
                notifications_sent.append('sms')
            except Exception as e:
                errors.append(f"SMS failed: {str(e)}")
        
        if 'whatsapp' in notify_methods and selected_employee.get('phone') and selected_employee.get('can_receive_messages'):
            try:
                twilio_service = self._get_twilio_service()
                twilio_service.send_whatsapp(
                    to=selected_employee['phone'],
                    body=escalation_message[:1600]  # WhatsApp limit
                )
                notifications_sent.append('whatsapp')
            except Exception as e:
                errors.append(f"WhatsApp failed: {str(e)}")
        
        # Update conversation status
        try:
            from extensions import db
            conversation.status = 'escalated'
            conversation.conv_metadata = conversation.conv_metadata or {}
            conversation.conv_metadata['escalation'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'reason': reason,
                'urgency': urgency_score,
                'assigned_to': selected_employee['id']
            }
            db.session.commit()
        except Exception:
            pass
        
        return {
            'success': True,
            'conversation_id': conversation.id,
            'assigned_employee': selected_employee['name'],
            'notifications_sent': notifications_sent,
            'errors': errors if errors else None
        }
    
    def _build_escalation_message(
        self,
        conversation,
        reason: str,
        urgency_score: int
    ) -> str:
        """Build a detailed escalation notification message"""
        from models.conversation import Message, MessageRole
        
        # Get last few messages for context
        recent_messages = conversation.messages.order_by(Message.created_at.desc()).limit(5).all()
        recent_messages.reverse()  # Oldest first
        
        message_history = ""
        for msg in recent_messages:
            role = "🧑 Usuario" if msg.role == MessageRole.USER else "🤖 Agente"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            message_history += f"\n{role}: {content}"
        
        contact_info = ""
        if conversation.contact_name:
            contact_info += f"Nombre: {conversation.contact_name}\n"
        if conversation.contact_email:
            contact_info += f"Email: {conversation.contact_email}\n"
        if conversation.contact_phone:
            contact_info += f"Teléfono: {conversation.contact_phone}\n"
        
        return f"""
🚨 ESCALACIÓN DE CONVERSACIÓN

📊 Urgencia: {urgency_score}%
📝 Razón: {reason}
🕐 Hora: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
📱 Canal: {conversation.channel.value if conversation.channel else 'N/A'}

👤 INFORMACIÓN DEL CONTACTO:
{contact_info if contact_info else 'No disponible'}

💬 ÚLTIMOS MENSAJES:
{message_history if message_history else 'Sin mensajes disponibles'}

🔗 Responda directamente a este contacto o acceda al dashboard para más detalles.
---
Enviado automáticamente por Aikrofy AI
"""
