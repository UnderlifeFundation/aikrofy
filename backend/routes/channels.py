from routing import APIRouter, Response, current_app, get_jwt_identity, jsonify, jwt_required, request
"""
Channel Management Routes
"""
from datetime import datetime, timedelta
import uuid  # Added for Webchat
import requests # Added for Telegram


from extensions import db
from models.user import User, UserRole
from models.channel import Channel, ChannelType, ChannelStatus

channels_bp = APIRouter('channels', __name__)


def get_user_company():
    """Helper to get current user's company"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None
        if user.company:
            return user.company
        if user.role == UserRole.SUPER_ADMIN:
            from models.company import Company
            comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
            return comp
        return None
    except Exception as e:
        print(f"DEBUG: Channels - Error: {e}")
        return None


@channels_bp.route('/', methods=['GET'])
@jwt_required()
def list_channels():
    """List all channels for the company"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    channels = Channel.query.filter_by(company_id=company.id).all()
    # Include credentials so UI can pre-fill forms (secrets should be masked by frontend or here if refined)
    return jsonify({'channels': [c.to_dict(include_credentials=True) for c in channels]})


@channels_bp.route('/', methods=['POST'])
@channels_bp.route('/connect', methods=['POST'])
@jwt_required()
def connect_channel():
    """Initiate channel connection"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json() or {}
    
    type_str = data.get('type') or data.get('channel_type')
    try:
        channel_type = ChannelType(type_str)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid channel type'}), 400
        
    # Check if channel is allowed in current subscription plan
    if company.subscription and company.subscription.plan:
        is_courtesy = company.subscription.status.value == 'courtesy'
        if not is_courtesy:
            plan_features = company.subscription.plan.features or {}
            allowed_channels = plan_features.get('channels', [])
            
            check_val = channel_type.value
            if check_val == 'voice':
                check_val = 'voice_calls'
                
            if check_val not in allowed_channels:
                return jsonify({
                     'error': f'Channel {channel_type.value.title()} is not included in your current subscription plan.'
                }), 403
    
    # Check if channel already exists
    channel = Channel.query.filter_by(
        company_id=company.id,
        type=channel_type
    ).first()
    
    if not channel:
        channel = Channel(
            company_id=company.id,
            type=channel_type,
            name=data.get('name', channel_type.value.title())
        )
        db.session.add(channel)
        db.session.flush() # Generate ID for webhooks
    
    # Handle different channel types
    if channel_type == ChannelType.WHATSAPP:
        return connect_whatsapp(channel, data)
    elif channel_type == ChannelType.EMAIL:
        return connect_email(channel, data)
    elif channel_type == ChannelType.VOICE:
        return connect_voice(channel, data)
    elif channel_type == ChannelType.SMS:
        return connect_sms(channel, data)
    elif channel_type == ChannelType.TELEGRAM:
        return connect_telegram(channel, data)
    elif channel_type == ChannelType.WEBCHAT:
        return connect_webchat(channel, data)
    else:
        return jsonify({'error': 'Channel type not supported'}), 400


from config import Config


@channels_bp.route('/meta/config', methods=['GET'])
@jwt_required()
def get_meta_config():
    """Return Meta App configuration for frontend Facebook Login / Embedded Signup"""
    return jsonify({
        'app_id': getattr(Config, 'META_APP_ID', ''),
        'config_id': getattr(Config, 'META_CONFIG_ID', ''),
        'verify_token': getattr(Config, 'META_VERIFY_TOKEN', 'aikrofy_meta_secret_2026')
    })


# ─── Meta Embedded Signup Helpers ───────────────────────────────────────────

META_GRAPH_VERSION = 'v21.0'
META_GRAPH_BASE = f'https://graph.facebook.com/{META_GRAPH_VERSION}'


def _meta_exchange_code(code: str) -> dict:
    """
    Exchange a short-lived Embedded Signup authorization code for a
    customer-scoped User Access Token using the server-side APP_ID/SECRET.
    Returns dict with 'access_token' on success, 'error' on failure.
    """
    app_id = getattr(Config, 'META_APP_ID', '')
    app_secret = getattr(Config, 'META_APP_SECRET', '')
    if not app_id or not app_secret:
        return {'error': 'META_APP_ID and META_APP_SECRET are not configured on this server.'}
    try:
        res = requests.get(
            f'{META_GRAPH_BASE}/oauth/access_token',
            params={
                'client_id': app_id,
                'client_secret': app_secret,
                'code': code,
            },
            timeout=15,
        )
        data = res.json()
        if 'access_token' in data:
            return {'access_token': data['access_token']}
        err = data.get('error', {})
        return {'error': err.get('message', 'Unknown error during code exchange')}
    except Exception as exc:
        return {'error': f'Network error during token exchange: {exc}'}


def _meta_discover_waba(access_token: str) -> dict:
    """
    Retrieve all WhatsApp Business Accounts (WABAs) the user granted access to.
    Uses 3 complementary Graph API strategies:
    1. Debug token target_ids (official for Meta Tech Provider Embedded Signup)
    2. /me/businesses (client & owned WABAs)
    3. /me/client_whatsapp_business_accounts
    """
    app_id = getattr(Config, 'META_APP_ID', '')
    app_secret = getattr(Config, 'META_APP_SECRET', '')
    waba_dict = {}

    # Strategy 1: Debug token granular scopes (Embedded Signup target_ids)
    if app_id and app_secret:
        try:
            app_token = f"{app_id}|{app_secret}"
            res = requests.get(
                f'{META_GRAPH_BASE}/debug_token',
                params={'input_token': access_token, 'access_token': app_token},
                timeout=10,
            )
            data = res.json().get('data', {})
            granular_scopes = data.get('granular_scopes', [])
            target_ids = []
            for scope_info in granular_scopes:
                if scope_info.get('scope') in ['whatsapp_business_management', 'whatsapp_business_messaging']:
                    target_ids.extend(scope_info.get('target_ids', []))

            for waba_id in set(target_ids):
                w_res = requests.get(
                    f'{META_GRAPH_BASE}/{waba_id}',
                    headers={'Authorization': f'Bearer {access_token}'},
                    params={'fields': 'id,name,currency,timezone_id'},
                    timeout=10,
                )
                w_data = w_res.json()
                if 'id' in w_data:
                    waba_dict[w_data['id']] = {'id': w_data['id'], 'name': w_data.get('name', f"WABA {w_data['id']}")}
        except Exception as exc:
            print(f"Debug token WABA discovery error: {exc}")

    # Strategy 2: If no WABAs found yet, query /me/businesses
    if not waba_dict:
        try:
            res = requests.get(
                f'{META_GRAPH_BASE}/me/businesses',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'fields': 'id,name,client_whatsapp_business_accounts{id,name},owned_whatsapp_business_accounts{id,name}'},
                timeout=10,
            )
            data = res.json()
            businesses = data.get('data', [])
            for biz in businesses:
                client_wabas = biz.get('client_whatsapp_business_accounts', {}).get('data', [])
                owned_wabas = biz.get('owned_whatsapp_business_accounts', {}).get('data', [])
                for w in client_wabas + owned_wabas:
                    waba_dict[w['id']] = {'id': w['id'], 'name': w.get('name', f"WABA {w['id']}")}
        except Exception as exc:
            print(f"Businesses discovery error: {exc}")

    # Strategy 3: Query /me/client_whatsapp_business_accounts
    if not waba_dict:
        try:
            res = requests.get(
                f'{META_GRAPH_BASE}/me/client_whatsapp_business_accounts',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'fields': 'id,name,currency,timezone_id'},
                timeout=10,
            )
            data = res.json()
            if 'data' in data:
                for w in data['data']:
                    waba_dict[w['id']] = {'id': w['id'], 'name': w.get('name', f"WABA {w['id']}")}
        except Exception as exc:
            print(f"Client WABA discovery error: {exc}")

    if waba_dict:
        return {'waba_list': list(waba_dict.values())}

    return {'error': 'No se encontraron Cuentas de WhatsApp Business (WABA). Asegúrate de haber seleccionado tu negocio y otorgado todos los permisos durante el inicio de sesión.'}


def _meta_get_phone_numbers(waba_id: str, access_token: str) -> dict:
    """
    Retrieve phone numbers registered under a specific WABA.
    Returns dict with 'phone_numbers' (list) or 'error'.
    """
    try:
        res = requests.get(
            f'{META_GRAPH_BASE}/{waba_id}/phone_numbers',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'fields': 'id,display_phone_number,verified_name,code_verification_status,quality_rating'},
            timeout=15,
        )
        data = res.json()
        if 'error' in data:
            return {'error': data['error'].get('message', 'Failed to retrieve phone numbers')}
        return {'phone_numbers': data.get('data', [])}
    except Exception as exc:
        return {'error': f'Network error fetching phone numbers: {exc}'}


def _meta_subscribe_app_to_waba(waba_id: str, access_token: str) -> dict:
    """
    Subscribe the Aikrofy Meta App to a WABA so that webhooks are delivered.
    This call replaces the manual "paste callback URL" step for the client.
    Returns dict with 'success': True or 'error'.
    """
    try:
        res = requests.post(
            f'{META_GRAPH_BASE}/{waba_id}/subscribed_apps',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15,
        )
        data = res.json()
        if data.get('success'):
            return {'success': True}
        if 'error' in data:
            return {'error': data['error'].get('message', 'Failed to subscribe app to WABA')}
        # Some API versions return True directly
        return {'success': True}
    except Exception as exc:
        return {'error': f'Network error subscribing app to WABA: {exc}'}


def _meta_get_phone_number_info(phone_number_id: str, access_token: str) -> dict:
    """
    Fetch details (display number, verified name) for a specific phone number ID.
    """
    try:
        res = requests.get(
            f'{META_GRAPH_BASE}/{phone_number_id}',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'fields': 'id,display_phone_number,verified_name,code_verification_status'},
            timeout=10,
        )
        data = res.json()
        if 'error' in data:
            return {'error': data['error'].get('message', 'Failed to fetch phone number info')}
        return data
    except Exception as exc:
        return {'error': f'Network error fetching phone number info: {exc}'}


# ─── New route: list available WABAs/phone numbers after code exchange ────────

@channels_bp.route('/meta/embedded-signup', methods=['POST'])
@jwt_required()
def meta_embedded_signup():
    """
    Step 1 of Embedded Signup (Tech Provider flow):
    Receives the authorization 'code' from the frontend postMessage,
    exchanges it for an access token, and returns discovered WABAs / phone numbers
    so the frontend can display a selection if multiple exist.

    If there is exactly one WABA and one phone number, auto-completes the connection.
    """
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    body = request.get_json() or {}
    code = body.get('code')
    # These may be provided directly by the postMessage event
    waba_id_hint = body.get('waba_id')
    phone_number_id_hint = body.get('phone_number_id')

    if not code:
        return jsonify({'error': 'Authorization code is required'}), 400

    # 1. Exchange code → access_token
    # When waba_id is pre-provided (step 2 of multi-step flow), the 'code'
    # field may already be an access_token (prefixed with 'EAA'). Skip exchange.
    if waba_id_hint and code.startswith('EAA'):
        # Already an access token — no exchange needed
        access_token = code
    else:
        token_result = _meta_exchange_code(code)
        if 'error' in token_result:
            return jsonify({'error': token_result['error']}), 400
        access_token = token_result['access_token']

    # 2. Discover WABAs
    waba_id = waba_id_hint
    phone_number_id = phone_number_id_hint
    phone_info = {}

    if not waba_id:
        waba_result = _meta_discover_waba(access_token)
        if 'error' in waba_result:
            return jsonify({'error': waba_result['error']}), 400
        waba_list = waba_result.get('waba_list', [])
        if not waba_list:
            return jsonify({'error': 'No WhatsApp Business Accounts found for this user. Please ensure you granted the required permissions during signup.'}), 400
        if len(waba_list) == 1:
            waba_id = waba_list[0]['id']
        else:
            # Multiple WABAs — return list for user selection
            return jsonify({
                'action': 'select_waba',
                'access_token': access_token,
                'waba_list': waba_list,
            }), 200

    # 3. Subscribe app to WABA (automatic webhook setup)
    sub_result = _meta_subscribe_app_to_waba(waba_id, access_token)
    subscription_ok = sub_result.get('success', False)

    # 4. Discover phone numbers
    if not phone_number_id:
        phone_result = _meta_get_phone_numbers(waba_id, access_token)
        if 'error' in phone_result:
            return jsonify({'error': phone_result['error']}), 400
        phone_numbers = phone_result.get('phone_numbers', [])
        if not phone_numbers:
            return jsonify({'error': 'No phone numbers found in the selected WhatsApp Business Account.'}), 400
        if len(phone_numbers) == 1:
            phone_info = phone_numbers[0]
            phone_number_id = phone_info['id']
        else:
            # Multiple phones — return list for user selection
            return jsonify({
                'action': 'select_phone',
                'access_token': access_token,
                'waba_id': waba_id,
                'phone_numbers': phone_numbers,
                'subscription_ok': subscription_ok,
            }), 200
    else:
        # phone_number_id was provided — fetch info
        phone_info = _meta_get_phone_number_info(phone_number_id, access_token)

    # 5. Complete connection with discovered data
    return _meta_complete_connection(
        channel_company=company,
        access_token=access_token,
        waba_id=waba_id,
        phone_number_id=phone_number_id,
        phone_info=phone_info,
        subscription_ok=subscription_ok,
    )


@channels_bp.route('/meta/select-phone', methods=['POST'])
@jwt_required()
def meta_select_phone():
    """
    Step 2 (conditional): Called when the user selects a specific phone number
    or WABA from a list (when multiple exist). Completes the connection.
    """
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    body = request.get_json() or {}
    access_token = body.get('access_token')
    waba_id = body.get('waba_id')
    phone_number_id = body.get('phone_number_id')

    if not access_token or not waba_id or not phone_number_id:
        return jsonify({'error': 'access_token, waba_id and phone_number_id are required'}), 400

    # Subscribe if not already done
    sub_result = _meta_subscribe_app_to_waba(waba_id, access_token)
    subscription_ok = sub_result.get('success', False)

    # Fetch phone info
    phone_info = _meta_get_phone_number_info(phone_number_id, access_token)

    return _meta_complete_connection(
        channel_company=company,
        access_token=access_token,
        waba_id=waba_id,
        phone_number_id=phone_number_id,
        phone_info=phone_info,
        subscription_ok=subscription_ok,
    )


def _meta_complete_connection(channel_company, access_token, waba_id, phone_number_id, phone_info, subscription_ok):
    """
    Finalizes saving the Meta WhatsApp connection to the Channel and Company.
    Creates the channel record if it does not exist.
    """
    from sqlalchemy.orm.attributes import flag_modified

    display_phone = phone_info.get('display_phone_number', '')
    verified_name = phone_info.get('verified_name', '')
    verify_status = phone_info.get('code_verification_status', '')

    # Use the global verify_token from server config (Tech Provider mode)
    verify_token = getattr(Config, 'META_VERIFY_TOKEN', f'aikrofy_meta_{channel_company.id}')

    # Find or create the WhatsApp channel for this company
    channel = Channel.query.filter_by(
        company_id=channel_company.id,
        type=ChannelType.WHATSAPP
    ).first()
    if not channel:
        channel = Channel(
            company_id=channel_company.id,
            type=ChannelType.WHATSAPP,
            name='WhatsApp Business (Meta)'
        )
        db.session.add(channel)
        db.session.flush()

    channel.credentials = {
        'provider': 'meta',
        'phone_number_id': phone_number_id,
        'waba_id': waba_id,
        'access_token': access_token,
        'verify_token': verify_token,
        'phone_number': display_phone,
        'verified_name': verified_name,
        'verification_status': verify_status,
        'webhook_subscribed': subscription_ok,
    }
    channel.phone_number = display_phone
    channel.update_status(ChannelStatus.CONNECTED, 'Connected via Meta Embedded Signup (Cloud API)')

    # Sync credentials to company api_keys for fast access
    if not channel_company.api_keys:
        channel_company.api_keys = {}
    channel_company.api_keys['whatsapp_provider'] = 'meta'
    channel_company.api_keys['meta_phone_id'] = phone_number_id
    channel_company.api_keys['meta_waba_id'] = waba_id
    channel_company.api_keys['meta_token'] = access_token
    flag_modified(channel_company, 'api_keys')

    db.session.commit()

    # Trigger automatic template sync from Meta Graph API
    try:
        from services.meta_template_service import MetaTemplateService
        MetaTemplateService.sync_templates_from_meta(channel_company.id)
    except Exception as exc:
        print(f"[MetaConnect] Auto template sync warning: {exc}")

    return jsonify({
        'action': 'connected',
        'status': 'connected',
        'phone_number': display_phone,
        'verified_name': verified_name,
        'waba_id': waba_id,
        'phone_number_id': phone_number_id,
        'webhook_subscribed': subscription_ok,
        'channel': channel.to_dict(include_credentials=False),
    }), 200


def connect_whatsapp(channel, data):
    """Connect WhatsApp channel via Baileys, Twilio or Meta (Cloud API)"""
    credentials = data.get('credentials', {})
    provider = data.get('provider', 'baileys')  # Default to baileys as requested

    if provider == 'meta':
        # WhatsApp Cloud API (Meta) — legacy path kept for manual/direct credential entry.
        # The preferred path is the /meta/embedded-signup endpoint above.
        from sqlalchemy.orm.attributes import flag_modified

        code = credentials.get('code')
        access_token = credentials.get('access_token')

        # Exchange code if access_token not provided
        if code and not access_token:
            token_result = _meta_exchange_code(code)
            if 'error' in token_result:
                return jsonify({'error': token_result['error']}), 400
            access_token = token_result['access_token']

        phone_number_id = credentials.get('phone_number_id')
        waba_id = credentials.get('waba_id')

        if not access_token:
            return jsonify({'error': 'META_APP_ID and META_APP_SECRET must be configured on the server, or supply an access_token directly.'}), 400

        if not phone_number_id:
            return jsonify({'error': 'phone_number_id is required when using the manual/legacy connection path.'}), 400

        # Fetch phone info
        phone_info = _meta_get_phone_number_info(phone_number_id, access_token)
        phone_number = phone_info.get('display_phone_number') or credentials.get('phone_number', '')
        verified_name = phone_info.get('verified_name', '')

        # Auto-subscribe webhooks if waba_id is available
        subscription_ok = False
        if waba_id:
            sub_result = _meta_subscribe_app_to_waba(waba_id, access_token)
            subscription_ok = sub_result.get('success', False)

        verify_token = credentials.get('verify_token') or getattr(Config, 'META_VERIFY_TOKEN', f'aikrofy_meta_{channel.company_id}')

        # Save
        channel.credentials = {
            'provider': 'meta',
            'phone_number_id': phone_number_id,
            'waba_id': waba_id,
            'access_token': access_token,
            'verify_token': verify_token,
            'phone_number': phone_number,
            'verified_name': verified_name,
            'webhook_subscribed': subscription_ok,
        }
        channel.phone_number = phone_number
        channel.update_status(ChannelStatus.CONNECTED, 'Connected via Meta (Cloud API)')

        company = channel.company
        if not company.api_keys:
            company.api_keys = {}
        company.api_keys['whatsapp_provider'] = 'meta'
        company.api_keys['meta_phone_id'] = phone_number_id
        company.api_keys['meta_waba_id'] = waba_id
        company.api_keys['meta_token'] = access_token
        flag_modified(company, 'api_keys')
        db.session.commit()

        return jsonify({
            'action': 'connected',
            'status': 'connected',
            'phone_number': phone_number,
            'waba_id': waba_id,
            'phone_number_id': phone_number_id,
            'webhook_subscribed': subscription_ok,
            'channel': channel.to_dict(include_credentials=False),
        }), 200

    elif provider == 'twilio':
        # Twilio WhatsApp
        if credentials.get('account_sid'):
            # Merge with existing
            existing = channel.credentials or {}
            new_creds = {
                'provider': 'twilio',
                'account_sid': credentials.get('account_sid'),
                'phone_number': credentials.get('phone_number')
            }
            
            # Handle auth_token
            auth_token = credentials.get('auth_token')
            if auth_token and auth_token != '********':
                new_creds['auth_token'] = auth_token
            elif existing.get('auth_token'):
                new_creds['auth_token'] = existing.get('auth_token')
                
            channel.credentials = new_creds
            channel.phone_number = credentials.get('phone_number')
            channel.update_status(ChannelStatus.CONNECTED, 'Connected via Twilio')

            # Sync to Company API Keys
            company = channel.company
            if not company.api_keys: company.api_keys = {}
            
            company.api_keys['whatsapp_provider'] = 'twilio'
            company.api_keys['twilio_sid'] = new_creds['account_sid']
            if new_creds.get('auth_token'):
                company.api_keys['twilio_token'] = new_creds['auth_token']
            if new_creds.get('phone_number'):
                company.api_keys['twilio_whatsapp_number'] = new_creds['phone_number']
            
            # Fallback telephony provider if not set
            if not company.api_keys.get('telephony_provider'):
                 company.api_keys['telephony_provider'] = 'twilio'
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(company, "api_keys")

        else:
            # Sandbox logic (legacy or dev)
            channel.update_status(ChannelStatus.CONNECTING, 'Awaiting connection')
            channel.qr_code = f"whatsapp://send?phone=+14155238886&text=join%20{channel.company_id}-sandbox"
            channel.qr_expires_at = datetime.utcnow() + timedelta(minutes=15)

    elif provider == 'baileys':
        # Baileys (Direct WhatsApp Web via Node.js API)
        try:
            from services.whatsapp_service import WhatsAppBaileysService
            
            company = channel.company
            service = WhatsAppBaileysService(str(company.id))
            
            # Check if API is available
            if not WhatsAppBaileysService.is_available():
                return jsonify({'error': 'WhatsApp API service is not available. Please ensure it is running.'}), 503
            
            # Initialize session
            result = service.init_session()
            
            if result.get('error'):
                return jsonify({'error': result.get('error')}), 500
            
            # Save to channel
            channel.credentials = {
                'provider': 'baileys',
                'session_id': str(company.id)
            }
            channel.update_status(ChannelStatus.CONNECTING, 'Scan QR code to connect')
            
            # Sync to Company API Keys
            if not company.api_keys:
                company.api_keys = {}
            company.api_keys['whatsapp_provider'] = 'baileys'
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(company, "api_keys")
            
        except Exception as e:
            return jsonify({'error': f'Baileys connection error: {str(e)}'}), 500
            
    else:
        return jsonify({'error': 'Unknown provider'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': f'WhatsApp connection initiated via {provider.title()}',
        'channel': channel.to_dict()
    })


def connect_email(channel, data):
    """Connect Email channel via SendGrid/SMTP"""
    credentials = data.get('credentials', {})
    existing = channel.credentials or {}
    
    # SendGrid
    if credentials.get('api_key') or (existing.get('provider') == 'sendgrid' and existing.get('api_key') and not credentials.get('smtp_host')):
        from_email = credentials.get('from_email') or credentials.get('email_user') or credentials.get('smtp_user') or existing.get('from_email')
        new_creds = {
            'provider': 'sendgrid',
            'from_email': from_email
        }
        
        api_key = credentials.get('api_key')
        if api_key and api_key != '********':
            new_creds['api_key'] = api_key
        elif existing.get('api_key'):
             new_creds['api_key'] = existing.get('api_key')
             
        channel.credentials = new_creds
        channel.email_address = from_email
        channel.update_status(ChannelStatus.CONNECTED, 'Connected via SendGrid')
        
    elif credentials.get('smtp_host') or (existing.get('provider') == 'smtp' and existing.get('smtp_host')) or credentials.get('smtp_user') or credentials.get('email_user'):
        # SMTP/IMAP Credentials
        email_user = credentials.get('email_user') or credentials.get('smtp_user') or existing.get('email_user') or existing.get('smtp_user')
        email_pass = credentials.get('email_pass') or credentials.get('smtp_password') or credentials.get('smtp_pass') or existing.get('email_pass') or existing.get('smtp_password')
        from_email = credentials.get('from_email') or email_user or existing.get('from_email')
        smtp_host = credentials.get('smtp_host') or existing.get('smtp_host') or 'smtp.gmail.com'
        smtp_port = credentials.get('smtp_port') or existing.get('smtp_port') or 587
        
        new_creds = {
            'provider': 'smtp',
            'imap_host': credentials.get('imap_host') or existing.get('imap_host'),
            'imap_port': credentials.get('imap_port') or existing.get('imap_port'),
            'imap_encryption': credentials.get('imap_encryption') or existing.get('imap_encryption', 'tls'),
            'smtp_host': smtp_host,
            'smtp_port': int(smtp_port) if str(smtp_port).isdigit() else 587,
            'smtp_encryption': credentials.get('smtp_encryption') or existing.get('smtp_encryption', 'tls'),
            'email_user': email_user,
            'email_pass': email_pass,
            'from_email': from_email
        }
        
        channel.credentials = new_creds
        channel.email_address = from_email
        channel.update_status(ChannelStatus.CONNECTED, 'Connected via Custom SMTP/IMAP')
    else:
        return jsonify({'error': 'Email credentials required'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': 'Email channel connected',
        'channel': channel.to_dict(include_credentials=False)
    })


def connect_voice(channel, data):
    """Connect Voice channel via Twilio or LiveKit"""
    credentials = data.get('credentials', {})
    provider = data.get('provider', 'twilio')  # Default to twilio for backward compatibility
    
    if provider == 'livekit':
        if credentials.get('livekit_url') and credentials.get('livekit_api_key') and credentials.get('livekit_api_secret'):
            # Save to Channel
            channel.credentials = {
                'provider': 'livekit',
                'livekit_url': credentials['livekit_url'],
                'livekit_api_key': credentials['livekit_api_key'],
                'livekit_api_secret': credentials['livekit_api_secret'],
                'livekit_caller_id': credentials.get('livekit_caller_id')
            }
            channel.phone_number = credentials.get('livekit_caller_id', 'LiveKit VoIP')
            channel.update_status(ChannelStatus.CONNECTED, 'Connected via LiveKit')
            
            # Sync to Company API Keys (for LiveKitService)
            company = channel.company
            if not company.api_keys:
                company.api_keys = {}
            
            company.api_keys['livekit_url'] = credentials['livekit_url']
            company.api_keys['livekit_api_key'] = credentials['livekit_api_key']
            company.api_keys['livekit_api_secret'] = credentials['livekit_api_secret']
            if credentials.get('livekit_caller_id'):
                company.api_keys['livekit_caller_id'] = credentials['livekit_caller_id']
            
            # Also set global telephony provider to LiveKit if not set
            if not company.api_keys.get('telephony_provider'):
                 company.api_keys['telephony_provider'] = 'livekit'
            
            # Trigger updates
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(company, "api_keys")
            
        else:
            return jsonify({'error': 'LiveKit URL, API Key, and Secret are required'}), 400

    elif provider == 'twilio':
        if credentials.get('account_sid'):
            # Merge
            existing = channel.credentials or {}
            new_creds = {
                'provider': 'twilio',
                'account_sid': credentials.get('account_sid'),
                'phone_number': credentials.get('phone_number')
            }
            
            auth_token = credentials.get('auth_token')
            if auth_token and auth_token != '********':
                new_creds['auth_token'] = auth_token
            elif existing.get('auth_token'):
                new_creds['auth_token'] = existing.get('auth_token')
                
            channel.credentials = new_creds
            channel.phone_number = credentials.get('phone_number')
            channel.update_status(ChannelStatus.CONNECTED, 'Connected via Twilio')
            
            # Sync to Company API Keys
            company = channel.company
            if not company.api_keys: company.api_keys = {}
                
            company.api_keys['twilio_sid'] = new_creds['account_sid']
            if new_creds.get('auth_token'):
                company.api_keys['twilio_token'] = new_creds['auth_token']
            if new_creds.get('phone_number'):
                company.api_keys['twilio_voice_number'] = new_creds['phone_number']
                
            # Also set global telephony provider to Twilio if not set
            if not company.api_keys.get('telephony_provider'):
                 company.api_keys['telephony_provider'] = 'twilio'
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(company, "api_keys")
            
        else:
            return jsonify({'error': 'Twilio credentials required'}), 400
            
    else:
         return jsonify({'error': 'Unknown provider'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': f'Voice channel connected via {provider.title()}',
        'channel': channel.to_dict()
    })


def connect_sms(channel, data):
    """Connect SMS channel via Twilio"""
    credentials = data.get('credentials', {})
    
    if credentials.get('account_sid'):
        # Merge
        existing = channel.credentials or {}
        new_creds = {
            'account_sid': credentials.get('account_sid'),
            'phone_number': credentials.get('phone_number')
        }
        
        auth_token = credentials.get('auth_token')
        if auth_token and auth_token != '********':
            new_creds['auth_token'] = auth_token
        elif existing.get('auth_token'):
            new_creds['auth_token'] = existing.get('auth_token')

        channel.credentials = new_creds
        channel.phone_number = credentials.get('phone_number')
        channel.update_status(ChannelStatus.CONNECTED, 'Connected via Twilio')
    else:
        return jsonify({'error': 'Twilio credentials required'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': 'SMS channel connected',
        'channel': channel.to_dict(include_credentials=False)
    })



# =====================================================
# BAILEYS WHATSAPP ENDPOINTS
# =====================================================

@channels_bp.route('/whatsapp/qr', methods=['GET'])
@jwt_required()
def get_whatsapp_qr():
    """Get QR code SVG for Baileys WhatsApp session"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        from services.whatsapp_service import WhatsAppBaileysService
        service = WhatsAppBaileysService(str(company.id))
        
        # Check status first
        status = service.get_status()
        if status.get('connected'):
            return jsonify({'status': 'connected', 'message': 'Already connected, no QR needed'})
        
        # Get QR
        qr_svg = service.get_qr()
        if qr_svg:
            
            return Response(content=qr_svg, media_type='image/svg+xml')
        else:
            return jsonify({'status': 'waiting', 'message': 'QR not ready yet, please wait...'}), 202
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/whatsapp/status', methods=['GET'])
@jwt_required()
def get_whatsapp_status():
    """Get WhatsApp channel connection status (Meta, Twilio, or Baileys)"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    # First check database channel status (supports Meta Cloud API, Twilio, and direct providers)
    channel = Channel.query.filter_by(
        company_id=company.id,
        type=ChannelType.WHATSAPP
    ).first()

    creds = channel.credentials or {} if channel else {}
    provider = creds.get('provider', 'meta')

    # If channel is using Baileys, always query live microservice status to reflect reality
    if channel and provider == 'baileys':
        try:
            from services.whatsapp_service import WhatsAppBaileysService
            service = WhatsAppBaileysService(str(company.id))
            status = service.get_status()
            is_live_connected = status.get('connected', False)
            if is_live_connected:
                if channel.status != ChannelStatus.CONNECTED:
                    channel.update_status(ChannelStatus.CONNECTED, 'Connected via Baileys')
                    db.session.commit()
                return jsonify({
                    'connected': True,
                    'provider': 'baileys',
                    'phone': channel.phone_number,
                    'status': 'connected'
                })
            else:
                if channel.status == ChannelStatus.CONNECTED:
                    channel.update_status(ChannelStatus.DISCONNECTED, 'Disconnected')
                    db.session.commit()
                return jsonify({
                    'connected': False,
                    'provider': 'baileys',
                    'status': 'disconnected'
                })
        except Exception as e:
            pass

    if channel and channel.status == ChannelStatus.CONNECTED:
        phone = channel.phone_number or creds.get('phone_number')
        return jsonify({
            'connected': True,
            'provider': provider,
            'phone': phone,
            'verified_name': creds.get('verified_name', ''),
            'status': 'connected'
        })

    try:
        from services.whatsapp_service import WhatsAppBaileysService
        service = WhatsAppBaileysService(str(company.id))
        status = service.get_status()
        
        # If connected, update channel status in DB
        if status.get('connected'):
            if channel and channel.status != ChannelStatus.CONNECTED:
                channel.update_status(ChannelStatus.CONNECTED, 'Connected via Baileys')
                db.session.commit()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e), 'connected': False}), 500


@channels_bp.route('/whatsapp/disconnect', methods=['POST'])
@jwt_required()
def disconnect_whatsapp_baileys():
    """Disconnect Baileys WhatsApp session"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        from services.whatsapp_service import WhatsAppBaileysService
        service = WhatsAppBaileysService(str(company.id))
        result = service.logout()
        
        # Update channel in DB
        channel = Channel.query.filter_by(
            company_id=company.id,
            type=ChannelType.WHATSAPP
        ).first()
        if channel:
            channel.update_status(ChannelStatus.DISCONNECTED, 'Logged out')
            channel.credentials = {}
            db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/types', methods=['GET'])
