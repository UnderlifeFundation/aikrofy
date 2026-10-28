from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
CRM Configuration Routes
Endpoints for managing CRM platform connections per company.
"""
from datetime import datetime
import logging

from extensions import db
from models.user import User
from models.crm_config import CRMConfig, CRMPlatform

logger = logging.getLogger(__name__)
crm_bp = APIRouter('crm', __name__)


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
    'hubspot': {
        'label': 'HubSpot',
        'fields': [
            {'key': 'access_token', 'label': 'Private App Access Token', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'https://api.hubapi.com',
        'url_help': 'Your HubSpot API Gateway URL (defaults to https://api.hubapi.com)',
    },
    'salesforce': {
        'label': 'Salesforce',
        'fields': [
            {'key': 'client_id', 'label': 'Consumer Key (Client ID)', 'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Consumer Secret (Client Secret)', 'type': 'password', 'required': True},
            {'key': 'refresh_token', 'label': 'OAuth Refresh Token', 'type': 'password', 'required': True},
            {'key': 'instance_url', 'label': 'Instance URL (e.g. login.salesforce.com)', 'type': 'text', 'required': False},
        ],
        'url_placeholder': 'https://yourinstance.my.salesforce.com',
        'url_help': 'Your Salesforce My Domain URL',
    },
    'pipedrive': {
        'label': 'Pipedrive',
        'fields': [
            {'key': 'api_token', 'label': 'API Token / Personal Token', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'https://api.pipedrive.com/v1',
        'url_help': 'Pipedrive API v1 base URL (defaults to https://api.pipedrive.com/v1)',
    },
    'zoho': {
        'label': 'Zoho CRM',
        'fields': [
            {'key': 'access_token', 'label': 'Access Token (OAuth)', 'type': 'password', 'required': True},
            {'key': 'region', 'label': 'Data Center Region (e.g. .com, .eu, .in)', 'type': 'text', 'required': True},
        ],
        'url_placeholder': 'https://www.zohoapis.com/crm/v3',
        'url_help': 'Your Zoho CRM regional v3 endpoint URL',
    },
    'dynamics_365': {
        'label': 'Microsoft Dynamics 365',
        'fields': [
            {'key': 'access_token', 'label': 'OAuth Access Token', 'type': 'password', 'required': True},
            {'key': 'environment_url', 'label': 'Environment Web API URL', 'type': 'text', 'required': True},
        ],
        'url_placeholder': 'https://orgname.api.crm.dynamics.com',
        'url_help': 'Dynamics 365 / Dataverse Environment URL',
    },
    'custom': {
        'label': 'Custom Integration',
        'fields': [
            {'key': 'api_key', 'label': 'Custom System API Key / Auth', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'https://your-custom-crm-endpoint.com/api',
        'url_help': 'Endpoint to send CRM actions and custom schemas',
    }
}


@crm_bp.route('/platforms', methods=['GET'])
@jwt_required()
def get_platforms():
    """Return available CRM platforms and their credential schemas."""
    return jsonify({'platforms': PLATFORM_FIELDS})


@crm_bp.route('/config', methods=['GET'])
@jwt_required()
def get_config():
    """Get current company CRM configuration."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    config = CRMConfig.query.filter_by(company_id=company.id).first()
    if not config:
        return jsonify({'config': None})

    return jsonify({'config': config.to_dict()})


@crm_bp.route('/config', methods=['POST'])
@jwt_required()
def save_config():
    """Create or update CRM configuration."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json()
    platform_str = data.get('platform', '')
    crm_url = data.get('crm_url', '').strip()
    credentials = data.get('credentials', {})

    # Validate platform
    try:
        platform = CRMPlatform(platform_str)
    except ValueError:
        return jsonify({'error': f'Unsupported CRM platform: {platform_str}'}), 400

    # Validate required credential fields
    platform_def = PLATFORM_FIELDS.get(platform_str, {})
    for field in platform_def.get('fields', []):
        if field.get('required') and not credentials.get(field['key']):
            return jsonify({'error': f"Field '{field['label']}' is required"}), 400

    # Upsert
    config = CRMConfig.query.filter_by(company_id=company.id).first()
    if config:
        config.platform = platform
        config.crm_url = crm_url or None
        config.credentials = credentials
        config.is_connected = False  # Reset until re-tested
        config.last_error = None
    else:
        config = CRMConfig(
            company_id=company.id,
            platform=platform,
            crm_url=crm_url or None,
            credentials=credentials,
        )
        db.session.add(config)

    db.session.commit()

    return jsonify({
        'message': 'CRM configuration saved',
        'config': config.to_dict(),
    })


@crm_bp.route('/test', methods=['POST'])
@jwt_required()
def test_connection():
    """Test the stored CRM credentials by making a live API call."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    config = CRMConfig.query.filter_by(company_id=company.id).first()
    if not config:
        return jsonify({'error': 'No CRM configuration found. Save your credentials first.'}), 404

    # Use the factory to get the connector
    from services.crm.factory import get_crm_connector
    try:
        connector = get_crm_connector(company)
        if not connector:
            return jsonify({'error': 'Could not initialize CRM connector'}), 500

        result = connector.test_connection()

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


