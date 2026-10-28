"""
dLocal Go Adapter - Multi-gateway payment integration.
Supports Latin American localized redirect payments and snake_case API payloads.

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


class DLocalGoAdapter(AbstractPaymentGateway):
    """Adapter for dLocal Go using native REST API."""

    def configure(self) -> None:
        self.api_key = self.credentials.get("api_key")
        self.secret_key = self.credentials.get("secret_key")
        self.base_url = "https://api.dlocalgo.com/v1"

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Create a payment in dLocal Go and return redirect_url."""
        try:
            url = f"{self.base_url}/payments"
            headers = {
                "Authorization": f"Bearer {self.api_key}:{self.secret_key}",
                "Content-Type": "application/json"
            }
            # Native snake_case payload
            payload = {
                "amount": float(request.amount),
                "currency": request.currency,
                "country": self.config_payload.get("country", "UY"),
                "success_url": request.return_url or "https://aikrofy.com/payment/success",
                "back_url": request.cancel_url or "https://aikrofy.com/payment/cancel",
                "notification_url": self.config_payload.get("notification_url", "https://api.aikrofy.com/api/payment-gateways/webhook/dlocal_go"),
                "external_id": request.idempotency_key
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
                    error_message=res_json.get("message", "dLocal Go payment failed")
                )
                
            return NormalizedTransactionResponse(
                success=True,
                status="pending",
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("id"),
                payment_url=res_json.get("redirect_url"),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="DLOCALGO_ERROR", error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return self.charge(request)

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return NormalizedTransactionResponse(
            success=True, status="captured", amount=request.amount, currency=request.currency,
            transaction_id=transaction_id
        )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        try:
            url = f"{self.base_url}/payments/{transaction_id}/refunds"
            headers = {
                "Authorization": f"Bearer {self.api_key}:{self.secret_key}",
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
                transaction_id=res_json.get("id"),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="REFUND_ERROR", error_message=str(e)
            )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        return self.refund(transaction_id)

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return self.charge(request)

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Verify signature for dLocal Go webhooks (HMAC-SHA256)."""
        try:
            signature = headers.get("X-DF-Signature") or headers.get("x-df-signature")
            if not signature or not self.secret_key:
                return False
            
            computed_hmac = hmac.new(
                self.secret_key.encode('utf-8'),
                raw_body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(computed_hmac, signature)
        except Exception:
            return False
