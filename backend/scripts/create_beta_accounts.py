"""
Script to create Grupra beta account with 1000 trial credits,
provision owner and 2 delegated admin accounts, and send all confirmation/credentials emails.
"""
import sys
import os
import secrets
import string
import time
import urllib.parse
from datetime import datetime, timedelta
import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from extensions import db
from models.user import User, UserRole
from models.company import Company
from models.agent import Agent
from models.employee import Employee, EmployeeRole
from models.beta_lead import BetaLead, BetaLeadStatus
from models.subscription import Subscription, SubscriptionStatus, Plan, PlanInterval
from models.platform_config import PlatformConfig
from models.channel import Channel, ChannelType
from services.email_service import EmailService
from services.krof_agent_service import KrofAgentService

def main():
    cfg = get_config()
    print("=" * 70)
    print("🚀 Aikrofy — Creación de Cuenta Beta y Administradores Delegados")
    print("=" * 70)

    email_service = EmailService()
    platform_cfg = PlatformConfig.get_config()
    comp_id = platform_cfg.platform_company_id or 1

    # -------------------------------------------------------------------------
    # 1. Registro de Lead Beta para Mauricio Ramírez (mramirezl@grupra.com)
    # -------------------------------------------------------------------------
    owner_email = "mramirezl@grupra.com"
    owner_name = "Mauricio Ramírez"
    company_name = "Grupra"
    owner_temp_password = "Grupra#" + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)) + "!"

    print(f"\n[1/3] Registrando Lead Beta para {owner_name} ({owner_email})...")
    lead = BetaLead.query.filter_by(email=owner_email).first()
    if not lead:
        lead = BetaLead(
            email=owner_email,
            contact_name=owner_name,
            company_name=company_name,
            role_in_company="Propietario / Director General",
            phone="+593900000000",
            industry="Servicios Corporativos",
            employee_count="11-50",
            ai_experience="intermedio",
            ai_results_satisfaction="alta",
            ai_expectations="Automatizar atención comercial, operaciones y agendamiento inteligente con agentes IA.",
            status=BetaLeadStatus.PENDING
        )
        db.session.add(lead)
        db.session.commit()
        print(f"  ✓ Lead creado exitosamente con ID {lead.id}")
    else:
        print(f"  ✓ Lead ya existía con ID {lead.id}")

    # Enviar correo 1: Confirmación de registro a lista de espera
    print(f"  ✉️ Enviando correo de bienvenida a lista de espera a {owner_email}...")
    try:
        krof_waitlist_email = KrofAgentService.generate_waitlist_confirmation_email(lead.to_dict())
        res_waitlist = email_service.send_email(
            company_id=comp_id,
            to_email=owner_email,
            subject=krof_waitlist_email['subject'],
            body=krof_waitlist_email['html_body']
        )
        if res_waitlist.get('success'):
            lead.waitlist_email_sent_at = datetime.utcnow()
            db.session.commit()
            print(f"  ✅ Correo de Lista de Espera enviado con éxito a {owner_email}")
        else:
            print(f"  ⚠️ No se pudo enviar correo de lista de espera: {res_waitlist.get('message')}")
    except Exception as e:
        print(f"  ⚠️ Error enviando correo de lista de espera: {e}")

    time.sleep(1)

    # -------------------------------------------------------------------------
    # 2. Aprobación del Beta y Creación de Empresa / Cuenta Propietario (1000 créditos)
    # -------------------------------------------------------------------------
    print(f"\n[2/3] Aprobando Beta y aprovisionando Empresa '{company_name}' con 1000 créditos...")
    
    # Crear o buscar Company
    company = Company.query.filter_by(name=company_name).first()
    if not company:
        company = Company(
            name=company_name,
            industry="Servicios Corporativos",
            agent_name="Krof",
            language="es",
            credit_balance=1000,
            trial_activated=True,
            is_active=True,
            subscription_tier="courtesy",
            plan_type="pyme",
            max_departments=5,
            max_employees=20
        )
        db.session.add(company)
        db.session.flush()
        print(f"  ✓ Empresa '{company_name}' creada con ID {company.id} y 1000 créditos.")

        # Crear agente por defecto
        Agent.create_default_agent(company.id, db.session)
        print(f"  ✓ Agente por defecto creado para la empresa.")

        # Asignar suscripción cortesía
        plan = Plan.query.filter_by(is_default=True).first() or Plan.query.first()
        if plan:
            sub = Subscription(
                company_id=company.id,
                plan_id=plan.id,
                status=SubscriptionStatus.COURTESY,
                interval=PlanInterval.MONTHLY
            )
            db.session.add(sub)
            print(f"  ✓ Suscripción de cortesía asignada.")
    else:
        company.credit_balance = 1000
        company.trial_activated = True
        company.is_active = True
        print(f"  ✓ Empresa '{company_name}' ya existía (ID {company.id}). Saldo ajustado a 1000 créditos.")

    # Crear o buscar Usuario Propietario
    owner_user = User.query.filter_by(email=owner_email).first()
    if not owner_user:
        owner_user = User(
            email=owner_email,
            name=owner_name,
            role=UserRole.ADMIN,
            company_id=company.id,
            is_active=True,
            is_company_owner=True,
            is_beta_approved=True
        )
        owner_user.set_password(owner_temp_password)
        db.session.add(owner_user)
        db.session.flush()
        print(f"  ✓ Usuario Propietario '{owner_email}' creado con ID {owner_user.id} (is_company_owner=True).")
    else:
        owner_user.company_id = company.id
        owner_user.is_company_owner = True
        owner_user.is_beta_approved = True
        owner_user.set_password(owner_temp_password)
        print(f"  ✓ Usuario Propietario '{owner_email}' actualizado (ID {owner_user.id}).")

    # Empleado Propietario
    owner_emp = Employee.query.filter_by(company_id=company.id, email=owner_email).first()
    if not owner_emp:
        owner_emp = Employee(
            company_id=company.id,
            user_id=owner_user.id,
            name=owner_name,
            email=owner_email,
            phone="+593900000000",
            whatsapp="+593900000000",
            role=EmployeeRole.OWNER,
            department="Dirección General",
            has_web_access=True,
            is_active=True
        )
        db.session.add(owner_emp)
    else:
        owner_emp.user_id = owner_user.id
        owner_emp.role = EmployeeRole.OWNER
        owner_emp.has_web_access = True

    # Actualizar Lead
    lead.status = BetaLeadStatus.APPROVED
    lead.approved_at = datetime.utcnow()
    lead.created_user_id = owner_user.id
    lead.created_company_id = company.id
    lead.credits_granted = 1000

    db.session.commit()

    # Generar Magic Link y WhatsApp link para el Owner
    secret_key = cfg.JWT_SECRET_KEY or cfg.SECRET_KEY or 'd15306490de06401ca61722312ba884e95b5aa11d1946d27ec97cab3349c229e'
    token_payload = {
        'user_id': owner_user.id,
        'company_id': company.id,
        'email': owner_user.email,
        'redirect_path': '/onboarding',
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    magic_token = jwt.encode(token_payload, secret_key, algorithm='HS256')
    frontend_url = (getattr(cfg, 'FRONTEND_URL', 'https://app.aikrofy.com') or 'https://app.aikrofy.com').rstrip('/')
    magic_login_url = f"{frontend_url}/login?token={magic_token}"

    wa_number = "593988888888"
    wa_channel = Channel.query.filter_by(type=ChannelType.WHATSAPP).first()
    if wa_channel and wa_channel.phone_number:
        wa_number = ''.join(c for c in wa_channel.phone_number if c.isdigit())
    
    wa_prefill = f"Hola Krof, soy {owner_name} de {company_name}. Acabo de recibir mi acceso al Beta de Aikrofy para configurar mi empresa."
    whatsapp_onboarding_url = f"https://wa.me/{wa_number}?text={urllib.parse.quote(wa_prefill)}"

    # Enviar correo 2: Credenciales de Acceso Aprobado con 1000 créditos
    print(f"  ✉️ Enviando correo de credenciales de Acceso Beta Aprobado a {owner_email}...")
    try:
        krof_approval_email = KrofAgentService.generate_beta_approval_email(
            lead_data=lead.to_dict(),
            temp_password=owner_temp_password,
            credits=1000,
            magic_login_url=magic_login_url,
            whatsapp_onboarding_url=whatsapp_onboarding_url
        )
        res_approval = email_service.send_email(
            company_id=comp_id,
            to_email=owner_email,
            subject=krof_approval_email['subject'],
            body=krof_approval_email['html_body']
        )
        if res_approval.get('success'):
            print(f"  ✅ Correo de Acceso Beta Aprobado enviado con éxito a {owner_email}")
        else:
            print(f"  ⚠️ No se pudo enviar correo de aprobación: {res_approval.get('message')}")
    except Exception as e:
        print(f"  ⚠️ Error enviando correo de aprobación: {e}")

    time.sleep(1)

    # -------------------------------------------------------------------------
    # 3. Creación de Cuentas Administradoras Adicionales (cbarreno@nextgen.ec, bherrera@nextgen.ec)
    # -------------------------------------------------------------------------
    print(f"\n[3/3] Registrando Administradores Delegados para {company_name}...")

    admins_to_create = [
        {
            "email": "cbarreno@nextgen.ec",
            "name": "Carlos Barreno",
            "department": "Administración",
            "role": EmployeeRole.ADMIN,
            "temp_password": "NextGen#Barreno" + ''.join(secrets.choice(string.digits) for _ in range(4))
        },
        {
            "email": "bherrera@nextgen.ec",
            "name": "Bryan Herrera",
            "department": "Administración",
            "role": EmployeeRole.ADMIN,
            "temp_password": "NextGen#Herrera" + ''.join(secrets.choice(string.digits) for _ in range(4))
        }
    ]

    admin_results = []

    for adm in admins_to_create:
        adm_email = adm["email"]
        adm_name = adm["name"]
        adm_pass = adm["temp_password"]
        adm_dept = adm["department"]

        print(f"\n  ➤ Procesando Administrador: {adm_name} ({adm_email})...")

        # User
        user_adm = User.query.filter_by(email=adm_email).first()
        if not user_adm:
            user_adm = User(
                email=adm_email,
                name=adm_name,
                role=UserRole.ADMIN,
                company_id=company.id,
                is_active=True,
                is_company_owner=False,  # Administrador delegado, no propietario
                is_beta_approved=True
            )
            user_adm.set_password(adm_pass)
            db.session.add(user_adm)
            db.session.flush()
            print(f"    ✓ Usuario creado ID {user_adm.id} (is_company_owner=False, role=ADMIN).")
        else:
            user_adm.company_id = company.id
            user_adm.role = UserRole.ADMIN
            user_adm.is_company_owner = False
            user_adm.is_beta_approved = True
            user_adm.set_password(adm_pass)
            print(f"    ✓ Usuario existente ID {user_adm.id} actualizado.")

        # Employee
        emp_adm = Employee.query.filter_by(company_id=company.id, email=adm_email).first()
        if not emp_adm:
            emp_adm = Employee(
                company_id=company.id,
                user_id=user_adm.id,
                name=adm_name,
                email=adm_email,
                role=adm["role"],
                department=adm_dept,
                has_web_access=True,
                is_active=True
            )
            db.session.add(emp_adm)
            print(f"    ✓ Ficha de Empleado creada con acceso web activo.")
        else:
            emp_adm.user_id = user_adm.id
            emp_adm.role = adm["role"]
            emp_adm.department = adm_dept
            emp_adm.has_web_access = True
            emp_adm.is_active = True
            print(f"    ✓ Ficha de Empleado existente actualizada con acceso web.")

        db.session.commit()

        # Enviar correo de invitación con credenciales
        print(f"    ✉️ Enviando correo con credenciales de Administrador a {adm_email}...")
        try:
            invitation_email = KrofAgentService.generate_employee_invitation_email(
                company_name=company_name,
                employee_name=adm_name,
                email=adm_email,
                temp_password=adm_pass,
                role_title="Administrador"
            )
            res_invite = email_service.send_email(
                company_id=comp_id,
                to_email=adm_email,
                subject=invitation_email['subject'],
                body=invitation_email['html_body']
            )
            if res_invite.get('success'):
                print(f"    ✅ Correo de invitación enviado con éxito a {adm_email}")
                status_mail = "Enviado exitosamente"
            else:
                print(f"    ⚠️ No se pudo enviar correo: {res_invite.get('message')}")
                status_mail = f"Error: {res_invite.get('message')}"
        except Exception as e:
            print(f"    ⚠️ Error enviando correo: {e}")
            status_mail = f"Excepción: {str(e)}"

        admin_results.append({
            "name": adm_name,
            "email": adm_email,
            "temp_password": adm_pass,
            "email_status": status_mail
        })

    print("\n" + "=" * 70)
    print("✨ RESUMEN DE CUENTAS CREADAS:")
    print("=" * 70)
    print(f"🏢 Empresa: {company_name} (ID: {company.id}) | Créditos de Prueba: {company.credit_balance}")
    print(f"\n👑 PROPIETARIO:")
    print(f"   • Nombre:     {owner_name}")
    print(f"   • Email:      {owner_email}")
    print(f"   • Password:   {owner_temp_password}")
    print(f"   • Rol:        Owner / Administrador Principal (is_company_owner=True)")
    print(f"   • Magic Link: {magic_login_url}")
    print(f"\n👥 ADMINISTRADORES DELEGADOS:")
    for a in admin_results:
        print(f"   • {a['name']} ({a['email']})")
        print(f"     - Password:     {a['temp_password']}")
        print(f"     - Rol:          Administrador (is_company_owner=False, sin onboarding)")
        print(f"     - Estado Email: {a['email_status']}")
    print("=" * 70)

if __name__ == '__main__':
    main()
