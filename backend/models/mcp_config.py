"""
CompanyMCPServer Model - Configuration for external Model Context Protocol (MCP) servers.

This model enables B2B multi-tenant registration of external MCP servers using
the SSE/HTTP transport protocol. By configuring an MCP server, a company can
expose custom APIs as agent tools without writing any new Python backend code.
"""
from datetime import datetime
from extensions import db


class CompanyMCPServer(db.Model):
    """
    Configuration for a remote Model Context Protocol (MCP) server.
    Connected to a Company (One-to-Many).
    """
    __tablename__ = 'company_mcp_servers'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)

    # ── Identity ──────────────────────────────────────────────────────────
    name = db.Column(db.String(100), nullable=False)        # slug: "crm-interno"
    label = db.Column(db.String(255), nullable=False)       # display: "CRM Interno"
    description = db.Column(db.Text, nullable=True)         # description for UI

    # ── Connection ────────────────────────────────────────────────────────
    # For SaaS multi-tenancy, we enforce SSE (Server-Sent Events) over HTTP.
    # We do NOT allow stdio transport since running local subprocesses is not scalable/safe.
    url = db.Column(db.String(512), nullable=False)         # SSE endpoint: "https://mcp.company.com/sse"
    headers = db.Column(db.JSON, default=dict)              # Auth headers, e.g. {"Authorization": "Bearer token"}

    # ── Status ────────────────────────────────────────────────────────────
    is_active = db.Column(db.Boolean, default=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────
    company = db.relationship('Company', backref=db.backref('mcp_servers', lazy='dynamic', cascade='all, delete-orphan'))

    # ── Constraints ───────────────────────────────────────────────────────
    __table_args__ = (
        db.UniqueConstraint('company_id', 'name', name='unique_company_mcp_server'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API serialization."""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'label': self.label,
            'description': self.description,
            'url': self.url,
            # Mask sensitive headers in API responses (optional but standard security practice)
            'headers': {k: '********' for k in self.headers.keys()} if self.headers else {},
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<CompanyMCPServer {self.name} (company={self.company_id})>'
