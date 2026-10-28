"""
Employee Detection Service
============================
Detects when an incoming WhatsApp (or other channel) message is from a
registered employee/team member of the company, allowing the system to:
  - Route messages differently (internal agent, role-based context)
  - Skip CRM customer record creation
  - Skip credit deduction
  - Inject department-aware system prompt context
  - Apply RAG namespace isolation per department

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class EmployeeDetectionService:
    """
    Service responsible for detecting whether a message sender is a registered
    employee of a company.

    Detection strategy:
    1. Normalize the incoming phone number (strip country codes, spaces, etc.)
    2. Query the Employee model using both ``phone`` and ``whatsapp`` fields.
    3. Return the employee record if found, or None if the sender is external.
    """

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize a phone number to digits only (remove +, spaces, dashes)."""
        if not phone:
            return ''
        return ''.join(c for c in phone if c.isdigit())

    @classmethod
    def detect_employee(cls, company_id: int, from_phone: str, sender_email: str = None) -> Optional[Any]:
        """
        Detect if the sender is a registered employee of the company.

        Args:
            company_id: The company's database ID.
            from_phone: The sender's phone number (raw, may include 'whatsapp:' prefix, +CC, or LID).
            sender_email: Optional sender email.

        Returns:
            Employee instance if detected, None otherwise.
        """
        try:
            from models.employee import Employee
            from models.user import User
            from models.company import Company

            # 1. Check if sender is identified by email
            if sender_email:
                emp_by_email = Employee.query.filter_by(
                    company_id=company_id,
                    email=sender_email.strip().lower(),
                    is_active=True
                ).first()
                if emp_by_email:
                    logger.info(
                        "[EMPLOYEE_DETECT] ✅ Employee detected by email: %s (role=%s) for company=%s",
                        emp_by_email.name, emp_by_email.role.value, company_id
                    )
                    return emp_by_email

            # Clean prefix added by Twilio / WhatsApp
            clean_phone = (from_phone or '').replace('whatsapp:', '').strip()
            
            # Fetch all active employees for this company
            employees = Employee.query.filter_by(
                company_id=company_id,
                is_active=True
            ).all()

            # 2. Check if clean_phone is a WhatsApp LID (e.g. 76235954716750@lid or raw lid)
            is_lid = '@lid' in clean_phone or clean_phone.endswith('.0') or clean_phone.endswith('.91') or clean_phone.endswith('.92')
            if is_lid:
                lid_raw = clean_phone.split('@')[0].strip()
                for employee in employees:
                    # Check if LID is stored in whatsapp or specializations or conv_metadata
                    if employee.whatsapp and lid_raw in employee.whatsapp:
                        logger.info("[EMPLOYEE_DETECT] ✅ Employee detected by LID in whatsapp field: %s", employee.name)
                        return employee
                    if employee.specializations and isinstance(employee.specializations, list) and (lid_raw in employee.specializations or f"{lid_raw}@lid" in employee.specializations):
                        logger.info("[EMPLOYEE_DETECT] ✅ Employee detected by LID in specializations: %s", employee.name)
                        return employee
                
                # Check if this company's owner/admin is mapped in conversations with this LID
                from models.conversation import Conversation, ConversationType
                past_owner_conv = Conversation.query.filter(
                    Conversation.company_id == company_id,
                    Conversation.contact_phone == clean_phone,
                    Conversation.type.in_([ConversationType.EMPLOYEE, ConversationType.ADMIN])
                ).first()
                if past_owner_conv and past_owner_conv.conv_metadata and past_owner_conv.conv_metadata.get('employee_id'):
                    emp_cached = Employee.query.get(past_owner_conv.conv_metadata.get('employee_id'))
                    if emp_cached and emp_cached.is_active:
                        logger.info("[EMPLOYEE_DETECT] ✅ Employee detected by past conversation metadata: %s", emp_cached.name)
                        return emp_cached

                # Check whatsapp_lid_mapping table
                try:
                    from extensions import db
                    res = db.session.execute(
                        db.text("SELECT phone_number FROM whatsapp_lid_mapping WHERE company_id = :cid AND (lid_jid = :lid OR lid_jid LIKE :lid_like) LIMIT 1"),
                        {"cid": company_id, "lid": clean_phone, "lid_like": f"%{lid_raw}%"}
                    ).fetchone()
                    if res and res[0]:
                        mapped_phone = str(res[0])
                        mapped_digits = cls._normalize_phone(mapped_phone)
                        for employee in employees:
                            for field_value in [employee.phone, employee.whatsapp]:
                                if field_value:
                                    field_digits = cls._normalize_phone(field_value)
                                    if field_digits and (field_digits == mapped_digits or field_digits.endswith(mapped_digits[-9:]) or mapped_digits.endswith(field_digits[-9:])):
                                        logger.info("[EMPLOYEE_DETECT] ✅ Employee detected via whatsapp_lid_mapping (%s -> %s): %s", clean_phone, mapped_phone, employee.name)
                                        return employee
                except Exception as map_err:
                    logger.debug("[EMPLOYEE_DETECT] Error querying whatsapp_lid_mapping: %s", map_err)

            digits_only = cls._normalize_phone(clean_phone)
            if not digits_only:
                return None

            for employee in employees:
                # Check against both phone and whatsapp fields
                for field_value in [employee.phone, employee.whatsapp]:
                    if field_value:
                        field_digits = cls._normalize_phone(field_value)
                        # Match: either exact or suffix (last 9+ digits)
                        if field_digits and (
                            field_digits == digits_only or
                            (len(digits_only) >= 9 and field_digits.endswith(digits_only[-9:])) or
                            (len(field_digits) >= 9 and digits_only.endswith(field_digits[-9:]))
                        ):
                            logger.info(
                                "[EMPLOYEE_DETECT] ✅ Employee detected: %s "
                                "(role=%s, dept=%s) for company=%s",
                                employee.name,
                                employee.role.value,
                                employee.department or 'N/A',
                                company_id,
                            )
                            # Auto-cache LID mapping if this lookup was initiated via LID
                            if is_lid:
                                try:
                                    from services.cache_service import CacheService
                                    CacheService.set(f"wa:lid_map:{company_id}:{clean_phone.split('@')[0]}", field_digits, ttl=86400 * 30)
                                except Exception:
                                    pass
                            return employee

            # 3. Check Company Owner / Admins from Users table and Company Phone
            company = Company.query.get(company_id)
            if company:
                # 3a. Check company's registered phone
                company_phone_digits = cls._normalize_phone(company.phone or '')
                is_company_phone_match = company_phone_digits and (
                    company_phone_digits == digits_only or
                    (len(digits_only) >= 9 and company_phone_digits.endswith(digits_only[-9:])) or
                    (len(company_phone_digits) >= 9 and digits_only.endswith(company_phone_digits[-9:]))
                )

                # 3b. Find company root owner or first active admin user
                owner_user = User.query.filter_by(company_id=company_id, is_active=True).filter(
                    (User.is_company_owner == True) | (User.role.in_(['admin', 'super_admin']))
                ).order_by(User.is_company_owner.desc()).first()

                # If company phone matches, or if only 1 active owner and incoming is from WhatsApp LID
                if is_company_phone_match or is_lid:
                    # Find existing Employee with role owner/admin or create a virtual/linked Employee wrapper
                    owner_employee = Employee.query.filter_by(company_id=company_id, is_active=True).filter(
                        Employee.role.in_(['owner', 'admin'])
                    ).first()

                    if is_company_phone_match:
                        target_name = (owner_employee.name if owner_employee else (owner_user.name if owner_user else company.name))
                        logger.info(f"[EMPLOYEE_DETECT] ✅ Owner recognized via Company.phone ({company.phone}): {target_name}")
                        if owner_employee:
                            return owner_employee
                        if owner_user:
                            # If no employee record exists yet, find or create one for the owner
                            from models.employee import EmployeeRole
                            new_owner_emp = Employee(
                                company_id=company_id,
                                user_id=owner_user.id,
                                name=owner_user.name,
                                email=owner_user.email,
                                phone=company.phone,
                                whatsapp=company.phone,
                                role=EmployeeRole.OWNER,
                                has_web_access=True,
                                is_active=True
                            )
                            try:
                                from extensions import db
                                db.session.add(new_owner_emp)
                                db.session.commit()
                                return new_owner_emp
                            except Exception:
                                db.session.rollback()

            logger.debug(
                "[EMPLOYEE_DETECT] No employee match for phone=%s in company=%s",
                clean_phone, company_id,
            )
            return None

        except Exception as exc:
            logger.error("[EMPLOYEE_DETECT] Error during detection: %s", exc)
            return None

    @classmethod
    def build_employee_context(cls, employee: Any) -> Dict[str, Any]:
        """
        Build a context dictionary with employee info to inject into the agent state.

        Args:
            employee: Employee model instance.

        Returns:
            Dictionary with employee context data including department info.
        """
        dept_id = getattr(employee, 'department_id', None)
        dept_name = None

        if dept_id:
            try:
                from models.department import Department
                dept = Department.query.get(dept_id)
                if dept:
                    dept_name = dept.name
            except Exception:
                pass

        dept_name = dept_name or employee.department or 'General'

        return {
            'is_employee': True,
            'employee_id': employee.id,
            'employee_name': employee.name,
            'employee_role': employee.role.value,
            'employee_department': dept_name,
            'employee_department_id': dept_id,
            'employee_specializations': employee.specializations or [],
            'has_web_access': getattr(employee, 'has_web_access', False),
            'is_manager': employee.role.value in ('owner', 'manager', 'admin'),
        }

    @classmethod
    def get_rag_namespaces(cls, employee: Any, company) -> List[str]:
        """
        Returns the ordered list of Pinecone namespaces to query for an employee.

        Priority:
          1. Department-specific namespace (if employee has a department)
          2. Global company namespace (always included as fallback)

        This ensures employees get both their department knowledge AND the
        company-wide shared knowledge base.

        Args:
            employee: Employee model instance.
            company: Company model instance.

        Returns:
            List of namespace strings ordered by priority.
        """
        namespaces = []

        dept_id = getattr(employee, 'department_id', None)
        if dept_id:
            try:
                from models.department import Department
                dept = Department.query.get(dept_id)
                if dept and dept.is_active:
                    dept_namespace = dept.get_pinecone_namespace()
                    if dept_namespace:
                        namespaces.append(dept_namespace)
            except Exception as exc:
                logger.warning("[EMPLOYEE_DETECT] Could not resolve dept namespace: %s", exc)

        # Global company namespace (always added as fallback)
        if company and company.pinecone_namespace:
            global_ns = company.pinecone_namespace
        elif company:
            global_ns = f"company_{company.id}"
        else:
            global_ns = "global"

        if global_ns not in namespaces:
            namespaces.append(global_ns)

        return namespaces

    @classmethod
    def get_employee_system_prompt_addon(
        cls,
        employee: Any,
        company_name: str = '',
        department_name: str = '',
    ) -> str:
        """
        Generate additional system prompt context that identifies the sender as
        an internal team member with their specific role, permissions, and
        department context.

        Args:
            employee: Employee model instance.
            company_name: Optional company name for personalization.
            department_name: Optional department name (resolved from FK if empty).

        Returns:
            String to prepend to the agent system prompt.
        """
        # Resolve department name
        if not department_name:
            dept_id = getattr(employee, 'department_id', None)
            if dept_id:
                try:
                    from models.department import Department
                    dept = Department.query.get(dept_id)
                    if dept:
                        department_name = dept.name
                except Exception:
                    pass
            department_name = department_name or employee.department or ''

        role_descriptions = {
            'owner': 'el propietario/CEO de la empresa con acceso completo a toda la información',
            'manager': 'un gerente de la empresa con acceso a datos operacionales y de equipo',
            'admin': 'un administrador del sistema con capacidades de configuración avanzadas',
            'sales': 'un miembro del equipo de ventas con acceso a CRM, leads y pipelines de venta',
            'support': 'un agente de soporte interno con acceso a tickets, clientes y historial de conversaciones',
            'general': 'un empleado de la empresa con acceso a información operacional básica',
        }

        role_desc = role_descriptions.get(employee.role.value, 'un miembro del equipo')
        dept_context = f" del departamento de **{department_name}**" if department_name else ""

        addon = f"""
---
⚠️ CONTEXTO INTERNO Y PERSONALIZACIÓN DE IDENTIDAD:
Estás hablando directamente por WhatsApp con **{employee.name}**, quien es **{role_desc}{dept_context}** de {company_name or 'la empresa'}.
NO es un cliente externo ni un lead. Es el DUEÑO / MIEMBRO INTERNO del equipo con acceso total.

INSTRUCCIONES OBLIGATORIAS DE RESPUESTA:
- Salúdalo SIEMPRE llamándolo por su nombre (**{employee.name}**) y reconociendo su rol ({employee.role.value.upper()}). Ejemplo: "¡Hola {employee.name}! Con gusto te asisto..." o "Hola {employee.name}, aquí Krof a tu disposición como {employee.role.value}...".
- NUNCA lo trates como a un cliente nuevo ni le preguntes su nombre o datos.
- Responde en modo INTERNO y ejecutivo: tienes total autorización para reportar métricas, gestionar agentes, coordinar campañas, crear landings y supervisar la plataforma.
- Usa un tono proactivo, ágil y colaborativo.
{f"- Como {employee.role.value}, tiene control absoluto y acceso total a todas las funciones y herramientas del sistema." if employee.role.value in ('owner', 'manager', 'admin') else ""}
{f"- Especializado en: {', '.join(employee.specializations)}" if employee.specializations else ""}
---
"""
        return addon
