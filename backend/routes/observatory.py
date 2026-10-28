from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Sentinel Observatory Routes - AI Agent Tracing, LEM-Ops & LEM-V4 Invariants,
LLM Token Consumption, and Security Telemetry.
Provides a unified LangSmith/Langfuse-grade observability hub for Aikrofy.

All figures are MEASURED (see services/turn_telemetry.py). When a value was not
captured for a turn it is returned as null so the UI shows "—" instead of a made-up
number.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from datetime import datetime, timedelta
from extensions import db
from models.user import User
from models.company import Company
from models.conversation import Conversation, Message, MessageRole
from models.trust_guardrail import TrustGuardrail
from services.token_credit_service import TokenCreditService

logger = logging.getLogger(__name__)
observatory_bp = APIRouter('observatory', __name__)

LEM_THRESHOLD = 0.20
_PREVIEW_CHARS = 140
_PAYLOAD_CHARS = 6000


def _get_company():
    """Resolve the current user's company."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return None
    from decorators import get_current_company_context
    return get_current_company_context(user, request)


def _role_value(msg):
    return msg.role.value if hasattr(msg.role, 'value') else str(msg.role)


def _is_assistant(msg):
    return str(_role_value(msg)).lower() == MessageRole.ASSISTANT.value


def _clip(text, limit=_PAYLOAD_CHARS):
    text = text or ''
    return text if len(text) <= limit else text[:limit] + f'… [+{len(text) - limit} chars]'


def _verdict(meta):
    """Normalised LEM verdict for a turn: SECURE_INVARIANT | BLOCKED | UNMEASURED."""
    if not meta or meta.get('lem_energy') is None:
        return 'UNMEASURED'
    if meta.get('lem_verdict') == 'blocked' or meta['lem_energy'] >= LEM_THRESHOLD:
        return 'BLOCKED'
    return 'SECURE_INVARIANT'


def _trace_summary(msg):
    meta = msg.trace_meta or {}
    usage = meta.get('usage') or {}
    return {
        'id': msg.id,
        'conversation_id': msg.conversation_id,
        'role': _role_value(msg),
        'content_preview': (msg.content or '')[:_PREVIEW_CHARS],
        'channel': msg.channel,
        'created_at': msg.created_at.isoformat() if msg.created_at else None,
        'latency_ms': msg.latency_ms,
        'tokens_used': msg.tokens_used,
        'tokens_in': usage.get('prompt_tokens'),
        'tokens_out': usage.get('completion_tokens'),
        'model': meta.get('model'),
        'agent_name': meta.get('agent_name'),
        'is_byok': meta.get('is_byok'),
        'credits_charged': meta.get('credits_charged'),
        'cost_usd': meta.get('cost_usd'),
        'tool_count': len(msg.tool_calls or []),
        'energy': meta.get('lem_energy'),
        'threshold': meta.get('lem_threshold', LEM_THRESHOLD),
        'deterministic_status': _verdict(meta),
        'has_telemetry': bool(meta),
    }


@observatory_bp.route('/metrics', methods=['GET'])
@jwt_required()
def get_observatory_metrics():
    """
    Returns observability metrics for the company, computed from real traces in the
    last 24h: requests, latency, tokens, cost, LEM energy and blocked risks, plus the
    two credit layers.
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        total_convs = Conversation.query.filter_by(company_id=company.id).count()

        recent = Message.query.join(Conversation).filter(
            Conversation.company_id == company.id,
            Message.created_at >= cutoff_24h,
        ).order_by(Message.created_at.desc()).limit(2000).all()
        assistant = [m for m in recent if _is_assistant(m)]

        latencies = [m.latency_ms for m in assistant if m.latency_ms is not None]
        tokens = [m.tokens_used for m in assistant if m.tokens_used is not None]
        metas = [m.trace_meta for m in assistant if m.trace_meta]
        energies = [x['lem_energy'] for x in metas if x.get('lem_energy') is not None]
        blocked = sum(1 for x in metas if _verdict(x) == 'BLOCKED')
        credits_spent = sum(x.get('credits_charged') or 0 for x in metas)
        cost_usd = sum(x.get('cost_usd') or 0.0 for x in metas)

        # 2-Layer Credit Engine Balances
        core_credits = company.credit_balance if company.credit_balance is not None else 0
        obs_credits = getattr(company, 'observability_credit_balance', None)
        if obs_credits is None:
            obs_credits = 50

        guardrails_active = TrustGuardrail.query.filter_by(company_id=company.id, is_active=True).count()

        # Single source of truth shared with the LEM engine and the agents.
        is_protected = TokenCreditService.has_lem_protection(company)
        routing_mode = getattr(company, 'llm_routing_mode', None) or 'core_pool'

        return jsonify({
            'success': True,
            'company_id': company.id,
            'provider': company.llm_provider or 'openai',
            'model': company.llm_model or 'gpt-5-nano',
            'is_byok': bool(company.api_keys and company.api_keys.get(company.llm_provider or 'openai'))
                       or routing_mode == 'byok',
            'llm_routing_mode': routing_mode,
            'credit_balance': core_credits,
            'observability_credit_balance': obs_credits,
            'protection_balance': max(core_credits, obs_credits),
            'is_protected': is_protected,
            'is_beta_account': bool(company.trial_activated) or bool(getattr(company, 'is_demo', False)),
            'layers': {
                'layer_1_core_operations': {
                    'name': 'Core Agent Operations (LLM, STT/TTS, Tools)',
                    'balance': core_credits,
                    'status': 'active' if core_credits > 0 or core_credits == -1 else 'depleted'
                },
                'layer_2_observability': {
                    'name': 'Telemetry, Live Neural Traces & E(z,S)',
                    'balance': obs_credits,
                    'status': 'active' if obs_credits > 0 or obs_credits == -1 else 'depleted'
                }
            },
            'metrics_24h': {
                'requests': len(assistant),
                'total_conversations': total_convs,
                'traced_requests': len(metas),
                'avg_latency_ms': round(sum(latencies) / len(latencies)) if latencies else None,
                'p95_latency_ms': sorted(latencies)[int(len(latencies) * 0.95) - 1] if len(latencies) >= 2 else (latencies[0] if latencies else None),
                'total_tokens': sum(tokens) if tokens else 0,
                'credits_spent': credits_spent,
                'cost_usd': round(cost_usd, 6),
                'lem_ops_evaluations': len(energies),
                'average_energy': round(sum(energies) / len(energies), 4) if energies else None,
                'risks_blocked': blocked,
                'lem_threshold': LEM_THRESHOLD,
                'active_guardrails': guardrails_active
            }
        }), 200
    except Exception as e:
        logger.error(f"[OBSERVATORY] Error fetching metrics: {e}")
        return jsonify({'error': str(e)}), 500


