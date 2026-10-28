"""
Customer Model - Multi-tenant customer management
"""
from datetime import datetime
from extensions import db
from sqlalchemy.dialects.mysql import JSON

class Customer(db.Model):
    """
    Customer model represents an end-user/client associated with a Company.
    Multi-tenant: email/phone unicity is ideally per-company, though here we enforce
    soft constraints via application logic or compound indexes if needed.
    """
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    
    # Contact info - Indexed for quick lookups
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True, index=True)
    
    # Location
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    
    # Official Identification (DNI, Passport, etc)
    ident_number = db.Column(db.String(50), nullable=True)

    # Employment (B2B)
    work_company = db.Column(db.String(255), nullable=True)
    buying_role = db.Column(db.String(50), default='End User', nullable=True) # B2B/B2C Role
    
    # CRM & Pipeline fields
    funnel_stage_id = db.Column(db.Integer, db.ForeignKey('funnel_stages.id'), nullable=True, index=True)
    lead_score = db.Column(db.Integer, default=0, nullable=False)
    
    # Flexible metadata for CRM details (address, preferences, extra fields)
    customer_metadata = db.Column(JSON, nullable=True)
    
    # AI Control
    is_ai_active = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('customers', lazy=True, cascade='all, delete-orphan'))
    funnel_stage = db.relationship('FunnelStage', backref=db.backref('customers', lazy='dynamic'))
    
    @property
    def full_name(self):
        """Returns full name as first_name + last_name"""
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or "Cliente"

    @property
    def name(self):
        """Alias for full_name"""
        return self.full_name
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f"{self.first_name or ''} {self.last_name or ''}".strip(),
            'email': self.email,
            'phone': self.phone,
            'country': self.country,
            'city': self.city,
            'ident_number': self.ident_number,
            'work_company': self.work_company,
            'buying_role': self.buying_role,
            'funnel_stage_id': self.funnel_stage_id,
            'lead_score': self.lead_score,
            'metadata': self.customer_metadata,
            'is_ai_active': self.is_ai_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
