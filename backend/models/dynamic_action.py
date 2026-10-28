"""
Dynamic Action Model - No-Code External REST & Webhook Connectors
Allows businesses to configure external endpoints, query parameters, authentication,
and response mappings that are dynamically converted into LangChain @tool decorators.
"""
from datetime import datetime
from enum import Enum
from extensions import db

class HttpMethod(str, Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'

class AuthType(str, Enum):
    NONE = 'none'
    BEARER = 'bearer'
    API_KEY = 'api_key'
    BASIC = 'basic'
    CUSTOM_HEADER = 'custom_header'

class DynamicAction(db.Model):
    """External API endpoint wrapped dynamically as an agent tool"""
    __tablename__ = 'dynamic_actions'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    # Tool identity
    name = db.Column(db.String(100), nullable=False)  # snake_case tool name
    display_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)  # LLM prompt description

    # HTTP Config
    endpoint_url = db.Column(db.String(1024), nullable=False)
    http_method = db.Column(db.Enum(HttpMethod), default=HttpMethod.POST, nullable=False)
    
    # Auth
    auth_type = db.Column(db.Enum(AuthType), default=AuthType.NONE, nullable=False)
    auth_config = db.Column(db.JSON, default=dict)  # {'token': '...', 'header_key': 'X-API-KEY'}

    # Schema definition for arguments expected by the LLM
    # [{'name': 'order_id', 'type': 'string', 'description': 'Order ID', 'required': True}]
    parameters_schema = db.Column(db.JSON, default=list)

    # Headers and static payloads
    headers = db.Column(db.JSON, default=dict)
    static_payload = db.Column(db.JSON, default=dict)

    # Response extraction rule (e.g. JSONPath or key filter)
    response_path = db.Column(db.String(255), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('dynamic_actions', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self, include_secrets=False):
        data = {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'endpoint_url': self.endpoint_url,
            'http_method': self.http_method.value if hasattr(self.http_method, 'value') else self.http_method,
            'auth_type': self.auth_type.value if hasattr(self.auth_type, 'value') else self.auth_type,
            'parameters_schema': self.parameters_schema,
            'headers': self.headers,
            'response_path': self.response_path,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_secrets:
            data['auth_config'] = self.auth_config
            data['static_payload'] = self.static_payload
        else:
            data['auth_config'] = {'configured': bool(self.auth_config)}
        return data

    def __repr__(self):
        return f'<DynamicAction {self.id}: {self.name}>'
