"""
Bulk Ingestion Service - Aikrofy
Supports CSV and XLSX bulk uploads for leads, employees, and transactions.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import csv
import io
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Entity Definitions ──────────────────────────────────────────────────────
# Each entity defines its columns, required fields, and display name.

ENTITY_DEFINITIONS = {
    'leads': {
        'label': 'Leads / Contactos',
        'description': 'Importación masiva de leads y contactos al CRM',
        'columns': [
            {'key': 'first_name',    'label': 'Nombre',           'required': True,  'type': 'str'},
            {'key': 'last_name',     'label': 'Apellido',         'required': False, 'type': 'str'},
            {'key': 'email',         'label': 'Email',            'required': False, 'type': 'str'},
            {'key': 'phone',         'label': 'Teléfono',         'required': False, 'type': 'str'},
            {'key': 'country',       'label': 'País',             'required': False, 'type': 'str'},
            {'key': 'city',          'label': 'Ciudad',           'required': False, 'type': 'str'},
            {'key': 'ident_number',  'label': 'Identificación',   'required': False, 'type': 'str'},
            {'key': 'work_company',  'label': 'Empresa',          'required': False, 'type': 'str'},
            {'key': 'buying_role',   'label': 'Rol de Compra',    'required': False, 'type': 'str'},
        ]
    },
    'empleados': {
        'label': 'Empleados / Equipo',
        'description': 'Importación masiva de miembros del equipo',
        'columns': [
            {'key': 'name',       'label': 'Nombre Completo', 'required': True,  'type': 'str'},
            {'key': 'email',      'label': 'Email',           'required': False, 'type': 'str'},
            {'key': 'phone',      'label': 'Teléfono',        'required': False, 'type': 'str'},
            {'key': 'whatsapp',   'label': 'WhatsApp',        'required': False, 'type': 'str'},
            {'key': 'role',       'label': 'Rol',             'required': False, 'type': 'str'},
            {'key': 'department', 'label': 'Departamento',    'required': False, 'type': 'str'},
        ]
    },
    'ventas': {
        'label': 'Ventas / Transacciones',
        'description': 'Importación masiva de transacciones y ventas',
        'columns': [
            {'key': 'amount',         'label': 'Monto',           'required': True,  'type': 'float'},
            {'key': 'currency',       'label': 'Moneda',          'required': False, 'type': 'str'},
            {'key': 'description',    'label': 'Descripción',     'required': False, 'type': 'str'},
            {'key': 'service_type',   'label': 'Tipo de Servicio','required': False, 'type': 'str'},
            {'key': 'provider',       'label': 'Proveedor',       'required': False, 'type': 'str'},
            {'key': 'status',         'label': 'Estado',          'required': False, 'type': 'str'},
            {'key': 'customer_email', 'label': 'Email del Cliente','required': False, 'type': 'str'},
        ]
    },
}

# ─── Example rows for template generation ────────────────────────────────────

ENTITY_EXAMPLES = {
    'leads': [
        {'first_name': 'Juan', 'last_name': 'Pérez', 'email': 'juan@empresa.com',
         'phone': '+593991234567', 'country': 'Ecuador', 'city': 'Guayaquil',
         'ident_number': '0912345678', 'work_company': 'Tech Corp', 'buying_role': 'Decision Maker'},
        {'first_name': 'María', 'last_name': 'García', 'email': 'maria@otro.com',
         'phone': '+573001234567', 'country': 'Colombia', 'city': 'Bogotá',
         'ident_number': '', 'work_company': '', 'buying_role': 'End User'},
    ],
    'empleados': [
        {'name': 'Carlos López', 'email': 'carlos@empresa.com', 'phone': '+593991111111',
         'whatsapp': '+593991111111', 'role': 'sales', 'department': 'Ventas'},
        {'name': 'Ana Torres', 'email': 'ana@empresa.com', 'phone': '+593992222222',
         'whatsapp': '+593992222222', 'role': 'support', 'department': 'Soporte'},
    ],
    'ventas': [
        {'amount': '1500.00', 'currency': 'USD', 'description': 'Consultoría mensual',
         'service_type': 'Consulting', 'provider': 'manual', 'status': 'completed',
         'customer_email': 'cliente@ejemplo.com'},
        {'amount': '350.50', 'currency': 'USD', 'description': 'Venta de producto',
         'service_type': 'Product', 'provider': 'manual', 'status': 'pending',
         'customer_email': ''},
    ],
}


# ─── Column Normalizer ────────────────────────────────────────────────────────

def _normalize_column(col_name: str) -> str:
    """Normalize column names for fuzzy matching: lowercase, strip, replace spaces/hyphens."""
    return re.sub(r'[\s\-_]+', '_', col_name.strip().lower())


COL_ALIASES = {
    # leads
    'nombre': 'first_name', 'first_name': 'first_name', 'firstname': 'first_name', 'name': 'first_name',
    'apellido': 'last_name', 'last_name': 'last_name', 'lastname': 'last_name', 'surname': 'last_name',
    'correo': 'email', 'email': 'email', 'mail': 'email', 'correo_electronico': 'email',
    'telefono': 'phone', 'phone': 'phone', 'cel': 'phone', 'celular': 'phone', 'movil': 'phone',
    'pais': 'country', 'country': 'country', 'país': 'country',
    'ciudad': 'city', 'city': 'city',
    'identificacion': 'ident_number', 'ident_number': 'ident_number', 'cedula': 'ident_number', 'dni': 'ident_number',
    'empresa': 'work_company', 'work_company': 'work_company', 'company': 'work_company',
    'rol_de_compra': 'buying_role', 'buying_role': 'buying_role', 'rol': 'role', 'role': 'role',
    # employees
    'nombre_completo': 'name', 'full_name': 'name',
    'whatsapp': 'whatsapp', 'departamento': 'department', 'department': 'department',
    # ventas
    'monto': 'amount', 'amount': 'amount', 'valor': 'amount',
    'moneda': 'currency', 'currency': 'currency',
    'descripcion': 'description', 'description': 'description', 'descripción': 'description',
    'tipo_de_servicio': 'service_type', 'service_type': 'service_type', 'servicio': 'service_type',
    'proveedor': 'provider', 'provider': 'provider',
    'estado': 'status', 'status': 'status',
    'email_del_cliente': 'customer_email', 'customer_email': 'customer_email', 'email_cliente': 'customer_email',
}


def _map_columns(file_headers: list) -> dict:
    """Map file column headers to canonical field keys."""
    mapping = {}
    for h in file_headers:
        normalized = _normalize_column(h)
        canonical = COL_ALIASES.get(normalized)
        if canonical:
            mapping[h] = canonical
    return mapping


# ─── Template generation ──────────────────────────────────────────────────────

def generate_csv_template(entity: str) -> bytes:
    """Generate a CSV template with headers and example rows for the given entity."""
    definition = ENTITY_DEFINITIONS.get(entity)
    if not definition:
        raise ValueError(f"Unknown entity: {entity}")
    
    columns = [col['key'] for col in definition['columns']]
    examples = ENTITY_EXAMPLES.get(entity, [])
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for row in examples:
        writer.writerow(row)
    
    return output.getvalue().encode('utf-8-sig')  # BOM for Excel compat


def generate_xlsx_template(entity: str) -> bytes:
    """Generate an XLSX template with headers and example rows."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except ImportError:
        raise ImportError("openpyxl is not installed. Run: pip install openpyxl")
    
    definition = ENTITY_DEFINITIONS.get(entity)
    if not definition:
        raise ValueError(f"Unknown entity: {entity}")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = definition['label']
    
    # Header row styling
    header_fill = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    
    columns = [col for col in definition['columns']]
    for col_idx, col_def in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_def['label'])
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 20
    
    # Example rows
    examples = ENTITY_EXAMPLES.get(entity, [])
    for row_idx, example in enumerate(examples, 2):
        for col_idx, col_def in enumerate(columns, 1):
            ws.cell(row=row_idx, column=col_idx, value=str(example.get(col_def['key'], '')))
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_row(row_data: dict, entity: str, row_number: int) -> list:
    """Validate a single row. Returns list of error strings."""
    errors = []
    definition = ENTITY_DEFINITIONS.get(entity, {})
    columns = definition.get('columns', [])
    
    for col_def in columns:
        key = col_def['key']
        value = row_data.get(key, '')
        
        # Required field check
        if col_def.get('required') and not str(value).strip():
            errors.append(f"Fila {row_number}: Campo requerido '{col_def['label']}' está vacío")
            continue
        
        # Type validation for non-empty values
        if str(value).strip() and col_def['type'] == 'float':
            try:
                float(str(value).replace(',', '.'))
            except (ValueError, TypeError):
                errors.append(f"Fila {row_number}: '{col_def['label']}' debe ser un número (obtenido: '{value}')")
    
    return errors


