"""
Transaction Service - Financial Logging & Auditing
"""
from models.transaction import Transaction, TransactionStatus
from extensions import db
from datetime import datetime

class TransactionService:
    @staticmethod
    def create_transaction(company_id, amount, currency, description, customer_id=None, conversation_id=None, provider="paypal", channel=None):
        """
        Log a new pending transaction.
        """
        txn = Transaction(
            company_id=company_id,
            customer_id=customer_id,
            conversation_id=conversation_id,
            amount=amount,
            currency=currency,
            description=description,
            provider=provider,
            status=TransactionStatus.PENDING.value,
            channel=channel
        )
        db.session.add(txn)
        db.session.commit()
        return txn

    @staticmethod
    def update_provider_order_id(txn_id, order_id):
        """
        Link internal ID with Provider Order ID (e.g. PayPal Token)
        """
        txn = Transaction.query.get(txn_id)
        if txn:
            txn.provider_order_id = order_id
            db.session.commit()
            return txn
        return None

    @staticmethod
    def update_status_by_order_id(provider_order_id, status, provider_response=None):
        """
        Update status based on Provider Order ID (used in webhooks)
        """
        txn = Transaction.query.filter_by(provider_order_id=provider_order_id).first()
        if txn:
            txn.status = status
            txn.updated_at = datetime.utcnow()
            db.session.commit()
            return txn
        return None

    @staticmethod
    def get_by_provider_id(provider_order_id):
        return Transaction.query.filter_by(provider_order_id=provider_order_id).first()
