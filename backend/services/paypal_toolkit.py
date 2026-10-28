"""
PayPal Toolkit Service - Agentic Payments
Uses paypalrestsdk for in-conversation payment processing via Orders API v2.
"""
import os
import requests
from typing import Dict, Any
from base64 import b64encode


class PayPalToolkitService:
    """
    PayPal Toolkit Integration for Agentic Payments.
    Uses PayPal Orders API v2 directly via REST.
    
    Architecture: Multi-tenant (Company credentials > Platform credentials)
    """
    
    def __init__(self, company=None):
        # Cache company info immediately to avoid session detachment issues
        self._company_name = company.name if company else "PymAI"
        self._company_id = company.id if company else 1
        self._company_api_keys = dict(company.api_keys) if company and company.api_keys else {}
        self._gateway_credentials = {}
        
        # Load from unified PaymentGatewayConfig if present
        if company:
            try:
                from models.payment_gateway import PaymentGatewayConfig, GatewayProvider
                config = PaymentGatewayConfig.query.filter_by(
                    company_id=company.id,
                    gateway_provider=GatewayProvider.PAYPAL
                ).first()
                if config and config.credentials:
                    self._gateway_credentials = dict(config.credentials)
            except Exception as e:
                print(f"Error loading unified PayPal credentials: {e}")
        
        self._access_token = None
        self._initialized = False
        self._base_url = None
        
        try:
            self._initialize()
        except Exception as e:
            print(f"PayPal Toolkit initialization failed: {e}")


    
    def _get_credential(self, key: str) -> str:
        """Resolve credential: Unified Config > Company Keys > Env"""
        # 1. Check cached unified PaymentGatewayConfig Credentials
        if self._gateway_credentials:
            unified_map = {
                'paypal_client_id': 'client_id',
                'paypal_client_secret': 'client_secret',
                'paypal_mode': 'mode'
            }
            mapped_key = unified_map.get(key)
            if mapped_key and self._gateway_credentials.get(mapped_key):
                return self._gateway_credentials.get(mapped_key)

        # 2. Check cached Company Keys (support both naming conventions)
        if self._company_api_keys:
            value = self._company_api_keys.get(key)
            if value:
                return value
            
            # Check alternate key names (paypal_id vs paypal_client_id)
            alt_keys = {
                'paypal_client_id': 'paypal_id',
                'paypal_client_secret': 'paypal_secret',
                'paypal_id': 'paypal_client_id',
                'paypal_secret': 'paypal_client_secret'
            }
            if key in alt_keys:
                value = self._company_api_keys.get(alt_keys[key])
                if value:
                    return value
        
        # 3. Check Environment Variables
        env_map = {
            'paypal_client_id': 'PAYPAL_CLIENT_ID',
            'paypal_client_secret': 'PAYPAL_CLIENT_SECRET',
            'paypal_mode': 'PAYPAL_MODE'
        }
        return os.getenv(env_map.get(key, ''), '')
    
    def _initialize(self):
        """Initialize PayPal API - Get access token"""
        client_id = self._get_credential('paypal_client_id')
        client_secret = self._get_credential('paypal_client_secret')
        mode = self._get_credential('paypal_mode') or 'sandbox'
        
        if not client_id or not client_secret:
            print("PayPal credentials not configured. Toolkit disabled.")
            return
        
        # Set base URL based on mode
        if mode.lower() == 'live':
            self._base_url = "https://api-m.paypal.com"
        else:
            self._base_url = "https://api-m.sandbox.paypal.com"
        
        # Get OAuth token
        try:
            auth = b64encode(f"{client_id}:{client_secret}".encode()).decode()
            
            response = requests.post(
                f"{self._base_url}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data="grant_type=client_credentials"
            )
            
            if response.status_code == 200:
                self._access_token = response.json().get('access_token')
                self._initialized = True
                print(f"PayPal Toolkit initialized (mode: {mode})")
            else:
                print(f"PayPal auth failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"PayPal initialization error: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if toolkit is ready"""
        return self._initialized and self._access_token is not None
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated request to PayPal API"""
        if not self.is_available:
            return {'error': 'Not initialized'}
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self._base_url}{endpoint}"
        
        if method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'GET':
            response = requests.get(url, headers=headers)
        else:
            return {'error': f'Unsupported method: {method}'}
        
        return response.json() if response.content else {}
    
    def create_order(self, amount: float, currency: str = "USD", description: str = "Payment") -> Dict[str, Any]:
        """
        Create a PayPal order for in-conversation payment.
        Uses Orders API v2: https://developer.paypal.com/docs/api/orders/v2/
        """
        if not self.is_available:
            return {'success': False, 'error': 'Toolkit not configured', 'fallback': True}
        
        try:
            order_data = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}"
                    },
                    "description": description[:127] if description else "Payment"
                }],
                "application_context": {
                    "brand_name": self._company_name,
                    "landing_page": "BILLING",  # Opens directly to Credit/Debit Card guest form
                    "user_action": "PAY_NOW",
                    "shipping_preference": "NO_SHIPPING",
                    "return_url": f"{os.getenv('API_BASE_URL', 'http://localhost:5001')}/api/payments/success?cid={self._company_id}",
                    "cancel_url": f"{os.getenv('API_BASE_URL', 'http://localhost:5001')}/api/payments/cancel"
                }
            }
            
            result = self._make_request('POST', '/v2/checkout/orders', order_data)
            
            if result and result.get('id'):
                # Extract approval link
                approval_url = None
                for link in result.get('links', []):
                    if link.get('rel') == 'approve':
                        approval_url = link.get('href')
                        break
                
                return {
                    'success': True,
                    'order_id': result['id'],
                    'status': result.get('status', 'CREATED'),
                    'approval_url': approval_url,
                    'amount': amount,
                    'currency': currency,
                    'description': description
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Failed to create order'),
                    'details': result
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order details"""
        if not self.is_available:
            return {'success': False, 'error': 'Toolkit not configured'}
        
        try:
            result = self._make_request('GET', f'/v2/checkout/orders/{order_id}')
            
            if result and 'id' in result:
                return {
                    'success': True,
                    'order_id': result.get('id'),
                    'status': result.get('status'),
                    'amount': result.get('purchase_units', [{}])[0].get('amount', {}),
                    'payer': result.get('payer', {}),
                    'create_time': result.get('create_time')
                }
            else:
                return {'success': False, 'error': 'Order not found', 'details': result}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def capture_order(self, order_id: str) -> Dict[str, Any]:
        """Capture payment for an approved order"""
        if not self.is_available:
            return {'success': False, 'error': 'Toolkit not configured'}
        
        try:
            result = self._make_request('POST', f'/v2/checkout/orders/{order_id}/capture', {})
            
            if result and result.get('status') == 'COMPLETED':
                capture = result.get('purchase_units', [{}])[0].get('payments', {}).get('captures', [{}])[0]
                return {
                    'success': True,
                    'order_id': result.get('id'),
                    'status': 'COMPLETED',
                    'capture_id': capture.get('id'),
                    'amount': capture.get('amount', {}),
                    'payer_email': result.get('payer', {}).get('email_address'),
                    'message': 'Payment completed successfully!'
                }
            else:
                return {
                    'success': False,
                    'error': 'Capture failed', 
                    'status': result.get('status') if result else 'unknown',
                    'details': result
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Singleton-like factory for reuse
_toolkit_instances: Dict[int, PayPalToolkitService] = {}

def get_paypal_toolkit(company=None) -> PayPalToolkitService:
    """Get or create PayPal Toolkit instance for a company"""
    company_id = company.id if company else 0
    
    if company_id not in _toolkit_instances:
        _toolkit_instances[company_id] = PayPalToolkitService(company)
    
    return _toolkit_instances[company_id]
