"""
Marketplace & Modular Assets Routes — Aikrofy Ecosystem
Handles:
1. Catalog listing of modular assets (Blog Module, Ecommerce, etc.)
2. Asset purchasing (via credit deduction or balance)
3. Cryptographic license generation anchored to tenant and domain
4. License verification webhook (called by client VPS to validate installation)
5. Secure ZIP download of the modular template package

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import os
import io
import zipfile
import logging
from datetime import datetime

from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from extensions import db
from models.user import User, UserRole
from models.company import Company
from models.modular_asset import ModularAsset, AssetLicense, AssetType
from models.transaction import Transaction, TransactionType, TransactionStatus, TransactionProvider

logger = logging.getLogger(__name__)
marketplace_bp = APIRouter('marketplace', __name__)


def get_user_company():
    """Return (user, company) for the authenticated request."""
    try:
        uid = int(get_jwt_identity())
        user = User.query.get(uid)
        if not user:
            return None, None
        if user.company:
            return user, user.company
        if user.role == UserRole.SUPER_ADMIN:
            comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
            return user, comp
        return None, None
    except Exception as e:
        logger.error(f"get_user_company error: {e}")
        return None, None


@marketplace_bp.route('/assets', methods=['GET'])
@jwt_required()
def list_available_assets():
    """Returns the catalog of modular assets and their purchase status for the company."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    # Auto-seed default assets if table is empty
    ensure_default_assets()

    assets = ModularAsset.query.filter_by(is_active=True).all()
    licenses = AssetLicense.query.filter_by(company_id=company.id, is_active=True).all()
    owned_asset_ids = {lic.asset_id: lic for lic in licenses}

    result = []
    for asset in assets:
        data = asset.to_dict()
        lic = owned_asset_ids.get(asset.id)
        data['is_purchased'] = lic is not None
        if lic:
            data['license_key'] = lic.license_key
            data['allowed_domains'] = lic.allowed_domains
            data['status_message'] = lic.status_message
            data['last_verified_at'] = lic.last_verified_at.isoformat() if lic.last_verified_at else None
        result.append(data)

    return jsonify({
        'company_id': company.id,
        'credit_balance': company.credit_balance,
        'assets': result
    }), 200


