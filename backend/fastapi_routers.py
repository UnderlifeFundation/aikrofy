from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from config import get_config
from models.user import User, UserRole
from models.company import Company
from models.subscription import Plan
from services.dlocal_service import DLocalGoService
from utils.auth_fastapi import create_access_token, create_refresh_token, get_current_user_id
from database import get_db


def _require_admin(user: User):
    """Raise 403 if the user does not have ADMIN, SUPER_ADMIN, or AGENCY role or is not company owner."""
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.AGENCY) and not getattr(user, 'is_company_owner', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need administrator privileges to perform this action."
        )


def _get_effective_company(request: Request, user: User, db: Session) -> Company:
    """
    Resolves target company for current request.
    If the user has AGENCY or SUPER_ADMIN role and sends 'X-Company-Context' (or 'x-company-context'),
    validates the delegated agency access and returns that client company.
    Otherwise returns user's primary company.
    """
    context_comp_id = request.headers.get("X-Company-Context") or request.headers.get("x-company-context")
    if context_comp_id:
        try:
            target_id = int(context_comp_id)
            if user.role == UserRole.SUPER_ADMIN:
                comp = db.query(Company).get(target_id)
                if comp:
                    return comp

            from models.agency import AgencyCompanyAccess
            access = db.query(AgencyCompanyAccess).filter_by(
                agency_user_id=user.id,
                company_id=target_id,
                is_active=True
            ).first()
            if access:
                comp = db.query(Company).get(target_id)
                if comp:
                    return comp
        except Exception:
            pass

    if user.company:
        return user.company

    if user.role == UserRole.SUPER_ADMIN:
        comp = db.query(Company).filter(Company.name.ilike('%aikrofy%')).first() or db.query(Company).get(1)
        if comp:
            return comp

    raise HTTPException(status_code=404, detail="Company not found")



router = APIRouter()
config = get_config()

# ---------------------------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------------------------

