"""
CRM and ERP Synchronization for Payment Transactions.
Syncs transaction state asynchronously with connected business tools.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from extensions import db
from models.payment_gateway import PaymentTransaction, TransactionStatus
from models.company import Company

logger = logging.getLogger(__name__)

def sync_transaction_to_crm_erp(transaction_id: int) -> None:
    """Syncs payment transaction results to CRM or ERP if connected."""
    try:
        # Prevent database session locks
        try:
            db.session.rollback()
        except Exception:
            pass

        tx = PaymentTransaction.query.get(transaction_id)
        if not tx:
            logger.warning(f"CRM/ERP Sync: Transaction {transaction_id} not found.")
            return

        company = tx.company
        if not company:
            return

        status_str = tx.status.value if tx.status else "pending"
        
        # 1. CRM Synchronization
        # Check if CRM is enabled/connected
        crm_config = getattr(company, 'crm_config', None)
        if crm_config and crm_config.is_connected:
            try:
                from services.crm.factory import get_crm_connector
                from services.crm.canonical_models import Deal
                
                connector = get_crm_connector(company)
                if connector:
                    # Create Deal representation
                    deal = Deal(
                        title=tx.description or f"Payment Link - Ref {tx.idempotency_key[:10]}",
                        amount=float(tx.amount),
                        stage="Closed Won" if status_str == "captured" else "Closed Lost" if status_str == "failed" else "Appointments",
                        pipeline="default",
                        description=f"Gateway: {tx.gateway_config.gateway_provider.value if tx.gateway_config else 'Unknown'}, status: {status_str}, Phone: {tx.customer_phone or ''}"
                    )
                    
                    res = connector.create_deal(deal)
                    logger.info(f"CRM Sync: Successfully created deal for transaction {tx.id}. Result: {res}")
            except Exception as crm_err:
                logger.error(f"CRM Sync Error: {crm_err}")

        # 2. ERP Synchronization
        # Check if ERP is enabled/connected
        erp_config = getattr(company, 'erp_config', None)
        if erp_config and erp_config.is_connected:
            try:
                from services.erp.factory import get_erp_driver
                driver = get_erp_driver(company)
                if driver:
                    # Record payment or invoice update in connected ERP
                    # Nuvei / SAP / Odoo etc.
                    erp_data = {
                        "amount": float(tx.amount),
                        "currency": tx.currency,
                        "description": tx.description or f"Conversational Payment Ref: {tx.id}",
                        "external_reference": tx.external_transaction_id or tx.idempotency_key,
                        "status": status_str,
                        "customer": {
                            "email": tx.customer_email,
                            "phone": tx.customer_phone,
                            "name": tx.customer_name
                        }
                    }
                    # Odoo / SAP / Custom drivers typically implement record creation
                    if hasattr(driver, 'create_invoice'):
                        res = driver.create_invoice(erp_data)
                        logger.info(f"ERP Sync: Successfully synced payment invoice. Result: {res}")
            except Exception as erp_err:
                logger.error(f"ERP Sync Error: {erp_err}")

    except Exception as e:
        logger.error(f"CRM/ERP global sync execution failed: {e}")
