"""
Payment Gateway Configuration and Transaction Routes.
Endpoints for managing multi-gateway integrations and webhooks.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from datetime import datetime
from decimal import Decimal
import logging
from extensions import db
from models.user import User
from models.payment_gateway import PaymentGatewayConfig, PaymentTransaction, GatewayProvider, TransactionStatus
from services.payment_gateways.schemas import NormalizedTransactionRequest

logger = logging.getLogger(__name__)
payment_gateways_bp = APIRouter('payment_gateways', __name__)

def _get_user_company():
    """Helper to get current user's company."""
    user_id = get_jwt_identity()
    try:
        user = User.query.get(int(user_id))
        if not user or not user.company:
            return None, None
        return user, user.company
    except Exception:
        return None, None

# Define fields required for each provider (for UI generation)
PROVIDER_FIELDS = {
    'stripe': {
        'label': 'Stripe',
        'fields': [
            {'key': 'secret_key', 'label': 'Secret Key (sk_...)', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Configure webhook endpoints pointing to: /api/payment-gateways/webhook/stripe'
    },
    'paypal': {
        'label': 'PayPal',
        'fields': [
            {'key': 'client_id', 'label': 'Client ID', 'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True},
            {'key': 'mode', 'label': 'Mode (sandbox or live)', 'type': 'text', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Add webhook endpoints pointing to: /api/payment-gateways/webhook/paypal'
    },
    'mercadopago': {
        'label': 'Mercado Pago',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token (APP_USR-...)', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Add webhook endpoints pointing to: /api/payment-gateways/webhook/mercadopago'
    },
    'kushki': {
        'label': 'Kushki Pagos',
        'fields': [
            {'key': 'private_merchant_id', 'label': 'Private Merchant ID', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Add webhook endpoints pointing to: /api/payment-gateways/webhook/kushki'
    },
    'nuvei': {
        'label': 'Nuvei (SafeCharge)',
        'fields': [
            {'key': 'merchant_id', 'label': 'Merchant ID', 'type': 'text', 'required': True},
            {'key': 'merchant_site_id', 'label': 'Merchant Site ID', 'type': 'text', 'required': True},
            {'key': 'secret_key', 'label': 'Secret Key / SHA256 Shared Secret', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Add webhook endpoints pointing to: /api/payment-gateways/webhook/nuvei'
    },
    'dlocal_go': {
        'label': 'dLocal Go',
        'fields': [
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
            {'key': 'secret_key', 'label': 'Secret Key', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Add webhook endpoints pointing to: /api/payment-gateways/webhook/dlocal_go'
    },
    'authorize_net': {
        'label': 'Authorize.Net',
        'fields': [
            {'key': 'api_login_id', 'label': 'API Login ID', 'type': 'text', 'required': True},
            {'key': 'transaction_key', 'label': 'Transaction Key', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'Not Required',
        'url_help': 'Configure Webhook signature key in Authorize.net portal for webhook verification.'
    },
    'custom': {
        'label': 'Custom Gateway',
        'fields': [
            {'key': 'api_key', 'label': 'API Key / Token', 'type': 'password', 'required': True},
            {'key': 'api_secret', 'label': 'API Secret Key (optional)', 'type': 'password', 'required': False},
        ],
        'url_placeholder': 'https://api.yourgateway.com/v1/payments',
        'url_help': 'Enter the full custom JSON API endpoint URL.'
    }
}


@payment_gateways_bp.route('/providers', methods=['GET'])
@jwt_required()
def get_providers():
    """Return list of supported payment providers and credential layouts."""
    return jsonify({'providers': PROVIDER_FIELDS})


@payment_gateways_bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get active payment gateway config for company."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first()
    if not config:
        return jsonify({'config': None})
        
    return jsonify({'config': config.to_dict()})


@payment_gateways_bp.route('/config', methods=['POST'])
@jwt_required()
def save_config():
    """Create or update payment gateway configuration."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    data = request.get_json()
    provider_str = data.get('gateway_provider', '')
    api_endpoint = data.get('api_endpoint')
    credentials = data.get('credentials', {})
    config_payload = data.get('config_payload', {})
    sandbox_mode = data.get('sandbox_mode', True)
    
    try:
        provider = GatewayProvider(provider_str)
    except ValueError:
        return jsonify({'error': f'Unsupported provider: {provider_str}'}), 400
        
    # Validate required credentials
    provider_def = PROVIDER_FIELDS.get(provider_str, {})
    for field in provider_def.get('fields', []):
        if field.get('required') and not credentials.get(field['key']):
            return jsonify({'error': f"Field '{field['label']}' is required"}), 400
            
    # Upsert
    config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first()
    if config:
        config.gateway_provider = provider
        config.api_endpoint = api_endpoint
        config.credentials = credentials
        config.config_payload = config_payload
        config.sandbox_mode = sandbox_mode
        config.is_connected = False
        config.last_error = None
    else:
        config = PaymentGatewayConfig(
            company_id=company.id,
            gateway_provider=provider,
            api_endpoint=api_endpoint,
            credentials=credentials,
            config_payload=config_payload,
            sandbox_mode=sandbox_mode
        )
        db.session.add(config)
        
    db.session.commit()
    return jsonify({
        'message': 'Payment gateway configuration saved',
        'config': config.to_dict()
    })


@payment_gateways_bp.route('/test', methods=['POST'])
@jwt_required()
def test_connection():
    """Test connection using factory and dynamically selected adapter."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first()
    if not config:
        return jsonify({'error': 'No config found'}), 404
        
    from services.payment_gateways.factory import PaymentAdapterFactory
    try:
        adapter = PaymentAdapterFactory.get_adapter(
            provider=config.gateway_provider.value,
            credentials=config.credentials,
            config_payload=config.config_payload,
            sandbox_mode=config.sandbox_mode
        )
        
        # Test connection by running config setup or a dummy call
        adapter.configure()
        
        # Connection succeeds if configure completes without errors
        config.is_connected = True
        config.last_tested_at = datetime.utcnow()
        config.last_error = None
        db.session.commit()
        
        return jsonify({
            'result': {'success': True},
            'config': config.to_dict()
        })
    except Exception as e:
        config.is_connected = False
        config.last_tested_at = datetime.utcnow()
        config.last_error = str(e)
        db.session.commit()
        return jsonify({
            'result': {'success': False, 'error': str(e)},
            'config': config.to_dict()
        })


@payment_gateways_bp.route('/disconnect', methods=['POST'])
@jwt_required()
def disconnect():
    """Remove payment gateway configuration."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first()
    if config:
        db.session.delete(config)
        db.session.commit()
        
    return jsonify({'message': 'Payment gateway disconnected'})


@payment_gateways_bp.route('/transactions', methods=['GET'])
@jwt_required()
def list_transactions():
    """List ledger of processed conversational payments."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    txs = PaymentTransaction.query.filter_by(company_id=company.id).order_by(PaymentTransaction.created_at.desc()).all()
    return jsonify({'transactions': [tx.to_dict() for tx in txs]})


# ------------------------------------------------------------------
# Webhook Route Handlers (Public Endpoints)
# ------------------------------------------------------------------
@payment_gateways_bp.route('/webhook/<provider>', methods=['POST'])
def handle_webhook(provider: str):
    """
    Public webhook receiver for async payment events from providers.
    Does not require JWT authentication.
    """
    raw_body = request.get_data()
    headers = dict(request.headers)
    
    # Locate configuration matching webhook provider based on query or payload metadata
    # (Since webhook payloads generally contain external IDs or idempotency keys,
    # we first attempt signature check against the matching company's settings)
    data = request.get_json(silent=True) or {}
    
    # 1. Resolve transaction ref
    external_ref = None
    if provider == 'stripe':
        external_ref = data.get('id')  # Event ID or PaymentIntent ID inside object
        obj = data.get('data', {}).get('object', {})
        external_ref = obj.get('id') or external_ref
    elif provider == 'paypal':
        resource = data.get('resource', {})
        external_ref = resource.get('id') or data.get('id')
    elif provider == 'mercadopago':
        # Mercado Pago payload: resource is URL pointing to payment details
        # Let's extract resource ID
        external_ref = data.get('data', {}).get('id') or data.get('id')
    elif provider == 'kushki':
        external_ref = data.get('ticketNumber')
    elif provider == 'nuvei':
        external_ref = data.get('orderId') or data.get('transactionId')
    elif provider == 'dlocal_go':
        external_ref = data.get('id')
        
    # Search transaction by external ID or idempotency key
    tx = None
    if external_ref:
        tx = PaymentTransaction.query.filter(
            (PaymentTransaction.external_transaction_id == str(external_ref)) |
            (PaymentTransaction.idempotency_key == str(external_ref))
        ).first()
        
    if not tx:
        # If not found immediately, we can check database transactions for general match
        logger.warning(f"Webhook received for unknown transaction ref: {external_ref}")
        return jsonify({'error': 'Transaction not found'}), 404
        
    # Retrieve gateway config for this company
    config = PaymentGatewayConfig.query.filter_by(company_id=tx.company_id).first()
    if not config or config.gateway_provider.value != provider:
        return jsonify({'error': 'Config mismatch'}, 400)
        
    # Verify cryptographic signature using adapter
    from services.payment_gateways.factory import PaymentAdapterFactory
    try:
        adapter = PaymentAdapterFactory.get_adapter(
            provider=config.gateway_provider.value,
            credentials=config.credentials,
            config_payload=config.config_payload,
            sandbox_mode=config.sandbox_mode
        )
        
        # Verify webhook signature (Stripe / PayPal / MP / Kushki / Nuvei)
        is_valid = adapter.verify_webhook(raw_body, headers)
        if not is_valid:
            logger.warning(f"Invalid webhook signature received for provider: {provider}")
            return jsonify({'error': 'Invalid signature'}), 401
            
        # Webhook verified successfully! Update transaction status
        # Parse status based on provider response format
        new_status = TransactionStatus.PENDING
        
        if provider == 'stripe':
            event_type = data.get('type')
            if event_type == 'payment_intent.succeeded':
                new_status = TransactionStatus.CAPTURED
            elif event_type == 'payment_intent.payment_failed':
                new_status = TransactionStatus.FAILED
                tx.error_message = data.get('data', {}).get('object', {}).get('last_payment_error', {}).get('message')
                
        elif provider == 'paypal':
            event_type = data.get('event_type')
            if event_type == 'PAYMENT.CAPTURE.COMPLETED':
                new_status = TransactionStatus.CAPTURED
            elif event_type == 'PAYMENT.CAPTURE.DENIED':
                new_status = TransactionStatus.FAILED
                
        elif provider == 'mercadopago':
            # Query the actual state from API to prevent spoofing
            if data.get('action') == 'payment.updated':
                payment_id = data.get('data', {}).get('id')
                # Fetch details using adapter
                res = adapter.charge(NormalizedTransactionRequest(
                    amount=tx.amount, currency=tx.currency, idempotency_key=tx.idempotency_key, payment_token=payment_id
                ))
                if res.success:
                    new_status = TransactionStatus.CAPTURED
                else:
                    new_status = TransactionStatus.FAILED
                    
        elif provider == 'kushki':
            transaction_status = data.get('transactionStatus')
            if transaction_status == 'APPROVED':
                new_status = TransactionStatus.CAPTURED
            elif transaction_status == 'DECLINED':
                new_status = TransactionStatus.FAILED
                
        elif provider == 'nuvei':
            dmn_status = data.get('transactionStatus') or data.get('status')
            if dmn_status == 'APPROVED':
                new_status = TransactionStatus.CAPTURED
            elif dmn_status == 'DECLINED':
                new_status = TransactionStatus.FAILED
                
        elif provider == 'dlocal_go':
            dl_status = data.get('status')
            if dl_status == 'PAID':
                new_status = TransactionStatus.CAPTURED
            elif dl_status == 'REJECTED':
                new_status = TransactionStatus.FAILED

        # Update and save
        tx.status = new_status
        tx.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Fire background sync task to update CRM/ERP if configured
        try:
            from services.payment_gateways.sync import sync_transaction_to_crm_erp
            sync_transaction_to_crm_erp(tx.id)
        except Exception as sync_err:
            logger.error(f"CRM/ERP Sync failed: {sync_err}")
            
        return jsonify({'status': 'processed'})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({'error': str(e)}), 500