# ─── Row Processors ───────────────────────────────────────────────────────────

def _process_lead_row(row_data: dict, company_id: int) -> dict:
    """Process and insert a single leads/contacts row."""
    from extensions import db
    from models.customer import Customer
    from models.funnel_stage import FunnelStage
    
    first_name = str(row_data.get('first_name', '')).strip()
    email = str(row_data.get('email', '')).strip() or None
    phone = str(row_data.get('phone', '')).strip() or None
    
    # Deduplication: skip if email or phone already exists for this company
    if email:
        existing = Customer.query.filter_by(company_id=company_id, email=email).first()
        if existing:
            return {'skipped': True, 'reason': f'Email {email} ya existe'}
    if phone and not email:
        existing = Customer.query.filter_by(company_id=company_id, phone=phone).first()
        if existing:
            return {'skipped': True, 'reason': f'Teléfono {phone} ya existe'}
    
    # Assign first funnel stage
    first_stage = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).first()
    funnel_stage_id = first_stage.id if first_stage else None
    
    customer = Customer(
        company_id=company_id,
        first_name=first_name,
        last_name=str(row_data.get('last_name', '')).strip() or None,
        email=email,
        phone=phone,
        country=str(row_data.get('country', '')).strip() or None,
        city=str(row_data.get('city', '')).strip() or None,
        ident_number=str(row_data.get('ident_number', '')).strip() or None,
        work_company=str(row_data.get('work_company', '')).strip() or None,
        buying_role=str(row_data.get('buying_role', 'End User')).strip() or 'End User',
        funnel_stage_id=funnel_stage_id,
    )
    db.session.add(customer)
    return {'skipped': False}


