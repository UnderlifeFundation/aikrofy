"""
Transaction Model - Financial Audit Trail
"""
from datetime import datetime
from enum import Enum
from extensions import db

class TransactionStatus(str, Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    CANCELLED = 'cancelled'

class TransactionProvider(str, Enum):
    PAYPAL = 'paypal'
    STRIPE = 'stripe'
    DLOCAL = 'dlocal'
    PADDLE = 'paddle'
    MANUAL = 'manual'

class TransactionType(str, Enum):
    PAYMENT = 'payment'             # Customer payment (PayPal order etc.)
    SUBSCRIPTION = 'subscription'   # Recurring subscription payment
    CREDIT_TOP_UP = 'credit_top_up' # One-off credit purchase

class Transaction(db.Model):
    """
    Transaction record linked to a Customer and a Conversation.
    """
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    
    # Context
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True, index=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=True)
    
    # Financial Details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    description = db.Column(db.Text, nullable=True)
    service_type = db.Column(db.String(100), nullable=True) # e.g. "Web Development", "Consulting"
    
    # Provider Details
    provider = db.Column(db.String(50), default=TransactionProvider.PAYPAL.value)
    provider_order_id = db.Column(db.String(100), nullable=True, index=True) # e.g. PayPal Order ID
    status = db.Column(db.String(50), default=TransactionStatus.PENDING.value)
    
    # Transaction Type (payment, subscription, credit_top_up)
    transaction_type = db.Column(db.String(50), default=TransactionType.PAYMENT.value)
    
    # Credits granted by this transaction (for CREDIT_TOP_UP type)
    credits_granted = db.Column(db.Integer, default=0)
    
    # Meta
    channel = db.Column(db.String(50), nullable=True) # telegram, webchat, etc
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('transactions', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('transactions', lazy=True))
    conversation = db.relationship('Conversation', backref=db.backref('transactions', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'description': self.description,
            'service_type': self.service_type,
            'transaction_type': self.transaction_type,
            'credits_granted': self.credits_granted,
            'provider_order_id': self.provider_order_id,
            'customer_name': self.customer.full_name if self.customer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
