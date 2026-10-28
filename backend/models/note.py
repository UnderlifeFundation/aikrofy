"""
Note Model - CRM internal notes for contacts
"""
from datetime import datetime
from extensions import db

class Note(db.Model):
    """
    Note model represents an internal comment or record about a Customer.
    Used for CRM tracking and team communication.
    """
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Author (Admin/Manager)
    
    content = db.Column(db.Text, nullable=False)
    
    # Metadata
    author_name = db.Column(db.String(100), nullable=True) # Cache author name for quick display
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('notes', lazy=True))
    customer = db.relationship('Customer', backref=db.backref('notes', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('authored_notes', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'customer_id': self.customer_id,
            'user_id': self.user_id,
            'content': self.content,
            'author_name': self.author_name or (self.user.full_name if self.user else "System"),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
