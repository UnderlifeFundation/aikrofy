"""
Campaign QR Codes & Telemetry Routes for Aikrofy
Handles:
1. Public high-speed redirection & scan logging: GET /r/<slug>
2. Multi-tenant CRUD operations (isolated per Company or via Agency context header)
3. Asset rendering / download endpoints (SVG, PNG, Embed snippet)
4. Aggregate & Granular Analytics for Campaigns

Copyright © 2026 WEBLIFETECH / AIKROFY. All Rights Reserved.
"""
import io
import json
import logging
from datetime import datetime
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request, redirect
from extensions import db
from models.user import User, UserRole
from models.campaign_qr import CampaignQRCode, QRCodeScanEvent
from models.company_campaign import CompanyCampaign
from models.agent import Agent
from models.landing_page import LandingPage
from models.media_asset import CompanyMediaAsset
from decorators import get_current_company_context

logger = logging.getLogger(__name__)
campaign_qr_bp = APIRouter('campaign_qr', __name__)

# Fallback QR generator via standard libraries if needed server-side
try:
    import qrcode
    from qrcode.image.svg import SvgImage
    HAS_QRCODE_LIB = True
except ImportError:
    HAS_QRCODE_LIB = False


# ==========================================
# PUBLIC REDIRECT & SCAN TELEMETRY ENGINE
# ==========================================

@campaign_qr_bp.route('/r/<slug>', methods=['GET'])
def resolve_qr_redirect(slug):
    """
    Public resolution endpoint: qr.aikrofy.com/r/<slug>
    Executes instant 302 redirection while registering granular scan telemetry.
    Never expires physically; destination can be updated dynamically anytime.
    """
    qr_code = CampaignQRCode.query.filter_by(slug=slug).first()
    if not qr_code:
        return jsonify({'error': 'Código QR no encontrado o inválido'}), 404

    target_url = qr_code.target_destination

    # If QR or parent campaign is inactive, route to fallback or fallback URL
    if not qr_code.is_active:
        target_url = qr_code.fallback_destination or "https://aikrofy.com"
    elif qr_code.campaign_id and qr_code.campaign:
        if not qr_code.campaign.is_currently_valid:
            target_url = qr_code.fallback_destination or qr_code.target_destination

    # Register Scan Event Asynchronously / Inline
    try:
        ua_header = request.headers.get('User-Agent', '')
        ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_addr and ',' in ip_addr:
            ip_addr = ip_addr.split(',')[0].strip()

        # Extract device type
        ua_lower = ua_header.lower()
        device_type = 'desktop'
        if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
            device_type = 'mobile'
        elif 'ipad' in ua_lower or 'tablet' in ua_lower:
            device_type = 'tablet'

        # OS detection
        os_family = 'Other'
        if 'iphone' in ua_lower or 'ipad' in ua_lower or 'ios' in ua_lower:
            os_family = 'iOS'
        elif 'android' in ua_lower:
            os_family = 'Android'
        elif 'macintosh' in ua_lower or 'mac os' in ua_lower:
            os_family = 'macOS'
        elif 'windows' in ua_lower:
            os_family = 'Windows'
        elif 'linux' in ua_lower:
            os_family = 'Linux'

        # Browser detection
        browser_family = 'Other'
        if 'chrome' in ua_lower and 'safari' in ua_lower and 'edg' not in ua_lower:
            browser_family = 'Chrome'
        elif 'safari' in ua_lower and 'chrome' not in ua_lower:
            browser_family = 'Safari'
        elif 'firefox' in ua_lower:
            browser_family = 'Firefox'
        elif 'edg' in ua_lower:
            browser_family = 'Edge'

        scan_event = QRCodeScanEvent(
            qr_code_id=qr_code.id,
            company_id=qr_code.company_id,
            campaign_id=qr_code.campaign_id,
            ip_address=ip_addr,
            user_agent=ua_header,
            device_type=device_type,
            os_family=os_family,
            browser_family=browser_family,
            referrer=request.referrer or request.headers.get('Referer'),
            utm_source=request.args.get('utm_source'),
            utm_medium=request.args.get('utm_medium'),
            utm_campaign=request.args.get('utm_campaign')
        )
        db.session.add(scan_event)

        # Update aggregated metrics
        qr_code.total_scans = (qr_code.total_scans or 0) + 1
        qr_code.last_scanned_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        logger.error(f"Error logging QR scan for {slug}: {e}")
        db.session.rollback()

    # Prepend schema if raw URL without protocol
    if target_url.startswith(('http://', 'https://', 'mailto:', 'tel:', 'wa.me')):
        if target_url.startswith('wa.me'):
            target_url = f"https://{target_url}"
    elif not target_url.startswith('/'):
        target_url = f"https://{target_url}"

    return redirect(target_url, code=302)


