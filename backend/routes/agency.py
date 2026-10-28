"""
Agency & Multi-Tenant Management Routes
Enables Agency users to:
1. List all assigned client companies with their status, balance and metrics.
2. Link new companies to the agency portfolio.
3. Switch active company context securely.
4. Manage enterprise billing tiers ($X / mo per company + fuel credits).

Copyright © 2026 WEBLIFETECH. All Rights Reserved.
"""
import logging
import secrets
import uuid
from datetime import datetime
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from extensions import db
from config import get_config
from models.user import User, UserRole
from models.company import Company
from models.agency import AgencyCompanyAccess
from models.subscription import Plan
from services.email_service import EmailService

logger = logging.getLogger(__name__)
agency_bp = APIRouter('agency', __name__)


def get_agency_user():
    """Validates that current user has agency or super_admin permissions."""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None
        if user.role in (UserRole.AGENCY, UserRole.SUPER_ADMIN):
            return user
        # Check if user has any active agency delegations
        if AgencyCompanyAccess.query.filter_by(agency_user_id=user.id, is_active=True).first():
            return user
        return None
    except Exception as e:
        logger.error(f"Error checking agency user: {e}")
        return None


@agency_bp.route('/companies', methods=['GET'])
@jwt_required()
def list_agency_companies():
    """Returns all companies managed by this agency account."""
    user = get_agency_user()
    if not user:
        return jsonify({'error': 'No tienes permisos de cuenta Agencia'}), 403

    # If super admin, can optionally list all or their delegated ones
    if user.role == UserRole.SUPER_ADMIN and request.args.get('all') == 'true':
        companies = Company.query.order_by(Company.name.asc()).all()
        return jsonify({
            'companies': [c.to_dict() for c in companies],
            'total': len(companies),
            'is_super_admin': True
        })

    accesses = AgencyCompanyAccess.query.filter_by(agency_user_id=user.id, is_active=True).all()
    
    result = []
    for acc in accesses:
        result.append(acc.to_dict())

    # Include own company as home workspace if available
    home_company = user.company
    
    return jsonify({
        'companies': result,
        'home_company': home_company.to_dict() if home_company else None,
        'total': len(result)
    })


