from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Funnel Live-Flow Routes
Returns live pipeline data: stages, contacts per stage, acquisition sources.
Used by the Neural Funnel Flow and Radial Acquisition Wheel views.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from extensions import db
from models.user import User
from models.customer import Customer
from models.funnel_stage import FunnelStage
from models.conversation import Conversation, Message
from models.contact_attribution import ContactAttribution
from models.transaction import Transaction, TransactionStatus
from sqlalchemy import func

logger = logging.getLogger(__name__)

funnel_live_bp = APIRouter('funnel_live', __name__)


def _get_company():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return None
    from decorators import get_current_company_context
    return get_current_company_context(user, request)


def _relationship_heat(customer: Customer) -> str:
    """
    Score a contact's 'heat' based on lead_score.
    hot ≥ 70 | warm 30-69 | cold < 30
    """
    score = customer.lead_score or 0
    if score >= 70:
        return 'hot'
    if score >= 30:
        return 'warm'
    return 'cold'


def _source_channel(customer: Customer, attribution_map: dict | None = None) -> str:
    """Extract source channel from ContactAttribution, customer metadata or conversation."""
    if attribution_map and customer.id in attribution_map:
        attr = attribution_map[customer.id]
        if attr.utm_source:
            src = attr.utm_source.strip().lower()
            if 'fb' in src or 'facebook' in src or 'meta' in src:
                return 'facebook'
            if 'ig' in src or 'insta' in src:
                return 'instagram'
            if 'google' in src or 'adwords' in src:
                return 'google'
            if 'wa' in src or 'whatsapp' in src:
                return 'whatsapp'
            if 'email' in src or 'newsletter' in src:
                return 'email'
            return src
        if attr.meta_click_id:
            return 'facebook'
        if attr.google_click_id:
            return 'google'

    meta = customer.customer_metadata or {}
    src = (
        meta.get('source_channel')
        or meta.get('utm_source')
        or meta.get('source')
        or meta.get('channel')
    )
    if src:
        src_lower = str(src).strip().lower()
        if 'wa' in src_lower or 'whatsapp' in src_lower:
            return 'whatsapp'
        if 'ig' in src_lower or 'insta' in src_lower:
            return 'instagram'
        if 'fb' in src_lower or 'facebook' in src_lower:
            return 'facebook'
        if 'email' in src_lower:
            return 'email'
        if 'google' in src_lower:
            return 'google'
        return src_lower
    
    # Fallback to phone prefix check or general inbound
    if customer.phone:
        return 'whatsapp'
    if customer.email:
        return 'website'
    return 'organic'


def _amount_usd(customer: Customer, txn_map: dict | None = None) -> float:
    """Extract potential deal amount or real completed transactions for this customer."""
    if txn_map and customer.id in txn_map:
        return float(txn_map[customer.id])
    
    meta = customer.customer_metadata or {}
    try:
        val = meta.get('deal_amount') or meta.get('amount') or meta.get('value')
        if val is not None:
            return float(val)
    except (TypeError, ValueError):
        pass
    
    # Estimated value based on lead score if positive
    if customer.lead_score and customer.lead_score > 50:
        return round(float(customer.lead_score * 12.5), 2)
    return 0.0


def _touch_count(customer_id: int) -> int:
    """Count messages/touches for a customer (proxy for conversation depth)."""
    try:
        conv = Conversation.query.filter_by(customer_id=customer_id).first()
        if not conv:
            return 0
        return Message.query.filter_by(conversation_id=conv.id).count()
    except Exception:
        return 0


