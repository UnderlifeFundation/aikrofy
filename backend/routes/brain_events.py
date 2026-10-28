from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Brain Events Routes
Provides SSE streaming and demo simulation endpoints for the Living Brain Canvas.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

brain_events_bp = APIRouter('brain_events', __name__)


def _get_company():
    """Resolve the current user's company."""
    user_id = get_jwt_identity()
    from models.user import User
    user = User.query.get(int(user_id))
    if not user:
        return None
    from decorators import get_current_company_context
    return get_current_company_context(user, request)


@brain_events_bp.route('/brain-events/simulate', methods=['POST'])
@jwt_required()
def simulate_brain_activity():
    """
    POST /api/rag/brain-events/simulate
    Simulates a full AI thought trace for demo / Living Brain Canvas testing.
    Body: { "query": "..." }
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    data = request.get_json() or {}
    query = str(data.get('query', 'Consulta de demostración')).strip()[:200]

    try:
        from services.brain_events_service import BrainEventsService
        import threading

        def _run_simulation():
            import time
            cid = company.id
            q_preview = query[:80]

            # Step 1: Agent awakens — Thought Start
            BrainEventsService.emit_thought_start(cid, "Conductor IA", q_preview)
            time.sleep(0.25)

            # Step 2: RAG retrieval starts
            BrainEventsService.emit_rag_query(cid, q_preview)
            time.sleep(0.35)

            # Step 3: RAG hits simulate document chunks found
            sample_docs = [
                ("doc_1", "precios_y_servicios.pdf", 0.91, "Los planes de suscripción incluyen..."),
                ("doc_2", "politica_de_atencion.pdf", 0.84, "El tiempo de respuesta promedio es..."),
                ("doc_3", "catalogo_productos.pdf", 0.77, "Catálogo actualizado con los productos..."),
            ]
            for doc_id, fname, score, preview in sample_docs:
                BrainEventsService.emit_rag_hit(cid, doc_id, fname, score, preview)
                time.sleep(0.2)

            # Step 4: Tool dispatch (e.g., sending a WhatsApp message)
            BrainEventsService.emit_tool_dispatch(cid, "whatsapp_send_message", input_preview=f"Respondiendo: {q_preview[:60]}")
            time.sleep(0.3)

            BrainEventsService.emit_tool_result(cid, "whatsapp_send_message", "success", "Mensaje enviado correctamente")
            time.sleep(0.2)

            # Step 5: Completion — ripple wave
            BrainEventsService.emit_response_complete(cid, "Conductor IA", tokens_used=487, channel="whatsapp")

        # Run simulation in background thread (non-blocking)
        thread = threading.Thread(target=_run_simulation, daemon=True)
        thread.start()

        return jsonify({
            'status': 'simulation_started',
            'query': query,
            'message': 'Brain simulation started. Watch the Living Brain Canvas for synaptic activity.',
        })

    except Exception as exc:
        logger.exception('Error in brain simulate: %s', exc)
        return jsonify({'error': 'Error interno del servidor'}), 500


@brain_events_bp.route('/brain-events/status', methods=['GET'])
@jwt_required()
def get_brain_status():
    """
    GET /api/rag/brain-events/status
    Returns current brain / agent activity status for the company.
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    try:
        from models.agent import Agent
        from models.conversation import Conversation
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(minutes=15)

        total_agents = Agent.query.filter_by(company_id=company.id, is_active=True).count()
        active_conversations = Conversation.query.filter(
            Conversation.company_id == company.id,
            Conversation.updated_at >= cutoff
        ).count()

        return jsonify({
            'status': 'active' if active_conversations > 0 else 'idle',
            'total_agents': total_agents,
            'active_conversations': active_conversations,
            'socket_room': f'company_room_{company.id}',
        })

    except Exception as exc:
        logger.exception('Error in brain status: %s', exc)
        return jsonify({'error': 'Error interno del servidor'}), 500


