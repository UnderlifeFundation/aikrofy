"""
Employee Management Routes — Extended for Enterprise Departments
================================================================
Replaces the original 144-line employees.py with a fully-featured version that
supports:
  - Department assignment via ``department_id``
  - Web-dashboard account provisioning (``has_web_access``, ``user_id``)
  - Plan quota enforcement via EnterpriseLimits
  - Granular permission fields (``can_receive_calls``, etc.)
  - Filtering by department, role, and availability

Hierarchy Enforcement (v2.0 — 2026-08-29)
------------------------------------------
  • Only the company OWNER (is_company_owner=True) or platform SUPER_ADMIN may:
      - Provision / revoke web dashboard access (has_web_access toggle)
      - Create employees with role ADMIN
      - Delete employees that have an ADMIN-level user account
  • Delegated ADMINs may:
      - Create / edit / delete employees with role < ADMIN (managers, sales,
        support, general)
      - Edit employees that already have web access (but not add/remove it)
  • MANAGERs may read only.

Prefix: /api/employees
Auth:   JWT required on all routes.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request

from extensions import db
from models.user import User, UserRole
from models.company import Company
from models.employee import Employee, EmployeeRole
from services.permission_service import PermissionService
from services.auth_guard import (
    can_manage_employees,
    can_grant_web_access,
    can_manage_target_user,
    can_delete_admin_user,
    is_admin_or_above,
    is_company_root,
)

employees_bp = APIRouter('employees', __name__)


# ── Internal helpers ───────────────────────────────────────────────────────

def _get_user_company():
    """Helper to get current user's company."""
    user_id = get_jwt_identity()
    try:
        uid = int(user_id)
        user = User.query.get(uid)
        if not user or not user.company:
            return None, None
        return user, user.company
    except Exception:
        return None, None


def _check_admin(user: User) -> bool:
    """True for ADMIN and above (backward-compat helper)."""
    return user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER)


def _resolve_linked_user(employee_id: int):
    """Return the linked User for an employee, or None."""
    emp = Employee.query.get(employee_id)
    if emp and emp.user_id:
        return User.query.get(emp.user_id)
    return None


# ── Routes ─────────────────────────────────────────────────────────────────

