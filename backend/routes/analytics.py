import logging
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Analytics & Dashboard Routes
"""
from datetime import datetime, timedelta


from sqlalchemy import func
from extensions import db
from models.user import User, UserRole
from models.conversation import Conversation, Message, ConversationType, MessageChannel
from models.channel import Channel, ChannelStatus
from models.document import Document, DocumentStatus
from models.employee import Employee
from models.customer import Customer

logger = logging.getLogger(__name__)
analytics_bp = APIRouter('analytics', __name__)


def _get_crm_integration_status(company_id: int) -> dict:
    """Returns generic CRM connection status from the CRMConfig table."""
    try:
        from models.crm_config import CRMConfig
        crm = CRMConfig.query.filter_by(company_id=company_id, is_active=True).first()
        if crm:
            return {'connected': True, 'platform': crm.platform.value if hasattr(crm.platform, 'value') else str(crm.platform)}
    except Exception:
        pass
    return {'connected': False, 'platform': None}



def get_user_company():
    """Helper to get current user's company.

    [OPTIMIZACIÓN HASH TABLE - Estructura 5]
    Sirve company desde caché Redis O(1) cuando hay sesión activa.
    Evita 2 queries SQL (User + Company JOIN) por cada petición de analítica.
    """
    try:
        user_id = int(get_jwt_identity())

        # [HASH TABLE] Intentar company desde caché de sesión
        from services.cache_service import CacheService
        cached_session = CacheService.get(f"user:session:{user_id}")
        if cached_session and cached_session.get('company'):
            # Traer el objeto ORM real desde el ID cacheado
            company_id = cached_session['company'].get('id')
            if company_id:
                from models.company import Company as CompanyModel
                company = CompanyModel.query.get(company_id)
                if company:
                    return company

        # Cache miss — query SQL normal
        user = User.query.get(user_id)
        if not user:
            return None
        if not user.company and user.role == UserRole.SUPER_ADMIN:
            from models.company import Company as CompanyModel
            return CompanyModel.query.filter(CompanyModel.name.ilike('%aikrofy%')).first() or CompanyModel.query.get(1)
        if not user.company:
            print(f"DEBUG: Analytics - User/Company missing for ID {user_id}")
            return None

        # Repoblar caché de sesión si faltaba
        try:
            user_dict = user.to_dict()
            company_dict = user.company.to_dict()
            CacheService.set(f"user:session:{user_id}", {'user': user_dict, 'company': company_dict}, ttl=300)
        except Exception:
            pass  # Cache error no es bloqueante

        return user.company
    except Exception as e:
        print(f"DEBUG: Analytics - Error: {e}")
        return None


@analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get main dashboard data"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    from services.cache_service import CacheService
    cache_key = f"analytics:dashboard:company_{company.id}"
    try:
        cached_data = CacheService.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
    except Exception as e:
        print(f"Error reading dashboard cache: {e}")
    
    # Time ranges
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Conversation stats
    total_conversations = Conversation.query.filter_by(company_id=company.id).count()
    active_conversations = Conversation.query.filter_by(company_id=company.id, is_active=True).count()
    today_conversations = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= today_start
    ).count()
    
    # Message stats
    total_messages = db.session.query(func.count(Message.id)).join(Conversation).filter(
        Conversation.company_id == company.id
    ).scalar() or 0
    
    today_messages = db.session.query(func.count(Message.id)).join(Conversation).filter(
        Conversation.company_id == company.id,
        Message.created_at >= today_start
    ).scalar() or 0
    
    # Channel status
    channels = Channel.query.filter_by(company_id=company.id).all()
    connected_channels = sum(1 for c in channels if c.status == ChannelStatus.CONNECTED)
    
    # Document stats
    total_documents = Document.query.filter_by(company_id=company.id).count()
    indexed_documents = Document.query.filter_by(company_id=company.id, status=DocumentStatus.INDEXED).count()
    
    # Employee count
    employee_count = Employee.query.filter_by(company_id=company.id, is_active=True).count()
    
    # Agent stats
    from models.agent import Agent, AgentObjective
    agents = Agent.query.filter(
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).all()
    
    # Integration status (from config tables)
    from models.crm_config import CRMConfig
    from models.ecommerce_config import EcommerceConfig
    from models.erp_config import ERPConfig
    from models.payment_gateway import PaymentGatewayConfig

    crm_cfg = CRMConfig.query.filter_by(company_id=company.id, is_connected=True).first()
    ecom_cfg = EcommerceConfig.query.filter_by(company_id=company.id, is_connected=True).first()
    erp_cfg = ERPConfig.query.filter_by(company_id=company.id, is_connected=True).first()
    payment_cfg = PaymentGatewayConfig.query.filter_by(company_id=company.id, is_connected=True).first()

    api_keys = company.api_keys or {}
    integrations = {
        'google_calendar': {
            'connected': bool(api_keys.get('google_oauth_credentials') and api_keys.get('google_calendar_id')),
            'calendar_id': api_keys.get('google_calendar_id')
        },
        'google_sheets': {
            'connected': bool(api_keys.get('google_oauth_credentials') and api_keys.get('google_sheet_id')),
            'sheet_id': api_keys.get('google_sheet_id')
        },
        'crm': {
            'connected': bool(crm_cfg),
            'platform': crm_cfg.platform.value if crm_cfg and hasattr(crm_cfg.platform, 'value') else (str(crm_cfg.platform) if crm_cfg else None)
        },
        'ecommerce': {
            'connected': bool(ecom_cfg),
            'platform': ecom_cfg.platform.value if ecom_cfg and hasattr(ecom_cfg.platform, 'value') else (str(ecom_cfg.platform) if ecom_cfg else None)
        },
        'erp': {
            'connected': bool(erp_cfg),
            'platform': erp_cfg.platform.value if erp_cfg and hasattr(erp_cfg.platform, 'value') else (str(erp_cfg.platform) if erp_cfg else None)
        },
        'payments': {
            'connected': bool(payment_cfg) or bool(api_keys.get('paypal_id') and api_keys.get('paypal_secret')),
            'platform': payment_cfg.gateway_provider.value if payment_cfg and hasattr(payment_cfg.gateway_provider, 'value') else ('paypal' if bool(api_keys.get('paypal_id')) else None)
        },
        'paypal': {
            'connected': bool(api_keys.get('paypal_id') and api_keys.get('paypal_secret')),
            'mode': api_keys.get('paypal_mode')
        }
    }
    
    payload = {
        'overview': {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'today_conversations': today_conversations,
            'total_messages': total_messages,
            'today_messages': today_messages
        },
        'channels': {
            'total': len(channels),
            'connected': connected_channels,
            'list': [c.to_dict() for c in channels]
        },
        'documents': {
            'total': total_documents,
            'indexed': indexed_documents
        },
        'team': {
            'employees': employee_count
        },
        'agents': {
            'total': len(agents),
            'list': [{'id': a.id, 'name': a.name, 'status': 'active' if a.is_active else 'inactive'} for a in agents]
        },
        'integrations': integrations
    }
    
    try:
        from services.cache_service import CacheService
        CacheService.set(cache_key, payload, ttl=60)  # Cache for 60 seconds (1 minute)
    except Exception as e:
        print(f"Error saving dashboard cache: {e}")

    return jsonify(payload)


@analytics_bp.route('/summary', methods=['GET'])
@jwt_required()
def get_summary_stats():
    """Get summary statistics for Overview dashboard.

    [OPTIMIZACIÓN HASH TABLE - Estructura 5]
    Caché Redis por company_id+days para evitar recalcular en las
    múltiples peticiones concurrentes que el frontend dispara post-login.
    """
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    # Time ranges
    days = int(request.args.get('days', 30))

    # [HASH TABLE] Intentar servir desde caché
    from services.cache_service import CacheService
    cache_key = f"analytics:summary:company_{company.id}:days_{days}"
    cached = CacheService.get(cache_key)
    if cached:
        return jsonify(cached)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Appointments in period
    from models.appointment import Appointment
    appointments_count = Appointment.query.filter(
        Appointment.company_id == company.id,
        Appointment.created_at >= start_date
    ).count()

    # Conversations in period
    total_conversations = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date
    ).count()

    # Message stats in period
    from models.conversation import Message, MessageRole
    total_messages = db.session.query(func.count(Message.id)).join(Conversation).filter(
        Conversation.company_id == company.id,
        Message.created_at >= start_date
    ).scalar() or 0

    inbound_messages = db.session.query(func.count(Message.id)).join(Conversation).filter(
        Conversation.company_id == company.id,
        Message.created_at >= start_date,
        Message.role == MessageRole.USER
    ).scalar() or 0

    outbound_messages = total_messages - inbound_messages

    # Customer/Lead registrations in period
    from models.customer import Customer
    total_customers = Customer.query.filter(
        Customer.company_id == company.id,
        Customer.created_at >= start_date
    ).count()

    # Emails sent in period
    from models.email_log import EmailLog
    emails_sent = EmailLog.query.filter(
        EmailLog.company_id == company.id,
        EmailLog.sent_at >= start_date
    ).count()

    # Total Revenue (Completed Transactions) in period
    from models.transaction import Transaction, TransactionStatus
    total_revenue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.company_id == company.id,
        Transaction.status == TransactionStatus.COMPLETED.value,
        Transaction.created_at >= start_date
    ).scalar() or 0

    payload = {
        'appointments': appointments_count,
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'inbound_messages': inbound_messages,
        'outbound_messages': outbound_messages,
        'total_customers': total_customers,
        'emails_sent': emails_sent,
        'total_revenue': round(float(total_revenue), 2),
        'period_days': days
    }

    # [HASH TABLE] Persistir en caché Redis (TTL 60s — same as dashboard)
    CacheService.set(cache_key, payload, ttl=60)

    return jsonify(payload)



@analytics_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversation_stats():
    """Get detailed conversation statistics"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Parse date range
    days = int(request.args.get('days', 30))
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Daily conversation count
    daily_stats = db.session.query(
        func.date(Conversation.started_at).label('date'),
        func.count(Conversation.id).label('count')
    ).filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date
    ).group_by(
        func.date(Conversation.started_at)
    ).all()
    
    # Channel breakdown
    channel_stats = db.session.query(
        Conversation.channel,
        func.count(Conversation.id).label('count')
    ).filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date
    ).group_by(Conversation.channel).all()
    
    # Type breakdown (customer vs admin)
    type_stats = db.session.query(
        Conversation.type,
        func.count(Conversation.id).label('count')
    ).filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date
    ).group_by(Conversation.type).all()
    
    # Resolution rate (Action Based)
    from models.transaction import Transaction
    from models.appointment import Appointment
    from models.email_log import EmailLog
    
    all_txns = Transaction.query.filter(Transaction.company_id == company.id, Transaction.created_at >= start_date).count()
    all_appts = Appointment.query.filter(Appointment.company_id == company.id, Appointment.created_at >= start_date).count()
    email_cnt = EmailLog.query.filter(EmailLog.company_id == company.id, EmailLog.sent_at >= start_date).count()
    
    total = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date
    ).count()

    resolution_actions = all_txns + all_appts + email_cnt
    
    resolution_rate = (resolution_actions / total * 100) if total > 0 else 0
    
    return jsonify({
        'daily': [{'date': str(d.date), 'count': d.count} for d in daily_stats],
        'by_channel': [{'channel': c.channel if isinstance(c.channel, str) else c.channel.value, 'count': c.count} for c in channel_stats],
        'by_type': [{'type': t.type.value if hasattr(t.type, 'value') else t.type, 'count': t.count} for t in type_stats],
        'resolution_rate': round(resolution_rate, 2),
        'period_days': days
    })


