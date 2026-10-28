"""
User Model - Admin users and company employees

Hierarchy (highest → lowest):
  SUPER_ADMIN  — Platform superadmin (Aikrofy staff only)
  ADMIN        — Company owner/admin role (set at registration)
  MANAGER      — Delegated manager
  EMPLOYEE     — Dashboard-access employee (created by owner/admin)

The `is_company_owner` flag distinguishes the ROOT account of a company
(the person who registered) from delegated admins.  Rules:
  - Only the owner can: create/delete ADMIN-level users, grant/revoke
    `has_web_access` on any employee, and transfer ownership.
  - Delegated admins have full operational access but cannot manage
    other admins or grant dashboard access.
"""
from datetime import datetime
from enum import Enum
import bcrypt
from extensions import db


class UserRole(str, Enum):
    SUPER_ADMIN = 'super_admin'
    AGENCY = 'agency'
    ADMIN = 'admin'
    MANAGER = 'manager'
    EMPLOYEE = 'employee'


class User(db.Model):
    """User account model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.ADMIN, nullable=False)

    # ── Ownership flag ────────────────────────────────────────────────────
    # True ONLY for the user who originally registered the company account.
    # There is exactly one owner per company.  Platform super-admins always
    # bypass this check (they are implicitly treated as owners).
    is_company_owner = db.Column(db.Boolean, default=False, nullable=False)

    # Company relationship
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    company = db.relationship('Company', back_populates='users')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_beta_approved = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Integrations
    google_credentials = db.Column(db.JSON, nullable=True)
    
    # Real-Time IP Telemetry & GPS Geolocation
    last_ip = db.Column(db.String(64), nullable=True)
    last_ip_lat = db.Column(db.Float, nullable=True)
    last_ip_lng = db.Column(db.Float, nullable=True)
    last_ip_city = db.Column(db.String(100), nullable=True)
    last_ip_country = db.Column(db.String(100), nullable=True)
    last_ip_country_code = db.Column(db.String(10), nullable=True)
    last_ip_isp = db.Column(db.String(255), nullable=True)
    last_ip_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Physical Hardware Device Telemetry
    last_device_id = db.Column(db.String(100), nullable=True)
    last_device_name = db.Column(db.String(255), nullable=True)
    last_device_type = db.Column(db.String(50), nullable=True)
    last_gps_lat = db.Column(db.Float, nullable=True)
    last_gps_lng = db.Column(db.Float, nullable=True)
    has_hardware_gps = db.Column(db.Boolean, default=False, nullable=True)
    last_gps_accuracy = db.Column(db.Float, nullable=True)
    last_gps_speed = db.Column(db.Float, nullable=True)
    last_gps_heading = db.Column(db.Float, nullable=True)
    location_consent = db.Column(db.String(50), default='unknown', nullable=True)

    # ── Convenience properties ────────────────────────────────────────────

    @property
    def is_root(self) -> bool:
        """True if this user is the platform super-admin OR the company owner."""
        return self.role == UserRole.SUPER_ADMIN or bool(self.is_company_owner)

    @property
    def is_admin_or_above(self) -> bool:
        """True for owner + delegated admins (role ADMIN) and platform super-admins."""
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password):
        """Verify password"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
    
    def to_dict(self):
        """Convert to dictionary"""
        role_val = self.role.value if hasattr(self.role, 'value') else str(self.role or 'admin')
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': role_val,
            'is_company_owner': bool(self.is_company_owner),
            'company_id': self.company_id,
            'is_active': bool(self.is_active),
            'is_beta_approved': bool(self.is_beta_approved),
            'has_hardware_gps': bool(self.has_hardware_gps),
            'location_consent': self.location_consent or 'unknown',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
    
    def __repr__(self):
        return f'<User {self.email}>'
