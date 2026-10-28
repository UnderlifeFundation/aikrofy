"""
Meeting and Calendar Integrations API Routes
Manages connections and preferences for Google Meet, Microsoft Teams, and Zoom.
"""
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
import logging
from extensions import db
from models.user import User
from models.company import Company
from services.meeting_service import MeetingService
from services.google_service import GoogleService

logger = logging.getLogger(__name__)

meetings_bp = APIRouter('meetings', __name__, url_prefix='/api/integrations/meetings')


def get_user_and_company():
    """Helper to fetch authenticated user and active company"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or not user.company:
            return None, None
        return user, user.company
    except Exception as e:
        logger.error(f"[MEETINGS_API] Auth error: {e}")
        return None, None


@meetings_bp.route('/status', methods=['GET'])
@jwt_required()
def get_meetings_status():
    """
    Get connection status and active provider across Google Meet, Teams, and Zoom.
    """
    user, company = get_user_and_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    api_keys = company.api_keys or {}
    google_creds = api_keys.get('google_oauth_credentials') or (user.google_credentials if user else None)
    
    # Check Google authentication
    google_connected = False
    if google_creds:
        try:
            gs = GoogleService(user, company=company)
            google_connected = gs.is_authenticated()
        except Exception:
            google_connected = bool(google_creds.get('refresh_token') or google_creds.get('token'))

    # Check Zoom connection
    zoom_connected = bool(
        api_keys.get('zoom_credentials') or 
        (api_keys.get('zoom_client_id') and api_keys.get('zoom_client_secret') and api_keys.get('zoom_account_id')) or
        api_keys.get('zoom_access_token')
    )

    # Check Teams connection
    teams_connected = bool(
        api_keys.get('teams_credentials') or
        (api_keys.get('teams_client_id') and api_keys.get('teams_client_secret')) or
        api_keys.get('teams_access_token')
    )

    active_provider = MeetingService.get_configured_provider(company)

    return jsonify({
        'active_provider': active_provider,
        'providers': {
            'google': {
                'name': 'Google Meet & Calendar',
                'connected': google_connected,
                'calendar_id': api_keys.get('google_calendar_id', 'primary')
            },
            'teams': {
                'name': 'Microsoft Teams',
                'connected': teams_connected,
                'tenant_id': api_keys.get('teams_tenant_id')
            },
            'zoom': {
                'name': 'Zoom',
                'connected': zoom_connected,
                'account_id': api_keys.get('zoom_account_id')
            }
        }
    })


@meetings_bp.route('/provider', methods=['POST'])
@jwt_required()
def set_active_provider():
    """
    Set active meeting provider ('google', 'teams', 'zoom')
    """
    user, company = get_user_and_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    data = request.get_json() or {}
    provider = data.get('provider')
    if provider not in ['google', 'teams', 'zoom']:
        return jsonify({'error': 'Proveedor no soportado. Elija google, teams o zoom'}), 400

    keys = dict(company.api_keys or {})
    keys['meeting_provider'] = provider
    company.api_keys = keys

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "api_keys")
    db.session.commit()

    return jsonify({'success': True, 'active_provider': provider})


@meetings_bp.route('/zoom/connect', methods=['POST'])
@jwt_required()
def connect_zoom():
    """
    Connect Zoom via Server-to-Server OAuth credentials or direct access token
    """
    user, company = get_user_and_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    data = request.get_json() or {}
    account_id = data.get('account_id', '').strip()
    client_id = data.get('client_id', '').strip()
    client_secret = data.get('client_secret', '').strip()
    access_token = data.get('access_token', '').strip()

    if not access_token and not (account_id and client_id and client_secret):
        return jsonify({'error': 'Debe proporcionar (Account ID, Client ID y Client Secret) o un Access Token directo'}), 400

    keys = dict(company.api_keys or {})
    if account_id: keys['zoom_account_id'] = account_id
    if client_id: keys['zoom_client_id'] = client_id
    if client_secret: keys['zoom_client_secret'] = client_secret
    if access_token: keys['zoom_access_token'] = access_token
    keys['meeting_provider'] = 'zoom'

    company.api_keys = keys
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "api_keys")
    db.session.commit()

    # Validate token acquisition
    token = MeetingService.get_zoom_access_token(company)
    if not token:
        return jsonify({'error': 'Credenciales de Zoom inválidas o no se pudo generar el token'}), 400

    return jsonify({'success': True, 'message': 'Zoom conectado exitosamente'})


@meetings_bp.route('/teams/connect', methods=['POST'])
@jwt_required()
def connect_teams():
    """
    Connect Microsoft Teams via Entra ID / Microsoft Graph credentials
    """
    user, company = get_user_and_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    data = request.get_json() or {}
    tenant_id = data.get('tenant_id', 'common').strip()
    client_id = data.get('client_id', '').strip()
    client_secret = data.get('client_secret', '').strip()
    access_token = data.get('access_token', '').strip()

    if not access_token and not (client_id and client_secret):
        return jsonify({'error': 'Debe proporcionar Client ID y Client Secret de Azure / Teams'}), 400

    keys = dict(company.api_keys or {})
    if tenant_id: keys['teams_tenant_id'] = tenant_id
    if client_id: keys['teams_client_id'] = client_id
    if client_secret: keys['teams_client_secret'] = client_secret
    if access_token: keys['teams_access_token'] = access_token
    keys['meeting_provider'] = 'teams'

    company.api_keys = keys
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "api_keys")
    db.session.commit()

    return jsonify({'success': True, 'message': 'Microsoft Teams conectado exitosamente'})


@meetings_bp.route('/disconnect', methods=['POST'])
@jwt_required()
def disconnect_meetings():
    """
    Disconnect provider or clear meetings settings
    """
    user, company = get_user_and_company()
    if not company:
        return jsonify({'error': 'Empresa no encontrada'}), 404

    data = request.get_json() or {}
    target_provider = data.get('provider')  # 'google', 'zoom', 'teams', or all

    keys = dict(company.api_keys or {})
    if target_provider == 'zoom' or not target_provider:
        keys.pop('zoom_account_id', None)
        keys.pop('zoom_client_id', None)
        keys.pop('zoom_client_secret', None)
        keys.pop('zoom_access_token', None)
        keys.pop('zoom_credentials', None)

    if target_provider == 'teams' or not target_provider:
        keys.pop('teams_tenant_id', None)
        keys.pop('teams_client_id', None)
        keys.pop('teams_client_secret', None)
        keys.pop('teams_access_token', None)
        keys.pop('teams_credentials', None)

    if target_provider == 'google' or not target_provider:
        keys.pop('google_oauth_credentials', None)
        keys.pop('google_calendar_id', None)
        keys.pop('google_auth_mode', None)
        if user:
            user.google_credentials = None

    company.api_keys = keys
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "api_keys")
    db.session.commit()

    return jsonify({'success': True, 'message': 'Desconectado exitosamente'})
