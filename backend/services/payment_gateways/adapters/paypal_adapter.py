"""
PayPal Adapter - Multi-gateway payment integration.
Uses PayPal Orders API v2 natively via REST requests.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import requests
import binascii
import base64
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class PayPalAdapter(AbstractPaymentGateway):
    """Adapter for PayPal Gateway using native REST API v2."""

    def configure(self) -> None:
        self.client_id = self.credentials.get("client_id")
        self.client_secret = self.credentials.get("client_secret")
        self.mode = self.credentials.get("mode", "sandbox")
        
        if self.mode == "live":
            self.base_url = "https://api-m.paypal.com"
        else:
            self.base_url = "https://api-m.sandbox.paypal.com"

    def _get_access_token(self) -> str:
        """Fetch OAuth2 token from PayPal."""
        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US"
        }
        auth = (self.client_id, self.client_secret)
        data = {"grant_type": "client_credentials"}
        
        response = requests.post(url, headers=headers, auth=auth, data=data, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # PayPal captures typically happen through order capture after approval.
        # Direct capture requires a payment_source. We will simulate/implement via immediate capture order.
        try:
            token = self._get_access_token()
            url = f"{self.base_url}/v2/checkout/orders"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "PayPal-Request-Id": request.idempotency_key
            }
            payload = {
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": request.currency,
                        "value": f"{float(request.amount):.2f}"
                    },
                    "description": request.description
                }],
                "application_context": {
                    "brand_name": self.config_payload.get("brand_name", "Aikrofy"),
                    "landing_page": "BILLING",  # Opens directly to Credit/Debit Card guest form without requiring PayPal account
                    "user_action": "PAY_NOW",
                    "shipping_preference": "NO_SHIPPING",
                    "return_url": request.return_url or "https://aikrofy.com/payment/success",
                    "cancel_url": request.cancel_url or "https://aikrofy.com/payment/cancel"
                }
            }
            
            # Pre-fill customer email if available for frictionless card checkout
            if request.customer_email:
                payload["payer"] = {
                    "email_address": request.customer_email
                }
                if request.customer_name:
                    name_parts = request.customer_name.strip().split(' ', 1)
                    payload["payer"]["name"] = {
                        "given_name": name_parts[0],
                        "surname": name_parts[1] if len(name_parts) > 1 else ""
                    }
            
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            res_json = res.json()
            
            if res.status_code not in (200, 201):
                return NormalizedTransactionResponse(
                    success=False,
                    status="failed",
                    amount=request.amount,
                    currency=request.currency,
                    error_code=str(res.status_code),
                    error_message=res_json.get("message", "Order creation failed")
                )
                
            # If immediate token exists, we capture. Normally, PayPal redirects.
            # So standard conversational flow is create_payment_link.
            # Here we return the order ID.
            approve_url = None
            for link in res_json.get("links", []):
                if link["rel"] == "approve":
                    approve_url = link["href"]
                    
            return NormalizedTransactionResponse(
                success=True,
                status="pending",
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("id"),
                payment_url=approve_url,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=request.amount,
                currency=request.currency,
                error_code="PAYPAL_ERROR",
                error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        try:
            token = self._get_access_token()
            url = f"{self.base_url}/v2/checkout/orders"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "PayPal-Request-Id": request.idempotency_key
            }
            payload = {
                "intent": "AUTHORIZE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": request.currency,
                        "value": str(request.amount)
                    },
                    "description": request.description
                }]
            }
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            res_json = res.json()
            
            approve_url = None
            for link in res_json.get("links", []):
                if link["rel"] == "approve":
                    approve_url = link["href"]

            return NormalizedTransactionResponse(
                success=res.status_code in (200, 201),
                status="pending", # Needs user authorization/approval
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("id"),
                payment_url=approve_url,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="AUTH_ERROR", error_message=str(e)
            )

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Capture an approved PayPal Order."""
        try:
            token = self._get_access_token()
            url = f"{self.base_url}/v2/checkout/orders/{transaction_id}/capture"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            res = requests.post(url, json={}, headers=headers, timeout=10)
            res_json = res.json()
            
            if res.status_code not in (200, 201):
                return NormalizedTransactionResponse(
                    success=False,
                    status="failed",
                    amount=request.amount,
                    currency=request.currency,
                    error_code=str(res.status_code),
                    error_message=res_json.get("message", "Order capture failed")
                )
                
            purchase_unit = res_json.get("purchase_units", [{}])[0]
            capture_info = purchase_unit.get("payments", {}).get("captures", [{}])[0]
            
            return NormalizedTransactionResponse(
                success=res_json.get("status") == "COMPLETED",
                status="captured" if res_json.get("status") == "COMPLETED" else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=capture_info.get("id", transaction_id),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="CAPTURE_ERROR", error_message=str(e)
            )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        try:
            token = self._get_access_token()
            # Refund endpoint requires Capture ID
            url = f"{self.base_url}/v2/payments/captures/{transaction_id}/refund"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            payload = {}
            if amount:
                payload["amount"] = {
                    "value": f"{amount:.2f}",
                    "currency_code": "USD" # Default, or query transaction
                }
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            res_json = res.json()
            return NormalizedTransactionResponse(
                success=res.status_code in (200, 201),
                status="refunded" if res.status_code in (200, 201) else "failed",
                amount=Decimal(str(amount)) if amount else Decimal('0.00'),
                currency="USD",
                transaction_id=res_json.get("id"),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="REFUND_ERROR", error_message=str(e)
            )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        # Void an authorization ID
        try:
            token = self._get_access_token()
            url = f"{self.base_url}/v2/payments/authorizations/{transaction_id}/void"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            res = requests.post(url, json={}, headers=headers, timeout=10)
            return NormalizedTransactionResponse(
                success=res.status_code == 204,
                status="voided" if res.status_code == 204 else "failed",
                amount=Decimal('0.00'),
                currency="USD",
                transaction_id=transaction_id,
                raw_response={"status_code": res.status_code}
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="VOID_ERROR", error_message=str(e)
            )

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Creation of payment link is same as ordering
        return self.charge(request)

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Verifica la firma digital RSA-SHA256 del webhook de PayPal de forma offline."""
        try:
            transmission_id = headers.get("PAYPAL-TRANSMISSION-ID")
            transmission_time = headers.get("PAYPAL-TRANSMISSION-TIME")
            transmission_sig = headers.get("PAYPAL-TRANSMISSION-SIG")
            cert_url = headers.get("PAYPAL-CERT-URL")
            webhook_id = self.config_payload.get("webhook_id")

            if not all([transmission_id, transmission_time, transmission_sig, cert_url, webhook_id]):
                return False

            # 1. Calcular checksum CRC32 sin signo del cuerpo bruto
            crc32_val = binascii.crc32(raw_body) & 0xffffffff
            
            # 2. Formular la cadena de validación
            validation_string = f"{transmission_id}|{transmission_time}|{webhook_id}|{crc32_val}"

            # 3. Descargar certificado público
            cert_res = requests.get(cert_url, timeout=5.0)
            cert_res.raise_for_status()
            cert_data = cert_res.content

            # 4. Extraer clave pública usando pyOpenSSL o cryptography
            from OpenSSL import crypto
            x509 = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)
            pub_key = x509.get_pubkey().to_cryptography_key()

            # 5. Validar firma RSA PKCS1v15 con SHA256
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            signature_bytes = base64.b64decode(transmission_sig)

            pub_key.verify(
                signature_bytes,
                validation_string.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
