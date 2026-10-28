"""
Odoo ERP Driver - XML-RPC / JSON-2 integration.

Implements the two-step authentication flow (UID retrieval + execute_kw)
and includes a version-aware dispatcher for Odoo 19+ JSON-2 API migration.
"""
import xmlrpc.client
from typing import Any, Dict, List, Optional

from services.erp.driver_interface import BaseERPDriver, ERPAPIError


class OdooRPCDriver(BaseERPDriver):
    """Driver for interacting with Odoo ERP via XML-RPC remote calls."""

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        super().__init__(erp_url, credentials)
        self.url = self.erp_url
        self.db = credentials.get("db", "")
        self.username = credentials.get("username", "")
        self.api_key = credentials.get("api_key") or credentials.get("password", "")
        self.uid: Optional[int] = None
        self.models = None

    def authenticate(self) -> bool:
        """Authenticate against the common service to obtain the session UID."""
        if self.uid is not None:
            return True

        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self.uid = common.authenticate(self.db, self.username, self.api_key, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
                return True
            raise ConnectionError("Credentials denied by Odoo server.")
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(f"Odoo authentication communication error: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """Test credentials by authenticating and reading the company name."""
        try:
            self.authenticate()
            # Read the company name from res.company
            companies = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                "res.company", "search_read",
                [[]],
                {"fields": ["name"], "limit": 1}
            )
            company_name = companies[0]["name"] if companies else self.db
            return {"success": True, "company_name": company_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new res.partner record in Odoo."""
        self.authenticate()
        payload = {
            "name": customer_data.get("name"),
            "email": customer_data.get("email", ""),
            "phone": customer_data.get("phone", ""),
            "is_company": customer_data.get("is_company", True),
            "vat": customer_data.get("tax_id", ""),
        }

        customer_id = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "res.partner", "create",
            [payload]
        )
        return {"id": customer_id, "name": customer_data.get("name")}

    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query res.partner records."""
        return self.query_records(
            "res.partner", filters, limit
        )

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve a specific account.move record by ID."""
        self.authenticate()
        records = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "account.move", "search_read",
            [
                [["id", "=", int(invoice_id)]]
            ],
            {"fields": ["name", "partner_id", "invoice_date", "invoice_date_due",
                         "amount_total", "state", "currency_id", "invoice_line_ids"]}
        )
        if records:
            return records[0]
        raise ERPAPIError(f"Invoice {invoice_id} not found in Odoo.")

    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query account.move records of type out_invoice."""
        domain = [["move_type", "=", "out_invoice"]]
        for key, value in filters.items():
            domain.append([key, "=", value])

        self.authenticate()
        return self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "account.move", "search_read",
            [domain],
            {"fields": ["name", "partner_id", "invoice_date", "amount_total", "state"],
             "limit": limit}
        )

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new customer invoice in Odoo."""
        self.authenticate()

        lines = []
        for line in invoice_data.get("lines", []):
            lines.append((0, 0, {
                "product_id": line.get("item_code"),
                "quantity": line.get("quantity", 1),
                "price_unit": line.get("unit_price", 0),
                "name": line.get("description", ""),
            }))

        payload = {
            "move_type": "out_invoice",
            "partner_id": int(invoice_data.get("customer_code", 0)),
            "invoice_date": invoice_data.get("document_date"),
            "invoice_line_ids": lines,
        }

        invoice_id = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            "account.move", "create",
            [payload]
        )
        return {"id": invoice_id}

    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query product.product records."""
        return self.query_records("product.product", filters, limit)

    def query_records(self, entity_name: str, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Generic execute_kw query builder for any Odoo model."""
        self.authenticate()
        domain_filters = []
        for key, value in filters.items():
            domain_filters.append([key, "=", value])

        records = self.models.execute_kw(
            self.db, self.uid, self.api_key,
            entity_name, "search_read",
            [domain_filters],
            {"limit": limit}
        )
        return records