@jwt_required()
def get_channel_types():
    """Get available channel types"""
    return jsonify({
        'types': [
            {
                'id': 'whatsapp',
                'name': 'WhatsApp',
                'description': 'Send and receive WhatsApp messages',
                'icon': 'whatsapp',
                'requires': ['Twilio Account']
            },
            {
                'id': 'voice',
                'name': 'Voice Calls',
                'description': 'Handle inbound and outbound voice calls',
                'icon': 'phone',
                'requires': ['Twilio Account', 'Phone Number']
            },
            {
                'id': 'sms',
                'name': 'SMS',
                'description': 'Send and receive SMS messages',
                'icon': 'message-square',
                'requires': ['Twilio Account', 'Phone Number']
            },
            {
                'id': 'email',
                'name': 'Email',
                'description': 'Send and receive emails',
                'icon': 'mail',
                'requires': ['SendGrid API Key or SMTP']
            },
            {
                'id': 'telegram',
                'name': 'Telegram',
                'description': 'Connect a Telegram Bot',
                'icon': 'send',
                'requires': ['Bot Token']
            },
            {
                'id': 'webchat',
                'name': 'Web Chat',
                'description': 'Embed chat widget on your website',
                'icon': 'message-circle',
                'requires': ['Script Installation']
            }
        ]
    })


