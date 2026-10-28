"""
Landing Page Models - AI-Generated landing pages with telemetry and custom domains
"""
from datetime import datetime
from enum import Enum
from extensions import db


class LandingPageStatus(str, Enum):
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'


class LandingPage(db.Model):
    __tablename__ = 'landing_pages'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(150), nullable=False)  # unique per company via constraint
    html_content = db.Column(db.Text, nullable=True)
    css_content = db.Column(db.Text, nullable=True)
    js_content = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(LandingPageStatus), default=LandingPageStatus.DRAFT)
    version = db.Column(db.Integer, default=1)
    is_primary = db.Column(db.Boolean, default=False)
    custom_domain = db.Column(db.String(255), nullable=True)
    custom_domain_verified = db.Column(db.Boolean, default=False)
    token_cost = db.Column(db.Integer, default=50)
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    og_image_url = db.Column(db.String(500), nullable=True)
    views_count = db.Column(db.Integer, default=0)
    conversions_count = db.Column(db.Integer, default=0)
    llm_model = db.Column(db.String(100), default='gpt-5-nano')
    generation_prompt = db.Column(db.Text, nullable=True)
    screenshot_url = db.Column(db.String(500), nullable=True)
    generation_status = db.Column(db.String(50), default='idle')  # idle/generating/complete/error
    generation_error = db.Column(db.Text, nullable=True)
    # LLM model config for Enterprise users (JSON: {model, api_key, provider, base_url})
    llm_config = db.Column(db.JSON, default=dict)
    chatweb_enabled = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    company = db.relationship('Company', backref=db.backref('landing_pages', lazy='dynamic'))
    versions = db.relationship('LandingPageVersion', backref='landing_page', lazy='dynamic', cascade='all, delete-orphan')
    visits = db.relationship('LandingPageVisit', backref='landing_page', lazy='dynamic', cascade='all, delete-orphan')
    elements = db.relationship('LandingPageElement', backref='landing_page', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (db.UniqueConstraint('company_id', 'slug', name='uq_landing_company_slug'),)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'title': self.title,
            'slug': self.slug,
            'status': self.status.value if self.status else 'draft',
            'version': self.version,
            'is_primary': self.is_primary,
            'custom_domain': self.custom_domain,
            'custom_domain_verified': self.custom_domain_verified,
            'token_cost': self.token_cost,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'og_image_url': self.og_image_url,
            'views_count': self.views_count,
            'conversions_count': self.conversions_count,
            'llm_model': self.llm_model,
            'generation_prompt': self.generation_prompt,
            'screenshot_url': self.screenshot_url,
            'generation_status': self.generation_status,
            'generation_error': self.generation_error,
            'llm_config': self.llm_config or {},
            'chatweb_enabled': self.chatweb_enabled,
            'html_content': self.html_content,
            'css_content': self.css_content,
            'js_content': self.js_content,
            'has_content': bool(self.html_content),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }

    def __repr__(self):
        return f'<LandingPage {self.title}>'


class LandingPageVersion(db.Model):
    __tablename__ = 'landing_page_versions'

    id = db.Column(db.Integer, primary_key=True)
    landing_page_id = db.Column(db.Integer, db.ForeignKey('landing_pages.id'), nullable=False)
    html_content = db.Column(db.Text, nullable=True)
    css_content = db.Column(db.Text, nullable=True)
    js_content = db.Column(db.Text, nullable=True)
    version_number = db.Column(db.Integer, nullable=False)
    change_summary = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=True)  # email or 'whatsapp:+1234' or 'agent:cro'

    def to_dict(self):
        return {
            'id': self.id,
            'landing_page_id': self.landing_page_id,
            'version_number': self.version_number,
            'change_summary': self.change_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }


class LandingPageVisit(db.Model):
    __tablename__ = 'landing_page_visits'

    id = db.Column(db.Integer, primary_key=True)
    landing_page_id = db.Column(db.Integer, db.ForeignKey('landing_pages.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    visitor_ip = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    # UTM parameters
    utm_source = db.Column(db.String(255), nullable=True)
    utm_medium = db.Column(db.String(255), nullable=True)
    utm_campaign = db.Column(db.String(255), nullable=True)
    utm_term = db.Column(db.String(255), nullable=True)
    utm_content = db.Column(db.String(255), nullable=True)
    # Geo
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    # Device
    device_type = db.Column(db.String(50), nullable=True)  # desktop/tablet/mobile
    # Engagement
    time_on_page = db.Column(db.Integer, nullable=True)  # seconds
    scroll_depth = db.Column(db.Integer, nullable=True)  # 0-100 percentage
    cta_clicks = db.Column(db.JSON, default=list)
    form_submissions = db.Column(db.JSON, default=list)
    # Lead linking
    lead_id = db.Column(db.Integer, nullable=True)  # links to customer/contact
    whatsapp_lead_id = db.Column(db.String(100), nullable=True)  # e.g. '+521234567890'
    w_lead_token = db.Column(db.String(100), nullable=True)  # unique token from WhatsApp link
    # Lead scoring delta applied for this visit
    lead_score_delta = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'landing_page_id': self.landing_page_id,
            'session_id': self.session_id,
            'visitor_ip': self.visitor_ip,
            'referrer': self.referrer,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'utm_term': self.utm_term,
            'utm_content': self.utm_content,
            'country': self.country,
            'city': self.city,
            'region': self.region,
            'device_type': self.device_type,
            'time_on_page': self.time_on_page,
            'scroll_depth': self.scroll_depth,
            'cta_clicks': self.cta_clicks or [],
            'form_submissions': self.form_submissions or [],
            'lead_id': self.lead_id,
            'whatsapp_lead_id': self.whatsapp_lead_id,
            'w_lead_token': self.w_lead_token,
            'lead_score_delta': self.lead_score_delta,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LandingPageElement(db.Model):
    __tablename__ = 'landing_page_elements'

    id = db.Column(db.Integer, primary_key=True)
    landing_page_id = db.Column(db.Integer, db.ForeignKey('landing_pages.id'), nullable=False)
    element_type = db.Column(db.String(50), nullable=False)  # hero/cta/form/image/text/video/section
    element_key = db.Column(db.String(100), nullable=False)  # unique key within the page for no-code editor
    content = db.Column(db.JSON, default=dict)  # {text, href, src, alt, style, etc}
    css_overrides = db.Column(db.JSON, default=dict)  # CSS property overrides
    is_visible = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'landing_page_id': self.landing_page_id,
            'element_type': self.element_type,
            'element_key': self.element_key,
            'content': self.content or {},
            'css_overrides': self.css_overrides or {},
            'is_visible': self.is_visible,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class LandingPageCustomDomain(db.Model):
    __tablename__ = 'landing_page_custom_domains'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    domain = db.Column(db.String(255), unique=True, nullable=False)
    landing_page_id = db.Column(db.Integer, db.ForeignKey('landing_pages.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    verified_at = db.Column(db.DateTime, nullable=True)
    dns_token = db.Column(db.String(100), nullable=False)  # for CNAME verification
    ssl_status = db.Column(db.String(50), default='pending')  # pending/active/error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', backref=db.backref('custom_domains', lazy='dynamic'))
    landing_page = db.relationship('LandingPage', backref=db.backref('domain_mappings', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'domain': self.domain,
            'landing_page_id': self.landing_page_id,
            'is_active': self.is_active,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'dns_token': self.dns_token,
            'ssl_status': self.ssl_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<CustomDomain {self.domain}>'
