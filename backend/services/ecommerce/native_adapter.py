"""
Native Catalog Adapter - Built-in E-commerce & POS Engine for Aikrofy.
Implements BaseEcommerceAdapter using Aikrofy's native CatalogProduct & CatalogOrder
MySQL tables so micro-businesses, artisans, and Community Edition users have
full catalog, stock, and order capabilities without needing Shopify or WooCommerce.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import or_

from extensions import db
from models.catalog import CatalogProduct, CatalogOrder
from .base import BaseEcommerceAdapter


class NativeCatalogAdapter(BaseEcommerceAdapter):
    """Built-in Aikrofy Catalog & POS adapter backed by SQLAlchemy."""

    def __init__(self, company_id: int, company_name: str = "Aikrofy Store"):
        super().__init__(store_url=f"native://company/{company_id}", credentials={})
        self.company_id = company_id
        self.company_name = company_name

    def test_connection(self) -> Dict[str, Any]:
        count = CatalogProduct.query.filter_by(company_id=self.company_id, is_active=True).count()
        return {
            "success": True,
            "store_name": f"{self.company_name} (Catálogo Nativo & POS)",
            "products_count": count,
        }

    def _format_product(self, p: CatalogProduct) -> Dict[str, Any]:
        return {
            "id": str(p.id),
            "sku": p.sku,
            "barcode": p.barcode,
            "name": p.name,
            "description": p.description or "",
            "short_description": p.description or "",
            "category": p.category or "General",
            "price": f"{float(p.price or 0.0):.2f}",
            "currency": p.currency or "USD",
            "stock": int(p.stock or 0),
            "image_url": p.image_url or "",
            "url": "",
            "variants": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "sku": p.sku,
                    "price": f"{float(p.price or 0.0):.2f}",
                    "stock": int(p.stock or 0),
                }
            ],
        }

    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = CatalogProduct.query.filter_by(company_id=self.company_id, is_active=True)
        if query and query.strip():
            term = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    CatalogProduct.name.ilike(term),
                    CatalogProduct.description.ilike(term),
                    CatalogProduct.category.ilike(term),
                    CatalogProduct.sku.ilike(term),
                    CatalogProduct.barcode.ilike(term),
                )
            )
        products = q.order_by(CatalogProduct.id.desc()).limit(limit).all()
        return [self._format_product(p) for p in products]

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        clean = str(product_id).strip()
        p = None
        if clean.isdigit():
            p = CatalogProduct.query.filter_by(company_id=self.company_id, id=int(clean)).first()
        if not p:
            p = CatalogProduct.query.filter(
                CatalogProduct.company_id == self.company_id,
                or_(CatalogProduct.sku == clean, CatalogProduct.barcode == clean),
            ).first()
        return self._format_product(p) if p else None

    def get_inventory(self, product_id: str) -> Dict[str, Any]:
        prod = self.get_product(product_id)
        if not prod:
            return {"product_id": str(product_id), "total_stock": 0, "variants": []}
        return {
            "product_id": prod["id"],
            "total_stock": prod["stock"],
            "variants": prod["variants"],
        }

    def create_order(
        self,
        customer_data: Dict[str, Any],
        cart_items: List[Dict[str, Any]],
        notes: str = "",
    ) -> Dict[str, Any]:
        try:
            order_items = []
            subtotal = 0.0
            currency = "USD"

            for item in cart_items:
                pid = str(item.get("product_id", "")).strip()
                qty = max(1, int(item.get("quantity", 1)))
                p = None
                if pid.isdigit():
                    p = CatalogProduct.query.filter_by(company_id=self.company_id, id=int(pid)).first()
                if not p:
                    p = CatalogProduct.query.filter(
                        CatalogProduct.company_id == self.company_id,
                        or_(CatalogProduct.sku == pid, CatalogProduct.barcode == pid),
                    ).first()
                if not p:
                    return {"success": False, "error": f"Producto no encontrado: {pid}"}
                if p.stock < qty:
                    return {
                        "success": False,
                        "error": f"Stock insuficiente para '{p.name}' (disponible: {p.stock}, solicitado: {qty})",
                    }

                p.stock -= qty
                line_total = round(float(p.price or 0.0) * qty, 2)
                subtotal += line_total
                currency = p.currency or "USD"
                order_items.append(
                    {
                        "product_id": p.id,
                        "sku": p.sku,
                        "barcode": p.barcode,
                        "name": p.name,
                        "quantity": qty,
                        "unit_price": round(float(p.price or 0.0), 2),
                        "subtotal": line_total,
                    }
                )

            order_number = f"POS-{self.company_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            full_name = f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip() or "Cliente WhatsApp"

            order = CatalogOrder(
                company_id=self.company_id,
                order_number=order_number,
                customer_name=full_name,
                customer_phone=customer_data.get("phone", ""),
                customer_email=customer_data.get("email", ""),
                items=order_items,
                subtotal=round(subtotal, 2),
                tax_amount=0.0,
                discount_amount=0.0,
                total=round(subtotal, 2),
                currency=currency,
                payment_method=customer_data.get("payment_method", "whatsapp_order"),
                status="completed",
                source="whatsapp_ai",
                notes=notes,
            )
            db.session.add(order)
            db.session.commit()

            return {
                "success": True,
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total": f"{order.total:.2f}",
                "currency": order.currency,
                "status": order.status,
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
