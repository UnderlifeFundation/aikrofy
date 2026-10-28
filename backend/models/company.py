"""
Company Model - Multi-tenant company/business management
"""
from datetime import datetime
from enum import Enum
from extensions import db


class AgentGender(str, Enum):
    FEMALE = 'female'
    MALE = 'male'
    NEUTRAL = 'neutral'


class BusinessCategory(str, Enum):
    EMPRENDIMIENTO = 'emprendimiento'
    MICRO_NEGOCIO = 'micro_negocio'
    PYME = 'pyme'
    ENTERPRISE = 'enterprise'
    COMMUNITY = 'community'


class Company(db.Model):
    """Company/Business model - main tenant entity"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    
    # Agent Personalization
    agent_name = db.Column(db.String(100), default='Assistant')
    agent_gender = db.Column(db.Enum(AgentGender), default=AgentGender.NEUTRAL)
    personality_prompt = db.Column(db.Text, nullable=True)
    custom_instructions = db.Column(db.Text, nullable=True)
    
    # LLM Configuration
    llm_provider = db.Column(db.String(50), default='openai')
    llm_model = db.Column(db.String(100), default='gpt-5-nano')
    # LLM Routing Mode: 'core_pool' (Inference + LEM charged together) or 'byok' (Private Key / $0 LLM + 1 micro-credit LEM)
    llm_routing_mode = db.Column(db.String(50), default='core_pool')
    voice_provider = db.Column(db.String(50), default='elevenlabs')
    voice_model = db.Column(db.String(100), nullable=True)
    
    # API Keys (encrypted in production)
    api_keys = db.Column(db.JSON, default=dict)
    
    # Pinecone RAG Configuration
    pinecone_index = db.Column(db.String(255), nullable=True)
    pinecone_namespace = db.Column(db.String(255), nullable=True)
    
    # Business Info
    industry = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(50), default='UTC')
    language = db.Column(db.String(10), default='en')
    
    # Location
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    
    # Real-Time IP Telemetry & GPS Geolocation
    last_ip = db.Column(db.String(64), nullable=True)
    last_ip_lat = db.Column(db.Float, nullable=True)
    last_ip_lng = db.Column(db.Float, nullable=True)
    last_ip_city = db.Column(db.String(100), nullable=True)
    last_ip_country = db.Column(db.String(100), nullable=True)
    last_ip_isp = db.Column(db.String(255), nullable=True)
    last_ip_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Business Classification & Social Impact (Fundación Underlife Open-Core Initiative)
    business_category = db.Column(db.String(50), default='emprendimiento')
    courtesy_credits_granted = db.Column(db.Integer, default=0)
    courtesy_credits_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Contact Info
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    
    # Dynamic Credit System - 2-Layer Credit Engine
    # Layer 1: Core AI Operations (LLM Tokens, STT, TTS, Tool Execution)
    credit_balance = db.Column(db.Integer, default=0)
    # Layer 2: Observability & Agent Tracing (LangSmith/AgentOps Real-time Traces, E(z,S) Verification)
    observability_credit_balance = db.Column(db.Integer, default=50) # Default complimentary quota for beta users
    
    # Public conversational landing page slug
    public_slug = db.Column(db.String(100), unique=True, nullable=True)
    
    # Company Logo URL (used in widget, header, landing pages)
    logo_url = db.Column(db.String(500), nullable=True)
    
    # ── Enterprise Plan Quotas ────────────────────────────────────────────
    # Controls how many departments and employees a company can create.
    # Defaults correspond to the 'pyme' plan. Admins or Paddle webhooks
    # update these values when a company upgrades.
    max_departments = db.Column(db.Integer, default=1, nullable=False)   # 1 = PyME tier
    max_employees = db.Column(db.Integer, default=10, nullable=False)    # 10 = PyME tier
    max_agents = db.Column(db.Integer, default=3, nullable=False)        # 3 = default tier
    
    # ── Agency Quota ──────────────────────────────────────────────────────
    # Controls how many client companies an agency can manage.
    # Set by Super Admin based on the agency's contracted plan:
    #   Agency Starter: 3 companies
    #   Agency Pro:    10 companies
    #   Agency Scale:  25 companies
    #   Agency Enterprise: unlimited (-1)
    agency_max_companies = db.Column(db.Integer, default=0, nullable=False)  # 0 = not an agency

    # Relationships
    users = db.relationship('User', back_populates='company', lazy='dynamic')
    agents = db.relationship('Agent', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    channels = db.relationship('Channel', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    employees = db.relationship('Employee', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    departments = db.relationship('Department', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    documents = db.relationship('Document', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    skills = db.relationship('CompanySkill', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    guided_responses = db.relationship('GuidedResponse', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    campaigns = db.relationship('CompanyCampaign', back_populates='company', lazy='dynamic', cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    subscription_tier = db.Column(db.String(50), default='free')
    plan_type = db.Column(db.String(50), default='pyme')
    
    # Demo configuration
    is_demo = db.Column(db.Boolean, default=False)
    demo_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Beta / Trial Gating (ported from EnpiAI)
    trial_activated = db.Column(db.Boolean, default=False, nullable=False)
    feedback_submitted = db.Column(db.Boolean, default=False, nullable=False)
    beta_feedback = db.Column(db.JSON, nullable=True)
    initial_setup_completed = db.Column(db.Boolean, default=False, nullable=False)
    
    def get_full_system_prompt(self):
        """Generate complete system prompt including personality"""
        base_prompt = f"You are {self.agent_name}, an AI assistant"
        
        if self.agent_gender != AgentGender.NEUTRAL:
            base_prompt += f" ({self.agent_gender.value})"
        
        base_prompt += f" for {self.name}."
        
        if self.personality_prompt:
            base_prompt += f"\n\nPersonality: {self.personality_prompt}"
        
        if self.custom_instructions:
            base_prompt += f"\n\nSpecial Instructions: {self.custom_instructions}"
        
        return base_prompt

    @staticmethod
    def compute_default_modules(
        business_category: str = 'emprendimiento',
        industry: str = '',
        extra_context: str = '',
        plan_type: str = 'pyme'
    ) -> list:
        """
        Compute smart progressive disclosure modules based on the user's onboarding
        and registration profile so new accounts only see the tools they actually need.
        """
        cat = (business_category or 'emprendimiento').lower().strip()
        ind = (industry or '').lower()
        ctx = f"{ind} {(extra_context or '').lower()}"

        # Core essential modules always present for a clean start
        modules = [
            'dashboard',
            'pos',        # Native AI-POS, Catalog, Barcodes & QR labels
            'chat',       # Inbox & AI Conversations
            'contacts',   # Customers & Leads
            'channels',   # WhatsApp / Webchat / Telegram connection
            'agents',     # AI Agent & Copilot Configuration
            'settings',   # Settings & Personalizar Panel
        ]

        # Context-aware additions based on onboarding description / expectations
        if any(k in ctx for k in ['document', 'pdf', 'manual', 'catalogo', 'catálogo', 'conocimiento', 'rag', 'archivo', 'ley', 'legal', 'menu', 'menú']):
            modules.append('documents')
        if any(k in ctx for k in ['qr', 'campaña', 'campana', 'marketing', 'redes', 'anuncio', 'promo', 'feria', 'evento']):
            modules.append('campaigns')
        if any(k in ctx for k in ['landing', 'web', 'pagina', 'página', 'sitio', 'tienda online']):
            modules.append('landing_pages')
        if any(k in ctx for k in ['cita', 'agenda', 'reunion', 'reunión', 'calendario', 'consulta', 'reserva', 'turno', 'medico', 'médico', 'abogado', 'clinica', 'clínica']):
            modules.append('meetings')
        if any(k in ctx for k in ['pago', 'cobro', 'tarjeta', 'paypal', 'stripe', 'transferencia', 'factura']):
            modules.append('payments')
        if any(k in ctx for k in ['shopify', 'woocommerce', 'magento', 'prestashop']):
            modules.append('ecommerce')
        if any(k in ctx for k in ['hubspot', 'salesforce', 'pipedrive', 'zoho']):
            modules.append('crm')
        if any(k in ctx for k in ['sap', 'odoo', 'oracle', 'netsuite', 'erp', 'contabilidad']):
            modules.append('erp')
        if any(k in ctx for k in ['equipo', 'empleado', 'vendedor', 'colaborador', 'rrhh', 'departamento']):
            modules.extend(['employees', 'departments'])
        if any(k in ctx for k in ['voz', 'llamada', 'telefono', 'teléfono', 'call center', 'pbx']):
            modules.append('voice')

        # Category-based progressive expansion
        if cat == 'pyme':
            for m in ['documents', 'campaigns', 'payments', 'analytics', 'billing']:
                if m not in modules:
                    modules.append(m)
        elif cat == 'enterprise' or (plan_type or '').lower() == 'enterprise':
            for m in [
                'documents', 'campaigns', 'landing_pages', 'payments', 'ecommerce',
                'crm', 'erp', 'meetings', 'departments', 'employees', 'analytics',
                'observatory', 'marketplace', 'mcp', 'voice', 'whatsapp_templates', 'billing'
            ]:
                if m not in modules:
                    modules.append(m)
        else:
            # Emprendimiento / Micro-negocio / Community: keep it focused (add documents + campaigns + billing by default)
            for m in ['documents', 'campaigns', 'billing']:
                if m not in modules:
                    modules.append(m)

        # Deduplicate preserving order
        seen = set()
        result = []
        for m in modules:
            if m not in seen:
                seen.add(m)
                result.append(m)
        return result

    def get_enabled_modules(self) -> list:
        """Return the company's active workspace modules (custom checklist or smart defaults)."""
        if isinstance(self.api_keys, dict):
            custom = self.api_keys.get('enabled_modules')
            if isinstance(custom, list) and len(custom) > 0:
                # Always ensure 'dashboard' and 'settings' remain accessible
                ensured = list(custom)
                if 'dashboard' not in ensured:
                    ensured.insert(0, 'dashboard')
                if 'settings' not in ensured:
                    ensured.append('settings')
                return ensured

        return Company.compute_default_modules(
            business_category=self.business_category or 'emprendimiento',
            industry=self.industry or '',
            extra_context=f"{self.personality_prompt or ''} {self.custom_instructions or ''}",
            plan_type=self.plan_type or 'pyme'
        )
    
    def to_dict(self, include_api_keys=False):
        """Convert to dictionary"""
        from datetime import datetime, timedelta
        
        # Calculate 24-hour trial period validity
        in_trial = False
        if self.trial_activated and self.created_at:
            in_trial = datetime.utcnow() < (self.created_at + timedelta(hours=24))

        sub = self.subscription
        sub_status = getattr(sub, 'status', None)
        status_val = sub_status.value if hasattr(sub_status, 'value') else str(sub_status or '')
        is_courtesy = (status_val == 'courtesy')
        subscription_active = bool(sub and getattr(sub, 'is_active', False))

        logo = self.logo_url
        if not logo and isinstance(self.api_keys, dict):
            logo = self.api_keys.get('logo_url')

        gender_val = self.agent_gender.value if hasattr(self.agent_gender, 'value') else str(self.agent_gender or 'neutral')

        data = {
            'id': self.id,
            'name': self.name,
            'logo_url': logo,
            'agent_name': self.agent_name,
            'agent_gender': gender_val,
            'personality_prompt': self.personality_prompt,
            'custom_instructions': self.custom_instructions,
            'llm_provider': self.llm_provider,
            'llm_model': self.llm_model,
            'llm_routing_mode': getattr(self, 'llm_routing_mode', 'core_pool') or 'core_pool',
            'voice_provider': self.voice_provider,
            'voice_model': self.voice_model,
            'pinecone_index': self.pinecone_index,
            'industry': self.industry,
            'country': self.country,
            'city': self.city,
            'timezone': self.timezone,
            'language': self.language,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'is_active': bool(self.is_active),
            'subscription_tier': self.subscription_tier,
            'plan_type': self.plan_type or 'pyme',
            'max_departments': self.max_departments,
            'max_employees': self.max_employees,
            'max_agents': self.max_agents,
            'agency_max_companies': self.agency_max_companies,
            'subscription_active': subscription_active or is_courtesy or in_trial,
            'is_courtesy': is_courtesy,
            'is_demo': bool(self.is_demo),
            'demo_expires_at': self.demo_expires_at.isoformat() if self.demo_expires_at else None,
            'trial_activated': bool(self.trial_activated),
            'feedback_submitted': bool(self.feedback_submitted),
            'initial_setup_completed': bool(self.initial_setup_completed),
            'is_in_trial': in_trial,
            'business_category': self.business_category or 'emprendimiento',
            'enabled_modules': self.get_enabled_modules(),
            'courtesy_credits_granted': self.courtesy_credits_granted or 0,
            'courtesy_credits_expires_at': self.courtesy_credits_expires_at.isoformat() if self.courtesy_credits_expires_at else None,
            'credit_balance': self.credit_balance or 0,
            'observability_credit_balance': getattr(self, 'observability_credit_balance', 50) or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_api_keys:
            data['api_keys'] = self.api_keys
        
        return data
    
    def __repr__(self):
        return f'<Company {self.name}>'
