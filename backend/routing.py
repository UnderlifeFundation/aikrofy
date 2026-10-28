"""
PymAI - Unified Routing Engine (FastAPI Native)
Provides APIRouter wrappers, context proxies, rendering functions, and JWT utilities.
This replaces legacy Flask-based routing cleanly.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import sys
import contextvars
import os
import re
import logging
from fastapi import APIRouter as FastAPIAPIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse, Response, HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, Template
import jwt
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Context variables for request and JWT identity
_request_var = contextvars.ContextVar('routing_request', default=None)
_jwt_identity_var = contextvars.ContextVar('routing_jwt_identity', default=None)
_g_var = contextvars.ContextVar('routing_g_var', default=None)

class GProxy:
    def _get_dict(self):
        d = _g_var.get()
        if d is None:
            d = {}
            _g_var.set(d)
        return d

    def __getattr__(self, name):
        d = self._get_dict()
        if name not in d:
            raise AttributeError(f"g has no attribute '{name}'")
        return d[name]

    def __setattr__(self, name, value):
        d = self._get_dict()
        d[name] = value

    def __delattr__(self, name):
        d = self._get_dict()
        if name in d:
            del d[name]
        else:
            raise AttributeError(f"g has no attribute '{name}'")

g = GProxy()

class RequestProxy:
    def __getattr__(self, name):
        r = _request_var.get()
        if r is None:
            raise RuntimeError("Working outside of request context.")
        return getattr(r, name)

request = RequestProxy()

class FlaskFileStorage:
    def __init__(self, upload_file):
        self.filename = upload_file.filename
        self.content_type = upload_file.content_type
        self._upload_file = upload_file

    def save(self, destination):
        """Synchronously save the uploaded file to a destination path."""
        self._upload_file.file.seek(0)
        with open(destination, 'wb') as f:
            while True:
                chunk = self._upload_file.file.read(65536)
                if not chunk:
                    break
                f.write(chunk)

class MultiDictProxy(dict):
    """Wrapper to support Flask-like request.args.get(name, default, type)"""
    def get(self, key, default=None, type=None):
        val = super().get(key, default)
        if val is None or val == default:
            return default
        if type:
            try:
                return type(val)
            except (ValueError, TypeError):
                return default
        return val

class FlaskRequestMock:
    def __init__(self, fastapi_request: Request, json_data=None, form_data=None, raw_body=b'', files_data=None):
        self._req = fastapi_request
        self._json = json_data
        self._form = form_data or {}
        self._raw_body = raw_body
        self._files = files_data or {}
        
    def get_data(self, **kwargs):
        return self._raw_body
        
    @property
    def files(self):
        return self._files

    @property
    def args(self):
        return MultiDictProxy(self._req.query_params)
        
    @property
    def values(self):
        combined = dict(self._req.query_params)
        combined.update(self._form)
        return MultiDictProxy(combined)
        
    @property
    def form(self):
        return MultiDictProxy(self._form)
        
    @property
    def headers(self):
        return self._req.headers
        
    @property
    def cookies(self):
        return self._req.cookies
        
    @property
    def method(self):
        return self._req.method
        
    @property
    def url(self):
        return str(self._req.url)

    @property
    def host_url(self):
        return f"{self._req.url.scheme}://{self._req.url.netloc}/"

    @property
    def base_url(self):
        return f"{self._req.url.scheme}://{self._req.url.netloc}/"
        
    @property
    def path(self):
        return self._req.url.path
        
    @property
    def remote_addr(self):
        if self._req.client:
            return self._req.client.host
        return '127.0.0.1'

    @property
    def referrer(self):
        return self._req.headers.get('referer') or self._req.headers.get('referrer')

    @property
    def json(self):
        return self._json

    def get_json(self, force=False, silent=False):
        return self._json

# Configure Jinja2 templates directory
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, 'templates')
if not os.path.exists(templates_dir):
    templates_dir = os.path.join(os.path.dirname(current_dir), 'templates')

jinja_env = Environment(loader=FileSystemLoader(templates_dir))

def render_template(template_name, **context):
    template = jinja_env.get_template(template_name)
    html_content = template.render(**context)
    return HTMLResponse(content=html_content)

def render_template_string(source, **context):
    template = Template(source)
    html_content = template.render(**context)
    return HTMLResponse(content=html_content)

def redirect(location, code=302):
    return RedirectResponse(url=location, status_code=code)

def jsonify(*args, **kwargs):
    if args:
        if len(args) == 1:
            return args[0]
        return list(args)
    return kwargs

# Per-request session using ContextVar (thread/coroutine-safe)
_session_var = contextvars.ContextVar('routing_session', default=None)

class SessionProxy:
    """A per-request session dict backed by a ContextVar."""
    def _get_dict(self):
        d = _session_var.get()
        if d is None:
            d = {}
            _session_var.set(d)
        return d

    def __getitem__(self, key):
        return self._get_dict()[key]

    def __setitem__(self, key, value):
        self._get_dict()[key] = value

    def __delitem__(self, key):
        del self._get_dict()[key]

    def __contains__(self, key):
        return key in self._get_dict()

    def get(self, key, default=None):
        return self._get_dict().get(key, default)

    def pop(self, key, *args):
        return self._get_dict().pop(key, *args)

    def keys(self):
        return self._get_dict().keys()

    def __repr__(self):
        return repr(self._get_dict())

session = SessionProxy()
url_for = lambda *args, **kwargs: ""

def copy_current_request_context(f):
    return f

# Config current_app
class ConfigProxy:
    def __getattr__(self, name):
        cfg = get_config()
        return getattr(cfg, name, None)

    def __getitem__(self, key):
        cfg = get_config()
        if hasattr(cfg, key):
            return getattr(cfg, key)
        raise KeyError(f"Configuration key '{key}' not found.")

    def __setitem__(self, key, value):
        cfg = get_config()
        setattr(cfg, key, value)

    def __contains__(self, key):
        cfg = get_config()
        return hasattr(cfg, key)

    def get(self, name, default=None):
        cfg = get_config()
        return getattr(cfg, name, default)

class AppContextMock:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class CurrentAppMock:
    @property
    def config(self):
        return ConfigProxy()

    def _get_current_object(self):
        return self

    def app_context(self):
        return AppContextMock()

current_app = CurrentAppMock()

# JWT Helpers
def jwt_required(*args, **kwargs):
    def decorator(f):
        f._jwt_required = True
        return f
    return decorator

def get_jwt_identity():
    return _jwt_identity_var.get()

def verify_jwt_in_request(*args, **kwargs):
    ident = _jwt_identity_var.get()
    if ident is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

def get_jwt():
    ident = _jwt_identity_var.get()
    return {"sub": ident} if ident else {}

def create_access_token(data, expires_delta=None):
    from utils.auth_fastapi import create_access_token as cat
    return cat(data, expires_delta)

def create_refresh_token(data):
    from utils.auth_fastapi import create_refresh_token as crt
    return crt(data)

# Custom APIRouter mimicking legacy blueprint syntax but running FastAPI natively
class APIRouter:
    def __init__(self, name, import_name=None, url_prefix=None, **kwargs):
        self.name = name
        self.url_prefix = url_prefix or ""
        self.fastapi_router = FastAPIAPIRouter()
        
    def route(self, rule, **options):
        methods = options.get('methods', ['GET'])
        def decorator(f):
            def make_wrapper(func):
                async def wrapper(req: Request):
                    # JWT Authorization verification
                    user_id = None
                    auth_header = req.headers.get('Authorization')
                    if not auth_header:
                        token_arg = req.query_params.get('token')
                        if token_arg:
                            auth_header = f"Bearer {token_arg}"
                    if not auth_header:
                        cookie_token = req.cookies.get('access_token')
                        if cookie_token:
                            auth_header = f"Bearer {cookie_token}"
                    if auth_header and auth_header.startswith('Bearer '):
                        token = auth_header[7:]
                        try:
                            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
                            # Security: Only accept access tokens, not refresh tokens
                            token_type = payload.get("type", "access")
                            if token_type == "access":
                                user_id = payload.get("sub")
                                if user_id:
                                    try:
                                        from services.ip_security_service import IpSecurityService
                                        client_ip = IpSecurityService.extract_client_ip(req)
                                        device_id = req.headers.get("x-device-id")
                                        device_name = req.headers.get("x-device-name")
                                        device_type = req.headers.get("x-device-type")
                                        device_gps = req.headers.get("x-device-gps")
                                        
                                        IpSecurityService.record_ip_activity(
                                            ip=client_ip,
                                            user_id=int(user_id),
                                            user_agent=req.headers.get("user-agent"),
                                            endpoint=req.url.path,
                                            device_id=device_id,
                                            device_name=device_name,
                                            device_type=device_type,
                                            device_gps=device_gps
                                        )
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    
                    if getattr(func, '_jwt_required', False) and not user_id:
                        raise HTTPException(status_code=401, detail="Unauthorized")
                        
                    # Extract JSON and Form payloads, and raw body
                    json_data = None
                    raw_body = b''
                    if req.method in ['POST', 'PUT', 'PATCH']:
                        try:
                            raw_body = await req.body()
                        except Exception:
                            pass
                        try:
                            json_data = await req.json()
                        except Exception:
                            pass
                    form_data = {}
                    files_data = {}
                    try:
                        form = await req.form()
                        from fastapi import UploadFile
                        logger.debug(f"Form keys: {list(form.keys())}")
                        for k, v in form.multi_items():
                            logger.debug(f"Form item: k={k}, type={type(v).__name__}, is_upload={isinstance(v, UploadFile)}")
                            if isinstance(v, UploadFile) or hasattr(v, 'file'):
                                files_data[k] = FlaskFileStorage(v)
                            else:
                                form_data[k] = v
                    except Exception as fe:
                        logger.debug(f"Error parsing form data: {fe}")
                    
                    # Set Context Variables
                    _request_var.set(FlaskRequestMock(req, json_data, form_data, raw_body, files_data))
                    _jwt_identity_var.set(user_id)
                    _g_var.set({})
                    
                    from database import db_session
                    try:
                        db_session.rollback()
                    except Exception:
                        # Connection may already be dead — invalidate it so the pool discards it
                        try:
                            db_session.bind.invalidate()
                        except Exception:
                            pass
                    
                    path_params = {}
                    for k, v in req.path_params.items():
                        if isinstance(v, str) and v.isdigit():
                            path_params[k] = int(v)
                        else:
                            path_params[k] = v
                            
                    try:
                        res = func(**path_params)
                        if isinstance(res, tuple):
                            body = res[0]
                            status_code = res[1]
                            headers = res[2] if len(res) > 2 else None
                            if isinstance(body, dict):
                                return JSONResponse(content=body, status_code=status_code, headers=headers)
                            elif isinstance(body, str):
                                return HTMLResponse(content=body, status_code=status_code, headers=headers)
                            elif isinstance(body, (Response, HTMLResponse, RedirectResponse)):
                                return body
                            else:
                                return JSONResponse(content=body, status_code=status_code, headers=headers)
                                
                        if isinstance(res, (Response, HTMLResponse, RedirectResponse)):
                            return res
                        if isinstance(res, dict):
                            return res
                        if isinstance(res, str):
                            return HTMLResponse(content=res)
                        return res
                    except Exception as e:
                        logger.error(f"Error in wrapped route: {e}", exc_info=True)
                        try:
                            db_session.rollback()
                        except Exception:
                            pass
                        raise HTTPException(status_code=500, detail=str(e))
                    finally:
                        try:
                            db_session.remove()
                        except Exception:
                            # Connection was dropped (e.g. MySQL gone away after long AI call).
                            # Invalidate the underlying DBAPI connection so the pool discards it
                            # instead of trying to ROLLBACK on a dead socket.
                            try:
                                session = db_session.registry()
                                for conn in getattr(session, '_connections', {}).values():
                                    try:
                                        conn._connection.invalidate()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            try:
                                db_session.registry.registry.clear()
                            except Exception:
                                pass
                return wrapper
                
            wrapper_fn = make_wrapper(f)
            
            # Convert routing variables syntax
            fastapi_rule = rule
            fastapi_rule = re.sub(r'<[a-zA-Z_]+:([a-zA-Z_0-9]+)>', r'{\1}', fastapi_rule)
            fastapi_rule = re.sub(r'<([a-zA-Z_0-9]+)>', r'{\1}', fastapi_rule)
            
            self.fastapi_router.add_api_route(fastapi_rule, wrapper_fn, methods=methods)
            return f
        return decorator

    def before_request(self, f):
        return f

    def after_request(self, f):
        return f

    def errorhandler(self, code_or_exception):
        def decorator(f):
            return f
        return decorator

# Backward compatibility alias for Blueprint
Blueprint = APIRouter

