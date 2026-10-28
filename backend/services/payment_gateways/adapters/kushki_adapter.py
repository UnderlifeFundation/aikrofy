"""
Kushki Pagos Adapter - Multi-gateway payment integration.
Supports Kushki card charges, checkout links, and exact tax breakdowns.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP
import requests
import hmac
import hashlib
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class KushkiAdapter(AbstractPaymentGateway):
    """Adapter for Kushki Pagos using native REST API."""

    def configure(self) -> None:
        self.private_merchant_id = self.credentials.get("private_merchant_id")
        self.base_url = (
            "https://sandbox-api.kushkipagos.com"
            if self.sandbox_mode else
            "https://api.kushkipagos.com"
        )

    def _get_kushki_amount(self, amount: Decimal) -> Dict[str, Any]:
        """Forces tax breakdown with strict arithmetic precision as required."""
        # 12% standard VAT/IVA for Ecuador/others or customizable via config_payload
        vat_rate = Decimal(str(self.config_payload.get("vat_rate", 0.00)))
        
        if vat_rate > 0:
            # subtotalIva = amount / (1 + vat_rate)
            # iva = amount - subtotalIva
            subtotal_iva = (amount / (Decimal('1') + vat_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            iva = (amount - subtotal_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal_iva_0 = Decimal('0.00')
        else:
            subtotal_iva = Decimal('0.00')
            iva = Decimal('0.00')
            subtotal_iva_0 = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return {
            "subtotalIva": float(subtotal_iva),
            "subtotalIva0": float(subtotal_iva_0),
            "iva": float(iva),
            "ice": 0.0,
            "extraTaxes": {
                "propina": 0.0
            }
        }

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Process direct token payment via Kushki charges endpoint."""
        try:
            url = f"{self.base_url}/card/v1/charges"
            headers = {
                "Private-Merchant-Id": self.private_merchant_id,
                "Content-Type": "application/json"
            }
            
            amount_detail = self._get_kushki_amount(request.amount)
            payload = {
                "token": request.payment_token,
                "amount": {
                    "subtotalIva": amount_detail["subtotalIva"],
                    "subtotalIva0": amount_detail["subtotalIva0"],
                    "iva": amount_detail["iva"],
                    "ice": amount_detail["ice"],
                    "extraTaxes": amount_detail["extraTaxes"],
                    "currency": request.currency
                },
                "metadata": {
                    "idempotency_key": request.idempotency_key
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
                    error_message=res_json.get("message", "Kushki payment failed")
                )
                
            return NormalizedTransactionResponse(
                success=res_json.get("status") == "approved",
                status="captured" if res_json.get("status") == "approved" else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("ticketNumber"),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="KUSHKI_ERROR", error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Kushki authorize is done via pre-authorizations or direct charge simulation
        return self.charge(request)

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return NormalizedTransactionResponse(
            success=True, status="captured", amount=request.amount, currency=request.currency,
            transaction_id=transaction_id
        )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        try:
            url = f"{self.base_url}/card/v1/refunds"
            headers = {
                "Private-Merchant-Id": self.private_merchant_id,
                "Content-Type": "application/json"
            }
            payload = {
                "ticketNumber": transaction_id
            }
            if amount:
                payload["amount"] = {"value": float(amount)}
                
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            res_json = res.json()
            return NormalizedTransactionResponse(
                success=res.status_code in (200, 201),
                status="refunded" if res.status_code in (200, 201) else "failed",
                amount=Decimal(str(amount)) if amount else Decimal('0.00'),
                currency="USD",
                transaction_id=res_json.get("ticketNumber", transaction_id),
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
        """Create a Kushki Smartlink / Checkout session."""
        try:
            url = f"{self.base_url}/transfer/v1/init"
            headers = {
                "Private-Merchant-Id": self.private_merchant_id,
                "Content-Type": "application/json"
            }
            
            amount_detail = self._get_kushki_amount(request.amount)
            payload = {
                "amount": {
                    "subtotalIva": amount_detail["subtotalIva"],
                    "subtotalIva0": amount_detail["subtotalIva0"],
                    "iva": amount_detail["iva"],
                    "currency": request.currency
                },
                "redirectUrl": request.return_url or "https://aikrofy.com/payment/success",
                "description": request.description or "Payment",
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
                    error_message=res_json.get("message", "Smartlink initialization failed")
                )
                
            return NormalizedTransactionResponse(
                success=True,
                status="pending",
                amount=request.amount,
                currency=request.currency,
                transaction_id=res_json.get("token"),
                payment_url=res_json.get("redirectUrl"),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="PAYMENT_LINK_ERROR", error_message=str(e)
            )

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Valida que las notificaciones de eventos financieros provengan exactamente de Kushki."""
        try:
            timestamp = headers.get("X-Kushki-Id") or headers.get("x-kushki-id")
            received_signature = headers.get("X-Kushki-Signature") or headers.get("x-kushki-signature")
            webhook_signature_id = self.config_payload.get("webhook_signature_id")

            if not timestamp or not received_signature or not webhook_signature_id:
                return False

            base_string = f"{timestamp}{raw_body.decode('utf-8')}"
            computed_hmac = hmac.new(
                webhook_signature_id.encode('utf-8'),
                base_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(computed_hmac, received_signature)
        except Exception:
            return False
