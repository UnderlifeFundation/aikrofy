from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
import logging



from extensions import db
from models.user import User
from models.company import Company
from datetime import datetime
from models.subscription import Plan, Subscription, SubscriptionStatus
from models.transaction import Transaction, TransactionType, TransactionStatus, TransactionProvider
from services.paypal_service import PayPalService
import os

logger = logging.getLogger(__name__)
billing_bp = APIRouter('billing', __name__)
paypal_service = PayPalService()

@billing_bp.route('/plans', methods=['GET'])
@jwt_required()
def get_plans():
    """Returns all active plans for customers to see."""
    try:
        plans = Plan.query.filter_by(is_active=True).all()
        return jsonify([p.to_dict() for p in plans]), 200
    except Exception as e:
        logger.error(f"Error fetching plans in billing route: {e}")
        return jsonify({"error": str(e)}), 500

@billing_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    """
    Given a valid plan_id, returns the PayPal configuration 
    needed for the frontend SDK subscription flow.
    """
    try:
        db.session.rollback()
        data = request.json
        plan_id = data.get('plan_id')
        
        if not plan_id:
            return jsonify({'error': 'plan_id is required'}), 400
            
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.company:
            return jsonify({'error': 'No company attached to this user'}), 400

        company = user.company
        plan = Plan.query.get(plan_id)
        
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
            
        if not plan.paypal_plan_id:
            return jsonify({'error': 'Plan is not linked to a PayPal Plan ID'}), 404
            
        return jsonify({
            'type': 'subscription',
            'paypal_plan_id': plan.paypal_plan_id,
            'client_id': paypal_service.client_id or os.environ.get('PAYPAL_CLIENT_ID'),
            'user_email': user.email,
            'company_id': company.id
        }), 200
        
    except Exception as e:
        logger.error(f"Subscribe error in PymAI: {e}")
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/my-subscription', methods=['GET'])
@jwt_required()
def get_my_subscription():
    """Returns the current user/company's active subscription details."""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.company:
            return jsonify({'error': 'No company attached to this user'}), 400

        company = user.company
        sub = company.subscription
        
        # If it's a courtesy account, format mock active sub
        if sub and sub.status.value == 'courtesy':
            plan = Plan.query.filter_by(is_default=True).first()
            if not plan:
                plan = Plan.query.first()
                
            return jsonify({
                'status': 'courtesy',
                'is_active': True,
                'plan_name': plan.name if plan else 'Courtesy',
                'plan_description': plan.description if plan else 'Premium features enabled',
                'price': 0,
                'currency': 'USD',
                'features': plan.features if plan else {},
                'start_date': sub.start_date.isoformat() if sub.start_date else None,
                'next_payment_at': None,
                'notes': 'Courtesy account'
            }), 200

        # If they literally have no subscription at all (not even pending)
        if not sub:
            return jsonify({'status': 'none', 'is_active': False}), 200

        return jsonify({
            'status': sub.status.value,
            'is_active': sub.is_active,
            'plan_name': sub.plan.name if sub.plan else 'Unknown',
            'plan_description': sub.plan.description if sub.plan else '',
            'price': sub.plan.price_monthly if sub.plan else 0,
            'currency': sub.plan.currency if sub.plan else 'USD',
            'features': sub.plan.features if sub.plan else {},
            'start_date': sub.start_date.isoformat() if sub.start_date else None,
            'next_payment_at': sub.next_payment_at.isoformat() if sub.next_payment_at else None,
            'notes': sub.notes
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================
# Credit System Routes
# =============================================

@billing_bp.route('/credits', methods=['GET'])
@jwt_required()
def get_credit_balance():
    """Returns the current credit balance for the authenticated user's company."""
    # Preventive rollback to clear stale MySQL connections
    try:
        db.session.rollback()
    except Exception:
        pass
    
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'credit_balance': 0, 'plan_base_credits': 0, 'is_courtesy': False}), 200
        
        # Super admin without company — return safe defaults
        if not user.company:
            return jsonify({'credit_balance': -1, 'plan_base_credits': 0, 'is_courtesy': False}), 200

        company = user.company
        
        # Get plan base credits for context
        plan_base_credits = 0
        if company.subscription and company.subscription.plan:
            features = company.subscription.plan.features or {}
            plan_base_credits = features.get('monthly_credits', features.get('base_credits', 0))

        return jsonify({
            'credit_balance': company.credit_balance,
            'plan_base_credits': plan_base_credits,
            'is_courtesy': bool(company.subscription and company.subscription.status.value == 'courtesy')
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching credit balance: {e}")
        # Rollback on error
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({'credit_balance': 0, 'plan_base_credits': 0, 'is_courtesy': False, 'error': str(e)}), 200


@billing_bp.route('/credit-packages', methods=['GET'])
@jwt_required()
def get_credit_packages():
    """Returns the available credit top-up packages."""
    packages = [
        {'amount': 5,  'credits': 5000,  'conversations': 1000, 'label': '$5 - 5,000 Créditos (Starter)'},
        {'amount': 10, 'credits': 10000, 'conversations': 2500, 'label': '$10 - 10,000 Créditos (Popular)'},
        {'amount': 20, 'credits': 25000, 'conversations': 7000, 'label': '$20 - 25,000 Créditos (Pro Bonus +25%)'},
    ]
    return jsonify(packages), 200


@billing_bp.route('/top-up', methods=['POST'])
@jwt_required()
def purchase_credits():
    """
    Initiates a credit top-up purchase via PayPal.
    Expects JSON: { "amount": 5 | 10 | 20 }
    Creates a PayPal order and registers a pending transaction.
    """
    try:
        db.session.rollback()
    except:
        pass

    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.company:
            return jsonify({'error': 'No company attached'}), 400

        data = request.get_json()
        amount = data.get('amount')
        
        try:
            amount_val = float(amount)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount.'}), 400
            
        if int(amount_val) not in [5, 10, 20]:
            return jsonify({'error': 'Invalid amount. Choose $5, $10, or $20.'}), 400

        company = user.company
        credits_to_grant = {5: 5000, 10: 10000, 20: 25000}.get(int(amount_val), 5000)
        
        # Create PayPal Order
        order = paypal_service.create_order(
            amount=amount_val,
            currency='USD',
            description=f"Credit Recharge: {credits_to_grant} credits"
        )
        if not order:
            return jsonify({'error': 'Could not create PayPal order'}), 500
            
        order_id = order.get('id')
 
        # Log the pending transaction
        txn = Transaction(
            company_id=company.id,
            amount=amount_val,
            currency='USD',
            description=f"Credit Top-Up: {credits_to_grant} credits",
            service_type='credit_top_up',
            transaction_type=TransactionType.CREDIT_TOP_UP.value,
            credits_granted=credits_to_grant,
            provider=TransactionProvider.PAYPAL.value,
            provider_order_id=order_id,
            status=TransactionStatus.PENDING.value,
            channel='dashboard'
        )
        db.session.add(txn)
        db.session.commit()

        return jsonify({
            'type': 'order',
            'order_id': order_id,
            'client_id': paypal_service.client_id or os.environ.get('PAYPAL_CLIENT_ID'),
            'credits': credits_to_grant,
            'amount': amount_val,
            'transaction_id': txn.id
        }), 200

    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating credit top-up: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route('/capture-order', methods=['POST'])
@jwt_required()
def capture_paypal_order():
    """Capture a one-time order and grant credits."""
    try:
        db.session.rollback()
    except:
        pass
        
    try:
        data = request.json
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': 'order_id is required'}), 400
            
        capture = paypal_service.capture_order(order_id)
        if not capture or capture.get('status') != 'COMPLETED':
            return jsonify({'error': 'Payment could not be captured or is not completed'}), 400
            
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.company:
            return jsonify({'error': 'No company attached'}), 400
            
        company = user.company
        
        # Check if transaction exists
        txn = Transaction.query.filter_by(provider_order_id=order_id).first()
        if not txn:
            purchase_units = capture.get('purchase_units', [])
            amount_val = 0.0
            if purchase_units:
                amount_val = float(purchase_units[0].get('payments', {}).get('captures', [{}])[0].get('amount', {}).get('value', 0.0))
            else:
                amount_val = 5.0
            
            credits_to_grant = {5: 50, 10: 100, 20: 250}.get(int(amount_val), 50)
            
            txn = Transaction(
                company_id=company.id,
                amount=amount_val,
                currency='USD',
                description=f"Credit Top-Up: {credits_to_grant} credits",
                service_type='credit_top_up',
                transaction_type=TransactionType.CREDIT_TOP_UP.value,
                credits_granted=credits_to_grant,
                provider=TransactionProvider.PAYPAL.value,
                provider_order_id=order_id,
                status=TransactionStatus.PENDING.value,
                channel='dashboard'
            )
            db.session.add(txn)
            db.session.commit()
            
        # Update transaction status to COMPLETED
        if txn.status != TransactionStatus.COMPLETED.value:
            txn.status = TransactionStatus.COMPLETED.value
            company.credit_balance += txn.credits_granted
            db.session.commit()
            
        return jsonify({
            'message': 'Credits granted successfully',
            'new_balance': company.credit_balance
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error capturing credit top-up: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route('/verify-subscription', methods=['POST'])
@jwt_required()
def verify_subscription():
    """
    Directly query PayPal to verify the subscription status and activate locally.
    This provides an instant activation fallback for the frontend.
    """
    try:
        db.session.rollback()
    except:
        pass
        
    try:
        data = request.json
        subscription_id = data.get('subscription_id')
        
        if not subscription_id:
            return jsonify({'error': 'subscription_id is required'}), 400
            
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        
        if not user or not user.company:
            return jsonify({'error': 'No company attached to this user'}), 400
            
        company = user.company
        
        # Query PayPal API to get actual subscription details
        sub_details = paypal_service.get_subscription_details(subscription_id)
        if not sub_details:
            return jsonify({'error': 'Could not fetch subscription details from PayPal'}), 400
            
        status = sub_details.get('status')
        paypal_plan_id = sub_details.get('plan_id')
        
        if status in ['ACTIVE', 'APPROVED']:
            logger.info(f"Direct verification success: Sub {subscription_id} ({status}) -> Company {company.id}")
            
            plan = Plan.query.filter_by(external_plan_id=paypal_plan_id).first()
            if not plan:
                plan = Plan.query.filter_by(external_plan_token=paypal_plan_id).first()
                
            if not plan:
                return jsonify({'error': f"Plan with PayPal ID {paypal_plan_id} not found in database"}), 404
                
            sub = company.subscription
            if not sub:
                from models.subscription import Subscription
                sub = Subscription(
                    company_id=company.id,
                    plan_id=plan.id,
                    paypal_subscription_id=subscription_id,
                    status=SubscriptionStatus.ACTIVE,
                    start_date=datetime.utcnow()
                )
                db.session.add(sub)
            else:
                sub.plan_id = plan.id
                sub.paypal_subscription_id = subscription_id
                sub.status = SubscriptionStatus.ACTIVE
                sub.start_date = datetime.utcnow()
                
            # Log transaction
            txn = Transaction(
                company_id=company.id,
                amount=plan.price_monthly,
                currency=plan.currency,
                description=f"Subscription activated: {plan.name}",
                service_type='subscription',
                transaction_type=TransactionType.SUBSCRIPTION.value,
                provider=TransactionProvider.PAYPAL.value,
                provider_order_id=subscription_id,
                status=TransactionStatus.COMPLETED.value,
                channel='dashboard'
            )
            db.session.add(txn)
            
            db.session.commit()
            
            return jsonify({
                'message': 'Subscription verified and activated successfully',
                'status': 'active',
                'plan': plan.name
            }), 200
            
        return jsonify({
            'error': f"Subscription is not active (current status: {status})"
        }), 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error verifying subscription: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_company_transactions():
    """Returns the transaction history and invoices for the authenticated company."""
    try:
        db.session.rollback()
    except Exception:
        pass
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or not user.company:
            return jsonify([]), 200
        
        txns = Transaction.query.filter_by(company_id=user.company.id).order_by(Transaction.created_at.desc()).limit(50).all()
        return jsonify([t.to_dict() for t in txns]), 200
    except Exception as e:
        logger.error(f"Error fetching company transactions: {e}")
        return jsonify({"error": str(e)}), 500


@billing_bp.route('/sync-credits', methods=['POST'])
@jwt_required()
def sync_captured_credits():
    """
    Sync credits after successful payment capture from frontend.
    """
    try:
        db.session.rollback()
    except Exception:
        pass
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or not user.company:
            return jsonify({'error': 'No company attached'}), 400
            
        data = request.get_json() or {}
        order_id = data.get('order_id') or data.get('invoice_id')
        credits = int(data.get('credits', 0))
        amount = float(data.get('amount', 0))
        provider = data.get('provider', 'paypal')
        
        if credits <= 0 or amount <= 0:
            return jsonify({'error': 'Invalid credits or amount'}), 400
            
        company = user.company
        
        # Check if already recorded
        existing_txn = Transaction.query.filter_by(provider_order_id=order_id).first()
        if not existing_txn:
            txn = Transaction(
                company_id=company.id,
                amount=amount,
                currency='USD',
                description=f"Recarga Combustible IA: {credits:,} créditos",
                service_type='credit_top_up',
                transaction_type=TransactionType.CREDIT_TOP_UP.value,
                credits_granted=credits,
                provider=provider,
                provider_order_id=order_id,
                status=TransactionStatus.COMPLETED.value,
                channel='dashboard'
            )
            db.session.add(txn)
            company.credit_balance = (company.credit_balance or 0) + credits
            db.session.commit()
            logger.info(f"[CREDITS SYNC] Granted {credits} credits to Company {company.id}. New Balance: {company.credit_balance}")
            
        return jsonify({
            'success': True,
            'credit_balance': company.credit_balance,
            'message': 'Créditos sincronizados exitosamente'
        }), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing captured credits: {e}")
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/credits/create-order', methods=['POST'])
def create_credit_order():
    """
    Public and authenticated endpoint to create PayPal orders for credit top-up.
    Works seamlessly across reverse proxies and direct API client invocations.
    """
    try:
        data = request.get_json() or {}
        amount = float(data.get('amount', 20))
        credits = int(data.get('credits', 0)) or int(amount * 100)
        company_name = data.get('companyName') or data.get('company_name', 'Cliente Empresarial')
        tax_id = data.get('taxId') or data.get('tax_id', 'N/A')
        email = data.get('email', 'facturacion@empresa.com')
        phone = data.get('phone', '')
        method = data.get('method', 'card')

        origin = request.headers.get('origin') or 'https://aikrofy.com'
        invoice_id = f"AIK-CRED-{int(datetime.utcnow().timestamp() * 1000)}"

        # 1. Fetch live PayPal credentials from env or active service
        paypal_id = os.environ.get('PAYPAL_CLIENT_ID') or os.environ.get('PAYPAL_ID') or 'AUYxLqb4aKaVxE9Rd4l7ZmsmOD3EwFzCm5_qj9esAgDlvqUutzP5aomnhRFbWFg4s5vnJ14IOvMeY6in'
        paypal_secret = os.environ.get('PAYPAL_CLIENT_SECRET') or os.environ.get('PAYPAL_SECRET') or 'EKO7iXVxvhpnBO6QAGHvNYlAAQZFoyzEZLz4vS0J64RJoCKZnodSGctBuFIVEtqQ0AT99iauplBVHryi'
        paypal_mode = os.environ.get('PAYPAL_MODE', 'live')
        base_url = 'https://api-m.sandbox.paypal.com' if paypal_mode == 'sandbox' else 'https://api-m.paypal.com'

        import requests
        auth_response = requests.post(
            f"{base_url}/v1/oauth2/token",
            auth=(paypal_id, paypal_secret),
            data={'grant_type': 'client_credentials'},
            headers={'Accept': 'application/json', 'Accept-Language': 'en_US'}
        )
        auth_data = auth_response.json()
        access_token = auth_data.get('access_token')

        if not access_token:
            logger.error(f"[Credits Order] Failed to obtain PayPal access token: {auth_data}")
            return jsonify({'success': False, 'error': 'No se pudo autenticar con PayPal'}), 500

        is_guest_card = (method == 'card')
        order_payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': invoice_id,
                'amount': {'currency_code': 'USD', 'value': f"{amount:.2f}"},
                'description': f"Recarga Combustible IA: {credits:,} creditos ({company_name})",
                'custom_id': str({
                    'companyName': company_name,
                    'taxId': tax_id,
                    'phone': phone,
                    'credits': credits
                })[:127]
            }],
            'application_context': {
                'brand_name': 'Aikrofy Enterprise AI',
                'landing_page': 'BILLING' if is_guest_card else 'NO_PREFERENCE',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'PAY_NOW',
                'return_url': f"{origin}/pricing?success=true&provider={'card' if is_guest_card else 'paypal'}&orderId={invoice_id}&amount={amount}&credits={credits}",
                'cancel_url': f"{origin}/pricing?canceled=true#combustible",
            }
        }

        order_res = requests.post(
            f"{base_url}/v2/checkout/orders",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {access_token}"
            },
            json=order_payload
        )
        order_data = order_res.json()
        order_id = order_data.get('id')

        if not order_id:
            logger.error(f"[Credits Order] PayPal order error: {order_data}")
            return jsonify({'success': False, 'error': order_data.get('message', 'Error al crear orden en PayPal')}), 400

        approve_url = ''
        for link in order_data.get('links', []):
            if link.get('rel') == 'approve':
                approve_url = link.get('href')
                break

        return jsonify({
            'success': True,
            'orderId': order_id,
            'paymentUrl': approve_url,
            'invoiceId': invoice_id,
            'amount': amount,
            'credits': credits,
            'clientId': paypal_id
        }), 200

    except Exception as e:
        logger.error(f"Error creating credit order: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/credits/capture', methods=['POST'])
def capture_credit_order():
    """
    Public and authenticated endpoint to capture PayPal orders for credit top-up.
    """
    try:
        data = request.get_json() or {}
        order_id = data.get('orderId') or data.get('order_id')
        invoice_id = data.get('invoiceId') or data.get('invoice_id') or order_id
        company_name = data.get('companyName') or data.get('company_name', 'Cliente Empresarial')
        email = data.get('email', '')
        credits = int(data.get('credits', 0))

        if not order_id:
            return jsonify({'success': False, 'error': 'orderId es requerido'}), 400

        paypal_id = os.environ.get('PAYPAL_CLIENT_ID') or os.environ.get('PAYPAL_ID') or 'AUYxLqb4aKaVxE9Rd4l7ZmsmOD3EwFzCm5_qj9esAgDlvqUutzP5aomnhRFbWFg4s5vnJ14IOvMeY6in'
        paypal_secret = os.environ.get('PAYPAL_CLIENT_SECRET') or os.environ.get('PAYPAL_SECRET') or 'EKO7iXVxvhpnBO6QAGHvNYlAAQZFoyzEZLz4vS0J64RJoCKZnodSGctBuFIVEtqQ0AT99iauplBVHryi'
        paypal_mode = os.environ.get('PAYPAL_MODE', 'live')
        base_url = 'https://api-m.sandbox.paypal.com' if paypal_mode == 'sandbox' else 'https://api-m.paypal.com'

        import requests
        auth_response = requests.post(
            f"{base_url}/v1/oauth2/token",
            auth=(paypal_id, paypal_secret),
            data={'grant_type': 'client_credentials'},
            headers={'Accept': 'application/json', 'Accept-Language': 'en_US'}
        )
        auth_data = auth_response.json()
        access_token = auth_data.get('access_token')

        captured_amount = 50.0
        captured_credits = credits or 5000

        if access_token:
            capture_res = requests.post(
                f"{base_url}/v2/checkout/orders/{order_id}/capture",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f"Bearer {access_token}"
                }
            )
            capture_data = capture_res.json()
            if capture_data.get('status') in ['COMPLETED', 'APPROVED']:
                try:
                    val = capture_data['purchase_units'][0]['payments']['captures'][0]['amount']['value']
                    captured_amount = float(val)
                    captured_credits = int(captured_amount * 100)
                except Exception:
                    pass

        return jsonify({
            'success': True,
            'status': 'COMPLETED',
            'amount': captured_amount,
            'credits': captured_credits,
            'invoiceId': invoice_id,
            'companyName': company_name,
            'email': email
        }), 200

    except Exception as e:
        logger.error(f"Error capturing credit order: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


