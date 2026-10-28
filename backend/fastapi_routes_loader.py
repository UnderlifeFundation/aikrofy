"""
PymAI - Route Loader (FastAPI Native)
Registers all native APIRouters dynamically onto the FastAPI application instance.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging

# Import all legacy Flask blueprints (now migrated to APIRouter)
from routes.auth import auth_bp
from routes.companies import companies_bp
from routes.agents import agents_bp
from routes.channels import channels_bp
from routes.rag import rag_bp
from routes.analytics import analytics_bp
from routes.chat import chat_bp
from routes.admin import admin_bp
from routes.webhooks import webhooks_bp
from routes.customers import customers_bp
from routes.livekit_routes import livekit_bp
from routes.voice_agent_api import voice_agent_bp
from routes.employees import employees_bp
from routes.departments import departments_bp
from routes.google_auth import google_auth_bp
from routes.payments import payments_bp
from routes.ecommerce import ecommerce_bp
from routes.crm import crm_bp
from routes.billing import billing_bp
from routes.payment_gateways import payment_gateways_bp
from routes.voice import voice_bp
from routes.twilio import twilio_bp, twilio_webhooks_bp
from routes.demo import demo_bp
from routes.landing_pages import landing_pages_bp
from routes.hubspot import hubspot_router_bp
from routes.beta import beta_bp
from routes.whatsapp_templates import whatsapp_templates_bp
from routes.telemetry import telemetry_bp
from routes.marketplace import marketplace_bp
from routes.agency import agency_bp
from routes.meetings import meetings_bp
from routes.ingestion import ingestion_bp
from routes.media import media_bp
from routes.agent_hierarchy import agent_hierarchy_bp
from routes.funnel_live import funnel_live_bp
from routes.brain_events import brain_events_bp
from routes.knowledge_graph import knowledge_graph_bp
from routes.enterprise import enterprise_bp
from routes.campaign_qr import campaign_qr_bp
from routes.observatory import observatory_bp
from routes.catalog import catalog_bp
from routes.community_license import community_bp

logger = logging.getLogger(__name__)

def mount_legacy_blueprints(fastapi_app):
    """
    Mounts all native APIRouters systematically onto the FastAPI app instance.
    Replica of original routing rules from app.py.
    """
    logger.info("Mounting native APIRouters on FastAPI...")
    
    fastapi_app.include_router(auth_bp.fastapi_router, prefix='/api/auth')
    fastapi_app.include_router(telemetry_bp.fastapi_router, prefix='/api/telemetry')
    fastapi_app.include_router(beta_bp.fastapi_router, prefix='/api/beta')
    fastapi_app.include_router(companies_bp.fastapi_router, prefix='/api/companies')
    fastapi_app.include_router(agent_hierarchy_bp.fastapi_router, prefix='/api/agents')
    fastapi_app.include_router(agents_bp.fastapi_router, prefix='/api/agents')
    fastapi_app.include_router(channels_bp.fastapi_router, prefix='/api/channels')
    fastapi_app.include_router(whatsapp_templates_bp.fastapi_router, prefix='/api/whatsapp-templates')
    fastapi_app.include_router(knowledge_graph_bp.fastapi_router, prefix='/api/rag')
    fastapi_app.include_router(brain_events_bp.fastapi_router, prefix='/api/rag')
    fastapi_app.include_router(rag_bp.fastapi_router, prefix='/api/rag')
    fastapi_app.include_router(analytics_bp.fastapi_router, prefix='/api/analytics')
    fastapi_app.include_router(chat_bp.fastapi_router, prefix='/api/chat')
    fastapi_app.include_router(admin_bp.fastapi_router, prefix='/api/admin')
    fastapi_app.include_router(webhooks_bp.fastapi_router, prefix='/api/webhooks')
    fastapi_app.include_router(customers_bp.fastapi_router, prefix='/api/customers')
    fastapi_app.include_router(livekit_bp.fastapi_router, prefix=livekit_bp.url_prefix)
    fastapi_app.include_router(voice_agent_bp.fastapi_router) # No prefix, internal routes
    fastapi_app.include_router(employees_bp.fastapi_router, prefix='/api/employees')
    fastapi_app.include_router(departments_bp.fastapi_router, prefix='/api/departments')
    fastapi_app.include_router(google_auth_bp.fastapi_router, prefix=google_auth_bp.url_prefix)
    fastapi_app.include_router(payments_bp.fastapi_router, prefix='/api/payments')
    fastapi_app.include_router(ecommerce_bp.fastapi_router, prefix='/api/ecommerce')
    fastapi_app.include_router(crm_bp.fastapi_router, prefix='/api/crm')
    fastapi_app.include_router(billing_bp.fastapi_router, prefix='/api/billing')
    fastapi_app.include_router(payment_gateways_bp.fastapi_router, prefix='/api/payment-gateways')
    fastapi_app.include_router(voice_bp.fastapi_router, prefix='/api/voice')
    fastapi_app.include_router(twilio_bp.fastapi_router, prefix='/api/v1/twilio')
    fastapi_app.include_router(twilio_webhooks_bp.fastapi_router)
    fastapi_app.include_router(demo_bp.fastapi_router, prefix='/api/demo')
    fastapi_app.include_router(landing_pages_bp.fastapi_router, prefix='/api/landing-pages')
    fastapi_app.include_router(hubspot_router_bp.fastapi_router, prefix='/api/integrations/hubspot')
    fastapi_app.include_router(marketplace_bp.fastapi_router, prefix='/api/marketplace')
    fastapi_app.include_router(agency_bp.fastapi_router, prefix='/api/agency')
    fastapi_app.include_router(meetings_bp.fastapi_router, prefix=meetings_bp.url_prefix)
    fastapi_app.include_router(ingestion_bp.fastapi_router, prefix='/api/ingestion')
    fastapi_app.include_router(media_bp.fastapi_router, prefix='/api/media')
    # ── New Feature Routes ─────────────────────────────────────────────────
    fastapi_app.include_router(funnel_live_bp.fastapi_router, prefix='/api/funnel')
    fastapi_app.include_router(enterprise_bp.fastapi_router, prefix='/api/enterprise')
    fastapi_app.include_router(campaign_qr_bp.fastapi_router) # Includes /r/{slug} and /api/campaigns/qr
    fastapi_app.include_router(observatory_bp.fastapi_router, prefix='/api/observatory')
    fastapi_app.include_router(catalog_bp.fastapi_router, prefix='/api/catalog')
    fastapi_app.include_router(community_bp.fastapi_router, prefix='/api/community')
    # Public serving route (no prefix since it handles /l/{company_slug}/{page_slug})
    # Domain routing middleware is handled in fastapi_app.py startup
    
    logger.info("Successfully mounted all native APIRouters on FastAPI!")
