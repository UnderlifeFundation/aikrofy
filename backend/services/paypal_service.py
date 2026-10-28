import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class PayPalService:
    def __init__(self):
        self.client_id = os.environ.get('PAYPAL_CLIENT_ID') or os.environ.get('PAYPAL_ID')
        self.client_secret = os.environ.get('PAYPAL_CLIENT_SECRET') or os.environ.get('PAYPAL_SECRET')
        self.mode = os.environ.get('PAYPAL_MODE', 'sandbox') # 'sandbox' or 'live'
        
        if self.mode == 'live':
            self.base_url = "https://api-m.paypal.com"
        else:
            self.base_url = "https://api-m.sandbox.paypal.com"

    def get_access_token(self):
        """Get OAuth2 access token from PayPal."""
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                auth=(self.client_id, self.client_secret), 
                data=data
            )
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            logger.error(f"PayPal Auth Error: {e}")
            return None

    def get_subscription_details(self, subscription_id):
        """Fetch subscription details from PayPal."""
        token = self.get_access_token()
        if not token:
            return None
            
        url = f"{self.base_url}/v1/billing/subscriptions/{subscription_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"PayPal Get Subscription Error: {e}")
            return None

    def cancel_subscription(self, subscription_id, reason="User cancelled"):
        """Cancel a subscription in PayPal."""
        token = self.get_access_token()
        if not token:
            return False
            
        url = f"{self.base_url}/v1/billing/subscriptions/{subscription_id}/cancel"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {"reason": reason}
        
        try:
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 204
        except Exception as e:
            logger.error(f"PayPal Cancel Subscription Error: {e}")
            return False

    def create_order(self, amount, currency="USD", description="Credit Recharge"):
        """Create a PayPal order for one-time payment."""
        token = self.get_access_token()
        if not token:
            return None
            
        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency,
                    "value": str(amount)
                },
                "description": description
            }]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"PayPal Create Order Error: {e}")
            return None

    def capture_order(self, order_id):
        """Capture a previously created PayPal order."""
        token = self.get_access_token()
        if not token:
            return None
            
        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"PayPal Capture Order Error: {e}")
            return None

    def verify_webhook_signature(self, headers, body):
        """
        Verify the signature of a PayPal webhook using the PayPal REST API.
        See: https://developer.paypal.com/api/webhooks/v1/#verify-webhook-signature_post
        """
        webhook_id = os.environ.get('PAYPAL_WEBHOOK_ID', '')
        if not webhook_id:
            # In sandbox mode without a configured webhook ID, log a warning and
            # skip verification rather than silently accepting all requests.
            if self.mode == 'sandbox':
                logger.warning(
                    "PAYPAL_WEBHOOK_ID not configured — skipping signature verification in sandbox mode. "
                    "Set PAYPAL_WEBHOOK_ID in production for security."
                )
                return True
            # In live mode, deny unverifiable webhooks to prevent fraud.
            logger.error("PAYPAL_WEBHOOK_ID not set — rejecting webhook in live mode.")
            return False

        token = self.get_access_token()
        if not token:
            logger.error("Could not obtain PayPal access token for webhook verification.")
            return False

        url = f"{self.base_url}/v1/notifications/verify-webhook-signature"
        verification_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        # Ensure body is a string for the JSON payload
        raw_body = body if isinstance(body, str) else body.decode('utf-8')

        payload = {
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO") or headers.get("paypal-auth-algo", ""),
            "cert_url": headers.get("PAYPAL-CERT-URL") or headers.get("paypal-cert-url", ""),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID") or headers.get("paypal-transmission-id", ""),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG") or headers.get("paypal-transmission-sig", ""),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME") or headers.get("paypal-transmission-time", ""),
            "webhook_id": webhook_id,
            "webhook_event": raw_body,
        }
        try:
            response = requests.post(url, headers=verification_headers, json=payload, timeout=10)
            response.raise_for_status()
            verification_status = response.json().get("verification_status", "FAILURE")
            if verification_status != "SUCCESS":
                logger.warning(f"PayPal webhook verification failed: status={verification_status}")
                return False
            return True
        except Exception as e:
            logger.error(f"PayPal webhook signature verification error: {e}")
            return False