@agency_bp.route('/companies', methods=['POST'])
@jwt_required()
def add_company_to_agency():
    """Provisions a new client company under the agency's portfolio using platform standard quotas."""
    user = get_agency_user()
    if not user:
        return jsonify({'error': 'Permiso denegado'}), 403

    data = request.get_json() or {}
    company_name = data.get('name')
    if not company_name:
        return jsonify({'error': 'El nombre de la empresa es obligatorio'}), 400

    try:
        # ── Quota Enforcement ──────────────────────────────────────────────
        # Validate that the agency has not exceeded its allocated company quota.
        # Quota is set by Super Admin on the agency company record.
        agency_company = user.company
        if agency_company:
            max_companies = getattr(agency_company, 'agency_max_companies', 0)
            if max_companies > 0:  # 0 = unlimited (no quota set), -1 also means unlimited
                current_count = AgencyCompanyAccess.query.filter_by(
                    agency_user_id=user.id,
                    is_active=True
                ).count()
                if current_count >= max_companies:
                    return jsonify({
                        'error': f'Has alcanzado el límite de {max_companies} empresas de tu plan de agencia. '
                                 f'Contacta a soporte para ampliar tu cupo.',
                        'quota_exceeded': True,
                        'current_count': current_count,
                        'max_companies': max_companies
                    }), 403

        # Get platform default plan or starter plan for standard quotas
        default_plan = Plan.query.filter_by(is_default=True).first() or Plan.query.first()
        plan_features = (default_plan.features or {}) if default_plan else {}
        standard_credits = plan_features.get('monthly_credits', 1000)
        standard_price = default_plan.price_monthly if default_plan else 29.99

        # Create brand new isolated tenant company
        new_comp = Company(
            name=company_name,
            email=data.get('email'),
            phone=data.get('phone'),
            industry=data.get('industry', 'Servicios'),
            credit_balance=standard_credits,
            language=data.get('language', 'es')
        )
        db.session.add(new_comp)
        db.session.flush()

        # Link to agency with platform standard terms
        access = AgencyCompanyAccess(
            agency_user_id=user.id,
            company_id=new_comp.id,
            role_in_client=data.get('role_in_client', 'admin'),
            monthly_fee=standard_price,
            monthly_credits=standard_credits,
            is_active=True,
            status='active'
        )
        db.session.add(access)
        db.session.commit()

        return jsonify({
            'success': True,
            'company': new_comp.to_dict(),
            'access': access.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating agency company: {e}")
        return jsonify({'error': f'Error creando empresa cliente: {str(e)}'}), 500



@agency_bp.route('/invite-company', methods=['POST'])
@jwt_required()
def invite_company():
    """
    Allows an Agency to invite an existing registered company in Aikrofy.
    Generates a secure authorization token and sends an email to the company owner.
    """
    user = get_agency_user()
    if not user:
        return jsonify({'error': 'No tienes permisos de cuenta Agencia'}), 403

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'El correo electrónico de la empresa es obligatorio'}), 400

    # Search for target company by email or primary user email
    target_user = User.query.filter_by(email=email).first()
    target_company = None
    if target_user and target_user.company_id:
        target_company = Company.query.get(target_user.company_id)
    if not target_company:
        target_company = Company.query.filter_by(email=email).first()

    if not target_company:
        return jsonify({'error': f'No existe ninguna empresa registrada con el correo: {email}'}), 404

    if user.company_id == target_company.id:
        return jsonify({'error': 'No puedes invitar a tu propia empresa principal'}), 400

    # Check if already active or pending
    existing = AgencyCompanyAccess.query.filter_by(
        agency_user_id=user.id,
        company_id=target_company.id
    ).first()

    if existing and existing.is_active:
        return jsonify({'error': f'La empresa "{target_company.name}" ya se encuentra vinculada y activa'}), 400

    # Generate secure invite token
    token = f"agy_{secrets.token_urlsafe(32)}"
    
    default_plan = Plan.query.filter_by(is_default=True).first() or Plan.query.first()
    standard_price = default_plan.price_monthly if default_plan else 29.99
    standard_credits = (default_plan.features or {}).get('monthly_credits', 1000) if default_plan else 1000

    if not existing:
        existing = AgencyCompanyAccess(
            agency_user_id=user.id,
            company_id=target_company.id,
            role_in_client='admin',
            monthly_fee=standard_price,
            monthly_credits=standard_credits,
            is_active=False,
            status='pending_approval',
            invite_token=token
        )
        db.session.add(existing)
    else:
        existing.status = 'pending_approval'
        existing.invite_token = token
        existing.is_active = False

    db.session.commit()

    # Agency display name
    agency_name = user.company.name if user.company else user.name

    # Build authorization URL
    cfg = get_config()
    frontend_url = getattr(cfg, 'FRONTEND_URL', 'https://app.aikrofy.com').rstrip('/')
    auth_url = f"{frontend_url}/agency/authorize?token={token}"

    # Prepare email notification
    target_email = target_user.email if target_user else target_company.email
    subject = f"Solicitud de Vinculación de Agencia: {agency_name} desea administrar tu cuenta en Aikrofy"
    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; color: #1e293b;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #7c3aed; font-size: 26px; margin: 0; font-weight: 800;">Aikrofy</h1>
            <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Plataforma de Inteligencia Artificial & Multi-tenant</p>
        </div>
        
        <h2 style="font-size: 18px; color: #0f172a; margin-bottom: 12px;">Solicitud de Administración de Agencia</h2>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">
            Hola <strong>{target_company.name}</strong>,
        </p>
        <p style="font-size: 14px; line-height: 1.6; color: #334155;">
            La agencia <strong>{agency_name}</strong> ({user.email}) ha solicitado vincular tu cuenta para gestionar y optimizar tus agentes, flujos y canales en Aikrofy.
        </p>
        
        <div style="background-color: #f8fafc; border-left: 4px solid #7c3aed; padding: 14px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-size: 13px; color: #475569;">
                <strong>Importante:</strong> Tus datos permanecen 100% aislados e independientes. Si en el futuro decides desvincularte de la agencia, mantendrás intactos todos tus agentes, base de conocimientos y configuraciones.
            </p>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{auth_url}" style="background-color: #7c3aed; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);">
                Aprobar o Revisar Vinculación
            </a>
        </div>

        <p style="font-size: 12px; color: #94a3b8; text-align: center; line-height: 1.5;">
            Si el botón anterior no funciona, copia y pega el siguiente enlace en tu navegador:<br/>
            <a href="{auth_url}" style="color: #7c3aed; word-break: break-all;">{auth_url}</a>
        </p>

        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;" />
        <p style="font-size: 11px; color: #94a3b8; text-align: center;">
            Si no reconoces esta solicitud o no perteneces a esta organización, puedes ignorar este correo de forma segura.
        </p>
    </div>
    """

    email_sent = False
    try:
        mailer = EmailService(company=user.company)
        res = mailer.send_email(
            company_id=user.company_id,
            to_email=target_email,
            subject=subject,
            body=body_html
        )
        email_sent = bool(res and res.get('success'))
    except Exception as e:
        logger.error(f"Error sending agency invitation email: {e}")

    return jsonify({
        'success': True,
        'message': f'Solicitud de vinculación enviada a {target_email}',
        'email_sent': email_sent,
        'auth_url': auth_url,
        'company': target_company.to_dict()
    }), 200


@agency_bp.route('/invitation-details', methods=['GET'])
def get_invitation_details():
    """Public endpoint to verify invitation token and return agency and company details."""
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token de invitación no proporcionado'}), 400

    access = AgencyCompanyAccess.query.filter_by(invite_token=token).first()
    if not access:
        return jsonify({'error': 'Enlace de invitación inválido o ya utilizado'}), 404

    agency_user = access.agency_user
    agency_company = agency_user.company if agency_user else None
    client_company = access.company

    return jsonify({
        'success': True,
        'status': access.status,
        'is_active': access.is_active,
        'agency': {
            'name': agency_company.name if agency_company else (agency_user.name if agency_user else 'Agencia'),
            'email': agency_user.email if agency_user else '',
        },
        'company': {
            'id': client_company.id if client_company else None,
            'name': client_company.name if client_company else '',
            'email': client_company.email if client_company else '',
        }
    }), 200


@agency_bp.route('/respond-invitation', methods=['POST'])
def respond_invitation():
    """Public endpoint allowing the company owner to accept or reject agency delegation."""
    data = request.get_json() or {}
    token = data.get('token')
    action = data.get('action') # 'accept' or 'reject'

    if not token or action not in ('accept', 'reject'):
        return jsonify({'error': 'Token y acción válidos son requeridos'}), 400

    access = AgencyCompanyAccess.query.filter_by(invite_token=token).first()
    if not access:
        return jsonify({'error': 'Enlace de invitación inválido o expirado'}), 404

    if action == 'accept':
        access.is_active = True
        access.status = 'active'
        access.invite_token = None
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '¡Vinculación autorizada con éxito! La agencia ahora puede gestionar tu espacio sin comprometer tu independencia.'
        }), 200
    else:
        access.is_active = False
        access.status = 'rejected'
        access.invite_token = None
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Has rechazado la solicitud de vinculación de la agencia.'
        }), 200


@agency_bp.route('/companies/<int:company_id>/unlink', methods=['POST'])
@jwt_required()
def unlink_agency_company(company_id):
    """Unlinks a company from an agency while preserving all company data completely intact."""
    user = get_agency_user()
    if not user:
        return jsonify({'error': 'Permiso denegado'}), 403

    access = AgencyCompanyAccess.query.filter_by(
        agency_user_id=user.id,
        company_id=company_id
    ).first()

    if not access:
        # Check if user is the company owner des-linking the agency
        current_user_id = int(get_jwt_identity())
        current_user = User.query.get(current_user_id)
        if current_user and current_user.company_id == company_id:
            access = AgencyCompanyAccess.query.filter_by(company_id=company_id, is_active=True).first()

    if not access:
        return jsonify({'error': 'Relación de agencia no encontrada'}), 404

    access.is_active = False
    access.status = 'unlinked'
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Empresa desvinculada exitosamente. La cuenta y sus datos se mantienen intactos.'
    }), 200


@agency_bp.route('/companies/<int:company_id>/switch', methods=['POST'])
@jwt_required()
def switch_company_context(company_id):
    """
    Validates agency access to target company and returns target workspace context.
    The frontend stores this active context for row-level scoped API operations.
    """
    user = get_agency_user()
    if not user:
        return jsonify({'error': 'Permiso denegado'}), 403

    # Check permission
    if user.role != UserRole.SUPER_ADMIN:
        access = AgencyCompanyAccess.query.filter_by(
            agency_user_id=user.id,
            company_id=company_id,
            is_active=True
        ).first()
        if not access and user.company_id != company_id:
            return jsonify({'error': 'No tienes acceso a esta empresa'}), 403

    target_company = Company.query.get(company_id)
    if not target_company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    return jsonify({
        'success': True,
        'active_company': target_company.to_dict(),
        'message': f'Cambiado al espacio de trabajo: {target_company.name}'
    })


@agency_bp.route('/companies/<int:company_id>/credits', methods=['POST'])
@jwt_required()
def add_credits_to_client(company_id):
    """Allocates or purchases additional fuel credits for a specific client company."""
    user = get_agency_user()
    if not user:
        return jsonify({'error': 'Permiso denegado'}), 403

    data = request.get_json() or {}
    credits_to_add = int(data.get('credits', 0))
    if credits_to_add <= 0:
        return jsonify({'error': 'Cantidad de créditos inválida'}), 400

    target_company = Company.query.get(company_id)
    if not target_company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    target_company.credit_balance = (target_company.credit_balance or 0) + credits_to_add
    db.session.commit()

    return jsonify({
        'success': True,
        'company_id': target_company.id,
        'new_credit_balance': target_company.credit_balance
    })
