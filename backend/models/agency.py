"""
Agency Model - Multi-Company Management for Agencies / Enterprise Partners
Allows an agency account to administer, monitor, and switch between multiple tenant companies securely.

Copyright © 2026 WEBLIFETECH. All Rights Reserved.
"""
from datetime import datetime
from extensions import db


class AgencyCompanyAccess(db.Model):
    """
    Pivot model linking an Agency User to client companies.
    Maintains strict row-level isolation while granting delegated management access.
    """
    __tablename__ = 'agency_company_access'

    id = db.Column(db.Integer, primary_key=True)
    agency_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Permissions within client company: 'admin', 'manager', 'viewer'
    role_in_client = db.Column(db.String(50), default='admin', nullable=False)
    
    # Billing / quota tier for this client under the agency's license
    monthly_fee = db.Column(db.Float, default=99.0, nullable=False) # e.g. $99/mo per company
    monthly_credits = db.Column(db.Integer, default=5000, nullable=False) # Monthly fuel pool included
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(50), default='active', nullable=True) # 'active', 'pending_approval', 'rejected'
    invite_token = db.Column(db.String(255), nullable=True)
    
    # Audit timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agency_user = db.relationship('User', foreign_keys=[agency_user_id], backref=db.backref('client_accesses', lazy='dynamic', cascade='all, delete-orphan'))
    company = db.relationship('Company', foreign_keys=[company_id], backref=db.backref('agency_delegations', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        comp = self.company
        return {
            'id': self.id,
            'agency_user_id': self.agency_user_id,
            'company_id': self.company_id,
            'company_name': comp.name if comp else 'Desconocida',
            'company_email': comp.email if comp else '',
            'company_logo': getattr(comp, 'logo_url', None) or '',
            'credit_balance': getattr(comp, 'credit_balance', 0) if comp else 0,
            'role_in_client': self.role_in_client,
            'monthly_fee': self.monthly_fee,
            'monthly_credits': self.monthly_credits,
            'is_active': self.is_active,
            'status': self.status or ('active' if self.is_active else 'inactive'),
            'invite_token': self.invite_token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
