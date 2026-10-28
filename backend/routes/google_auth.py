from routing import APIRouter, current_app, get_jwt_identity, jsonify, jwt_required, redirect, request, session, url_for


from services.google_service import GoogleService
from models.user import User
from extensions import db
from utils.oauth_state_store import oauth_state_store
import os

google_auth_bp = APIRouter('google_auth', __name__, url_prefix='/api/auth/google')

@google_auth_bp.before_request
def before_request():
    """Gemini Rule B.1: Preventive rollback at entry points"""
    db.session.rollback()

@google_auth_bp.route('/login')
@jwt_required()
def login():
    """Start Google OAuth flow"""
    # 1. Get current user
    try:
        user_id = int(get_jwt_identity())
    except Exception as e:
        print(f"DEBUG: Google Auth Login - Error getting identity: {e}")
        return jsonify({'error': 'Invalid user identity'}), 401
    
    # 2. Configure redirect uri
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'https://app.aikrofy.com/api/auth/google/callback')
    
    # 3. Create flow
    flow = GoogleService.create_flow(redirect_uri=redirect_uri)
    
    # 4. Generate authorization url
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent to get refresh_token
    )
    
    # 5. Store state, user_id, and code_verifier (for PKCE) in persistent OAuth state store
    next_url = request.args.get('next')
    code_verifier = getattr(flow, 'code_verifier', None)
    oauth_state_store.set(state, {
        'user_id': user_id,
        'next_url': next_url,
        'code_verifier': code_verifier
    })
    print(f"DEBUG: Google Auth Login - Stored state={state[:20]}... for user_id={user_id} (has_code_verifier={bool(code_verifier)})")
    
    return jsonify({
        'url': authorization_url,
        'authorization_url': authorization_url,
        'data': {
            'authorization_url': authorization_url,
            'url': authorization_url
        }
    })

