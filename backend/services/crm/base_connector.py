"""
Base CRM Connector - Abstract interface for all CRM integrations.

All platform-specific adapters (HubSpot, Salesforce, Pipedrive, Zoho, Dynamics 365, Custom)
MUST inherit from this class and implement every abstract method. This ensures a
uniform API surface for the LangGraph agent tools regardless of the underlying platform.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from services.crm.canonical_models import Contact, Lead, Account, Deal


class BaseCRMConnector(ABC):
    """
    Abstract base class for CRM platform connectors.

    Each connector receives the crm_url and credentials dict from
    the CRMConfig model and uses them to interact with the
    platform's API.
    """

    def __init__(self, crm_url: Optional[str], credentials: Dict[str, Any]):
        self.crm_url = crm_url.rstrip('/') if crm_url else None
        self.credentials = credentials

    # ------------------------------------------------------------------
    # Connection Validation
    # ------------------------------------------------------------------

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Validate that the credentials are correct by making a lightweight
        API call (e.g. fetching company info or checking API status).

        Returns:
            { "success": True/False, "crm_name": "...", "error": "..." }
        """
        ...

    # ------------------------------------------------------------------
    # Contact Management
    # ------------------------------------------------------------------

    @abstractmethod
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Retrieve a standardized Contact record by ID."""
        ...

    @abstractmethod
    def create_contact(self, contact_data: Dict[str, Any]) -> Contact:
        """Create a Contact record and return the normalized result."""
        ...

    @abstractmethod
    def update_contact(self, contact_id: str, contact_data: Dict[str, Any]) -> Contact:
        """Update a Contact record and return the normalized result."""
        ...

    # ------------------------------------------------------------------
    # Lead Management
    # ------------------------------------------------------------------

    @abstractmethod
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Retrieve a standardized Lead record by ID."""
        ...

    @abstractmethod
    def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        """Create a Lead record and return the normalized result."""
        ...

    @abstractmethod
    def update_lead(self, lead_id: str, lead_data: Dict[str, Any]) -> Lead:
        """Update a Lead record and return the normalized result."""
        ...

    # ------------------------------------------------------------------
    # Account Management
    # ------------------------------------------------------------------

    @abstractmethod
    def get_account(self, account_id: str) -> Optional[Account]:
        """Retrieve a standardized Account record by ID."""
        ...

    @abstractmethod
    def create_account(self, account_data: Dict[str, Any]) -> Account:
        """Create an Account record and return the normalized result."""
        ...

    # ------------------------------------------------------------------
    # Deal / Opportunity Management
    # ------------------------------------------------------------------

    @abstractmethod
    def get_deal(self, deal_id: str) -> Optional[Deal]:
        """Retrieve a standardized Deal record by ID."""
        ...

    @abstractmethod
    def create_deal(self, deal_data: Dict[str, Any]) -> Deal:
        """Create a Deal record and return the normalized result."""
        ...

    @abstractmethod
    def update_deal_stage(self, deal_id: str, new_stage: str) -> Deal:
        """Update a Deal's pipeline stage and return the normalized result."""
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
                    raise CRMAPIError(
                        f"HTTP {resp.status_code}: {resp.text[:300]}",
                        status_code=resp.status_code
                    ) from e
            except requests.exceptions.ConnectionError as e:
                if attempt == max_retries - 1:
                    raise CRMAPIError(f"Connection error: {e}") from e
                time.sleep(1 * (attempt + 1))
            except requests.exceptions.Timeout as e:
                if attempt == max_retries - 1:
                    raise CRMAPIError(f"Request timed out: {e}") from e
                time.sleep(1 * (attempt + 1))

        raise CRMAPIError("Max retries exhausted")


class CRMAPIError(Exception):
    """Custom exception for CRM API errors."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code