# ==========================================
# AUTHENTICATED MULTI-TENANT CRUD ENDPOINTS
# ==========================================

def _get_authenticated_tenant():
    """Resolves authenticated user and strictly isolated Company context (supports agency switching)."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return None, None
    company = get_current_company_context(user, request)
    return user, company


@campaign_qr_bp.route('/api/campaigns/qr', methods=['GET'])
@jwt_required()
def list_campaign_qr_codes():
    """List QR codes strictly scoped to the active tenant/agency company."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    campaign_id = request.args.get('campaign_id', type=int)
    channel = request.args.get('channel')

    query = CampaignQRCode.query.filter_by(company_id=company.id)
    if campaign_id:
        query = query.filter_by(campaign_id=campaign_id)
    if channel:
        query = query.filter_by(intended_channel=channel)

    qr_codes = query.order_by(CampaignQRCode.created_at.desc()).all()
    base_host = request.host_url.rstrip('/')

    return jsonify({
        'company_id': company.id,
        'company_name': company.name,
        'total': len(qr_codes),
        'qr_codes': [qr.to_dict(base_redirect_url=base_host) for qr in qr_codes]
    }), 200


@campaign_qr_bp.route('/api/campaigns/qr', methods=['POST'])
@jwt_required()
def create_campaign_qr_code():
    """Create a new hyper-configurable QR code for the active company."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    target_destination = data.get('target_destination', '').strip()
    target_type = data.get('target_type', 'url')
    campaign_id = data.get('campaign_id')
    intended_channel = data.get('intended_channel', 'omnichannel')
    visual_config = data.get('visual_config', {})
    fallback_destination = data.get('fallback_destination')

    if not name or not target_destination:
        return jsonify({'error': 'Nombre y destino son obligatorios'}), 400

    # Ensure campaign belongs to same company if specified
    if campaign_id:
        campaign = CompanyCampaign.query.filter_by(id=campaign_id, company_id=company.id).first()
        if not campaign:
            return jsonify({'error': 'Campaña no válida o no pertenece a esta empresa'}), 400

    qr_code = CampaignQRCode(
        company_id=company.id,
        campaign_id=campaign_id,
        created_by_user_id=user.id,
        name=name,
        target_type=target_type,
        target_destination=target_destination,
        fallback_destination=fallback_destination,
        intended_channel=intended_channel,
        visual_config=visual_config,
        is_dynamic=True,
        is_active=True
    )
    db.session.add(qr_code)
    db.session.commit()

    base_host = request.host_url.rstrip('/')
    return jsonify({
        'message': 'Código QR creado exitosamente',
        'qr_code': qr_code.to_dict(base_redirect_url=base_host)
    }), 201


@campaign_qr_bp.route('/api/campaigns/qr/<qr_id>', methods=['GET'])
@jwt_required()
def get_campaign_qr_code(qr_id):
    """Get single QR details with analytics summary."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    qr_code = CampaignQRCode.query.filter_by(id=qr_id, company_id=company.id).first()
    if not qr_code:
        return jsonify({'error': 'Código QR no encontrado'}), 404

    base_host = request.host_url.rstrip('/')
    return jsonify({
        'qr_code': qr_code.to_dict(base_redirect_url=base_host)
    }), 200


