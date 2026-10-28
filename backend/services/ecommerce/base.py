"""
Base E-commerce Adapter - Abstract interface for all platform integrations.

All platform-specific adapters (Shopify, WooCommerce, etc.) MUST inherit from
this class and implement every abstract method. This ensures a uniform API
surface for the LangGraph agent tools regardless of the underlying platform.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseEcommerceAdapter(ABC):
    """
    Abstract base class for e-commerce platform adapters.

    Each adapter receives the store_url and credentials dict from
    the EcommerceConfig model and uses them to interact with the
    platform's API.
    """

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        self.store_url = store_url.rstrip('/')
        self.credentials = credentials

    # ------------------------------------------------------------------
    # Connection Validation
    # ------------------------------------------------------------------

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Validate that the credentials are correct by making a lightweight
        API call (e.g. fetching store info or a single product).

        Returns:
            { "success": True/False, "store_name": "...", "error": "..." }
        """
        ...

    # ------------------------------------------------------------------
    # Product Catalog
    # ------------------------------------------------------------------

    @abstractmethod
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the product catalog by keyword.

        Returns a list of standardized product dicts:
        [
            {
                "id": "...",
                "name": "...",
                "price": "19.99",
                "currency": "USD",
                "stock": 42,
                "image_url": "...",
                "url": "...",
                "variants": [ { "id": "...", "name": "...", "price": "...", "stock": ... } ]
            }
        ]
        """
        ...

    @abstractmethod
    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a single product by its platform ID.

        Returns the same standardized dict as search_products items,
        or None if not found.
        """
        ...

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    @abstractmethod
    def get_inventory(self, product_id: str) -> Dict[str, Any]:
        """
        Get real-time stock levels for a product (and its variants).

        Returns:
            {
                "product_id": "...",
                "total_stock": 42,
                "variants": [
                    { "id": "...", "name": "...", "stock": 10 }
                ]
            }
        """
        ...

    # ------------------------------------------------------------------
    # Order Creation
    # ------------------------------------------------------------------

    @abstractmethod
    def create_order(
        self,
        customer_data: Dict[str, Any],
        cart_items: List[Dict[str, Any]],
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Create an order on the platform.

        Args:
            customer_data: {
                "email": "...",
                "first_name": "...",
                "last_name": "...",
                "phone": "...",
                "address": { "line1": "", "city": "", "state": "", "zip": "", "country": "" }
            }
            cart_items: [
                { "product_id": "...", "variant_id": "...", "quantity": 1 }
            ]
            notes: Optional order notes from the conversation.

        Returns:
            {
                "success": True/False,
                "order_id": "...",
                "order_number": "...",
                "total": "99.99",
                "currency": "USD",
                "status": "pending",
                "checkout_url": "...",  (optional — for redirect-based checkout)
                "error": "..."
            }
        """
        ...

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_request(self, method, url, **kwargs) -> Any:
        """Utility wrapper around requests with timeout and error handling."""
        import requests

        kwargs.setdefault('timeout', 15)
        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            raise EcommerceAPIError(
                f"HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise EcommerceAPIError(f"Connection error: {e}") from e
        except requests.exceptions.Timeout as e:
            raise EcommerceAPIError(f"Request timed out: {e}") from e


class EcommerceAPIError(Exception):
    """Custom exception for e-commerce API errors."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code