def _process_employee_row(row_data: dict, company_id: int) -> dict:
    """Process and insert a single employee row."""
    from extensions import db
    from models.employee import Employee, EmployeeRole
    
    name = str(row_data.get('name', '')).strip()
    email = str(row_data.get('email', '')).strip() or None
    
    # Deduplication by email
    if email:
        existing = Employee.query.filter_by(company_id=company_id, email=email).first()
        if existing:
            return {'skipped': True, 'reason': f'Email {email} ya existe'}
    
    # Role validation
    role_str = str(row_data.get('role', 'general')).strip().lower()
    try:
        role = EmployeeRole(role_str)
    except ValueError:
        role = EmployeeRole.GENERAL
    
    employee = Employee(
        company_id=company_id,
        name=name,
        email=email,
        phone=str(row_data.get('phone', '')).strip() or None,
        whatsapp=str(row_data.get('whatsapp', '')).strip() or None,
        role=role,
        department=str(row_data.get('department', '')).strip() or None,
    )
    db.session.add(employee)
    return {'skipped': False}


def _process_venta_row(row_data: dict, company_id: int) -> dict:
    """Process and insert a single transaction/sale row."""
    from extensions import db
    from models.transaction import Transaction, TransactionStatus, TransactionProvider
    from models.customer import Customer
    
    amount_str = str(row_data.get('amount', '')).replace(',', '.').strip()
    try:
        amount = float(amount_str)
    except (ValueError, TypeError):
        return {'skipped': True, 'reason': f'Monto inválido: {amount_str}'}
    
    # Optional customer lookup by email
    customer_id = None
    customer_email = str(row_data.get('customer_email', '')).strip()
    if customer_email:
        cust = Customer.query.filter_by(company_id=company_id, email=customer_email).first()
        if cust:
            customer_id = cust.id
    
    # Status validation
    status_str = str(row_data.get('status', 'pending')).strip().lower()
    valid_statuses = [s.value for s in TransactionStatus]
    status = status_str if status_str in valid_statuses else 'pending'
    
    # Provider validation
    provider_str = str(row_data.get('provider', 'manual')).strip().lower()
    valid_providers = [p.value for p in TransactionProvider]
    provider = provider_str if provider_str in valid_providers else 'manual'
    
    transaction = Transaction(
        company_id=company_id,
        customer_id=customer_id,
        amount=amount,
        currency=str(row_data.get('currency', 'USD')).strip().upper() or 'USD',
        description=str(row_data.get('description', '')).strip() or None,
        service_type=str(row_data.get('service_type', '')).strip() or None,
        provider=provider,
        status=status,
        transaction_type='payment',
    )
    db.session.add(transaction)
    return {'skipped': False}


