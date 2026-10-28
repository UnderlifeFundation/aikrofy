"""
SAP Business One Driver - OData v4 Service Layer integration.

Implements session-based cookie authentication, OData query construction,
and automatic session renewal as specified in the ERP integration architecture.
"""
import requests
import time
from typing import Any, Dict, List, Optional

from services.erp.driver_interface import BaseERPDriver, ERPAPIError


class SAPBusinessOneDriver(BaseERPDriver):
    """Transactional driver for the SAP Business One Service Layer (OData v4)."""

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        super().__init__(erp_url, credentials)
        self.base_url = f"{self.erp_url}/b1s/v2"
        self.company_db = credentials.get("company_db", "")
        self.username = credentials.get("username", "")
        self.password = credentials.get("password", "")
        self.session = requests.Session()
        self.session.verify = credentials.get("verify_ssl", False)
        self.session_expiry: float = 0.0
        self.session_timeout = 1800.0  # Standard 30-minute session lifespan

    def authenticate(self) -> bool:
        """Establish and initiate session against the Login corporate endpoint."""
        current_time = time.time()
        if current_time < self.session_expiry:
            return True

        url = f"{self.base_url}/Login"
        payload = {
            "CompanyDB": self.company_db,
            "UserName": self.username,
            "Password": self.password
        }

        try:
            # Login calls carry ~5 second latency due to DI Core initialization
            response = self.session.post(url, json=payload, timeout=15.0)
            if response.status_code == 200:
                self.session_expiry = time.time() + self.session_timeout
                # Requests transparently manages B1SESSION and ROUTEID cookies
                return True
            raise ConnectionError(f"SAP B1 login error: {response.text}")
        except Exception as e:
            raise ConnectionError(f"SAP Business One connection failed: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """Test credentials by logging in and fetching company info."""
        try:
            self.authenticate()
            # Fetch a single business partner to validate access
            url = f"{self.base_url}/CompanyService_GetCompanyInfo"
            response = self.session.post(url, timeout=10.0)
            if response.status_code == 200:
                info = response.json()
                return {
                    "success": True,
                    "company_name": info.get("CompanyName", self.company_db),
                    "version": info.get("Version", "Unknown"),
                }
            return {"success": True, "company_name": self.company_db}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new BusinessPartner of type Customer in SAP B1."""
        self.authenticate()
        url = f"{self.base_url}/BusinessPartners"
        payload = {
            "CardCode": customer_data.get("customer_code") or customer_data.get("customer_id"),
            "CardName": customer_data.get("name"),
            "CardType": "cCustomer",
            "EmailAddress": customer_data.get("email", ""),
            "Phone1": customer_data.get("phone", ""),
        }

        response = self.session.post(url, json=payload, timeout=10.0)
        if response.status_code == 201:
            return response.json()
        raise ERPAPIError(f"SAP B1 customer creation failed: {response.text}", response.status_code)

    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query BusinessPartners of type Customer."""
        base_filter = "CardType eq 'cCustomer'"
        return self.query_records("BusinessPartners", filters, limit, base_filter=base_filter)

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve a specific invoice with field projection."""
        self.authenticate()
        url = (
            f"{self.base_url}/Invoices({invoice_id})"
            f"?$select=DocEntry,DocNum,CardCode,CardName,DocDate,DocDueDate,DocTotal,DocCurrency,DocumentStatus,DocumentLines"
        )
        response = self.session.get(url, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        raise ERPAPIError(f"Invoice {invoice_id} not found in SAP B1: {response.text}", response.status_code)

    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query invoices using OData filters."""
        return self.query_records("Invoices", filters, limit)

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invoice document in SAP B1."""
        self.authenticate()
        url = f"{self.base_url}/Invoices"

        lines = []
        for line in invoice_data.get("lines", []):
            lines.append({
                "ItemCode": line.get("item_code"),
                "Quantity": line.get("quantity", 1),
                "UnitPrice": line.get("unit_price", 0),
            })

        payload = {
            "CardCode": invoice_data.get("customer_code"),
            "DocDate": invoice_data.get("document_date"),
            "DocDueDate": invoice_data.get("due_date"),
            "DocumentLines": lines,
        }

        response = self.session.post(url, json=payload, timeout=15.0)
        if response.status_code == 201:
            return response.json()
        raise ERPAPIError(f"SAP B1 invoice creation failed: {response.text}", response.status_code)

    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query Items from inventory."""
        return self.query_records("Items", filters, limit)

    def query_records(
        self,
        entity_name: str,
        filters: Dict[str, Any],
        limit: int = 50,
        base_filter: str = ""
    ) -> List[Dict[str, Any]]:
        """Generic OData query builder for any entity."""
        self.authenticate()

        # Build OData $filter from dict
        filter_parts = []
        if base_filter:
            filter_parts.append(base_filter)
        for key, value in filters.items():
            if isinstance(value, str):
                filter_parts.append(f"{key} eq '{value}'")
            elif isinstance(value, (int, float)):
                filter_parts.append(f"{key} eq {value}")
            else:
                filter_parts.append(f"{key} eq '{value}'")

        filter_query = " and ".join(filter_parts)
        url = f"{self.base_url}/{entity_name}"
        if filter_query:
            url += f"?$filter={filter_query}&$top={limit}"
        else:
            url += f"?$top={limit}"

        # Inject pagination preference header
        headers = {"Prefer": f"odata.maxpagesize={limit}"}

        response = self.session.get(url, timeout=15.0, headers=headers)
        if response.status_code == 200:
            return response.json().get("value", [])
        raise ERPAPIError(f"OData query error on SAP {entity_name}: {response.text}", response.status_code)
