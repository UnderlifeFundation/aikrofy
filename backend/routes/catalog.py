"""
Native Catalog & AI-POS Routes (/api/catalog)
Provides full CRUD for products, automatic EAN-13 / Code-128 & QR generation,
barcode lookup, in-store POS checkout with instant stock deduction, and
thermal receipt / WhatsApp digital ticket dispatch.
"""
import random
from datetime import datetime
from sqlalchemy import or_
from routing import Blueprint, request, jsonify, jwt_required, get_jwt_identity
from extensions import db
from models.user import User
from models.catalog import CatalogProduct, CatalogOrder

catalog_bp = Blueprint('catalog', __name__)


def _get_user_company():
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id)) if user_id else None
    if not user or not user.company:
        return None, None
    return user, user.company


def _compute_ean13_check_digit(digits_12: str) -> str:
    """Compute standard GS1 / EAN-13 check digit for a 12-digit numeric prefix."""
    total = 0
    for idx, ch in enumerate(digits_12[:12]):
        d = int(ch)
        total += d if idx % 2 == 0 else d * 3
    check = (10 - (total % 10)) % 10
    return str(check)


GS1_COUNTRY_PREFIXES = {
    'ecuador': '786', 'ec': '786',
    'peru': '775', 'perú': '775', 'pe': '775',
    'colombia': '770', 'co': '770',
    'chile': '780', 'cl': '780',
    'argentina': '779', 'ar': '779',
    'bolivia': '777', 'bo': '777',
    'mexico': '750', 'méxico': '750', 'mx': '750',
    'brasil': '789', 'brazil': '789', 'br': '789',
    'espana': '840', 'españa': '840', 'spain': '840', 'es': '840',
    'republica checa': '859', 'república checa': '859', 'czech republic': '859', 'cz': '859',
    'estados unidos': '019', 'united states': '019', 'usa': '019', 'us': '019',
}


def _generate_ean13_barcode(company_id: int, country: str = None) -> str:
    """
    Generate a valid 13-digit EAN-13 barcode using the company's country GS1 prefix
    or the universal GS1 in-store / variable prefix ('200') for global compatibility.
    """
    c_key = (country or '').strip().lower()
    gs1_prefix = GS1_COUNTRY_PREFIXES.get(c_key, '200')
    comp_part = f"{company_id % 1000:03d}"
    rand_part = f"{random.randint(0, 999999):06d}"
    base_12 = f"{gs1_prefix}{comp_part}{rand_part}"
    return base_12 + _compute_ean13_check_digit(base_12)


# Alias for LangGraph tool compatibility
def _generate_ean13(company_id: int, sku: str = "", country: str = None) -> str:
    return _generate_ean13_barcode(company_id, country=country)


def _generate_sku(company_id: int, category: str = "PRD") -> str:
    prefix = "".join(c for c in (category or "PRD").upper() if c.isalpha())[:3] or "PRD"
    count = CatalogProduct.query.filter_by(company_id=company_id).count() + 1
    return f"{prefix}-{company_id:02d}-{count:04d}"


@catalog_bp.route('/products', methods=['GET'])
@jwt_required()
def list_products():
    """List all native catalog products for the authenticated company."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        CatalogProduct.__table__.create(db.engine, checkfirst=True)
    except Exception:
        pass

    search = (request.args.get('q') or '').strip()
    category = (request.args.get('category') or '').strip()

    q = CatalogProduct.query.filter_by(company_id=company.id, is_active=True)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                CatalogProduct.name.ilike(term),
                CatalogProduct.sku.ilike(term),
                CatalogProduct.barcode.ilike(term),
                CatalogProduct.category.ilike(term),
            )
        )
    if category and category.lower() != 'all':
        q = q.filter(CatalogProduct.category.ilike(category))

    products = q.order_by(CatalogProduct.id.desc()).all()
    items_list = [p.to_dict() for p in products]
    return jsonify({'data': items_list, 'products': items_list})


@catalog_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    """Create a new product with automatic SKU and EAN-13 barcode if omitted."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        CatalogProduct.__table__.create(db.engine, checkfirst=True)
    except Exception:
        pass

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'El nombre del producto es obligatorio'}), 400

    category = (data.get('category') or 'General').strip() or 'General'
    sku = (data.get('sku') or '').strip() or _generate_sku(company.id, category)
    barcode = (data.get('barcode') or '').strip() or _generate_ean13_barcode(company.id, country=company.country)

    try:
        price = max(0.0, float(data.get('price', 0.0)))
    except (ValueError, TypeError):
        price = 0.0

    try:
        stock = max(0, int(data.get('stock', 0)))
    except (ValueError, TypeError):
        stock = 0

    product = CatalogProduct(
        company_id=company.id,
        sku=sku,
        barcode=barcode,
        name=name,
        description=(data.get('description') or '').strip(),
        category=category,
        price=price,
        currency=(data.get('currency') or 'USD').strip().upper(),
        stock=stock,
        unit=(data.get('unit') or 'unidad').strip(),
        image_url=(data.get('image_url') or '').strip(),
        is_active=True,
    )
    db.session.add(product)
    db.session.commit()

    p_dict = product.to_dict()
    return jsonify({'message': 'Producto creado exitosamente', 'data': p_dict, 'product': p_dict}), 201


