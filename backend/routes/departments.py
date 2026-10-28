"""
Department Management Routes — Enterprise Feature
==================================================
Provides CRUD endpoints for Company Departments under the Enterprise plan.

Prefix: /api/departments
Auth:   JWT required on all routes.

Endpoints:
  GET    /               — list all departments for the company
  POST   /               — create a new department (quota-checked)
  GET    /<id>           — get a specific department with its employees
  PUT    /<id>           — update a department
  DELETE /<id>           — soft-delete (is_active=False) a department
  GET    /usage          — get current department/employee quota usage
  POST   /<id>/employees — add an employee to a specific department
  DELETE /<id>/employees/<eid> — remove employee from department (unassign)

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request

from extensions import db
from models.user import User, UserRole
from models.company import Company
from models.department import Department
from models.employee import Employee, EmployeeRole
from services.auth_guard import can_manage_employees, is_admin_or_above

departments_bp = APIRouter('departments', __name__)


# ── Internal helpers ───────────────────────────────────────────────────────

def _get_user_and_company():
    """
    Returns (user, company) for the JWT-authenticated request.
    Returns (None, None) on any failure.
    """
    user_id = get_jwt_identity()
    try:
        user = User.query.get(int(user_id))
        if not user or not user.company:
            return None, None
        return user, user.company
    except Exception:
        return None, None


def _get_department(dept_id: int, company_id: int):
    """Fetch a department verifying company ownership."""
    return Department.query.filter_by(
        id=dept_id, company_id=company_id
    ).first()


def _check_admin(user: User):
    """Return True if user has admin-level access (delegated or owner)."""
    return can_manage_employees(user)


# ── Routes ─────────────────────────────────────────────────────────────────

@departments_bp.route('/', methods=['GET'])
@jwt_required()
def list_departments():
    """
    GET /api/departments/
    List all active departments for the authenticated company.
    Includes per-department employee count and namespace info.
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    departments = Department.query.filter_by(
        company_id=company.id
    ).order_by(Department.name).all()

    return jsonify({
        'departments': [d.to_dict() for d in departments],
        'total': len(departments),
    })