@analytics_bp.route('/funnel', methods=['GET'])
@jwt_required()
def get_funnel_data():
    """Get sales funnel data.

    [OPTIMIZACIÓN HASH TABLE - Estructura 5]
    Caché Redis por company_id+days. El frontend llama este endpoint
    simultáneamente al summary justo al cargar el dashboard post-login.
    """
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    # Parse date range
    days = int(request.args.get('days', 30))

    # [HASH TABLE] Intentar servir desde caché
    from services.cache_service import CacheService
    cache_key = f"analytics:funnel:company_{company.id}:days_{days}"
    cached = CacheService.get(cache_key)
    if cached:
        return jsonify(cached)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # 1. Total Leads (All Conversations)
    total_leads = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.type == ConversationType.CUSTOMER,
        Conversation.started_at >= start_date
    ).count()

    # 2. Awareness (Engaged: > 2 messages OR lead_score > 10)
    # Refined: Conversations with > 1 message (User replied at least once)
    awareness = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.type == ConversationType.CUSTOMER,
        Conversation.started_at >= start_date
    ).join(Message).group_by(Conversation.id).having(func.count(Message.id) >= 2).count()

    # 3. Interest (Highly Engaged: lead_score >= 30 OR > 5 messages)
    interest = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.type == ConversationType.CUSTOMER,
        Conversation.started_at >= start_date
    ).join(Message).group_by(Conversation.id).having(
        (func.count(Message.id) >= 5) | (Conversation.lead_score >= 25)
    ).count()

    # 4. Consideration (Scheduled Appointment OR Evaluation)
    from models.appointment import Appointment
    consideration = Appointment.query.filter(
        Appointment.company_id == company.id,
        Appointment.created_at >= start_date
    ).count()

    # 5. Intent (Pending Transactions / Payment Links)
    from models.transaction import Transaction, TransactionStatus
    intent = Transaction.query.filter(
        Transaction.company_id == company.id,
        Transaction.created_at >= start_date
    ).count()

    # 6. Converted (Completed Transactions)
    converted = Transaction.query.filter(
        Transaction.company_id == company.id,
        Transaction.status == TransactionStatus.COMPLETED.value,
        Transaction.created_at >= start_date
    ).count()

    # --- ACTION-BASED METRICS ---
    all_txns_count = Transaction.query.filter(
        Transaction.company_id == company.id,
        Transaction.created_at >= start_date
    ).count()

    completed_txns_count = Transaction.query.filter(
        Transaction.company_id == company.id,
        Transaction.created_at >= start_date,
        Transaction.status == TransactionStatus.COMPLETED.value
    ).count()

    all_appts_count = Appointment.query.filter(
        Appointment.company_id == company.id,
        Appointment.created_at >= start_date
    ).count()

    from models.email_log import EmailLog
    email_count = EmailLog.query.filter(
        EmailLog.company_id == company.id,
        EmailLog.sent_at >= start_date
    ).count()

    resolution_actions = all_txns_count + all_appts_count + email_count
    conversion_actions = completed_txns_count + all_appts_count

    payload = {
        'funnel': [
            {'stage': 'Total Leads', 'count': total_leads},
            {'stage': 'Awareness', 'count': awareness},
            {'stage': 'Interest', 'count': interest},
            {'stage': 'Consideration (Meetings)', 'count': consideration},
            {'stage': 'Intent (Payment Links)', 'count': intent},
            {'stage': 'Converted (Sales)', 'count': converted}
        ],
        'conversion_rate': round((conversion_actions / total_leads * 100), 2) if total_leads > 0 else 0,
        'resolution_rate': round((resolution_actions / total_leads * 100), 2) if total_leads > 0 else 0,
        'period_days': days
    }

    # [HASH TABLE] Persistir en caché Redis (TTL 60s)
    CacheService.set(cache_key, payload, ttl=60)

    return jsonify(payload)


