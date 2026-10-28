from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Agent Hierarchy / Org Conductor Routes
Returns a hierarchical JSON tree: Conductor → Departments → Agents
Used by the Org Conductor view in the frontend.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from datetime import datetime, timedelta

from extensions import db
from models.user import User
from models.agent import Agent, AgentObjective
from models.department import Department
from models.employee import Employee
from models.channel import Channel, ChannelStatus
from models.document import Document
from models.company_skill import CompanySkill

logger = logging.getLogger(__name__)

agent_hierarchy_bp = APIRouter('agent_hierarchy', __name__)


def _get_company():
    """Resolve the current user's company (supports agency context)."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return None
    from decorators import get_current_company_context
    return get_current_company_context(user, request)


def _agent_live_stats(agent: Agent) -> dict:
    """
    Build lightweight live-stats for a single agent.
    Counts conversations active in the last 15 min.
    """
    from models.conversation import Conversation
    cutoff = datetime.utcnow() - timedelta(minutes=15)
    try:
        active_convs = (
            Conversation.query
            .filter(
                Conversation.company_id == agent.company_id,
                Conversation.updated_at >= cutoff,
            )
            .count()
        )
    except Exception:
        active_convs = 0

    return {
        'active_conversations': active_convs,
        'is_online': agent.is_active,
        'last_seen': agent.updated_at.isoformat() if agent.updated_at else None,
    }


def _get_core_system_agents(company_id: int) -> list[dict]:
    """
    Core immutable system workers operating under the Conductor hood.
    These execute background RAG indexing, telephony streaming, webhook dispatching, etc.
    """
    return [
        {
            'id': 'core_orchestrator',
            'name': 'Aikrofy Conductor (Core)',
            'role': 'Super Agent · Multi-Agent Orchestrator',
            'is_core': True,
            'is_active': True,
            'tier': 'lead',
            'category': 'ORCHESTRATOR',
            'tools': ['LangGraph', 'Task Router', 'Ollama/Claude', 'FastAPI Webhook'],
            'live': {'active_conversations': 0, 'is_online': True},
        },
        {
            'id': 'core_rag_memory',
            'name': 'Neural Memory Core (Pinecone)',
            'role': 'Vector Search & Real-time Embeddings',
            'is_core': True,
            'is_active': True,
            'tier': 'worker',
            'category': 'MEMORY',
            'tools': ['Pinecone', 'text-embedding-3-small', 'Document Chunker'],
            'live': {'active_conversations': 0, 'is_online': True},
        },
        {
            'id': 'core_comms_transporter',
            'name': 'Comms Dispatcher',
            'role': 'Omnichannel Messaging Transporter',
            'is_core': True,
            'is_active': True,
            'tier': 'worker',
            'category': 'COMMS',
            'tools': ['Baileys WhatsApp', 'Twilio Voice', 'Websocket Server', 'Email SMTP'],
            'live': {'active_conversations': 0, 'is_online': True},
        },
        {
            'id': 'core_telemetry_sentinel',
            'name': 'Telemetry & Fraud Sentinel',
            'role': 'GPS & Hardware Device Validator',
            'is_core': True,
            'is_active': True,
            'tier': 'worker',
            'category': 'SECURITY',
            'tools': ['Device Telemetry', 'GPS Validator', 'Rate Limiter'],
            'live': {'active_conversations': 0, 'is_online': True},
        },
    ]


@agent_hierarchy_bp.route('/hierarchy', methods=['GET'])
@jwt_required()
def get_agent_hierarchy():
    """
    GET /api/agents/hierarchy
    Returns the full org conductor tree for the authenticated company:
    {
      operator: { name, role, email },
      triad: { brain, conductor, comms },
      core_agents: [...],
      pillars: [{ department, agents: [...] }],
      stats: { total_agents, total_departments, active_conversations }
    }
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    try:
        # ── Conductor: the single INTERNAL / orchestrator agent ──────────────
        conductor_agent = Agent.query.filter(
            Agent.company_id == company.id,
            Agent.objective == AgentObjective.INTERNAL,
        ).first()

        if not conductor_agent:
            conductor_agent = (
                Agent.query
                .filter_by(company_id=company.id, is_active=True)
                .order_by(Agent.priority.desc())
                .first()
            )

        conductor_data = None
        if conductor_agent:
            conductor_data = {
                **conductor_agent.to_dict(),
                'is_core': False,
                'tier': 'lead',
                'live': _agent_live_stats(conductor_agent),
            }
        else:
            # Stand-in default conductor
            conductor_data = {
                'id': 0,
                'name': 'Conductor Inteligente',
                'description': 'Orquestador central del ecosistema de agentes',
                'objective': 'INTERNAL',
                'is_core': True,
                'tier': 'lead',
                'live': {'active_conversations': 0, 'is_online': True},
            }

        # ── Triad: Brain Knowledge, Conductor, Comms Feed ───────────────────
        doc_count = Document.query.filter_by(company_id=company.id).count()
        skills_count = CompanySkill.query.filter_by(company_id=company.id).count()
        channels = Channel.query.filter_by(company_id=company.id).all()
        connected_channels = sum(1 for c in channels if c.status == ChannelStatus.CONNECTED)

        triad = {
            'brain': {
                'title': 'G-Brain RAG',
                'caption': f'{doc_count} docs · {skills_count} skills vectorizadas',
                'href': '/documents',
                'status': 'connected' if doc_count > 0 else 'idle',
            },
            'conductor': conductor_data,
            'comms': {
                'title': 'Comms Feed',
                'caption': f'{connected_channels}/{len(channels)} canales activos',
                'href': '/channels',
                'status': 'connected' if connected_channels > 0 else 'idle',
                'channels': [{'type': c.type.value if hasattr(c.type, 'value') else str(c.type), 'name': c.name, 'status': c.status.value if hasattr(c.status, 'value') else str(c.status)} for c in channels],
            },
        }

        # ── Pillars: active departments ──────────────────────────────────────
        departments = (
            Department.query
            .filter_by(company_id=company.id, is_active=True)
            .order_by(Department.name)
            .all()
        )

        all_custom_agents = (
            Agent.query
            .filter_by(company_id=company.id, is_active=True)
            .all()
        )

        pillars = []
        if departments:
            # Distribute agents or assign by heuristics/name match
            for idx, d in enumerate(departments):
                dept_tools = ['Pinecone RAG', 'Conversation Router', 'Audit Log']
                if 'ventas' in d.name.lower() or 'sales' in d.name.lower():
                    dept_tools += ['Stripe / PayPal', 'WhatsApp CRM', 'Funnel Tracking']
                elif 'soporte' in d.name.lower() or 'support' in d.name.lower():
                    dept_tools += ['Ticket Manager', 'Knowledge Base', 'Sentiment AI']
                elif 'marketing' in d.name.lower():
                    dept_tools += ['Campaign Ads', 'Landing Generator', 'Media Library']
                else:
                    dept_tools += ['FastAPI Worker', 'Background Task']

                # Agents in this dept
                agents_for_dept = [
                    {
                        **a.to_dict(),
                        'is_core': False,
                        'tier': 'lead' if (a.priority and a.priority > 5) else 'worker',
                        'live': _agent_live_stats(a),
                    }
                    for a in all_custom_agents
                    if a.id != (conductor_agent.id if conductor_agent else None)
                ]

                pillars.append({
                    'id': d.id,
                    'name': d.name,
                    'description': d.description or 'Pilar departamental activo',
                    'is_active': d.is_active,
                    'data_access_level': d.data_access_level,
                    'employee_count': d.employees.count() if hasattr(d.employees, 'count') else 0,
                    'tools': dept_tools,
                    'agents': agents_for_dept,
                })
        else:
            pillars = [{
                'id': 1,
                'name': 'Operaciones Generales',
                'description': 'Pilar de ejecución y atención de clientes',
                'is_active': True,
                'data_access_level': 'internal',
                'employee_count': 1,
                'tools': ['WhatsApp Baileys', 'Pinecone RAG', 'PayPal / Stripe', 'Audit Log'],
                'agents': [
                    {
                        **a.to_dict(),
                        'is_core': False,
                        'tier': 'lead' if (a.priority and a.priority > 5) else 'worker',
                        'live': _agent_live_stats(a),
                    }
                    for a in all_custom_agents
                    if a.id != (conductor_agent.id if conductor_agent else None)
                ],
            }]

        core_agents = _get_core_system_agents(company.id)
        total_agents = len(all_custom_agents) + len(core_agents)

        return jsonify({
            'operator': {
                'name': user.full_name if hasattr(user, 'full_name') and user.full_name else (user.email.split('@')[0].capitalize() if user and user.email else 'Operator'),
                'role': user.role.value if user and hasattr(user.role, 'value') else 'Administrator',
                'email': user.email if user else '',
            },
            'triad': triad,
            'conductor': conductor_data,
            'core_agents': core_agents,
            'pillars': pillars,
            'stats': {
                'total_agents': total_agents,
                'custom_agents': len(all_custom_agents),
                'core_agents': len(core_agents),
                'total_departments': len(pillars),
            },
        })

    except Exception as exc:
        logger.exception('Error building agent hierarchy: %s', exc)
        return jsonify({'error': 'Error interno del servidor'}), 500
