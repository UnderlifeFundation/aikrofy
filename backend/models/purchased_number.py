from extensions import db
from datetime import datetime

class PurchasedNumber(db.Model):
    """
    Model representing virtual phone numbers purchased through Twilio API in pymai.
    Stores metadata like SID, phone number, and association with the company.
    """
    __tablename__ = 'purchased_numbers'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    sid = db.Column(db.String(100), nullable=False)
    friendly_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Company
    company = db.relationship('Company', backref=db.backref('purchased_numbers', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'phone_number': self.phone_number,
            'sid': self.sid,
            'friendly_name': self.friendly_name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