def connect_telegram(channel, data):
    """Connect Telegram Bot"""
    credentials = data.get('credentials', {})
    token = (
        credentials.get('telegram_token') or 
        credentials.get('bot_token') or 
        credentials.get('token') or
        data.get('token')
    )
    
    # If no new token provided, try to use existing one
    if not token and channel.credentials:
        token = channel.credentials.get('telegram_token') or channel.credentials.get('bot_token')
    
    if not token:
        return jsonify({'error': 'Telegram Bot Token required'}), 400
        
    try:
        token = token.strip()
        # Verify Token with Telegram API
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        if resp.status_code != 200:
             return jsonify({'error': 'Token de Telegram inválido. Verifica el token con @BotFather.'}), 400
        
        bot_data = resp.json().get('result', {})
        bot_username = bot_data.get('username')
        
        # Set Webhook - Telegram strictly requires a valid HTTPS URL
        base_url = 'https://api.aikrofy.com'
        webhook_url = f"{base_url}/api/webhooks/telegram/{channel.id}"
        
        # Call SetWebhook
        try:
            wh_resp = requests.post(f"https://api.telegram.org/bot{token}/setWebhook", json={'url': webhook_url}, timeout=10)
            if wh_resp.status_code != 200:
                 print(f"Warning: SetWebhook failed: {wh_resp.text}")
            else:
                 print(f"Telegram Webhook successfully registered: {webhook_url}")
        except Exception as wh_e:
            print(f"Warning: SetWebhook network error: {wh_e}")
             
        channel.credentials = {
            'provider': 'telegram',
            'telegram_token': token,
            'bot_token': token,
            'bot_username': bot_username,
            'webhook_url': webhook_url
        }
        channel.update_status(ChannelStatus.CONNECTED, f"Connected as @{bot_username}")
        
    except Exception as e:
         return jsonify({'error': f"Telegram connection error: {str(e)}"}), 500
    
    db.session.commit()
    return jsonify({
        'message': f'Telegram connected as @{bot_username}',
        'channel': channel.to_dict(include_credentials=False)
    })


