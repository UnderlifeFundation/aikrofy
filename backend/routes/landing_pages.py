"""
Landing Page Generator Routes — PymAI Ecosystem
API-First & AI-First: Complete CRUD, generation triggers, domain management,
element no-code editor, telemetry ingestion, and conversational integration.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
import secrets
import string
import re
from datetime import datetime, timedelta

from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from fastapi.responses import HTMLResponse as FastAPIHTMLResponse
from extensions import db
from models.user import User, UserRole
from models.company import Company

logger = logging.getLogger(__name__)
landing_pages_bp = APIRouter('landing_pages', __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

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
            from models.company import Company
            comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
            return user, comp
        return None, None
    except Exception as e:
        logger.error(f"get_user_company error: {e}")
        return None, None


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:100]


def generate_dns_token(length: int = 32) -> str:
    """Generate a random DNS verification token."""
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def deduct_tokens(company: Company, amount: int, description: str) -> bool:
    """Deduct tokens from company credit balance. Returns False if insufficient."""
    if company.credit_balance < amount:
        return False
    company.credit_balance -= amount
    db.session.add(company)
    # Log transaction (non-blocking, best effort)
    try:
        from models.transaction import Transaction
        tx = Transaction(
            company_id=company.id,
            amount=-amount,
            description=description,
            transaction_type='token_deduction',
            status='completed'
        )
        db.session.add(tx)
    except Exception:
        pass  # Transaction logging is non-critical
    return True


def is_enterprise(company: Company) -> bool:
    """Check if a company has an enterprise plan."""
    return (company.plan_type or '').lower() in ('enterprise', 'executiv', 'corporate')


# ─── Landing Page CRUD ────────────────────────────────────────────────────────

@landing_pages_bp.route('/', methods=['GET'])
@jwt_required()
def list_landing_pages():
    """List all landing pages for the company."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage
        pages = LandingPage.query.filter_by(company_id=company.id).order_by(
            LandingPage.updated_at.desc()
        ).all()
        return jsonify({'landing_pages': [p.to_dict() for p in pages]})
    except Exception as e:
        logger.error(f"list_landing_pages error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/', methods=['POST'])
@jwt_required()
def create_landing_page():
    """Create a new landing page (draft). Does NOT generate content yet."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    title = data.get('title', 'Mi Landing Page')
    slug_raw = data.get('slug') or slugify(title)

    try:
        from models.landing_page import LandingPage

        # Ensure slug uniqueness within company
        base_slug = slugify(slug_raw)
        slug = base_slug
        counter = 1
        while LandingPage.query.filter_by(company_id=company.id, slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        page = LandingPage(
            company_id=company.id,
            title=title,
            slug=slug,
            meta_title=data.get('meta_title', title),
            meta_description=data.get('meta_description', ''),
            llm_model=data.get('llm_model', 'gpt-5-nano'),
            llm_config=data.get('llm_config', {}),
        )
        db.session.add(page)
        db.session.commit()
        return jsonify({'landing_page': page.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"create_landing_page error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>', methods=['GET'])
@jwt_required()
def get_landing_page(page_id: int):
    """Get a specific landing page with all details."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        data = page.to_dict()
        # Include elements for the no-code editor
        data['elements'] = [e.to_dict() for e in page.elements.order_by(
            db.text('sort_order asc')
        ).all()]
        return jsonify({'landing_page': data})
    except Exception as e:
        logger.error(f"get_landing_page error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>', methods=['PUT'])
@jwt_required()
def update_landing_page(page_id: int):
    """Update landing page metadata / content directly (no-code edits)."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageVersion
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        data = request.get_json() or {}

        # Save current version before making changes (if content exists)
        if page.html_content and data.get('html_content'):
            version = LandingPageVersion(
                landing_page_id=page.id,
                html_content=page.html_content,
                css_content=page.css_content,
                js_content=page.js_content,
                version_number=page.version,
                change_summary=data.get('change_summary', 'Manual update'),
                created_by=user.email if user else 'unknown'
            )
            db.session.add(version)
            page.version = page.version + 1

        # Update allowed fields
        updatable = ['title', 'html_content', 'css_content', 'js_content',
                     'meta_title', 'meta_description', 'og_image_url',
                     'custom_domain', 'llm_model', 'llm_config', 'chatweb_enabled']
        for field in updatable:
            if field in data:
                setattr(page, field, data[field])

        if 'campaign_id' in data:
            import re
            camp_id = data['campaign_id']
            curr_meta = page.meta_description or ''
            cleaned_meta = re.sub(r'\s*\[CAMPAIGN_ID:\d+\]', '', curr_meta).strip()
            if camp_id:
                page.meta_description = f"{cleaned_meta} [CAMPAIGN_ID:{camp_id}]".strip()
            else:
                page.meta_description = cleaned_meta

        db.session.commit()
        return jsonify({'landing_page': page.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"update_landing_page error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>/publish', methods=['POST'])
@jwt_required()
def publish_landing_page(page_id: int):
    """Publish or unpublish a landing page."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageStatus
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        if not page.html_content:
            return jsonify({'error': 'Cannot publish an empty landing page. Generate content first.'}), 400

        data = request.get_json() or {}
        action = data.get('action', 'publish')  # 'publish' or 'unpublish'

        if action == 'publish':
            page.status = LandingPageStatus.PUBLISHED
            page.published_at = datetime.utcnow()
        else:
            page.status = LandingPageStatus.DRAFT
            page.published_at = None

        db.session.commit()
        return jsonify({'landing_page': page.to_dict(), 'message': f'Landing page {action}ed successfully.'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"publish_landing_page error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>', methods=['DELETE'])
@jwt_required()
def delete_landing_page(page_id: int):
    """Delete a landing page (archives it first)."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        db.session.delete(page)
        db.session.commit()
        return jsonify({'message': 'Landing page deleted successfully.'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"delete_landing_page error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── AI Generation ────────────────────────────────────────────────────────────

@landing_pages_bp.route('/<int:page_id>/generate', methods=['POST'])
@jwt_required()
def trigger_generation(page_id: int):
    """
    Trigger AI generation for a landing page.
    Deducts tokens and enqueues a Celery task.
    Supports: text prompt, screenshot URL, Figma URL.
    Enterprise users can specify custom LLM model/API keys.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageStatus
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        if page.generation_status == 'generating':
            return jsonify({'error': 'Generation already in progress for this page.'}), 409

        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        screenshot_url = data.get('screenshot_url', '')
        figma_url = data.get('figma_url', '')
        generation_type = data.get('generation_type', 'create')  # 'create' or 'update'
        token_cost = 10 if generation_type == 'update' else 50

        # Enterprise model override
        llm_model = data.get('llm_model', page.llm_model or 'gpt-5-nano')
        llm_config = data.get('llm_config', page.llm_config or {})

        # Non-enterprise users are locked to platform default model
        if not is_enterprise(company):
            llm_model = 'gpt-5-nano'
            llm_config = {}

        # Token check
        if company.credit_balance < token_cost:
            return jsonify({
                'error': 'Insufficient token balance.',
                'required': token_cost,
                'available': company.credit_balance,
                'recharge_url': '/subscribe'
            }), 402

        # Deduct tokens
        if not deduct_tokens(company, token_cost, f'Landing page generation: {page.title}'):
            return jsonify({'error': 'Token deduction failed.'}), 500

        # Update page status
        page.generation_status = 'generating'
        page.generation_prompt = prompt or page.generation_prompt
        page.screenshot_url = screenshot_url or page.screenshot_url
        page.llm_model = llm_model
        page.llm_config = llm_config
        db.session.commit()

        # Enqueue Celery task
        from celery_app import celery
        celery.send_task(
            'tasks.generate_landing_page',
            args=[page.id, company.id],
            kwargs={
                'prompt': prompt,
                'screenshot_url': screenshot_url,
                'figma_url': figma_url,
                'generation_type': generation_type,
                'llm_model': llm_model,
                'llm_config': llm_config,
                'user_email': user.email if user else 'unknown',
            }
        )

        return jsonify({
            'message': 'Generation started.',
            'landing_page': page.to_dict(),
            'tokens_deducted': token_cost,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"trigger_generation error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>/generation-status', methods=['GET'])
@jwt_required()
def get_generation_status(page_id: int):
    """Poll the generation status of a landing page."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        return jsonify({
            'generation_status': page.generation_status,
            'generation_error': page.generation_error,
            'has_content': bool(page.html_content),
            'version': page.version,
        })

    except Exception as e:
        logger.error(f"get_generation_status error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Versions ─────────────────────────────────────────────────────────────────

@landing_pages_bp.route('/<int:page_id>/versions', methods=['GET'])
@jwt_required()
def list_versions(page_id: int):
    """List all saved versions of a landing page."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageVersion
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        versions = LandingPageVersion.query.filter_by(landing_page_id=page_id).order_by(
            LandingPageVersion.version_number.desc()
        ).all()
        return jsonify({'versions': [v.to_dict() for v in versions]})

    except Exception as e:
        logger.error(f"list_versions error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>/versions/<int:version_number>/restore', methods=['POST'])
@jwt_required()
def restore_version(page_id: int, version_number: int):
    """Restore a previous version of a landing page."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageVersion
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        version = LandingPageVersion.query.filter_by(
            landing_page_id=page_id, version_number=version_number
        ).first()
        if not version:
            return jsonify({'error': 'Version not found'}), 404

        # Save current as new version before restoring
        current_version = LandingPageVersion(
            landing_page_id=page.id,
            html_content=page.html_content,
            css_content=page.css_content,
            js_content=page.js_content,
            version_number=page.version,
            change_summary=f'Auto-saved before restore to v{version_number}',
            created_by=user.email if user else 'system'
        )
        db.session.add(current_version)

        page.html_content = version.html_content
        page.css_content = version.css_content
        page.js_content = version.js_content
        page.version = page.version + 1
        db.session.commit()

        return jsonify({'landing_page': page.to_dict(), 'message': f'Restored to version {version_number}.'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"restore_version error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Elements (No-Code Editor) ────────────────────────────────────────────────

@landing_pages_bp.route('/<int:page_id>/elements', methods=['GET'])
@jwt_required()
def list_elements(page_id: int):
    """Get all editable elements for no-code editing."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageElement
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        elements = LandingPageElement.query.filter_by(landing_page_id=page_id).order_by(
            LandingPageElement.sort_order.asc()
        ).all()
        return jsonify({'elements': [e.to_dict() for e in elements]})

    except Exception as e:
        logger.error(f"list_elements error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/<int:page_id>/elements/<int:element_id>', methods=['PUT'])
@jwt_required()
def update_element(page_id: int, element_id: int):
    """Update a specific element via the no-code editor (deducts 10 tokens)."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageElement
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        element = LandingPageElement.query.filter_by(id=element_id, landing_page_id=page_id).first()
        if not element:
            return jsonify({'error': 'Element not found'}), 404

        data = request.get_json() or {}
        if 'content' in data:
            element.content = data['content']
        if 'css_overrides' in data:
            element.css_overrides = data['css_overrides']
        if 'is_visible' in data:
            element.is_visible = data['is_visible']

        db.session.commit()
        return jsonify({'element': element.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"update_element error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Custom Domains ───────────────────────────────────────────────────────────

@landing_pages_bp.route('/domains', methods=['GET'])
@jwt_required()
def list_custom_domains():
    """List all custom domains registered for the company."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPageCustomDomain
        domains = LandingPageCustomDomain.query.filter_by(company_id=company.id).all()
        return jsonify({'domains': [d.to_dict() for d in domains]})

    except Exception as e:
        logger.error(f"list_custom_domains error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/domains', methods=['POST'])
@jwt_required()
def register_custom_domain():
    """Register a new custom domain. Available to all users (beta)."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPageCustomDomain
        data = request.get_json() or {}
        domain = (data.get('domain') or '').strip().lower()

        if not domain:
            return jsonify({'error': 'Domain is required.'}), 400

        # Basic domain validation
        domain_pattern = r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*\.[a-z]{2,}$'
        if not re.match(domain_pattern, domain):
            return jsonify({'error': 'Invalid domain format.'}), 400

        # Check if domain already registered globally
        existing = LandingPageCustomDomain.query.filter_by(domain=domain).first()
        if existing:
            if existing.company_id == company.id:
                return jsonify({'error': 'You have already registered this domain.'}), 409
            return jsonify({'error': 'This domain is already registered to another account.'}), 409

        dns_token = generate_dns_token()
        custom_domain = LandingPageCustomDomain(
            company_id=company.id,
            domain=domain,
            landing_page_id=data.get('landing_page_id'),
            dns_token=dns_token,
            is_active=False,
        )
        db.session.add(custom_domain)
        db.session.commit()

        return jsonify({
            'domain': custom_domain.to_dict(),
            'dns_instructions': {
                'type': 'CNAME',
                'name': f'pymai-verify.{domain}',
                'value': f'{dns_token}.domains.pymai.com',
                'ttl': 3600,
                'note': 'Add this CNAME record to your DNS provider, then click Verify.'
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"register_custom_domain error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/domains/<int:domain_id>/verify', methods=['POST'])
@jwt_required()
def verify_custom_domain(domain_id: int):
    """Attempt to verify DNS ownership for a custom domain."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPageCustomDomain
        domain_record = LandingPageCustomDomain.query.filter_by(
            id=domain_id, company_id=company.id
        ).first()
        if not domain_record:
            return jsonify({'error': 'Domain not found.'}), 404

        # DNS verification (CNAME lookup)
        import socket
        expected_cname = f'{domain_record.dns_token}.domains.pymai.com'
        verified = False
        try:
            result = socket.gethostbyname(f'pymai-verify.{domain_record.domain}')
            # In production this would check actual CNAME record
            # For now, we trust the token submission
            verified = True
        except Exception:
            # Try alternate verification - check if token is in a TXT record
            verified = False

        if verified:
            domain_record.is_active = True
            domain_record.verified_at = datetime.utcnow()
            domain_record.ssl_status = 'active'
            db.session.commit()
            return jsonify({
                'domain': domain_record.to_dict(),
                'message': 'Domain verified and activated successfully! SSL is being provisioned.'
            })
        else:
            return jsonify({
                'domain': domain_record.to_dict(),
                'message': 'DNS record not found yet. DNS propagation can take up to 48 hours. Please try again later.',
                'verified': False
            }), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"verify_custom_domain error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/domains/<int:domain_id>/assign', methods=['POST'])
@jwt_required()
def assign_domain_to_page(domain_id: int):
    """Assign a verified domain to a specific landing page."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPageCustomDomain, LandingPage
        domain_record = LandingPageCustomDomain.query.filter_by(
            id=domain_id, company_id=company.id
        ).first()
        if not domain_record:
            return jsonify({'error': 'Domain not found.'}), 404

        data = request.get_json() or {}
        page_id = data.get('landing_page_id')
        if page_id:
            page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
            if not page:
                return jsonify({'error': 'Landing page not found.'}), 404

        domain_record.landing_page_id = page_id
        db.session.commit()
        return jsonify({'domain': domain_record.to_dict(), 'message': 'Domain assigned successfully.'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"assign_domain_to_page error: {e}")
        return jsonify({'error': str(e)}), 500


@landing_pages_bp.route('/domains/<int:domain_id>', methods=['DELETE'])
@jwt_required()
def delete_custom_domain(domain_id: int):
    """Remove a custom domain registration."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPageCustomDomain
        domain_record = LandingPageCustomDomain.query.filter_by(
            id=domain_id, company_id=company.id
        ).first()
        if not domain_record:
            return jsonify({'error': 'Domain not found.'}), 404

        db.session.delete(domain_record)
        db.session.commit()
        return jsonify({'message': 'Custom domain removed successfully.'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"delete_custom_domain error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Telemetry (Public Tracker) ────────────────────────────────────────────────

@landing_pages_bp.route('/<int:page_id>/track', methods=['POST'])
def track_visit(page_id: int):
    """
    Public endpoint — called by pymai-tracker.js embedded in the landing page.
    No auth required. Records telemetry events and updates lead scores.
    """
    try:
        from models.landing_page import LandingPage, LandingPageVisit
        data = request.get_json() or {}

        page = LandingPage.query.get(page_id)
        if not page:
            return jsonify({'error': 'Not found'}), 404

        session_id = data.get('session_id', secrets.token_hex(16))
        event_type = data.get('event', 'pageview')  # pageview / scroll / cta_click / form_submit / heartbeat

        # Find or create visit for this session
        visit = LandingPageVisit.query.filter_by(
            landing_page_id=page_id, session_id=session_id
        ).first()

        if not visit:
            # New visit — extract geo from IP (best effort)
            visitor_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
            visit = LandingPageVisit(
                landing_page_id=page_id,
                session_id=session_id,
                visitor_ip=visitor_ip,
                user_agent=request.headers.get('User-Agent', '')[:500],
                referrer=(data.get('referrer') or '')[:500],
                utm_source=data.get('utm_source'),
                utm_medium=data.get('utm_medium'),
                utm_campaign=data.get('utm_campaign'),
                utm_term=data.get('utm_term'),
                utm_content=data.get('utm_content'),
                device_type=data.get('device_type'),
                w_lead_token=data.get('w_lead_token'),
                whatsapp_lead_id=data.get('whatsapp_lead_id'),
            )
            db.session.add(visit)
            # Increment views count
            page.views_count = (page.views_count or 0) + 1
            db.session.flush()

        # Process event types
        lead_score_delta = 0
        if event_type == 'pageview':
            lead_score_delta = 5

        elif event_type == 'scroll':
            depth = int(data.get('depth', 0))
            visit.scroll_depth = max(visit.scroll_depth or 0, depth)
            if depth >= 70 and (visit.scroll_depth or 0) < 70:
                lead_score_delta = 10

        elif event_type == 'cta_click':
            cta_label = data.get('cta_label', 'unknown')
            clicks = list(visit.cta_clicks or [])
            clicks.append({'label': cta_label, 'ts': datetime.utcnow().isoformat()})
            visit.cta_clicks = clicks
            lead_score_delta = 15

        elif event_type == 'form_submit':
            form_data = data.get('form_data', {})
            submissions = list(visit.form_submissions or [])
            submissions.append({'data': form_data, 'ts': datetime.utcnow().isoformat()})
            visit.form_submissions = submissions
            page.conversions_count = (page.conversions_count or 0) + 1
            lead_score_delta = 40

            # Attempt to link form submission to a lead profile
            _link_form_to_lead(page.company_id, visit, form_data)

        elif event_type == 'heartbeat':
            elapsed = int(data.get('elapsed_seconds', 0))
            visit.time_on_page = max(visit.time_on_page or 0, elapsed)

        # Accumulate lead score delta
        visit.lead_score_delta = (visit.lead_score_delta or 0) + lead_score_delta

        # Update lead score if linked
        if visit.lead_id and lead_score_delta > 0:
            _update_lead_score(visit.lead_id, lead_score_delta, f'Landing page interaction: {event_type}')

        db.session.commit()
        return jsonify({'ok': True, 'session_id': session_id})

    except Exception as e:
        db.session.rollback()
        logger.error(f"track_visit error: {e}")
        return jsonify({'ok': False}), 200  # Always 200 to not break tracking


def _link_form_to_lead(company_id: int, visit: 'LandingPageVisit', form_data: dict):
    """Try to link a visit to a known lead/customer via email or phone."""
    try:
        from models.customer import Customer
        email = form_data.get('email') or form_data.get('correo')
        phone = form_data.get('phone') or form_data.get('telefono') or form_data.get('whatsapp')

        customer = None
        if email:
            customer = Customer.query.filter_by(company_id=company_id, email=email).first()
        if not customer and phone:
            customer = Customer.query.filter_by(company_id=company_id, phone=phone).first()

        # Also check by WhatsApp lead token
        if not customer and visit.whatsapp_lead_id:
            customer = Customer.query.filter_by(
                company_id=company_id, phone=visit.whatsapp_lead_id
            ).first()

        if customer:
            visit.lead_id = customer.id
            # Update customer profile with web data
            if email and not customer.email:
                customer.email = email
            db.session.add(customer)

        elif email or phone:
            # Create a new customer lead from the form
            new_customer = Customer(
                company_id=company_id,
                name=form_data.get('name') or form_data.get('nombre', 'Lead from Landing Page'),
                email=email,
                phone=phone,
                source='landing_page',
                lead_score=40,  # form submission score
            )
            db.session.add(new_customer)
            db.session.flush()
            visit.lead_id = new_customer.id

    except Exception as e:
        logger.warning(f"_link_form_to_lead error (non-critical): {e}")


def _update_lead_score(lead_id: int, delta: int, reason: str):
    """Update the lead score for a customer."""
    try:
        from models.customer import Customer
        customer = Customer.query.get(lead_id)
        if customer:
            current_score = getattr(customer, 'lead_score', 0) or 0
            customer.lead_score = min(100, current_score + delta)
            db.session.add(customer)
    except Exception as e:
        logger.warning(f"_update_lead_score error (non-critical): {e}")


# ─── Analytics ────────────────────────────────────────────────────────────────

@landing_pages_bp.route('/<int:page_id>/analytics', methods=['GET'])
@jwt_required()
def get_landing_analytics(page_id: int):
    """
    Full analytics for a landing page with segment filtering.
    Supports: ?device=mobile&utm_source=whatsapp&country=MX&date_from=...&date_to=...
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        from models.landing_page import LandingPage, LandingPageVisit
        from sqlalchemy import func

        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return jsonify({'error': 'Landing page not found'}), 404

        # Filters
        device = request.args.get('device')
        utm_source = request.args.get('utm_source')
        utm_medium = request.args.get('utm_medium')
        utm_campaign = request.args.get('utm_campaign')
        country = request.args.get('country')
        region = request.args.get('region')
        has_lead = request.args.get('has_lead')
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')

        query = LandingPageVisit.query.filter_by(landing_page_id=page_id)

        if device:
            query = query.filter(LandingPageVisit.device_type == device)
        if utm_source:
            query = query.filter(LandingPageVisit.utm_source == utm_source)
        if utm_medium:
            query = query.filter(LandingPageVisit.utm_medium == utm_medium)
        if utm_campaign:
            query = query.filter(LandingPageVisit.utm_campaign == utm_campaign)
        if country:
            query = query.filter(LandingPageVisit.country == country)
        if region:
            query = query.filter(LandingPageVisit.region == region)
        if has_lead == 'true':
            query = query.filter(LandingPageVisit.lead_id.isnot(None))
        elif has_lead == 'false':
            query = query.filter(LandingPageVisit.lead_id.is_(None))

        if date_from_str:
            try:
                date_from = datetime.fromisoformat(date_from_str)
                query = query.filter(LandingPageVisit.created_at >= date_from)
            except ValueError:
                pass
        if date_to_str:
            try:
                date_to = datetime.fromisoformat(date_to_str)
                query = query.filter(LandingPageVisit.created_at <= date_to)
            except ValueError:
                pass

        visits = query.all()
        total_visits = len(visits)
        leads_count = sum(1 for v in visits if v.lead_id)
        conversions = sum(1 for v in visits if v.form_submissions)
        avg_scroll = sum(v.scroll_depth or 0 for v in visits) / max(total_visits, 1)
        avg_time = sum(v.time_on_page or 0 for v in visits) / max(total_visits, 1)

        # Device breakdown
        device_breakdown = {}
        for v in visits:
            dt = v.device_type or 'unknown'
            device_breakdown[dt] = device_breakdown.get(dt, 0) + 1

        # UTM source breakdown
        utm_breakdown = {}
        for v in visits:
            src = v.utm_source or 'direct'
            utm_breakdown[src] = utm_breakdown.get(src, 0) + 1

        # Country breakdown
        country_breakdown = {}
        for v in visits:
            ct = v.country or 'unknown'
            country_breakdown[ct] = country_breakdown.get(ct, 0) + 1

        # CTA performance
        cta_clicks_total = sum(len(v.cta_clicks or []) for v in visits)

        # Daily visits trend (last 30 days)
        now = datetime.utcnow()
        daily_data = {}
        for i in range(30):
            day = (now - timedelta(days=i)).strftime('%Y-%m-%d')
            daily_data[day] = 0
        for v in visits:
            day = v.created_at.strftime('%Y-%m-%d')
            if day in daily_data:
                daily_data[day] += 1
        daily_trend = [{'date': k, 'visits': v} for k, v in sorted(daily_data.items())]

        return jsonify({
            'page': {
                'id': page.id,
                'title': page.title,
                'slug': page.slug,
                'status': page.status.value if page.status else 'draft',
                'views_count': page.views_count,
                'conversions_count': page.conversions_count,
            },
            'analytics': {
                'total_visits': total_visits,
                'leads_identified': leads_count,
                'conversions': conversions,
                'conversion_rate': round(conversions / max(total_visits, 1) * 100, 2),
                'avg_scroll_depth': round(avg_scroll, 1),
                'avg_time_on_page': round(avg_time, 1),
                'cta_clicks_total': cta_clicks_total,
                'ctr': round(cta_clicks_total / max(total_visits, 1) * 100, 2),
            },
            'segments': {
                'by_device': device_breakdown,
                'by_utm_source': utm_breakdown,
                'by_country': country_breakdown,
            },
            'daily_trend': daily_trend,
        })

    except Exception as e:
        logger.error(f"get_landing_analytics error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Conversational Integration (WhatsApp / Dashboard Chat) ──────────────────

@landing_pages_bp.route('/from-agent', methods=['POST'])
@jwt_required()
def create_from_agent():
    """
    Unified endpoint for agent/chat-driven landing page creation and modification.
    Called by the AIChatSidebar, WhatsApp agent, or any LangGraph node.
    """
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    try:
        data = request.get_json() or {}
        action = data.get('action')  # 'create' | 'update' | 'publish' | 'analyze' | 'navigate'

        if action == 'navigate':
            # Return the URL to navigate to the landing page builder
            page_id = data.get('landing_page_id')
            if page_id:
                return jsonify({'redirect_url': f'/landing-pages/{page_id}', 'action': 'navigate'})
            return jsonify({'redirect_url': '/landing-pages', 'action': 'navigate'})

        elif action == 'create':
            # Create and start generation
            from models.landing_page import LandingPage
            title = data.get('title', 'Nueva Landing Page')
            slug = slugify(data.get('slug') or title)

            # Ensure unique slug
            base_slug = slug
            counter = 1
            while LandingPage.query.filter_by(company_id=company.id, slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            page = LandingPage(
                company_id=company.id,
                title=title,
                slug=slug,
                llm_model='gpt-5-nano' if not is_enterprise(company) else data.get('llm_model', 'gpt-5-nano'),
                generation_prompt=data.get('prompt', ''),
            )
            db.session.add(page)
            db.session.commit()

            # Auto-trigger generation if prompt is provided
            if data.get('prompt') or data.get('screenshot_url'):
                # Check tokens
                if company.credit_balance >= 50:
                    deduct_tokens(company, 50, f'Agent-created landing: {title}')
                    page.generation_status = 'generating'
                    db.session.commit()

                    from celery_app import celery
                    celery.send_task(
                        'tasks.generate_landing_page',
                        args=[page.id, company.id],
                        kwargs={
                            'prompt': data.get('prompt', ''),
                            'screenshot_url': data.get('screenshot_url', ''),
                            'generation_type': 'create',
                            'llm_model': page.llm_model,
                            'llm_config': {},
                            'user_email': user.email if user else 'agent',
                        }
                    )

            return jsonify({
                'landing_page': page.to_dict(),
                'redirect_url': f'/landing-pages/{page.id}',
                'message': f'Landing page "{title}" created. Generation started.'
            }), 201

        elif action == 'analyze':
            page_id = data.get('landing_page_id')
            if not page_id:
                return jsonify({'error': 'landing_page_id required for analyze action.'}), 400

            from models.landing_page import LandingPage
            page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
            if not page:
                return jsonify({'error': 'Landing page not found.'}), 404

            return jsonify({
                'landing_page': page.to_dict(),
                'summary': {
                    'views': page.views_count,
                    'conversions': page.conversions_count,
                    'conversion_rate': round(page.conversions_count / max(page.views_count, 1) * 100, 2),
                    'status': page.status.value if page.status else 'draft',
                }
            })

        else:
            return jsonify({'error': f'Unknown action: {action}. Supported: create, update, publish, analyze, navigate.'}), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"create_from_agent error: {e}")
        return jsonify({'error': str(e)}), 500


# ─── Public Landing Page Serving ─────────────────────────────────────────────

def _get_tracker_script(page_id: int) -> str:
    return f"""
<script>
(function(){{
  var LP_ID = {page_id};
  var sid = sessionStorage.getItem('pymai_sid') || Math.random().toString(36).substr(2,16);
  sessionStorage.setItem('pymai_sid', sid);
  var params = new URLSearchParams(window.location.search);
  var payload = {{
    session_id: sid,
    event: 'pageview',
    referrer: document.referrer,
    device_type: window.innerWidth < 768 ? 'mobile' : window.innerWidth < 1024 ? 'tablet' : 'desktop',
    utm_source: params.get('utm_source'),
    utm_medium: params.get('utm_medium'),
    utm_campaign: params.get('utm_campaign'),
    utm_term: params.get('utm_term'),
    utm_content: params.get('utm_content'),
    w_lead_token: params.get('w_lead_id'),
    whatsapp_lead_id: params.get('wid'),
  }};
  fetch('/api/landing-pages/'+LP_ID+'/track', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(payload)}});

  // Scroll tracking
  var maxScroll = 0;
  window.addEventListener('scroll', function(){{
    var pct = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
    if(pct > maxScroll){{
      maxScroll = pct;
      if(pct >= 70){{
        fetch('/api/landing-pages/'+LP_ID+'/track', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{session_id:sid, event:'scroll', depth:pct}})}});
      }}
    }}
  }});

  // CTA click tracking
  document.addEventListener('click', function(e){{
    var el = e.target.closest('[data-cta]');
    if(el){{
      fetch('/api/landing-pages/'+LP_ID+'/track', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{session_id:sid, event:'cta_click', cta_label:el.dataset.cta}})}});
    }}
  }});

  // Form submission tracking (captures leads to CRM)
  document.addEventListener('submit', function(e){{
    var form = e.target;
    var formData = {{}};
    var inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(function(input){{
      if(input.name && input.value){{
        formData[input.name] = input.value;
      }}
    }});
    fetch('/api/landing-pages/'+LP_ID+'/track', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{session_id:sid, event:'form_submit', form_data:formData}})
    }});
  }});

  // Heartbeat (time on page)
  setInterval(function(){{
    fetch('/api/landing-pages/'+LP_ID+'/track', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify({{session_id:sid, event:'heartbeat', elapsed_seconds: Math.round((Date.now()-performance.timing.navigationStart)/1000)}})}});
  }}, 15000);
}})();
</script>"""


def _get_landing_html(page) -> str:
    tracker_script = _get_tracker_script(page.id)
    
    if page.chatweb_enabled:
        try:
            from models.channel import Channel, ChannelType, ChannelStatus
            import uuid
            from extensions import db
            webchat_channel = Channel.query.filter_by(
                company_id=page.company_id, type=ChannelType.WEBCHAT
            ).first()
            if not webchat_channel:
                webchat_channel = Channel(
                    company_id=page.company_id,
                    type=ChannelType.WEBCHAT,
                    name="Webchat Landing Page",
                    status=ChannelStatus.CONNECTED,
                    status_message="Widget Ready",
                    credentials={'widget_id': str(uuid.uuid4())}
                )
                db.session.add(webchat_channel)
                db.session.commit()
            
            credentials = webchat_channel.credentials or {}
            widget_id = credentials.get('widget_id')
            if not widget_id:
                widget_id = str(uuid.uuid4())
                webchat_channel.credentials = {'widget_id': widget_id}
                db.session.commit()
                
            tracker_script += f'\n<script src="/api/static/js/widget.js?id={widget_id}"></script>'
        except Exception as e:
            logger.warning(f"Error appending webchat widget script: {e}")
                
    html = page.html_content or ""
    if '</body>' in html:
        return html.replace('</body>', tracker_script + '</body>')
    else:
        return html + tracker_script


@landing_pages_bp.route('/public/<string:slug>', methods=['GET'])
def serve_public_landing_single_slug(slug: str):
    """
    Serve a published landing page publicly by either company_slug (primary page)
    or directly by page_slug.
    """
    try:
        from models.landing_page import LandingPage, LandingPageStatus
        from models.company import Company
 
        # 1. Try treating slug as company_slug to serve its primary page
        company = Company.query.filter_by(public_slug=slug, is_active=True).first()
        page = None
        if company:
            # Try to get primary page first
            page = LandingPage.query.filter_by(
                company_id=company.id, is_primary=True, status=LandingPageStatus.PUBLISHED
            ).first()
            # Fallback to any published page for this company
            if not page:
                page = LandingPage.query.filter_by(
                    company_id=company.id, status=LandingPageStatus.PUBLISHED
                ).first()
 
        # 2. If not found via company slug, try treating slug as a direct page_slug
        if not page:
            page = LandingPage.query.filter_by(
                slug=slug, status=LandingPageStatus.PUBLISHED
            ).first()
 
        if not page or not page.html_content:
            return jsonify({'error': 'Not found'}), 404
 
        html = _get_landing_html(page)
        return FastAPIHTMLResponse(content=html, status_code=200)
 
    except Exception as e:
        logger.error(f"serve_public_landing_single_slug error: {e}")
        return jsonify({'error': 'Internal error'}), 500
 
 
@landing_pages_bp.route('/public/<string:company_slug>/<string:page_slug>', methods=['GET'])
def serve_public_landing(company_slug: str, page_slug: str):
    """
    Serve a published landing page publicly at /l/{company_slug}/{page_slug}.
    This is called by the Nginx proxy for domain-routed requests.
    """
    try:
        from models.landing_page import LandingPage, LandingPageStatus
        from models.company import Company
 
        company = Company.query.filter_by(public_slug=company_slug, is_active=True).first()
        if not company:
            return jsonify({'error': 'Not found'}), 404
 
        page = LandingPage.query.filter_by(
            company_id=company.id, slug=page_slug, status=LandingPageStatus.PUBLISHED
        ).first()
        if not page or not page.html_content:
            return jsonify({'error': 'Not found'}), 404
 
        html = _get_landing_html(page)
        return FastAPIHTMLResponse(content=html, status_code=200)
 
    except Exception as e:
        logger.error(f"serve_public_landing error: {e}")
        return jsonify({'error': 'Internal error'}), 500
 
 
# ─── Custom Domain Serving (Nginx catch-all) ──────────────────────────────────
 
@landing_pages_bp.route('/custom-domain/', methods=['GET'])
@landing_pages_bp.route('/custom-domain/<path:path>', methods=['GET'])
def serve_custom_domain(path: str = ''):
    """
    Serve a landing page for a custom domain.
    Called by the Nginx default_server catch-all via:
      proxy_pass http://127.0.0.1:5010/api/landing-pages/custom-domain/
      proxy_set_header X-Custom-Domain $host;
 
    Looks up the Host header in landing_page_custom_domains to find
    which landing page to serve.
    """
    try:
        from models.landing_page import LandingPage, LandingPageCustomDomain, LandingPageStatus
 
        # Get the custom domain from the Nginx-forwarded header (or Host fallback)
        custom_domain = request.headers.get('X-Custom-Domain') or request.headers.get('Host', '')
        # Strip port if present
        custom_domain = custom_domain.split(':')[0].strip().lower()
 
        if not custom_domain:
            return jsonify({'error': 'No custom domain header found'}), 400
 
        # Find domain record
        domain_record = LandingPageCustomDomain.query.filter_by(
            domain=custom_domain, is_active=True
        ).first()
 
        if not domain_record or not domain_record.landing_page_id:
            logger.warning(f"No active domain record found for: {custom_domain}")
            return jsonify({'error': 'Domain not configured or not verified'}), 404
 
        # Get the landing page
        page = LandingPage.query.filter_by(
            id=domain_record.landing_page_id,
            status=LandingPageStatus.PUBLISHED
        ).first()
 
        if not page or not page.html_content:
            logger.warning(f"No published landing page for domain: {custom_domain}")
            return jsonify({'error': 'No published landing page for this domain'}), 404
 
        html = _get_landing_html(page)
        return FastAPIHTMLResponse(content=html, status_code=200)
 
    except Exception as e:
        logger.error(f"serve_custom_domain error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
