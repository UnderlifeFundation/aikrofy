"""
Beta Management Routes
"""
import logging
import secrets
import string
from datetime import datetime, timedelta
from routing import APIRouter, jsonify, request, jwt_required
from extensions import db
from decorators import super_admin_required
from models.platform_config import PlatformConfig
from models.beta_lead import BetaLead, BetaLeadStatus
from models.user import User, UserRole
from models.company import Company
from models.subscription import Subscription, SubscriptionStatus, Plan, PlanInterval
from services.email_service import EmailService

logger = logging.getLogger(__name__)

beta_bp = APIRouter('beta', __name__)

@beta_bp.before_request
def before_request():
    db.session.rollback()

@beta_bp.route('/status', methods=['GET'])
def get_beta_status():
    """Public endpoint to check if beta mode is active."""
    try:
        config = PlatformConfig.get_config()
        return jsonify({
            'beta_mode': config.beta_mode
        }), 200
    except Exception as e:
        logger.error(f"Error checking beta status: {e}")
        return jsonify({'beta_mode': False}), 200

@beta_bp.route('/register', methods=['POST'])
def submit_beta_lead():
    """Public endpoint for prospects submitting the dynamic onboarding waitlist form."""
    try:
        data = request.get_json() or {}
        
        # Strictly required contact info
        required_contact = ['contact_name', 'email', 'phone', 'company_name']
        for field in required_contact:
            if not data.get(field) or not str(data.get(field)).strip():
                return jsonify({'error': f'El campo {field} es requerido'}), 400

        email = data['email'].strip().lower()
        role_in_company = str(data.get('role_in_company') or 'Prospecto').strip()
        industry = str(data.get('industry') or 'other').strip()
        employee_count = str(data.get('employee_count') or '1-5').strip()
        
        # Check if already applied or user exists
        existing_lead = BetaLead.query.filter_by(email=email).first()
        if existing_lead:
            return jsonify({
                'message': 'Ya estás registrado en la lista de espera de la versión beta. Te notificaremos pronto.',
                'lead': existing_lead.to_dict()
            }), 200
            
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'message': 'Tu correo ya se encuentra registrado en nuestra plataforma. Puedes iniciar sesión normalmente.',
                'registered_user': True
            }), 200

        # Capture and geolocate submission IP
        submission_ip = "127.0.0.1"
        ip_geo = {}
        try:
            from services.ip_security_service import IpSecurityService
            submission_ip = IpSecurityService.extract_client_ip(request)
            ip_geo = IpSecurityService.resolve_ip_geolocation(submission_ip)
        except Exception as e:
            logger.warning(f"Error resolving beta submission IP geo: {e}")

        lead = BetaLead(
            contact_name=data['contact_name'].strip(),
            role_in_company=role_in_company,
            email=email,
            phone=data['phone'].strip(),
            company_name=data['company_name'].strip(),
            industry=industry,
            employee_count=employee_count,
            products_services=data.get('products_services', ''),
            ai_experience=data.get('ai_experience', ''),
            ai_results_satisfaction=data.get('ai_results_satisfaction', ''),
            ai_expectations=data.get('ai_expectations', ''),
            additional_notes=data.get('additional_notes', ''),
            submission_ip=submission_ip,
            ip_lat=ip_geo.get('lat'),
            ip_lng=ip_geo.get('lng'),
            ip_city=ip_geo.get('city'),
            ip_country=ip_geo.get('country')
        )

        db.session.add(lead)
        db.session.commit()

        # Auto-sync prospect to Company 1 (Aikrofy AI Platform) Contacts / CRM
        try:
            from models.customer import Customer
            name_parts = lead.contact_name.split(' ', 1)
            first_n = name_parts[0]
            last_n = name_parts[1] if len(name_parts) > 1 else ''
            
            customer = Customer.query.filter_by(company_id=1, email=lead.email).first()
            if not customer:
                customer = Customer(
                    company_id=1,
                    first_name=first_n,
                    last_name=last_n,
                    email=lead.email,
                    phone=lead.phone,
                    work_company=lead.company_name,
                    buying_role=lead.role_in_company or 'Prospecto Beta',
                    customer_metadata={
                        'source': 'beta_registration',
                        'industry': lead.industry,
                        'employee_count': lead.employee_count,
                        'ai_expectations': lead.ai_expectations,
                        'ai_experience': lead.ai_experience,
                        'beta_status': lead.status
                    }
                )
                db.session.add(customer)
                db.session.commit()
        except Exception as sync_err:
            logger.warning(f"Could not auto-sync beta lead to customer: {sync_err}")

        # Send confirmation email on registration asynchronously so response is instant (<100ms)
        def _send_waitlist_email(lead_dict, target_email):
            try:
                from services.krof_agent_service import KrofAgentService
                from services.email_service import EmailService
                from models.platform_config import PlatformConfig

                krof_email = KrofAgentService.generate_waitlist_confirmation_email(lead_dict)
                email_service = EmailService()
                config_obj = PlatformConfig.get_config()
                comp_id = config_obj.platform_company_id or 1

                email_service.send_email(
                    company_id=comp_id,
                    to_email=target_email,
                    subject=krof_email['subject'],
                    body=krof_email['html_body']
                )
            except Exception as mail_err:
                logger.warning(f"Could not send registration confirmation email: {mail_err}")

        import threading
        threading.Thread(target=_send_waitlist_email, args=(lead.to_dict(), lead.email), daemon=True).start()

        return jsonify({
            'message': 'Registro completado con éxito. Has sido añadido a la lista de espera.',
            'lead': lead.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering beta lead: {e}")
        return jsonify({'error': str(e)}), 500


@beta_bp.route('/leads', methods=['GET'])
@jwt_required()
@super_admin_required
def list_beta_leads():
    """Super admin endpoint to list all beta leads."""
    try:
        leads = BetaLead.query.order_by(BetaLead.created_at.desc()).all()
        return jsonify({
            'data': [l.to_dict() for l in leads]
        }), 200
    except Exception as e:
        logger.error(f"Error listing beta leads: {e}")
        return jsonify({'error': str(e)}), 500


@beta_bp.route('/leads/<int:lead_id>/approve', methods=['POST'])
@jwt_required()
@super_admin_required
def approve_beta_lead(lead_id):
    """
    Super admin approves a beta lead:
    1. Generates provisional password
    2. Creates Company & User with is_beta_approved=True
    3. Sets courtesy subscription / initial credits
    4. Marks lead as APPROVED
    5. Attempts to send welcome email with provisional credentials
    """
    try:
        lead = BetaLead.query.get_or_404(lead_id)
        if lead.status == BetaLeadStatus.APPROVED:
            return jsonify({'message': 'Lead ya había sido aprobado previamente', 'lead': lead.to_dict()}), 200

        data = request.get_json() or {}
        credits_to_grant = int(data.get('credits', 1500))

        # Check existing user
        user = User.query.filter_by(email=lead.email).first()
        company = None
        
        # Generate 10-char provisional password
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(10))

        if not user:
            # Determine business category from employee_count in BetaLead
            emp_str = (lead.employee_count or '').lower()
            if any(x in emp_str for x in ['50', '100', '200', '500', '+']):
                lead_cat = 'enterprise'
            elif any(x in emp_str for x in ['11', '20', '25', '30']):
                lead_cat = 'pyme'
            else:
                lead_cat = 'emprendimiento'

            initial_modules = Company.compute_default_modules(
                business_category=lead_cat,
                industry=lead.industry or '',
                extra_context=f"{lead.products_services or ''} {lead.ai_expectations or ''} {lead.additional_notes or ''}",
                plan_type='enterprise' if lead_cat == 'enterprise' else 'pyme'
            )

            # Create company
            company = Company(
                name=lead.company_name,
                industry=lead.industry,
                business_category=lead_cat,
                agent_name="Assistant",
                language="es",
                initial_setup_completed=True,
                credit_balance=credits_to_grant,
                api_keys={'enabled_modules': initial_modules}
            )
            db.session.add(company)
            db.session.flush()

            # Create default agent
            from models.agent import Agent
            Agent.create_default_agent(company.id, db.session)

            # Create user
            user = User(
                email=lead.email,
                name=lead.contact_name,
                role=UserRole.ADMIN,
                company_id=company.id,
                is_active=True,
                is_beta_approved=True,
                is_company_owner=True
            )
            user.set_password(temp_password)
            db.session.add(user)
            db.session.flush()

            # Register as Owner Employee for instant WhatsApp & internal Copilot recognition
            from models.employee import Employee, EmployeeRole
            owner_employee = Employee(
                company_id=company.id,
                name=lead.contact_name,
                email=lead.email,
                phone=lead.phone,
                whatsapp=lead.phone,
                role=EmployeeRole.OWNER,
                department="Dirección General",
                has_web_access=True,
                is_active=True
            )
            db.session.add(owner_employee)
            db.session.flush()

            # Assign default courtesy subscription
            plan = Plan.query.filter_by(is_default=True).first() or Plan.query.first()
            if plan:
                sub = Subscription(
                    company_id=company.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.COURTESY,
                    interval=PlanInterval.MONTHLY
                )
                db.session.add(sub)
        else:
            user.is_beta_approved = True
            if user.company:
                company = user.company
                company.credit_balance = (company.credit_balance or 0) + credits_to_grant

        # Update lead status
        lead.status = BetaLeadStatus.APPROVED
        lead.approved_at = datetime.utcnow()
        lead.created_user_id = user.id if user else None
        lead.created_company_id = company.id if company else None
        lead.credits_granted = credits_to_grant

        db.session.commit()

        # Try to send notification email using Krof AI Engine
        email_sent = False
        try:
            import jwt
            import urllib.parse
            from services.krof_agent_service import KrofAgentService
            from models.channel import Channel, ChannelType
            from config import get_config
            cfg = get_config()

            secret_key = cfg.JWT_SECRET_KEY or cfg.SECRET_KEY or 'd15306490de06401ca61722312ba884e95b5aa11d1946d27ec97cab3349c229e'
            token_payload = {
                'user_id': user.id,
                'company_id': company.id,
                'email': user.email,
                'redirect_path': '/onboarding',
                'exp': datetime.utcnow() + timedelta(days=7)
            }
            magic_token = jwt.encode(token_payload, secret_key, algorithm='HS256')
            frontend_url = (getattr(cfg, 'FRONTEND_URL', 'https://app.aikrofy.com') or 'https://app.aikrofy.com').rstrip('/')
            magic_login_url = f"{frontend_url}/login?token={magic_token}"

            # Check Platform WhatsApp number from channel
            wa_number = "593988888888"
            wa_channel = Channel.query.filter_by(type=ChannelType.WHATSAPP).first()
            if wa_channel and wa_channel.phone_number:
                wa_number = ''.join(c for c in wa_channel.phone_number if c.isdigit())
            
            clean_company_name = company.name if company else lead.company_name
            wa_prefill = f"Hola Krof, soy {lead.contact_name} de {clean_company_name}. Acabo de recibir mi acceso al Beta de Aikrofy para configurar mi empresa."
            encoded_text = urllib.parse.quote(wa_prefill)
            whatsapp_onboarding_url = f"https://wa.me/{wa_number}?text={encoded_text}"

            krof_email = KrofAgentService.generate_beta_approval_email(
                lead_data=lead.to_dict(),
                temp_password=temp_password,
                credits=credits_to_grant,
                magic_login_url=magic_login_url,
                whatsapp_onboarding_url=whatsapp_onboarding_url
            )

            config = PlatformConfig.get_config()
            comp_id = config.platform_company_id or 1
            email_service = EmailService()

            res = email_service.send_email(
                company_id=comp_id,
                to_email=lead.email,
                subject=krof_email['subject'],
                body=krof_email['html_body']
            )
            email_sent = res.get('success', False)
        except Exception as mail_err:
            logger.warning(f"Could not send approval email: {mail_err}")

        return jsonify({
            'message': 'Lead de Beta aprobado exitosamente',
            'lead': lead.to_dict(),
            'temp_password': temp_password,
            'email_sent': email_sent
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving beta lead: {e}")
        return jsonify({'error': str(e)}), 500


@beta_bp.route('/leads/<int:lead_id>/reject', methods=['POST'])
@jwt_required()
@super_admin_required
def reject_beta_lead(lead_id):
    """Super admin rejects a beta lead."""
    try:
        lead = BetaLead.query.get_or_404(lead_id)
        lead.status = BetaLeadStatus.REJECTED
        db.session.commit()
        return jsonify({'message': 'Lead rechazado', 'lead': lead.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@beta_bp.route('/leads/<int:lead_id>/reactivate', methods=['POST'])
@jwt_required()
@super_admin_required
def reactivate_beta_lead(lead_id):
    """Super admin reactivates a rejected beta lead back to pending status."""
    try:
        lead = BetaLead.query.get_or_404(lead_id)
        lead.status = BetaLeadStatus.PENDING
        db.session.commit()
        return jsonify({'message': 'Lead reactivado a pendiente', 'lead': lead.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@beta_bp.route('/leads/<int:lead_id>', methods=['DELETE'])
@jwt_required()
@super_admin_required
def delete_beta_lead(lead_id):
    """Super admin permanently deletes a beta lead."""
    try:
        lead = BetaLead.query.get_or_404(lead_id)
        db.session.delete(lead)
        db.session.commit()
        return jsonify({'message': 'Lead eliminado permanentemente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