@campaign_qr_bp.route('/api/campaigns/qr/<qr_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_campaign_qr_code(qr_id):
    """
    Update target destination or visual configurations.
    Physical printed QR codes DO NOT CHANGE when destination is updated.
    """
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    qr_code = CampaignQRCode.query.filter_by(id=qr_id, company_id=company.id).first()
    if not qr_code:
        return jsonify({'error': 'Código QR no encontrado'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        qr_code.name = data['name'].strip()
    if 'target_destination' in data:
        qr_code.target_destination = data['target_destination'].strip()
    if 'fallback_destination' in data:
        qr_code.fallback_destination = data['fallback_destination'].strip()
    if 'target_type' in data:
        qr_code.target_type = data['target_type']
    if 'intended_channel' in data:
        qr_code.intended_channel = data['intended_channel']
    if 'visual_config' in data:
        qr_code.visual_config = data['visual_config']
    if 'is_active' in data:
        qr_code.is_active = bool(data['is_active'])

    db.session.commit()
    base_host = request.host_url.rstrip('/')
    return jsonify({
        'message': 'Código QR actualizado correctamente',
        'qr_code': qr_code.to_dict(base_redirect_url=base_host)
    }), 200


@campaign_qr_bp.route('/api/campaigns/qr/<qr_id>', methods=['DELETE'])
@jwt_required()
def delete_campaign_qr_code(qr_id):
    """Safely delete or deactivate QR code."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    qr_code = CampaignQRCode.query.filter_by(id=qr_id, company_id=company.id).first()
    if not qr_code:
        return jsonify({'error': 'Código QR no encontrado'}), 404

    db.session.delete(qr_code)
    db.session.commit()
    return jsonify({'message': 'Código QR eliminado exitosamente'}), 200


@campaign_qr_bp.route('/api/campaigns/qr/<qr_id>/analytics', methods=['GET'])
@jwt_required()
def get_campaign_qr_analytics(qr_id):
    """Returns telemetry analytics: scans by device, OS, browser, timeline."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    qr_code = CampaignQRCode.query.filter_by(id=qr_id, company_id=company.id).first()
    if not qr_code:
        return jsonify({'error': 'Código QR no encontrado'}), 404

    events = QRCodeScanEvent.query.filter_by(qr_code_id=qr_code.id).order_by(QRCodeScanEvent.scanned_at.desc()).limit(500).all()

    devices = {}
    os_breakdown = {}
    browsers = {}
    for ev in events:
        dev = ev.device_type or 'Desconocido'
        devices[dev] = devices.get(dev, 0) + 1
        os = ev.os_family or 'Desconocido'
        os_breakdown[os] = os_breakdown.get(os, 0) + 1
        br = ev.browser_family or 'Desconocido'
        browsers[br] = browsers.get(br, 0) + 1

    return jsonify({
        'qr_code_id': qr_code.id,
        'name': qr_code.name,
        'total_scans': qr_code.total_scans,
        'last_scanned_at': qr_code.last_scanned_at.isoformat() if qr_code.last_scanned_at else None,
        'devices': devices,
        'operating_systems': os_breakdown,
        'browsers': browsers,
        'recent_events': [ev.to_dict() for ev in events[:50]]
    }), 200


# ==========================================
# STRATEGIC CAMPAIGNS (EMPRESA) CRUD & RECURSOS
# ==========================================

@campaign_qr_bp.route('/api/campaigns', methods=['GET'])
@jwt_required()
def list_strategic_campaigns():
    """List all strategic campaigns with aggregated linked resources and metrics."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    campaigns = CompanyCampaign.query.filter_by(company_id=company.id).order_by(CompanyCampaign.created_at.desc()).all()
    base_host = request.host_url.rstrip('/')

    results = []
    for camp in campaigns:
        # Collect linked resources
        qrs = CampaignQRCode.query.filter_by(campaign_id=camp.id, company_id=company.id).all()
        agents = Agent.query.filter_by(company_id=company.id).filter(Agent.system_prompt.ilike(f"%[CAMPAIGN_ID:{camp.id}]%")).all()
        landings = LandingPage.query.filter_by(company_id=company.id).filter(LandingPage.meta_description.ilike(f"%[CAMPAIGN_ID:{camp.id}]%")).all()
        media_assets = CompanyMediaAsset.query.filter_by(company_id=company.id).filter(CompanyMediaAsset.description.ilike(f"%[CAMPAIGN_ID:{camp.id}]%")).all()

        total_scans = sum(q.total_scans or 0 for q in qrs)
        total_landing_views = sum(l.views_count or 0 for l in landings)

        c_data = camp.to_dict()
        c_data['metrics'] = {
            'total_qrs': len(qrs),
            'total_scans': total_scans,
            'total_agents': len(agents),
            'total_landings': len(landings),
            'total_landing_views': total_landing_views,
            'total_media': len(media_assets)
        }
        c_data['linked_resources'] = {
            'qrs': [q.to_dict(base_redirect_url=base_host) for q in qrs],
            'agents': [{'id': a.id, 'name': a.name, 'objective': a.objective.value if hasattr(a.objective, 'value') else a.objective} for a in agents],
            'landings': [{'id': l.id, 'title': l.title, 'slug': l.slug, 'views_count': l.views_count} for l in landings],
            'media': [{'id': m.id, 'filename': m.filename, 'file_url': m.file_url, 'media_type': m.media_type} for m in media_assets]
        }
        results.append(c_data)

    return jsonify({
        'company_id': company.id,
        'total': len(results),
        'campaigns': results
    }), 200


@campaign_qr_bp.route('/api/campaigns', methods=['POST'])
@jwt_required()
def create_strategic_campaign():
    """Create a new strategic marketing campaign with optional resource binding."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()

    if not name or not description:
        return jsonify({'error': 'El nombre y el objetivo/contexto de la campaña son obligatorios'}), 400

    start_date = None
    end_date = None
    if data.get('start_date'):
        try:
            start_date = datetime.fromisoformat(data['start_date'].replace('Z', ''))
        except Exception:
            pass
    if data.get('end_date'):
        try:
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', ''))
        except Exception:
            pass

    campaign = CompanyCampaign(
        company_id=company.id,
        name=name,
        description=description,
        is_active=bool(data.get('is_active', True)),
        start_date=start_date,
        end_date=end_date
    )
    db.session.add(campaign)
    db.session.commit()

    # Optional initial binding
    # 1. Bind agents
    agent_ids = data.get('agent_ids', [])
    for aid in agent_ids:
        ag = Agent.query.filter_by(id=aid, company_id=company.id).first()
        if ag:
            marker = f"\n[CAMPAIGN_ID:{campaign.id}]"
            if marker not in (ag.system_prompt or ''):
                ag.system_prompt = (ag.system_prompt or '') + marker

    # 2. Bind landing pages
    landing_ids = data.get('landing_ids', [])
    for lid in landing_ids:
        lp = LandingPage.query.filter_by(id=lid, company_id=company.id).first()
        if lp:
            marker = f" [CAMPAIGN_ID:{campaign.id}]"
            if marker not in (lp.meta_description or ''):
                lp.meta_description = (lp.meta_description or '') + marker

    # 3. Bind media assets
    media_ids = data.get('media_ids', [])
    for mid in media_ids:
        ma = CompanyMediaAsset.query.filter_by(id=mid, company_id=company.id).first()
        if ma:
            marker = f" [CAMPAIGN_ID:{campaign.id}]"
            if marker not in (ma.description or ''):
                ma.description = (ma.description or '') + marker

    # 4. Bind QRs
    qr_ids = data.get('qr_ids', [])
    for qid in qr_ids:
        qr = CampaignQRCode.query.filter_by(id=qid, company_id=company.id).first()
        if qr:
            qr.campaign_id = campaign.id

    db.session.commit()

    return jsonify({
        'message': 'Campaña estratégica creada exitosamente',
        'campaign': campaign.to_dict()
    }), 201


@campaign_qr_bp.route('/api/campaigns/<int:campaign_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_strategic_campaign(campaign_id):
    """Update strategic campaign parameters and status."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    campaign = CompanyCampaign.query.filter_by(id=campaign_id, company_id=company.id).first()
    if not campaign:
        return jsonify({'error': 'Campaña no encontrada'}), 404

    data = request.get_json() or {}
    if 'name' in data and data['name'].strip():
        campaign.name = data['name'].strip()
    if 'description' in data and data['description'].strip():
        campaign.description = data['description'].strip()
    if 'is_active' in data:
        campaign.is_active = bool(data['is_active'])
    if 'start_date' in data:
        try:
            campaign.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '')) if data['start_date'] else None
        except Exception:
            pass
    if 'end_date' in data:
        try:
            campaign.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '')) if data['end_date'] else None
        except Exception:
            pass

    db.session.commit()

    return jsonify({
        'message': 'Campaña actualizada exitosamente',
        'campaign': campaign.to_dict()
    }), 200


@campaign_qr_bp.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
@jwt_required()
def delete_strategic_campaign(campaign_id):
    """Delete a strategic campaign and disassociate its resources safely."""
    user, company = _get_authenticated_tenant()
    if not company:
        return jsonify({'error': 'Contexto de empresa no identificado'}), 403

    campaign = CompanyCampaign.query.filter_by(id=campaign_id, company_id=company.id).first()
    if not campaign:
        return jsonify({'error': 'Campaña no encontrada'}), 404

    # Remove campaign binding from QRs
    CampaignQRCode.query.filter_by(campaign_id=campaign.id, company_id=company.id).update({'campaign_id': None})

    db.session.delete(campaign)
    db.session.commit()

    return jsonify({'message': 'Campaña eliminada correctamente'}), 200

