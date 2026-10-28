"""
Nuvei Adapter - Multi-gateway payment integration.
Supports secure server-side openOrder checksum calculation and Nuvei DMN verification.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any
from decimal import Decimal
import requests
import hmac
import hashlib
from datetime import datetime
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class NuveiAdapter(AbstractPaymentGateway):
    """Adapter for Nuvei (SafeCharge) using server-side security features."""

    def configure(self) -> None:
        self.merchant_id = self.credentials.get("merchant_id")
        self.merchant_site_id = self.credentials.get("merchant_site_id")
        self.secret_key = self.credentials.get("secret_key")
        self.base_url = (
            "https://ppp-test.safecharge.com/ppp/api/v1"
            if self.sandbox_mode else
            "https://secure.safecharge.com/ppp/api/v1"
        )

    def _generate_checksum(self, client_request_id: str, amount: str, currency: str, timestamp: str) -> str:
        """Calcula el hash SHA256 requerido por la API de Nuvei de forma segura en el servidor."""
        # merchantId + merchantSiteId + clientRequestId + amount + currency + timeStamp + merchantSecretKey
        base_string = (
            f"{self.merchant_id}"
            f"{self.merchant_site_id}"
            f"{client_request_id}"
            f"{amount}"
            f"{currency}"
            f"{timestamp}"
            f"{self.secret_key}"
        )
        return hashlib.sha256(base_string.encode('utf-8')).hexdigest()

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Nuvei direct payment
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            amount_str = f"{request.amount:.2f}"
            checksum = self._generate_checksum(
                request.idempotency_key, amount_str, request.currency, timestamp
            )
            
            url = f"{self.base_url}/payment.do"
            payload = {
                "merchantId": self.merchant_id,
                "merchantSiteId": self.merchant_site_id,
                "clientRequestId": request.idempotency_key,
                "amount": amount_str,
                "currency": request.currency,
                "timeStamp": timestamp,
                "checksum": checksum,
                "paymentOption": {
                    "card": {
                        "ccTempToken": request.payment_token
                    }
                },
                "transactionType": "Sale"
            }
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            
            success = res_json.get("transactionStatus") == "APPROVED"
            return NormalizedTransactionResponse(
                success=success,
                status="captured" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=str(res_json.get("transactionId")),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="NUVEI_ERROR", error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Same as charge but transactionType = Auth
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            amount_str = f"{request.amount:.2f}"
            checksum = self._generate_checksum(
                request.idempotency_key, amount_str, request.currency, timestamp
            )
            
            url = f"{self.base_url}/payment.do"
            payload = {
                "merchantId": self.merchant_id,
                "merchantSiteId": self.merchant_site_id,
                "clientRequestId": request.idempotency_key,
                "amount": amount_str,
                "currency": request.currency,
                "timeStamp": timestamp,
                "checksum": checksum,
                "paymentOption": {
                    "card": {
                        "ccTempToken": request.payment_token
                    }
                },
                "transactionType": "Auth"
            }
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            
            success = res_json.get("transactionStatus") == "APPROVED"
            return NormalizedTransactionResponse(
                success=success,
                status="authorized" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=str(res_json.get("transactionId")),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="AUTH_ERROR", error_message=str(e)
            )

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            amount_str = f"{request.amount:.2f}"
            
            # Checksum for settle: merchantId + merchantSiteId + clientRequestId + amount + currency + timeStamp + merchantSecretKey
            checksum = self._generate_checksum(
                request.idempotency_key, amount_str, request.currency, timestamp
            )
            url = f"{self.base_url}/settleTransaction.do"
            payload = {
                "merchantId": self.merchant_id,
                "merchantSiteId": self.merchant_site_id,
                "clientRequestId": request.idempotency_key,
                "relatedTransactionId": transaction_id,
                "amount": amount_str,
                "currency": request.currency,
                "timeStamp": timestamp,
                "checksum": checksum
            }
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            
            success = res_json.get("transactionStatus") == "APPROVED"
            return NormalizedTransactionResponse(
                success=success,
                status="captured" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=str(res_json.get("transactionId")),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="CAPTURE_ERROR", error_message=str(e)
            )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            amount_str = f"{amount:.2f}" if amount else "0.00"
            checksum = self._generate_checksum(
                transaction_id, amount_str, "USD", timestamp
            )
            url = f"{self.base_url}/refundTransaction.do"
            payload = {
                "merchantId": self.merchant_id,
                "merchantSiteId": self.merchant_site_id,
                "clientRequestId": transaction_id,
                "relatedTransactionId": transaction_id,
                "amount": amount_str,
                "currency": "USD",
                "timeStamp": timestamp,
                "checksum": checksum
            }
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            return NormalizedTransactionResponse(
                success=res_json.get("transactionStatus") == "APPROVED",
                status="refunded" if res_json.get("transactionStatus") == "APPROVED" else "failed",
                amount=Decimal(str(amount)) if amount else Decimal('0.00'),
                currency="USD",
                transaction_id=str(res_json.get("transactionId")),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="REFUND_ERROR", error_message=str(e)
            )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            checksum = self._generate_checksum(
                transaction_id, "0.00", "USD", timestamp
            )
            url = f"{self.base_url}/voidTransaction.do"
            payload = {
                "merchantId": self.merchant_id,
                "merchantSiteId": self.merchant_site_id,
                "clientRequestId": transaction_id,
                "relatedTransactionId": transaction_id,
                "amount": "0.00",
                "currency": "USD",
                "timeStamp": timestamp,
                "checksum": checksum
            }
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            return NormalizedTransactionResponse(
                success=res_json.get("transactionStatus") == "APPROVED",
                status="voided" if res_json.get("transactionStatus") == "APPROVED" else "failed",
                amount=Decimal('0.00'),
                currency="USD",
                transaction_id=transaction_id,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="VOID_ERROR", error_message=str(e)
            )

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Create checkout session page link using openOrder."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            amount_str = f"{request.amount:.2f}"
            checksum = self._generate_checksum(
                request.idempotency_key, amount_str, request.currency, timestamp
            )
            
            url = f"{self.base_url}/openOrder.do"
            payload = {
                "merchantId": self.merchant_id,
                "merchantSiteId": self.merchant_site_id,
                "clientRequestId": request.idempotency_key,
                "amount": amount_str,
                "currency": request.currency,
                "timeStamp": timestamp,
                "checksum": checksum,
                "transactionType": "Sale",
                "backUrl": request.return_url or "https://aikrofy.com/payment/success",
                "errorUrl": request.cancel_url or "https://aikrofy.com/payment/cancel"
            }
            res = requests.post(url, json=payload, timeout=10)
            res_json = res.json()
            
            if res_json.get("status") == "ERROR":
                return NormalizedTransactionResponse(
                    success=False,
                    status="failed",
                    amount=request.amount,
                    currency=request.currency,
                    error_code=res_json.get("errCode"),
                    error_message=res_json.get("reason", "OpenOrder failed")
                )
                
            # Generar URL de checkout ( SafeCharge Cashier )
            cashier_url = (
                f"https://ppp-test.safecharge.com/ppp/cashier/login.do"
                if self.sandbox_mode else
                f"https://secure.safecharge.com/ppp/cashier/login.do"
            )
            session_token = res_json.get("sessionToken")
            payment_url = f"{cashier_url}?sessionToken={session_token}"
            
            return NormalizedTransactionResponse(
                success=True,
                status="pending",
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("orderId"),
                payment_url=payment_url,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="PAYMENT_LINK_ERROR", error_message=str(e)
            )

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Verifica las llamadas DMN asíncronas emitidas por la infraestructura de Nuvei."""
        try:
            timestamp = headers.get("X-Authentication-Timestamp") or headers.get("x-authentication-timestamp")
            received_digest = headers.get("X-Authentication-Digest") or headers.get("x-authentication-digest")
            shared_secret = self.credentials.get("secret_key")

            if not timestamp or not received_digest or not shared_secret:
                return False

            base_message = raw_body + timestamp.encode('utf-8')
            computed_digest = hmac.new(
                shared_secret.encode('utf-8'),
                base_message,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(computed_digest, received_digest)
        except Exception:
            return False
