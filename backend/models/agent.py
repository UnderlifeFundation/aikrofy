"""
Agent Model - Multi-agent configuration with features and tones
"""
from datetime import datetime
from enum import Enum
from extensions import db


class AgentTone(str, Enum):
    PROFESSIONAL = 'professional'
    FRIENDLY = 'friendly'
    FORMAL = 'formal'
    CASUAL = 'casual'
    RECEPTIONIST = 'receptionist'
    SALES = 'sales'
    SUPPORT = 'support'
    CONCIERGE = 'concierge'


class AgentObjective(str, Enum):
    CUSTOMER_SERVICE = 'customer_service'
    SALES = 'sales'
    SCHEDULING = 'scheduling'
    LEAD_QUALIFICATION = 'lead_qualification'
    SUPPORT = 'support'
    PAYMENTS = 'payments'
    INVENTORY = 'inventory'
    GENERAL = 'general'
    INTERNAL = 'internal'     # For employee/team-facing internal agents
    ANALYTICS = 'analytics'   # For data analysis and reporting agents


class FeatureCategory(str, Enum):
    CHANNEL = 'channel'
    INTEGRATION = 'integration'
    TONE = 'tone'
    OBJECTIVE = 'objective'
    AI_FEATURE = 'ai_feature'
    TOOL = 'tool'


class AgentGender(str, Enum):
    MALE = 'male'
    FEMALE = 'female'
    NEUTRAL = 'neutral'