@catalog_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """Update an existing product."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    product = CatalogProduct.query.filter_by(company_id=company.id, id=product_id).first()
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    data = request.get_json() or {}
    if 'name' in data and str(data['name']).strip():
        product.name = str(data['name']).strip()
    if 'description' in data:
        product.description = str(data['description'] or '').strip()
    if 'category' in data:
        product.category = str(data['category'] or 'General').strip()
    if 'sku' in data and str(data['sku']).strip():
        product.sku = str(data['sku']).strip()
    if 'barcode' in data and str(data['barcode']).strip():
        product.barcode = str(data['barcode']).strip()
    if 'price' in data:
        try:
            product.price = max(0.0, float(data['price']))
        except (ValueError, TypeError):
            pass
    if 'stock' in data:
        try:
            product.stock = max(0, int(data['stock']))
        except (ValueError, TypeError):
            pass
    if 'unit' in data:
        product.unit = str(data['unit'] or 'unidad').strip()
    if 'image_url' in data:
        product.image_url = str(data['image_url'] or '').strip()

    db.session.commit()
    return jsonify({'message': 'Producto actualizado', 'data': product.to_dict()})


@catalog_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """Soft-delete a product from active catalog."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    product = CatalogProduct.query.filter_by(company_id=company.id, id=product_id).first()
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    product.is_active = False
    db.session.commit()
    return jsonify({'message': 'Producto eliminado'})


@catalog_bp.route('/scan/<code_str>', methods=['GET'])
@jwt_required()
def scan_barcode_or_qr(code_str):
    """Fast O(1) lookup by barcode, SKU, or AIKROFY-POS QR payload."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    raw = (code_str or '').strip()
    # If scanned from an AIKROFY-POS QR: "AIKROFY-POS:<company_id>:<sku>:<price>"
    if raw.startswith('AIKROFY-POS:'):
        parts = raw.split(':')
        if len(parts) >= 3:
            raw = parts[2].strip()

    product = CatalogProduct.query.filter(
        CatalogProduct.company_id == company.id,
        CatalogProduct.is_active == True,
        or_(CatalogProduct.barcode == raw, CatalogProduct.sku == raw),
    ).first()

    if not product:
        return jsonify({'error': f'Código no encontrado: {raw}'}), 404

    p_dict = product.to_dict()
    return jsonify({'data': p_dict, 'product': p_dict})


@catalog_bp.route('/orders', methods=['GET'])
@jwt_required()
def list_orders():
    """List recent POS and WhatsApp catalog orders."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        CatalogOrder.__table__.create(db.engine, checkfirst=True)
    except Exception:
        pass

    orders = (
        CatalogOrder.query.filter_by(company_id=company.id)
        .order_by(CatalogOrder.id.desc())
        .limit(50)
        .all()
    )
    orders_list = [o.to_dict() for o in orders]
    return jsonify({'data': orders_list, 'orders': orders_list})


