"""
Conversation Model - Chat history and messages
"""
from datetime import datetime
from enum import Enum
from extensions import db


class ConversationType(str, Enum):
    CUSTOMER = 'customer'
    ADMIN = 'admin'
    EMPLOYEE = 'employee'
    INTERNAL = 'internal'


class HandoverStatus(str, Enum):
    BOT_ACTIVE = 'bot_active'
    HUMAN_TAKEN = 'human_taken'
    HUMAN_LISTENING = 'human_listening'
    RESOLVED = 'resolved'


class MessageRole(str, Enum):
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


class MessageChannel(str, Enum):
    WHATSAPP = 'whatsapp'
    VOICE = 'voice'
    SMS = 'sms'
    EMAIL = 'email'
    WEBCHAT = 'webchat'
    ADMIN_CHAT = 'admin_chat'
    TELEGRAM = 'telegram'
    PLAYGROUND = 'playground'


class Conversation(db.Model):
    """Conversation thread"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, index=True)
    
    # Conversation Type
    type = db.Column(db.Enum(ConversationType), default=ConversationType.CUSTOMER)
    
    # Contact Info
    contact_name = db.Column(db.String(255), nullable=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    contact_email = db.Column(db.String(255), nullable=True)
    
    # Channel (Stored as String to avoid SQLAlchemy Enum strict validation issues with MySQL)
    channel = db.Column(db.String(50), nullable=False)
    
    # Metadata
    conv_metadata = db.Column(db.JSON, default=dict)
    tags = db.Column(db.JSON, default=list)
    
    # Status & Handover (Enterprise 10X Protocol)
    is_active = db.Column(db.Boolean, default=True)
    is_resolved = db.Column(db.Boolean, default=False)
    handover_status = db.Column(db.String(50), default='bot_active', nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Human operator
    handover_summary = db.Column(db.Text, nullable=True)  # AI-generated 3-line case snapshot
    
    # Analytics
    sentiment_score = db.Column(db.Float, nullable=True)  # -1 to 1
    lead_score = db.Column(db.Integer, nullable=True)  # 0 to 100
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    company = db.relationship('Company', back_populates='conversations')
    customer = db.relationship('Customer', backref=db.backref('conversations', lazy='dynamic'))
    messages = db.relationship('Message', back_populates='conversation', lazy='dynamic', cascade='all, delete-orphan', order_by='Message.created_at')
    
    def to_dict(self, include_messages=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'customer_id': self.customer_id,
            'type': self.type.value,
            'contact_name': self.contact_name,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'channel': self.channel.value if hasattr(self.channel, 'value') else self.channel,
            'conv_metadata': self.conv_metadata,
            'tags': self.tags,
            'is_active': self.is_active,
            'is_resolved': self.is_resolved,
            'handover_status': self.handover_status or 'bot_active',
            'assigned_user_id': self.assigned_user_id,
            'handover_summary': self.handover_summary,
            'sentiment_score': self.sentiment_score,
            'lead_score': self.lead_score,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'message_count': self.messages.count()
        }
        
        if include_messages:
            data['messages'] = [m.to_dict() for m in self.messages.limit(100)]
        
        return data
    
    def __repr__(self):
        return f'<Conversation {self.id}>'


class Message(db.Model):
    """Individual message in a conversation"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    
    # Message Content
    role = db.Column(db.Enum(MessageRole), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Channel Info (Stored as String to avoid SQLAlchemy Enum strict validation issues with MySQL)
    channel = db.Column(db.String(50), nullable=True)
    
    # Media (for voice messages, images, etc.)
    media_url = db.Column(db.String(512), nullable=True)
    media_type = db.Column(db.String(50), nullable=True)
    
    # Tool/Action tracking
    tool_calls = db.Column(db.JSON, default=list)  # [{name, args, result}, ...]
    
    # Analytics
    tokens_used = db.Column(db.Integer, nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)

    # Observability: measured per-turn telemetry (LEM energy/verdict, usage, model,
    # credits, spans). Populated by services.turn_telemetry; never simulated.
    trace_meta = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = db.relationship('Conversation', back_populates='messages')
    audit = db.relationship('MessageAudit', back_populates='message', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        channel_val = self.channel
        if hasattr(self.channel, 'value'):
            channel_val = self.channel.value
            
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role.value,
            'content': self.content,
            'channel': channel_val,
            'media_url': self.media_url,
            'media_type': self.media_type,
            'tool_calls': self.tool_calls,
            'tokens_used': self.tokens_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Message {self.id}>'
