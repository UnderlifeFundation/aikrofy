"""
Enterprise API Routes - Visual Graphs, Dynamic Actions, Trust Guardrails, and Handover
"""
import logging
from routing import APIRouter, jsonify, request, jwt_required, get_jwt_identity
from extensions import db
from models.user import User, UserRole
from models.company import Company
from models.company_agent_graph import CompanyAgentGraph
from models.dynamic_action import DynamicAction, HttpMethod, AuthType
from models.trust_guardrail import TrustGuardrail, GuardrailType, GuardrailAction
from models.conversation import Conversation, HandoverStatus
from services.graph_compiler_service import GraphCompilerService
from services.handover_service import HandoverService
from services.dynamic_tools import DynamicToolsService

logger = logging.getLogger(__name__)

enterprise_bp = APIRouter('enterprise', __name__)

def get_current_company():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None, None
        if user.company:
            return user, user.company
        if user.role == UserRole.SUPER_ADMIN:
            comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
            return user, comp
        return None, None
    except Exception as e:
        logger.error(f"Error getting company context: {e}")
        return None, None

# ─── 1. KROF STUDIO: VISUAL FLOW CANVAS ROUTES ─────────────────────────────────

@enterprise_bp.route('/graphs', methods=['GET'])
@jwt_required()
def list_graphs():
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    graphs = CompanyAgentGraph.query.filter_by(company_id=company.id, is_active=True).all()
    return jsonify({'graphs': [g.to_dict() for g in graphs]})

@enterprise_bp.route('/graphs', methods=['POST'])
@jwt_required()
def create_or_save_graph():
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    graph_id = data.get('id')
    canvas_data = data.get('canvas_data', {})
    name = data.get('name', 'Flujo de Conversación Krof')
    description = data.get('description', '')

    if graph_id:
        graph = CompanyAgentGraph.query.filter_by(id=graph_id, company_id=company.id).first()
        if not graph:
            return jsonify({'error': 'Graph not found'}), 404
        graph.name = name
        graph.description = description
        graph.canvas_data = canvas_data
        graph.compiled_spec = GraphCompilerService.compile_canvas(canvas_data)
    else:
        compiled = GraphCompilerService.compile_canvas(canvas_data)
        graph = CompanyAgentGraph(
            company_id=company.id,
            name=name,
            description=description,
            canvas_data=canvas_data,
            compiled_spec=compiled,
            is_published=False,
            version=1
        )
        db.session.add(graph)

    db.session.commit()
    return jsonify({'success': True, 'graph': graph.to_dict()})

@enterprise_bp.route('/graphs/<int:graph_id>/publish', methods=['POST'])
@jwt_required()
def publish_graph(graph_id):
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        graph = CompanyAgentGraph.query.filter_by(id=graph_id, company_id=company.id).first()
        if not graph:
            return jsonify({'error': 'Graph not found'}), 404
        published = GraphCompilerService.save_and_publish_graph(graph_id, company.id, graph.canvas_data)
        return jsonify({'success': True, 'graph': published.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ─── 2. NO-CODE DYNAMIC ACTION CONNECTORS ──────────────────────────────────────

@enterprise_bp.route('/actions', methods=['GET'])
@jwt_required()
def list_actions():
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    actions = DynamicAction.query.filter_by(company_id=company.id, is_active=True).all()
    return jsonify({'actions': [a.to_dict(include_secrets=False) for a in actions]})

@enterprise_bp.route('/actions', methods=['POST'])
@jwt_required()
def create_action():
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    action = DynamicAction(
        company_id=company.id,
        name=data.get('name', 'custom_action').lower().replace(' ', '_'),
        display_name=data.get('display_name', 'Custom Action'),
        description=data.get('description', ''),
        endpoint_url=data.get('endpoint_url', ''),
        http_method=data.get('http_method', 'POST'),
        auth_type=data.get('auth_type', 'none'),
        auth_config=data.get('auth_config', {}),
        parameters_schema=data.get('parameters_schema', []),
        headers=data.get('headers', {}),
        static_payload=data.get('static_payload', {}),
        response_path=data.get('response_path', None)
    )
    db.session.add(action)
    db.session.commit()
    return jsonify({'success': True, 'action': action.to_dict(include_secrets=False)})

@enterprise_bp.route('/actions/<int:action_id>', methods=['DELETE'])
@jwt_required()
def delete_action(action_id):
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    action = DynamicAction.query.filter_by(id=action_id, company_id=company.id).first()
    if not action:
        return jsonify({'error': 'Action not found'}), 404
    db.session.delete(action)
    db.session.commit()
    return jsonify({'success': True})

# ─── 3. TRUST & GOVERNANCE GUARDRAILS ──────────────────────────────────────────

@enterprise_bp.route('/guardrails', methods=['GET'])
@jwt_required()
def list_guardrails():
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    guardrails = TrustGuardrail.query.filter_by(company_id=company.id, is_active=True).all()
    return jsonify({'guardrails': [g.to_dict() for g in guardrails]})

@enterprise_bp.route('/guardrails', methods=['POST'])
@jwt_required()
def create_guardrail():
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    guardrail = TrustGuardrail(
        company_id=company.id,
        name=data.get('name', 'Regla de Seguridad'),
        guardrail_type=data.get('guardrail_type', 'pii_masking'),
        action=data.get('action', 'mask'),
        rules=data.get('rules', {})
    )
    db.session.add(guardrail)
    db.session.commit()
    return jsonify({'success': True, 'guardrail': guardrail.to_dict()})

# ─── 4. LIVE HANDOVER CONTROLS ────────────────────────────────────────────────

@enterprise_bp.route('/handover/<int:conversation_id>/takeover', methods=['POST'])
@jwt_required()
def human_takeover(conversation_id):
    user, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    conv = Conversation.query.filter_by(id=conversation_id, company_id=company.id).first()
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    conv = HandoverService.execute_handover(conv, reason=f"Tomada manualmente por operador: {user.name}")
    conv.assigned_user_id = user.id
    db.session.commit()

    return jsonify({'success': True, 'conversation': conv.to_dict()})

@enterprise_bp.route('/handover/<int:conversation_id>/release', methods=['POST'])
@jwt_required()
def release_to_bot(conversation_id):
    _, company = get_current_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    conv = Conversation.query.filter_by(id=conversation_id, company_id=company.id).first()
    if not conv:
        return jsonify({'error': 'Conversation not found'}), 404

    conv = HandoverService.release_to_ai(conv)
    return jsonify({'success': True, 'conversation': conv.to_dict()})
