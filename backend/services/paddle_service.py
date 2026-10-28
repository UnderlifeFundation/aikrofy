"""
Paddle Billing Integration Service
Handles Subscriptions and Checkout generation for Paddle.
"""
import os
import logging

logger = logging.getLogger(__name__)

import hmac
import hashlib

class PaddleService:
    def __init__(self):
        self.env = os.environ.get('PADDLE_ENVIRONMENT', 'sandbox').lower()
        self.api_key = os.environ.get('PADDLE_API_KEY')
        self.webhook_secret = os.environ.get('PADDLE_WEBHOOK_SECRET')
        
        if self.env == 'production':
            self.checkout_base_url = "https://checkout.paddle.com/checkout/buy"
            self.api_base_url = "https://api.paddle.com"
        else:
            self.checkout_base_url = "https://sandbox-checkout.paddle.com/checkout/buy"
            self.api_base_url = "https://sandbox-api.paddle.com"

    def verify_signature(self, raw_body_bytes: bytes, signature_header: str) -> bool:
        """
        Verify the Paddle-Signature header to authenticate the webhook sender.
        Allows signature bypass in sandbox environment only if webhook secret is not set.
        """
        if not self.webhook_secret or "your_" in self.webhook_secret or self.webhook_secret == "placeholder":
            logger.warning("PADDLE_WEBHOOK_SECRET is not configured or is a placeholder.")
            if self.env == 'sandbox':
                logger.info("Signature verification bypassed in sandbox environment.")
                return True
            return False

        if not signature_header:
            return False

        try:
            # Paddle-Signature format: ts=1692609120;h1=abcd...
            parts = dict(item.split('=') for item in signature_header.split(';'))
            timestamp = parts.get('ts')
            signature = parts.get('h1')
            
            if not timestamp or not signature:
                return False

            # Signed payload: timestamp + ":" + raw_body
            signed_payload = timestamp.encode('utf-8') + b":" + raw_body_bytes

            computed_hmac = hmac.new(
                self.webhook_secret.encode('utf-8'),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(computed_hmac, signature)
        except Exception as e:
            logger.error(f"Error verifying Paddle signature: {e}")
            return False

    def get_checkout_url(self, plan_token: str, company_id: int, email: str = None) -> str:
        """
        Generates the Paddle checkout link for a subscription.
        plan_token represents the Paddle Price ID (e.g. pri_01h...).
        If it's still using a legacy dLocal token, we use a default sandbox fallback.
        """
        price_id = plan_token
        # If the token is a legacy dLocal token (doesn't start with pri_), we use fallback sandbox IDs
        if not price_id or not price_id.startswith('pri_'):
            # Sandbox default price IDs for Jab, Uppercut, Knockout
            defaults = {
                'Jab': 'pri_01j00000000000000000000001',
                'Uppercut': 'pri_01j00000000000000000000002',
                'Knockout': 'pri_01j00000000000000000000003'
            }
            # Or map via plan name / legacy tokens
            if plan_token == 'MMz3OdBYKzxueoACPAbgtblUc7COuTI1':
                price_id = 'pri_01j00000000000000000000001' # Jab
            elif plan_token == 'zeNOrJ89cGpeEkoQfywg4U0WoIb37UjU':
                price_id = 'pri_01j00000000000000000000002' # Uppercut
            elif plan_token == 'k4ybKppmVij1Ph7OhfCL7wZYFt6ZtYuy':
                price_id = 'pri_01j00000000000000000000003' # Knockout
            else:
                price_id = defaults.get(plan_token, 'pri_01j00000000000000000000001')
        
        url = f"{self.checkout_base_url}/{price_id}?passthrough={company_id}"
        if email:
            url += f"&customer_email={email}"
        return url

    def create_one_time_payment(self, amount: float, company_id: int, currency: str = "USD", email: str = None) -> dict:
        """
        Creates a one-time payment link via Paddle for credit top-ups.
        Maps amount to sandbox/configured Price IDs.
        """
        defaults = {
            5: 'pri_topup_5usd',
            10: 'pri_topup_10usd',
            20: 'pri_topup_20usd'
        }
        price_id = defaults.get(int(amount), 'pri_topup_5usd')
        
        checkout_url = f"{self.checkout_base_url}/{price_id}?passthrough=topup_{company_id}"
        if email:
            checkout_url += f"&customer_email={email}"
            
        credits_to_grant = {5: 50, 10: 100, 20: 250}.get(int(amount), 50)
        
        return {
            'checkout_url': checkout_url,
            'payment_id': f"pad_{company_id}_{int(amount)}",
            'credits': credits_to_grant,
            'amount': amount,
            'currency': currency
        }