def connect_webchat(channel, data):
    """Connect Web Chat Widget"""
    # Generate unique ID for this widget instance
    if not channel.credentials or 'widget_id' not in channel.credentials:
        widget_id = str(uuid.uuid4())
        channel.credentials = {'widget_id': widget_id}
    
    channel.update_status(ChannelStatus.CONNECTED, 'Widget Ready')
    db.session.commit()
    
    return jsonify({
        'message': 'Web Chat Widget generated',
        'channel': channel.to_dict(include_credentials=True)
    })


@channels_bp.route('/webchat/ping', methods=['POST'])
def webchat_ping():
    """
    Public (or semi-public) endpoint for the widget to signal it's active.
    Updates the channel status to CONNECTED.
    """
    data = request.get_json()
    widget_id = data.get('widget_id')
    
    if not widget_id:
        return jsonify({'error': 'Widget ID required'}), 400
        
    # Find channel by widget_id in credentials
    # For JSON fields in modern SQLAlchemy, this works across most DBs
    channels = Channel.query.filter(Channel.type == ChannelType.WEBCHAT).all()
    channel = next((c for c in channels if c.credentials and c.credentials.get('widget_id') == widget_id), None)
    
    if not channel:
        return jsonify({'error': 'Invalid Widget ID'}), 404
        
    # Resolve active agent name configured by the company
    from models.agent import Agent
    active_agent = Agent.query.filter_by(company_id=channel.company_id, is_active=True).order_by(Agent.priority.desc()).first()
    agent_name = active_agent.name if active_agent else (getattr(channel.company, 'agent_name', None) or channel.company.name or 'Asistente')
    company_name = channel.company.name if channel.company else 'Empresa'
    logo_url = (getattr(channel.company, 'logo_url', None) or (channel.company.api_keys.get('logo_url') if channel.company and channel.company.api_keys else None)) if channel.company else None
    agent_gender = channel.company.agent_gender.value if channel.company and channel.company.agent_gender else 'neutral'
    voice_model = channel.company.voice_model if channel.company else None

    return jsonify({
        'status': 'ok',
        'company_name': company_name,
        'agent_name': agent_name,
        'brand_name': company_name,
        'logo_url': logo_url,
        'agent_gender': agent_gender,
        'voice_model': voice_model
    })


