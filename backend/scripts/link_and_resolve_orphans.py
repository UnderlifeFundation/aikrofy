
"""
Script to link orphaned Transactions and Appointments to Conversations.
This fixes the Resolution Rate discrepancy where successful actions exist but aren't linked to a conversation (and thus aren't resolving it).
"""
import sys
import os
from datetime import timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.conversation import Conversation
from models.transaction import Transaction, TransactionStatus
from models.appointment import Appointment
from models.customer import Customer

app = create_app()

def main():
    print("Running Orphan Linker...")
    with app.app_context():
        linked_txns = 0
        linked_appts = 0
        
        # 1. Link Transactions
        orphaned_txns = Transaction.query.filter(Transaction.conversation_id == None).all()
        for txn in orphaned_txns:
            # Strategy: Find most recent conversation for this customer BEFORE or AROUND txn time
            customer_id = txn.customer_id
            
            if not customer_id:
                # Try to find customer by other means? (Maybe skipped for now)
                continue
                
            # Find conv
            recent_conv = Conversation.query.filter(
                Conversation.company_id == txn.company_id,
                Conversation.type == 'customer',
                # Customer match
                # Use a join or explicit lookup if conv stores customer_id (it doesn't, it stores phone/email metadata)
                # But we can assume if we have customer_id on txn, we can find convs. 
                # Convs are usually linked by phone number or email match to Customer.
            ).order_by(Conversation.started_at.desc()).all()
            
            # Filter in python because of potential metadata complexity
            target_conv = None
            customer = Customer.query.get(customer_id)
            if not customer: continue
            
            for conv in recent_conv:
                # Check match
                matches = False
                if conv.contact_phone and customer.phone and conv.contact_phone in customer.phone: matches = True
                if customer.email and conv.contact_email and customer.email == conv.contact_email: matches = True
                
                # Loose time check: Conv started before txn?
                if matches:
                     # If conv started before or within 7 days of txn
                     if conv.started_at <= txn.created_at + timedelta(hours=168):
                         target_conv = conv
                         break
            
            if target_conv:
                print(f"[TXN] Linking Transaction {txn.id} ($ {txn.amount}) to Conversation {target_conv.id}")
                txn.conversation_id = target_conv.id
                
                if not target_conv.is_resolved:
                    target_conv.is_resolved = True
                    target_conv.resolved_at = txn.created_at
                
                linked_txns += 1

        # 2. Link Appointments
        orphaned_appts = Appointment.query.filter(Appointment.conversation_id == None).all()
        for appt in orphaned_appts:
            customer_id = appt.customer_id
            if not customer_id: continue
            
            customer = Customer.query.get(customer_id)
            if not customer: continue

            # Find conv (same logic)
            recent_conv = Conversation.query.filter(
                Conversation.company_id == appt.company_id,
                Conversation.type == 'customer'
            ).order_by(Conversation.started_at.desc()).all()
            
            target_conv = None
            for conv in recent_conv:
                matches = False
                if conv.contact_phone and customer.phone and conv.contact_phone in customer.phone: matches = True
                
                if matches:
                     if conv.started_at <= appt.created_at + timedelta(hours=24):
                         target_conv = conv
                         break
            
            if target_conv:
                 print(f"[APPT] Linking Appointment {appt.id} to Conversation {target_conv.id}")
                 appt.conversation_id = target_conv.id
                 
                 if not target_conv.is_resolved:
                     target_conv.is_resolved = True
                     target_conv.resolved_at = appt.created_at
                 
                 linked_appts += 1
        
        db.session.commit()
        print(f"\nSummary: Linked {linked_txns} Transactions and {linked_appts} Appointments.")

if __name__ == '__main__':
    main()
