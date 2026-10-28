"""
WhatsApp LID Mapping Model - persistent LID JID -> real phone number resolution per company.

WhatsApp now addresses many senders by LID (e.g. 123456789@lid) instead of the
phone JID. The webhook layer resolves the real phone via `remoteJidAlt` /
`participantAlt` and persists the mapping here (plus Redis) through
`CustomerService.save_lid_mapping()` so future messages from the same LID
resolve without a fresh alt payload.
"""
from datetime import datetime
from extensions import db


class WhatsAppLidMapping(db.Model):
    """LID -> phone mapping scoped per company (tenant)."""
    __tablename__ = 'whatsapp_lid_mapping'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    lid_jid = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('company_id', 'lid_jid', name='uq_lid_mapping_company_lid'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'lid_jid': self.lid_jid,
            'phone_number': self.phone_number,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<WhatsAppLidMapping {self.lid_jid} -> {self.phone_number} (company {self.company_id})>'
