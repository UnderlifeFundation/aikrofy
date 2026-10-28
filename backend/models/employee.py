"""
Employee Model - Company team members
=====================================
Extended with:
  - ``department_id``    → FK to departments table (nullable, backward-compat)
  - ``user_id``          → FK to users table: links to a web-dashboard account (nullable)
  - ``has_web_access``   → Boolean flag controlling dashboard access vs messaging-only
  - ``permissions``      → JSON RBAC matrix: granular access control per ERP/CRM/
                           E-Commerce/RAG/Channels/Agentic (RBAC v1.0 — 2026-08-27)

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from datetime import datetime
from enum import Enum
from extensions import db


class EmployeeRole(str, Enum):
    OWNER = 'owner'
    MANAGER = 'manager'
    SALES = 'sales'
    SUPPORT = 'support'
    ADMIN = 'admin'
    GENERAL = 'general'


class Employee(db.Model):
    """Company employee/team member"""
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey('companies.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    # ── Department containment (new — nullable for backward-compat) ────────
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

    # ── Web Dashboard Account Link (new) ──────────────────────────────────
    # When set, this employee can log in to the web interface.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        unique=True,  # one employee per web-user account
    )
    # Explicit flag: True → can log in to the web dashboard.
    # False → messaging channels only (WhatsApp, Telegram, Webchat).
    has_web_access = db.Column(db.Boolean, default=False, nullable=False)

    # ── Personal Info ─────────────────────────────────────────────────────
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    whatsapp = db.Column(db.String(50), nullable=True)

    # ── Role & Department (legacy text field kept for compatibility) ───────
    role = db.Column(db.Enum(EmployeeRole), default=EmployeeRole.GENERAL)
    department = db.Column(db.String(100), nullable=True)  # free-text label (legacy)

    # ── Availability ──────────────────────────────────────────────────────
    is_available = db.Column(db.Boolean, default=True)
    availability_hours = db.Column(
        db.JSON, default=dict
    )  # {"mon": {"start": "09:00", "end": "17:00"}, ...}

    # ── Channel Permissions ───────────────────────────────────────────────
    can_receive_calls = db.Column(db.Boolean, default=True)
    can_receive_messages = db.Column(db.Boolean, default=True)
    can_receive_escalations = db.Column(db.Boolean, default=True)

    # ── Specializations ───────────────────────────────────────────────────
    specializations = db.Column(db.JSON, default=list)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ── Status ────────────────────────────────────────────────────────────
    is_active = db.Column(db.Boolean, default=True)

    # ── RBAC Permissions Matrix (v1.0) ────────────────────────────────────
    # Granular JSON matrix defining resource-level access per employee.
    # Schema is managed by PermissionService (services/permission_service.py).
    # If NULL, PermissionService.get_defaults_for_role(employee.role) is used.
    # ─── Example shape ────────────────────────────────────────────────────
    # {
    #   "department_level": {"access_tier": "internal", ...},
    #   "integrations": {
    #       "erp": {"enabled": True, "read_products": True, ...},
    #       "crm": {"enabled": True, "read_contacts": True, ...},
    #       "ecommerce": {"enabled": False, ...},
    #       "databases_and_mcp": {"can_query_direct_db": False, ...}
    #   },
    #   "channels_and_agentic": {
    #       "can_receive_calls": True, "can_receive_escalations": True,
    #       "can_override_agent_responses": False, "can_manage_skills": False
    #   }
    # }
    permissions = db.Column(db.JSON, default=dict, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    company = db.relationship('Company', back_populates='employees')
    department_rel = db.relationship(
        'Department',
        back_populates='employees',
        foreign_keys=[department_id],
    )
    web_user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('employee_profile', uselist=False),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'department_id': self.department_id,
            'department_name': (
                self.department_rel.name if self.department_rel else self.department
            ),
            'user_id': self.user_id,
            'has_web_access': self.has_web_access,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'whatsapp': self.whatsapp,
            'role': self.role.value,
            'department': self.department,
            'is_available': self.is_available,
            'availability_hours': self.availability_hours,
            'can_receive_calls': self.can_receive_calls,
            'can_receive_messages': self.can_receive_messages,
            'can_receive_escalations': self.can_receive_escalations,
            'specializations': self.specializations,
            'permissions': self.permissions or {},
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<Employee {self.name!r}>'
