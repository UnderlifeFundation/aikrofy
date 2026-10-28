from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Knowledge Graph / Brain Galaxy Routes
Returns a graph (nodes + edges) connecting:
  - Documents (RAG)
  - Skills (CompanySkill)
  - Media assets (CompanyMediaAsset)
  - Agents
  - Departments
Used by the Brain Knowledge Galaxy visualization.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from typing import Any

from extensions import db
from models.user import User
from models.agent import Agent, AgentObjective
from models.department import Department
from models.document import Document
from models.company_skill import CompanySkill
from models.media_asset import CompanyMediaAsset

logger = logging.getLogger(__name__)

knowledge_graph_bp = APIRouter('knowledge_graph', __name__)


def _get_company():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return None
    from decorators import get_current_company_context
    return get_current_company_context(user, request)


@knowledge_graph_bp.route('/knowledge-graph', methods=['GET'])
@jwt_required()
def get_knowledge_graph():
    """
    GET /api/rag/knowledge-graph
    Returns:
    {
      nodes: [{ id, type, label, description, metadata }],
      edges: [{ source, target, relation }],
      stats: { documents, skills, media, agents, departments }
    }

    Node types: 'document' | 'skill' | 'media' | 'agent' | 'department'
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    try:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        # ── Documents ────────────────────────────────────────────────────────
        documents = (
            Document.query
            .filter_by(company_id=company.id)
            .limit(100)
            .all()
        )
        for doc in documents:
            node_id = f'doc_{doc.id}'
            d = doc.to_dict() if hasattr(doc, 'to_dict') else {}
            nodes.append({
                'id': node_id,
                'type': 'document',
                'label': d.get('filename') or d.get('name') or f'Documento {doc.id}',
                'description': d.get('description') or d.get('summary') or '',
                'metadata': {
                    'created_at': d.get('created_at'),
                    'file_type': d.get('file_type') or d.get('mimetype'),
                },
            })

        # ── Skills ───────────────────────────────────────────────────────────
        skills = (
            CompanySkill.query
            .filter_by(company_id=company.id)
            .limit(50)
            .all()
        )
        for skill in skills:
            node_id = f'skill_{skill.id}'
            s = skill.to_dict() if hasattr(skill, 'to_dict') else {}
            nodes.append({
                'id': node_id,
                'type': 'skill',
                'label': s.get('name') or f'Skill {skill.id}',
                'description': s.get('description') or '',
                'metadata': {
                    'category': s.get('category'),
                    'status': s.get('status'),
                },
            })

        # ── Media Assets ─────────────────────────────────────────────────────
        media_assets = (
            CompanyMediaAsset.query
            .filter_by(company_id=company.id)
            .limit(80)
            .all()
        )
        for asset in media_assets:
            node_id = f'media_{asset.id}'
            a = asset.to_dict() if hasattr(asset, 'to_dict') else {}
            nodes.append({
                'id': node_id,
                'type': 'media',
                'label': a.get('original_filename') or a.get('filename') or f'Media {asset.id}',
                'description': a.get('folder') or '',
                'metadata': {
                    'media_type': a.get('media_type'),
                    'file_url': a.get('file_url'),
                    'keywords': a.get('keywords'),
                },
            })

        # ── Agents ───────────────────────────────────────────────────────────
        agents = (
            Agent.query
            .filter_by(company_id=company.id, is_active=True)
            .all()
        )
        for agent in agents:
            node_id = f'agent_{agent.id}'
            nodes.append({
                'id': node_id,
                'type': 'agent',
                'label': agent.name,
                'description': agent.description or '',
                'metadata': {
                    'objective': agent.objective.value if hasattr(agent.objective, 'value') else str(agent.objective),
                    'tone': agent.tone.value if hasattr(agent.tone, 'value') else str(agent.tone),
                    'priority': agent.priority,
                },
            })

        # ── Departments ──────────────────────────────────────────────────────
        departments = (
            Department.query
            .filter_by(company_id=company.id, is_active=True)
            .all()
        )
        for dept in departments:
            node_id = f'dept_{dept.id}'
            nodes.append({
                'id': node_id,
                'type': 'department',
                'label': dept.name,
                'description': dept.description or '',
                'metadata': {
                    'data_access_level': dept.data_access_level,
                    'employee_count': dept.employees.count() if hasattr(dept.employees, 'count') else 0,
                },
            })

        # ── Edges ────────────────────────────────────────────────────────────
        # Connect Obsidian / Pinecone Memory Core
        nodes.insert(0, {
            'id': 'core_pinecone',
            'type': 'department',
            'label': 'Pinecone Vector Core',
            'description': 'Espacio vectorial principal de la empresa (dimensión 1536)',
            'metadata': {'status': 'active', 'dimension': 1536},
        })

        # Memory Core → Departments
        for dept in departments:
            edges.append({
                'source': 'core_pinecone',
                'target': f'dept_{dept.id}',
                'relation': 'pillar',
            })

        # Departments → Agents (hierarchical)
        for dept in departments:
            for agent in agents:
                edges.append({
                    'source': f'dept_{dept.id}',
                    'target': f'agent_{agent.id}',
                    'relation': 'gestiona_agente',
                })
                break  # Primary lead per department

        # Agents → Skills (limit 2-3 per agent to keep readable constallation)
        for i, agent in enumerate(agents):
            matched_skills = skills[i:i+3] if len(skills) > i else skills[:2]
            for skill in matched_skills:
                edges.append({
                    'source': f'agent_{agent.id}',
                    'target': f'skill_{skill.id}',
                    'relation': 'usa_skill',
                })

        # Departments / Agents → Documents (RAG)
        for doc in documents:
            # Connect document to closest department or first agent
            if doc.department_id:
                edges.append({
                    'source': f'dept_{doc.department_id}',
                    'target': f'doc_{doc.id}',
                    'relation': 'tiene_documento',
                })
            elif agents:
                target_agent = agents[hash(doc.filename) % len(agents)]
                edges.append({
                    'source': f'agent_{target_agent.id}',
                    'target': f'doc_{doc.id}',
                    'relation': 'consulta_rag',
                })

        # Skills / Campaigns → Media Assets
        for i, asset in enumerate(media_assets):
            if skills:
                target_skill = skills[i % len(skills)]
                edges.append({
                    'source': f'skill_{target_skill.id}',
                    'target': f'media_{asset.id}',
                    'relation': 'referencia_media',
                })

        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'documents': len(documents),
                'skills': len(skills),
                'media': len(media_assets),
                'agents': len(agents),
                'departments': len(departments),
                'total_nodes': len(nodes),
                'total_edges': len(edges),
            },
        })

    except Exception as exc:
        logger.exception('Error building knowledge graph: %s', exc)
        return jsonify({'error': 'Error interno del servidor'}), 500
