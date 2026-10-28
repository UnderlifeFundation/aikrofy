"""
Appointment Model - Calendar/Scheduling Audit Trail
Copyright © 2025 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from datetime import datetime
from enum import Enum
from extensions import db


class AppointmentStatus(str, Enum):
    SCHEDULED = 'scheduled'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    RESCHEDULED = 'rescheduled'


class Appointment(db.Model):
    """
    Appointment record linked to a Customer, Company and optionally a Channel.
    Tracks all scheduled meetings/events.
    """
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    
    # Context
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)

    
    # Appointment Details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)  # Meeting reason/subject
    
    # Timing
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, default=30)
    
    # Client Timezone Info  
    client_timezone = db.Column(db.String(100), nullable=True)  # e.g. "America/Buenos_Aires"
    client_city = db.Column(db.String(100), nullable=True)
    client_country = db.Column(db.String(100), nullable=True)
    
    # Google Calendar Integration
    google_event_id = db.Column(db.String(255), nullable=True, index=True)
    google_meet_link = db.Column(db.String(500), nullable=True)
    
    # Status
    status = db.Column(db.String(50), default=AppointmentStatus.SCHEDULED.value)
    
    # Booking Source
    channel_type = db.Column(db.String(50), nullable=True)  # webchat, whatsapp, telegram, etc
    
    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('appointments', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('appointments', lazy=True))
    conversation = db.relationship('Conversation', backref=db.backref('appointments', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'client_city': self.client_city,
            'client_country': self.client_country,
            'client_timezone': self.client_timezone,
            'google_meet_link': self.google_meet_link,
            'status': self.status,
            'channel_type': self.channel_type,
            'customer_name': self.customer.full_name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
