from extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship

class EmailLog(db.Model):
    __tablename__ = 'email_logs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    to_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), nullable=True)
    body_summary = db.Column(db.Text, nullable=True) # First 500 chars or summary
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship('Company', backref='email_logs')
    conversation = relationship('Conversation', backref='email_logs')
    customer = relationship('Customer', backref='email_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'conversation_id': self.conversation_id,
            'customer_id': self.customer_id,
            'to_email': self.to_email,
            'subject': self.subject,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }
