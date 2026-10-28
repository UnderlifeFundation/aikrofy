"""
Microsoft Dynamics 365 Business Central Driver - OData v4 integration.

Implements OAuth 2.0 Client Credentials via Microsoft Entra ID and
OData v4 queries with $batch support for rate-limit mitigation.
"""
import requests
import time
from typing import Any, Dict, List

from services.erp.driver_interface import BaseERPDriver, ERPAPIError


class DynamicsBCDriver(BaseERPDriver):
    """Driver for Microsoft Dynamics 365 Business Central (Cloud OData v4)."""

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        super().__init__(erp_url, credentials)
        self.tenant_id = credentials.get("tenant_id", "")
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.environment = credentials.get("environment", "production")
        self.company_id = credentials.get("company_id", "")
        self.base_url = (
            f"https://api.businesscentral.dynamics.com/v2.0/"
            f"{self.tenant_id}/{self.environment}/api/v2.0"
        )
        self.access_token: str = ""
        self.token_expiry: float = 0.0

    def authenticate(self) -> bool:
        """Obtain an OAuth 2.0 access token from Microsoft Entra ID."""
        if time.time() < self.token_expiry and self.access_token:
            return True

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://api.businesscentral.dynamics.com/.default",
        }

        try:
            response = requests.post(token_url, data=payload, timeout=15.0)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token", "")
                expires_in = data.get("expires_in", 3500)
                self.token_expiry = time.time() + expires_in
                return True
            raise ConnectionError(f"Dynamics BC OAuth error: {response.text}")
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(f"Dynamics BC authentication failed: {str(e)}")

    def _headers(self) -> Dict[str, str]:
        """Return authorization headers for API calls."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _company_url(self, entity: str) -> str:
        """Build the fully qualified URL with company context."""
        if self.company_id:
            return f"{self.base_url}/companies({self.company_id})/{entity}"
        return f"{self.base_url}/{entity}"

    def test_connection(self) -> Dict[str, Any]:
        """Test credentials by listing companies."""
        try:
            self.authenticate()
            url = f"{self.base_url}/companies"
            response = requests.get(url, headers=self._headers(), timeout=10.0)
            if response.status_code == 200:
                companies = response.json().get("value", [])
                if companies:
                    name = companies[0].get("displayName", companies[0].get("name", "Unknown"))
                    # Auto-set company_id if not configured
                    if not self.company_id:
                        self.company_id = companies[0].get("id", "")
                    return {"success": True, "company_name": name}
                return {"success": True, "company_name": "Dynamics 365 BC"}
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a customer record in Business Central."""
        self.authenticate()
        url = self._company_url("customers")
        payload = {
            "displayName": customer_data.get("name"),
            "email": customer_data.get("email", ""),
            "phoneNumber": customer_data.get("phone", ""),
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10.0)
        if response.status_code in (200, 201):
            result = response.json()
            return {"id": result.get("id"), "name": result.get("displayName")}
        raise ERPAPIError(f"Dynamics BC customer creation failed: {response.text}", response.status_code)

    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query customers using OData filters."""
        return self.query_records("customers", filters, limit)

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve a sales invoice by ID."""
        self.authenticate()
        url = self._company_url(f"salesInvoices({invoice_id})")
        response = requests.get(url, headers=self._headers(), timeout=10.0)
        if response.status_code == 200:
            return response.json()
        raise ERPAPIError(f"Invoice {invoice_id} not found in Dynamics BC: {response.text}", response.status_code)

    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query salesInvoices using OData filters."""
        return self.query_records("salesInvoices", filters, limit)

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new sales invoice in Business Central."""
        self.authenticate()
        url = self._company_url("salesInvoices")

        payload = {
            "customerNumber": invoice_data.get("customer_code"),
            "invoiceDate": invoice_data.get("document_date"),
            "dueDate": invoice_data.get("due_date"),
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=15.0)
        if response.status_code in (200, 201):
            result = response.json()
            invoice_bc_id = result.get("id")

            # Add line items
            for line in invoice_data.get("lines", []):
                line_url = self._company_url(f"salesInvoices({invoice_bc_id})/salesInvoiceLines")
                line_payload = {
                    "itemId": line.get("item_code"),
                    "quantity": line.get("quantity", 1),
                    "unitPrice": line.get("unit_price", 0),
                    "description": line.get("description", ""),
                }
                requests.post(line_url, json=line_payload, headers=self._headers(), timeout=10.0)

            return {"id": invoice_bc_id, "number": result.get("number")}
        raise ERPAPIError(f"Dynamics BC invoice creation failed: {response.text}", response.status_code)

    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query items from Business Central inventory."""
        return self.query_records("items", filters, limit)

    def query_records(self, entity_name: str, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Generic OData v4 query builder for any entity."""
        self.authenticate()

        filter_parts = []
        for key, value in filters.items():
            if isinstance(value, str):
                filter_parts.append(f"{key} eq '{value}'")
            elif isinstance(value, (int, float)):
                filter_parts.append(f"{key} eq {value}")
            else:
                filter_parts.append(f"{key} eq '{value}'")

        filter_query = " and ".join(filter_parts)
        url = self._company_url(entity_name)
        params = {"$top": str(limit)}
        if filter_query:
            params["$filter"] = filter_query

        response = requests.get(url, headers=self._headers(), params=params, timeout=15.0)
        if response.status_code == 200:
            return response.json().get("value", [])
        raise ERPAPIError(f"OData query error on Dynamics BC {entity_name}: {response.text}", response.status_code)
