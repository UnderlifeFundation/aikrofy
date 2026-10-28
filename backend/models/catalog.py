"""
Native Catalog & AI-POS Models (CatalogProduct & CatalogOrder)
Allows micro-businesses, artisans, and self-hosted Open-Core users to manage
products, barcodes/QRs, stock, and in-store/WhatsApp POS orders natively
without requiring an external Shopify or WooCommerce subscription.
"""
from datetime import datetime
from extensions import db


class CatalogProduct(db.Model):
    """Native product & inventory item bounded to a Company."""
    __tablename__ = 'catalog_products'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)

    sku = db.Column(db.String(64), nullable=False, index=True)
    barcode = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), default='General')

    price = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(10), nullable=False, default='USD')
    stock = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(32), default='unidad')

    image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'sku': self.sku,
            'barcode': self.barcode,
            'name': self.name,
            'description': self.description or '',
            'category': self.category or 'General',
            'price': round(float(self.price or 0.0), 2),
            'currency': self.currency or 'USD',
            'stock': int(self.stock or 0),
            'unit': self.unit or 'unidad',
            'image_url': self.image_url or '',
            'is_active': bool(self.is_active),
            'qr_payload': f"AIKROFY-POS:{self.company_id}:{self.sku}:{round(float(self.price or 0.0), 2)}",
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CatalogOrder(db.Model):
    """Native POS & WhatsApp Commerce Order bounded to a Company."""
    __tablename__ = 'catalog_orders'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    order_number = db.Column(db.String(64), nullable=False, index=True)

    customer_name = db.Column(db.String(255), default='Consumidor Final')
    customer_phone = db.Column(db.String(64), nullable=True)
    customer_email = db.Column(db.String(255), nullable=True)
    customer_tax_id = db.Column(db.String(64), default='9999999999999')

    # List of {product_id, sku, name, quantity, unit_price, subtotal}
    items = db.Column(db.JSON, default=list)

    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(10), nullable=False, default='USD')

    payment_method = db.Column(db.String(50), default='cash')  # cash, transfer, qr, card, payment_link
    status = db.Column(db.String(50), default='completed')     # completed, pending, cancelled
    source = db.Column(db.String(50), default='pos')           # pos, whatsapp_ai, web_catalog
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'order_number': self.order_number,
            'customer_name': self.customer_name or 'Consumidor Final',
            'customer_phone': self.customer_phone or '',
            'customer_email': self.customer_email or '',
            'customer_tax_id': self.customer_tax_id or '9999999999999',
            'items': self.items or [],
            'subtotal': round(float(self.subtotal or 0.0), 2),
            'tax_amount': round(float(self.tax_amount or 0.0), 2),
            'discount_amount': round(float(self.discount_amount or 0.0), 2),
            'total': round(float(self.total or 0.0), 2),
            'currency': self.currency or 'USD',
            'payment_method': self.payment_method or 'cash',
            'status': self.status or 'completed',
            'source': self.source or 'pos',
            'notes': self.notes or '',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