@employees_bp.route('/', methods=['GET'])
@jwt_required()
def get_employees():
    """
    GET /api/employees/
    List all employees for the company.

    Query params (all optional):
      department_id  (int)  — filter by department
      role           (str)  — filter by role enum value
      is_active      (bool) — default True; pass 'all' to include inactive
      has_web_access (bool) — filter web-dashboard vs messaging-only users
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    query = Employee.query.filter_by(company_id=company.id)

    # Filters
    dept_id = request.args.get('department_id', type=int)
    if dept_id is not None:
        query = query.filter_by(department_id=dept_id)

    role_filter = request.args.get('role')
    if role_filter:
        try:
            query = query.filter_by(role=EmployeeRole(role_filter))
        except ValueError:
            return jsonify({'error': f"Invalid role: {role_filter}"}), 400

    is_active_param = request.args.get('is_active', 'true').lower()
    if is_active_param != 'all':
        is_active = is_active_param not in ('false', '0')
        query = query.filter_by(is_active=is_active)

    has_web = request.args.get('has_web_access')
    if has_web is not None:
        query = query.filter_by(has_web_access=has_web.lower() not in ('false', '0'))

    employees = query.order_by(Employee.name).all()

    # Enrich each employee dict with linked user's role so the frontend
    # can display the appropriate controls.
    result = []
    for e in employees:
        d = e.to_dict()
        if e.user_id:
            linked_user = User.query.get(e.user_id)
            if linked_user:
                d['linked_user_role'] = linked_user.role.value
                d['linked_user_is_owner'] = bool(linked_user.is_company_owner)
        result.append(d)

    return jsonify({
        'employees': result,
        'total': len(result),
    })


@employees_bp.route('/', methods=['POST'])
@jwt_required()
def add_employee():
    """
    POST /api/employees/
    Add a new employee. Enforces plan quota and hierarchy rules.

    Body:
      name                  (str, required)
      email                 (str, optional)
      phone                 (str, optional)
      whatsapp              (str, optional)
      role                  (str, default 'general')
      department_id         (int, optional) — link to a Department
      department            (str, optional) — legacy free-text (kept for compat)
      is_available          (bool, default True)
      can_receive_calls     (bool, default True)
      can_receive_messages  (bool, default True)
      can_receive_escalations (bool, default True)
      specializations       (list, default [])
      has_web_access        (bool, default False) — provision a web login
        → ONLY allowed if the caller is the company owner or super-admin.
      web_email             (str) — required only when has_web_access=True AND no existing account
      web_password          (str) — required only when has_web_access=True AND no existing account
      web_role              (str) — user role to assign (default 'employee').
        → Assigning 'admin' requires caller to be company owner.
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not can_manage_employees(user):
        return jsonify({'error': 'Se requieren privilegios de administrador para crear empleados'}), 403

    data = request.get_json() or {}

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Plan quota
    try:
        from services.enterprise_limits import EnterpriseLimits, PlanQuotaExceeded
        EnterpriseLimits.check_employee_quota(company)
    except PlanQuotaExceeded as exc:
        return jsonify({
            'error': str(exc),
            'code': 'QUOTA_EXCEEDED',
            'resource': exc.resource,
            'limit': exc.limit,
            'plan': exc.plan,
        }), 402

    # Validate role
    try:
        role = EmployeeRole(data.get('role', 'general'))
    except ValueError:
        return jsonify({'error': f"Invalid role: {data.get('role')}"}), 400

    # Validate department_id if provided
    dept_id = data.get('department_id')
    if dept_id:
        from models.department import Department
        dept = Department.query.filter_by(id=dept_id, company_id=company.id, is_active=True).first()
        if not dept:
            return jsonify({'error': 'Department not found or not active'}), 404

    # ── Web access guard ───────────────────────────────────────────────
    has_web_access = bool(data.get('has_web_access', False))
    web_user_id = None

    if has_web_access:
        # Only the company owner / super-admin can grant dashboard access
        if not can_grant_web_access(user):
            return jsonify({
                'error': 'Solo el propietario de la cuenta puede habilitar el acceso al dashboard para los empleados'
            }), 403

        web_email = (data.get('web_email') or data.get('email') or '').strip()
        web_password = (data.get('web_password') or '').strip()

        if not web_email:
            return jsonify({
                'error': 'web_email is required when has_web_access is True'
            }), 400

        # Determine the role to assign to the web user.
        # Admins can only be created by the company owner.
        web_role_str = (data.get('web_role') or 'employee').lower()
        if web_role_str == 'admin' and not is_company_root(user):
            return jsonify({
                'error': 'Solo el propietario de la cuenta puede crear usuarios con rol de administrador'
            }), 403

        try:
            web_role = UserRole(web_role_str)
        except ValueError:
            web_role = UserRole.EMPLOYEE

        # Check if account already exists
        existing_user = User.query.filter_by(email=web_email).first()
        if existing_user:
            if existing_user.company_id != company.id:
                return jsonify({
                    'error': 'That email is already associated with a different company'
                }), 409
            # Re-use existing user account
            web_user_id = existing_user.id
        else:
            if not web_password or len(web_password) < 8:
                return jsonify({
                    'error': 'web_password must be at least 8 characters when creating a new account'
                }), 400

            new_web_user = User(
                email=web_email,
                name=name,
                role=web_role,
                company_id=company.id,
                is_active=True,
                # is_company_owner stays False — only the founding registration sets it
            )
            new_web_user.set_password(web_password)
            db.session.add(new_web_user)
            db.session.flush()  # get ID before commit
            web_user_id = new_web_user.id

    try:
        employee = Employee(
            company_id=company.id,
            department_id=dept_id or None,
            user_id=web_user_id,
            has_web_access=has_web_access,
            name=name,
            email=data.get('email'),
            phone=data.get('phone'),
            whatsapp=data.get('whatsapp'),
            role=role,
            department=data.get('department'),
            is_available=data.get('is_available', True),
            can_receive_calls=data.get('can_receive_calls', True),
            can_receive_messages=data.get('can_receive_messages', True),
            can_receive_escalations=data.get('can_receive_escalations', True),
            specializations=data.get('specializations', []),
        )

        # ── Auto-assign role permission preset ─────────────────────────
        PermissionService.apply_role_preset(employee)
        # Merge any custom permission overrides sent in the payload
        custom_perms = data.get('permissions')
        if custom_perms and isinstance(custom_perms, dict):
            PermissionService.patch_permissions(employee, custom_perms)

        # Sync legacy department text from department FK
        if dept_id:
            from models.department import Department
            dept_obj = Department.query.get(dept_id)
            if dept_obj:
                employee.department = dept_obj.name

        db.session.add(employee)
        db.session.commit()

        return jsonify({
            'message': 'Employee added successfully',
            'employee': employee.to_dict(),
        }), 201

    except ValueError:
        db.session.rollback()
        return jsonify({'error': 'Invalid role value'}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@employees_bp.route('/<int:employee_id>', methods=['GET'])
@jwt_required()
def get_employee(employee_id):
    """GET /api/employees/<id> — fetch a single employee."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    employee = Employee.query.filter_by(id=employee_id, company_id=company.id).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    d = employee.to_dict()
    if employee.user_id:
        linked_user = User.query.get(employee.user_id)
        if linked_user:
            d['linked_user_role'] = linked_user.role.value
            d['linked_user_is_owner'] = bool(linked_user.is_company_owner)

    return jsonify({'employee': d})


@employees_bp.route('/<int:employee_id>', methods=['PUT'])
@jwt_required()
def update_employee(employee_id):
    """
    PUT /api/employees/<id>
    Update an employee record.  All fields are optional.

    Hierarchy rules:
      - `has_web_access` toggle: only company owner / super-admin
      - `web_role` change to 'admin': only company owner / super-admin
      - Editing an employee whose linked user is an admin: only owner / super-admin
      - Changing department_id also syncs the legacy text field.
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    employee = Employee.query.filter_by(id=employee_id, company_id=company.id).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    if not can_manage_employees(user):
        return jsonify({'error': 'Se requieren privilegios de administrador'}), 403

    # Check if the target employee's linked user is an admin (owner or delegated).
    # Only the company root can edit such employees.
    if employee.user_id:
        linked_user = User.query.get(employee.user_id)
        if linked_user and linked_user.role == UserRole.ADMIN:
            if not is_company_root(user):
                return jsonify({
                    'error': 'Solo el propietario de la cuenta puede editar empleados con rol de administrador'
                }), 403

    data = request.get_json() or {}

    try:
        if 'name' in data:
            employee.name = data['name']
        if 'email' in data:
            employee.email = data['email']
        if 'phone' in data:
            employee.phone = data['phone']
        if 'whatsapp' in data:
            employee.whatsapp = data['whatsapp']
        if 'role' in data:
            new_role = EmployeeRole(data['role'])
            # If role changed → re-apply the canonical preset so permissions
            # reflect the new role (custom overrides from the new payload still apply).
            if new_role != employee.role:
                employee.role = new_role
                PermissionService.apply_role_preset(employee)
            else:
                employee.role = new_role
        if 'department' in data:
            employee.department = data['department']
        if 'department_id' in data:
            dept_id = data['department_id']
            if dept_id:
                from models.department import Department
                dept_obj = Department.query.filter_by(
                    id=dept_id, company_id=company.id, is_active=True
                ).first()
                if not dept_obj:
                    return jsonify({'error': 'Department not found or not active'}), 404
                employee.department_id = dept_id
                employee.department = dept_obj.name  # sync legacy field
            else:
                employee.department_id = None
        if 'is_available' in data:
            employee.is_available = bool(data['is_available'])
        if 'availability_hours' in data:
            employee.availability_hours = data['availability_hours']
        if 'can_receive_calls' in data:
            employee.can_receive_calls = bool(data['can_receive_calls'])
        if 'can_receive_messages' in data:
            employee.can_receive_messages = bool(data['can_receive_messages'])
        if 'can_receive_escalations' in data:
            employee.can_receive_escalations = bool(data['can_receive_escalations'])
        if 'specializations' in data:
            employee.specializations = data['specializations']
        if 'is_active' in data:
            employee.is_active = bool(data['is_active'])

        # ── Web access provisioning/deprovisioning ──────────────────────
        if 'has_web_access' in data:
            # Only the company owner / super-admin can change this flag
            if not can_grant_web_access(user):
                return jsonify({
                    'error': 'Solo el propietario de la cuenta puede habilitar o deshabilitar el acceso al dashboard'
                }), 403

            new_web = bool(data['has_web_access'])
            if new_web and not employee.user_id:
                # Provision new web account if credentials provided
                web_email = (data.get('web_email') or data.get('email') or employee.email or '').strip()
                web_password = (data.get('web_password') or '').strip()

                # Determine role for the new account
                web_role_str = (data.get('web_role') or 'employee').lower()
                if web_role_str == 'admin' and not is_company_root(user):
                    return jsonify({
                        'error': 'Solo el propietario puede crear cuentas con rol de administrador'
                    }), 403
                try:
                    web_role = UserRole(web_role_str)
                except ValueError:
                    web_role = UserRole.EMPLOYEE

                if web_email and web_password and len(web_password) >= 8:
                    existing_user = User.query.filter_by(email=web_email).first()
                    if existing_user:
                        if existing_user.company_id == company.id:
                            employee.user_id = existing_user.id
                            employee.has_web_access = True
                    else:
                        new_web_user = User(
                            email=web_email,
                            name=employee.name,
                            role=web_role,
                            company_id=company.id,
                            is_active=True,
                        )
                        new_web_user.set_password(web_password)
                        db.session.add(new_web_user)
                        db.session.flush()
                        employee.user_id = new_web_user.id
                        employee.has_web_access = True
                elif employee.user_id:
                    employee.has_web_access = True
            elif not new_web and employee.user_id:
                # Deactivate web account (keep User record but mark inactive)
                linked_user = User.query.get(employee.user_id)
                if linked_user:
                    # Never deactivate the company owner account through employee management
                    if linked_user.is_company_owner:
                        return jsonify({
                            'error': 'No se puede deshabilitar el acceso del propietario de la cuenta'
                        }), 403
                    linked_user.is_active = False
                employee.has_web_access = False
            else:
                employee.has_web_access = new_web

        # ── Permissions patch ───────────────────────────────────────────
        if 'permissions' in data and isinstance(data['permissions'], dict):
            PermissionService.patch_permissions(employee, data['permissions'])

        db.session.commit()

        return jsonify({
            'message': 'Employee updated successfully',
            'employee': employee.to_dict(),
        })

    except ValueError:
        db.session.rollback()
        return jsonify({'error': 'Invalid role value'}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@employees_bp.route('/<int:employee_id>', methods=['DELETE'])
@jwt_required()
def delete_employee(employee_id):
    """
    DELETE /api/employees/<id>
    Hard-delete an employee.  Also deactivates the linked web account if any.

    Hierarchy rules:
      - Deleting an employee with a linked ADMIN user requires the caller
        to be the company owner or platform super-admin.
      - The company owner's own employee record cannot be deleted.
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not can_manage_employees(user):
        return jsonify({'error': 'Se requieren privilegios de administrador'}), 403

    employee = Employee.query.filter_by(id=employee_id, company_id=company.id).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    # Check linked user permissions
    if employee.user_id:
        linked_user = User.query.get(employee.user_id)
        if linked_user:
            # Never delete the company owner's employee record
            if linked_user.is_company_owner:
                return jsonify({
                    'error': 'No se puede eliminar el empleado vinculado al propietario de la cuenta'
                }), 403
            # Deleting an admin-linked employee requires owner/super-admin
            if linked_user.role == UserRole.ADMIN:
                if not can_delete_admin_user(user, linked_user):
                    return jsonify({
                        'error': 'Solo el propietario de la cuenta puede eliminar empleados con rol de administrador'
                    }), 403

    try:
        # Deactivate web account if linked (unless it's the owner)
        if employee.user_id:
            linked_user = User.query.get(employee.user_id)
            if linked_user and not linked_user.is_company_owner:
                linked_user.is_active = False

        db.session.delete(employee)
        db.session.commit()
        return jsonify({'message': 'Employee deleted successfully'})

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@employees_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_employee_roles():
    """
    GET /api/employees/roles
    Returns the available employee roles and their descriptions.
    Used by the frontend for dropdown population.
    """
    roles = [
        {'value': r.value, 'label': r.value.capitalize()} for r in EmployeeRole
    ]
    return jsonify({'roles': roles})


@employees_bp.route('/role-presets', methods=['GET'])
@jwt_required()
def get_role_presets():
    """
    GET /api/employees/role-presets
    Returns the canonical permission presets for all roles.
    Used by the frontend PermissionsModal to show/apply defaults.
    """
    from services.permission_service import ROLE_PERMISSION_PRESETS
    return jsonify({'presets': ROLE_PERMISSION_PRESETS})


@employees_bp.route('/<int:employee_id>/permissions', methods=['GET'])
@jwt_required()
def get_employee_permissions(employee_id):
    """
    GET /api/employees/<id>/permissions
    Returns the effective (resolved) permissions for an employee.
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    employee = Employee.query.filter_by(id=employee_id, company_id=company.id).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    effective = PermissionService.effective_permissions(employee)
    return jsonify({
        'employee_id': employee_id,
        'role': employee.role.value,
        'custom_overrides': employee.permissions or {},
        'effective_permissions': effective,
    })


@employees_bp.route('/<int:employee_id>/permissions', methods=['PATCH'])
@jwt_required()
def patch_employee_permissions(employee_id):
    """
    PATCH /api/employees/<id>/permissions
    Deep-merge a permissions dict into the employee's custom overrides.

    Body:
      {
        "permissions": { ... },     # nested permission patches
        "reset_to_role_preset": false  # if true, clears custom overrides first
      }
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not can_manage_employees(user):
        return jsonify({'error': 'Se requieren privilegios de administrador'}), 403

    employee = Employee.query.filter_by(id=employee_id, company_id=company.id).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    # Patching permissions for an admin-linked employee requires owner
    if employee.user_id:
        linked_user = User.query.get(employee.user_id)
        if linked_user and linked_user.role == UserRole.ADMIN and not is_company_root(user):
            return jsonify({
                'error': 'Solo el propietario puede modificar los permisos de administradores'
            }), 403

    data = request.get_json() or {}
    reset = bool(data.get('reset_to_role_preset', False))

    try:
        if reset:
            # Completely reset to role defaults (clears all custom overrides)
            PermissionService.apply_role_preset(employee)
        else:
            patches = data.get('permissions', {})
            if not isinstance(patches, dict):
                return jsonify({'error': "'permissions' must be an object"}), 400
            PermissionService.patch_permissions(employee, patches)

        db.session.commit()

        return jsonify({
            'message': 'Permissions updated successfully',
            'employee_id': employee_id,
            'effective_permissions': PermissionService.effective_permissions(employee),
        })

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@employees_bp.route('/<int:employee_id>/grant-dashboard-access', methods=['POST'])
@jwt_required()
def grant_dashboard_access(employee_id):
    """
    POST /api/employees/<id>/grant-dashboard-access
    Owner-only endpoint to grant or revoke an employee's dashboard login.

    Body:
      {
        "grant": true,            # true = enable, false = revoke
        "web_email": "...",       # required only if granting and no account exists
        "web_password": "...",    # required only if creating a new account
        "web_role": "employee"    # user role ('admin' only allowed for owners)
      }
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    # Only company owner / super-admin may use this endpoint
    if not can_grant_web_access(user):
        return jsonify({
            'error': 'Solo el propietario de la cuenta puede habilitar o deshabilitar el acceso al dashboard'
        }), 403

    employee = Employee.query.filter_by(id=employee_id, company_id=company.id).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    data = request.get_json() or {}
    grant = bool(data.get('grant', True))

    try:
        if grant:
            if employee.user_id:
                # Already has an account — just activate it
                linked_user = User.query.get(employee.user_id)
                if linked_user:
                    linked_user.is_active = True
                employee.has_web_access = True
            else:
                # Create a new web account
                web_email = (data.get('web_email') or employee.email or '').strip()
                web_password = (data.get('web_password') or '').strip()

                if not web_email:
                    return jsonify({'error': 'web_email is required'}), 400
                if not web_password or len(web_password) < 8:
                    return jsonify({'error': 'web_password must be at least 8 characters'}), 400

                web_role_str = (data.get('web_role') or 'employee').lower()
                if web_role_str == 'admin' and not is_company_root(user):
                    return jsonify({
                        'error': 'Solo el propietario puede crear cuentas con rol de administrador'
                    }), 403
                try:
                    web_role = UserRole(web_role_str)
                except ValueError:
                    web_role = UserRole.EMPLOYEE

                existing_user = User.query.filter_by(email=web_email).first()
                if existing_user:
                    if existing_user.company_id != company.id:
                        return jsonify({'error': 'Email ya registrado en otra empresa'}), 409
                    employee.user_id = existing_user.id
                    existing_user.is_active = True
                else:
                    new_user = User(
                        email=web_email,
                        name=employee.name,
                        role=web_role,
                        company_id=company.id,
                        is_active=True,
                    )
                    new_user.set_password(web_password)
                    db.session.add(new_user)
                    db.session.flush()
                    employee.user_id = new_user.id

                employee.has_web_access = True

        else:
            # Revoke access
            if employee.user_id:
                linked_user = User.query.get(employee.user_id)
                if linked_user:
                    if linked_user.is_company_owner:
                        return jsonify({
                            'error': 'No se puede revocar el acceso del propietario de la cuenta'
                        }), 403
                    linked_user.is_active = False
            employee.has_web_access = False

        db.session.commit()

        return jsonify({
            'message': f"Dashboard access {'granted' if grant else 'revoked'} successfully",
            'employee': employee.to_dict(),
        })

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500