@channels_bp.route('/webchat/telemetry', methods=['POST'])
def webchat_telemetry():
    """
    Receives real-time browser execution telemetry, DOM action verification,
    and client inspection events from the client widget for live audit.
    """
    data = request.get_json() or {}
    widget_id = data.get('widget_id')
    event_type = data.get('event_type')
    action = data.get('action')
    details = data.get('details', {})
    
    print(f"[CLIENT LIVE TELEMETRY] Widget: {widget_id} | Event: {event_type} | Action: {action} | Details: {details}")
    return jsonify({'status': 'logged', 'received': True}), 200


# =====================================================
# PARAMETERIZED / DYNAMIC ROUTES (Defined at the end to prevent shadowing static routes)
# =====================================================

@channels_bp.route('/<int:channel_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_channel_by_id(channel_id):
    """Update channel credentials/status by ID"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    channel = Channel.query.filter_by(id=channel_id, company_id=company.id).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    data = request.get_json() or {}
    
    # If channel type specific credentials are provided, route to the proper connect handler
    if channel.type == ChannelType.EMAIL:
        return connect_email(channel, data)
    elif channel.type == ChannelType.TELEGRAM:
        return connect_telegram(channel, data)
    elif channel.type == ChannelType.WHATSAPP:
        return connect_whatsapp(channel, data)
    elif channel.type == ChannelType.VOICE:
        return connect_voice(channel, data)
    elif channel.type == ChannelType.SMS:
        return connect_sms(channel, data)
    elif channel.type == ChannelType.WEBCHAT:
        return connect_webchat(channel, data)
    else:
        if 'credentials' in data:
            channel.credentials = data.get('credentials')
        if 'name' in data:
            channel.name = data.get('name')
        if 'status' in data:
            try:
                channel.status = ChannelStatus(data.get('status'))
            except:
                pass
        db.session.commit()
        return jsonify({'message': 'Channel updated', 'channel': channel.to_dict(include_credentials=False)})


@channels_bp.route('/<int:channel_id>', methods=['DELETE'])
@jwt_required()
def delete_channel(channel_id):
    """Disconnect / delete a channel by ID"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    channel = Channel.query.filter_by(id=channel_id, company_id=company.id).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    try:
        channel.update_status(ChannelStatus.DISCONNECTED, 'Manually disconnected')
        channel.credentials = {}
        db.session.commit()
        return jsonify({'message': 'Channel disconnected', 'channel': channel.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/<channel_type>', methods=['GET'])
@jwt_required()
def get_channel(channel_type):
    """Get specific channel details"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        ctype = ChannelType(channel_type)
    except ValueError:
        return jsonify({'error': 'Invalid channel type'}), 400
    
    channel = Channel.query.filter_by(company_id=company.id, type=ctype).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    return jsonify({'channel': channel.to_dict(include_credentials=True)})


@channels_bp.route('/<channel_type>/disconnect', methods=['POST'])
@jwt_required()
def disconnect_channel(channel_type):
    """Disconnect a channel"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        ctype = ChannelType(channel_type)
    except ValueError:
        return jsonify({'error': 'Invalid channel type'}), 400
    
    channel = Channel.query.filter_by(company_id=company.id, type=ctype).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    channel.update_status(ChannelStatus.DISCONNECTED, 'Manually disconnected')
    channel.credentials = {}
    db.session.commit()
    
    return jsonify({
        'message': 'Channel disconnected',
        'channel': channel.to_dict()
    })


@channels_bp.route('/<channel_type>/test', methods=['POST'])
@jwt_required()
def test_channel(channel_type):
    """Test channel connection"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    try:
        ctype = ChannelType(channel_type)
    except ValueError:
        return jsonify({'error': 'Invalid channel type'}), 400
    
    channel = Channel.query.filter_by(company_id=company.id, type=ctype).first()
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    
    if channel.status != ChannelStatus.CONNECTED:
        return jsonify({'error': 'Channel is not connected'}), 400
    
    # Channel testing by channel type
    test_result = {'status': 'ok', 'message': f'Channel {ctype.value} is active and reachable'}
    try:
        if ctype == ChannelType.WHATSAPP:
            from services.whatsapp_service import WhatsAppBaileysService
            baileys = WhatsAppBaileysService(str(company.id))
            status_data = baileys.get_status()
            if not status_data.get('connected'):
                return jsonify({
                    'status': 'error',
                    'error': 'WhatsApp session disconnected in Baileys server',
                    'details': status_data
                }), 502
            test_result['details'] = status_data

        elif ctype == ChannelType.TELEGRAM:
            token = (channel.credentials or {}).get('bot_token')
            if not token:
                return jsonify({'status': 'error', 'error': 'Missing Telegram bot_token in channel credentials'}), 400
            resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
            data = resp.json()
            if not data.get('ok'):
                return jsonify({'status': 'error', 'error': 'Telegram getMe failed', 'details': data}), 502
            test_result['details'] = {'bot_username': data.get('result', {}).get('username')}

        elif ctype == ChannelType.WEBCHAT:
            test_result['details'] = {'active': True, 'webchat_id': channel.id}

        elif ctype in (ChannelType.VOICE, ChannelType.SMS):
            # Check Twilio credentials if available
            creds = channel.credentials or {}
            sid = creds.get('account_sid')
            auth_token = creds.get('auth_token')
            if sid and auth_token:
                resp = requests.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json", auth=(sid, auth_token), timeout=10)
                if resp.status_code != 200:
                    return jsonify({'status': 'error', 'error': 'Twilio credentials verification failed', 'code': resp.status_code}), 502
                test_result['details'] = {'account_status': resp.json().get('status')}

    except Exception as test_err:
        return jsonify({
            'status': 'error',
            'error': f'Failed to test channel {ctype.value}: {str(test_err)}'
        }), 500

    channel.last_activity = datetime.utcnow()
    db.session.commit()

    return jsonify(test_result)

