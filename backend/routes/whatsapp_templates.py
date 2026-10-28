from routing import APIRouter, Response, current_app, get_jwt_identity, jsonify, jwt_required, request
"""
WhatsApp Templates API Routes (Meta Graph API v21.0 HSM Management & AI Analytics)
"""
import logging
from extensions import db
from models.user import User, UserRole
from models.whatsapp_template import WhatsAppTemplate
from services.meta_template_service import MetaTemplateService

logger = logging.getLogger(__name__)

whatsapp_templates_bp = APIRouter('whatsapp_templates', __name__)


def get_user_company():
    """Helper to get current user's company"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None
        if user.company:
            return user.company
        if user.role == UserRole.SUPER_ADMIN:
            from models.company import Company
            return Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
        return None
    except Exception as e:
        logger.error(f"[whatsapp_templates] get_user_company error: {e}")
        return None


@whatsapp_templates_bp.route('/', methods=['GET'])
@jwt_required()
def list_templates():
    """List all WhatsApp Cloud API templates for current company."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    templates = WhatsAppTemplate.query.filter_by(company_id=company.id).order_by(WhatsAppTemplate.updated_at.desc()).all()
    return jsonify({
        'success': True,
        'templates': [t.to_dict() for t in templates]
    })


@whatsapp_templates_bp.route('/sync', methods=['POST'])
@jwt_required()
def sync_templates():
    """Fetch templates directly from Meta Graph API and sync local DB."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    result = MetaTemplateService.sync_templates_from_meta(company.id)
    if not result.get('success'):
        return jsonify(result), 400

    templates = WhatsAppTemplate.query.filter_by(company_id=company.id).order_by(WhatsAppTemplate.updated_at.desc()).all()
    return jsonify({
        'success': True,
        'synced_count': result.get('synced_count', 0),
        'templates': [t.to_dict() for t in templates]
    })


@whatsapp_templates_bp.route('/create', methods=['POST'])
@jwt_required()
def create_template():
    """Create a new Meta WhatsApp template (POST /message_templates)."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    result = MetaTemplateService.create_template_on_meta(company.id, data)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result), 201


@whatsapp_templates_bp.route('/generate-ai', methods=['POST'])
@jwt_required()
def generate_ai_template():
    """Generate an AI-optimized WhatsApp template based on conversion goals."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    goal = data.get('goal', 'Aumentar ventas e interés')
    audience = data.get('target_audience', 'Prospectos calificados')

    result = MetaTemplateService.generate_ai_optimized_template(company.id, goal, audience)
    return jsonify(result)


@whatsapp_templates_bp.route('/<int:template_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_template(template_id):
    """Update an existing WhatsApp template on Meta Graph API and locally."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    result = MetaTemplateService.update_template_on_meta(company.id, template_id, data)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)


@whatsapp_templates_bp.route('/<int:template_id>', methods=['DELETE'])
@jwt_required()
def delete_template(template_id):
    """Delete a WhatsApp template on Meta Graph API and locally."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    result = MetaTemplateService.delete_template_on_meta(company.id, template_id)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)