@google_auth_bp.route('/callback')
def callback():
    """Handle Google OAuth callback"""
    # 1. Verify state
    state = request.args.get('state')
    
    if not state:
        print("DEBUG: Google Auth Callback - Missing state parameter")
        return redirect(f"{os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')}/channels?google_error=missing_state")
    
    # 2. Retrieve and consume state from store
    state_data = oauth_state_store.pop(state)
    
    if not state_data:
        print(f"DEBUG: Google Auth Callback - Invalid or expired state: {state[:20]}...")
        return redirect(f"{os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')}/channels?google_error=invalid_state")
    
    user_id = state_data.get('user_id')
    next_url = state_data.get('next_url')
    code_verifier = state_data.get('code_verifier')
    
    if not user_id:
        print("DEBUG: Google Auth Callback - No user_id in state data")
        return redirect(f"{os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')}/channels?google_error=session_lost")

    # 3. Get redirect URI again
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'https://app.aikrofy.com/api/auth/google/callback')
    
    try:
        # 4. Create flow and restore code_verifier for PKCE validation
        flow = GoogleService.create_flow(redirect_uri=redirect_uri)
        if code_verifier:
            flow.code_verifier = code_verifier
        
        # Fix: When behind Nginx reverse proxy, request.url may have http:// scheme
        # but Google OAuth requires the exact redirect_uri (https://).
        # We reconstruct the authorization_response URL using the configured redirect URI.
        authorization_response = str(request.url)
        if authorization_response.startswith('http://') and redirect_uri.startswith('https://'):
            authorization_response = 'https://' + authorization_response[len('http://'):]
            print(f"DEBUG: Google Auth Callback - Fixed scheme in authorization_response")
        
        flow.fetch_token(authorization_response=authorization_response)

        
        credentials = flow.credentials
        
        # 5. Get user from DB
        user = User.query.get(user_id)
        
        if not user:
             print(f"DEBUG: Google Auth Callback - User {user_id} not found")
             return redirect(f"{os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')}/channels?google_error=user_not_found")
             
        # 6. Convert credentials to json
        creds_json = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else GoogleService.SCOPES
        }
        
        user.google_credentials = creds_json
        
        # 7. Auto-Promote to Company Level (so Agent can use it immediately)
        if user.company:
            company = user.company
            if company.api_keys is None:
                company.api_keys = {}
            
            # Create copy to ensure mutation is tracked
            keys = company.api_keys.copy()
            keys['google_oauth_credentials'] = creds_json
            keys['google_auth_mode'] = 'oauth'
            
            company.api_keys = keys
        
        db.session.commit()
        print(f"DEBUG: Google Auth Callback - Successfully connected Google for user {user.email}")
        
        # 8. Dynamic Redirect
        frontend_url = os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')
        
        if next_url:
             # If next_url is relative (starts with /), append to frontend_url
             if next_url.startswith('/'):
                 return redirect(f"{frontend_url}{next_url}?google_connected=true")
             else:
                 return redirect(f"{next_url}?google_connected=true")
        
        # Default fallback
        return redirect(f"{frontend_url}/channels?google_connected=true")
        
    except Exception as e:
        print(f"DEBUG: Google Auth Callback - Error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(f"{os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')}/channels?google_error=oauth_failed")

@google_auth_bp.route('/status')
@jwt_required()
def status():
    """Check if user has Google connected"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
    except Exception as e:
        print(f"DEBUG: Google Auth Status - Error: {e}")
        return jsonify({'error': 'Invalid user identity'}), 401
    
    connected = False
    calendar_status = "Disconnected"
    
    if user and user.google_credentials:
        # Try initializing service to check validity
        try:
            print(f"DEBUG: Checking Google Auth Status for User {user.email}")
            service = GoogleService(user)
            
            if service.creds:
                 print(f"DEBUG: Creds found. Valid: {service.creds.valid}, Expired: {service.creds.expired}, Has Refresh Token: {bool(service.creds.refresh_token)}")
                 if service.creds.expired and service.creds.refresh_token:
                      try:
                          from google.auth.transport.requests import Request
                          service.creds.refresh(Request())
                          print("DEBUG: Token refreshed successfully")
                      except Exception as re:
                          print(f"DEBUG: Token refresh failed: {re}")
            
            if service.is_authenticated():
                connected = True
                calendar_status = "Connected"
            else:
                print("DEBUG: is_authenticated() returned False")
                
        except Exception as e:
            print(f"DEBUG: Google Auth Status - Exception: {e}")
            import traceback
            traceback.print_exc()
            
    return jsonify({
        'connected': connected,
        'services': {
            'calendar': calendar_status,
            'sheets': calendar_status  # Using same scope for now
        }
    })

@google_auth_bp.route('/disconnect', methods=['POST'])
@jwt_required()
def disconnect():
    """Remove Google credentials"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
    except Exception as e:
        print(f"DEBUG: Google Auth Disconnect - Error: {e}")
        return jsonify({'error': 'Invalid user identity'}), 401
    
    if user:
        user.google_credentials = None
        
        # Also clear company level keys if they exist
        if user.company:
            company = user.company
            if company.api_keys:
                keys = dict(company.api_keys)
                keys.pop('google_oauth_credentials', None)
                keys.pop('google_calendar_id', None)
                keys.pop('google_sheet_id', None)
                keys.pop('google_auth_mode', None)
                company.api_keys = keys
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(company, "api_keys")

        db.session.commit()
        return jsonify({'status': 'disconnected'})
    
    return jsonify({'error': 'User not found'}), 404

@google_auth_bp.route('/calendars', methods=['GET'])
@jwt_required()
def list_calendars():
    """List available calendars"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        service = GoogleService(user)
        if not service.is_authenticated():
            return jsonify({'error': 'Google not connected'}), 400
            
        calendars = service.list_calendars()
        
        # Format for frontend
        options = [{'id': c['id'], 'name': c.get('summary', 'Unknown')} for c in calendars]
        return jsonify({'calendars': options})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@google_auth_bp.route('/sheets', methods=['GET'])
@jwt_required()
def list_sheets():
    """List available sheets"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        service = GoogleService(user)
        if not service.is_authenticated():
            return jsonify({'error': 'Google not connected'}), 400
            
        sheets = service.list_sheets()
        
        # Format for frontend
        options = [{'id': s['id'], 'name': s.get('name', 'Unknown')} for s in sheets]
        return jsonify({'sheets': options})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@google_auth_bp.route('/config', methods=['POST'])
@jwt_required()
def save_config():
    """
    Save selected Google resources and promote user credentials to Company
    This allows agents (backend) to use this user's connection.
    """
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        company = user.company
        if not company:
            return jsonify({'error': 'User has no company'}), 400

        # Support both user.google_credentials and company.api_keys['google_oauth_credentials']
        user_creds = user.google_credentials
        company_creds = (company.api_keys or {}).get('google_oauth_credentials') if company.api_keys else None
        active_creds = user_creds or company_creds

        if not active_creds:
            return jsonify({'error': 'Google not connected'}), 400

        data = request.get_json(silent=True) or request.json or {}
        calendar_id = data.get('calendar_id')
        sheet_id = data.get('sheet_id')

        # Promote credentials to Company level
        keys = dict(company.api_keys or {})
        keys['google_oauth_credentials'] = active_creds
        
        if calendar_id:
            keys['google_calendar_id'] = calendar_id
            
        if sheet_id:
            keys['google_sheet_id'] = sheet_id
            
        # Signal that we are using OAuth now, not Service Account
        keys['google_auth_mode'] = 'oauth'
        
        company.api_keys = keys
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(company, "api_keys")
        db.session.commit()
        
        return jsonify({'status': 'saved', 'message': 'Google integration configured for Company', 'calendar_id': calendar_id})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