@marketplace_bp.route('/assets/purchase', methods=['POST'])
@jwt_required()
def purchase_asset():
    """
    Purchases a modular asset using credits or balance.
    Generates a unique cryptographic license anchored to the tenant and allowed domain.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    asset_slug = data.get('slug')
    target_domain = (data.get('domain') or '').strip().lower()

    if not asset_slug:
        return jsonify({'error': 'asset slug is required'}), 400

    asset = ModularAsset.query.filter_by(slug=asset_slug, is_active=True).first()
    if not asset:
        return jsonify({'error': 'Asset not found or inactive'}), 404

    # Check if company already owns an active license
    existing_lic = AssetLicense.query.filter_by(
        company_id=company.id,
        asset_id=asset.id,
        is_active=True
    ).first()

    if existing_lic:
        # If already owned and new domain provided, append domain
        if target_domain and target_domain not in (existing_lic.allowed_domains or []):
            domains = list(existing_lic.allowed_domains or [])
            domains.append(target_domain)
            existing_lic.allowed_domains = domains
            db.session.commit()
        return jsonify({
            'message': 'Asset already purchased. License retrieved.',
            'license': existing_lic.to_dict()
        }), 200

    # Verify credits
    required_credits = asset.credits_cost
    if company.credit_balance != -1 and company.credit_balance < required_credits:
        return jsonify({
            'error': f'Saldo de combustible IA insuficiente. Requiere {required_credits} créditos, balance actual: {company.credit_balance}.',
            'required_credits': required_credits,
            'current_balance': company.credit_balance
        }), 402

    # Deduct credits
    if company.credit_balance != -1:
        company.credit_balance -= required_credits

    # Generate Cryptographic License Key
    license_key = AssetLicense.generate_license_token(
        company_id=company.id,
        asset_slug=asset.slug,
        domain=target_domain
    )

    domains = [target_domain] if target_domain else ["*"]
    license_obj = AssetLicense(
        license_key=license_key,
        company_id=company.id,
        asset_id=asset.id,
        allowed_domains=domains,
        is_active=True,
        status_message='Active and Verified by Aikrofy Engine'
    )
    db.session.add(license_obj)

    # Register Transaction
    txn = Transaction(
        company_id=company.id,
        amount=asset.price_usd,
        currency='USD',
        description=f"Compra de Módulo en Marketplace: {asset.name}",
        service_type='asset_purchase',
        transaction_type=TransactionType.TOKEN_DEDUCTION.value if hasattr(TransactionType, 'TOKEN_DEDUCTION') else 'asset_purchase',
        credits_granted=0,
        provider=TransactionProvider.INTERNAL.value if hasattr(TransactionProvider, 'INTERNAL') else 'aikrofy',
        provider_order_id=license_key[:30],
        status=TransactionStatus.COMPLETED.value,
        channel='marketplace'
    )
    db.session.add(txn)
    db.session.commit()

    logger.info(f"Company {company.id} successfully purchased {asset.slug} -> License {license_key[:15]}...")

    return jsonify({
        'success': True,
        'message': f'¡Módulo {asset.name} adquirido exitosamente!',
        'license': license_obj.to_dict(),
        'new_credit_balance': company.credit_balance
    }), 201


@marketplace_bp.route('/assets/paypal/create-order', methods=['POST'])
@jwt_required()
def create_asset_paypal_order():
    """
    Creates a PayPal order for direct USD checkout (PayPal or Guest Card) of a modular asset.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    asset_slug = data.get('slug')
    target_domain = (data.get('domain') or '').strip().lower()

    if not asset_slug:
        return jsonify({'error': 'asset slug is required'}), 400

    asset = ModularAsset.query.filter_by(slug=asset_slug, is_active=True).first()
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404

    # Check if already owned
    existing_lic = AssetLicense.query.filter_by(company_id=company.id, asset_id=asset.id, is_active=True).first()
    if existing_lic:
        return jsonify({
            'already_owned': True,
            'message': 'Este módulo ya fue adquirido previamente.',
            'license': existing_lic.to_dict()
        }), 200

    from services.paypal_service import PayPalService
    paypal_svc = PayPalService()

    amount_val = float(asset.price_usd or 1200.0)
    order = paypal_svc.create_order(
        amount=amount_val,
        currency='USD',
        description=f"Compra de Módulo: {asset.name} ({company.name})"
    )

    if not order or not order.get('id'):
        return jsonify({'error': 'No se pudo generar la orden de PayPal'}), 500

    order_id = order.get('id')

    # Pending transaction
    txn = Transaction(
        company_id=company.id,
        amount=amount_val,
        currency='USD',
        description=f"Compra Módulo PayPal: {asset.name}",
        service_type='asset_purchase',
        transaction_type=TransactionType.SUBSCRIPTION.value if hasattr(TransactionType, 'SUBSCRIPTION') else 'asset_purchase',
        credits_granted=0,
        provider=TransactionProvider.PAYPAL.value if hasattr(TransactionProvider, 'PAYPAL') else 'paypal',
        provider_order_id=order_id,
        status=TransactionStatus.PENDING.value,
        channel='marketplace'
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        'order_id': order_id,
        'client_id': paypal_svc.client_id or os.environ.get('PAYPAL_CLIENT_ID'),
        'amount': amount_val,
        'asset_slug': asset.slug,
        'domain': target_domain
    }), 200


