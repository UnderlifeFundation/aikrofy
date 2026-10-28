"""
FunnelStage Model - Pipeline stages for CRM/Kanban board per company.
"""
from datetime import datetime
from extensions import db


class FunnelStage(db.Model):
    """Funnel Stage / Kanban Column for a Company."""
    __tablename__ = 'funnel_stages'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('funnel_stages', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<FunnelStage {self.name} for company={self.company_id}>'