@observatory_bp.route('/traces', methods=['GET'])
@jwt_required()
def get_observatory_traces():
    """
    Returns recent agent turns (assistant replies) with measured latency, tokens,
    model, credits and LEM verdict. Supports ?limit, ?status=SECURE_INVARIANT|BLOCKED|UNMEASURED
    and ?channel.
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        limit = min(max(int(request.args.get('limit', 25)), 1), 100)
        status = (request.args.get('status') or '').upper()
        channel = (request.args.get('channel') or '').strip().lower()

        q = Message.query.join(Conversation).filter(
            Conversation.company_id == company.id,
            Message.role == MessageRole.ASSISTANT,
        )
        if channel:
            q = q.filter(Message.channel == channel)
        rows = q.order_by(Message.created_at.desc()).limit(limit * 4 if status else limit).all()

        traces = [_trace_summary(m) for m in rows]
        if status in ('SECURE_INVARIANT', 'BLOCKED', 'UNMEASURED'):
            traces = [t for t in traces if t['deterministic_status'] == status][:limit]

        return jsonify({'success': True, 'traces': traces}), 200
    except Exception as e:
        logger.error(f"[OBSERVATORY] Error fetching traces: {e}")
        return jsonify({'error': str(e)}), 500


@observatory_bp.route('/traces/<int:message_id>', methods=['GET'])
@jwt_required()
def get_observatory_trace_detail(message_id):
    """
    Deep-dive for one turn: the user input that triggered it, the output, tool calls,
    RAG evidence (MessageAudit), and the measured span waterfall.
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        msg = Message.query.join(Conversation).filter(
            Message.id == message_id,
            Conversation.company_id == company.id,  # tenant isolation
        ).first()
        if not msg:
            return jsonify({'error': 'Trace not found'}), 404

        # The user message that triggered this turn = latest user msg before it.
        trigger = Message.query.filter(
            Message.conversation_id == msg.conversation_id,
            Message.role == MessageRole.USER,
            Message.created_at <= msg.created_at,
            Message.id < msg.id,
        ).order_by(Message.id.desc()).first()

        meta = msg.trace_meta or {}

        tools = []
        for tc in (msg.tool_calls or []):
            if not isinstance(tc, dict):
                continue
            tools.append({
                'name': tc.get('tool') or tc.get('name') or 'tool',
                'arguments': tc.get('arguments') if 'arguments' in tc else tc.get('args'),
                'result': _clip(str(tc.get('result')), 1500) if tc.get('result') is not None else None,
            })

        audit = msg.audit
        rag = None
        if audit:
            rag = {
                'chunk_ids': audit.pinecone_chunk_ids or [],
                'metadata': audit.rag_metadata or {},
            }

        spans = list(meta.get('spans') or [])
        total_ms = msg.latency_ms
        # Derive each span's duration from the gap to the next measured event.
        for i, s in enumerate(spans):
            nxt = spans[i + 1]['at_ms'] if i + 1 < len(spans) else (total_ms if total_ms is not None else s['at_ms'])
            s['duration_ms'] = max(0, (nxt or 0) - s['at_ms'])

        detail = _trace_summary(msg)
        detail.update({
            'input': _clip(trigger.content) if trigger else None,
            'input_created_at': trigger.created_at.isoformat() if trigger and trigger.created_at else None,
            'output': _clip(msg.content),
            'tool_calls': tools,
            'rag': rag,
            'spans': spans,
            'total_ms': total_ms,
            'billed_usd': meta.get('billed_usd'),
            'lem_verdict': meta.get('lem_verdict'),
        })
        return jsonify({'success': True, 'trace': detail}), 200
    except Exception as e:
        logger.error(f"[OBSERVATORY] Error fetching trace {message_id}: {e}")
        return jsonify({'error': str(e)}), 500
