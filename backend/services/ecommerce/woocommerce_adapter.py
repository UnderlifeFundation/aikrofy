"""
WooCommerce Adapter — REST API v3 integration.

Authentication: Basic Auth (Consumer Key / Consumer Secret).
API surface:   REST v3 (/wp-json/wc/v3/).
Rate limiting:  WordPress server-dependent.
Monetary types: All amounts are strings with 2 decimal places.
"""
import requests
from typing import Dict, List, Any, Optional
from requests.auth import HTTPBasicAuth

from services.ecommerce.base import BaseEcommerceAdapter, EcommerceAPIError


class WooCommerceAdapter(BaseEcommerceAdapter):

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        super().__init__(store_url, credentials)
        self.consumer_key = credentials.get('consumer_key', '')
        self.consumer_secret = credentials.get('consumer_secret', '')
        if not self.store_url.startswith('http'):
            self.store_url = f"https://{self.store_url}"
        self.base_api = f"{self.store_url}/wp-json/wc/v3"

    def _auth(self):
        return HTTPBasicAuth(self.consumer_key, self.consumer_secret)

    def _get(self, endpoint: str, params: dict = None) -> Any:
        url = f"{self.base_api}/{endpoint}"
        resp = self._safe_request('GET', url, auth=self._auth(), params=params)
        return resp.json()

    def _post(self, endpoint: str, data: dict) -> Any:
        url = f"{self.base_api}/{endpoint}"
        resp = self._safe_request('POST', url, auth=self._auth(), json=data)
        return resp.json()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        try:
            # System status endpoint is lightweight
            data = self._get('system_status')
            env = data.get('environment', {})
            return {
                'success': True,
                'store_name': env.get('site_title', env.get('home_url', self.store_url)),
            }
        except EcommerceAPIError as e:
            # Fallback: try fetching one product
            if e.status_code == 401:
                return {'success': False, 'error': 'Invalid credentials (Consumer Key/Secret)'}
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        raw = self._get('products', params={'search': query, 'per_page': min(limit, 100), 'status': 'publish'})
        products = []
        for p in raw:
            variants = []
            for v in p.get('variations_data', []):
                variants.append({
                    'id': str(v.get('id', '')),
                    'name': v.get('attributes', [{}])[0].get('option', '') if v.get('attributes') else '',
                    'price': v.get('price', '0'),
                    'stock': v.get('stock_quantity', 0),
                })
            products.append({
                'id': str(p['id']),
                'name': p.get('name', ''),
                'price': p.get('price', '0'),
                'currency': '',  # WooCommerce returns currency in settings, not per product
                'stock': p.get('stock_quantity', 0) if p.get('manage_stock') else -1,
                'image_url': (p.get('images', [{}])[0].get('src', '') if p.get('images') else ''),
                'url': p.get('permalink', ''),
                'variants': variants,
                'on_sale': p.get('on_sale', False),
                'sale_price': p.get('sale_price', ''),
                'regular_price': p.get('regular_price', ''),
                'short_description': p.get('short_description', ''),
            })
        return products

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        try:
            p = self._get(f'products/{product_id}')
            return {
                'id': str(p['id']),
                'name': p.get('name', ''),
                'description': p.get('description', ''),
                'price': p.get('price', '0'),
                'currency': '',
                'stock': p.get('stock_quantity', 0) if p.get('manage_stock') else -1,
                'image_url': (p.get('images', [{}])[0].get('src', '') if p.get('images') else ''),
                'url': p.get('permalink', ''),
                'variants': [],
                'on_sale': p.get('on_sale', False),
                'sale_price': p.get('sale_price', ''),
                'regular_price': p.get('regular_price', ''),
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------
    def get_inventory(self, product_id: str) -> Dict[str, Any]:
        try:
            p = self._get(f'products/{product_id}')
            variants = []
            # Fetch variations if product type is variable
            if p.get('type') == 'variable':
                var_data = self._get(f'products/{product_id}/variations', params={'per_page': 50})
                for v in var_data:
                    variants.append({
                        'id': str(v['id']),
                        'name': ', '.join(a.get('option', '') for a in v.get('attributes', [])),
                        'stock': v.get('stock_quantity', 0),
                    })
            total = sum(v['stock'] for v in variants) if variants else (p.get('stock_quantity') or 0)
            return {'product_id': product_id, 'total_stock': total, 'variants': variants}
        except Exception:
            return {'product_id': product_id, 'total_stock': 0, 'variants': []}

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def create_order(self, customer_data: Dict[str, Any], cart_items: List[Dict[str, Any]], notes: str = "") -> Dict[str, Any]:
        address = customer_data.get('address', {})
        billing = {
            'first_name': customer_data.get('first_name', ''),
            'last_name': customer_data.get('last_name', ''),
            'email': customer_data.get('email', ''),
            'phone': customer_data.get('phone', ''),
            'address_1': address.get('line1', ''),
            'city': address.get('city', ''),
            'state': address.get('state', ''),
            'postcode': address.get('zip', ''),
            'country': address.get('country', ''),
        }

        line_items = []
        for item in cart_items:
            li = {'product_id': int(item['product_id']), 'quantity': item.get('quantity', 1)}
            if item.get('variant_id'):
                li['variation_id'] = int(item['variant_id'])
            line_items.append(li)

        payload = {
            'payment_method': 'manual',
            'payment_method_title': 'Conversational AI Order',
            'set_paid': False,
            'billing': billing,
            'shipping': billing,  # Same as billing by default
            'line_items': line_items,
            'customer_note': notes,
        }

        try:
            result = self._post('orders', payload)
            if 'id' in result:
                return {
                    'success': True,
                    'order_id': str(result['id']),
                    'order_number': str(result.get('number', result['id'])),
                    'total': result.get('total', '0'),
                    'currency': result.get('currency', 'USD'),
                    'status': result.get('status', 'pending'),
                    'checkout_url': result.get('payment_url', ''),
                }
            else:
                return {'success': False, 'error': result.get('message', 'Unknown error from WooCommerce')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
