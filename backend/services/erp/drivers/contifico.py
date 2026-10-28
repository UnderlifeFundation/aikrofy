"""
Contifico ERP Driver - Integration with Siigo Contífico (Ecuador).

Implements the REST API (v1) of Contifico, including endpoints for invoice creation,
business partners (personas), items, and queries.
"""
import requests
import time
from typing import Any, Dict, List, Optional
from services.erp.driver_interface import BaseERPDriver, ERPAPIError


class ContificoDriver(BaseERPDriver):
    """Transactional driver for the Siigo Contífico API (Ecuador)."""

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        # Default Contífico API v1 endpoint if none provided
        url = erp_url or "https://api.contifico.com/sistema/api/v1"
        super().__init__(url, credentials)
        self.api_key = credentials.get("api_key", "")
        self.pos_token = credentials.get("pos_token", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        })
        self.session.verify = True

    def authenticate(self) -> bool:
        """Contífico uses static API Keys. Validate by querying a single record."""
        try:
            url = f"{self.erp_url}/persona/"
            response = self.session.get(url, params={"limit": 1}, timeout=10.0)
            if response.status_code == 200:
                return True
            raise ConnectionError(f"Contifico authentication failed with HTTP {response.status_code}: {response.text}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Contifico: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """Validate credential state."""
        try:
            success = self.authenticate()
            return {
                "success": success,
                "company_name": "Contifico ERP Connection",
                "message": "Successfully authenticated with Contifico API."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a client/person in Contifico."""
        self.authenticate()
        url = f"{self.erp_url}/persona/"
        
        payload = {
            "cedula": customer_data.get("tax_id") or customer_data.get("cedula") or "",
            "nombre": customer_data.get("name") or customer_data.get("razon_social") or "",
            "tipo": customer_data.get("type", "C"), # C = Cliente, P = Proveedor
            "telefonos": customer_data.get("phone", ""),
            "email": customer_data.get("email", ""),
            "direccion": customer_data.get("address", "")
        }

        response = self.session.post(url, json=payload, timeout=10.0)
        if response.status_code in [200, 201]:
            return response.json()
        raise ERPAPIError(f"Contifico customer creation failed: {response.text}", response.status_code)

    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query clients from Contifico."""
        filters = dict(filters)
        filters.setdefault("tipo", "C")
        return self.query_records("persona", filters, limit)

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve detailed information of a document."""
        self.authenticate()
        url = f"{self.erp_url}/documento/{invoice_id}/"
        response = self.session.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        raise ERPAPIError(f"Invoice {invoice_id} not found in Contifico: {response.text}", response.status_code)

    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query invoices from Contifico."""
        filters = dict(filters)
        # FAC represents invoices in Contifico documents
        filters.setdefault("tipo", "FAC")
        return self.query_records("registro/documento", filters, limit)

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a document invoice in Contifico."""
        self.authenticate()
        url = f"{self.erp_url}/documento/"

        # Handle details/lines mapping
        lines = []
        subtotal_0 = 0.0
        subtotal_12 = 0.0
        iva_total = 0.0
        
        for line in invoice_data.get("lines", []):
            qty = float(line.get("quantity", 1))
            price = float(line.get("unit_price", 0))
            taxable = qty * price
            vat_rate = int(line.get("vat_rate", 12))
            
            line_data = {
                "producto_id": line.get("item_code") or line.get("product_id"),
                "cantidad": qty,
                "precio": price,
                "porcentaje_iva": vat_rate,
                "base_gravable": taxable
            }
            lines.append(line_data)
            
            # Simple tax calculation helper
            if vat_rate == 0:
                subtotal_0 += taxable
            else:
                subtotal_12 += taxable
                iva_total += taxable * (vat_rate / 100.0)

        total_amount = subtotal_0 + subtotal_12 + iva_total

        # Build payload matching the Contifico schema
        payload = {
            "pos": self.pos_token,
            "fecha_emision": invoice_data.get("document_date") or time.strftime("%d/%m/%Y"),
            "tipo_documento": "FAC",
            "tipo_registro": invoice_data.get("type_record", "CLI"), # CLI = Clientes
            "estado": invoice_data.get("status", "P"), # P = Pendiente
            "cliente": {
                "ruc": invoice_data.get("customer_tax_id") or invoice_data.get("customer_code"),
                "razon_social": invoice_data.get("customer_name") or invoice_data.get("name"),
                "tipo": invoice_data.get("customer_type", "N"), # N = Natural, J = Jurídica
                "email": invoice_data.get("customer_email") or invoice_data.get("email", "")
            },
            "subtotal_0": round(subtotal_0, 2),
            "subtotal_12": round(subtotal_12, 2),
            "iva": round(iva_total, 2),
            "total": round(total_amount, 2),
            "detalles": lines
        }

        response = self.session.post(url, json=payload, timeout=15.0)
        if response.status_code in [200, 201]:
            return response.json()
        raise ERPAPIError(f"Contifico invoice creation failed: {response.text}", response.status_code)

    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query items/products catalog."""
        return self.query_records("producto", filters, limit)

    def query_records(self, entity_name: str, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Generic query to Contifico endpoints."""
        self.authenticate()
        url = f"{self.erp_url}/{entity_name}/"
        
        # Build URL parameters from query filters
        params = dict(filters)
        params.setdefault("limit", limit)
        
        response = self.session.get(url, params=params, timeout=15.0)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data[:limit]
            return data.get("results", []) if isinstance(data, dict) else []
        raise ERPAPIError(f"Contifico query failed on {entity_name}: {response.text}", response.status_code)
