"""
LangChain Payment Gateway Tools - Multi-gateway payment integration.
Enables agents to initiate and verify payments during conversations.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from typing import Optional
import uuid
import logging
from decimal import Decimal
from langchain_core.tools import tool
from routing import g
from extensions import db
from models.payment_gateway import PaymentGatewayConfig, PaymentTransaction, TransactionStatus, TransactionChannel
from models.customer import Customer
from services.payment_gateways.factory import PaymentAdapterFactory
from services.payment_gateways.schemas import NormalizedTransactionRequest

logger = logging.getLogger(__name__)


@tool
def payment_create_link(
    amount: float,
    currency: str = "USD",
    description: str = "Payment Link",
    customer_id: Optional[int] = None
) -> str:
    """
    Create a payment link for the customer.
    PREREQUISITE: If the customer is already identified in context or registered, generate the link immediately. If not registered, verify them first.
    IMPORTANT: If the price or product is known from the knowledge base, catalog, or user context (e.g. Landing Page $97), generate the payment link immediately with that amount without asking the customer to re-confirm the price.
    
    Args:
        amount: The total charge amount (use known price from context or knowledge base)
        currency: 3-character ISO currency code (default: USD)
        description: Description of the products/services being paid for
        customer_id: The numeric ID of the verified customer (optional)
        
    Returns:
        A text response containing the payment link for the customer to click.
    """
    try:
        # Clear stale DB sessions
        try:
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        conversation = getattr(g, 'current_conversation', None)
        agent = getattr(g, 'current_agent', None)

        if not company:
            return "Payment error: No company context found."

        # Fetch payment gateway configuration
        config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first()
        if not config or not config.is_connected:
            return "Payment error: This company has not configured an active payment gateway connection yet."

        cust_name, cust_email, cust_phone = None, None, None
        if customer_id:
            customer = Customer.query.get(customer_id)
            if customer:
                cust_name = getattr(customer, 'full_name', None) or getattr(customer, 'name', 'Cliente')
                cust_email = customer.email
                cust_phone = customer.phone

        # Fallback to conversation context if not provided
        if conversation and not cust_phone:
            cust_phone = conversation.contact_phone
        if conversation and not cust_name:
            cust_name = conversation.contact_name

        # Generate unique idempotency key
        idempotency_key = str(uuid.uuid4())

        # Create pending database transaction ledger
        channel_map = {
            "whatsapp": TransactionChannel.WHATSAPP,
            "telegram": TransactionChannel.TELEGRAM,
            "webchat": TransactionChannel.WEBCHAT,
            "voice": TransactionChannel.VOICE
        }
        channel = channel_map.get(conversation.channel if conversation else "webchat", TransactionChannel.WEBCHAT)

        txn = PaymentTransaction(
            company_id=company.id,
            gateway_config_id=config.id,
            customer_email=cust_email,
            customer_phone=cust_phone,
            customer_name=cust_name,
            amount=Decimal(str(amount)),
            currency=currency.upper(),
            description=description,
            status=TransactionStatus.PENDING,
            idempotency_key=idempotency_key,
            channel=channel,
            agent_id=agent.id if agent else None,
            conversation_id=conversation.id if conversation else None
        )
        db.session.add(txn)
        db.session.commit()

        # Instantiate provider adapter
        adapter = PaymentAdapterFactory.get_adapter(
            provider=config.gateway_provider.value,
            credentials=config.credentials,
            config_payload=config.config_payload,
            sandbox_mode=config.sandbox_mode
        )

        # Call adapter to create link
        req = NormalizedTransactionRequest(
            amount=Decimal(str(amount)),
            currency=currency.upper(),
            customer_email=cust_email,
            customer_phone=cust_phone,
            customer_name=cust_name,
            description=description,
            idempotency_key=idempotency_key,
            return_url=config.config_payload.get("return_url", "https://aikrofy.com/payment/success"),
            cancel_url=config.config_payload.get("cancel_url", "https://aikrofy.com/payment/cancel")
        )

        res = adapter.create_payment_link(req)

        if res.success and res.payment_url:
            # Build branded Hosted Checkout portal URL for guest debit/credit card payments
            portal_base = "https://app.aikrofy.com"
            hosted_portal_url = f"{portal_base}/api/payments/checkout/{idempotency_key}"

            # Update transaction record
            txn.payment_url = hosted_portal_url
            txn.external_transaction_id = res.transaction_id
            db.session.commit()

            return (
                f"Aquí tienes el portal seguro de pago para completar tu transacción de {amount} {currency.upper()} "
                f"por '{description}':\n{hosted_portal_url}\n\n"
                f"💳 Puedes pagar directamente con tarjeta de débito o crédito (como invitado, sin necesidad de tener cuenta PayPal) o con tu cuenta PayPal."
            )
        else:
            txn.status = TransactionStatus.FAILED
            txn.error_code = res.error_code or "LINK_CREATION_FAILED"
            txn.error_message = res.error_message or "Failed to generate payment url from gateway"
            db.session.commit()

            logger.error(f"Payment Link creation failed: {txn.error_message}")
            return f"Lo siento, ocurrió un error al generar tu enlace de pago: {txn.error_message}"

    except Exception as e:
        logger.error(f"Error in payment_create_link tool: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return f"Error procesando la solicitud de pago: {str(e)}"


@tool
def payment_check_status(idempotency_key: str) -> str:
    """
    Check the current status of a payment transaction.
    
    Args:
        idempotency_key: The unique reference key of the payment transaction
        
    Returns:
        A status summary message showing if the transaction is pending, captured, or failed.
    """
    try:
        try:
            db.session.rollback()
        except Exception:
            pass

        txn = PaymentTransaction.query.filter_by(idempotency_key=idempotency_key).first()
        if not txn:
            # Check by external transaction ID if passed
            txn = PaymentTransaction.query.filter_by(external_transaction_id=idempotency_key).first()

        if not txn:
            return f"No se encontró ninguna transacción con el ID o clave de referencia '{idempotency_key}'."

        return (
            f"Transacción #{txn.id} ({txn.currency} {txn.amount}):\n"
            f"- Estado: {txn.status.value.upper()}\n"
            f"- Cliente: {txn.customer_name or 'N/A'}\n"
            f"- Descripción: {txn.description or 'N/A'}\n"
            f"- Fecha: {txn.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    except Exception as e:
        logger.error(f"Error in payment_check_status: {e}")
        return f"Error al consultar el estado de la transacción: {str(e)}"