@analytics_bp.route('/sentiment', methods=['GET'])
@jwt_required()
def get_sentiment_data():
    """Get sentiment analysis data"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # Parse date range
    days = int(request.args.get('days', 30))
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Average sentiment
    avg_sentiment = db.session.query(
        func.avg(Conversation.sentiment_score)
    ).filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date,
        Conversation.sentiment_score != None
    ).scalar() or 0
    
    # Sentiment distribution
    positive = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date,
        Conversation.sentiment_score != None,
        Conversation.sentiment_score > 0.3
    ).count()
    
    neutral = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date,
        Conversation.sentiment_score != None,
        Conversation.sentiment_score >= -0.3,
        Conversation.sentiment_score <= 0.3
    ).count()
    
    negative = Conversation.query.filter(
        Conversation.company_id == company.id,
        Conversation.started_at >= start_date,
        Conversation.sentiment_score != None,
        Conversation.sentiment_score < -0.3
    ).count()
    
    return jsonify({
        'average_sentiment': round(avg_sentiment, 2),
        'distribution': {
            'positive': positive,
            'neutral': neutral,
            'negative': negative
        },
        'period_days': days
    })

@analytics_bp.route('/customers', methods=['GET'])
@jwt_required()
def get_customer_stats():
    """Get registered customer stats (Contacts with Data)"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    # Count customers with valid data (Name, Email OR Phone)
    # Assuming 'Customer' table already implies some data, but verifying.
    # User said: "solo son los contactos donde tenemos datos, es decir correo, nombre"
    
    count = Customer.query.filter(
        Customer.company_id == company.id,
        (Customer.email != None) | (Customer.phone != None) | (Customer.first_name != None)
    ).count()
    
    return jsonify({
        'count': count,
        'label': 'Clientes Registrados'
    })


