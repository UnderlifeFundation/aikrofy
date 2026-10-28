"""
Company Campaign Model - Dynamic Ephemeral Context Injection
"""
from datetime import datetime
from extensions import db

class CompanyCampaign(db.Model):
    """Dynamic campaigns to inject priority context temporarily (e.g. Black Friday)"""
    __tablename__ = 'company_campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Configuration
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False) # The context to inject
    
    # Status and Time gating
    is_active = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    company = db.relationship('Company', back_populates='campaigns')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_currently_valid(self):
        """Check if campaign is active and within date bounds"""
        if not self.is_active:
            return False
        
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
            
        return True

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_currently_valid': self.is_currently_valid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<CompanyCampaign {self.name} for Company {self.company_id}>'
