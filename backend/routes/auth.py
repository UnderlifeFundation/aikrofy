from routing import APIRouter, create_access_token, create_refresh_token, current_app, get_jwt_identity, jsonify, jwt_required, request, verify_jwt_in_request
"""
Authentication Routes
"""
from datetime import datetime, timedelta
import logging

(
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, verify_jwt_in_request
)
import requests as py_requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import uuid
import os
from extensions import db
from models.user import User, UserRole
from models.company import Company
from models.platform_config import PlatformConfig
# [HASH TABLE OPT] Estructura 5: Cache in-memory Redis para O(1) lookups
from services.cache_service import CacheService

logger = logging.getLogger(__name__)

# Sesión HTTP persistente para verificación de tokens de Google con TLS connection pooling
_google_http_session = py_requests.Session()
_google_auth_request = google_requests.Request(session=_google_http_session)

# TTLs de caché
_CACHE_TTL_PLATFORM_CONFIG = 300   # 5 min — PlatformConfig es singleton casi inmutable
_CACHE_TTL_USER_SESSION    = 300   # 5 min — datos de sesión post-login
_CACHE_TTL_USER_BY_EMAIL   = 300   # 5 min — lookup por email


def _get_platform_config_cached():
    """[HASH TABLE] PlatformConfig singleton cacheado en Redis. Evita query SQL en cada login."""
    key = "platform_config:singleton"
    cached = CacheService.get(key)
    if cached:
        # Reconstruir objeto liviano desde cache
        config_obj = type('PlatformConfigCache', (), cached)()
        return config_obj
    config = PlatformConfig.get_config()
    CacheService.set(key, {
        'beta_mode': config.beta_mode,
        'maintenance_mode': config.maintenance_mode,
    }, ttl=_CACHE_TTL_PLATFORM_CONFIG)
    return config


def _get_user_by_email_cached(email: str):
    """[HASH TABLE] User lookup por email cacheado en Redis. Evita query SQL en cada Google login."""
    key = f"user:email:{email}"
    cached = CacheService.get(key)
    if cached:
        return User.query.get(cached['id'])
    user = User.query.filter_by(email=email).first()
    if user:
        CacheService.set(key, {'id': user.id}, ttl=_CACHE_TTL_USER_BY_EMAIL)
    return user


def _cache_user_session(user, company):
    """[HASH TABLE] Almacena user+company dict en Redis indexado por user.id.
    Permite que GET /api/auth/me sea O(1) sin query SQL."""
    user_dict = user.to_dict()
    company_dict = company.to_dict() if company else None
    payload = {'user': user_dict, 'company': company_dict}
    CacheService.set(f"user:session:{user.id}", payload, ttl=_CACHE_TTL_USER_SESSION)
    return user_dict, company_dict


def _invalidate_user_cache(user):
    """[HASH TABLE] Invalida entradas de caché al mutar datos del usuario."""
    CacheService.delete(f"user:email:{user.email}")
    CacheService.delete(f"user:session:{user.id}")

auth_bp = APIRouter('auth', __name__)

@auth_bp.before_request
def before_request():
    """Gemini Rule B.1: Preventive rollback at entry points"""
    db.session.rollback()


@auth_bp.route('/debug-token', methods=['GET'])
def debug_token():
    """Debug endpoint to check token"""
    
    auth_header = request.headers.get('Authorization', 'No Authorization header')
    jwt_secret = current_app.config.get('JWT_SECRET_KEY', 'NOT SET')
    
    # Show first 10 chars of secret for debugging
    secret_preview = jwt_secret[:10] + '...' if len(jwt_secret) > 10 else jwt_secret
    
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return jsonify({
            'header_received': auth_header,
            'user_id': user_id,
            'status': 'valid',
            'jwt_secret_preview': secret_preview
        })
    except Exception as e:
        return jsonify({
            'header_received': auth_header,
            'error': str(e),
            'error_type': type(e).__name__,
            'status': 'invalid',
            'jwt_secret_preview': secret_preview
        }), 401


