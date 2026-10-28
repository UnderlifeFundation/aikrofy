"""
Guided Response Model - Literal overrides for RAG hallucination prevention
"""
from datetime import datetime
from enum import Enum
from extensions import db

class GuidedResponseAction(str, Enum):
    NONE = 'none'
    PAYMENT_LINK = 'payment_link'
    HUMAN_ESCALATION = 'human_escalation'
    SEND_AUDIO = 'send_audio'

class GuidedResponse(db.Model):
    """Literal overrides to prevent LLM hallucinations on specific topics"""
    __tablename__ = 'guided_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Configuration
    trigger_phrases = db.Column(db.JSON, nullable=False, default=list) # List of strings
    literal_response = db.Column(db.Text, nullable=False)
    action_to_trigger = db.Column(db.Enum(GuidedResponseAction), default=GuidedResponseAction.NONE)
    media_url = db.Column(db.String(512), nullable=True) # E.g., for SEND_AUDIO
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    company = db.relationship('Company', back_populates='guided_responses')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'trigger_phrases': self.trigger_phrases,
            'literal_response': self.literal_response,
            'action_to_trigger': self.action_to_trigger.value if self.action_to_trigger else None,
            'media_url': self.media_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<GuidedResponse {self.id} for Company {self.company_id}>'
