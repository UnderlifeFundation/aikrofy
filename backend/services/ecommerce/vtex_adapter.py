"""
VTEX Adapter — Microservices Checkout API integration.

Authentication: AppKey + AppToken headers.
API surface:   REST (Catalog, Checkout orderForm, Search).
Key concept:   Iterative orderForm manipulation (stateful checkout).
"""
import requests
from typing import Dict, List, Any, Optional

from services.ecommerce.base import BaseEcommerceAdapter, EcommerceAPIError


class VTEXAdapter(BaseEcommerceAdapter):

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        super().__init__(store_url, credentials)
        self.app_key = credentials.get('app_key', '')
        self.app_token = credentials.get('app_token', '')
        # VTEX URLs: https://{accountName}.vtexcommercestable.com.br
        if not self.store_url.startswith('http'):
            self.store_url = f"https://{self.store_url}"

    def _headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-VTEX-API-AppKey': self.app_key,
            'X-VTEX-API-AppToken': self.app_token,
        }

    def _get(self, path: str, params: dict = None) -> Any:
        url = f"{self.store_url}{path}"
        if params:
            import urllib.parse
            query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            url = f"{url}?{query_string}"
            resp = self._safe_request('GET', url, headers=self._headers())
        else:
            resp = self._safe_request('GET', url, headers=self._headers())
        return resp.json()

    def _post(self, path: str, data: dict = None) -> Any:
        url = f"{self.store_url}{path}"
        resp = self._safe_request('POST', url, headers=self._headers(), json=data or {})
        return resp.json()

    def _patch(self, path: str, data: dict = None) -> Any:
        url = f"{self.store_url}{path}"
        resp = self._safe_request('PATCH', url, headers=self._headers(), json=data or {})
        return resp.json()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        try:
            # Lightweight: fetch first product from Search API
            data = self._get('/api/catalog_system/pub/products/search', params={'_from': 0, '_to': 0})
            return {
                'success': True,
                'store_name': self.store_url.split('//')[1].split('.')[0] if '//' in self.store_url else self.store_url,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Products (using VTEX Search API)
    # ------------------------------------------------------------------
    def _format_products(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        products = []
        for p in data:
            skus = p.get('items', [])
            variants = []
            total_stock = 0
            for sku in skus:
                sellers = sku.get('sellers', [])
                stock = 0
                price = '0'
                for seller in sellers:
                    offer = seller.get('commertialOffer', {})
                    stock += offer.get('AvailableQuantity', 0)
                    price = str(offer.get('Price', 0))
                total_stock += stock
                variants.append({
                    'id': str(sku.get('itemId', '')),
                    'name': sku.get('name', ''),
                    'price': price,
                    'stock': stock,
                })
            images = p.get('items', [{}])[0].get('images', [])
            products.append({
                'id': str(p.get('productId', '')),
                'name': p.get('productName', ''),
                'price': variants[0]['price'] if variants else '0',
                'currency': 'BRL',
                'stock': total_stock,
                'image_url': images[0].get('imageUrl', '') if images else '',
                'url': p.get('link', ''),
                'variants': variants,
            })
        return products

    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        def _do_search(q):
            try:
                res = self._get('/api/catalog_system/pub/products/search',
                                 params={'ft': q, '_from': 0, '_to': min(limit - 1, 49)})
                return res if isinstance(res, list) else []
            except Exception:
                return []

        # 1. Try original query
        data = _do_search(query)
        if data:
            return self._format_products(data)

        # 2. Try simple singular fallback for Spanish (e.g. try both ending in -s and -es)
        words = query.strip().split()
        modified = False
        new_words_s = []  # Try stripping 's' (e.g. leches -> leche)
        new_words_es = [] # Try stripping 'es' (e.g. panales -> panal)
        for w in words:
            if len(w) > 3 and w.lower().endswith('s'):
                new_words_s.append(w[:-1])
                if w.lower().endswith('es') and len(w) > 4:
                    new_words_es.append(w[:-2])
                else:
                    new_words_es.append(w[:-1])
                modified = True
            else:
                new_words_s.append(w)
                new_words_es.append(w)
        
        if modified:
            singular_query_s = " ".join(new_words_s)
            print(f"[VTEX Search] Fallback to singular (-s): '{singular_query_s}'")
            data = _do_search(singular_query_s)
            if data:
                return self._format_products(data)

            singular_query_es = " ".join(new_words_es)
            if singular_query_es != singular_query_s:
                print(f"[VTEX Search] Fallback to singular (-es): '{singular_query_es}'")
                data = _do_search(singular_query_es)
                if data:
                    return self._format_products(data)

        # 3. Try fallback for individual keywords if multiple words
        if len(words) > 1:
            filtered_words = [w for w in words if len(w) > 2]
            if not filtered_words:
                filtered_words = words
            filtered_words.sort(key=len, reverse=True)
            for w in filtered_words:
                print(f"[VTEX Search] Fallback to keyword: '{w}'")
                data = _do_search(w)
                if data:
                    return self._format_products(data)

        return []

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = self._get(f'/api/catalog_system/pub/products/search',
                             params={'fq': f'productId:{product_id}'})
            if not data:
                return None
            p = data[0]
            skus = p.get('items', [])
            variants = []
            total_stock = 0
            for sku in skus:
                sellers = sku.get('sellers', [])
                stock = 0
                price = '0'
                for seller in sellers:
                    offer = seller.get('commertialOffer', {})
                    stock += offer.get('AvailableQuantity', 0)
                    price = str(offer.get('Price', 0))
                total_stock += stock
                variants.append({'id': str(sku.get('itemId', '')), 'name': sku.get('name', ''), 'price': price, 'stock': stock})
            return {
                'id': str(p.get('productId', '')),
                'name': p.get('productName', ''),
                'description': p.get('description', ''),
                'price': variants[0]['price'] if variants else '0',
                'currency': 'BRL',
                'stock': total_stock,
                'image_url': '',
                'url': p.get('link', ''),
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
    # Orders (via Checkout API — iterative orderForm)
    # ------------------------------------------------------------------
    def create_order(self, customer_data: Dict[str, Any], cart_items: List[Dict[str, Any]], notes: str = "") -> Dict[str, Any]:
        """
        VTEX order creation is iterative:
        1. Create orderForm (cart)
        2. Add items
        3. Add client profile
        4. Add shipping data
        5. Place order
        """
        try:
            # Step 1: Create new cart (orderForm)
            order_form = self._post('/api/checkout/pub/orderForm')
            of_id = order_form.get('orderFormId', '')
            if not of_id:
                return {'success': False, 'error': 'Failed to create VTEX orderForm'}

            # Step 2: Add items
            items_payload = {
                'orderItems': [
                    {
                        'id': str(item.get('variant_id') or item.get('product_id')),
                        'quantity': item.get('quantity', 1),
                        'seller': '1',
                    }
                    for item in cart_items
                ]
            }
            self._post(f'/api/checkout/pub/orderForm/{of_id}/items', items_payload)

            # Step 3: Client profile
            address = customer_data.get('address', {})
            client_profile = {
                'email': customer_data.get('email', ''),
                'firstName': customer_data.get('first_name', ''),
                'lastName': customer_data.get('last_name', ''),
                'phone': customer_data.get('phone', ''),
                'document': customer_data.get('document', ''),
                'documentType': 'cpf',
            }
            self._patch(f'/api/checkout/pub/orderForm/{of_id}/attachments/clientProfileData',
                         client_profile)

            # Step 4: Shipping data
            shipping_data = {
                'address': {
                    'addressType': 'residential',
                    'receiverName': f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}",
                    'street': address.get('line1', ''),
                    'city': address.get('city', ''),
                    'state': address.get('state', ''),
                    'postalCode': address.get('zip', ''),
                    'country': address.get('country', 'BRA'),
                }
            }
            self._post(f'/api/checkout/pub/orderForm/{of_id}/attachments/shippingData',
                        shipping_data)

            # Step 5: Place order
            result = self._post(f'/api/checkout/pub/orderForm/{of_id}/transaction', {
                'referenceId': of_id,
                'savePersonalData': False,
                'optinNewsLetter': False,
                'value': 0,  # VTEX calculates from orderForm
                'referenceValue': 0,
                'interestValue': 0,
            })

            orders = result.get('orders', [])
            if orders:
                order = orders[0]
                return {
                    'success': True,
                    'order_id': order.get('orderId', ''),
                    'order_number': order.get('orderId', ''),
                    'total': str(order.get('value', 0) / 100),  # VTEX stores cents
                    'currency': 'BRL',
                    'status': 'pending',
                }
            return {'success': False, 'error': 'No orders returned from VTEX placement'}

        except Exception as e:
            return {'success': False, 'error': str(e)}
