"""
Authorization Service — Aikrofy Hierarchy Guard (v1.0)
=======================================================
Centralised role-hierarchy enforcement.  All route-level permission checks
for user management, dashboard-access provisioning and employee lifecycle
should call helpers from this module instead of duplicating logic.

Hierarchy (highest → lowest):
  SUPER_ADMIN / platform level  — can do anything
  Company Owner (is_company_owner=True, role=ADMIN)
      → can create/delete ADMIN users inside their own company
      → sole authority to grant/revoke `has_web_access` for employees
      → sole authority to delete or demote other admins
  Delegated Admin (role=ADMIN, is_company_owner=False)
      → full operational access (modules, integrations, configuration)
      → can create/delete/edit employees with role < ADMIN
      → CANNOT manage other admins, cannot grant/revoke dashboard access
  Manager (role=MANAGER)
      → limited: can read, no destructive actions on users
  Employee (role=EMPLOYEE)
      → only their own profile

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.user import User

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Role ordering (higher number = more privilege)
# ─────────────────────────────────────────────────────────────────────────────

_ROLE_RANK = {
    'employee': 1,
    'manager': 2,
    'admin': 3,       # covers both owner and delegated admin
    'super_admin': 10,
}


def _rank(user: "User") -> int:
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role or 'employee')
    return _ROLE_RANK.get(role_val.lower(), 0)


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_platform_superadmin(user: "User") -> bool:
    """True for platform-level super admins (Aikrofy staff)."""
    from models.user import UserRole
    return user.role == UserRole.SUPER_ADMIN


def is_company_root(user: "User") -> bool:
    """
    True if the user is effectively the root of their company account.
    This is the platform super-admin OR the original account owner
    (is_company_owner flag).
    """
    return is_platform_superadmin(user) or bool(user.is_company_owner)


def is_admin_or_above(user: "User") -> bool:
    """True for any admin (owner or delegated) and super-admins."""
    from models.user import UserRole
    return user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)


def can_manage_employees(user: "User") -> bool:
    """
    True if the user can create / update / delete employee records.
    Both delegated admins and owners have this right.
    Managers can read but not create/delete.
    """
    from models.user import UserRole
    return user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN)


def can_grant_web_access(user: "User") -> bool:
    """
    True if the user can toggle `has_web_access` on employee records,
    which effectively controls who can log in to the dashboard.
    ONLY the company root (owner) and platform super-admins may do this.
    """
    return is_company_root(user)


def can_manage_target_user(actor: "User", target: "User") -> bool:
    """
    Return True if `actor` is allowed to create, update, or delete `target`.

    Rules
    -----
    - Platform super-admin can manage anyone.
    - Company owner can manage any user in their own company (except other owners).
    - Delegated admin can only manage users with strictly lower role rank
      (i.e. managers and employees, NOT other admins or the owner).
    - A user cannot manage themselves for role/owner changes (they can update
      their own profile through /auth/me).
    """
    if is_platform_superadmin(actor):
        return True

    # Must be in the same company
    if actor.company_id != target.company_id:
        return False

    # Nobody can touch the root owner through employee management routes
    if target.is_company_owner and not is_platform_superadmin(actor):
        return False

    if is_company_root(actor):
        # Owner can manage anyone in the same company except another owner
        return not target.is_company_owner

    # Delegated admin: can only manage strictly lower-ranked users
    if is_admin_or_above(actor):
        return _rank(target) < _rank(actor)

    return False


def can_delete_admin_user(actor: "User", target: "User") -> bool:
    """
    True if `actor` may delete a user with ADMIN role.
    Only the company owner (root) and platform super-admins may do this.
    """
    if is_platform_superadmin(actor):
        return True
    if is_company_root(actor) and actor.company_id == target.company_id:
        # Owner can delete delegated admins but not themselves
        return actor.id != target.id and not target.is_company_owner
    return False


def assert_can_manage_employee(actor: "User", target_user: "User | None" = None) -> None:
    """
    Raise PermissionError if `actor` cannot manage employees in general,
    or cannot manage the specific `target_user` if provided.

    Call this in route handlers before performing write operations.
    """
    if not can_manage_employees(actor):
        raise PermissionError("Se requieren privilegios de administrador para gestionar empleados.")

    if target_user is not None and not can_manage_target_user(actor, target_user):
        raise PermissionError(
            "No tiene permisos para gestionar este usuario. "
            "Solo el propietario de la cuenta puede gestionar administradores."
        )


def jsonify_permission_error(message: str):
    """Import-safe jsonify for permission error responses."""
    try:
        from routing import jsonify
        return jsonify({'error': message}), 403
    except ImportError:
        # Fallback for test contexts
        return {'error': message}, 403
