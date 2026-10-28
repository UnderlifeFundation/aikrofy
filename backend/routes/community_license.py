"""
Community Activation API Routes (/api/community)
Allows self-hosted instances to check and submit activation tokens,
and allows the Cloud instance to generate and verify activation tokens for the community.
"""
from routing import Blueprint, request, jsonify, jwt_required
from services.community_license_service import CommunityLicenseService

community_bp = Blueprint('community_license', __name__)


@community_bp.route('/status', methods=['GET'])
def get_activation_status():
    """
    Returns whether the current instance is activated, its edition, and registered organization.
    """
    is_comm = CommunityLicenseService.is_community_mode()
    stored = CommunityLicenseService.get_stored_activation()

    if not is_comm:
        # Running in Cloud or Enterprise mode: automatically active
        return jsonify({
            'mode': 'cloud',
            'is_community': False,
            'is_activated': True,
            'message': 'Aikrofy Cloud / Enterprise Infrastructure - Fully Active'
        })

    if stored:
        return jsonify({
            'mode': 'community',
            'is_community': True,
            'is_activated': True,
            'token': stored['token'][:16] + '...',
            'source': stored.get('source'),
            'payload': stored.get('payload'),
            'message': f"Instancia Community Oficial Activada para {stored.get('payload', {}).get('org', 'Organización')}"
        })

    return jsonify({
        'mode': 'community',
        'is_community': True,
        'is_activated': False,
        'message': 'Esta instancia de Aikrofy Community requiere un Token de Activación Oficial para operar.',
        'activation_url': 'https://aikrofy.com/community'
    }), 200


@community_bp.route('/activate', methods=['POST'])
def activate_instance():
    """
    Accepts an activation token entered by the user in the self-hosted interface,
    validates its cryptographic signature and persists it locally.
    """
    data = request.get_json() or {}
    token = (data.get('token') or '').strip()

    if not token:
        return jsonify({'error': 'Debes ingresar un Token de Activación válido'}), 400

    ok, msg, payload = CommunityLicenseService.verify_token(token)
    if not ok:
        return jsonify({'error': msg, 'is_activated': False}), 400

    saved = CommunityLicenseService.store_activation(token, payload or {})
    if not saved:
        return jsonify({'error': 'Error guardando el token de activación en el servidor'}), 500

    return jsonify({
        'success': True,
        'is_activated': True,
        'message': f"¡Instancia activada con éxito para {payload.get('org', payload.get('email'))}!",
        'payload': payload
    }), 200


@community_bp.route('/generate-token', methods=['POST'])
def generate_token():
    """
    [CLOUD ENDPOINT] Receives registration data from a user wanting to self-host,
    creates/registers the community lead, and returns a signed activation token.
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    organization = (data.get('organization') or data.get('company_name') or name).strip()
    country = (data.get('country') or '').strip()

    if not email or '@' not in email:
        return jsonify({'error': 'Correo electrónico inválido o requerido'}), 400
    if not name:
        return jsonify({'error': 'Nombre o contacto es requerido'}), 400

    # Generate cryptographic token
    res = CommunityLicenseService.generate_token(
        email=email,
        name=name,
        organization=organization,
        country=country,
        edition='community'
    )

    # In Cloud, record lead in BetaLead or CommunityRegistry if available
    try:
        from extensions import db
        from models.beta_lead import BetaLead
        lead = BetaLead.query.filter_by(email=email).first()
        if not lead:
            lead = BetaLead(
                contact_name=name,
                role_in_company='Self-Hosted Community Admin',
                email=email,
                phone=data.get('phone') or 'N/A',
                company_name=organization or f"{name} Community",
                industry=data.get('industry') or 'Open-Source Self-Hosted',
                employee_count='1-5',
                products_services=f"Self-Hosted Node | Token: {res['token'][:16]}...",
                ai_expectations='Self-hosted community installation',
                additional_notes=f"Activation token issued for {country}"
            )
            db.session.add(lead)
            db.session.commit()
    except Exception:
        pass

    return jsonify({
        'success': True,
        'token': res['token'],
        'expires_at': res['expires_at'],
        'organization': organization,
        'message': 'Token de Activación Oficial generado exitosamente por Fundación Underlife & Aikrofy.'
    }), 201


@community_bp.route('/verify-token', methods=['POST'])
def verify_token_remote():
    """
    [CLOUD ENDPOINT] Remote verification endpoint invoked by self-hosted nodes
    if they need real-time validation against the official Cloud Gateway.
    """
    data = request.get_json() or {}
    token = (data.get('token') or '').strip()

    ok, msg, payload = CommunityLicenseService.verify_token(token)
    return jsonify({
        'valid': ok,
        'message': msg,
        'payload': payload
    }), (200 if ok else 400)