# ============================================================
# Customizable Dynamic Dashboards & Widgets (Fase 5)
# ============================================================

@analytics_bp.route('/custom-config', methods=['GET'])
@jwt_required()
def get_user_dashboard():
    """Retrieve or initialize user customizable dashboard configurations."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    user_id = int(get_jwt_identity())
    from models.analytics_dashboard import UserDashboard, DashboardWidget, PredefinedMetric

    # 1. Fetch or create default dashboard for user
    dashboard = UserDashboard.query.filter_by(
        company_id=company.id,
        user_id=user_id
    ).first()

    if not dashboard:
        logger.info(f"Initializing default customizable dashboard for user {user_id} in company {company.id}")
        dashboard = UserDashboard(
            company_id=company.id,
            user_id=user_id,
            dashboard_name="Dashboard Principal",
            is_default=True
        )
        db.session.add(dashboard)
        db.session.commit()

        # Seed default widgets for this new dashboard
        metrics = PredefinedMetric.query.all()
        default_layouts = {
            "leads_by_score_range": {"x": 0, "y": 0, "w": 6, "h": 3},
            "contacts_by_channel": {"x": 6, "y": 0, "w": 6, "h": 3},
            "funnel_conversions": {"x": 0, "y": 3, "w": 12, "h": 4}
        }

        for metric in metrics:
            layout = default_layouts.get(metric.metric_key, {"x": 0, "y": 0, "w": 4, "h": 3})
            widget = DashboardWidget(
                dashboard_id=dashboard.id,
                predefined_metric_id=metric.id,
                widget_title=metric.display_name,
                chart_type=metric.default_chart_type,
                grid_layout=layout,
                widget_settings={"days_back": 30}
            )
            db.session.add(widget)
        db.session.commit()

    # 2. Serialize widgets list
    widgets = []
    for widget in dashboard.widgets.all():
        widgets.append({
            'id': widget.id,
            'title': widget.widget_title,
            'chartType': widget.chart_type.value if hasattr(widget.chart_type, 'value') else widget.chart_type,
            'layout': {
                'i': str(widget.id),
                'x': widget.grid_layout.get('x', 0),
                'y': widget.grid_layout.get('y', 0),
                'w': widget.grid_layout.get('w', 4),
                'h': widget.grid_layout.get('h', 3)
            },
            'metric_key': widget.metric.metric_key
        })

    return jsonify({
        'dashboard_id': dashboard.id,
        'name': dashboard.dashboard_name,
        'widgets': widgets
    }), 200


@analytics_bp.route('/layout/save', methods=['POST'])
@jwt_required()
def save_dashboard_layout():
    """Save user dashboard widgets layout coordinates."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    user_id = int(get_jwt_identity())
    data = request.get_json()
    layouts = data.get('layouts', [])
    
    from models.analytics_dashboard import UserDashboard, DashboardWidget

    for item in layouts:
        widget_id = item.get('widgetId')
        grid_layout = item.get('grid_layout', {})
        
        # Verify ownership of the widget
        widget = DashboardWidget.query.join(UserDashboard).filter(
            DashboardWidget.id == widget_id,
            UserDashboard.company_id == company.id,
            UserDashboard.user_id == user_id
        ).first()

        if widget:
            widget.grid_layout = {
                'x': int(grid_layout.get('x', 0)),
                'y': int(grid_layout.get('y', 0)),
                'w': int(grid_layout.get('w', 4)),
                'h': int(grid_layout.get('h', 3))
            }
            
    db.session.commit()
    return jsonify({'success': True, 'message': 'Layout saved successfully'}), 200


