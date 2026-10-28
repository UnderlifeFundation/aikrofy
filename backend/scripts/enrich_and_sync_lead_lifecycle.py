"""
Script: enrich_and_sync_lead_lifecycle.py
Purpose:
- Matches Beta Leads with Customer records for 360-degree demographic and telemetry profiling.
- Cleans up or identifies orphan / unrecognized visitor stubs.
- Recalculates composite lead scores based on corporate domain, buying role, country, and AI interaction.
- Autonomously advances Kanban pipeline stages according to business milestones.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.company import Company
from models.user import User
from models.customer import Customer
from models.beta_lead import BetaLead, BetaLeadStatus
from models.conversation import Conversation, Message
from models.funnel_stage import FunnelStage
from models.subscription import Subscription, SubscriptionStatus
from services.lead_scoring_service import LeadScoringService

def run_enrichment():
    app = create_app()
    with app.app_context():
        print("=== 1. ENRICHING BETA LEADS & PLATFORM CRM CUSTOMERS ===")
        # 1. Sync & Enrich all BetaLeads to Company 1 (Platform CRM)
        platform_company_id = 1
        
        # Ensure default stages exist for Company 1
        stages = FunnelStage.query.filter_by(company_id=platform_company_id).order_by(FunnelStage.sort_order.asc()).all()
        if not stages:
            default_names = ["Lead / Solicitud Demo", "Demo Activa", "Calificado", "Propuesta", "Negociación", "Cliente Activo"]
            for idx, name in enumerate(default_names):
                stg = FunnelStage(company_id=platform_company_id, name=name, sort_order=idx)
                db.session.add(stg)
            db.session.commit()
            stages = FunnelStage.query.filter_by(company_id=platform_company_id).order_by(FunnelStage.sort_order.asc()).all()
        
        stage_map = {s.sort_order: s.id for s in stages}
        
        beta_leads = BetaLead.query.all()
        for b in beta_leads:
            parts = b.contact_name.strip().split(' ', 1)
            first_n = parts[0]
            last_n = parts[1] if len(parts) > 1 else ''
            
            customer = Customer.query.filter(
                (Customer.company_id == platform_company_id) & 
                ((Customer.email == b.email) | (Customer.phone == b.phone))
            ).first()
            
            if not customer:
                customer = Customer(
                    company_id=platform_company_id,
                    first_name=first_n,
                    last_name=last_n,
                    email=b.email,
                    phone=b.phone,
                    work_company=b.company_name,
                    buying_role=b.role_in_company or 'Solicitante Demo',
                    country=b.ip_country or 'Ecuador',
                    city=b.ip_city or 'Quito',
                    customer_metadata={
                        'source': 'beta_registration',
                        'industry': b.industry,
                        'employee_count': b.employee_count,
                        'ai_expectations': b.ai_expectations,
                        'ai_experience': b.ai_experience,
                        'products_services': b.products_services,
                        'beta_status': b.status.value if hasattr(b.status, 'value') else b.status
                    }
                )
                db.session.add(customer)
                db.session.flush()
                print(f"Created customer for BetaLead: {b.contact_name} ({b.company_name})")
            else:
                customer.first_name = first_n
                customer.last_name = last_n
                customer.work_company = b.company_name
                customer.buying_role = b.role_in_company or customer.buying_role
                if not customer.customer_metadata:
                    customer.customer_metadata = {}
                customer.customer_metadata.update({
                    'industry': b.industry,
                    'employee_count': b.employee_count,
                    'ai_expectations': b.ai_expectations,
                    'ai_experience': b.ai_experience,
                    'products_services': b.products_services,
                    'beta_status': b.status.value if hasattr(b.status, 'value') else b.status
                })
                print(f"Updated customer metadata for BetaLead: {b.contact_name} ({b.company_name})")

            # Determine initial stage based on beta status
            if b.status == BetaLeadStatus.APPROVED:
                customer.funnel_stage_id = stage_map.get(1) or stage_map.get(0) # Demo Activa
            else:
                customer.funnel_stage_id = stage_map.get(0) # Lead / Solicitud Demo

        db.session.commit()

        print("\n=== 2. CLEANING UP / FORMATTING ORPHAN WEBCHAT STUBS ===")
        # Find customers with 'None None' or no contact info
        orphan_customers = Customer.query.filter(
            (Customer.first_name.in_(['None', '', None])) | 
            (Customer.first_name.like('Visitante Webchat%'))
        ).all()
        
        for c in orphan_customers:
            conv_count = Conversation.query.filter_by(customer_id=c.id).count()
            # If completely empty with 0 conversations and no email/phone, delete or format
            if conv_count == 0 and not c.email and not c.phone:
                print(f"Removing empty orphan customer #{c.id}")
                db.session.delete(c)
            else:
                if not c.first_name or c.first_name == 'None':
                    c.first_name = "Visitante Webchat"
                if c.last_name == 'None':
                    c.last_name = f"#{c.id}"
                if not c.buying_role:
                    c.buying_role = "Prospecto Anónimo"
                print(f"Formatted active guest customer #{c.id}: {c.first_name} {c.last_name}")

        db.session.commit()

        print("\n=== 3. RECALCULATING COMPOSITE LEAD SCORES & ADVANCING STAGES ===")
        all_customers = Customer.query.all()
        for cust in all_customers:
            try:
                score = LeadScoringService.calculate_composite_score(cust.company_id, cust.id)
                print(f"Customer #{cust.id} ({cust.first_name} {cust.last_name} | {cust.work_company or cust.email}): Score = {score}/100, Stage ID = {cust.funnel_stage_id}")
            except Exception as e:
                print(f"Error calculating score for customer #{cust.id}: {e}")

        print("\n=== ENRICHMENT & LIFECYCLE SYNC COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_enrichment()
