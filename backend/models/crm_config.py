"""
CRMConfig Model - CRM platform integration configuration per company.
Stores credentials and connection state for HubSpot, Salesforce, Pipedrive,
Zoho CRM, Microsoft Dynamics 365, and custom CRMs.
"""
from datetime import datetime
from enum import Enum
from extensions import db


class CRMPlatform(str, Enum):
    HUBSPOT = 'hubspot'
    SALESFORCE = 'salesforce'
    PIPEDRIVE = 'pipedrive'
    ZOHO = 'zoho'
    DYNAMICS_365 = 'dynamics_365'
    CUSTOM = 'custom'


class CRMConfig(db.Model):
    """CRM platform connection configuration (One-to-One with Company)."""
    __tablename__ = 'crm_configs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, unique=True)

    # Platform Selection
    platform = db.Column(db.Enum(CRMPlatform), nullable=False)

    # Connection Details (universal)
    crm_url = db.Column(db.String(512), nullable=True)

    # Credentials stored as JSON for flexibility across platforms
    # HubSpot:       { "access_token": "..." } or { "client_id": "...", "client_secret": "...", "refresh_token": "..." }
    # Salesforce:    { "client_id": "...", "client_secret": "...", "refresh_token": "...", "instance_url": "..." }
    # Pipedrive:     { "api_token": "..." } or { "client_id": "...", "client_secret": "...", "refresh_token": "..." }
    # Zoho:          { "client_id": "...", "client_secret": "...", "refresh_token": "...", "region": ".com" }
    # Dynamics 365:  { "tenant_id": "...", "client_id": "...", "client_secret": "...", "environment_url": "..." }
    # Custom:        { "db_uri": "...", ... } (user-defined)
    credentials = db.Column(db.JSON, default=dict)

    # Custom CRM schema (JSON Schema for the dynamic mapping engine)
    # Only used when platform == 'custom'
    custom_schema = db.Column(db.JSON, nullable=True)

    # Connection Status
    is_connected = db.Column(db.Boolean, default=False)
    last_tested_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    company = db.relationship('Company', backref=db.backref('crm_config', uselist=False))

    def to_dict(self, include_credentials=False):
        """Convert to dictionary (credentials masked by default)."""
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'platform': self.platform.value if self.platform else None,
            'crm_url': self.crm_url,
            'is_connected': self.is_connected,
            'last_tested_at': self.last_tested_at.isoformat() if self.last_tested_at else None,
            'last_error': self.last_error,
            'custom_schema': self.custom_schema,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_credentials:
            data['credentials'] = self.credentials
        else:
            # Return which keys exist (for UI state) without actual secrets
            data['credentials_configured'] = list((self.credentials or {}).keys())
        return data

    def __repr__(self):
        return f'<CRMConfig {self.platform.value if self.platform else "none"} for company={self.company_id}>'