@brain_events_bp.route('/brain-events/topology', methods=['GET'])
@jwt_required()
def get_brain_topology():
    """
    GET /api/rag/brain-events/topology
    Returns the real, dynamic neural topology for the authenticated company,
    connecting channels, the LEM equilibrium guardian, agents, tools, and RAG documents.
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    try:
        from models.channel import Channel
        from models.agent import Agent
        from models.document import Document
        from models.payment_gateway import PaymentGatewayConfig

        nodes = []
        edges = []

        # 1. LEM Invariant Core (Latent Equilibrium Models - Neurosymbolic Arbiter)
        nodes.append({
            'id': 'lem_guardian',
            'type': 'lem',
            'label': 'Guardián LEM (E < 0.20)',
            'description': 'Motor determinista neurosimbólico de equilibrio de estados z[16] (Fail-Closed).',
            'glowIntensity': 0.8,
            'metadata': {
                'engine': 'Latent Equilibrium Models (LEM-Ops)',
                'threshold': 0.20,
                'status': 'active_fail_closed',
                'endpoint': 'https://lem.weblifetech.com/v1/verify',
                'avg_latency': '< 2ms'
            }
        })

        # 2. Conductor / Central Orchestrator
        nodes.append({
            'id': 'conductor_core',
            'type': 'conductor',
            'label': 'Krof (Conductor IA)',
            'description': 'Orquestador cognitivo de decisiones y enrutamiento dinámico.',
            'glowIntensity': 0.9,
            'metadata': {
                'role': 'orchestrator',
                'model': 'gpt-5-nano / Hybrid BYOK',
                'state': 'online'
            }
        })
        edges.append({
            'source': 'lem_guardian',
            'target': 'conductor_core',
            'color': '#f59e0b',
            'relation': 'invariante_aprobado'
        })

        # 3. Canales Habilitados (Channels)
        channels = Channel.query.filter_by(company_id=company.id).all()
        if not channels:
            # Default Webchat channel if none explicitly registered
            nodes.append({
                'id': 'channel_webchat_default',
                'type': 'channel',
                'label': 'Webchat Copilot',
                'description': 'Canal de mensajería web interactivo en tiempo real.',
                'glowIntensity': 0.5,
                'metadata': {'status': 'connected', 'type': 'webchat'}
            })
            edges.append({
                'source': 'channel_webchat_default',
                'target': 'lem_guardian',
                'color': '#10b981',
                'relation': 'inbound_message'
            })
        else:
            for ch in channels:
                ch_id = f"channel_{ch.id}"
                ch_type = ch.type.value if hasattr(ch.type, 'value') else str(ch.type)
                ch_status = ch.status.value if hasattr(ch.status, 'value') else str(ch.status)
                nodes.append({
                    'id': ch_id,
                    'type': 'channel',
                    'label': ch.name or f"Canal {ch_type.capitalize()}",
                    'description': f"Canal {ch_type} ({ch_status}).",
                    'glowIntensity': 0.6 if ch_status == 'connected' else 0.2,
                    'metadata': {
                        'type': ch_type,
                        'status': ch_status,
                        'phone': ch.phone_number,
                        'last_activity': ch.last_activity.isoformat() if ch.last_activity else None
                    }
                })
                edges.append({
                    'source': ch_id,
                    'target': 'lem_guardian',
                    'color': '#10b981',
                    'relation': 'inbound_message'
                })

        # 4. Agentes Reales (Agents)
        agents = Agent.query.filter_by(company_id=company.id, is_active=True).all()
        for ag in agents[:8]:  # Top active agents
            ag_id = f"agent_{ag.id}"
            nodes.append({
                'id': ag_id,
                'type': 'agent',
                'label': ag.name,
                'description': ag.description or f"Agente especializado {ag.name}",
                'glowIntensity': 0.5,
                'metadata': {
                    'agent_id': ag.id,
                    'objective': ag.objective.value if hasattr(ag.objective, 'value') else str(ag.objective),
                    'priority': getattr(ag, 'priority', 1)
                }
            })
            edges.append({
                'source': 'conductor_core',
                'target': ag_id,
                'color': '#6366f1',
                'relation': 'delega_tarea'
            })

        # 5. Herramientas & Integraciones Reales (Tools)
        # CRM Tool
        nodes.append({
            'id': 'tool_crm_pipeline',
            'type': 'tool',
            'label': 'CRM & Leads Pipeline',
            'description': 'Gestión de contactos, embudos de conversión y scoring dinámico.',
            'glowIntensity': 0.4,
            'metadata': {'module': 'crm', 'status': 'ready'}
        })
        edges.append({
            'source': 'conductor_core',
            'target': 'tool_crm_pipeline',
            'color': '#06b6d4',
            'relation': 'dispatches_tool'
        })

        # Gateways / Payments
        gateways = PaymentGatewayConfig.query.filter_by(company_id=company.id).all()
        nodes.append({
            'id': 'tool_payments',
            'type': 'tool',
            'label': 'Pasarela Pagos (Stripe/PayPal)',
            'description': 'Procesamiento de pagos y generación de enlaces de cobro.',
            'glowIntensity': 0.4,
            'metadata': {'status': 'configured' if gateways else 'unconfigured'}
        })
        edges.append({
            'source': 'conductor_core',
            'target': 'tool_payments',
            'color': '#06b6d4',
            'relation': 'dispatches_tool'
        })

        # LiveKit Voice Engine
        nodes.append({
            'id': 'tool_voice_livekit',
            'type': 'tool',
            'label': 'Motor Voz (LiveKit WebRTC)',
            'description': 'Conversación bidireccional de baja latencia con síntesis de voz.',
            'glowIntensity': 0.4,
            'metadata': {'status': 'ready', 'webrtc': 'active'}
        })
        edges.append({
            'source': 'conductor_core',
            'target': 'tool_voice_livekit',
            'color': '#06b6d4',
            'relation': 'dispatches_tool'
        })

        # 6. RAG Memory Core & Real Documents
        nodes.append({
            'id': 'rag_memory_core',
            'type': 'rag_chunk',
            'label': 'Memoria Vectorial RAG',
            'description': 'Base de conocimiento indexada en espacio vectorial semántico.',
            'glowIntensity': 0.6,
            'metadata': {'dimension': 1536, 'index': 'pinecone-hybrid'}
        })
        edges.append({
            'source': 'conductor_core',
            'target': 'rag_memory_core',
            'color': '#38bdf8',
            'relation': 'consulta_rag'
        })

        real_docs = Document.query.filter_by(company_id=company.id).limit(6).all()
        for doc in real_docs:
            d_id = f"doc_{doc.id}"
            nodes.append({
                'id': d_id,
                'type': 'rag_chunk',
                'label': doc.filename[:22],
                'description': f"Documento RAG: {doc.filename}",
                'glowIntensity': 0.3,
                'metadata': {
                    'doc_id': doc.id,
                    'file_type': doc.file_type,
                    'status': doc.status.value if hasattr(doc.status, 'value') else str(doc.status)
                }
            })
            edges.append({
                'source': 'rag_memory_core',
                'target': d_id,
                'color': '#38bdf8',
                'relation': 'chunk_relevance'
            })

        return jsonify({
            'company_id': company.id,
            'company_name': company.name,
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'channels_count': len(channels) or 1,
                'agents_count': len(agents),
                'tools_count': 3,
                'docs_count': len(real_docs),
                'total_nodes': len(nodes),
                'total_edges': len(edges)
            }
        })

    except Exception as exc:
        logger.exception('Error in get_brain_topology: %s', exc)
        return jsonify({'error': 'Error interno del servidor'}), 500

