"""
Enterprise Plan Limits Service
================================
Centralises all quota/limit checks for Aikrofy's Enterprise tier.

Checks performed before creating:
  * Departments  → Company.max_departments
  * Employees    → Company.max_employees

Usage (inside a route handler):
    from services.enterprise_limits import EnterpriseLimits, PlanQuotaExceeded

    try:
        EnterpriseLimits.check_department_quota(company)
    except PlanQuotaExceeded as exc:
        return jsonify({'error': str(exc), 'code': 'QUOTA_EXCEEDED'}), 402

Plan defaults (server_default in DB, can be overridden per company):
    ┌──────────────────┬────────────────────┬──────────────────┐
    │ Tier             │ max_departments    │ max_employees    │
    ├──────────────────┼────────────────────┼──────────────────┤
    │ pyme (free/basic)│ 1                  │ 10               │
    │ enterprise       │ 5                  │ 50               │
    │ enterprise_plus  │ 20                 │ 200              │
    │ custom           │ unlimited (set DB) │ unlimited        │
    └──────────────────┴────────────────────┴──────────────────┘

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.company import Company

logger = logging.getLogger(__name__)


# ── Plan tier upgrade matrix ───────────────────────────────────────────────
# Used by billing hooks (Paddle, PayPal) to update company quotas automatically
# when a subscription plan changes.
PLAN_QUOTAS: dict[str, dict[str, int]] = {
    "pyme": {
        "max_departments": 1,
        "max_employees": 10,
    },
    "enterprise": {
        "max_departments": 5,
        "max_employees": 50,
    },
    "enterprise_plus": {
        "max_departments": 20,
        "max_employees": 200,
    },
    # 'custom' tier: quotas are set individually per company in the DB.
}


class PlanQuotaExceeded(Exception):
    """Raised when a company tries to exceed its plan quota."""
    def __init__(self, resource: str, current: int, limit: int, plan: str):
        self.resource = resource
        self.current = current
        self.limit = limit
        self.plan = plan
        super().__init__(
            f"Quota exceeded for '{resource}': {current}/{limit} used "
            f"(plan: {plan}). Upgrade your plan to continue."
        )


class EnterpriseLimits:
    """
    Static helper class for quota enforcement.
    All methods raise ``PlanQuotaExceeded`` on violation; no side-effects.
    """

    # ── Department quota ──────────────────────────────────────────────────
    @staticmethod
    def check_department_quota(company: "Company") -> None:
        """
        Raises PlanQuotaExceeded if the company has reached its department limit.
        Must be called BEFORE inserting a new Department record.
        """
        from models.department import Department
        current = Department.query.filter_by(
            company_id=company.id, is_active=True
        ).count()
        limit = company.max_departments
        if current >= limit:
            logger.warning(
                "[LIMITS] Company %s hit department quota (%d/%d) on plan '%s'",
                company.id, current, limit, company.plan_type
            )
            raise PlanQuotaExceeded("departments", current, limit, company.plan_type or "pyme")

    # ── Employee quota ────────────────────────────────────────────────────
    @staticmethod
    def check_employee_quota(company: "Company") -> None:
        """
        Raises PlanQuotaExceeded if the company has reached its employee limit.
        Must be called BEFORE inserting a new Employee record.
        """
        from models.employee import Employee
        current = Employee.query.filter_by(
            company_id=company.id, is_active=True
        ).count()
        limit = company.max_employees
        if current >= limit:
            logger.warning(
                "[LIMITS] Company %s hit employee quota (%d/%d) on plan '%s'",
                company.id, current, limit, company.plan_type
            )
            raise PlanQuotaExceeded("employees", current, limit, company.plan_type or "pyme")

    # ── Quota info (for dashboard display) ────────────────────────────────
    @staticmethod
    def get_usage(company: "Company") -> dict:
        """
        Returns current usage vs. limits for the company.
        Suitable for including in the company.to_dict() or a dedicated /quota endpoint.
        """
        from models.department import Department
        from models.employee import Employee

        dept_count = Department.query.filter_by(company_id=company.id, is_active=True).count()
        emp_count = Employee.query.filter_by(company_id=company.id, is_active=True).count()

        return {
            "departments": {
                "used": dept_count,
                "limit": company.max_departments,
                "available": max(0, company.max_departments - dept_count),
                "at_limit": dept_count >= company.max_departments,
            },
            "employees": {
                "used": emp_count,
                "limit": company.max_employees,
                "available": max(0, company.max_employees - emp_count),
                "at_limit": emp_count >= company.max_employees,
            },
            "plan": company.plan_type or "pyme",
        }

    # ── Upgrade company quotas (called from billing webhook) ──────────────
    @staticmethod
    def apply_plan_quotas(company: "Company", plan_type: str) -> bool:
        """
        Update company quotas based on the plan tier.
        Returns True if quotas were changed, False if plan_type is unknown or 'custom'.

        Usage (from Paddle/PayPal webhook handler):
            EnterpriseLimits.apply_plan_quotas(company, 'enterprise')
            db.session.commit()
        """
        plan_type = (plan_type or "pyme").lower()
        quotas = PLAN_QUOTAS.get(plan_type)
        if not quotas:
            # 'custom' or unknown — do not overwrite manual quotas
            logger.info(
                "[LIMITS] plan_type='%s' for company %s has no standard quota table. Skipping.",
                plan_type, company.id
            )
            return False

        company.plan_type = plan_type
        company.max_departments = quotas["max_departments"]
        company.max_employees = quotas["max_employees"]
        logger.info(
            "[LIMITS] Applied plan '%s' quotas to company %s: %s",
            plan_type, company.id, quotas
        )
        return True
