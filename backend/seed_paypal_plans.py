import logging
from app import create_app
from extensions import db
from models.subscription import Plan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_paypal_tokens():
    app = create_app()
    with app.app_context():
        # Mapping plan names to PayPal Live Plan IDs and new prices
        paypal_plans_data = {
            'Jab': {
                'price_id': 'P-3MY0809184136540KNIT2ROI',
                'price_monthly': 29.99,
                'price_annual': 299.90
            },
            'Uppercut': {
                'price_id': 'P-4N293957WJ902173LNIT2TRI',
                'price_monthly': 69.99,
                'price_annual': 699.90
            },
            'Knockout': {
                'price_id': 'P-46K32402ML574194UNIT2T7Q',
                'price_monthly': 199.00,
                'price_annual': 1990.00
            }
        }

        logger.info("Updating plans for PayPal Live Billing (IDs & pricing)...")
        for plan_name, info in paypal_plans_data.items():
            plan = Plan.query.filter_by(name=plan_name).first()
            if plan:
                price_id = info['price_id']
                price_monthly = info['price_monthly']
                price_annual = info['price_annual']
                
                updated = False
                if plan.external_plan_id != price_id:
                    logger.info(f"Updating plan '{plan_name}' ID from '{plan.external_plan_id}' to '{price_id}'")
                    plan.external_plan_id = price_id
                    plan.external_plan_token = price_id
                    updated = True
                
                if plan.price_monthly != price_monthly:
                    logger.info(f"Updating plan '{plan_name}' monthly price from {plan.price_monthly} to {price_monthly}")
                    plan.price_monthly = price_monthly
                    updated = True
                    
                if plan.price_annual != price_annual:
                    logger.info(f"Updating plan '{plan_name}' annual price from {plan.price_annual} to {price_annual}")
                    plan.price_annual = price_annual
                    updated = True
                
                if not updated:
                    logger.info(f"Plan '{plan_name}' is already up-to-date.")
            else:
                logger.warning(f"Plan '{plan_name}' not found in database to update.")
        
        db.session.commit()
        logger.info("Database plans synchronized with PayPal live configurations successfully.")

if __name__ == '__main__':
    update_paypal_tokens()

