"""
PaymentGateway Models - Multi-gateway payment integration per company.
Stores gateway configuration and an immutable transaction ledger.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from extensions import db


class GatewayProvider(str, Enum):
    STRIPE = 'stripe'
    PAYPAL = 'paypal'
    MERCADOPAGO = 'mercadopago'
    KUSHKI = 'kushki'
    NUVEI = 'nuvei'
    DLOCAL_GO = 'dlocal_go'
    AUTHORIZE_NET = 'authorize_net'
    CUSTOM = 'custom'


class TransactionStatus(str, Enum):
    PENDING = 'pending'
    AUTHORIZED = 'authorized'
    CAPTURED = 'captured'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    VOIDED = 'voided'


class TransactionChannel(str, Enum):
    WHATSAPP = 'whatsapp'
    TELEGRAM = 'telegram'
    WEBCHAT = 'webchat'
    VOICE = 'voice'
    DASHBOARD = 'dashboard'


class PaymentGatewayConfig(db.Model):
    """Payment gateway configuration (One-to-One with Company)."""
    __tablename__ = 'payment_gateway_configs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey('companies.id'),
        nullable=False, unique=True
    )

    # Provider Selection
    gateway_provider = db.Column(db.Enum(GatewayProvider), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)

    # Custom gateway endpoint (only used for GatewayProvider.CUSTOM)
    api_endpoint = db.Column(db.String(512), nullable=True)

    # Credentials stored as JSON — flexible per provider
    # Stripe:        { "secret_key": "sk_..." }
    # PayPal:        { "client_id": "...", "client_secret": "...", "mode": "sandbox|live" }
    # MercadoPago:   { "access_token": "..." }
    # Kushki:        { "private_merchant_id": "..." }
    # Nuvei:         { "merchant_id": "...", "merchant_site_id": "...", "secret_key": "..." }
    # dLocal Go:     { "api_key": "...", "secret_key": "..." }
    # Authorize.Net: { "api_login_id": "...", "transaction_key": "..." }
    # Custom:        { "api_key": "...", "api_secret": "..." }
    credentials = db.Column(db.JSON, default=dict)

    # Extra configuration (webhook secrets, custom mapping rules, etc.)
    config_payload = db.Column(db.JSON, default=dict)

    # Environment
    sandbox_mode = db.Column(db.Boolean, default=True)

    # Connection Status
    is_connected = db.Column(db.Boolean, default=False)
    last_tested_at = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationship
    company = db.relationship(
        'Company',
        backref=db.backref('payment_gateway_config', uselist=False)
    )

    def to_dict(self, include_credentials=False):
        """Convert to dictionary (credentials masked by default)."""
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'gateway_provider': (
                self.gateway_provider.value if self.gateway_provider else None
            ),
            'display_name': self.display_name,
            'api_endpoint': self.api_endpoint,
            'sandbox_mode': self.sandbox_mode,
            'is_connected': self.is_connected,
            'last_tested_at': (
                self.last_tested_at.isoformat()
                if self.last_tested_at else None
            ),
            'last_error': self.last_error,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            'updated_at': (
                self.updated_at.isoformat()
                if self.updated_at else None
            ),
        }
        if include_credentials:
            data['credentials'] = self.credentials
            data['config_payload'] = self.config_payload
        else:
            # Return which keys exist (for UI state) without actual secrets
            data['credentials_configured'] = list(
                (self.credentials or {}).keys()
            )
        return data

    def __repr__(self):
        provider = (
            self.gateway_provider.value
            if self.gateway_provider else 'none'
        )
        return (
            f'<PaymentGatewayConfig {provider} '
            f'for company={self.company_id}>'
        )


class PaymentTransaction(db.Model):
    """Immutable ledger of all payment transactions processed via agents."""
    __tablename__ = 'payment_transactions'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey('companies.id'), nullable=False
    )
    gateway_config_id = db.Column(
        db.Integer,
        db.ForeignKey('payment_gateway_configs.id'),
        nullable=True
    )

    # Customer Info
    customer_email = db.Column(db.String(255), nullable=True)
    customer_phone = db.Column(db.String(50), nullable=True)
    customer_name = db.Column(db.String(255), nullable=True)

    # Transaction Details
    amount = db.Column(db.Numeric(18, 4), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False
    )

    # External Reference
    external_transaction_id = db.Column(db.String(255), nullable=True)
    idempotency_key = db.Column(
        db.String(255), unique=True, nullable=False
    )

    # Payment URL (for redirect-based gateways like PayPal, dLocal Go)
    payment_url = db.Column(db.Text, nullable=True)

    # Channel & Agent context
    channel = db.Column(db.Enum(TransactionChannel), nullable=True)
    agent_id = db.Column(
        db.Integer, db.ForeignKey('agents.id'), nullable=True
    )
    conversation_id = db.Column(
        db.Integer, db.ForeignKey('conversations.id'), nullable=True
    )

    # Error tracking
    error_code = db.Column(db.String(100), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    # Raw gateway response metadata
    gateway_metadata = db.Column(db.JSON, default=dict)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    company = db.relationship('Company', backref='payment_transactions')
    gateway_config = db.relationship(
        'PaymentGatewayConfig',
        backref='transactions'
    )

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'customer_name': self.customer_name,
            'amount': str(self.amount) if self.amount else None,
            'currency': self.currency,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'external_transaction_id': self.external_transaction_id,
            'idempotency_key': self.idempotency_key,
            'payment_url': self.payment_url,
            'channel': self.channel.value if self.channel else None,
            'agent_id': self.agent_id,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'created_at': (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            'updated_at': (
                self.updated_at.isoformat()
                if self.updated_at else None
            ),
        }

    def __repr__(self):
        return (
            f'<PaymentTransaction {self.id} '
            f'amount={self.amount} {self.currency} '
            f'status={self.status.value if self.status else "?"}'
            f'>'
        )
