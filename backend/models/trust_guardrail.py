"""
Trust Guardrail Model - Enterprise Security, PII Masking & Risk Governance
Defines boundaries, forbidden words, financial execution limits,
and supervisory two-step approvals.
"""
from datetime import datetime
from enum import Enum
from extensions import db

class GuardrailType(str, Enum):
    PII_MASKING = 'pii_masking'
    PROMPT_INJECTION_DEFENSE = 'prompt_injection_defense'
    PRICE_DISCOUNT_LIMIT = 'price_discount_limit'
    TWO_STEP_APPROVAL = 'two_step_approval'
    CONTENT_POLICY = 'content_policy'

class GuardrailAction(str, Enum):
    BLOCK = 'block'
    MASK = 'mask'
    ESCALATE = 'escalate'
    LOG_AUDIT = 'log_audit'

class TrustGuardrail(db.Model):
    """Company-level security and governance guardrails"""
    __tablename__ = 'trust_guardrails'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    name = db.Column(db.String(255), nullable=False)
    guardrail_type = db.Column(db.Enum(GuardrailType), nullable=False)
    action = db.Column(db.Enum(GuardrailAction), default=GuardrailAction.MASK, nullable=False)

    # Configuration rules in JSON:
    # e.g. { "max_discount_pct": 15, "high_risk_threshold_usd": 500, "forbidden_terms": [...] }
    rules = db.Column(db.JSON, default=dict)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('trust_guardrails', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'guardrail_type': self.guardrail_type.value if hasattr(self.guardrail_type, 'value') else self.guardrail_type,
            'action': self.action.value if hasattr(self.action, 'value') else self.action,
            'rules': self.rules,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<TrustGuardrail {self.id}: {self.name} ({self.guardrail_type})>'
