import json
import logging
from app import create_app
from extensions import db
from models.subscription import Plan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_plans():
    app = create_app()
    with app.app_context():
        # Define the plans
        plans_data = [
            {
                'name': 'Jab',
                'description': 'Perfect for small businesses starting their automation journey.',
                'price_monthly': 29.0,
                'price_annual': 290.0,
                'currency': 'USD',
                'features': {
                    'max_agents': 1,
                    'max_documents': 10,
                    'max_leads': 100,
                    'monthly_credits': 2000,
                    'channels': ['webchat', 'whatsapp'],
                    'integrations': ['google_sheets', 'scheduling'],
                    'rag_enabled': True,
                    'analytics_enabled': False,
                    'voice_enabled': False,
                    'scheduling_enabled': True,
                    'payments_enabled': False,
                },
                'is_active': True,
                'is_default': True
            },
            {
                'name': 'Uppercut',
                'description': 'Advanced automation for growing teams across multiple channels.',
                'price_monthly': 99.0,
                'price_annual': 990.0,
                'currency': 'USD',
                'features': {
                    'max_agents': 3,
                    'max_documents': 50,
                    'max_leads': 500,
                    'monthly_credits': 10000,
                    'channels': ['webchat', 'whatsapp', 'email'],
                    'integrations': ['google_sheets', 'scheduling', 'crm_sync', 'ecommerce', 'payments'],
                    'rag_enabled': True,
                    'analytics_enabled': True,
                    'voice_enabled': False,
                    'scheduling_enabled': True,
                    'payments_enabled': True,
                },
                'is_active': True,
                'is_default': False
            },
            {
                'name': 'Knockout',
                'description': 'The ultimate comprehensive package for heavy hitters.',
                'price_monthly': 299.0,
                'price_annual': 2990.0,
                'currency': 'USD',
                'features': {
                    'max_agents': 10,
                    'max_documents': 500,
                    'max_leads': 999999,
                    'monthly_credits': 40000,
                    'channels': ['webchat', 'whatsapp', 'email', 'telegram', 'voice_calls'],
                    'integrations': ['google_sheets', 'scheduling', 'crm_sync', 'ecommerce', 'payments', 'erp_integration'],
                    'rag_enabled': True,
                    'analytics_enabled': True,
                    'voice_enabled': True,
                    'scheduling_enabled': True,
                    'payments_enabled': True,
                },
                'is_active': True,
                'is_default': False
            }
        ]

        logger.info("Starting plan seeding...")
        for p_data in plans_data:
            existing = Plan.query.filter_by(name=p_data['name']).first()
            if existing:
                logger.info(f"Plan '{p_data['name']}' already exists. Updating pricing & features.")
                existing.price_monthly = p_data['price_monthly']
                existing.price_annual = p_data['price_annual']
                existing.features = p_data['features']
                existing.description = p_data['description']
                existing.is_default = p_data['is_default']
            else:
                logger.info(f"Creating plan '{p_data['name']}'.")
                new_plan = Plan(**p_data)
                db.session.add(new_plan)
                
        # Ensure only one plan is default
        defaults = Plan.query.filter_by(is_default=True).all()
        if len(defaults) > 1:
            for p in defaults:
                if p.name != 'Jab':
                    p.is_default = False
                    
        db.session.commit()
        logger.info("Plan seeds completed successfully.")

if __name__ == '__main__':
    seed_plans()
