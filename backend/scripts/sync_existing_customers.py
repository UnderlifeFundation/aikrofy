"""
sync_existing_customers.py
---------------------------
Backfills existing customers into the configured CRM platform.
Now uses the generic CRMFactory instead of the legacy HubSpotService directly.

Usage: python3 scripts/sync_existing_customers.py
"""
import sys
import os
import time

sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models.company import Company
from models.customer import Customer
from models.appointment import Appointment
from models.transaction import Transaction
from models.conversation import Conversation

app = create_app()

def determine_status(customer):
    """
    Determine correct Lifecycle Stage and Lead Status based on history.
    """
    # 1. Transactions - Highest Priority (Customer)
    tx_count = Transaction.query.filter_by(customer_id=customer.id, status='completed').count()
    if tx_count > 0:
        return 'customer', 'CUSTOMER'
        
    # 2. Appointments - High Priority (Opportunity)
    app_count = Appointment.query.filter_by(customer_id=customer.id).count()
    if app_count > 0:
        return 'opportunity', 'SQL'
        
    # 3. Conversations - Medium Priority (In Progress)
    from sqlalchemy import or_
    conv_count = Conversation.query.filter(
        or_(
            Conversation.contact_email == customer.email,
            Conversation.contact_phone == customer.phone
        )
    ).count()
    if conv_count > 0:
        return 'lead', 'IN_PROGRESS'
        
    # 4. Default - New Lead
    return 'lead', 'NEW'

with app.app_context():
    company = Company.query.get(1)
    if not company:
        print("Company 1 not found")
        sys.exit(1)

    from services.crm.factory import CRMFactory
    from services.crm.canonical_models import Contact

    crm_connector = CRMFactory.get_connector(company.id)
    if not crm_connector:
        print(f"No CRM configured for company: {company.name}. Exiting.")
        sys.exit(0)

    print(f"--- Starting CRM Backfill for {company.name} using {type(crm_connector).__name__} ---")
    
    customers = Customer.query.filter_by(company_id=company.id).all()
    print(f"Found {len(customers)} customers.")
    
    success_count = 0
    error_count = 0
    
    for customer in customers:
        if not customer.email:
            print(f"Skipping Customer {customer.id} (No Email)")
            continue
            
        stage, status = determine_status(customer)
        print(f"Syncing {customer.email} -> Stage: {stage}, Status: {status}")
        
        try:
            contact_data = Contact(
                email=customer.email,
                first_name=customer.first_name,
                last_name=customer.last_name,
                phone=customer.phone,
                lead_status=status
            )
            crm_connector.create_or_update_contact(customer.email, contact_data)
            success_count += 1
            time.sleep(0.5)  # Rate limit
            
        except Exception as e:
            print(f"   ERROR: {e}")
            error_count += 1
            
    print(f"\n--- Backfill Complete ---")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
