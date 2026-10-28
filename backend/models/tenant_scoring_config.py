"""
TenantScoringConfig Model - Configures parameters and manual rules for lead scoring.
"""
from datetime import datetime
from extensions import db


class TenantScoringConfig(db.Model):
    """Scoring weights and rules for a Company/Tenant."""
    __tablename__ = 'tenant_scoring_configs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, unique=True)

    # Weights: w_ML + w_Manual = 1.0
    weight_ml = db.Column(db.Float, default=0.50, nullable=False)
    weight_manual = db.Column(db.Float, default=0.50, nullable=False)

    # Rules structure (JSON format)
    # {
    #   "email_domains": { "gmail.com": -10, "outlook.com": -10 },
    #   "industries": { "Technology": 15, "Healthcare": 10 },
    #   "countries": { "US": 5, "MX": 10 },
    #   "buying_roles": { "CEO": 25, "Director": 20, "End User": 0 }
    # }
    scoring_rules = db.Column(db.JSON, default=dict, nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    company = db.relationship('Company', backref=db.backref('scoring_config', uselist=False, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'weight_ml': self.weight_ml,
            'weight_manual': self.weight_manual,
            'scoring_rules': self.scoring_rules,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<TenantScoringConfig company={self.company_id}>'