class Agent(db.Model):
    """Agent configuration model"""
    __tablename__ = 'agents'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Basic Info
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Tone & Personality
    tone = db.Column(db.Enum(AgentTone), default=AgentTone.PROFESSIONAL)
    objective = db.Column(db.Enum(AgentObjective), default=AgentObjective.GENERAL)
    gender = db.Column(db.Enum(AgentGender), default=AgentGender.NEUTRAL)
    
    # System Prompt (combined with company prompt)
    system_prompt = db.Column(db.Text, nullable=True)
    
    # Configuration
    # 'twilio' or 'livekit'. If null, uses company default.
    telephony_provider = db.Column(db.String(50), nullable=True)
    
    # Priority (for multi-agent orchestration)
    priority = db.Column(db.Integer, default=1)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    company = db.relationship('Company', back_populates='agents')
    features = db.relationship('AgentFeature', back_populates='agent', lazy='dynamic', cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_enabled_features(self, category=None):
        """Get all enabled features, optionally filtered by category"""
        query = self.features.filter_by(is_enabled=True)
        if category:
            query = query.filter_by(category=category)
        return query.all()
    
    def has_feature(self, feature_name):
        """Check if a specific feature is enabled"""
        feature = self.features.filter_by(name=feature_name, is_enabled=True).first()
        return feature is not None
    
    def get_full_prompt(self):
        """Generate complete prompt including company and agent settings"""
        prompts = []
        
        # Company base prompt
        if self.company:
            if self.objective == AgentObjective.INTERNAL:
                base_prompt = f"You are Krof, the official AI Copilot for Aikrofy, assisting the team of {self.company.name}."
                prompts.append(base_prompt)
            else:
                prompts.append(self.company.get_full_system_prompt())
        
        # Tone prompt
        tone_prompts = {
            AgentTone.RECEPTIONIST: "Act as a professional receptionist, screening and qualifying calls, scheduling appointments, and being courteous.",
            AgentTone.SALES: "Act as a persuasive but helpful sales agent, understanding customer needs and presenting solutions.",
            AgentTone.SUPPORT: "Act as a patient and helpful support agent, resolving issues and answering questions clearly.",
            AgentTone.PROFESSIONAL: "Maintain a professional, business-like tone in all interactions.",
            AgentTone.FRIENDLY: "Be warm, approachable, and conversational while remaining helpful.",
            AgentTone.FORMAL: "Use formal language and maintain strict professionalism.",
            AgentTone.CASUAL: "Be relaxed and casual while still being helpful and informative.",
            AgentTone.CONCIERGE: "Act as a high-end concierge, providing premium personalized service.",
        }
        prompts.append(tone_prompts.get(self.tone, ""))
        
        # Objective prompt
        objective_prompts = {
            AgentObjective.SCHEDULING: "Your primary goal is to help schedule meetings, calls, and appointments. Check calendar availability and confirm bookings.",
            AgentObjective.SALES: "Your primary goal is to understand customer needs, present products/services, and close sales conversationally.",
            AgentObjective.PAYMENTS: "You can process payments conversationally using PayPal. Guide customers through purchases.",
            AgentObjective.INVENTORY: "You have access to inventory data. Help customers check stock, prices, and product information.",
            AgentObjective.LEAD_QUALIFICATION: "Qualify leads by asking relevant questions and gathering contact information for follow-up.",
            AgentObjective.SUPPORT: "Help resolve issues, answer questions, and provide support based on available documentation.",
            AgentObjective.CUSTOMER_SERVICE: "Provide excellent customer service, addressing inquiries and concerns promptly.",
            AgentObjective.INTERNAL: "You are an INTERNAL TEAM ASSISTANT. You help company employees and team members with their daily tasks, data queries, internal processes, customer status updates, and operational decisions. Always provide detailed, data-driven responses appropriate for internal use. You have access to all company data relevant to each team member's role.",
            AgentObjective.ANALYTICS: "You are a DATA ANALYTICS ASSISTANT. Help team members analyze metrics, interpret KPIs, generate reports, and make data-driven decisions. Provide clear insights with numbers and actionable recommendations.",
        }
        prompts.append(objective_prompts.get(self.objective, ""))
        
        # Agent-specific prompt
        if self.system_prompt:
            prompts.append(self.system_prompt)
        
        return "\n\n".join(filter(None, prompts))
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'tone': self.tone.value if hasattr(self.tone, 'value') else self.tone,
            'objective': self.objective.value if hasattr(self.objective, 'value') else self.objective,
            'gender': self.gender.value if hasattr(self.gender, 'value') else (self.gender if self.gender else 'neutral'),
            'system_prompt': self.system_prompt,
            'priority': self.priority,
            'is_active': self.is_active,
            'features': [f.to_dict() for f in self.features],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def create_default_agent(cls, company_id, session):
        """Create a default active agent with initialized features for a company"""
        existing = cls.query.filter_by(company_id=company_id, name="Default Assistant").first()
        if existing:
            return existing
            
        agent = cls(
            company_id=company_id,
            name="Default Assistant",
            description="Default support and sales assistant",
            tone=AgentTone.PROFESSIONAL,
            objective=AgentObjective.GENERAL,
            gender=AgentGender.NEUTRAL,
            system_prompt="Help the user with support and sales inquiries.",
            is_active=True
        )
        session.add(agent)
        session.flush()
        
        for feature_data in DEFAULT_FEATURES:
            is_enabled = False
            if feature_data['name'] in ['webchat', 'whatsapp', 'rag_memory', 'conversation_history']:
                is_enabled = True
            
            feature = AgentFeature(
                agent_id=agent.id,
                category=feature_data['category'],
                name=feature_data['name'],
                label=feature_data['label'],
                description=feature_data['description'],
                is_enabled=is_enabled,
                order=feature_data['order']
            )
            session.add(feature)
        
        session.commit()
        return agent

    def __repr__(self):
        return f'<Agent {self.name}>'


class AgentFeature(db.Model):
    """Agent feature toggles (checkboxes)"""
    __tablename__ = 'agent_features'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    
    # Feature Definition
    category = db.Column(db.Enum(FeatureCategory), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # State
    is_enabled = db.Column(db.Boolean, default=False)
    
    # Configuration (for features that need extra settings)
    config = db.Column(db.JSON, default=dict)
    
    # Display order within category
    order = db.Column(db.Integer, default=0)
    
    # Relationships
    agent = db.relationship('Agent', back_populates='features')
    
    # Unique constraint per agent
    __table_args__ = (
        db.UniqueConstraint('agent_id', 'name', name='unique_agent_feature'),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'category': self.category.value if hasattr(self.category, 'value') else self.category,
            'name': self.name,
            'label': self.label,
            'description': self.description,
            'is_enabled': self.is_enabled,
            'config': self.config,
            'order': self.order
        }
    
    def __repr__(self):
        return f'<AgentFeature {self.name}>'


# Default features to initialize for new agents
DEFAULT_FEATURES = [
    # Channels
    {'category': FeatureCategory.CHANNEL, 'name': 'whatsapp', 'label': 'WhatsApp', 'description': 'Send and receive WhatsApp messages', 'order': 1},
    {'category': FeatureCategory.CHANNEL, 'name': 'voice_calls', 'label': 'Voice Calls', 'description': 'Handle inbound and outbound voice calls', 'order': 2},
    {'category': FeatureCategory.CHANNEL, 'name': 'sms', 'label': 'SMS', 'description': 'Send and receive SMS messages', 'order': 3},
    {'category': FeatureCategory.CHANNEL, 'name': 'email', 'label': 'Email', 'description': 'Send and receive emails', 'order': 4},
    {'category': FeatureCategory.CHANNEL, 'name': 'telegram', 'label': 'Telegram', 'description': 'Send and receive Telegram messages', 'order': 5},
    {'category': FeatureCategory.CHANNEL, 'name': 'webchat', 'label': 'Web Chat', 'description': 'Interact via website chat widget', 'order': 6},
    
    # Integrations
    {'category': FeatureCategory.INTEGRATION, 'name': 'calendar', 'label': 'Google Calendar', 'description': 'Schedule meetings and check availability', 'order': 1},
    {'category': FeatureCategory.INTEGRATION, 'name': 'google_sheets', 'label': 'Google Sheets', 'description': 'Access inventory, prices, and data from spreadsheets', 'order': 2},
    {'category': FeatureCategory.INTEGRATION, 'name': 'paypal', 'label': 'PayPal Payments', 'description': 'Process payments conversationally', 'order': 3},
    {'category': FeatureCategory.INTEGRATION, 'name': 'crm_sync', 'label': 'CRM Sync', 'description': 'Sync with external CRM systems', 'order': 4},
    {'category': FeatureCategory.INTEGRATION, 'name': 'ecommerce', 'label': 'E-commerce', 'description': 'Connect to Shopify, WooCommerce, VTEX, Magento, PrestaShop or BigCommerce', 'order': 5},
    {'category': FeatureCategory.INTEGRATION, 'name': 'erp_integration', 'label': 'ERP', 'description': 'Connect to SAP Business One, Oracle NetSuite, Odoo, or Dynamics 365 Business Central', 'order': 6},
    
    # Tools
    {'category': FeatureCategory.TOOL, 'name': 'schedule_meeting', 'label': 'Schedule Meetings', 'description': 'Book meetings on connected calendars', 'order': 1},
    {'category': FeatureCategory.TOOL, 'name': 'send_email', 'label': 'Send Emails', 'description': 'Send emails on behalf of the company', 'order': 2},
    {'category': FeatureCategory.TOOL, 'name': 'check_inventory', 'label': 'Check Inventory', 'description': 'Look up product availability and prices', 'order': 3},
    {'category': FeatureCategory.TOOL, 'name': 'process_payment', 'label': 'Process Payments', 'description': 'Create and send payment links', 'order': 4},
    {'category': FeatureCategory.TOOL, 'name': 'create_task', 'label': 'Create Tasks', 'description': 'Create follow-up tasks for team members', 'order': 5},
    {'category': FeatureCategory.TOOL, 'name': 'transfer_call', 'label': 'Transfer Calls', 'description': 'Transfer calls to team members', 'order': 6},
    
    # AI Features
    {'category': FeatureCategory.AI_FEATURE, 'name': 'rag_memory', 'label': 'RAG Memory', 'description': 'Use uploaded documents for context', 'order': 1},
    {'category': FeatureCategory.AI_FEATURE, 'name': 'conversation_history', 'label': 'Conversation History', 'description': 'Remember past conversations with contacts', 'order': 2},
    {'category': FeatureCategory.AI_FEATURE, 'name': 'real_time_data', 'label': 'Real-time Data', 'description': 'Share live data with admin chat', 'order': 3},
    {'category': FeatureCategory.AI_FEATURE, 'name': 'sentiment_analysis', 'label': 'Sentiment Analysis', 'description': 'Analyze customer sentiment', 'order': 4},
    {'category': FeatureCategory.AI_FEATURE, 'name': 'auto_escalation', 'label': 'Auto Escalation', 'description': 'Automatically escalate complex issues', 'order': 5},
    {'category': FeatureCategory.AI_FEATURE, 'name': 'require_lead_capture', 'label': 'Lead Capture Gating', 'description': 'Require name and email before providing AI chat', 'order': 6},
]