@departments_bp.route('/', methods=['POST'])
@jwt_required()
def create_department():
    """
    POST /api/departments/
    Create a new department.  Enforces plan quota via EnterpriseLimits.

    Body:
      name                  (str, required)
      description           (str, optional)
      pinecone_namespace    (str, optional — auto-generated if omitted)
      restrict_conversations (bool, optional — default False)
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not _check_admin(user):
        return jsonify({'error': 'Admin privileges required to manage departments'}), 403

    data = request.get_json() or {}

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Department name is required'}), 400

    # Check for duplicate name within the company
    existing = Department.query.filter_by(
        company_id=company.id, name=name
    ).first()
    if existing:
        return jsonify({
            'error': f"A department named '{name}' already exists in this company"
        }), 409

    # Enforce plan quota
    try:
        from services.enterprise_limits import EnterpriseLimits, PlanQuotaExceeded
        EnterpriseLimits.check_department_quota(company)
    except PlanQuotaExceeded as exc:
        return jsonify({
            'error': str(exc),
            'code': 'QUOTA_EXCEEDED',
            'resource': exc.resource,
            'limit': exc.limit,
            'plan': exc.plan,
        }), 402

    try:
        dept = Department(
            company_id=company.id,
            name=name,
            description=data.get('description'),
            pinecone_namespace=data.get('pinecone_namespace') or None,
            restrict_conversations=bool(data.get('restrict_conversations', False)),
            data_access_level=data.get('data_access_level') or 'internal',
            allowed_integrations=data.get('allowed_integrations') if isinstance(data.get('allowed_integrations'), list) else [],
            is_active=True,
        )
        db.session.add(dept)
        db.session.commit()

        return jsonify({
            'message': 'Department created successfully',
            'department': dept.to_dict(),
        }), 201

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@departments_bp.route('/<int:dept_id>', methods=['GET'])
@jwt_required()
def get_department(dept_id):
    """
    GET /api/departments/<id>
    Returns a single department with its full employee list.
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    dept = _get_department(dept_id, company.id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404

    dept_data = dept.to_dict()
    employees = Employee.query.filter_by(
        department_id=dept.id, is_active=True
    ).all()
    dept_data['employees'] = [e.to_dict() for e in employees]

    return jsonify({'department': dept_data})


@departments_bp.route('/<int:dept_id>', methods=['PUT'])
@jwt_required()
def update_department(dept_id):
    """
    PUT /api/departments/<id>
    Update department metadata and data access policies.

    Body (all optional):
      name, description, pinecone_namespace, restrict_conversations, data_access_level, allowed_integrations, is_active
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not _check_admin(user):
        return jsonify({'error': 'Admin privileges required'}), 403

    dept = _get_department(dept_id, company.id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404

    data = request.get_json() or {}

    try:
        if 'name' in data:
            name = (data['name'] or '').strip()
            if not name:
                return jsonify({'error': 'Department name cannot be empty'}), 400
            # Check duplicate (excluding self)
            dup = Department.query.filter(
                Department.company_id == company.id,
                Department.name == name,
                Department.id != dept_id,
            ).first()
            if dup:
                return jsonify({'error': f"A department named '{name}' already exists"}), 409
            dept.name = name

        if 'description' in data:
            dept.description = data['description']
        if 'pinecone_namespace' in data:
            dept.pinecone_namespace = data['pinecone_namespace'] or None
        if 'restrict_conversations' in data:
            dept.restrict_conversations = bool(data['restrict_conversations'])
        if 'data_access_level' in data:
            dept.data_access_level = data['data_access_level'] or 'internal'
        if 'allowed_integrations' in data:
            dept.allowed_integrations = data['allowed_integrations'] if isinstance(data['allowed_integrations'], list) else []
        if 'is_active' in data:
            dept.is_active = bool(data['is_active'])

        db.session.commit()
        return jsonify({
            'message': 'Department updated successfully',
            'department': dept.to_dict(),
        })

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@departments_bp.route('/<int:dept_id>', methods=['DELETE'])
@jwt_required()
def delete_department(dept_id):
    """
    DELETE /api/departments/<id>
    Soft-deletes a department (sets is_active=False) and unassigns its employees.
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not _check_admin(user):
        return jsonify({'error': 'Admin privileges required'}), 403

    dept = _get_department(dept_id, company.id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404

    try:
        # Unassign all employees from this department (don't delete employees)
        Employee.query.filter_by(
            department_id=dept.id
        ).update({'department_id': None})

        # Soft delete
        dept.is_active = False
        db.session.commit()

        return jsonify({'message': 'Department deactivated and employees unassigned'})

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@departments_bp.route('/usage', methods=['GET'])
@jwt_required()
def get_quota_usage():
    """
    GET /api/departments/usage
    Returns the current department and employee quota usage for the company.
    Useful for dashboard plan-limit widgets.
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    from services.enterprise_limits import EnterpriseLimits
    usage = EnterpriseLimits.get_usage(company)
    return jsonify({'quota': usage})


@departments_bp.route('/<int:dept_id>/employees', methods=['POST'])
@jwt_required()
def assign_employee_to_department(dept_id):
    """
    POST /api/departments/<id>/employees
    Assign an existing employee to this department.

    Body:
      employee_id (int, required)
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not _check_admin(user):
        return jsonify({'error': 'Admin privileges required'}), 403

    dept = _get_department(dept_id, company.id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404

    data = request.get_json() or {}
    employee_id = data.get('employee_id')
    if not employee_id:
        return jsonify({'error': 'employee_id is required'}), 400

    employee = Employee.query.filter_by(
        id=employee_id, company_id=company.id
    ).first()
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    try:
        employee.department_id = dept.id
        # Sync legacy text field for display compatibility
        employee.department = dept.name
        db.session.commit()

        return jsonify({
            'message': f"Employee '{employee.name}' assigned to department '{dept.name}'",
            'employee': employee.to_dict(),
        })

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


@departments_bp.route('/<int:dept_id>/employees/<int:emp_id>', methods=['DELETE'])
@jwt_required()
def unassign_employee_from_department(dept_id, emp_id):
    """
    DELETE /api/departments/<dept_id>/employees/<emp_id>
    Remove an employee from this department (unassigns without deleting the employee).
    """
    user, company = _get_user_and_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if not _check_admin(user):
        return jsonify({'error': 'Admin privileges required'}), 403

    dept = _get_department(dept_id, company.id)
    if not dept:
        return jsonify({'error': 'Department not found'}), 404

    employee = Employee.query.filter_by(
        id=emp_id, company_id=company.id, department_id=dept_id
    ).first()
    if not employee:
        return jsonify({'error': 'Employee not found in this department'}), 404

    try:
        employee.department_id = None
        db.session.commit()
        return jsonify({
            'message': f"Employee '{employee.name}' unassigned from department '{dept.name}'"
        })

    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500