@marketplace_bp.route('/assets/paypal/capture-order', methods=['POST'])
@jwt_required()
def capture_asset_paypal_order():
    """
    Captures a completed PayPal order for an asset purchase and activates the license.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    order_id = data.get('order_id')
    asset_slug = data.get('slug')
    target_domain = (data.get('domain') or '').strip().lower()

    if not order_id or not asset_slug:
        return jsonify({'error': 'order_id and slug are required'}), 400

    asset = ModularAsset.query.filter_by(slug=asset_slug, is_active=True).first()
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404

    from services.paypal_service import PayPalService
    paypal_svc = PayPalService()

    capture = paypal_svc.capture_order(order_id)
    if not capture or capture.get('status') != 'COMPLETED':
        return jsonify({'error': 'No se pudo verificar o completar el cobro en PayPal'}), 400

    # Find or update transaction
    txn = Transaction.query.filter_by(provider_order_id=order_id).first()
    if txn:
        txn.status = TransactionStatus.COMPLETED.value
    else:
        txn = Transaction(
            company_id=company.id,
            amount=asset.price_usd,
            currency='USD',
            description=f"Compra Módulo PayPal Aprobado: {asset.name}",
            service_type='asset_purchase',
            transaction_type='asset_purchase',
            credits_granted=0,
            provider='paypal',
            provider_order_id=order_id,
            status=TransactionStatus.COMPLETED.value,
            channel='marketplace'
        )
        db.session.add(txn)

    # Check if license exists or create
    existing_lic = AssetLicense.query.filter_by(company_id=company.id, asset_id=asset.id, is_active=True).first()
    if not existing_lic:
        license_key = AssetLicense.generate_license_token(
            company_id=company.id,
            asset_slug=asset.slug,
            domain=target_domain
        )
        domains = [target_domain] if target_domain else ["*"]
        existing_lic = AssetLicense(
            license_key=license_key,
            company_id=company.id,
            asset_id=asset.id,
            allowed_domains=domains,
            is_active=True,
            status_message='Active and Verified via PayPal Purchase'
        )
        db.session.add(existing_lic)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'¡Pago verificado y módulo {asset.name} desbloqueado exitosamente!',
        'license': existing_lic.to_dict()
    }), 200


@marketplace_bp.route('/licenses/verify', methods=['POST'])
def verify_installation_license():
    """
    Public verification endpoint called by client VPS / Next.js blog instances.
    Enforces hardware/tenant protection.
    """
    data = request.get_json() or {}
    license_key = data.get('license_key', '').strip()
    company_id = data.get('company_id')
    asset_slug = data.get('asset_slug', 'blog_module')
    host_domain = (data.get('host_domain') or '').strip().lower()

    if not license_key or not company_id:
        return jsonify({
            'valid': False,
            'reason': 'license_key and company_id are mandatory.'
        }), 400

    try:
        cid = int(company_id)
    except ValueError:
        return jsonify({'valid': False, 'reason': 'Invalid company_id format.'}), 400

    # 1. Cryptographic HMAC check
    valid_sig, sig_msg = AssetLicense.verify_license_token(
        token=license_key,
        expected_company_id=cid,
        expected_asset_slug=asset_slug,
        check_domain=host_domain
    )

    if not valid_sig:
        logger.warning(f"License verification failed cryptographic check: {sig_msg} (Domain: {host_domain})")
        return jsonify({
            'valid': False,
            'reason': f"Fallo de integridad criptográfica: {sig_msg}"
        }), 403

    # 2. Database validation & Company subscription state
    lic = AssetLicense.query.filter_by(license_key=license_key, company_id=cid, is_active=True).first()
    if not lic:
        return jsonify({
            'valid': False,
            'reason': 'Licencia inactiva o no registrada en la base de datos de Aikrofy.'
        }), 403

    comp = Company.query.get(cid)
    if not comp:
        return jsonify({'valid': False, 'reason': 'Empresa titular no encontrada.'}), 404

    # Check allowed domains in record
    if lic.allowed_domains and "*" not in lic.allowed_domains and host_domain:
        matched = any(d in host_domain or host_domain in d for d in lic.allowed_domains)
        if not matched and host_domain not in ['localhost', '127.0.0.1']:
            return jsonify({
                'valid': False,
                'reason': f"El dominio '{host_domain}' no está autorizado para esta licencia."
            }), 403

    lic.last_verified_at = datetime.utcnow()
    db.session.commit()

    # Return platform context so blog can connect seamlessly to Aikrofy Copilot and RAG
    return jsonify({
        'valid': True,
        'company_id': comp.id,
        'company_name': comp.name,
        'agent_name': comp.agent_name or 'Krof',
        'voice_model': comp.voice_model,
        'features_unlocked': lic.asset.features if lic.asset else {},
        'verified_at': lic.last_verified_at.isoformat()
    }), 200


@marketplace_bp.route('/assets/download/<string:slug>', methods=['GET'])
@jwt_required()
def download_asset_zip(slug: str):
    """
    Downloads the pre-configured zip package for the customer's VPS,
    injecting their unique license key and company configuration file inside the zip.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    asset = ModularAsset.query.filter_by(slug=slug, is_active=True).first()
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404

    # Verify ownership
    lic = AssetLicense.query.filter_by(company_id=company.id, asset_id=asset.id, is_active=True).first()
    if not lic and company.credit_balance != -1:
        return jsonify({'error': 'Debe adquirir el módulo antes de poder descargarlo.'}), 403

    if not lic:
        # Unlimited company auto-license
        lic_key = AssetLicense.generate_license_token(company.id, asset.slug, "*")
        lic = AssetLicense(
            license_key=lic_key,
            company_id=company.id,
            asset_id=asset.id,
            allowed_domains=["*"],
            is_active=True
        )
        db.session.add(lic)
        db.session.commit()

    lic.downloads_count = (lic.downloads_count or 0) + 1
    db.session.commit()

    # Generate dynamic client installer bundle in memory
    from fastapi.responses import Response
    zip_buffer = io.BytesIO()

    # Pre-populate dynamic configuration
    env_content = f"""# Aikrofy Modular Blog Configuration
# Auto-generated for {company.name} (ID: {company.id})
AIKROFY_COMPANY_ID={company.id}
AIKROFY_LICENSE_KEY={lic.license_key}
AIKROFY_API_URL=https://aikrofy.com
MEDIA_SUITE_URL=https://media.weblifetech.com
PORT=3020
NODE_ENV=production
"""
    readme_content = f"""# Aikrofy Native Modular Blog — {company.name}

Instrucciones de Despliegue en tu VPS:
1. Extrae este paquete en tu servidor VPS:
   tar -xzf o unzip aikrofy-blog-module.zip
2. Ejecuta:
   npm install
   npm run build
   pm2 start npm --name "{company.name.lower().replace(' ', '-')}-blog" -- start -- -p 3020
3. Apunta tu Nginx o proxy inverso a http://127.0.0.1:3020

Tu Licencia Cifrada Única:
{lic.license_key}

Soporte y Copiloto:
El módulo se sincroniza de forma nativa con tu copiloto Krof y con WhatsApp.
"""

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('.env.production', env_content)
        zf.writestr('README_VPS.md', readme_content)
        # We also reference the standalone template directory
        template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'blog-template-blank'))
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                # Skip node_modules and build dirs
                if 'node_modules' in root or '.next' in root or '.git' in root:
                    continue
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, template_dir)
                    zf.write(full_path, arcname=rel_path)

    zip_buffer.seek(0)
    filename = f"aikrofy-{asset.slug}-v{asset.version}-{company.id}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type='application/zip',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