@funnel_live_bp.route('/live-flow', methods=['GET'])
@jwt_required()
def get_live_flow():
    """
    GET /api/funnel/live-flow
    Returns:
    {
      stages: [{ id, name, sort_order, count, value_usd }],
      contacts: [{ id, name, stage_id, stage_name, relationship, touches,
                   source_channel, amount_usd, lead_score, phone, email }],
      sources: { organic: N, whatsapp: N, ... },
      kpis: { total_contacts, hot_leads, avg_score, total_value_usd }
    }
    """
    company = _get_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    try:
        # ── Funnel stages ────────────────────────────────────────────────────
        stages = (
            FunnelStage.query
            .filter_by(company_id=company.id)
            .order_by(FunnelStage.sort_order)
            .all()
        )

        stage_map = {s.id: s for s in stages}

        # ── Contacts ─────────────────────────────────────────────────────────
        customers = (
            Customer.query
            .filter_by(company_id=company.id)
            .order_by(Customer.lead_score.desc())
            .limit(300)  # Cap for performance
            .all()
        )
        customer_ids = [c.id for c in customers]

        # ── Preload attributions for these customers ────────────────────────
        attribution_map = {}
        if customer_ids:
            attrs = ContactAttribution.query.filter(
                ContactAttribution.company_id == company.id,
                ContactAttribution.customer_id.in_(customer_ids)
            ).all()
            for a in attrs:
                attribution_map[a.customer_id] = a

        # ── Preload transactions / revenue per customer ─────────────────────
        txn_map = {}
        if customer_ids:
            try:
                txns = db.session.query(
                    Transaction.customer_id,
                    func.sum(Transaction.amount).label('total')
                ).filter(
                    Transaction.company_id == company.id,
                    Transaction.customer_id.in_(customer_ids),
                    Transaction.status == TransactionStatus.COMPLETED.value
                ).group_by(Transaction.customer_id).all()
                for cid, total in txns:
                    if cid:
                        txn_map[cid] = float(total or 0)
            except Exception as e:
                logger.warning('Could not query transactions by customer_id: %s', e)

        # ── Also get total company revenue for KPI context ──────────────────
        overall_revenue = 0.0
        try:
            overall_revenue = float(db.session.query(
                func.sum(Transaction.amount)
            ).filter(
                Transaction.company_id == company.id,
                Transaction.status == TransactionStatus.COMPLETED.value
            ).scalar() or 0.0)
        except Exception:
            pass

        stage_counts: dict[int | None, int] = defaultdict(int)
        stage_values: dict[int | None, float] = defaultdict(float)
        source_counts: dict[str, int] = defaultdict(int)

        contacts_data = []
        for c in customers:
            stage_id = c.funnel_stage_id
            stage_counts[stage_id] += 1
            amount = _amount_usd(c, txn_map)
            stage_values[stage_id] += amount
            channel = _source_channel(c, attribution_map)
            source_counts[channel] += 1

            stage_name = stage_map[stage_id].name if stage_id and stage_id in stage_map else 'Sin etapa'

            contacts_data.append({
                'id': c.id,
                'name': c.full_name,
                'email': c.email,
                'phone': c.phone,
                'stage_id': stage_id,
                'stage_name': stage_name,
                'relationship': _relationship_heat(c),
                'touches': _touch_count(c.id),
                'source_channel': channel,
                'amount_usd': amount,
                'lead_score': c.lead_score,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            })

        stages_data = []
        for s in stages:
            stages_data.append({
                **s.to_dict(),
                'count': stage_counts.get(s.id, 0),
                'value_usd': round(stage_values.get(s.id, 0.0), 2),
            })

        # Unassigned bucket
        unassigned_count = stage_counts.get(None, 0)
        if unassigned_count > 0:
            stages_data.insert(0, {
                'id': None,
                'name': 'Sin etapa',
                'sort_order': -1,
                'count': unassigned_count,
                'value_usd': round(stage_values.get(None, 0.0), 2),
            })

        # ── KPIs ─────────────────────────────────────────────────────────────
        hot_leads = sum(1 for c in customers if (c.lead_score or 0) >= 70)
        avg_score = (
            round(sum(c.lead_score or 0 for c in customers) / len(customers), 1)
            if customers else 0
        )
        pipeline_value = round(sum(_amount_usd(c, txn_map) for c in customers), 2)
        total_value = max(pipeline_value, overall_revenue)

        return jsonify({
            'stages': stages_data,
            'contacts': contacts_data,
            'sources': dict(source_counts),
            'kpis': {
                'total_contacts': len(customers),
                'hot_leads': hot_leads,
                'avg_score': avg_score,
                'total_value_usd': round(total_value, 2),
                'pipeline_value_usd': pipeline_value,
                'completed_revenue_usd': round(overall_revenue, 2),
            },
        })

    except Exception as exc:
        logger.exception('Error building funnel live-flow: %s', exc)
        return jsonify({'error': 'Error interno del servidor'}), 500
