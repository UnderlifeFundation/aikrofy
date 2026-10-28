"""
Magento (Adobe Commerce) Adapter — REST API integration.

Authentication: Bearer token (Admin or Integration token).
API surface:   REST /V1/ endpoints.
Key concept:   Guest carts (Quote) with masked cart IDs, separate
               billing/shipping steps, and Quote-to-Order conversion.
"""
import requests
from typing import Dict, List, Any, Optional

from services.ecommerce.base import BaseEcommerceAdapter, EcommerceAPIError


class MagentoAdapter(BaseEcommerceAdapter):

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        super().__init__(store_url, credentials)
        self.access_token = credentials.get('access_token', '')
        if not self.store_url.startswith('http'):
            self.store_url = f"https://{self.store_url}"
        self.base_api = f"{self.store_url}/rest/V1"

    def _headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}',
        }

    def _get(self, endpoint: str, params: dict = None) -> Any:
        url = f"{self.base_api}/{endpoint}"
        resp = self._safe_request('GET', url, headers=self._headers(), params=params)
        return resp.json()

    def _post(self, endpoint: str, data: dict = None) -> Any:
        url = f"{self.base_api}/{endpoint}"
        resp = self._safe_request('POST', url, headers=self._headers(), json=data or {})
        return resp.json()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        try:
            data = self._get('store/storeConfigs')
            if isinstance(data, list) and data:
                store = data[0]
                return {
                    'success': True,
                    'store_name': store.get('base_url', self.store_url),
                }
            return {'success': True, 'store_name': self.store_url}
        except EcommerceAPIError as e:
            if e.status_code == 401:
                return {'success': False, 'error': 'Invalid access token'}
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        params = {
            'searchCriteria[filterGroups][0][filters][0][field]': 'name',
            'searchCriteria[filterGroups][0][filters][0][value]': f'%{query}%',
            'searchCriteria[filterGroups][0][filters][0][conditionType]': 'like',
            'searchCriteria[pageSize]': min(limit, 50),
            'searchCriteria[currentPage]': 1,
        }
        try:
            data = self._get('products', params=params)
        except Exception:
            return []

        products = []
        for p in data.get('items', []):
            # Extract stock from extension_attributes if available
            stock_item = {}
            ext = p.get('extension_attributes', {})
            if ext.get('stock_item'):
                stock_item = ext['stock_item']

            # Extract price from custom_attributes or top-level
            price = str(p.get('price', 0))

            # Find image
            image_url = ''
            for attr in p.get('custom_attributes', []):
                if attr.get('attribute_code') == 'image':
                    image_url = f"{self.store_url}/pub/media/catalog/product{attr['value']}"
                    break

            products.append({
                'id': str(p.get('id', '')),
                'name': p.get('name', ''),
                'price': price,
                'currency': '',  # Magento returns currency via store config
                'stock': stock_item.get('qty', 0) if stock_item.get('is_in_stock') else 0,
                'image_url': image_url,
                'url': '',
                'sku': p.get('sku', ''),
                'variants': [],
            })
        return products

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        try:
            # Magento products are fetched by SKU or ID
            # Try by SKU first (more common), fall back to search by ID
            p = self._get(f'products/{product_id}')
            stock_item = p.get('extension_attributes', {}).get('stock_item', {})
            price = str(p.get('price', 0))
            image_url = ''
            description = ''
            for attr in p.get('custom_attributes', []):
                if attr.get('attribute_code') == 'image':
                    image_url = f"{self.store_url}/pub/media/catalog/product{attr['value']}"
                elif attr.get('attribute_code') == 'description':
                    description = attr.get('value', '')

            return {
                'id': str(p.get('id', '')),
                'name': p.get('name', ''),
                'description': description,
                'price': price,
                'currency': '',
                'stock': stock_item.get('qty', 0) if stock_item.get('is_in_stock') else 0,
                'image_url': image_url,
                'url': '',
                'sku': p.get('sku', ''),
                'variants': [],
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------
    def get_inventory(self, product_id: str) -> Dict[str, Any]:
        product = self.get_product(product_id)
        if not product:
            return {'product_id': product_id, 'total_stock': 0, 'variants': []}
        return {
            'product_id': product_id,
            'total_stock': product.get('stock', 0),
            'variants': [],
        }

    # ------------------------------------------------------------------
    # Orders (Guest Cart → Quote → Order)
    # ------------------------------------------------------------------
    def create_order(self, customer_data: Dict[str, Any], cart_items: List[Dict[str, Any]], notes: str = "") -> Dict[str, Any]:
        """
        Magento order flow:
        1. POST /V1/guest-carts/ → masked cart ID
        2. POST /V1/guest-carts/{id}/items (per item)
        3. POST /V1/guest-carts/{id}/shipping-information
        4. POST /V1/guest-carts/{id}/payment-information → order ID
        """
        try:
            # Step 1: Create guest cart
            cart_id = self._post('guest-carts')
            if not isinstance(cart_id, str):
                return {'success': False, 'error': 'Failed to create Magento guest cart'}

            # Step 2: Add items
            for item in cart_items:
                sku = item.get('sku') or item.get('product_id')
                item_payload = {
                    'cartItem': {
                        'sku': str(sku),
                        'qty': item.get('quantity', 1),
                        'quote_id': cart_id,
                    }
                }
                self._post(f'guest-carts/{cart_id}/items', item_payload)

            # Step 3: Set shipping information
            address = customer_data.get('address', {})
            address_obj = {
                'firstname': customer_data.get('first_name', 'Guest'),
                'lastname': customer_data.get('last_name', 'Customer'),
                'email': customer_data.get('email', ''),
                'telephone': customer_data.get('phone', '0000000000'),
                'street': [address.get('line1', 'N/A')],
                'city': address.get('city', 'N/A'),
                'region': address.get('state', ''),
                'regionId': 0,
                'postcode': address.get('zip', '00000'),
                'countryId': address.get('country', 'US'),
            }
            shipping_payload = {
                'addressInformation': {
                    'shippingAddress': address_obj,
                    'billingAddress': address_obj,
                    'shipping_method_code': 'flatrate',
                    'shipping_carrier_code': 'flatrate',
                }
            }
            self._post(f'guest-carts/{cart_id}/shipping-information', shipping_payload)

            # Step 4: Place order with payment
            payment_payload = {
                'paymentMethod': {'method': 'checkmo'},  # Check/Money Order (manual)
                'billingAddress': address_obj,
            }
            order_id = self._post(f'guest-carts/{cart_id}/payment-information', payment_payload)

            if isinstance(order_id, (int, str)):
                return {
                    'success': True,
                    'order_id': str(order_id),
                    'order_number': str(order_id),
                    'total': '0',  # Total computed by Magento
                    'currency': '',
                    'status': 'pending',
                }
            return {'success': False, 'error': f'Unexpected response: {order_id}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}