@router.post("/auth/register")
async def register(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    required = ['email', 'password', 'name', 'company_name']
    for field in required:
        if not data.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")
            
    if db.query(User).filter_by(email=data['email']).first():
        raise HTTPException(status_code=409, detail="Email already registered")
        
    try:
        company = Company(
            name=data['company_name'],
            agent_name=data.get('agent_name', 'Assistant'),
            language=data.get('language', 'en')
        )
        db.add(company)
        db.flush()
        
        user = User(
            email=data['email'],
            name=data['name'],
            role=UserRole.ADMIN,
            company_id=company.id
        )
        user.set_password(data['password'])
        db.add(user)
        db.commit()
        
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "data": {
                "message": "Registration successful",
                "user": user.to_dict(),
                "company": company.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auth/login")
async def login(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    if not data.get('email') or not data.get('password'):
        raise HTTPException(status_code=400, detail="Email and password are required")
        
    user = db.query(User).filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
        
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "data": {
            "message": "Login successful",
            "user": user.to_dict(),
            "company": user.company.to_dict() if user.company else None,
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    }

@router.get("/auth/me")
async def get_me(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "data": {
            "user": user.to_dict(),
            "company": user.company.to_dict() if user.company else None
        }
    }

# ---------------------------------------------------------------------------
# BILLING ROUTES — Served by billing_bp via fastapi_routes_loader.py
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ERP INTEGRATION ROUTES
# ---------------------------------------------------------------------------

# Credential field definitions per ERP platform (for frontend rendering)
ERP_PLATFORM_FIELDS = {
    'sap_b1': {
        'label': 'SAP Business One',
        'fields': [
            {'key': 'company_db', 'label': 'Company Database', 'type': 'text', 'required': True},
            {'key': 'username', 'label': 'Username', 'type': 'text', 'required': True},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'https://sap-server:50000',
        'url_help': 'Your SAP Business One Service Layer URL (with port)',
    },
    'netsuite': {
        'label': 'Oracle NetSuite',
        'fields': [
            {'key': 'account_id', 'label': 'Account ID', 'type': 'text', 'required': True},
            {'key': 'client_id', 'label': 'Client ID (OAuth 2.0)', 'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'TSTDRV12345',
        'url_help': 'Your NetSuite Account ID (used to construct the API URL)',
    },
    'odoo': {
        'label': 'Odoo ERP',
        'fields': [
            {'key': 'db', 'label': 'Database Name', 'type': 'text', 'required': True},
            {'key': 'username', 'label': 'Username / Email', 'type': 'text', 'required': True},
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'https://mycompany.odoo.com',
        'url_help': 'Your Odoo instance URL',
    },
    'dynamics_bc': {
        'label': 'Microsoft Dynamics 365 BC',
        'fields': [
            {'key': 'tenant_id', 'label': 'Azure Tenant ID', 'type': 'text', 'required': True},
            {'key': 'client_id', 'label': 'Application (Client) ID', 'type': 'text', 'required': True},
            {'key': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True},
            {'key': 'environment', 'label': 'Environment', 'type': 'text', 'required': False},
        ],
        'url_placeholder': 'production',
        'url_help': 'Your Dynamics 365 Business Central environment name (e.g. production, sandbox)',
    },
    'contifico': {
        'label': 'Siigo Contífico ERP',
        'fields': [
            {'key': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True},
            {'key': 'pos_token', 'label': 'Token POS', 'type': 'text', 'required': True},
        ],
        'url_placeholder': 'https://api.contifico.com/sistema/api/v1',
        'url_help': 'API URL for Contífico (e.g., https://api.contifico.com/sistema/api/v1)',
    },
    'mysql': {
        'label': 'Custom Database (MySQL)',
        'fields': [
            {'key': 'host', 'label': 'Host IP/Domain', 'type': 'text', 'required': True},
            {'key': 'port', 'label': 'Port', 'type': 'text', 'required': True},
            {'key': 'database', 'label': 'Database Name', 'type': 'text', 'required': True},
            {'key': 'username', 'label': 'Username', 'type': 'text', 'required': True},
            {'key': 'password', 'label': 'Password', 'type': 'password', 'required': True},
        ],
        'url_placeholder': 'mysql://my-server:3306/dbname',
        'url_help': 'Database connection URI or identifier',
    },
}



@router.get("/erp/platforms")
async def get_erp_platforms():
    """Return available ERP platforms and their credential schemas."""
    return {"platforms": ERP_PLATFORM_FIELDS}


@router.get("/erp/config")
async def get_erp_config(request: Request, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Get current company ERP configuration (supports agency workspace context)."""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    company = _get_effective_company(request, user, db)

    from models.erp_config import ERPConfig
    config = db.query(ERPConfig).filter_by(company_id=company.id).first()
    if not config:
        return {"config": None}

    return {"config": config.to_dict()}


@router.post("/erp/config")
async def save_erp_config(request: Request, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Create or update ERP configuration. Requires ADMIN or AGENCY role (supports agency workspace context)."""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _require_admin(user)
    company = _get_effective_company(request, user, db)

    data = await request.json()
    platform_str = data.get("platform", "")
    erp_url = data.get("erp_url", "").strip()
    credentials = data.get("credentials", {})

    # Validate platform
    from models.erp_config import ERPConfig, ERPPlatform
    try:
        platform = ERPPlatform(platform_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported ERP platform: {platform_str}")

    if not erp_url:
        raise HTTPException(status_code=400, detail="ERP URL is required")

    # Validate required credential fields
    platform_def = ERP_PLATFORM_FIELDS.get(platform_str, {})
    for field in platform_def.get("fields", []):
        if field.get("required") and not credentials.get(field["key"]):
            raise HTTPException(status_code=400, detail=f"Field '{field['label']}' is required")

    # Upsert
    config = db.query(ERPConfig).filter_by(company_id=company.id).first()
    if config:
        config.platform = platform
        config.erp_url = erp_url
        config.credentials = credentials
        config.is_connected = False  # Reset until re-tested
        config.last_error = None
    else:
        config = ERPConfig(
            company_id=company.id,
            platform=platform,
            erp_url=erp_url,
            credentials=credentials,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return {
        "message": "ERP configuration saved",
        "config": config.to_dict(),
    }


@router.post("/erp/test")
async def test_erp_connection(request: Request, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Test stored ERP credentials by making a live API call. Requires ADMIN or AGENCY role (supports agency workspace context)."""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _require_admin(user)
    company = _get_effective_company(request, user, db)

    from models.erp_config import ERPConfig
    config = db.query(ERPConfig).filter_by(company_id=company.id).first()
    if not config:
        raise HTTPException(status_code=404, detail="No ERP configuration found. Save your credentials first.")

    from services.erp.factory import get_erp_driver
    try:
        driver = get_erp_driver(company)
        if not driver:
            raise HTTPException(status_code=500, detail="Could not initialize ERP driver")

        result = driver.test_connection()

        # Update connection status
        config.is_connected = result.get("success", False)
        from datetime import datetime
        config.last_tested_at = datetime.utcnow()
        config.last_error = result.get("error") if not result.get("success") else None
        db.commit()

        return {
            "result": result,
            "config": config.to_dict(),
        }
    except Exception as e:
        config.is_connected = False
        from datetime import datetime
        config.last_tested_at = datetime.utcnow()
        config.last_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/erp/disconnect")
async def disconnect_erp(request: Request, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """Remove ERP configuration for the company. Requires ADMIN or AGENCY role (supports agency workspace context)."""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _require_admin(user)
    company = _get_effective_company(request, user, db)

    from models.erp_config import ERPConfig
    config = db.query(ERPConfig).filter_by(company_id=company.id).first()
    if config:
        db.delete(config)
        db.commit()

    return {"message": "ERP disconnected"}

