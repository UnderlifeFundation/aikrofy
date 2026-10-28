"""
Platform Config Model - Global settings managed by Super Admin.
"""
from datetime import datetime
from extensions import db


class PlatformConfig(db.Model):
    """
    Singleton-like table for global platform settings.
    Only one row should exist (id=1). Super Admin manages it.
    """
    __tablename__ = 'platform_config'

    id = db.Column(db.Integer, primary_key=True)

    # --- LLM Controls ---
    enable_failover = db.Column(db.Boolean, default=False, nullable=False)
    default_llm_provider = db.Column(db.String(50), default='openai')
    default_llm_model = db.Column(db.String(100), default='gpt-4')

    # --- RAG Controls ---
    global_rag_enabled = db.Column(db.Boolean, default=True, nullable=False)
    global_rag_namespace = db.Column(db.String(100), default='global')

    # --- Platform Controls ---
    maintenance_mode = db.Column(db.Boolean, default=False, nullable=False)
    beta_mode = db.Column(db.Boolean, default=False, nullable=False)
    max_agents_per_company = db.Column(db.Integer, default=3)
    max_documents_per_company = db.Column(db.Integer, default=50)
    platform_company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    # --- Timestamps ---
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    @classmethod
    def get_config(cls):
        """Get or create the singleton config row."""
        config = cls.query.get(1)
        if not config:
            config = cls(id=1)
            db.session.add(config)
            db.session.commit()
        return config

    def to_dict(self):
        return {
            'enable_failover': self.enable_failover,
            'default_llm_provider': self.default_llm_provider,
            'default_llm_model': self.default_llm_model,
            'global_rag_enabled': self.global_rag_enabled,
            'global_rag_namespace': self.global_rag_namespace,
            'maintenance_mode': self.maintenance_mode,
            'beta_mode': self.beta_mode,
            'max_agents_per_company': self.max_agents_per_company,
            'max_documents_per_company': self.max_documents_per_company,
            'platform_company_id': self.platform_company_id,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<PlatformConfig failover={self.enable_failover}>'
