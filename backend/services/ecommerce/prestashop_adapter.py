"""
PrestaShop Adapter — Webservice CRUD integration.

Authentication: API Key via Basic Auth (key as username, no password).
API surface:   REST-like CRUD at /api/ with XML or JSON (?output_format=JSON).
Key concept:   stock_availables for inventory, strict entity dependency
               chain for order creation.
"""
import requests
from typing import Dict, List, Any, Optional
from requests.auth import HTTPBasicAuth

from services.ecommerce.base import BaseEcommerceAdapter, EcommerceAPIError


class PrestaShopAdapter(BaseEcommerceAdapter):

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        super().__init__(store_url, credentials)
        self.api_key = credentials.get('api_key', '')
        if not self.store_url.startswith('http'):
            self.store_url = f"https://{self.store_url}"
        self.base_api = f"{self.store_url}/api"

    def _auth(self):
        return HTTPBasicAuth(self.api_key, '')

    def _get(self, resource: str, params: dict = None) -> Any:
        default_params = {'output_format': 'JSON'}
        if params:
            default_params.update(params)
        url = f"{self.base_api}/{resource}"
        resp = self._safe_request('GET', url, auth=self._auth(), params=default_params)
        return resp.json()

    def _post(self, resource: str, data: dict) -> Any:
        url = f"{self.base_api}/{resource}"
        resp = self._safe_request('POST', url, auth=self._auth(), json=data,
                                  params={'output_format': 'JSON'})
        return resp.json()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        try:
            data = self._get('', params={'output_format': 'JSON'})
            # Root endpoint returns list of available resources
            return {
                'success': True,
                'store_name': self.store_url.split('//')[1].split('/')[0] if '//' in self.store_url else self.store_url,
            }
        except EcommerceAPIError as e:
            if e.status_code == 401:
                return {'success': False, 'error': 'Invalid API key'}
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            params = {
                'filter[name]': f'[{query}]%',
                'display': 'full',
                'limit': str(min(limit, 50)),
            }
            data = self._get('products', params=params)
        except Exception:
            # Fallback: get all and filter
            try:
                data = self._get('products', params={'display': 'full', 'limit': str(min(limit, 50))})
            except Exception:
                return []

        products = []
        items = data.get('products', [])
        if isinstance(items, dict):
            items = [items]

        for p in items:
            # Get first image if available
            image_url = ''
            if p.get('id_default_image'):
                image_url = f"{self.store_url}/api/images/products/{p['id']}/{p['id_default_image']}"

            price = str(p.get('price', '0'))
            name = ''
            # PrestaShop returns name as array of language entries
            name_data = p.get('name', '')
            if isinstance(name_data, list):
                name = name_data[0].get('value', '') if name_data else ''
            elif isinstance(name_data, dict):
                name = name_data.get('value', str(name_data))
            else:
                name = str(name_data)

            products.append({
                'id': str(p.get('id', '')),
                'name': name,
                'price': price,
                'currency': '',
                'stock': p.get('quantity', 0),
                'image_url': image_url,
                'url': '',
                'variants': [],
            })
        return products

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = self._get(f'products/{product_id}', params={'display': 'full'})
            p = data.get('product', data)
            name_data = p.get('name', '')
            if isinstance(name_data, list):
                name = name_data[0].get('value', '') if name_data else ''
            elif isinstance(name_data, dict):
                name = name_data.get('value', str(name_data))
            else:
                name = str(name_data)

            desc_data = p.get('description', '')
            if isinstance(desc_data, list):
                description = desc_data[0].get('value', '') if desc_data else ''
            elif isinstance(desc_data, dict):
                description = desc_data.get('value', str(desc_data))
            else:
                description = str(desc_data)

            return {
                'id': str(p.get('id', '')),
                'name': name,
                'description': description,
                'price': str(p.get('price', '0')),
                'currency': '',
                'stock': p.get('quantity', 0),
                'image_url': '',
                'url': '',
                'variants': [],
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Inventory (via stock_availables)
    # ------------------------------------------------------------------
    def get_inventory(self, product_id: str) -> Dict[str, Any]:
        try:
            data = self._get('stock_availables', params={
                'filter[id_product]': product_id,
                'display': 'full',
            })
            stocks = data.get('stock_availables', [])
            if isinstance(stocks, dict):
                stocks = [stocks]
            total = sum(int(s.get('quantity', 0)) for s in stocks)
            return {
                'product_id': product_id,
                'total_stock': total,
                'variants': [{'id': str(s.get('id', '')), 'name': '', 'stock': int(s.get('quantity', 0))} for s in stocks],
            }
        except Exception:
            return {'product_id': product_id, 'total_stock': 0, 'variants': []}

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    def create_order(self, customer_data: Dict[str, Any], cart_items: List[Dict[str, Any]], notes: str = "") -> Dict[str, Any]:
        """
        PrestaShop requires a complex dependency chain:
        - id_customer, id_cart, id_address_delivery, id_address_invoice,
          id_currency, id_lang, module, payment, total_paid, etc.

        For conversational commerce, we create a simplified order
        that the store admin can then process.
        """
        try:
            # Build minimal order payload
            # Note: In production, you'd need to create cart, customer, and
            # address entities first. This is a simplified version.
            associations = {
                'order_rows': {
                    'order_row': [
                        {
                            'product_id': str(item.get('product_id', '')),
                            'product_quantity': str(item.get('quantity', 1)),
                        }
                        for item in cart_items
                    ]
                }
            }

            order_data = {
                'order': {
                    'id_customer': '0',  # Guest
                    'id_address_delivery': '0',
                    'id_address_invoice': '0',
                    'id_cart': '0',
                    'id_currency': '1',
                    'id_lang': '1',
                    'module': 'ps_chatcommerce',
                    'payment': 'Conversational AI Order',
                    'total_paid': '0',
                    'total_paid_real': '0',
                    'total_products': '0',
                    'total_products_wt': '0',
                    'conversion_rate': '1',
                    'associations': associations,
                }
            }

            result = self._post('orders', order_data)
            order = result.get('order', result)

            return {
                'success': True,
                'order_id': str(order.get('id', '')),
                'order_number': str(order.get('reference', order.get('id', ''))),
                'total': str(order.get('total_paid', '0')),
                'currency': '',
                'status': 'pending',
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
