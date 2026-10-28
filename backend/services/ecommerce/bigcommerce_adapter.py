"""
BigCommerce Adapter — Hybrid V2/V3 REST API integration.

Authentication: X-Auth-Token header with store hash in URL.
API surface:   V3 Catalog, V2 Orders, Storefront GraphQL.
Rate limiting:  Header-based (X-Rate-Limit-Requests-Left).
"""
import time
import requests
from typing import Dict, List, Any, Optional

from services.ecommerce.base import BaseEcommerceAdapter, EcommerceAPIError


class BigCommerceAdapter(BaseEcommerceAdapter):

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        super().__init__(store_url, credentials)
        self.access_token = credentials.get('access_token', '')
        self.store_hash = credentials.get('store_hash', '')
        # BigCommerce API base: https://api.bigcommerce.com/stores/{store_hash}
        self.api_base = f"https://api.bigcommerce.com/stores/{self.store_hash}"

    def _headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Auth-Token': self.access_token,
        }

    def _handle_rate_limit(self, resp):
        """Check rate limit headers and sleep if needed."""
        remaining = resp.headers.get('X-Rate-Limit-Requests-Left')
        if remaining and int(remaining) < 5:
            reset_ms = int(resp.headers.get('X-Rate-Limit-Time-Reset-Ms', 1000))
            time.sleep(reset_ms / 1000.0)

    def _get(self, endpoint: str, params: dict = None) -> Any:
        url = f"{self.api_base}/{endpoint}"
        resp = self._safe_request('GET', url, headers=self._headers(), params=params)
        self._handle_rate_limit(resp)
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> Any:
        url = f"{self.api_base}/{endpoint}"
        resp = self._safe_request('POST', url, headers=self._headers(), json=data)
        self._handle_rate_limit(resp)
        return resp.json()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        try:
            data = self._get('v2/store')
            return {
                'success': True,
                'store_name': data.get('name', self.store_hash),
            }
        except EcommerceAPIError as e:
            if e.status_code in (401, 403):
                return {'success': False, 'error': 'Invalid store hash or access token'}
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Products (V3 Catalog)
    # ------------------------------------------------------------------
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            data = self._get('v3/catalog/products', params={
                'keyword': query,
                'limit': min(limit, 250),
                'include': 'variants,images',
                'is_visible': True,
            })
        except Exception:
            return []

        products = []
        for p in data.get('data', []):
            variants = []
            total_stock = 0
            for v in p.get('variants', []):
                stock = v.get('inventory_level', 0)
                total_stock += stock
                variants.append({
                    'id': str(v.get('id', '')),
                    'name': v.get('option_values', [{}])[0].get('label', '') if v.get('option_values') else '',
                    'price': str(v.get('price', p.get('price', 0))),
                    'stock': stock,
                })

            images = p.get('images', [])
            image_url = images[0].get('url_standard', '') if images else ''

            if not variants:
                total_stock = p.get('inventory_level', 0)

            products.append({
                'id': str(p.get('id', '')),
                'name': p.get('name', ''),
                'price': str(p.get('price', 0)),
                'currency': '',  # Set via store config
                'stock': total_stock,
                'image_url': image_url,
                'url': p.get('custom_url', {}).get('url', ''),
                'variants': variants,
            })
        return products

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = self._get(f'v3/catalog/products/{product_id}', params={
                'include': 'variants,images',
            })
            p = data.get('data', {})
            if not p:
                return None

            variants = []
            total_stock = 0
            for v in p.get('variants', []):
                stock = v.get('inventory_level', 0)
                total_stock += stock
                variants.append({
                    'id': str(v.get('id', '')),
                    'name': v.get('option_values', [{}])[0].get('label', '') if v.get('option_values') else '',
                    'price': str(v.get('price', p.get('price', 0))),
                    'stock': stock,
                })

            images = p.get('images', [])
            if not variants:
                total_stock = p.get('inventory_level', 0)

            return {
                'id': str(p.get('id', '')),
                'name': p.get('name', ''),
                'description': p.get('description', ''),
                'price': str(p.get('price', 0)),
                'currency': '',
                'stock': total_stock,
                'image_url': images[0].get('url_standard', '') if images else '',
                'url': p.get('custom_url', {}).get('url', ''),
                'variants': variants,
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
            'total_stock': product['stock'],
            'variants': [{'id': v['id'], 'name': v['name'], 'stock': v['stock']} for v in product['variants']],
        }

    # ------------------------------------------------------------------
    # Orders (V2 Orders API — single-call creation)
    # ------------------------------------------------------------------
    def create_order(self, customer_data: Dict[str, Any], cart_items: List[Dict[str, Any]], notes: str = "") -> Dict[str, Any]:
        address = customer_data.get('address', {})
        billing_address = {
            'first_name': customer_data.get('first_name', ''),
            'last_name': customer_data.get('last_name', ''),
            'email': customer_data.get('email', ''),
            'phone': customer_data.get('phone', ''),
            'street_1': address.get('line1', ''),
            'city': address.get('city', ''),
            'state': address.get('state', ''),
            'zip': address.get('zip', ''),
            'country': address.get('country', 'United States'),
            'country_iso2': address.get('country', 'US'),
        }

        products_list = []
        for item in cart_items:
            products_list.append({
                'product_id': int(item['product_id']),
                'quantity': item.get('quantity', 1),
            })

        order_payload = {
            'customer_id': 0,  # Guest
            'status_id': 1,  # Pending
            'billing_address': billing_address,
            'shipping_addresses': [billing_address],
            'products': products_list,
            'customer_message': notes,
        }

        try:
            result = self._post('v2/orders', order_payload)
            if 'id' in result:
                return {
                    'success': True,
                    'order_id': str(result['id']),
                    'order_number': str(result.get('id', '')),
                    'total': str(result.get('total_inc_tax', '0')),
                    'currency': result.get('currency_code', 'USD'),
                    'status': result.get('status', 'Pending'),
                }
            return {'success': False, 'error': result.get('title', 'Unknown BigCommerce error')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
