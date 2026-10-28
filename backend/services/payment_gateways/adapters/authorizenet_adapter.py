"""
Authorize.Net Adapter - Multi-gateway payment integration.
Supports XML/JSON transaction requests containing createTransactionRequest.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any
from decimal import Decimal
import requests
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class AuthorizeNetAdapter(AbstractPaymentGateway):
    """Adapter for Authorize.Net using XML/JSON REST API."""

    def configure(self) -> None:
        self.api_login_id = self.credentials.get("api_login_id")
        self.transaction_key = self.credentials.get("transaction_key")
        self.base_url = (
            "https://apitest.authorize.net/xml/v1/request.api"
            if self.sandbox_mode else
            "https://api.authorize.net/xml/v1/request.api"
        )

    def _post_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON POST to Authorize.Net."""
        res = requests.post(self.base_url, json=payload, timeout=10)
        res.raise_for_status()
        # Authorize.Net JSON API returns BOM sometimes or raw text. Strip BOM if present.
        content = res.text.lstrip('\ufeff')
        import json
        return json.loads(content)

    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Process charge using authCaptureTransaction type inside createTransactionRequest."""
        try:
            payload = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.api_login_id,
                        "transactionKey": self.transaction_key
                    },
                    "refId": request.idempotency_key[:20],  # refId max 20 chars
                    "transactionRequest": {
                        "transactionType": "authCaptureTransaction",
                        "amount": f"{request.amount:.2f}",
                        "payment": {
                            "opaqueData": {
                                "dataDescriptor": "COMMON.ACCEPT.INAPP.PAYMENT",
                                "dataValue": request.payment_token
                            }
                        },
                        "customerIP": "127.0.0.1",
                        "userFields": {
                            "userField": [
                                {
                                    "name": "idempotency_key",
                                    "value": request.idempotency_key
                                }
                            ]
                        }
                    }
                }
            }
            res_json = self._post_request(payload)
            
            tx_res = res_json.get("transactionResponse", {})
            errors = tx_res.get("errors", [])
            messages = res_json.get("messages", {})
            
            success = messages.get("resultCode") == "Ok" and tx_res.get("responseCode") == "1"
            
            return NormalizedTransactionResponse(
                success=success,
                status="captured" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=tx_res.get("transId"),
                error_code=str(tx_res.get("responseCode")) if not success else None,
                error_message=errors[0].get("errorText") if errors else (messages.get("message", [{}])[0].get("text") if not success else None),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="AUTHORIZENET_ERROR", error_message=str(e)
            )

    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Process authorization only using authOnlyTransaction type."""
        try:
            payload = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.api_login_id,
                        "transactionKey": self.transaction_key
                    },
                    "refId": request.idempotency_key[:20],
                    "transactionRequest": {
                        "transactionType": "authOnlyTransaction",
                        "amount": f"{request.amount:.2f}",
                        "payment": {
                            "opaqueData": {
                                "dataDescriptor": "COMMON.ACCEPT.INAPP.PAYMENT",
                                "dataValue": request.payment_token
                            }
                        }
                    }
                }
            }
            res_json = self._post_request(payload)
            tx_res = res_json.get("transactionResponse", {})
            success = res_json.get("messages", {}).get("resultCode") == "Ok" and tx_res.get("responseCode") == "1"
            
            return NormalizedTransactionResponse(
                success=success,
                status="authorized" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=tx_res.get("transId"),
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="AUTH_ERROR", error_message=str(e)
            )

    def capture(self, transaction_id: str, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Capture a previously authorized transaction using priorAuthCaptureTransaction."""
        try:
            payload = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.api_login_id,
                        "transactionKey": self.transaction_key
                    },
                    "transactionRequest": {
                        "transactionType": "priorAuthCaptureTransaction",
                        "amount": f"{request.amount:.2f}",
                        "refTransId": transaction_id
                    }
                }
            }
            res_json = self._post_request(payload)
            tx_res = res_json.get("transactionResponse", {})
            success = res_json.get("messages", {}).get("resultCode") == "Ok" and tx_res.get("responseCode") == "1"
            
            return NormalizedTransactionResponse(
                success=success,
                status="captured" if success else "failed",
                amount=request.amount,
                currency=request.currency,
                transaction_id=tx_res.get("transId") or transaction_id,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=request.amount, currency=request.currency,
                error_code="CAPTURE_ERROR", error_message=str(e)
            )

    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        """Refund transaction using refundTransaction type."""
        try:
            payload = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.api_login_id,
                        "transactionKey": self.transaction_key
                    },
                    "transactionRequest": {
                        "transactionType": "refundTransaction",
                        "amount": f"{amount:.2f}" if amount else "0.00",
                        "refTransId": transaction_id,
                        "payment": {
                            "creditCard": {
                                "cardNumber": "0000",  # Authorize.net requires last 4 digits for refund
                                "expirationDate": "XXXX"
                            }
                        }
                    }
                }
            }
            res_json = self._post_request(payload)
            tx_res = res_json.get("transactionResponse", {})
            success = res_json.get("messages", {}).get("resultCode") == "Ok" and tx_res.get("responseCode") == "1"
            
            return NormalizedTransactionResponse(
                success=success,
                status="refunded" if success else "failed",
                amount=Decimal(str(amount)) if amount else Decimal('0.00'),
                currency="USD",
                transaction_id=tx_res.get("transId") or transaction_id,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="REFUND_ERROR", error_message=str(e)
            )

    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        """Void transaction using voidTransaction type."""
        try:
            payload = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.api_login_id,
                        "transactionKey": self.transaction_key
                    },
                    "transactionRequest": {
                        "transactionType": "voidTransaction",
                        "refTransId": transaction_id
                    }
                }
            }
            res_json = self._post_request(payload)
            tx_res = res_json.get("transactionResponse", {})
            success = res_json.get("messages", {}).get("resultCode") == "Ok" and tx_res.get("responseCode") == "1"
            
            return NormalizedTransactionResponse(
                success=success,
                status="voided" if success else "failed",
                amount=Decimal('0.00'),
                currency="USD",
                transaction_id=tx_res.get("transId") or transaction_id,
                raw_response=res_json
            )
        except Exception as e:
            return NormalizedTransactionResponse(
                success=False, status="failed", amount=Decimal('0.00'), currency="USD",
                error_code="VOID_ERROR", error_message=str(e)
            )

    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        # Authorize.Net doesn't have a simple, unified host payment redirect link API
        # without additional Merchant details or using their Accept Hosted interface.
        # We will simulate it via generating a mock Accept Hosted iframe request or throw error.
        return NormalizedTransactionResponse(
            success=False,
            status="failed",
            amount=request.amount,
            currency=request.currency,
            error_code="NOT_SUPPORTED",
            error_message="Authorize.Net hosted checkout sessions are not natively supported in this adapter. Use direct Accept API token charging."
        )

    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Authorize.Net uses Webhook Signature verification with HMAC-SHA512 of webhook body."""
        try:
            signature = headers.get("X-Anet-Signature") or headers.get("x-anet-signature")
            signature_key = self.config_payload.get("signature_key")
            if not signature or not signature_key:
                return False
            
            # Signature format is: sha512=HASH
            if signature.startswith("sha512="):
                received_hash = signature.split("=")[1]
            else:
                received_hash = signature
                
            computed_hash = hmac.new(
                signature_key.encode('utf-8'),
                raw_body,
                hashlib.sha512
            ).hexdigest()
            
            return hmac.compare_digest(computed_hash.lower(), received_hash.lower())
        except Exception:
            return False
