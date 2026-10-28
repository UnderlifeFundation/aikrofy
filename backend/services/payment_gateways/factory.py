"""
Payment Adapter Factory - Multi-gateway payment integration.
Resolves dynamic instances of payment gateway adapters using the Factory Pattern.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Dict, Any
from services.payment_gateways.base import AbstractPaymentGateway
from services.payment_gateways.adapters.stripe_adapter import StripeAdapter
from services.payment_gateways.adapters.paypal_adapter import PayPalAdapter
from services.payment_gateways.adapters.mercadopago_adapter import MercadoPagoAdapter
from services.payment_gateways.adapters.kushki_adapter import KushkiAdapter
from services.payment_gateways.adapters.nuvei_adapter import NuveiAdapter
from services.payment_gateways.adapters.dlocalgo_adapter import DLocalGoAdapter
from services.payment_gateways.adapters.authorizenet_adapter import AuthorizeNetAdapter
from services.payment_gateways.adapters.custom_adapter import CustomAdapter


class PaymentAdapterFactory:
    """Factory to dynamically instantiate the correct payment gateway adapter."""

    _adapters = {
        "stripe": StripeAdapter,
        "paypal": PayPalAdapter,
        "mercadopago": MercadoPagoAdapter,
        "kushki": KushkiAdapter,
        "nuvei": NuveiAdapter,
        "dlocal_go": DLocalGoAdapter,
        "authorize_net": AuthorizeNetAdapter,
        "custom": CustomAdapter
    }

    @classmethod
    def get_adapter(
        cls,
        provider: str,
        credentials: Dict[str, Any],
        config_payload: Dict[str, Any] = None,
        sandbox_mode: bool = True
    ) -> AbstractPaymentGateway:
        """Resolves and returns a configured adapter instance."""
        adapter_class = cls._adapters.get(provider.lower())
        if not adapter_class:
            raise ValueError(f"Unsupported payment gateway provider: {provider}")
        
        return adapter_class(
            credentials=credentials,
            config_payload=config_payload,
            sandbox_mode=sandbox_mode
        )