def ensure_default_assets():
    """Seeds default modular assets if not present."""
    try:
        blog_asset = ModularAsset.query.filter_by(slug='blog_module').first()
        if not blog_asset:
            blog_asset = ModularAsset(
                slug='blog_module',
                name='Módulo de Blog Agéntico Ultra-SEO & Canvas',
                description='Plantilla desacoplada en Next.js con arquitectura natural de cola larga, navegación SPA instantánea sin recargas, copiloto Krof en CMS y widget interactivo de captación en frontend.',
                asset_type=AssetType.BLOG_MODULE,
                version='1.0.0',
                price_usd=1200.0,
                credits_cost=120000,
                zip_filename='aikrofy-blog-module.zip',
                features={
                    'seo_long_tail': True,
                    'copilot_voice_whatsapp': True,
                    'canvas_drag_drop': True,
                    'mediasuite_integration': True,
                    'client_vps_storage': True,
                    'frontend_sales_widget': True
                }
            )
            db.session.add(blog_asset)

        ecom_asset = ModularAsset.query.filter_by(slug='ecommerce_module').first()
        if not ecom_asset:
            ecom_asset = ModularAsset(
                slug='ecommerce_module',
                name='Módulo de eCommerce Agéntico Headless',
                description='Arquitectura modular desacoplada para catálogo interactivo, carritos autónomos y pasarelas de pago sincronizadas con WhatsApp.',
                asset_type=AssetType.ECOMMERCE_MODULE,
                version='1.0.0',
                price_usd=79.0,
                credits_cost=800,
                zip_filename='aikrofy-ecommerce-module.zip',
                features={
                    'voice_catalog_search': True,
                    'inventory_sync': True,
                    'dynamic_payment_links': True
                }
            )
            db.session.add(ecom_asset)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.warning(f"Failed to ensure default modular assets: {e}")
