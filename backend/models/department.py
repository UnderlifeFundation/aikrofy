"""
Department Model — Enterprise Multi-Tenant Data Containment
========================================================
A department is a sub-unit of a Company (tenant). It allows enterprise
customers to:
  - Isolate their RAG knowledge base (Pinecone namespace) per department.
  - Restrict which employees can access which conversations.
  - Apply role-based permissions for web dashboard vs messaging-only access.

Hierarchy:
    Company (tenant)
        └── Department (sub-container)
              └── Employee (team member)

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from datetime import datetime
from extensions import db


class Department(db.Model):
    """
    Department model — sub-tenant data container within a Company.

    Each department has its own isolated Pinecone namespace so that
    documents uploaded for 'Finance' are never queried by 'Sales' agents,
    and vice versa.  The namespace pattern is:

        company_{company_id}_dept_{department_id}

    When ``pinecone_namespace`` is explicitly set on the record it takes
    precedence; otherwise it is auto-generated from the IDs above.
    """

    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)

    # ── Parent Tenant ─────────────────────────────────────────────────────
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # ── RAG Containment ───────────────────────────────────────────────────
    # Override for explicit namespace; if None, the auto-generated one is used.
    pinecone_namespace = db.Column(db.String(255), nullable=True)

    # ── Access Policy ─────────────────────────────────────────────────────
    # If True, only employees belonging to this department can read its
    # conversations inside the web dashboard.
    restrict_conversations = db.Column(db.Boolean, default=False, nullable=False)

    # ── RBAC Department-Level Data Policies (v1.0) ────────────────────────
    # data_access_tier: Controls the sensitivity classification of documents
    # uploaded to this department's RAG namespace.
    #   "public"       → Any employee or agent can query this namespace.
    #   "internal"     → Only department employees + managers can query.
    #   "confidential" → Only department employees with explicit permission.
    #   "restricted"   → Only owner/admin; never exposed to agents.
    data_access_level = db.Column(
        db.String(20), default='internal', nullable=False
    )

    # allowed_integrations: JSON list of integration slugs enabled for this dept.
    # Example: ["odoo", "hubspot", "shopify"]
    # An empty list means the department inherits the company-level integrations.
    allowed_integrations = db.Column(db.JSON, default=list, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ── Relationships ─────────────────────────────────────────────────────
    company = db.relationship("Company", back_populates="departments")
    employees = db.relationship(
        "Employee",
        back_populates="department_rel",
        lazy="dynamic",
        foreign_keys="Employee.department_id",
    )

    # ── Helpers ───────────────────────────────────────────────────────────
    def get_pinecone_namespace(self) -> str:
        """
        Returns the effective Pinecone namespace for this department.

        If an explicit namespace has been set, return it.
        Otherwise, derive it automatically from company + department IDs
        so it is always unique and predictable.
        """
        if self.pinecone_namespace:
            return self.pinecone_namespace
        return f"company_{self.company_id}_dept_{self.id}"

    def get_global_namespace(self) -> str:
        """
        Returns the company-level (shared) Pinecone namespace.

        During RAG queries for employees in this department, the agent
        should search BOTH ``get_pinecone_namespace()`` AND this namespace
        so that company-wide knowledge is also available.
        """
        if self.company and self.company.pinecone_namespace:
            return self.company.pinecone_namespace
        return f"company_{self.company_id}"

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dictionary."""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "description": self.description,
            "pinecone_namespace": self.get_pinecone_namespace(),
            "restrict_conversations": self.restrict_conversations,
            "data_access_level": self.data_access_level or 'internal',
            "allowed_integrations": self.allowed_integrations or [],
            "is_active": self.is_active,
            "employee_count": self.employees.filter_by(is_active=True).count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Department {self.name!r} (company={self.company_id})>"
