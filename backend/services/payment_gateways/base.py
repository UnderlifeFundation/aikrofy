"""
Abstract Payment Gateway Interface - Multi-gateway payment integration.
Defines the required methods for all concrete payment adapters.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from services.payment_gateways.schemas import (
    NormalizedTransactionRequest,
    NormalizedTransactionResponse
)


class AbstractPaymentGateway(ABC):
    """Base interface for all payment gateway adapters using the Adapter Pattern."""

    def __init__(self, credentials: Dict[str, Any], config_payload: Dict[str, Any] = None, sandbox_mode: bool = True):
        self.credentials = credentials or {}
        self.config_payload = config_payload or {}
        self.sandbox_mode = sandbox_mode
        self.configure()

    @abstractmethod
    def configure(self) -> None:
        """Initialize the underlying SDK or client session using self.credentials."""
        pass

    @abstractmethod
    def charge(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Create and capture a charge immediately (direct charge)."""
        pass

    @abstractmethod
    def authorize(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Authorize a payment (hold funds) without capturing yet."""
        pass

    @abstractmethod
    def capture(self, transaction_id: str, amount: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Capture a previously authorized transaction."""
        pass

    @abstractmethod
    def refund(self, transaction_id: str, amount: float = None) -> NormalizedTransactionResponse:
        """Refund a captured transaction (partial or full)."""
        pass

    @abstractmethod
    def void(self, transaction_id: str) -> NormalizedTransactionResponse:
        """Void an authorized but uncaptured transaction."""
        pass

    @abstractmethod
    def create_payment_link(self, request: NormalizedTransactionRequest) -> NormalizedTransactionResponse:
        """Create a hosted checkout page link for in-chat/conversational payments."""
        pass

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, headers: Dict[str, str]) -> bool:
        """Verify the cryptographic signature of incoming webhooks."""
        pass