@auth_bp.route('/debug-create-token', methods=['GET'])
def debug_create_token():
    """Debug endpoint to create and immediately verify a test token"""
    
    
    jwt_secret = current_app.config.get('JWT_SECRET_KEY', 'NOT SET')
    secret_preview = jwt_secret[:10] + '...' if len(jwt_secret) > 10 else jwt_secret
    
    # Create a test token
    test_token = create_access_token(data={"sub": "999"})
    
    # Try to verify it immediately
    try:
        # Manually decode to check
        import jwt as pyjwt
        decoded = pyjwt.decode(test_token, jwt_secret, algorithms=['HS256'])
        return jsonify({
            'test_token': test_token[:50] + '...',
            'decoded': decoded,
            'jwt_secret_preview': secret_preview,
            'status': 'Token created and verified successfully'
        })
    except Exception as e:
        return jsonify({
            'test_token': test_token[:50] + '...',
            'error': str(e),
            'jwt_secret_preview': secret_preview,
            'status': 'Token verification failed'
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user and company"""
    config = PlatformConfig.get_config()
    data = request.get_json()
    
    # Validate required fields
    required = ['email', 'password', 'name', 'company_name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    email = data['email'].strip().lower()

    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Business Category & Courtesy Credit assignment (Fundación Underlife Initiative)
    raw_category = (data.get('business_category') or 'emprendimiento').strip().lower()
    valid_categories = {'emprendimiento', 'micro_negocio', 'pyme', 'enterprise', 'community'}
    business_category = raw_category if raw_category in valid_categories else 'emprendimiento'

    # In beta mode, automatic courtesy access is granted to small business and open-core community members
    if config.beta_mode and not data.get('bypass_beta', True):
        return jsonify({
            'error': 'BETA_MODE_ACTIVE',
            'is_waitlist': True,
            'message': 'Actualmente nos encontramos en fase Beta privada por invitación. Completa nuestro formulario de descubrimiento para unirte a la lista de espera.'
        }), 403
    
    try:
        # Determine courtesy credits based on social impact tier
        # Micro/PyME/Emprendimiento receive initial courtesy credit grant by Fundación Underlife
        if business_category in ['emprendimiento', 'micro_negocio']:
            courtesy_credits = 5000  # $5.00 USD value
            courtesy_days = 30
        elif business_category == 'pyme':
            courtesy_credits = 10000 # $10.00 USD value
            courtesy_days = 45
        elif business_category == 'community':
            courtesy_credits = 3000  # Non-commercial community grant
            courtesy_days = 60
        else:
            courtesy_credits = 1000  # Default trial
            courtesy_days = 14

        expires_at = datetime.utcnow() + timedelta(days=courtesy_days)

        # Create company with smart progressive disclosure modules
        raw_company_name = (data.get('company_name') or '').strip()
        is_placeholder_name = not raw_company_name or raw_company_name.lower() in ['', 'mi empresa', 'my company', 'nueva empresa', 'company']
        initial_plan_type = 'pyme' if business_category in ['emprendimiento', 'micro_negocio', 'pyme'] else 'enterprise'
        initial_modules = Company.compute_default_modules(
            business_category=business_category,
            industry=data.get('industry') or '',
            extra_context=f"{data.get('products_services') or ''} {data.get('ai_expectations') or ''}",
            plan_type=initial_plan_type
        )
        company = Company(
            name=raw_company_name or f"{data['name']}'s Company",
            agent_name=data.get('agent_name', 'Assistant'),
            industry=data.get('industry'),
            language=data.get('language', 'en'),
            business_category=business_category,
            credit_balance=courtesy_credits,
            courtesy_credits_granted=courtesy_credits,
            courtesy_credits_expires_at=expires_at,
            plan_type=initial_plan_type,
            subscription_tier='free' if business_category != 'enterprise' else 'enterprise_trial',
            initial_setup_completed=not is_placeholder_name,
            api_keys={'enabled_modules': initial_modules}
        )
        db.session.add(company)
        db.session.flush()
        
        # Create default agent for the company
        from models.agent import Agent
        Agent.create_default_agent(company.id, db.session)
        
        # Create user — mark as company owner (root account)
        user = User(
            email=email,
            name=data['name'],
            role=UserRole.ADMIN,
            company_id=company.id,
            is_beta_approved=True,
            is_company_owner=True,  # This is the founding account of the company
        )
        user.set_password(data['password'])
        db.session.add(user)
        
        db.session.commit()
        
        # Generate tokens (identity must be string for JWT compatibility)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return jsonify({
            'data': {
                'message': 'Registration successful',
                'user': user.to_dict(),
                'company': company.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON body required'}), 400
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is disabled'}), 403

        config = PlatformConfig.get_config()
        if config.beta_mode and user.role != UserRole.SUPER_ADMIN:
            # Existing active accounts, companies, or verified users are never locked out
            if user.is_beta_approved is None or user.company_id is not None or user.is_active:
                if not user.is_beta_approved:
                    user.is_beta_approved = True
                    db.session.commit()
            elif not user.is_beta_approved:
                return jsonify({
                    'error': 'BETA_MODE_UNAPPROVED',
                    'is_waitlist': True,
                    'message': 'Tu cuenta está en la lista de espera para la versión Beta. Te avisaremos cuando sea aprobada.'
                }), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Record real-time IP Geolocation telemetry (fail-safe)
        try:
            from services.ip_security_service import IpSecurityService
            client_ip = IpSecurityService.extract_client_ip(request)
            IpSecurityService.record_ip_activity(
                ip=client_ip,
                user_id=user.id,
                company_id=user.company_id,
                user_agent=request.headers.get('User-Agent'),
                endpoint='/api/auth/login'
            )
        except Exception as ip_err:
            logger.warning(f"Failed to track IP on login: {ip_err}")

        # Generate tokens (identity must be string for JWT compatibility)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        # Populate session cache safely
        user_dict = user.to_dict()
        company_dict = user.company.to_dict() if user.company else None
        
        return jsonify({
            'data': {
                'message': 'Login successful',
                'user': user_dict,
                'company': company_dict,
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': f'Error en inicio de sesión: {str(e)}'}), 500


@auth_bp.route('/google', methods=['POST'])
def google_auth():
    """Authenticate or auto-register user via Google JWT.
    
    [OPTIMIZACIÓN HASH TABLE - Estructura 5]
    Aplica caché Redis en 3 puntos críticos:
      1. PlatformConfig singleton → evita query SQL en cada login.
      2. User lookup por email → evita query SQL si el usuario ya existe.
      3. Sesión user+company → alimenta GET /api/auth/me con O(1) sin BD.
    """
    try:
        data = request.get_json()
        token = data.get('credential')
        if not token:
            return jsonify({'error': 'Missing credential'}), 400

        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        try:
            # [1] Verificar token Google con session pooling reutilizable (sub-100ms)
            idinfo = id_token.verify_oauth2_token(token, _google_auth_request, client_id)
        except ValueError as e:
            print(f"DEBUG GOOGLE AUTH ERROR: Invalid Google token: {str(e)}", flush=True)
            return jsonify({'error': f'Invalid Google token: {str(e)}'}), 401

        email = idinfo.get('email', '').strip().lower()
        name = idinfo.get('name', '').strip()

        # [2] HASH TABLE: PlatformConfig cacheado — O(1) en Redis en lugar de SQL
        config = _get_platform_config_cached()

        # [3] HASH TABLE: User lookup cacheado por email — O(1) en Redis
        user = _get_user_by_email_cached(email)

        # Auto-Registration si el usuario no existe
        if not user:
            # Courtesy grant for Google auto-registered accounts via Fundación Underlife
            courtesy_credits = 5000
            expires_at = datetime.utcnow() + timedelta(days=30)

            # Crear empresa por defecto con créditos de cortesía
            company = Company(
                name=f"{name}'s Hub",
                agent_name='Assistant',
                language='en',
                business_category='emprendimiento',
                credit_balance=courtesy_credits,
                courtesy_credits_granted=courtesy_credits,
                courtesy_credits_expires_at=expires_at,
                subscription_tier='free',
                plan_type='pyme'
            )
            db.session.add(company)
            db.session.flush()

            # Create default agent for the company
            from models.agent import Agent
            Agent.create_default_agent(company.id, db.session)

            # Crear usuario — marcar como propietario fundador de la empresa
            user = User(
                email=email,
                name=name,
                role=UserRole.ADMIN,
                company_id=company.id,
                is_beta_approved=True,
                is_company_owner=True,  # This is the founding account of the company
            )
            # Contraseña aleatoria para seguridad (usan Google)
            user.set_password(str(uuid.uuid4()))
            db.session.add(user)
            db.session.flush()

            db.session.commit()
            print(f"DEBUG: Auto-registered new user via Google with Fundación Underlife credits: {email}")
        else:
            if not user.is_active:
                return jsonify({'error': 'Account is deactivated'}), 403
            if config.beta_mode and user.role != UserRole.SUPER_ADMIN:
                if user.is_beta_approved is None or user.company_id is not None or user.is_active:
                    if not user.is_beta_approved:
                        user.is_beta_approved = True
                        db.session.commit()
                elif not user.is_beta_approved:
                    return jsonify({
                        'error': 'BETA_MODE_UNAPPROVED',
                        'is_waitlist': True,
                        'message': 'Tu cuenta se encuentra en lista de espera de la versión Beta.'
                    }), 403

        # Actualizar last_login e invalidar caché obsoleto del usuario
        user.last_login = datetime.utcnow()
        _invalidate_user_cache(user)  # [HASH TABLE] Invalidar caché stale
        db.session.commit()

        # Record real-time IP Geolocation telemetry
        try:
            from services.ip_security_service import IpSecurityService
            client_ip = IpSecurityService.extract_client_ip(request)
            IpSecurityService.record_ip_activity(
                ip=client_ip,
                user_id=user.id,
                company_id=user.company_id,
                user_agent=request.headers.get('User-Agent'),
                endpoint='/api/auth/google'
            )
        except Exception as e:
            logger.warning(f"Failed to track IP on google auth: {e}")

        # Generate tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # [4] HASH TABLE: Poblar caché de sesión — GET /api/auth/me será O(1)
        response_user_dict, company_dict = _cache_user_session(user, user.company)
        response_user_dict['company'] = company_dict

        return jsonify({
            'data': {
                'message': 'Google login successful',
                'user': response_user_dict,
                'company': company_dict,
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/magic-login', methods=['POST'])
def magic_login():
    """
    Direct 1-click secure authentication from magic links (Email / WhatsApp).
    Validates a short-lived or secure access token and returns user session + JWT.
    """
    try:
        data = request.get_json() or {}
        token = data.get('token')
        if not token:
            return jsonify({'error': 'Token requerido'}), 400

        import jwt
        secret_key = current_app.config.get('JWT_SECRET_KEY') or current_app.config.get('SECRET_KEY') or 'd15306490de06401ca61722312ba884e95b5aa11d1946d27ec97cab3349c229e'

        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        except Exception:
            return jsonify({'error': 'Enlace de acceso inválido o expirado'}), 401

        user_id = payload.get('user_id') or payload.get('sub')
        if not user_id:
            return jsonify({'error': 'Enlace de acceso inválido'}), 401

        user = User.query.get(int(user_id))
        if not user or not user.is_active:
            return jsonify({'error': 'Usuario no encontrado o inactivo'}), 404

        # Generate fresh JWT session tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        user.last_login = datetime.utcnow()
        db.session.commit()

        # Cache session
        response_user_dict, company_dict = _cache_user_session(user, user.company)

        return jsonify({
            'data': {
                'message': 'Autenticación exitosa',
                'user': response_user_dict,
                'company': company_dict,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'redirect_path': payload.get('redirect_path') or ('/onboarding' if getattr(user, 'is_company_owner', False) else '/dashboard')
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Magic login error: {e}")
        return jsonify({'error': f'Error en acceso directo: {str(e)}'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = get_jwt_identity()  # Already a string
    access_token = create_access_token(data={"sub": str(user_id)})
    return jsonify({
        'data': {'access_token': access_token}
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info, including owner flag and RBAC context.
    
    [OPTIMIZACIÓN HASH TABLE - Estructura 5]
    Sirve datos desde caché Redis O(1) si existen (poblados por google_auth / login).
    Solo realiza query SQL si el caché expiró o fue invalidado.

    Response includes:
      - user:    standard user dict with `is_company_owner` flag
      - company: company dict
      - permissions_context: {
            is_company_owner: bool,
            can_grant_web_access: bool,
            can_manage_admins: bool,
            employee_profile: dict | null  (linked employee record if any)
            effective_permissions: dict    (RBAC matrix if employee, else null)
        }
    """
    try:
        user_id = int(get_jwt_identity())  # Convert string back to int

        # [HASH TABLE] Intentar servir desde caché de sesión
        # Note: we skip cache here to always return fresh owner/employee context
        # (cache may be stale if owner status was just back-filled)
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        user_dict = user.to_dict()
        company_dict = user.company.to_dict() if user.company else None

        # ── Build permissions context ──────────────────────────────────
        from services.auth_guard import (
            is_company_root, can_grant_web_access, is_admin_or_above
        )

        employee_dict = None
        effective_perms = None
        try:
            from models.employee import Employee
            from services.permission_service import PermissionService
            employee = Employee.query.filter_by(
                user_id=user_id, is_active=True
            ).first()
            if employee:
                employee_dict = employee.to_dict()
                effective_perms = PermissionService.effective_permissions(employee)
        except Exception as ep_err:
            logger.warning(f"Could not load employee profile in /me: {ep_err}")

        permissions_context = {
            'is_company_owner': bool(user.is_company_owner),
            'can_grant_web_access': can_grant_web_access(user),
            'can_manage_admins': is_company_root(user),  # only root can delete/create admins
            'is_admin_or_above': is_admin_or_above(user),
            'employee_profile': employee_dict,
            'effective_permissions': effective_perms,
        }

        try:
            _cache_user_session(user, user.company)  # Repoblar caché
        except Exception:
            pass

        return jsonify({
            'data': {
                'user': user_dict,
                'company': company_dict,
                'permissions_context': permissions_context,
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/auth/me: {e}", exc_info=True)
        return jsonify({'error': f'Error recuperando sesión: {str(e)}'}), 500



@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    """Update current user info"""
    user_id = int(get_jwt_identity())  # Convert string back to int
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if data.get('name'):
        user.name = data['name']
    
    if data.get('password'):
        user.set_password(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated',
        'user': user.to_dict()
    })
