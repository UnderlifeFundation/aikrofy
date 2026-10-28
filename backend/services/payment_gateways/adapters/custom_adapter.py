"""
Custom Adapter - Multi-gateway payment integration.
Supports dynamic JSON mapping and routing for proprietary/custom API integrations.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any, List
from decimal import Decimal
import requests
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class CustomAdapter(AbstractPaymentGateway):
    """Declarative Adapter for proprietary custom gateways using dynamic JSON mapping."""

    def configure(self) -> None:
        self.api_endpoint = self.config_payload.get("api_endpoint")
        self.api_key = self.credentials.get("api_key")
        self.api_secret = self.credentials.get("api_secret")
        
        # Mappings configuration
        self.mappings = self.config_payload.get("mapping", {})
        self.success_path = self.config_payload.get("success_path", "status")
        self.success_value = self.config_payload.get("success_value", "success")
        self.transaction_id_path = self.config_payload.get("transaction_id_path", "id")
        self.error_message_path = self.config_payload.get("error_message_path", "error.message")

    def _set_nested_value(self, d: Dict[str, Any], path: str, value: Any) -> None:
        """Sets a value in a nested dict using a dot-separated path (e.g. 'payer.email')."""
        parts = path.split(".")
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = value

    def _get_nested_value(self, d: Dict[str, Any], path: str) -> Any:
        """Gets a value from a nested dict using a dot-separated path."""
        parts = path.split(".")
        current = d
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _build_payload(self, request: NormalizedTransactionRequest) -> Dict[str, Any]:
        """Builds custom API request body based on mapping rules."""
        payload = {}
        
        # Standard field mappings
        field_values = {
            "amount": float(request.amount),
            "currency": request.currency,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "customer_name": request.customer_name,
            "description": request.description,
            "payment_token": request.payment_token,
            "idempotency_key": request.idempotency_key,
            "return_url": request.return_url,
            "cancel_url": request.cancel_url
        }
        
        for field, value in field_values.items():
            if field in self.mappings and value is not None:
                path = self.mappings[field]
                self._set_nested_value(payload, path, value)
                
        return payload

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Send mapped request to the custom API endpoint."""
        if not self.api_endpoint:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="CONFIG_ERROR", error_message="Custom api_endpoint is not configured"
            )
            
        try:
            payload = self._build_payload(request)
            headers = {
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            if self.api_secret:
                headers["X-API-Secret"] = self.api_secret
                
            res = requests.post(self.api_endpoint, json=payload, headers=headers, timeout=10)
            res_json = res.json()
            
            # Evaluate success using path resolution
            status_val = self._get_nested_value(res_json, self.success_path)
            success = str(status_val).lower() == str(self.success_value).lower()
            tx_id = self._get_nested_value(res_json, self.transaction_id_path)
            err_msg = self._get_nested_value(res_json, self.error_message_path) if not success else None
            
            return NormalizedTransactionResponse(
                success=success,
                status="captured" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=str(tx_id) if tx_id else None,
                error_message=err_msg,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="CUSTOM_GATEWAY_ERROR", error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return self.charge(request)

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        return NormalizedTransactionResponse(
            success=True, status="captured", amount=request.amount, currency=request.currency,
            transaction_id=transaction_id
        )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        return NormalizedTransactionResponse(
            success=False, status="failed", amount=Decimal('0.00'), currency="USD",
            error_code="NOT_SUPPORTED", error_message="Refunds are not configured for custom adapter"
        )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        return NormalizedTransactionResponse(
            success=False, status="failed", amount=Decimal('0.00'), currency="USD",
            error_code="NOT_SUPPORTED", error_message="Voids are not configured for custom adapter"
        )

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Standard fallback to direct charging or redirect link parsing
        res = self.charge(request)
        if res.success:
            # Resolve redirect payment link from response using configured path if any
            link_path = self.config_payload.get("payment_url_path", "payment_url")
            res.payment_url = self._get_nested_value(res.raw_response, link_path)
        return res

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Generic signature verification for custom adapters (e.g. SHA256 signature)."""
        try:
            signature_header = self.config_payload.get("webhook_signature_header", "X-Signature")
            signature = headers.get(signature_header) or headers.get(signature_header.lower())
            secret = self.config_payload.get("webhook_secret")
            if not signature or not secret:
                return False
                
            computed_hmac = hmac.new(
                secret.encode('utf-8'),
                raw_body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(computed_hmac, signature)
        except Exception:
            return False
