"""
MercadoPago Adapter - Multi-gateway payment integration.
Supports Mercado Pago preferences, payments, and pre-approvals search.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any
from decimal import Decimal
import requests
import hmac
import hashlib
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class MercadoPagoAdapter(AbstractPaymentGateway):
    """Adapter for Mercado Pago using native REST API calls."""

    def configure(self) -> None:
        self.access_token = self.credentials.get("access_token")
        self.base_url = "https://api.mercadopago.com"

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Create a direct payment
        try:
            url = f"{self.base_url}/v1/payments"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": request.idempotency_key
            }
            payload = {
                "transaction_amount": float(request.amount),
                "token": request.payment_token,
                "description": request.description,
                "installments": 1,
                "payment_method_id": "visa",  # Default placeholder for direct token
                "payer": {
                    "email": request.customer_email or "anonymous@example.com"
                }
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
                    error_message=res_json.get("message", "Payment creation failed")
                )
                
            status_map = {
                "approved": "captured",
                "in_process": "pending",
                "rejected": "failed",
                "cancelled": "voided",
                "refunded": "refunded"
            }
            status = status_map.get(res_json.get("status"), "pending")
            
            return NormalizedTransactionResponse(
                success=res_json.get("status") == "approved",
                status=status,
                amount=request.amount,
                currency=request.currency,
                transaction_id=str(res_json.get("id")),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="MERCADOPAGO_ERROR", error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Mercado Pago doesn't support auth/capture standard flow natively on all methods
        # without additional permissions/configurations. We'll fallback to preferences.
        return self.charge(request)

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return NormalizedTransactionResponse(
            success=True, status="captured", amount=request.amount, currency=request.currency,
            transaction_id=transaction_id
        )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        try:
            url = f"{self.base_url}/v1/payments/{transaction_id}/refunds"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {}
            if amount:
                payload["amount"] = float(amount)
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            res_json = res.json()
            return NormalizedTransactionResponse(
                success=res.status_code in (200, 201),
                status="refunded" if res.status_code in (200, 201) else "failed",
                amount=Decimal(str(amount)) if amount else Decimal('0.00'),
                currency="USD",
                transaction_id=str(res_json.get("id")),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="REFUND_ERROR", error_message=str(e)
            )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        # Cancel a payment that has not yet been processed
        try:
            url = f"{self.base_url}/v1/payments/{transaction_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {"status": "cancelled"}
            res = requests.put(url, json=payload, headers=headers, timeout=10)
            return NormalizedTransactionResponse(
                success=res.status_code == 200,
                status="voided" if res.status_code == 200 else "failed",
                amount=Decimal('0.00'),
                currency="USD",
                transaction_id=transaction_id,
                raw_response=res.json()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="VOID_ERROR", error_message=str(e)
            )

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Create a Preference URL for Mercado Pago Checkout."""
        try:
            url = f"{self.base_url}/checkout/preferences"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "items": [{
                    "title": request.description or "Payment",
                    "quantity": 1,
                    "unit_price": float(request.amount),
                    "currency_id": request.currency
                }],
                "payer": {
                    "email": request.customer_email or "anonymous@example.com"
                },
                "back_urls": {
                    "success": request.return_url or "https://aikrofy.com/payment/success",
                    "failure": request.cancel_url or "https://aikrofy.com/payment/cancel",
                    "pending": request.return_url or "https://aikrofy.com/payment/pending"
                },
                "auto_return": "approved",
                "external_reference": request.idempotency_key
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
                    error_message=res_json.get("message", "Preference creation failed")
                )
                
            sandbox_url = res_json.get("sandbox_init_point")
            prod_url = res_json.get("init_point")
            
            return NormalizedTransactionResponse(
                success=True,
                status="pending",
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("id"),
                payment_url=sandbox_url if self.sandbox_mode else prod_url,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="PAYMENT_LINK_ERROR", error_message=str(e)
            )

    def search_preapproval_subscription(self, payer_email: str) -> Dict[str, Any]:
        """
        Sincroniza el estado de las suscripciones de Mercado Pago mitigando el desajuste
        de visibilidad de usuarios. Realiza consultas directas en /preapproval/search.
        """
        try:
            url = f"{self.base_url}/preapproval/search"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            params = {"payer_email": payer_email}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                return {
                    "sync_status": "synchronized",
                    "entity": "subscription_preapproval",
                    "data": res.json().get("results", [])
                }
            return {"error": f"API request failed with status code {res.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Valida que las notificaciones provengan de Mercado Pago usando firma HMAC-SHA256."""
        try:
            # MP X-Signature header format: ts=...,v1=...
            sig_header = headers.get("x-signature") or headers.get("X-Signature")
            secret = self.config_payload.get("webhook_secret")
            if not sig_header or not secret:
                return False

            parts = dict(x.split("=") for x in sig_header.split(","))
            ts = parts.get("ts")
            received_signature = parts.get("v1")

            if not ts or not received_signature:
                return False

            # Concatenar timestamp con el body o id según el webhook
            # Para webhooks de Mercado Pago, la firma se verifica concatenando:
            # id del recurso + timestamp
            # O usando la cadena base del payload
            # Aquí implementamos la verificación estándar HMAC-SHA256
            base_string = f"id;{raw_body.decode('utf-8')};ts;{ts}"
            computed_hmac = hmac.new(
                secret.encode('utf-8'),
                base_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(computed_hmac, received_signature)
        except Exception:
            return False
