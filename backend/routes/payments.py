from routing import APIRouter, jsonify, render_template, render_template_string, request
from datetime import datetime
import logging

from models.company import Company
from services.email_service import EmailService
from services.pdf_service import PDFService

payments_bp = APIRouter('payments', __name__)
logger = logging.getLogger(__name__)

@payments_bp.route('/dlocal/create-checkout', methods=['POST'])
def dlocal_create_checkout():
    """Generate a dLocal Go checkout link for a company."""
    
    data = request.get_json()
    company_id = data.get('company_id')
    plan_id = data.get('plan_id')
    email = data.get('email')
    
    if not company_id or not plan_id:
        return jsonify({'error': 'Missing company_id or plan_id'}), 400
        
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    from models.subscription import Plan
    from extensions import db
    plan = Plan.query.get(plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404
        
    from services.dlocal_service import DLocalGoService
    dlocal = DLocalGoService()
    
    if not plan.external_plan_token:
        try:
            dlocal_plan = dlocal.create_plan(
                name=plan.name,
                description=plan.description or f"Subscription to {plan.name}",
                amount=plan.price_monthly,
                currency=plan.currency or "USD",
                frequency_type="MONTHLY"
            )
            plan.external_plan_token = dlocal_plan.get('plan_token')
            db.session.commit()
        except Exception as e:
            return jsonify({'error': f"Failed to create dLocal plan: {str(e)}"}), 500
            
    url = dlocal.get_checkout_url(plan.external_plan_token, company_id, email)
    return jsonify({'checkout_url': url}), 200

@payments_bp.route('/success', methods=['GET'])
def payment_success():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    company_id = request.args.get('cid')
    
    # Support for both API v1 (paymentId) and v2 (token)
    token = request.args.get('token')
    
    if not (payment_id or token) or not company_id:
        return "Invalid parameters: Missing paymentId/token or cid", 400
        
    company = Company.query.get(company_id)
    if not company:
        return "Company not found", 404

    # Unified V2 Logic — All PayPal payments use PayPalToolkitService (Orders API v2)
    order_ref = token or payment_id
    try:
        from services.paypal_toolkit import PayPalToolkitService
        toolkit = PayPalToolkitService(company)
        result = toolkit.capture_order(order_ref)
        
        if result.get('success') or result.get('status') == 'COMPLETED':
            amount_val = result.get('amount', '0.00')
            currency = result.get('currency', 'USD')
            description = result.get('description', 'Service')
            
            invoice_data = {
                'id': result.get('capture_id', order_ref),
                'company_name': company.name or "PymAI User",
                'amount': amount_val,
                'currency': currency,
                'description': description
            }
            
            # Update Transaction Status
            from services.transaction_service import TransactionService
            from models.transaction import TransactionStatus
            TransactionService.update_status_by_order_id(order_ref, TransactionStatus.COMPLETED.value)
            
        else:
             from services.transaction_service import TransactionService
             from models.transaction import TransactionStatus
             TransactionService.update_status_by_order_id(order_ref, TransactionStatus.FAILED.value)
             return f"Payment Capture Failed: {result.get('error', 'Unknown error')}", 400
             
    except Exception as e:
        logger.error(f"PayPal Capture failed: {e}")
        return f"Capture Error: {e}", 500

    # COMMON: Generate Receipt
    try:
        # Generate PDF
        pdf_buffer = PDFService.generate_invoice(invoice_data)
        
        # Send Email
        # Note: Payer email might be different in V2, for now we assume we might not get it easily 
        # without another call, or stick to V1 logic. In V2 'payer' block is in capture result.
        # For simplicity, we skip email lookup details modification here to stay focused, 
        # or defaults to None if not easily available.
        
        email_service = EmailService()
        # Trying to send to contact email if we have conversation context? 
        # Or just skip invalid email error silently.
        
        logger.info(f"Payment {invoice_data['id']} successful. Receipt generated.")
            
    except Exception as e:
        logger.error(f"Post-payment processing failed: {e}")

    # Prepare display amount
    display_amount = invoice_data['amount']
    if isinstance(display_amount, dict):
        display_amount = display_amount.get('value', '0.00')

    # Fetch additional context from Transaction (if available)
    from services.transaction_service import TransactionService
    txn = TransactionService.get_by_provider_id(invoice_data['id'])
    
    customer_name = "Valued Customer"
    service_description = invoice_data.get('description', 'Service')
    
    if txn and txn.customer:
        customer_name = txn.customer.full_name
        # Use stored description/service if richer
        if txn.description: 
            service_description = txn.description
            
        # === CRM SYNC: Update Lifecycle to Customer ===
        try:
            from services.crm.factory import CRMFactory
            from services.crm.canonical_models import Contact
            crm_connector = CRMFactory.get_connector(company.id)
            if crm_connector and txn.customer.email:
                contact_data = Contact(email=txn.customer.email, lead_status='CUSTOMER')
                crm_connector.create_or_update_contact(txn.customer.email, contact_data)
                logger.info(f"CRM: Updated {txn.customer.email} to CUSTOMER")
        except Exception as crm_e:
            logger.error(f"CRM Sync Error: {crm_e}")

    # Render branded success page
    return render_template(
        'payment_success.html',
        company_name=invoice_data['company_name'],
        order_id=invoice_data['id'],
        amount=display_amount,
        currency=invoice_data['currency'],
        description=service_description,
        customer_name=customer_name
    )


@payments_bp.route('/cancel', methods=['GET'])
def payment_cancel():
    return render_template_string("""
        <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: red;">Payment Cancelled</h1>
            <p>You have cancelled the transaction.</p>
            <script>setTimeout(function(){ window.close(); }, 3000);</script>
        </body>
        </html>
    """)


# ============================================================
# Multi-Tenant Hosted Checkout (Guest Card + PayPal)
# Uses the merchant company's own configured Payment Gateway
# ============================================================

@payments_bp.route('/checkout/<idempotency_key>', methods=['GET'])
def hosted_checkout(idempotency_key: str):
    """
    Public branded hosted checkout page for conversational payments.
    Renders PayPal Smart Buttons with company's Client ID so customers
    can pay with debit/credit card as a guest without logging in.
    """
    from models.payment_gateway import PaymentTransaction, PaymentGatewayConfig
    txn = PaymentTransaction.query.filter_by(idempotency_key=idempotency_key).first()
    if not txn:
        return "Transacción no encontrada o expirada.", 404

    company = Company.query.get(txn.company_id)
    if not company:
        return "Empresa no encontrada.", 404

    config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first()
    if not config or not config.is_connected:
        return "La empresa no tiene una pasarela de pago activa configurada.", 400

    client_id = config.credentials.get('client_id')
    if not client_id:
        return "Configuración de pasarela incompleta.", 400

    return render_template(
        'hosted_checkout.html',
        company_id=company.id,
        company_name=company.name,
        amount=f"{float(txn.amount):.2f}",
        currency=txn.currency,
        description=txn.description or "Pago de Servicio",
        customer_name=txn.customer_name or "",
        client_id=client_id,
        idempotency_key=idempotency_key
    )


@payments_bp.route('/checkout/<idempotency_key>/create-order', methods=['POST'])
def hosted_checkout_create_order(idempotency_key: str):
    """
    Called by the hosted checkout page's PayPal Buttons to create an Order
    directly under the company's PayPal account credentials.
    """
    from models.payment_gateway import PaymentTransaction, PaymentGatewayConfig
    from services.payment_gateways.factory import PaymentAdapterFactory
    from services.payment_gateways.schemas import NormalizedTransactionRequest
    from decimal import Decimal

    txn = PaymentTransaction.query.filter_by(idempotency_key=idempotency_key).first()
    if not txn:
        return jsonify({'error': 'Transacción no encontrada'}), 404

    config = PaymentGatewayConfig.query.filter_by(company_id=txn.company_id).first()
    if not config or not config.is_connected:
        return jsonify({'error': 'Pasarela no conectada'}), 400

    try:
        adapter = PaymentAdapterFactory.get_adapter(
            provider=config.gateway_provider.value,
            credentials=config.credentials,
            config_payload=config.config_payload,
            sandbox_mode=config.sandbox_mode
        )

        origin = request.headers.get('origin') or 'https://aikrofy.com'
        req = NormalizedTransactionRequest(
            amount=Decimal(str(txn.amount)),
            currency=txn.currency,
            customer_email=txn.customer_email,
            customer_phone=txn.customer_phone,
            customer_name=txn.customer_name,
            description=txn.description or 'Pago',
            idempotency_key=f"{idempotency_key}-{int(datetime.utcnow().timestamp())}",
            return_url=f"{origin}/api/payments/success?cid={txn.company_id}",
            cancel_url=f"{origin}/api/payments/cancel"
        )

        res = adapter.create_payment_link(req)
        if res.success and res.transaction_id:
            txn.external_transaction_id = res.transaction_id
            from extensions import db
            db.session.commit()
            return jsonify({'order_id': res.transaction_id})
        else:
            return jsonify({'error': res.error_message or 'Error al crear la orden'}), 400

    except Exception as e:
        logger.error(f"Error in hosted_checkout_create_order: {e}")
        return jsonify({'error': str(e)}), 500


@payments_bp.route('/checkout/<idempotency_key>/capture', methods=['POST'])
def hosted_checkout_capture(idempotency_key: str):
    """
    Called upon customer approval in PayPal Buttons to capture funds
    into the company's PayPal merchant balance.
    """
    from models.payment_gateway import PaymentTransaction, PaymentGatewayConfig, TransactionStatus
    from services.payment_gateways.factory import PaymentAdapterFactory
    from services.payment_gateways.schemas import NormalizedTransactionRequest
    from decimal import Decimal
    from extensions import db
    from datetime import datetime

    data = request.get_json() or {}
    order_id = data.get('order_id')

    txn = PaymentTransaction.query.filter_by(idempotency_key=idempotency_key).first()
    if not txn:
        return jsonify({'error': 'Transacción no encontrada'}), 404

    target_order_id = order_id or txn.external_transaction_id
    if not target_order_id:
        return jsonify({'error': 'ID de orden no disponible'}), 400

    config = PaymentGatewayConfig.query.filter_by(company_id=txn.company_id).first()
    if not config or not config.is_connected:
        return jsonify({'error': 'Pasarela no conectada'}), 400

    try:
        adapter = PaymentAdapterFactory.get_adapter(
            provider=config.gateway_provider.value,
            credentials=config.credentials,
            config_payload=config.config_payload,
            sandbox_mode=config.sandbox_mode
        )

        req = NormalizedTransactionRequest(
            amount=Decimal(str(txn.amount)),
            currency=txn.currency,
            idempotency_key=idempotency_key
        )

        res = adapter.capture(target_order_id, req)
        if res.success:
            txn.status = TransactionStatus.CAPTURED
            txn.updated_at = datetime.utcnow()
            db.session.commit()

            # Fire CRM/ERP sync
            try:
                from services.payment_gateways.sync import sync_transaction_to_crm_erp
                sync_transaction_to_crm_erp(txn.id)
            except Exception as sync_e:
                logger.error(f"Sync error after hosted capture: {sync_e}")

            return jsonify({
                'success': True,
                'redirect_url': f"/api/payments/success?cid={txn.company_id}&token={target_order_id}"
            })
        else:
            return jsonify({'success': False, 'error': res.error_message or 'Captura fallida'}), 400

    except Exception as e:
        logger.error(f"Error in hosted_checkout_capture: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

