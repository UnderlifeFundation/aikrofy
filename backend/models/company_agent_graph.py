"""
Company Agent Graph Model - Visual Workflow Builder Storage
Supports visual flow editing with @xyflow/react, JSON-to-StateGraph compiling,
and versioned publication.
"""
from datetime import datetime
from extensions import db

class CompanyAgentGraph(db.Model):
    """Visual Agent Workflow Graph definition per company/agent"""
    __tablename__ = 'company_agent_graphs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=True)

    name = db.Column(db.String(255), nullable=False, default="Flujo Principal de Conversación")
    description = db.Column(db.Text, nullable=True)

    # Graph definitions for visual canvas and executable state
    # canvas_data stores { nodes: [...], edges: [...], viewport: {...} }
    canvas_data = db.Column(db.JSON, nullable=False, default=dict)
    
    # compiled_spec stores normalized routing rules, topics, and transitions
    compiled_spec = db.Column(db.JSON, nullable=False, default=dict)

    is_published = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)

    # Relationships
    company = db.relationship('Company', backref=db.backref('agent_graphs', lazy='dynamic', cascade='all, delete-orphan'))
    agent = db.relationship('Agent', backref=db.backref('agent_graphs', lazy='dynamic'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'agent_id': self.agent_id,
            'name': self.name,
            'description': self.description,
            'canvas_data': self.canvas_data,
            'compiled_spec': self.compiled_spec,
            'is_published': self.is_published,
            'is_active': self.is_active,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<CompanyAgentGraph {self.id}: {self.name} (v{self.version})>'