@analytics_bp.route('/widget-data', methods=['POST'])
@jwt_required()
def get_widget_data():
    """Securely execute predefined SQL template and return widget analytics data."""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    user_id = int(get_jwt_identity())
    data = request.get_json()
    widget_id = data.get('widget_id')
    days_back = int(data.get('days_back', 30))

    from models.analytics_dashboard import UserDashboard, DashboardWidget
    from sqlalchemy import text

    # Verify widget ownership to prevent cross-tenant data leaks
    widget = DashboardWidget.query.join(UserDashboard).filter(
        DashboardWidget.id == widget_id,
        UserDashboard.company_id == company.id
    ).first()

    if not widget or not widget.metric:
        return jsonify({'error': 'Widget not found'}), 404

    sql_template = widget.metric.aggregation_query_template

    try:
        # Run safe parameterized SQL execution
        result = db.session.execute(
            text(sql_template),
            {"company_id": company.id, "days_back": days_back}
        ).fetchall()
        
        # Format dataset: [{label: str, value: int}, ...]
        serialized_data = [{"label": str(row[0]), "value": row[1]} for row in result]

        return jsonify({
            'widget_id': widget_id,
            'title': widget.widget_title,
            'chart_type': widget.chart_type.value if hasattr(widget.chart_type, 'value') else widget.chart_type,
            'metric_key': widget.metric.metric_key,
            'data': serialized_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error executing widget analytical query: {e}")
        return jsonify({'error': f"Failed to execute metric query: {str(e)}"}), 500