@catalog_bp.route('/orders', methods=['POST'])
@jwt_required()
def create_pos_order():
    """
    Process an in-store POS checkout or manual order, deduct stock atomically,
    and optionally send the digital receipt via WhatsApp.
    """
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        CatalogProduct.__table__.create(db.engine, checkfirst=True)
        CatalogOrder.__table__.create(db.engine, checkfirst=True)
    except Exception:
        pass

    data = request.get_json() or {}
    raw_items = data.get('items') or []
    if not raw_items:
        return jsonify({'error': 'El carrito está vacío'}), 400

    order_items = []
    subtotal = 0.0
    currency = 'USD'

    for item in raw_items:
        pid = item.get('product_id')
        qty = max(1, int(item.get('quantity') or item.get('qty') or 1))
        product = CatalogProduct.query.filter_by(company_id=company.id, id=int(pid), is_active=True).first()
        if not product:
            return jsonify({'error': f'Producto ID {pid} no encontrado'}), 404
        if product.stock < qty:
            return jsonify({
                'error': f"Stock insuficiente para '{product.name}' (Disponible: {product.stock}, Solicitado: {qty})"
            }), 400

        product.stock -= qty
        line_sub = round(float(product.price or 0.0) * qty, 2)
        subtotal += line_sub
        currency = product.currency or 'USD'

        order_items.append({
            'product_id': product.id,
            'sku': product.sku,
            'barcode': product.barcode,
            'name': product.name,
            'quantity': qty,
            'unit_price': round(float(product.price or 0.0), 2),
            'subtotal': line_sub,
        })

    discount = max(0.0, float(data.get('discount_amount', 0.0) or 0.0))
    tax_rate = max(0.0, float(data.get('tax_rate', 0.0) or 0.0))
    taxable = max(0.0, subtotal - discount)
    if 'tax_amount' in data and data.get('tax_amount') is not None:
        tax_amount = round(max(0.0, float(data.get('tax_amount') or 0.0)), 2)
    else:
        tax_amount = round(taxable * (tax_rate / 100.0), 2)
    total = round(taxable + tax_amount, 2)

    order_number = f"POS-{company.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    customer_name = (data.get('customer_name') or 'Consumidor Final').strip()
    customer_phone = (data.get('customer_phone') or '').strip()
    customer_tax_id = (data.get('customer_tax_id') or '9999999999999').strip()
    payment_method = (data.get('payment_method') or 'cash').strip()

    order = CatalogOrder(
        company_id=company.id,
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=(data.get('customer_email') or '').strip(),
        customer_tax_id=customer_tax_id,
        items=order_items,
        subtotal=round(subtotal, 2),
        tax_amount=tax_amount,
        discount_amount=round(discount, 2),
        total=total,
        currency=currency,
        payment_method=payment_method,
        status='completed',
        source=data.get('source', 'pos'),
        notes=(data.get('notes') or '').strip(),
    )
    db.session.add(order)
    db.session.commit()

    # Optional: Send digital receipt via WhatsApp if customer_phone is provided
    whatsapp_sent = False
    should_send_wa = data.get('send_whatsapp_receipt', data.get('send_whatsapp', True))
    if customer_phone and should_send_wa:
        try:
            from services.whatsapp_service import WhatsAppService
            lines_txt = "\n".join(
                f"• {it['quantity']}x {it['name']} (${it['unit_price']:.2f}) = ${it['subtotal']:.2f}"
                for it in order_items
            )
            receipt_msg = (
                f"🧾 *COMPROBANTE DE COMPRA — {company.name}*\n"
                f"Orden: `{order.order_number}`\n"
                f"Cliente: {customer_name}\n"
                f"────────────────────\n"
                f"{lines_txt}\n"
                f"────────────────────\n"
                f"*TOTAL PAGADO: ${order.total:.2f} {order.currency}*\n"
                f"Método: {payment_method.upper()}\n\n"
                f"¡Gracias por tu compra!"
            )
            wa_res = WhatsAppService.send_message(str(company.id), customer_phone, receipt_msg)
            whatsapp_sent = bool(wa_res)
        except Exception:
            whatsapp_sent = False

    o_dict = order.to_dict()
    return jsonify({
        'message': 'Venta registrada con éxito',
        'whatsapp_sent': whatsapp_sent,
        'data': o_dict,
        'order': o_dict,
    }), 201
