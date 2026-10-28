"""
dLocal Go Integration Service
Handles Subscriptions API integration for Latam recurring billing.
"""
import os
import requests
import logging

logger = logging.getLogger(__name__)

class DLocalGoService:
    def __init__(self):
        self.api_key = os.environ.get('DLOCAL_API_KEY')
        self.api_secret = os.environ.get('DLOCAL_API_SECRET')
        
        # Determine environment
        self.env = os.environ.get('DLOCAL_ENVIRONMENT', 'sandbox').lower()
        if self.env == 'production':
            self.base_api_url = "https://api.dlocalgo.com/v1"
            self.checkout_base_url = "https://checkout.dlocalgo.com/validate/subscription"
        else:
            self.base_api_url = "https://api-sbx.dlocalgo.com/v1"
            self.checkout_base_url = "https://checkout-sbx.dlocalgo.com/validate/subscription"

    def _get_headers(self):
        """Construct authentication headers for dLocal Go API."""
        if not self.api_key or not self.api_secret:
            logger.warning("DLOCAL_API_KEY or DLOCAL_API_SECRET is not set")
            
        return {
            "Authorization": f"Bearer {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }

    def create_plan(self, name: str, description: str, amount: float, currency: str = "USD", frequency_type: str = "MONTHLY", frequency_value: int = 1):
        """
        Creates a new Subscription Plan in dLocal Go.
        Returns the plan details including 'plan_token' and 'id'.
        """
        url = f"{self.base_api_url}/subscription/plan"
        
        # We need a proper notification callback so our webhook /webhooks/dlocal works
        # If testing locally, DLOCAL_WEBHOOK_URL should be an ngrok tunnel.
        backend_url = os.environ.get('DLOCAL_WEBHOOK_URL', os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:5000'))
        notification_url = f"{backend_url}/api/webhooks/dlocal"
        
        frontend_url = os.environ.get('NEXT_PUBLIC_APP_URL', 'http://localhost:3000')
        success_url = f"{frontend_url}/dashboard"
        back_url = f"{frontend_url}/subscribe"
        error_url = f"{frontend_url}/subscribe"
        
        payload = {
            "name": name,
            "description": description,
            "amount": amount,
            "currency": currency,
            "frequency_type": frequency_type,
            "frequency_value": frequency_value,
            "notification_url": notification_url,
            "success_url": success_url,
            "back_url": back_url,
            "error_url": error_url
        }
        
        try:
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"dLocal Go create_plan failed: {e.response.text}")
            raise Exception(f"Failed to create dLocal plan: {e.response.text}")
        except Exception as e:
            logger.error(f"dLocal Go create_plan error: {str(e)}")
            raise

    def update_plan(self, plan_id: str, name: str = None, description: str = None, amount: float = None):
        """
        Updates an existing Subscription Plan in dLocal Go.
        Allows updating name, description, and amount.
        """
        url = f"{self.base_api_url}/subscription/plan/{plan_id}"
        
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if amount is not None:
            payload["amount"] = amount
            
        if not payload:
            return None # Nothing to update
            
        try:
            response = requests.patch(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"dLocal Go update_plan failed: {e.response.text}")
            raise Exception(f"Failed to update dLocal plan: {e.response.text}")
        except Exception as e:
            logger.error(f"dLocal Go update_plan error: {str(e)}")
            raise

    def get_checkout_url(self, plan_token: str, company_id: int, email: str = None) -> str:
        """
        Generates the payment link for a specific company.
        Uses external_id to map the payment back to our user when the webhook fires.
        """
        # Base url: https://checkout-sbx.dlocalgo.com/validate/subscription/{plan_token}
        url = f"{self.checkout_base_url}/{plan_token}?external_id={company_id}"
        if email:
            url += f"&email={email}"
        return url

    # =============================================
    # Credit Top-Up: One-Time Payment
    # =============================================

    # Credit conversion rates: USD amount -> credits granted
    CREDIT_PACKAGES = {
        5:   50,    # $5  -> 50 credits  (10 conversations)
        10:  100,   # $10 -> 100 credits (20 conversations)
        20:  250,   # $20 -> 250 credits (50 conversations, bonus included)
    }

    def create_one_time_payment(self, amount: float, company_id: int, currency: str = "USD", email: str = None) -> dict:
        """
        Creates a one-time payment link via dLocal Go for credit top-ups.
        Uses the /v1/payments endpoint (not subscriptions).
        
        Args:
            amount: Amount in USD (must be one of CREDIT_PACKAGES keys: 5, 10, 20)
            company_id: Company ID for tracking
            currency: Currency code
            email: Optional payer email
            
        Returns:
            dict with 'checkout_url' and 'credits' to be granted on confirmation
        """
        credits_to_grant = self.CREDIT_PACKAGES.get(int(amount))
        if credits_to_grant is None:
            raise ValueError(f"Invalid top-up amount: ${amount}. Valid amounts: {list(self.CREDIT_PACKAGES.keys())}")

        backend_url = os.environ.get('DLOCAL_WEBHOOK_URL', os.environ.get('NEXT_PUBLIC_API_URL', 'http://localhost:5000'))
        notification_url = f"{backend_url}/api/webhooks/dlocal"
        
        frontend_url = os.environ.get('NEXT_PUBLIC_APP_URL', 'http://localhost:3000')
        success_url = f"{frontend_url}/dashboard?topup=success"
        back_url = f"{frontend_url}/subscribe"
        error_url = f"{frontend_url}/subscribe?topup=error"

        # Determine the correct checkout base for one-time payments
        if self.env == 'production':
            checkout_base = "https://checkout.dlocalgo.com"
        else:
            checkout_base = "https://checkout-sbx.dlocalgo.com"

        payload = {
            "amount": amount,
            "currency": currency,
            "country": "EC",  # Default; can be dynamic based on company
            "description": f"PymAI Credit Top-Up: {credits_to_grant} credits",
            "external_id": f"topup_{company_id}",
            "notification_url": notification_url,
            "success_url": success_url,
            "back_url": back_url,
            "error_url": error_url,
        }

        if email:
            payload["payer"] = {"email": email}

        try:
            url = f"{self.base_api_url}/payments"
            response = requests.post(url, json=payload, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

            # dLocal Go returns a payment_id or redirect_url
            checkout_url = data.get('redirect_url') or data.get('checkout_url') or f"{checkout_base}/collect/{data.get('id', '')}"

            return {
                'checkout_url': checkout_url,
                'payment_id': data.get('id'),
                'credits': credits_to_grant,
                'amount': amount,
                'currency': currency
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"dLocal Go one-time payment failed: {e.response.text}")
            raise Exception(f"Failed to create dLocal payment: {e.response.text}")
        except Exception as e:
            logger.error(f"dLocal Go one-time payment error: {str(e)}")
            raise
