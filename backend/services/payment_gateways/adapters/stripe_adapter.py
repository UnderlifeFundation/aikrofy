"""
Stripe Payment Adapter - Multi-gateway payment integration.
Supports Stripe payment intents and checkout sessions.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any
from decimal import Decimal
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)

class StripeAdapter(AbstractPaymentGateway):
    """Adapter for Stripe Gateway."""

    def configure(self) -> None:
        self.secret_key = self.credentials.get("secret_key")
        # Initialize client/SDK if available
        try:
            import stripe
            stripe.api_key = self.secret_key
            self.stripe = stripe
        except ImportError:
            self.stripe = None

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # For Stripe, a direct charge is typically creating a PaymentIntent
        if not self.stripe:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=request.amount,
                currency=request.currency,
                error_code="LIBRARY_MISSING",
                error_message="stripe library not installed in environment"
            )

        try:
            # Amount in cents
            amount_cents = int(request.amount * 100)
            intent = self.stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=request.currency.lower(),
                payment_method=request.payment_token,
                confirm=True if request.payment_token else False,
                description=request.description,
                metadata={"idempotency_key": request.idempotency_key},
                idempotency_key=request.idempotency_key
            )
            
            status_map = {
                "succeeded": "captured",
                "requires_capture": "authorized",
                "requires_action": "pending",
                "requires_payment_method": "failed",
                "canceled": "voided"
            }
            status = status_map.get(intent.status, "pending")
            
            return NormalizedTransactionResponse(
                success=intent.status == "succeeded",
                status=status,
                amount=request.amount,
                currency=request.currency,
                transaction_id=intent.id,
                raw_response=intent.to_dict()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=request.amount,
                currency=request.currency,
                error_code="CHARGE_ERROR",
                error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        if not self.stripe:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency
            )
        try:
            amount_cents = int(request.amount * 100)
            intent = self.stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=request.currency.lower(),
                payment_method=request.payment_token,
                capture_method="manual",
                confirm=True if request.payment_token else False,
                description=request.description,
                metadata={"idempotency_key": request.idempotency_key},
                idempotency_key=request.idempotency_key
            )
            return NormalizedTransactionResponse(
                success=True,
                status="authorized",
                amount=request.amount,
                currency=request.currency,
                transaction_id=intent.id,
                raw_response=intent.to_dict()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=request.amount,
                currency=request.currency,
                error_code="AUTH_ERROR",
                error_message=str(e)
            )

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        if not self.stripe:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency
            )
        try:
            intent = self.stripe.PaymentIntent.capture(transaction_id)
            return NormalizedTransactionResponse(
                success=intent.status == "succeeded",
                status="captured" if intent.status == "succeeded" else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=intent.id,
                raw_response=intent.to_dict()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=request.amount,
                currency=request.currency,
                error_code="CAPTURE_ERROR",
                error_message=str(e)
            )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        if not self.stripe:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD"
            )
        try:
            refund_args = {"payment_intent": transaction_id}
            if amount:
                refund_args["amount"] = int(amount * 100)
            res = self.stripe.Refund.create(**refund_args)
            return NormalizedTransactionResponse(
                success=res.status == "succeeded",
                status="refunded",
                amount=Decimal(str(amount)) if amount else Decimal('0.00'),
                currency="USD",
                transaction_id=res.id,
                raw_response=res.to_dict()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=Decimal('0.00'),
                currency="USD",
                error_code="REFUND_ERROR",
                error_message=str(e)
            )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        if not self.stripe:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD"
            )
        try:
            intent = self.stripe.PaymentIntent.cancel(transaction_id)
            return NormalizedTransactionResponse(
                success=intent.status == "canceled",
                status="voided",
                amount=Decimal('0.00'),
                currency="USD",
                transaction_id=intent.id,
                raw_response=intent.to_dict()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=Decimal('0.00'),
                currency="USD",
                error_code="VOID_ERROR",
                error_message=str(e)
            )

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        if not self.stripe:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency
            )
        try:
            amount_cents = int(request.amount * 100)
            # Create a stripe Checkout Session
            session = self.stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": request.currency.lower(),
                        "product_data": {
                            "name": request.description or "Payment",
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=request.return_url or "https://aikrofy.com/payment/success",
                cancel_url=request.cancel_url or "https://aikrofy.com/payment/cancel",
                metadata={"idempotency_key": request.idempotency_key}
            )
            return NormalizedTransactionResponse(
                success=True,
                status="pending",
                amount=request.amount,
                currency=request.currency,
                transaction_id=session.id,
                payment_url=session.url,
                raw_response=session.to_dict()
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False,
                status="failed",
                amount=request.amount,
                currency=request.currency,
                error_code="PAYMENT_LINK_ERROR",
                error_message=str(e)
            )

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        if not self.stripe:
            return False
        sig_header = headers.get("stripe-signature") or headers.get("Stripe-Signature")
        webhook_secret = self.config_payload.get("webhook_secret")
        if not sig_header or not webhook_secret:
            return False
        try:
            self.stripe.Webhook.construct_event(
                raw_body, sig_header, webhook_secret
            )
            return True
        except Exception:
            return False
