
"""
Script to retroactively resolve conversations that resulted in success:
1. Appointment Scheduled
2. Payment Completed
"""
import sys
import os

# Add parent directory to path to import app and extensions
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.conversation import Conversation
from models.appointment import Appointment
from models.transaction import Transaction, TransactionStatus
from datetime import datetime

app = create_app()

def main():
    print("Running retroactive resolution script...")
    
    with app.app_context():
        count = 0
        
        # 1. Resolve conversations with Appointments
        print("Checking Appointments...")
        appointments = Appointment.query.filter(Appointment.conversation_id != None).all()
        for appt in appointments:
            conv = Conversation.query.get(appt.conversation_id)
            if conv and not conv.is_resolved:
                conv.is_resolved = True
                conv.resolved_at = appt.created_at or datetime.utcnow()
                count += 1
                print(f"Resolving Conversation {conv.id} (Linked to Appointment {appt.id})")
        
        # 2. Resolve conversations with Completed OR PENDING Transactions (Intent)
        print("Checking Transactions (Completed & Pending)...")
        transactions = Transaction.query.filter(
            Transaction.conversation_id != None,
            Transaction.status.in_([TransactionStatus.COMPLETED.value, TransactionStatus.PENDING.value])
        ).all()
        
        for txn in transactions:
            conv = Conversation.query.get(txn.conversation_id)
            if conv and not conv.is_resolved:
                conv.is_resolved = True
                conv.resolved_at = txn.created_at or datetime.utcnow()
                count += 1
                print(f"Resolving Conversation {conv.id} (Linked to Transaction {txn.id})")
        
        db.session.commit()
        print(f"\nSuccessfully resolved {count} conversations.")

if __name__ == '__main__':
    main()
