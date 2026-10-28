import os
import json
import logging
from app import create_app
from extensions import db
from models.subscription import Plan
from services.dlocal_service import DLocalGoService
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_plans():
    app = create_app()
    with app.app_context():
        plans_data = [
            {
                'name': 'Jab',
                'description': 'Plan Inicial - Ideal para comenzar con automatización en WhatsApp.',
                'price_monthly': 29.0,
                'price_annual': 290.0,
                'currency': 'USD',
                'features': {
                    'max_documents': 10,
                    'max_leads': 100,
                    'channels': ['whatsapp'], # Only whatsapp
                    'rag_enabled': True,
                    'analytics_enabled': False,
                },
                'is_active': True,
                'is_default': True
            },
            {
                'name': 'Uppercut',
                'description': 'Plan Intermedio - Para equipos creciendo con WhatsApp y Webchat.',
                'price_monthly': 99.0,
                'price_annual': 990.0,
                'currency': 'USD',
                'features': {
                    'max_documents': 50,
                    'max_leads': 500,
                    'channels': ['whatsapp', 'webchat'], # Webchat added
                    'rag_enabled': True,
                    'analytics_enabled': True,
                },
                'is_active': True,
                'is_default': False
            },
            {
                'name': 'Knockout',
                'description': 'Plan Completo - Todos los canales disponibles para un soporte 360.',
                'price_monthly': 299.0,
                'price_annual': 2990.0,
                'currency': 'USD',
                'features': {
                    'max_documents': 999,
                    'max_leads': 999999,
                    'channels': ['whatsapp', 'webchat', 'telegram', 'voice_calls'], # Full
                    'rag_enabled': True,
                    'analytics_enabled': True,
                },
                'is_active': True,
                'is_default': False
            }
        ]

        dlocal = DLocalGoService()

        for p_data in plans_data:
            existing = Plan.query.filter_by(name=p_data['name']).first()
            if existing:
                existing.price_monthly = p_data['price_monthly']
                existing.price_annual = p_data['price_annual']
                existing.features = p_data['features']
                existing.description = p_data['description']
                existing.is_default = p_data['is_default']
                
                if not existing.external_plan_token:
                    # Create in dlocal
                    logger.info(f"Creating missing {existing.name} in dLocal...")
                    try:
                        dloc_resp = dlocal.create_plan(
                            name=existing.name,
                            description=existing.description,
                            amount=existing.price_monthly,
                            currency=existing.currency,
                            frequency_type="MONTHLY"
                        )
                        existing.external_plan_token = dloc_resp.get('plan_token')
                        existing.external_plan_id = dloc_resp.get('id')
                        logger.info(f"Created in dLocal: {existing.external_plan_token}")
                    except Exception as e:
                        logger.error(f"Failed to create {existing.name} in dLocal: {e}")
                else:
                    # Update in dlocal
                    logger.info(f"Updating {existing.name} in dLocal...")
                    try:
                        dloc_id = existing.external_plan_id or existing.external_plan_token
                        dlocal.update_plan(
                            plan_id=dloc_id,
                            name=existing.name,
                            description=existing.description,
                            amount=existing.price_monthly
                        )
                        logger.info(f"Updated in dLocal successfully.")
                    except Exception as e:
                        logger.error(f"Failed to update {existing.name} in dLocal: {e}")
            else:
                new_plan = Plan(**p_data)
                logger.info(f"Creating new plan {new_plan.name} in dLocal...")
                try:
                    dloc_resp = dlocal.create_plan(
                        name=new_plan.name,
                        description=new_plan.description,
                        amount=new_plan.price_monthly,
                        currency=new_plan.currency,
                        frequency_type="MONTHLY"
                    )
                    new_plan.external_plan_token = dloc_resp.get('plan_token')
                    new_plan.external_plan_id = dloc_resp.get('id')
                    logger.info(f"Created in dLocal: {new_plan.external_plan_token}")
                except Exception as e:
                    logger.error(f"Failed to create start {new_plan.name} in dLocal: {e}")
                
                db.session.add(new_plan)
                
        db.session.commit()
        logger.info("Plans synchronized with dLocal successfully!")

if __name__ == '__main__':
    sync_plans()
