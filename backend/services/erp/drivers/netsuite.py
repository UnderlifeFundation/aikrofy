"""
Oracle NetSuite Driver - REST SuiteTalk / SuiteQL integration.

Implements OAuth 2.0 Client Credentials flow and optimized SuiteQL queries
for reading data, and REST record endpoints for write operations.
"""
import requests
import time
from typing import Any, Dict, List

from services.erp.driver_interface import BaseERPDriver, ERPAPIError


class NetSuiteDriver(BaseERPDriver):
    """Driver for Oracle NetSuite via REST SuiteTalk and SuiteQL."""

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        super().__init__(erp_url, credentials)
        self.account_id = credentials.get("account_id", "")
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.base_url = f"https://{self.account_id}.suitetalk.api.netsuite.com/services/rest"
        self.access_token: str = ""
        self.token_expiry: float = 0.0

    def authenticate(self) -> bool:
        """Obtain or refresh an OAuth 2.0 access token via Client Credentials flow."""
        if time.time() < self.token_expiry and self.access_token:
            return True

        token_url = f"{self.base_url}/auth/oauth2/v1/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(token_url, data=payload, timeout=15.0)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token", "")
                # Default to 3500 seconds (just under 1 hour)
                expires_in = data.get("expires_in", 3500)
                self.token_expiry = time.time() + expires_in
                return True
            raise ConnectionError(f"NetSuite OAuth error: {response.text}")
        except ConnectionError:
            raise
        except Exception as e:
            raise ConnectionError(f"NetSuite authentication failed: {str(e)}")

    def _headers(self) -> Dict[str, str]:
        """Return authorization headers for API calls."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Prefer": "transient",
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test credentials by running a simple SuiteQL query."""
        try:
            self.authenticate()
            result = self._run_suiteql("SELECT companyname FROM company WHERE id = 1", limit=1)
            company_name = result[0].get("companyname", self.account_id) if result else self.account_id
            return {"success": True, "company_name": company_name}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_suiteql(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Execute a SuiteQL query and return results."""
        self.authenticate()
        url = f"{self.base_url}/query/v1/suiteql"
        payload = {"q": query}
        headers = self._headers()
        headers["Prefer"] = f"transient, resultSetMaxSize={limit}"

        response = requests.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code == 200:
            return response.json().get("items", [])
        raise ERPAPIError(f"SuiteQL error: {response.text}", response.status_code)

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a customer record via REST."""
        self.authenticate()
        url = f"{self.base_url}/record/v1/customer"
        payload = {
            "companyName": customer_data.get("name"),
            "email": customer_data.get("email", ""),
            "phone": customer_data.get("phone", ""),
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10.0)
        if response.status_code in (200, 201, 204):
            # NetSuite returns the ID in the Location header
            location = response.headers.get("Location", "")
            record_id = location.rsplit("/", 1)[-1] if location else ""
            return {"id": record_id, "name": customer_data.get("name")}
        raise ERPAPIError(f"NetSuite customer creation failed: {response.text}", response.status_code)

    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query customers using SuiteQL."""
        where_parts = []
        for key, value in filters.items():
            where_parts.append(f"{key} = '{value}'")
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        query = f"SELECT id, companyname, email, phone FROM customer WHERE {where_clause}"
        return self._run_suiteql(query, limit)

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve an invoice by its internal ID."""
        self.authenticate()
        url = f"{self.base_url}/record/v1/invoice/{invoice_id}"
        response = requests.get(url, headers=self._headers(), timeout=10.0)
        if response.status_code == 200:
            return response.json()
        raise ERPAPIError(f"Invoice {invoice_id} not found in NetSuite: {response.text}", response.status_code)

    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query invoices using SuiteQL for optimized reads."""
        where_parts = []
        for key, value in filters.items():
            where_parts.append(f"t.{key} = '{value}'")
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        query = (
            f"SELECT t.id, t.tranid, t.trandate, c.companyname, t.total "
            f"FROM transaction t JOIN customer c ON t.entity = c.id "
            f"WHERE t.type = 'CustInvc' AND {where_clause} "
            f"ORDER BY t.trandate DESC"
        )
        return self._run_suiteql(query, limit)

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invoice record."""
        self.authenticate()
        url = f"{self.base_url}/record/v1/invoice"

        items = []
        for line in invoice_data.get("lines", []):
            items.append({
                "item": {"id": line.get("item_code")},
                "quantity": line.get("quantity", 1),
                "rate": line.get("unit_price", 0),
            })

        payload = {
            "entity": {"id": invoice_data.get("customer_code")},
            "tranDate": invoice_data.get("document_date"),
            "item": {"items": items},
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=15.0)
        if response.status_code in (200, 201, 204):
            location = response.headers.get("Location", "")
            record_id = location.rsplit("/", 1)[-1] if location else ""
            return {"id": record_id}
        raise ERPAPIError(f"NetSuite invoice creation failed: {response.text}", response.status_code)

    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query inventory items using SuiteQL."""
        where_parts = []
        for key, value in filters.items():
            where_parts.append(f"{key} = '{value}'")
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        query = f"SELECT id, itemid, displayname, baseprice, quantityavailable FROM item WHERE {where_clause}"
        return self._run_suiteql(query, limit)

    def query_records(self, entity_name: str, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Generic SuiteQL query for any record type."""
        where_parts = []
        for key, value in filters.items():
            where_parts.append(f"{key} = '{value}'")
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        query = f"SELECT * FROM {entity_name} WHERE {where_clause}"
        return self._run_suiteql(query, limit)
