import logging
from app import create_app
from extensions import db
from models.subscription import Plan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_paddle_tokens():
    app = create_app()
    with app.app_context():
        # Mapping plan names to Sandbox Price IDs
        paddle_sandbox_tokens = {
            'Jab': 'pri_01j00000000000000000000001',
            'Uppercut': 'pri_01j00000000000000000000002',
            'Knockout': 'pri_01j00000000000000000000003'
        }

        logger.info("Updating plan external tokens for Paddle Billing...")
        for plan_name, price_id in paddle_sandbox_tokens.items():
            plan = Plan.query.filter_by(name=plan_name).first()
            if plan:
                if plan.external_plan_token != price_id:
                    logger.info(f"Updating plan '{plan_name}' token from '{plan.external_plan_token}' to '{price_id}'")
                    plan.external_plan_token = price_id
                    plan.external_plan_id = price_id
                else:
                    logger.info(f"Plan '{plan_name}' already has Paddle token: '{price_id}'")
            else:
                logger.warning(f"Plan '{plan_name}' not found in database to update.")
        
        db.session.commit()
        logger.info("Database plans synchronized with Paddle Price IDs successfully.")

if __name__ == '__main__':
    update_paddle_tokens()
