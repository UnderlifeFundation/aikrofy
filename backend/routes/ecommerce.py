from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
E-commerce Configuration Routes
Endpoints for managing e-commerce platform connections per company.
"""
from datetime import datetime


from extensions import db
from models.user import User
from models.ecommerce_config import EcommerceConfig, EcommercePlatform

ecommerce_bp = APIRouter('ecommerce', __name__)


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


# ------------------------------------------------------------------
# Credential field definitions per platform (for frontend rendering)
# ------------------------------------------------------------------
PLATFORM_FIELDS = {
    'shopify': {
        'label': 'Shopify',
        'fields': [
            {'key': 'access_token', 'label': 'Admin API Access Token', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'mystore.myshopify.com',
        'url_help': 'Your Shopify store domain (without https://)',
    },
    'woocommerce': {
        'label': 'WooCommerce',
        'fields': [
            {'key': 'consumer_key', 'label': 'Consumer Key', 'type': 'password', 'required': True},
            {'key': 'consumer_secret', 'label': 'Consumer Secret', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'www.mystore.com',
        'url_help': 'Your WordPress/WooCommerce site URL',
    },
    'vtex': {
        'label': 'VTEX',
        'fields': [
            {'key': 'app_key', 'label': 'Application Key', 'type': 'password', 'required': True},
            {'key': 'app_token', 'label': 'Application Token', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'mystore.vtexcommercestable.com.br',
        'url_help': 'Your VTEX account URL',
    },
    'magento': {
        'label': 'Magento / Adobe Commerce',
        'fields': [
            {'key': 'access_token', 'label': 'Integration Access Token', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'www.mystore.com',
        'url_help': 'Your Magento store URL',
    },
    'prestashop': {
        'label': 'PrestaShop',
        'fields': [
            {'key': 'api_key', 'label': 'Webservice API Key', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'www.mystore.com',
        'url_help': 'Your PrestaShop store URL',
    },
    'bigcommerce': {
        'label': 'BigCommerce',
        'fields': [
            {'key': 'store_hash', 'label': 'Store Hash', 'type': 'text', 'required': True},
            {'key': 'access_token', 'label': 'API Access Token', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'store-xxxxx.mybigcommerce.com',
        'url_help': 'Your BigCommerce store domain',
    },
}


@ecommerce_bp.route('/platforms', methods=['GET'])
@jwt_required()
def get_platforms():
    """Return available platforms and their credential schemas."""
    return jsonify({'platforms': PLATFORM_FIELDS})


@ecommerce_bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get current company e-commerce configuration."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    config = EcommerceConfig.query.filter_by(company_id=company.id).first()
    if not config:
        return jsonify({'config': None})

    return jsonify({'config': config.to_dict()})


@ecommerce_bp.route('/config', methods=['POST'])
@jwt_required()
def save_config():
    """Create or update e-commerce configuration."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json()
    platform_str = data.get('platform', '')
    store_url = data.get('store_url', '').strip()
    credentials = data.get('credentials', {})

    # Validate platform
    try:
        platform = EcommercePlatform(platform_str)
    except ValueError:
        return jsonify({'error': f'Unsupported platform: {platform_str}'}), 400

    if not store_url:
        return jsonify({'error': 'Store URL is required'}), 400

    # Validate required credential fields
    platform_def = PLATFORM_FIELDS.get(platform_str, {})
    for field in platform_def.get('fields', []):
        if field.get('required') and not credentials.get(field['key']):
            return jsonify({'error': f"Field '{field['label']}' is required"}), 400

    # Upsert
    config = EcommerceConfig.query.filter_by(company_id=company.id).first()
    if config:
        config.platform = platform
        config.store_url = store_url
        config.credentials = credentials
        config.is_connected = False  # Reset until re-tested
        config.last_error = None
    else:
        config = EcommerceConfig(
            company_id=company.id,
            platform=platform,
            store_url=store_url,
            credentials=credentials,
        )
        db.session.add(config)

    db.session.commit()

    return jsonify({
        'message': 'E-commerce configuration saved',
        'config': config.to_dict(),
    })


@ecommerce_bp.route('/test', methods=['POST'])
@jwt_required()
def test_connection():
    """Test the stored e-commerce credentials by making a live API call."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    config = EcommerceConfig.query.filter_by(company_id=company.id).first()
    if not config:
        return jsonify({'error': 'No e-commerce configuration found. Save your credentials first.'}), 404

    # Use the factory to get the adapter
    from services.ecommerce.factory import get_ecommerce_adapter
    try:
        adapter = get_ecommerce_adapter(company)
        if not adapter:
            return jsonify({'error': 'Could not initialize adapter'}), 500

        result = adapter.test_connection()

        # Update connection status
        config.is_connected = result.get('success', False)
        config.last_tested_at = datetime.utcnow()
        config.last_error = result.get('error') if not result.get('success') else None
        db.session.commit()

        return jsonify({
            'result': result,
            'config': config.to_dict(),
        })

    except Exception as e:
        config.is_connected = False
        config.last_tested_at = datetime.utcnow()
        config.last_error = str(e)
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@ecommerce_bp.route('/disconnect', methods=['POST'])
@jwt_required()
def disconnect():
    """Remove e-commerce configuration for the company."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    config = EcommerceConfig.query.filter_by(company_id=company.id).first()
    if config:
        db.session.delete(config)
        db.session.commit()

    return jsonify({'message': 'E-commerce disconnected'})