PROCESSORS = {
    'leads': _process_lead_row,
    'empleados': _process_employee_row,
    'ventas': _process_venta_row,
}


# ─── Main Upload Processor ────────────────────────────────────────────────────

def process_upload(file_content: bytes, filename: str, entity: str, company_id: int) -> dict:
    """
    Process a CSV or XLSX file for bulk ingestion.
    
    Returns:
        dict with keys: total, imported, skipped, errors, error_details
    """
    from extensions import db
    
    if entity not in ENTITY_DEFINITIONS:
        raise ValueError(f"Entidad desconocida: {entity}")
    
    processor = PROCESSORS.get(entity)
    if not processor:
        raise ValueError(f"Procesador no disponible para: {entity}")
    
    # ── Parse file ──────────────────────────────────────────────────────────
    rows = []
    file_headers = []
    fname_lower = filename.lower()
    
    if fname_lower.endswith('.xlsx') or fname_lower.endswith('.xls'):
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl is required for XLSX support. Run: pip install openpyxl")
        
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            return {'total': 0, 'imported': 0, 'skipped': 0, 'errors': 0, 'error_details': []}
        file_headers = [str(h).strip() if h is not None else '' for h in all_rows[0]]
        for row in all_rows[1:]:
            row_dict = {file_headers[i]: (str(v).strip() if v is not None else '') 
                       for i, v in enumerate(row) if i < len(file_headers)}
            rows.append(row_dict)
    else:
        # CSV (default)
        text = file_content.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        file_headers = reader.fieldnames or []
        rows = list(reader)
    
    if not file_headers or not rows:
        return {'total': 0, 'imported': 0, 'skipped': 0, 'errors': 0, 'error_details': []}
    
    # ── Column mapping ──────────────────────────────────────────────────────
    col_map = _map_columns(list(file_headers))
    
    # ── Process rows ────────────────────────────────────────────────────────
    total = len(rows)
    imported = 0
    skipped = 0
    errors = 0
    error_details = []
    
    for row_number, raw_row in enumerate(rows, 2):  # start at 2 (row 1 is header)
        # Skip completely empty rows
        if not any(str(v).strip() for v in raw_row.values()):
            continue
        
        # Map columns to canonical keys
        mapped_row = {}
        for file_col, value in raw_row.items():
            canonical = col_map.get(file_col, file_col)  # fallback to original key
            mapped_row[canonical] = value
        
        # Validation
        row_errors = _validate_row(mapped_row, entity, row_number)
        if row_errors:
            errors += 1
            error_details.extend(row_errors)
            continue
        
        # Processing
        try:
            result = processor(mapped_row, company_id)
            if result.get('skipped'):
                skipped += 1
                error_details.append(f"Fila {row_number}: Omitida — {result.get('reason', 'Duplicado')}")
            else:
                imported += 1
        except Exception as e:
            errors += 1
            error_details.append(f"Fila {row_number}: Error al procesar — {str(e)}")
            logger.error(f"[Ingestion] Error processing row {row_number} for {entity}: {e}")
    
    # Commit all at once
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"[Ingestion] Commit error for {entity}: {e}")
        raise
    
    logger.info(f"[Ingestion] {entity} upload complete: total={total}, imported={imported}, skipped={skipped}, errors={errors}")
    
    return {
        'total': total,
        'imported': imported,
        'skipped': skipped,
        'errors': errors,
        'error_details': error_details[:50],  # Limit error list to first 50
    }
