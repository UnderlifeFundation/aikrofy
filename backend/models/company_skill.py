"""
CompanySkill Model - Dynamic, per-company AI agent skill definitions.

This model is the core of the dynamic skills architecture. Instead of
hardcoding prompts for payments, scheduling, e-commerce, etc. inside
Python code (langgraph_agent.py), each company's agent behavior is
defined as modular CompanySkill records in the database.

Architecture:
    Company ──1:N──> CompanySkill ──> injected into LangGraph system prompt
                                  ──> required_tools filter LangGraph tool set

Skills are loaded at conversation-start by SkillService and assembled
into the final system prompt. This enables:
    - Per-company customization without code changes
    - AI-generated skills via meta-prompting (Skill Creator)
    - Versioning and rollback of skill definitions
    - Dynamic tool injection based on active skills
"""
from datetime import datetime
from enum import Enum
from extensions import db


class SkillCategory(str, Enum):
    """Categories for organizing skills in the dashboard UI."""
    CORE = 'core'                 # Base agent behavior (greeting, farewell, etc.)
    PAYMENTS = 'payments'         # PayPal, Stripe, payment flows
    SCHEDULING = 'scheduling'     # Calendar, appointment booking
    ECOMMERCE = 'ecommerce'       # Product catalog, cart, checkout
    SUPPORT = 'support'           # Ticket handling, FAQ, troubleshooting
    SALES = 'sales'               # Lead qualification, upselling
    CUSTOM = 'custom'             # Company-specific custom skills
    INTEGRATION = 'integration'   # CRM, ERP, external API behaviors


class SkillOrigin(str, Enum):
    """Tracks how the skill was created for audit/analytics."""
    SYSTEM = 'system'             # Pre-built default skills shipped with PymAI
    AI_GENERATED = 'ai_generated' # Created via the Skill Creator (meta-prompting)
    MANUAL = 'manual'             # Written manually by a company admin
    IMPORTED = 'imported'         # Imported from a shared skill marketplace/template


class CompanySkill(db.Model):
    """
    A modular, self-contained skill definition for a company's AI agent.
    
    Each skill encapsulates:
    - A structured system prompt block (injected into the LLM context)
    - The list of LangGraph tools this skill requires
    - Priority ordering for prompt assembly
    - Version tracking for safe rollback
    
    Example skills:
    - "Payments Handler": Instructs the agent on PayPal payment flows
    - "Appointment Scheduler": Defines the booking conversation protocol
    - "Product Recommender": Custom e-commerce recommendation logic
    """
    __tablename__ = 'company_skills'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    # ── Identity ──────────────────────────────────────────────────────────
    name = db.Column(db.String(100), nullable=False)        # slug: "payment_handler"
    label = db.Column(db.String(255), nullable=False)       # display: "Payment Handler"
    description = db.Column(db.Text, nullable=True)         # human description for UI
    category = db.Column(db.Enum(SkillCategory, values_callable=lambda x: [e.value for e in x]), default=SkillCategory.CUSTOM)
    origin = db.Column(db.Enum(SkillOrigin, values_callable=lambda x: [e.value for e in x]), default=SkillOrigin.MANUAL)

    # ── Prompt Block ──────────────────────────────────────────────────────
    # The structured instruction block injected into the LLM system prompt.
    # Can be plain text, Markdown, or XML-structured (Anthropic style).
    # Supports template variables: {{company_name}}, {{agent_name}}, etc.
    system_prompt_block = db.Column(db.Text, nullable=False)

    # ── Tool Requirements ─────────────────────────────────────────────────
    # JSON array of tool function names this skill needs active.
    # e.g. ["create_paypal_payment", "check_payment_status"]
    # When assembling tools for LangGraph, only tools required by at least
    # one active skill are injected — preventing bloated tool sets.
    required_tools = db.Column(db.JSON, default=list)

    # ── Constraints & Variables ───────────────────────────────────────────
    # Optional JSON for structured constraints (max tokens, format rules, etc.)
    constraints = db.Column(db.JSON, default=dict)
    # Optional JSON defining template variables and their default values
    # e.g. {"max_payment_amount": "500", "currency": "USD"}
    variables = db.Column(db.JSON, default=dict)

    # ── Ordering & Control ────────────────────────────────────────────────
    priority = db.Column(db.Integer, default=100)  # Lower = injected first in prompt
    is_enabled = db.Column(db.Boolean, default=True)

    # ── Versioning ────────────────────────────────────────────────────────
    version = db.Column(db.Integer, default=1)
    # Stores the previous prompt_block for 1-click rollback
    previous_prompt_block = db.Column(db.Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────
    company = db.relationship('Company', back_populates='skills')

    # ── Constraints ───────────────────────────────────────────────────────
    __table_args__ = (
        db.UniqueConstraint('company_id', 'name', name='unique_company_skill'),
        db.Index('ix_company_skills_company_enabled', 'company_id', 'is_enabled'),
    )

    # ── Methods ───────────────────────────────────────────────────────────

    def render_prompt(self, context: dict = None) -> str:
        """
        Render the system_prompt_block with template variable substitution.
        
        Args:
            context: Dict of variables to substitute. Keys like 'company_name'
                     replace {{company_name}} in the prompt block.
        
        Returns:
            The fully rendered prompt block string.
        """
        rendered = self.system_prompt_block
        if not context:
            context = {}
        
        # Merge skill-level default variables with runtime context
        merged = {**self.variables, **context} if self.variables else context
        
        for key, value in merged.items():
            rendered = rendered.replace(f'{{{{{key}}}}}', str(value))
        
        return rendered

    def update_prompt(self, new_prompt: str) -> None:
        """
        Update the prompt block with automatic versioning.
        Stores the previous version for 1-click rollback.
        """
        self.previous_prompt_block = self.system_prompt_block
        self.system_prompt_block = new_prompt
        self.version += 1

    def rollback_prompt(self) -> bool:
        """
        Rollback to the previous prompt version.
        Returns True if rollback succeeded, False if no previous version exists.
        """
        if self.previous_prompt_block is None:
            return False
        self.system_prompt_block, self.previous_prompt_block = (
            self.previous_prompt_block, self.system_prompt_block
        )
        self.version += 1
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary for API serialization."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'label': self.label,
            'description': self.description,
            'category': self.category.value if self.category else None,
            'origin': self.origin.value if self.origin else None,
            'system_prompt_block': self.system_prompt_block,
            'required_tools': self.required_tools or [],
            'constraints': self.constraints or {},
            'variables': self.variables or {},
            'priority': self.priority,
            'is_enabled': self.is_enabled,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<CompanySkill {self.name} (company={self.company_id})>'
