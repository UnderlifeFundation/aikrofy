"""
Shopify Adapter — GraphQL Admin API integration.

Authentication: Static access token in X-Shopify-Access-Token header.
API surface:   GraphQL Admin API (products, inventory, orders).
Rate limiting:  Query-cost-based throttle bucket.
"""
import json
import requests
from typing import Dict, List, Any, Optional

from services.ecommerce.base import BaseEcommerceAdapter, EcommerceAPIError


class ShopifyAdapter(BaseEcommerceAdapter):

    def __init__(self, store_url: str, credentials: Dict[str, str]):
        super().__init__(store_url, credentials)
        self.access_token = credentials.get('access_token', '')
        # Normalise URL: https://mystore.myshopify.com
        if not self.store_url.startswith('http'):
            self.store_url = f"https://{self.store_url}"
        self.graphql_url = f"{self.store_url}/admin/api/2024-10/graphql.json"

    def _headers(self):
        return {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token,
        }

    def _gql(self, query: str, variables: dict = None) -> dict:
        """Execute a GraphQL query and return the data payload."""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        resp = self._safe_request('POST', self.graphql_url,
                                  headers=self._headers(),
                                  json=payload)
        body = resp.json()
        if 'errors' in body:
            raise EcommerceAPIError(f"Shopify GraphQL errors: {body['errors']}")
        return body.get('data', {})

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    def test_connection(self) -> Dict[str, Any]:
        try:
            data = self._gql('{ shop { name email myshopifyDomain } }')
            shop = data.get('shop', {})
            return {
                'success': True,
                'store_name': shop.get('name', ''),
                'store_domain': shop.get('myshopifyDomain', ''),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        gql = """
        query searchProducts($query: String!, $first: Int!) {
          products(first: $first, query: $query) {
            edges {
              node {
                id
                title
                onlineStoreUrl
                featuredImage { url }
                variants(first: 5) {
                  edges {
                    node {
                      id
                      title
                      price
                      inventoryQuantity
                    }
                  }
                }
                priceRangeV2 {
                  minVariantPrice { amount currencyCode }
                }
              }
            }
          }
        }
        """
        data = self._gql(gql, {'query': query, 'first': min(limit, 50)})
        products = []
        for edge in data.get('products', {}).get('edges', []):
            node = edge['node']
            variants = []
            total_stock = 0
            for v_edge in node.get('variants', {}).get('edges', []):
                v = v_edge['node']
                stock = v.get('inventoryQuantity', 0)
                total_stock += stock
                variants.append({
                    'id': v['id'],
                    'name': v.get('title', ''),
                    'price': v.get('price', '0'),
                    'stock': stock,
                })
            price_info = node.get('priceRangeV2', {}).get('minVariantPrice', {})
            products.append({
                'id': node['id'],
                'name': node['title'],
                'price': price_info.get('amount', variants[0]['price'] if variants else '0'),
                'currency': price_info.get('currencyCode', 'USD'),
                'stock': total_stock,
                'image_url': (node.get('featuredImage') or {}).get('url', ''),
                'url': node.get('onlineStoreUrl', ''),
                'variants': variants,
            })
        return products

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        gql = """
        query getProduct($id: ID!) {
          product(id: $id) {
            id title onlineStoreUrl description
            featuredImage { url }
            variants(first: 20) {
              edges {
                node { id title price inventoryQuantity }
              }
            }
            priceRangeV2 { minVariantPrice { amount currencyCode } }
          }
        }
        """
        data = self._gql(gql, {'id': product_id})
        node = data.get('product')
        if not node:
            return None
        variants = []
        total_stock = 0
        for v_edge in node.get('variants', {}).get('edges', []):
            v = v_edge['node']
            stock = v.get('inventoryQuantity', 0)
            total_stock += stock
            variants.append({'id': v['id'], 'name': v.get('title', ''), 'price': v.get('price', '0'), 'stock': stock})
        price_info = node.get('priceRangeV2', {}).get('minVariantPrice', {})
        return {
            'id': node['id'],
            'name': node['title'],
            'description': node.get('description', ''),
            'price': price_info.get('amount', '0'),
            'currency': price_info.get('currencyCode', 'USD'),
            'stock': total_stock,
            'image_url': (node.get('featuredImage') or {}).get('url', ''),
            'url': node.get('onlineStoreUrl', ''),
            'variants': variants,
        }

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
    # Orders
    # ------------------------------------------------------------------
    def create_order(self, customer_data: Dict[str, Any], cart_items: List[Dict[str, Any]], notes: str = "") -> Dict[str, Any]:
        """Create a draft order via the draftOrderCreate mutation using GraphQL variables (safe from injection)."""
        line_items = [
            {
                "variantId": item.get("variant_id") or item.get("product_id"),
                "quantity": int(item.get("quantity", 1)),
            }
            for item in cart_items
        ]

        address = customer_data.get("address", {})

        mutation = """
        mutation CreateDraftOrder($input: DraftOrderInput!) {
          draftOrderCreate(input: $input) {
            draftOrder {
              id
              name
              totalPriceSet { shopMoney { amount currencyCode } }
            }
            userErrors { field message }
          }
        }
        """

        variables = {
            "input": {
                "lineItems": line_items,
                "email": customer_data.get("email", ""),
                "note": notes,
                "shippingAddress": {
                    "firstName": customer_data.get("first_name", ""),
                    "lastName": customer_data.get("last_name", ""),
                    "address1": address.get("line1", ""),
                    "city": address.get("city", ""),
                    "provinceCode": address.get("state", ""),
                    "zip": address.get("zip", ""),
                    "countryCode": address.get("country", "US"),
                    "phone": customer_data.get("phone", ""),
                },
            }
        }

        try:
            data = self._gql(mutation, variables=variables)
            result = data.get("draftOrderCreate", {})
            errors = result.get("userErrors", [])
            if errors:
                return {"success": False, "error": "; ".join(e["message"] for e in errors)}
            order = result.get("draftOrder", {})
            total_info = order.get("totalPriceSet", {}).get("shopMoney", {})
            return {
                "success": True,
                "order_id": order.get("id", ""),
                "order_number": order.get("name", ""),
                "total": total_info.get("amount", "0"),
                "currency": total_info.get("currencyCode", "USD"),
                "status": "pending",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
