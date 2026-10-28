"""
Channel Model - Communication channel configurations
"""
from datetime import datetime
from enum import Enum
from extensions import db


class ChannelType(str, Enum):
    WHATSAPP = 'whatsapp'
    VOICE = 'voice'
    SMS = 'sms'
    EMAIL = 'email'
    WEBCHAT = 'webchat'
    TELEGRAM = 'telegram'


class ChannelStatus(str, Enum):
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    ERROR = 'error'


class Channel(db.Model):
    """Communication channel configuration"""
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Channel Info
    type = db.Column(db.Enum(ChannelType), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # Credentials (encrypted in production)
    credentials = db.Column(db.JSON, default=dict)
    
    # Connection Info
    phone_number = db.Column(db.String(50), nullable=True)
    email_address = db.Column(db.String(255), nullable=True)
    
    # Status
    status = db.Column(db.Enum(ChannelStatus), default=ChannelStatus.DISCONNECTED)
    status_message = db.Column(db.String(255), nullable=True)
    
    # QR Code (for WhatsApp Web-style connections)
    qr_code = db.Column(db.Text, nullable=True)
    qr_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    connected_at = db.Column(db.DateTime, nullable=True)
    last_activity = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', back_populates='channels')
    
    # Unique constraint per company and type
    __table_args__ = (
        db.UniqueConstraint('company_id', 'type', 'phone_number', name='unique_company_channel'),
    )
    
    def update_status(self, status, message=None):
        """Update channel status"""
        self.status = status
        self.status_message = message
        if status == ChannelStatus.CONNECTED:
            self.connected_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Invalidate analytics dashboard cache so changes reflect immediately
        try:
            from services.cache_service import CacheService
            cache_key = f"analytics:dashboard:company_{self.company_id}"
            CacheService.delete(cache_key)
        except Exception:
            pass
    
    def to_dict(self, include_credentials=False):
        """Convert to dictionary"""
        type_val = self.type.value if hasattr(self.type, 'value') else self.type
        status_val = self.status.value if hasattr(self.status, 'value') else self.status
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'type': type_val,
            'channel_type': type_val,  # Alias for frontend compatibility
            'name': self.name,
            'phone_number': self.phone_number,
            'email_address': self.email_address,
            'status': status_val,
            'status_message': self.status_message,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_credentials:
            data['credentials'] = self.credentials
        
        # Include QR if pending
        if self.status == ChannelStatus.CONNECTING and self.qr_code:
            data['qr_code'] = self.qr_code
            data['qr_expires_at'] = self.qr_expires_at.isoformat() if self.qr_expires_at else None
        
        return data
    
    def __repr__(self):
        type_val = self.type.value if hasattr(self.type, 'value') else self.type
        return f'<Channel {type_val}:{self.name}>'
