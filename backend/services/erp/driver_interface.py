"""
BaseERPDriver - Abstract interface for all ERP platform integrations.

All platform-specific drivers (SAP B1, NetSuite, Odoo, Dynamics BC) MUST
inherit from this class and implement every abstract method. This ensures
a uniform API surface for the LangGraph agent tools regardless of the
underlying ERP system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseERPDriver(ABC):
    """
    Abstract base class for ERP platform drivers.

    Each driver receives the erp_url and credentials dict from
    the ERPConfig model and uses them to interact with the
    platform's API.
    """

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        self.erp_url = erp_url.rstrip('/')
        self.credentials = credentials

    # ------------------------------------------------------------------
    # Connection & Authentication
    # ------------------------------------------------------------------

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Initialize and validate the authentication context with the client's ERP.
        Must store and renew credentials in cache transparently.

        Returns:
            True if authentication succeeded.

        Raises:
            ConnectionError if authentication fails.
        """
        ...

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Validate that the credentials are correct by making a lightweight
        API call (e.g. fetching company info or a single record).

        Returns:
            { "success": True/False, "company_name": "...", "error": "..." }
        """
        ...

    # ------------------------------------------------------------------
    # Customer Management
    # ------------------------------------------------------------------

    @abstractmethod
    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a customer record in the target ERP.
        Receives a dictionary with canonical format and returns the
        normalized response.
        """
        ...

    @abstractmethod
    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Query customer records using canonical filters.
        """
        ...

    # ------------------------------------------------------------------
    # Invoice Management
    # ------------------------------------------------------------------

    @abstractmethod
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Retrieve the information of a specific invoice using its ID.
        Returns fields mapped under the canonical data schema.
        """
        ...

    @abstractmethod
    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Query invoices using canonical filters translated to ERP-native syntax.
        """
        ...

    @abstractmethod
    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new invoice in the ERP.
        """
        ...

    # ------------------------------------------------------------------
    # Inventory / Items
    # ------------------------------------------------------------------

    @abstractmethod
    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Query products/items from the ERP inventory.
        """
        ...

    # ------------------------------------------------------------------
    # Generic Record Operations
    # ------------------------------------------------------------------

    @abstractmethod
    def query_records(self, entity_name: str, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Perform queries on any entity, translating local filters to
        the ERP's syntax (OData filter, SuiteQL, or Odoo Domains).
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_request(self, method: str, url: str, **kwargs) -> Any:
        """Utility wrapper around requests with timeout, retry, and error handling."""
        import requests
        import time
        import random

        kwargs.setdefault('timeout', 15)
        max_retries = 3

        for attempt in range(max_retries):
            try:
                resp = requests.request(method, url, **kwargs)
                if resp.status_code == 429:
                    # Rate limited — exponential backoff with jitter
                    base_delay = 1.5
                    max_delay = 60.0
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.5)
                    time.sleep(delay + jitter)
                    continue
                resp.raise_for_status()
                return resp
            except requests.exceptions.HTTPError as e:
                if attempt == max_retries - 1:
                    raise ERPAPIError(
                        f"HTTP {resp.status_code}: {resp.text[:300]}",
                        status_code=resp.status_code
                    ) from e
            except requests.exceptions.ConnectionError as e:
                if attempt == max_retries - 1:
                    raise ERPAPIError(f"Connection error: {e}") from e
                time.sleep(1 * (attempt + 1))
            except requests.exceptions.Timeout as e:
                if attempt == max_retries - 1:
                    raise ERPAPIError(f"Request timed out: {e}") from e
                time.sleep(1 * (attempt + 1))

        raise ERPAPIError("Max retries exhausted")


class ERPAPIError(Exception):
    """Custom exception for ERP API errors."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code
