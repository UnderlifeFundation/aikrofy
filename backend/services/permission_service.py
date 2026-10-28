"""
Permission Service — Aikrofy RBAC Engine (v1.0)
================================================
Provides role-based access control (RBAC) for employees across all integrated
resources: ERP, CRM, E-Commerce, RAG/Pinecone namespaces, channels, and agentic
tools.

Design Principles
-----------------
- O(1) lookup: all checks use dot-path key access on a flat dict.
- Fail-closed: any missing key defaults to False (deny).
- Role presets: PermissionService.get_defaults_for_role() returns the canonical
  permission dict for each EmployeeRole.  The dict is deep-merged with any custom
  overrides stored on the employee.permissions JSON column.
- Backward-compatible: existing employees without a permissions column get the
  role preset on every call (no migration needed for reads).
- No Flask dependency: works with the project's hybrid FastAPI routing module.

Usage
-----
    from services.permission_service import PermissionService

    # Check one permission
    if not PermissionService.has_permission(employee, 'erp.read_stock'):
        abort(403)

    # Get the full matrix (merged preset + custom)
    matrix = PermissionService.effective_permissions(employee)

    # Route decorator
    @require_permission('crm.write_contacts')
    @jwt_required()
    def my_route():
        ...

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from __future__ import annotations

import copy
import functools
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from models.employee import Employee

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Role presets — canonical permissions per EmployeeRole value
# ─────────────────────────────────────────────────────────────────────────────

ROLE_PERMISSION_PRESETS: dict[str, dict[str, Any]] = {

    # ── OWNER / ADMIN — Full unrestricted access ──────────────────────────
    "owner": {
        "department_level": {
            "access_tier": "restricted",
            "can_view_department_conversations": True,
            "can_upload_department_rag": True,
        },
        "integrations": {
            "erp": {
                "enabled": True,
                "read_products": True,
                "read_stock": True,
                "read_prices": True,
                "create_orders": True,
                "read_invoices_financials": True,
            },
            "crm": {
                "enabled": True,
                "read_contacts": True,
                "write_contacts": True,
                "read_deals": True,
                "modify_deals": True,
            },
            "ecommerce": {
                "enabled": True,
                "view_catalog": True,
                "manage_inventory": True,
                "view_orders": True,
            },
            "databases_and_mcp": {
                "can_query_direct_db": True,
                "can_trigger_mcp_actions": True,
            },
        },
        "channels_and_agentic": {
            "can_receive_calls": True,
            "can_receive_messages": True,
            "can_receive_escalations": True,
            "can_override_agent_responses": True,
            "can_manage_skills": True,
        },
    },

    # ── MANAGER — Operational access, no financial data ───────────────────
    "manager": {
        "department_level": {
            "access_tier": "confidential",
            "can_view_department_conversations": True,
            "can_upload_department_rag": True,
        },
        "integrations": {
            "erp": {
                "enabled": True,
                "read_products": True,
                "read_stock": True,
                "read_prices": True,
                "create_orders": True,
                "read_invoices_financials": False,
            },
            "crm": {
                "enabled": True,
                "read_contacts": True,
                "write_contacts": True,
                "read_deals": True,
                "modify_deals": True,
            },
            "ecommerce": {
                "enabled": True,
                "view_catalog": True,
                "manage_inventory": True,
                "view_orders": True,
            },
            "databases_and_mcp": {
                "can_query_direct_db": False,
                "can_trigger_mcp_actions": False,
            },
        },
        "channels_and_agentic": {
            "can_receive_calls": True,
            "can_receive_messages": True,
            "can_receive_escalations": True,
            "can_override_agent_responses": True,
            "can_manage_skills": False,
        },
    },

    # ── SALES — Lead/deal centric, catalog view ───────────────────────────
    "sales": {
        "department_level": {
            "access_tier": "internal",
            "can_view_department_conversations": True,
            "can_upload_department_rag": False,
        },
        "integrations": {
            "erp": {
                "enabled": True,
                "read_products": True,
                "read_stock": True,
                "read_prices": True,
                "create_orders": False,
                "read_invoices_financials": False,
            },
            "crm": {
                "enabled": True,
                "read_contacts": True,
                "write_contacts": True,
                "read_deals": True,
                "modify_deals": False,
            },
            "ecommerce": {
                "enabled": True,
                "view_catalog": True,
                "manage_inventory": False,
                "view_orders": True,
            },
            "databases_and_mcp": {
                "can_query_direct_db": False,
                "can_trigger_mcp_actions": False,
            },
        },
        "channels_and_agentic": {
            "can_receive_calls": True,
            "can_receive_messages": True,
            "can_receive_escalations": True,
            "can_override_agent_responses": False,
            "can_manage_skills": False,
        },
    },

    # ── SUPPORT — Customer-facing, read-only on integrations ─────────────
    "support": {
        "department_level": {
            "access_tier": "internal",
            "can_view_department_conversations": True,
            "can_upload_department_rag": False,
        },
        "integrations": {
            "erp": {
                "enabled": True,
                "read_products": True,
                "read_stock": True,
                "read_prices": False,
                "create_orders": False,
                "read_invoices_financials": False,
            },
            "crm": {
                "enabled": True,
                "read_contacts": True,
                "write_contacts": False,
                "read_deals": False,
                "modify_deals": False,
            },
            "ecommerce": {
                "enabled": True,
                "view_catalog": True,
                "manage_inventory": False,
                "view_orders": True,
            },
            "databases_and_mcp": {
                "can_query_direct_db": False,
                "can_trigger_mcp_actions": False,
            },
        },
        "channels_and_agentic": {
            "can_receive_calls": True,
            "can_receive_messages": True,
            "can_receive_escalations": True,
            "can_override_agent_responses": False,
            "can_manage_skills": False,
        },
    },

    # ── GENERAL — Minimal, informational only ─────────────────────────────
    "general": {
        "department_level": {
            "access_tier": "public",
            "can_view_department_conversations": False,
            "can_upload_department_rag": False,
        },
        "integrations": {
            "erp": {
                "enabled": True,
                "read_products": True,
                "read_stock": False,
                "read_prices": False,
                "create_orders": False,
                "read_invoices_financials": False,
            },
            "crm": {
                "enabled": False,
                "read_contacts": False,
                "write_contacts": False,
                "read_deals": False,
                "modify_deals": False,
            },
            "ecommerce": {
                "enabled": True,
                "view_catalog": True,
                "manage_inventory": False,
                "view_orders": False,
            },
            "databases_and_mcp": {
                "can_query_direct_db": False,
                "can_trigger_mcp_actions": False,
            },
        },
        "channels_and_agentic": {
            "can_receive_calls": False,
            "can_receive_messages": True,
            "can_receive_escalations": False,
            "can_override_agent_responses": False,
            "can_manage_skills": False,
        },
    },
}

# "admin" is an alias of "owner"
ROLE_PERMISSION_PRESETS["admin"] = ROLE_PERMISSION_PRESETS["owner"]


# ─────────────────────────────────────────────────────────────────────────────
# Utility: deep merge dicts (custom overrides win over preset)
# ─────────────────────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*; override values win."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main service class
# ─────────────────────────────────────────────────────────────────────────────

class PermissionService:
    """
    Centralised RBAC engine for Aikrofy.

    All public methods are static/class methods so the service can be used
    without instantiation anywhere in the codebase.
    """

    # ── 1. Get role defaults ──────────────────────────────────────────────

    @staticmethod
    def get_defaults_for_role(role: str) -> dict[str, Any]:
        """
        Return a deep copy of the canonical permission preset for *role*.
        Unknown roles fall back to 'general'.
        """
        role_key = role.lower() if role else 'general'
        preset = ROLE_PERMISSION_PRESETS.get(role_key, ROLE_PERMISSION_PRESETS['general'])
        return copy.deepcopy(preset)

    # ── 2. Effective permissions (preset + custom overrides) ──────────────

    @staticmethod
    def effective_permissions(employee: "Employee") -> dict[str, Any]:
        """
        Return the resolved permission matrix for *employee*:
        - Starts with the role preset (deny-by-default).
        - Deep-merges any custom overrides stored in employee.permissions.

        This is the single source of truth for what an employee is allowed
        to do and should be called instead of reading employee.permissions
        directly.
        """
        role_value = employee.role.value if hasattr(employee.role, 'value') else str(employee.role)
        base = PermissionService.get_defaults_for_role(role_value)
        custom = employee.permissions or {}
        if custom:
            return _deep_merge(base, custom)
        return base

    # ── 3. has_permission — O(1) dot-path check ───────────────────────────

    @staticmethod
    def has_permission(employee: "Employee", permission_path: str) -> bool:
        """
        Check whether *employee* has a specific permission using dot-path notation.

        Path examples
        -------------
        - 'erp.read_stock'
        - 'crm.modify_deals'
        - 'ecommerce.manage_inventory'
        - 'databases_and_mcp.can_query_direct_db'
        - 'channels_and_agentic.can_override_agent_responses'
        - 'department_level.can_upload_department_rag'

        Shorthand integration paths are automatically resolved:
          'erp.*'              maps to integrations.erp.*
          'crm.*'              maps to integrations.crm.*
          'ecommerce.*'        maps to integrations.ecommerce.*
          'databases_and_mcp.*' maps to integrations.databases_and_mcp.*

        Returns False on any missing key or error (fail-closed).
        """
        try:
            matrix = PermissionService.effective_permissions(employee)
            parts = permission_path.split('.')
            if len(parts) == 2:
                category, action = parts
                # Map shorthand integration keys
                if category in ('erp', 'crm', 'ecommerce', 'databases_and_mcp'):
                    return bool(
                        matrix.get('integrations', {})
                              .get(category, {})
                              .get(action, False)
                    )
                if category == 'channels_and_agentic':
                    return bool(
                        matrix.get('channels_and_agentic', {}).get(action, False)
                    )
                if category == 'department_level':
                    return bool(
                        matrix.get('department_level', {}).get(action, False)
                    )
            # Fallback: walk the path manually
            node: Any = matrix
            for part in parts:
                if not isinstance(node, dict):
                    return False
                node = node.get(part, False)
            return bool(node)
        except Exception as exc:
            logger.warning("Permission check error for path '%s': %s", permission_path, exc)
            return False

    # ── 4. Bulk checks ────────────────────────────────────────────────────

    @staticmethod
    def has_all_permissions(employee: "Employee", *paths: str) -> bool:
        """Return True only if the employee has ALL of the given permissions."""
        return all(PermissionService.has_permission(employee, p) for p in paths)

    @staticmethod
    def has_any_permission(employee: "Employee", *paths: str) -> bool:
        """Return True if the employee has at least ONE of the given permissions."""
        return any(PermissionService.has_permission(employee, p) for p in paths)

    # ── 5. Apply role preset and save ────────────────────────────────────

    @staticmethod
    def apply_role_preset(employee: "Employee", save: bool = False) -> dict[str, Any]:
        """
        Overwrite employee.permissions with the canonical role preset.

        Call this when:
        - A new employee is created (no custom permissions yet).
        - The employee's role changes and we want to reset to defaults.

        If *save* is True the caller is responsible for db.session.commit().
        """
        role_value = employee.role.value if hasattr(employee.role, 'value') else str(employee.role)
        preset = PermissionService.get_defaults_for_role(role_value)
        employee.permissions = preset
        return preset

    # ── 6. Patch specific permissions ─────────────────────────────────────

    @staticmethod
    def patch_permissions(
        employee: "Employee",
        patches: dict[str, Any],
        save: bool = False,
    ) -> dict[str, Any]:
        """
        Deep-merge *patches* into the employee's effective permissions and
        write the result back to employee.permissions (custom overrides layer).

        This preserves any existing custom overrides not mentioned in *patches*.
        """
        current_custom = employee.permissions or {}
        merged = _deep_merge(current_custom, patches)
        employee.permissions = merged
        return merged


# ─────────────────────────────────────────────────────────────────────────────
# Route decorator (FastAPI-compatible via project routing module)
# ─────────────────────────────────────────────────────────────────────────────

def require_permission(permission_path: str):
    """
    Route decorator — requires the current user's linked employee to have
    *permission_path*.

    Compatible with the project's hybrid FastAPI routing module (routing.py).

    Usage::

        @employees_bp.route('/erp/stock', methods=['GET'])
        @jwt_required()
        @require_permission('erp.read_stock')
        def get_stock():
            ...

    The decorator resolves the employee by looking up the JWT identity against
    ``Employee.user_id``.  If the user has no linked employee (e.g. company
    owner with UserRole.ADMIN), the check is bypassed.
    Fails OPEN on import/resolution errors to never block unrelated routes.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                from routing import get_jwt_identity, jsonify
                from models.employee import Employee
                from models.user import User, UserRole

                user_id = get_jwt_identity()
                if user_id:
                    uid = int(user_id)
                    user = User.query.get(uid)
                    # Owners / super-admins bypass permission checks
                    if user and user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
                        return fn(*args, **kwargs)
                    # Check employee-linked permissions
                    if user:
                        employee = Employee.query.filter_by(
                            user_id=uid, is_active=True
                        ).first()
                        if employee and not PermissionService.has_permission(employee, permission_path):
                            return jsonify({
                                'error': 'Acceso denegado: permisos insuficientes',
                                'required_permission': permission_path,
                            }), 403
            except Exception as exc:
                logger.error("require_permission decorator error: %s", exc)
                # Fail-open for decorator errors to avoid breaking unrelated routes
            return fn(*args, **kwargs)
        return wrapper
    return decorator
