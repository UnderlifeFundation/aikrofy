"""
EcommerceConfig Model - E-commerce platform integration configuration per company.
Stores credentials and connection state for Shopify, WooCommerce, VTEX, Magento,
PrestaShop, and BigCommerce.
"""
from datetime import datetime
from enum import Enum
from extensions import db


class EcommercePlatform(str, Enum):
    SHOPIFY = 'shopify'
    WOOCOMMERCE = 'woocommerce'
    VTEX = 'vtex'
    MAGENTO = 'magento'
    PRESTASHOP = 'prestashop'
    BIGCOMMERCE = 'bigcommerce'


class EcommerceConfig(db.Model):
    """E-commerce platform connection configuration (One-to-One with Company)."""
    __tablename__ = 'ecommerce_configs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, unique=True)

    # Platform Selection
    platform = db.Column(db.Enum(EcommercePlatform), nullable=False)

    # Connection Details (universal)
    store_url = db.Column(db.String(512), nullable=False)

    # Credentials stored as JSON for flexibility across platforms
    # Shopify:      { "access_token": "..." }
    # WooCommerce:  { "consumer_key": "...", "consumer_secret": "..." }
    # VTEX:         { "app_key": "...", "app_token": "..." }
    # Magento:      { "access_token": "..." } (Bearer token)
    # PrestaShop:   { "api_key": "..." }
    # BigCommerce:  { "store_hash": "...", "access_token": "..." }
    credentials = db.Column(db.JSON, default=dict)

    # Connection Status
    is_connected = db.Column(db.Boolean, default=False)
    last_tested_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    company = db.relationship('Company', backref=db.backref('ecommerce_config', uselist=False))

    def to_dict(self, include_credentials=False):
        """Convert to dictionary (credentials masked by default)."""
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'platform': self.platform.value if self.platform else None,
            'store_url': self.store_url,
            'is_connected': self.is_connected,
            'last_tested_at': self.last_tested_at.isoformat() if self.last_tested_at else None,
            'last_error': self.last_error,
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
        return f'<EcommerceConfig {self.platform.value if self.platform else "none"} for company={self.company_id}>'