@crm_bp.route('/disconnect', methods=['POST'])
@jwt_required()
def disconnect():
    """Remove CRM configuration for the company."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    config = CRMConfig.query.filter_by(company_id=company.id).first()
    if config:
        db.session.delete(config)
        db.session.commit()

    return jsonify({'message': 'CRM disconnected'})


@crm_bp.route('/generate-mapping', methods=['POST'])
@jwt_required()
def generate_mapping():
    """AI code-first utility endpoint to auto-resolve mappings for custom schemas."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json()
    raw_sample = data.get('sample_payload')
    entity = data.get('entity')

    if not raw_sample or not entity:
        return jsonify({'error': 'sample_payload and entity are required fields'}), 400

    from services.crm.custom_mapper import CustomCRMMappingEngine
    openai_key = company.api_keys.get('openai') if company.api_keys else None
    
    mapping = CustomCRMMappingEngine.generate_mapping_with_llm(
        raw_json_sample=raw_sample,
        canonical_entity=entity,
        api_key=openai_key
    )

    return jsonify({
        'success': True,
        'mapping': mapping
    })


# ============================================================
# Pipeline / Kanban Stages Endpoints (Fase 6)
# ============================================================

@crm_bp.route('/stages', methods=['GET'])
@jwt_required()
def get_stages():
    """Get all pipeline stages for the company. Seed default stages if none exist."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    from models.funnel_stage import FunnelStage
    stages = FunnelStage.query.filter_by(company_id=company.id).order_by(FunnelStage.sort_order.asc()).all()

    if not stages:
        logger.info(f"Seeding default pipeline stages for company {company.id}")
        default_names = ["Lead", "Contactado", "Calificado", "Propuesta", "Negociación", "Ganado", "Perdido"]
        for idx, name in enumerate(default_names):
            stage = FunnelStage(
                company_id=company.id,
                name=name,
                sort_order=idx
            )
            db.session.add(stage)
        db.session.commit()
        # Fetch again
        stages = FunnelStage.query.filter_by(company_id=company.id).order_by(FunnelStage.sort_order.asc()).all()

    return jsonify({
        'success': True,
        'stages': [s.to_dict() for s in stages]
    }), 200


@crm_bp.route('/stages/move', methods=['POST'])
@jwt_required()
def move_customer_stage():
    """Move a contact to a different pipeline stage."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json()
    customer_id = data.get('customer_id')
    stage_id = data.get('stage_id')

    if not customer_id:
        return jsonify({'error': 'customer_id is required'}), 400

    from models.customer import Customer
    from models.funnel_stage import FunnelStage

    # 1. Fetch customer
    customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # 2. Verify stage exists and belongs to the company (if stage_id is not None)
    if stage_id is not None:
        stage = FunnelStage.query.filter_by(id=stage_id, company_id=company.id).first()
        if not stage:
            return jsonify({'error': 'Invalid funnel stage'}), 400
        customer.funnel_stage_id = stage.id
    else:
        customer.funnel_stage_id = None

    db.session.commit()

    # 3. Publish real-time pipeline event
    try:
        from services.realtime_service import RealtimeService
        RealtimeService.publish_lead_update(company.id, customer.id, {
            "lead_score": customer.lead_score,
            "funnel_stage_id": customer.funnel_stage_id
        })
    except Exception as err:
        logger.warning(f"Failed to publish lead move event: {err}")

    return jsonify({
        'success': True,
        'message': 'Lead moved successfully',
        'customer': customer.to_dict()
    }), 200


@crm_bp.route('/scoring-config', methods=['GET'])
@jwt_required()
def get_scoring_config():
    """Retrieve scoring configurations and decay settings for the company."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    from services.lead_scoring_service import LeadScoringService
    config = LeadScoringService.get_or_create_config(company.id)
    return jsonify({
        'success': True,
        'config': config.to_dict()
    }), 200


@crm_bp.route('/scoring-config', methods=['POST'])
@jwt_required()
def save_scoring_config():
    """Update company's hybrid lead scoring weights and manual rules."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    weight_ml = data.get('weight_ml')
    weight_manual = data.get('weight_manual')
    scoring_rules = data.get('scoring_rules', {})

    # Validate weights total 1.0
    if weight_ml is not None and weight_manual is not None:
        try:
            w_ml = float(weight_ml)
            w_manual = float(weight_manual)
            if abs((w_ml + w_manual) - 1.0) > 0.01:
                return jsonify({'error': 'Weights w_ML and w_Manual must sum up to exactly 1.0'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid weight values'}), 400

    from services.lead_scoring_service import LeadScoringService
    config = LeadScoringService.get_or_create_config(company.id)
    
    if weight_ml is not None:
        config.weight_ml = float(weight_ml)
    if weight_manual is not None:
        config.weight_manual = float(weight_manual)
    if scoring_rules:
        # Keep existing structure, only update fields passed
        current_rules = config.scoring_rules or {}
        current_rules.update(scoring_rules)
        config.scoring_rules = current_rules

    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Scoring configuration updated successfully',
        'config': config.to_dict()
    }), 200


