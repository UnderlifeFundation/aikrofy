from routing import jsonify, get_jwt_identity, verify_jwt_in_request
"""
Authentication and Authorization Decorators
"""
from functools import wraps


from models.user import User, UserRole

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return jsonify({'error': 'Super Admin privileges required'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))
        
        if not user or user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return jsonify({'error': 'Admin privileges required'}), 403
            
        return f(*args, **kwargs)
    return decorated_function

def subscription_required(f):
    """
    Verifies that the company of the current user has an active subscription,
    a courtesy account, or a valid 24-hour free trial.
    Must be used AFTER @jwt_required().
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            from extensions import db
            db.session.rollback()
        except:
            pass
            
        from datetime import datetime, timedelta

        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user:
            return jsonify({'error': 'Usuario no autenticado'}), 401

        # Super Admins bypass subscription checks unconditionally
        if user.role == UserRole.SUPER_ADMIN:
            return f(*args, **kwargs)

        if not user.company_id:
            return jsonify({'error': 'Company context required'}), 403

        company = user.company
        if not company:
            return jsonify({'error': 'Company context not found'}), 403

        sub = company.subscription
        is_active = bool(sub and sub.is_active)

        # Fallback 1: Courtesy account
        if not is_active and sub and sub.status.value == 'courtesy':
            is_active = True

        # Fallback 2: 24-hour free trial
        if not is_active and company.trial_activated and company.created_at:
            is_active = datetime.utcnow() < (company.created_at + timedelta(hours=24))

        if not is_active:
            return jsonify({
                'error': 'Active subscription required',
                'code': 'SUBSCRIPTION_REQUIRED'
            }), 402  # 402 Payment Required

        return f(*args, **kwargs)

    return decorated_function


def get_current_company_context(user, request):
    """
    Resolves the target company for the current request.
    Supports multi-company context switching for Agency accounts via 'X-Company-Context' header.
    """
    if not user:
        return None

    # Check for Agency / Super Admin multi-company context header
    context_comp_id = request.headers.get('X-Company-Context')
    if context_comp_id:
        try:
            target_id = int(context_comp_id)
            if user.role == UserRole.SUPER_ADMIN:
                from models.company import Company
                return Company.query.get(target_id)

            # Validate agency delegation
            from models.agency import AgencyCompanyAccess
            access = AgencyCompanyAccess.query.filter_by(
                agency_user_id=user.id,
                company_id=target_id,
                is_active=True
            ).first()
            if access:
                from models.company import Company
                return Company.query.get(target_id)
        except Exception:
            pass

    # Default fallback to user's assigned company
    if user.company:
        return user.company
    if user.role == UserRole.SUPER_ADMIN:
        from models.company import Company
        return Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)

    return None
