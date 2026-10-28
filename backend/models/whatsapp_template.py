"""
WhatsApp Message Template Model (HSM - Meta Cloud API)
Stores templates, components, status, and conversion analytics.
"""
from datetime import datetime
import enum
from extensions import db


class TemplateCategory(str, enum.Enum):
    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


class TemplateStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    DRAFT = "DRAFT"


class WhatsAppTemplate(db.Model):
    __tablename__ = 'whatsapp_templates'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    meta_template_id = db.Column(db.String(255), nullable=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False, default=TemplateCategory.MARKETING.value)
    language = db.Column(db.String(10), nullable=False, default='es')
    status = db.Column(db.String(50), nullable=False, default=TemplateStatus.DRAFT.value)
    components = db.Column(db.JSON, nullable=False, default=list)
    rejected_reason = db.Column(db.Text, nullable=True)

    # Conversion Analytics & AI Performance Metrics
    total_sent = db.Column(db.Integer, default=0)
    total_delivered = db.Column(db.Integer, default=0)
    total_read = db.Column(db.Integer, default=0)
    total_replied = db.Column(db.Integer, default=0)
    conversion_rate = db.Column(db.Float, default=0.0)
    ai_performance_score = db.Column(db.Float, default=0.0)
    ai_suggestions = db.Column(db.JSON, nullable=True, default=dict)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'meta_template_id': self.meta_template_id,
            'name': self.name,
            'category': self.category,
            'language': self.language,
            'status': self.status,
            'components': self.components or [],
            'rejected_reason': self.rejected_reason,
            'total_sent': self.total_sent or 0,
            'total_delivered': self.total_delivered or 0,
            'total_read': self.total_read or 0,
            'total_replied': self.total_replied or 0,
            'conversion_rate': round(self.conversion_rate or 0.0, 2),
            'ai_performance_score': round(self.ai_performance_score or 0.0, 1),
            'ai_suggestions': self.ai_suggestions or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
