from routing import APIRouter, current_app, get_jwt_identity, jsonify, jwt_required, request
"""
Admin Routes - Super Admin endpoints for platform management.
"""
import logging
from datetime import datetime


from extensions import db
from decorators import super_admin_required
from models.platform_config import PlatformConfig
from models.subscription import Plan, Subscription, SubscriptionStatus, PlanInterval
from models.company import Company
from models.user import User, UserRole
from models.conversation import Conversation, Message
# from models.lead import Lead # Lead is not explicitly in models/__init__.py but Customer is
from models.customer import Customer
from models.appointment import Appointment

logger = logging.getLogger(__name__)

admin_bp = APIRouter('admin', __name__)

@admin_bp.route('/platform-agent', methods=['GET'])
@jwt_required()
@super_admin_required
def get_platform_agent():
    """Get the configuration of the platform's support agent."""
    db.session.rollback()
    try:
        config = PlatformConfig.get_config()
        comp_id = config.platform_company_id
        
        if not comp_id:
            return jsonify({'data': None, 'message': 'Platform agent not configured'}), 200
            
        company = Company.query.get(comp_id)
        if not company:
            return jsonify({'error': 'Platform company record not found'}), 404
            
        agent = company.agents.first()
        return jsonify({
            'data': {
                'company': company.to_dict(),
                'agent': agent.to_dict() if agent else None
            }
        }), 200
    except Exception as e:
        logger.error(f"Get platform agent error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/platform-agent', methods=['POST'])
@jwt_required()
@super_admin_required
def setup_platform_agent():
    """Initialize or update the platform's support agent."""
    db.session.rollback()
    try:
        config = PlatformConfig.get_config()
        data = request.get_json()
        
        comp_id = config.platform_company_id
        company = None
        
        if comp_id:
            company = Company.query.get(comp_id)
            
        if not company:
            # Create new platform company
            company = Company(
                name="Pymai Brand",
                email="support@pymai.click",
            )
            db.session.add(company)
            db.session.flush()
            
            config.platform_company_id = company.id
            logger.info(f"Created new platform company with ID {company.id}")
        
        # Update company basic info
        if 'company' in data:
            c_data = data['company']
            if 'name' in c_data: company.name = c_data['name']

        # Update or Create Agent
        from models.agent import Agent, AgentTone, AgentObjective, AgentFeature, DEFAULT_FEATURES
        
        agent = company.agents.first()
        if not agent:
            agent = Agent(
                company_id=company.id,
                name="Pymai Assistant",
                tone=AgentTone.FRIENDLY,
                objective=AgentObjective.SALES
            )
            db.session.add(agent)
            db.session.flush()
            
            # Initialize default features
            for feat_data in DEFAULT_FEATURES:
                feat = AgentFeature(
                    agent_id=agent.id,
                    **feat_data
                )
                db.session.add(feat)
        
        # Update agent info
        if 'agent' in data:
            a_data = data['agent']
            if 'name' in a_data: agent.name = a_data['name']
            if 'tone' in a_data: agent.tone = AgentTone(a_data['tone'])
            if 'objective' in a_data: agent.objective = AgentObjective(a_data['objective'])
            if 'system_prompt' in a_data: agent.system_prompt = a_data['system_prompt']
            
            # Handle features toggle
            if 'features' in a_data:
                for feat_update in a_data['features']:
                    feat = AgentFeature.query.filter_by(agent_id=agent.id, name=feat_update['name']).first()
                    if feat:
                        feat.is_enabled = feat_update.get('is_enabled', feat.is_enabled)

        db.session.commit()
        return jsonify({
            'message': 'Platform agent updated',
            'data': {
                'company': company.to_dict(),
                'agent': agent.to_dict()
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Setup platform agent error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/metrics', methods=['GET'])
@jwt_required()
@super_admin_required
def get_platform_metrics():
    """Get platform-wide metrics for the Super Admin dashboard."""
    db.session.rollback()
    try:
        total_companies = Company.query.count()
        active_subscriptions = Subscription.query.filter(
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIAL,
                SubscriptionStatus.COURTESY
            ])
        ).count()
        
        # In PymAI, Customer is common, Lead might be a status of Customer or separate
        total_customers = Customer.query.count()
        total_conversations = Conversation.query.count()
        total_messages = Message.query.count()
        total_appointments = Appointment.query.count()

        # Monthly Recurring Revenue (MRR) estimate
        active_monthly = db.session.query(
            db.func.sum(Plan.price_monthly)
        ).join(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.interval == PlanInterval.MONTHLY
        ).scalar() or 0.0

        active_annual = db.session.query(
            db.func.sum(Plan.price_annual)
        ).join(Subscription).filter(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.interval == PlanInterval.ANNUAL
        ).scalar() or 0.0

        mrr = active_monthly + (active_annual / 12.0)

        return jsonify({
            'data': {
                'total_companies': total_companies,
                'active_subscriptions': active_subscriptions,
                'total_leads': total_customers, # Fallback if Lead is not separate
                'total_customers': total_customers,
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'total_appointments': total_appointments,
                'mrr': round(mrr, 2),
            }
        }), 200

    except Exception as e:
        logger.error(f"Platform metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/config', methods=['GET', 'PUT'])
@jwt_required()
@super_admin_required
def get_or_update_platform_config():
    """Get or update global platform configuration."""
    db.session.rollback()
    try:
        config = PlatformConfig.get_config()
        
        if request.method == 'PUT':
            data = request.get_json()
            config.enable_failover = data.get('enable_failover', config.enable_failover)
            config.default_llm_provider = data.get('default_llm_provider', config.default_llm_provider)
            config.default_llm_model = data.get('default_llm_model', config.default_llm_model)
            config.global_rag_enabled = data.get('global_rag_enabled', config.global_rag_enabled)
            config.global_rag_namespace = data.get('global_rag_namespace', config.global_rag_namespace)
            config.maintenance_mode = data.get('maintenance_mode', config.maintenance_mode)
            config.beta_mode = data.get('beta_mode', config.beta_mode)
            config.max_agents_per_company = data.get('max_agents_per_company', config.max_agents_per_company)
            config.max_documents_per_company = data.get('max_documents_per_company', config.max_documents_per_company)
            config.platform_company_id = data.get('platform_company_id', config.platform_company_id)
            
            db.session.commit()
            return jsonify({'data': config.to_dict(), 'message': 'Config updated'}), 200
            
        return jsonify({'data': config.to_dict()}), 200
    except Exception as e:
        logger.error(f"Config error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tenants', methods=['GET'])
@jwt_required()
@super_admin_required
def list_tenants():
    """List all companies with their subscription status (excluding system platform tenant)."""
    db.session.rollback()
    try:
        config = PlatformConfig.get_config()
        platform_company_id = config.platform_company_id

        # Exclude internal system tenant (e.g. Aikrofy AI Platform) and system tenant names
        query = Company.query.filter(Company.name != "Aikrofy AI Platform", Company.name != "PymAI AI Platform")
        if platform_company_id:
            query = query.filter(Company.id != platform_company_id)

        tenants = query.order_by(Company.created_at.desc()).all()
        result = []
        for company in tenants:
            d = company.to_dict()
            # Get primary user email and agency status
            primary_user = User.query.filter_by(company_id=company.id).filter(User.role.in_([UserRole.ADMIN, UserRole.AGENCY])).first()
            if not primary_user:
                primary_user = User.query.filter_by(company_id=company.id).first()
            d['user_email'] = primary_user.email if primary_user else company.email
            d['user_name'] = primary_user.name if primary_user else company.name
            d['is_agency'] = (primary_user.role == UserRole.AGENCY) if primary_user else False
            
            # Get active subscription
            sub = Subscription.query.filter_by(company_id=company.id).first()
            d['subscription_active'] = sub.is_active_status if sub else False
            d['is_courtesy'] = sub.status == SubscriptionStatus.COURTESY if sub else False
            d['plan_name'] = sub.plan.name if sub and sub.plan else None
            
            result.append(d)
            
        return jsonify(result), 200 # Frontend expects direct array for now based on reference
    except Exception as e:
        logger.error(f"List tenants error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tenants/<int:id>/agency', methods=['PATCH'])
@jwt_required()
@super_admin_required
def toggle_agency(id):
    """Grant or revoke Agency Mode (Multi-tenant capabilities) for a tenant's users.
    
    Accepts:
        enabled: bool — True to activate agency mode, False to deactivate.
        max_companies: int — Maximum number of client companies the agency can manage.
                            Defaults based on plan: Starter=3, Pro=10, Scale=25, Enterprise=-1.
    """
    db.session.rollback()
    try:
        data = request.get_json() or {}
        enabled = bool(data.get('enabled', False))
        max_companies = data.get('max_companies', None)
        
        company = Company.query.get_or_404(id)
        users = User.query.filter_by(company_id=id).all()
        if not users:
            return jsonify({'error': 'No se encontraron usuarios para esta empresa'}), 404

        # Primary user (owner or admin)
        primary_user = next((u for u in users if u.is_company_owner or u.role in (UserRole.ADMIN, UserRole.AGENCY)), users[0])
        
        if enabled:
            primary_user.role = UserRole.AGENCY
            # Set agency quota: default to 10 (Pro tier) if not specified
            if max_companies is not None:
                company.agency_max_companies = int(max_companies)
            elif company.agency_max_companies == 0:
                company.agency_max_companies = 10  # Default Pro tier quota
        else:
            primary_user.role = UserRole.ADMIN
            company.agency_max_companies = 0  # Reset quota when disabling agency
            
        db.session.commit()
        return jsonify({
            'success': True,
            'company_id': id,
            'is_agency': primary_user.role == UserRole.AGENCY,
            'agency_max_companies': company.agency_max_companies,
            'user_id': primary_user.id,
            'message': f"Modo Agencia {'activado' if enabled else 'desactivado'} con éxito para {company.name}"
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Toggle agency error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/tenants/<int:id>/courtesy', methods=['PATCH'])
@jwt_required()
@super_admin_required
def toggle_courtesy(id):
    """Grant or revoke courtesy/demo membership for a tenant.
    Accepts: { 
        is_courtesy: bool, 
        is_demo: bool, 
        demo_days: int, 
        credit_mode: 'unlimited'|'limited', 
        credit_amount: int 
    }
    """
    db.session.rollback()
    from datetime import timedelta
    try:
        data = request.get_json()
        is_courtesy = data.get('is_courtesy', False)
        is_demo = data.get('is_demo', False)
        demo_days = int(data.get('demo_days', 7))
        credit_mode = data.get('credit_mode', 'unlimited')
        credit_amount = data.get('credit_amount', 100)
        
        company = Company.query.get_or_404(id)
        sub = Subscription.query.filter_by(company_id=id).first()
        
        if not sub:
            # Create a default plan if none exists
            plan = Plan.query.filter_by(is_default=True).first() or Plan.query.first()
            if not plan:
                return jsonify({'error': 'No plans defined. Create a plan first.'}), 400
                
            sub = Subscription(
                company_id=id,
                plan_id=plan.id,
                status=SubscriptionStatus.COURTESY if is_courtesy else (SubscriptionStatus.TRIAL if is_demo else SubscriptionStatus.TRIAL),
                interval=PlanInterval.MONTHLY
            )
            db.session.add(sub)
        else:
            if is_courtesy:
                sub.status = SubscriptionStatus.COURTESY
            elif is_demo:
                sub.status = SubscriptionStatus.TRIAL
            else:
                sub.status = SubscriptionStatus.ACTIVE
        
        # Reset is_demo and demo_expires_at
        company.is_demo = is_demo
        if is_demo:
            company.demo_expires_at = datetime.utcnow() + timedelta(days=demo_days)
            company.credit_balance = int(credit_amount)
        else:
            company.demo_expires_at = None
            
            # Set credit balance based on courtesy mode or reset to plan
            if is_courtesy:
                if credit_mode == 'unlimited':
                    company.credit_balance = -1  # -1 = unlimited credits
                else:
                    company.credit_balance = int(credit_amount) if credit_amount else 100
            else:
                # Reset to plan base credits
                plan_features = sub.plan.features if sub.plan else {}
                company.credit_balance = plan_features.get('monthly_credits', 0) if plan_features else 0
            
        db.session.commit()
        return jsonify({
            'message': 'Tenant membership updated',
            'credit_balance': company.credit_balance,
            'is_demo': company.is_demo,
            'demo_expires_at': company.demo_expires_at.isoformat() if company.demo_expires_at else None
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/tenants/<int:id>', methods=['DELETE'])
@jwt_required()
@super_admin_required
def delete_tenant(id):
    """Permanently delete a tenant and all its data."""
    db.session.rollback()
    try:
        company = Company.query.get_or_404(id)

        # Protect system platform company from deletion
        config = PlatformConfig.get_config()
        if config.platform_company_id == id or company.name in ["Aikrofy AI Platform", "PymAI AI Platform"]:
            return jsonify({'error': 'Cannot delete system platform company'}), 400

        # Explicitly delete auxiliary records before company removal to prevent IntegrityError
        from models.purchased_number import PurchasedNumber
        from models.user import User
        from models.subscription import Subscription
        from models.payment_gateway import PaymentGatewayConfig, PaymentTransaction
        from models.crm_config import CRMConfig
        from models.erp_config import ERPConfig
        from models.ecommerce_config import EcommerceConfig
        from models.mcp_config import CompanyMCPServer
        from models.customer import Customer
        from models.appointment import Appointment
        from models.transaction import Transaction
        from models.note import Note
        from models.contact_attribution import ContactAttribution
        from models.conversation import Conversation, Message
        from models.email_log import EmailLog

        # Delete conversation & customer-dependent records
        EmailLog.query.filter_by(company_id=id).delete()
        Appointment.query.filter_by(company_id=id).delete()
        Transaction.query.filter_by(company_id=id).delete()
        Note.query.filter_by(company_id=id).delete()
        ContactAttribution.query.filter_by(company_id=id).delete()
        
        # Delete messages and conversations
        conv_ids = [c.id for c in Conversation.query.filter_by(company_id=id).all()]
        if conv_ids:
            Message.query.filter(Message.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
        Conversation.query.filter_by(company_id=id).delete()
        
        # Delete customers
        Customer.query.filter_by(company_id=id).delete()

        # Delete tenant configs & secondary objects
        PurchasedNumber.query.filter_by(company_id=id).delete()
        User.query.filter_by(company_id=id).delete()
        Subscription.query.filter_by(company_id=id).delete()
        PaymentTransaction.query.filter_by(company_id=id).delete()
        PaymentGatewayConfig.query.filter_by(company_id=id).delete()
        CRMConfig.query.filter_by(company_id=id).delete()
        ERPConfig.query.filter_by(company_id=id).delete()
        EcommerceConfig.query.filter_by(company_id=id).delete()
        CompanyMCPServer.query.filter_by(company_id=id).delete()

        db.session.delete(company)
        db.session.commit()
        return jsonify({'message': 'Tenant deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting tenant {id}: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/plans', methods=['GET', 'POST'])
@jwt_required()
@super_admin_required
def manage_plans():
    """List or create subscription plans."""
    db.session.rollback()
    if request.method == 'POST':
        data = request.get_json()
        try:
            plan = Plan(
                name=data['name'],
                description=data.get('description'),
                price_monthly=data.get('amount', data.get('price_monthly', 0.0)),
                price_annual=data.get('price_annual', 0.0),
                currency=data.get('currency', 'USD'),
                features=data.get('features', {}),
                is_active=data.get('is_active', True),
                is_default=data.get('is_default', False)
            )
            
            # Sync to dLocal
            from services.dlocal_service import DLocalGoService
            dlocal = DLocalGoService()
            try:
                 dlocal_plan = dlocal.create_plan(
                     name=plan.name,
                     description=plan.description or f"Subscription to {plan.name}",
                     amount=plan.price_monthly,
                     currency=plan.currency or "USD",
                     frequency_type="MONTHLY"
                 )
                 plan.external_plan_token = dlocal_plan.get('plan_token')
                 plan.external_plan_id = dlocal_plan.get('id')
            except Exception as dloc_e:
                 logger.error(f"dLocal sync failed on plan creation: {dloc_e}")
                 
            db.session.add(plan)
            db.session.commit()
            return jsonify(plan.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Create plan error: {e}")
            return jsonify({'error': str(e)}), 500
            
    plans = Plan.query.all()
    return jsonify([p.to_dict() for p in plans]), 200

@admin_bp.route('/plans/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required()
@super_admin_required
def update_delete_plan(id):
    """Update or deactivate a plan, syncing to dLocal."""
    db.session.rollback()
    plan = Plan.query.get_or_404(id)
    
    if request.method == 'DELETE':
        plan.is_active = False
        db.session.commit()
        return jsonify({'message': 'Plan deactivated'}), 200
        
    try:
        data = request.get_json()
        plan.name = data.get('name', plan.name)
        plan.description = data.get('description', plan.description)
        plan.price_monthly = data.get('amount', data.get('price_monthly', plan.price_monthly))
        plan.price_annual = data.get('price_annual', plan.price_annual)
        plan.currency = data.get('currency', plan.currency)
        
        if 'features' in data:
            plan.features = data['features']
            
        if 'is_active' in data:
            plan.is_active = data['is_active']
            
        if 'is_default' in data:
            plan.is_default = data['is_default']
            
        # Sync updates to dLocal
        from services.dlocal_service import DLocalGoService
        dlocal = DLocalGoService()
        
        if plan.external_plan_token:
            try:
                dloc_id = plan.external_plan_id or plan.external_plan_token
                dlocal.update_plan(
                    plan_id=dloc_id,
                    name=plan.name,
                    description=plan.description,
                    amount=plan.price_monthly
                )
            except Exception as e:
                logger.error(f"dLocal sync failed on plan update: {e}")
        else:
            try:
                dlocal_plan = dlocal.create_plan(
                    name=plan.name,
                    description=plan.description or f"Subscription to {plan.name}",
                    amount=plan.price_monthly,
                    currency=plan.currency or "USD",
                    frequency_type="MONTHLY"
                )
                plan.external_plan_token = dlocal_plan.get('plan_token')
                plan.external_plan_id = dlocal_plan.get('id')
            except Exception as e:
                logger.error(f"dLocal sync failed on plan fallback creation: {e}")
        
        db.session.commit()
        return jsonify(plan.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Update plan error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/geo-analytics', methods=['GET'])
@jwt_required()
@super_admin_required
def get_geo_analytics():
    """
    Super Admin Geo-Spatial Telemetry and Eye of God Radar.
    Returns OpenStreetMap compatible coordinates, usage time, lead scores,
    and security anomaly triangulations for all tenants, beta leads, and live sessions.
    """
    db.session.rollback()
    try:
        from services.geo_analytics_service import GeoAnalyticsService
        data = GeoAnalyticsService.get_geo_radar_data()
        return jsonify(data), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Geo-analytics fetch error: {e}", exc_info=True)
        return jsonify({'error': str(e), 'success': False}), 500


@admin_bp.route('/ip-block', methods=['POST'])
@jwt_required()
@super_admin_required
def block_ip_address():
    """Super Admin route to blacklist an abusive or unauthorized IP address."""
    db.session.rollback()
    try:
        data = request.get_json() or {}
        ip = data.get('ip', '').strip()
        reason = data.get('reason', 'Bloqueado por Super Admin')
        if not ip:
            return jsonify({'error': 'La dirección IP es requerida'}), 400

        user_id = int(get_jwt_identity())
        from services.ip_security_service import IpSecurityService
        result = IpSecurityService.block_ip(ip=ip, reason=reason, blocked_by=user_id)
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error blocking IP: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/ip-unblock', methods=['POST'])
@jwt_required()
@super_admin_required
def unblock_ip_address():
    """Super Admin route to remove an IP address from the security blacklist."""
    db.session.rollback()
    try:
        data = request.get_json() or {}
        ip = data.get('ip', '').strip()
        if not ip:
            return jsonify({'error': 'La dirección IP es requerida'}), 400

        from services.ip_security_service import IpSecurityService
        result = IpSecurityService.unblock_ip(ip=ip)
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unblocking IP: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/blocked-ips', methods=['GET'])
@jwt_required()
@super_admin_required
def list_blocked_ips():
    """Super Admin route to list all blacklisted IPs."""
    db.session.rollback()
    try:
        from models.ip_tracking import BlockedIp
        blocked = BlockedIp.query.filter_by(is_active=True).order_by(BlockedIp.blocked_at.desc()).all()
        return jsonify({'blocked_ips': [b.to_dict() for b in blocked]}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error listing blocked IPs: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/credits-breakdown', methods=['GET'])
@jwt_required()
@super_admin_required
def get_credits_breakdown():
    """
    Super Admin endpoint to audit and visualize token and credit consumption per tenant across all channels:
    - Webchat (Embedded website widget)
    - WhatsApp
    - Telegram
    - Admin Copilot Chat
    - Voice STT/TTS
    - Total tokens & current balances
    """
    db.session.rollback()
    try:
        from models.company import Company
        from models.conversation import Conversation, Message
        from models.user import User, UserRole
        from sqlalchemy import func

        config = PlatformConfig.get_config()
        platform_company_id = config.platform_company_id

        # Query all non-platform companies
        companies = Company.query.filter(
            Company.name != "Aikrofy AI Platform",
            Company.name != "PymAI AI Platform"
        )
        if platform_company_id:
            companies = companies.filter(Company.id != platform_company_id)
        
        companies_list = companies.order_by(Company.id.desc()).all()
        
        report = []
        for comp in companies_list:
            admin_user = User.query.filter_by(company_id=comp.id, role=UserRole.ADMIN).first()
            
            # Channel breakdown count of AI interactions / messages
            channel_counts = {}
            channels_query = db.session.query(
                Conversation.channel,
                func.count(Message.id),
                func.sum(func.coalesce(Message.tokens_used, 0))
            ).join(Message, Message.conversation_id == Conversation.id).filter(
                Conversation.company_id == comp.id
            ).group_by(Conversation.channel).all()
            
            total_msgs = 0
            total_tokens = 0
            for ch_name, msg_cnt, tok_sum in channels_query:
                ch_key = (ch_name or 'webchat').lower().strip()
                channel_counts[ch_key] = {
                    'messages': int(msg_cnt or 0),
                    'tokens': int(tok_sum or 0)
                }
                total_msgs += int(msg_cnt or 0)
                total_tokens += int(tok_sum or 0)
                
            # Estimated total credits consumed based on interactions
            estimated_credits_used = max(0, int(total_tokens / 1500)) if total_tokens > 0 else int(total_msgs * 2)

            report.append({
                'company_id': comp.id,
                'company_name': comp.name,
                'admin_email': admin_user.email if admin_user else (comp.email or 'N/A'),
                'credit_balance': comp.credit_balance if comp.credit_balance is not None else 0,
                'is_unlimited': comp.credit_balance == -1,
                'subscription_tier': comp.subscription_tier or 'free',
                'plan_type': comp.plan_type or 'pyme',
                'total_messages': total_msgs,
                'total_tokens': total_tokens,
                'estimated_credits_used': estimated_credits_used,
                'channels': {
                    'webchat': channel_counts.get('webchat', {'messages': 0, 'tokens': 0}),
                    'whatsapp': channel_counts.get('whatsapp', {'messages': 0, 'tokens': 0}),
                    'telegram': channel_counts.get('telegram', {'messages': 0, 'tokens': 0}),
                    'admin_chat': channel_counts.get('admin_chat', {'messages': 0, 'tokens': 0}),
                    'voice': channel_counts.get('voice', {'messages': 0, 'tokens': 0}),
                    'email': channel_counts.get('email', {'messages': 0, 'tokens': 0})
                }
            })
            
        return jsonify({
            'success': True,
            'data': report,
            'summary': {
                'total_tenants': len(report),
                'total_platform_tokens': sum(r['total_tokens'] for r in report),
                'total_platform_messages': sum(r['total_messages'] for r in report)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error fetching credits breakdown: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
