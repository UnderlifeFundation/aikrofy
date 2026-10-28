"""
Aikrofy - FastAPI Unified Gateway
This application handles both high-concurrency async requests, legacy Flask routes,
and Real-time Socket.IO communication for AI Agents.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import os
import time
import logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import get_config
from extensions import db, socketio, sio
from celery_app import celery
from database import engine, SessionLocal, get_db, db_session
from fastapi_routers import router as api_router
from fastapi_routes_loader import mount_legacy_blueprints
import socketio as pysocketio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

# FastAPI Initialization
app = FastAPI(
    title="Aikrofy Unified Gateway",
    description="Unified High-performance Gateway managing Async, Legacy, and Real-time services.",
    version="4.0.0"
)

# CORS configuration - Allow all client domains embedding widgets/APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Mount static files under /api/static and /api/uploads to resolve via Nginx proxying
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
static_dir = os.path.join(os.path.dirname(__file__), "static")
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "logos"), exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "voice"), exist_ok=True)

app.mount("/api/static", StaticFiles(directory=static_dir), name="static")
app.mount("/static", StaticFiles(directory=static_dir), name="static_root")
app.mount("/api/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads_root")

@app.get("/widget.js", include_in_schema=False)
@app.get("/api/widget.js", include_in_schema=False)
@app.get("/static/js/widget.js", include_in_schema=False)
@app.get("/api/static/js/widget.js", include_in_schema=False)
async def serve_widget_js():
    widget_file = os.path.join(static_dir, "js", "widget.js")
    if os.path.exists(widget_file):
        return FileResponse(
            widget_file,
            media_type="application/javascript",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="widget.js not found")
@app.on_event("startup")
async def startup_event():
    import asyncio
    import extensions
    extensions.set_main_loop(asyncio.get_running_loop())
    from services.realtime_service import start_redis_listener
    asyncio.create_task(start_redis_listener())

    # Ensure database schema integrity & new columns in background
    def run_schema_sync():
        try:
            from scripts.sync_db_schema import sync_database_schema
            sync_database_schema(verbose=False)
        except Exception as e:
            logger.warning(f"Startup DB sync error: {e}")

    asyncio.create_task(asyncio.to_thread(run_schema_sync))

# Database Session Cleanup Middleware
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    finally:
        try:
            db_session.remove()
        except Exception:
            # MySQL connection may have died during a long request (e.g. AI processing).
            # Discard the broken connection from the pool gracefully.
            try:
                db_session.registry.registry.clear()
            except Exception:
                pass

# IP Security & Blacklist Enforcement Middleware
@app.middleware("http")
async def ip_security_middleware(request: Request, call_next):
    from services.ip_security_service import IpSecurityService
    client_ip = IpSecurityService.extract_client_ip(request)
    
    # 1. Enforce IP Blacklist
    if IpSecurityService.is_ip_blocked(client_ip):
        logger.warning(f"🚫 [BLOCKED IP] Rejected connection from blacklisted IP: {client_ip} on {request.url.path}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={
                "error": "Acceso denegado: Esta dirección IP ha sido bloqueada por seguridad por la administración de la plataforma.",
                "blocked_ip": client_ip
            }
        )
        
    return await call_next(request)

# Community Activation Gate Middleware (Enforces Official Activation for Self-Hosted Community Edition)
@app.middleware("http")
async def community_activation_gate_middleware(request: Request, call_next):
    from services.community_license_service import CommunityLicenseService
    if CommunityLicenseService.is_community_mode():
        path = request.url.path
        # Exclude activation endpoints, auth/health checks and static assets from gating
        is_exempt = (
            path.startswith("/api/community/") or
            path.startswith("/api/auth/") or
            path.startswith("/api/static/") or
            path.startswith("/static/") or
            path == "/health" or
            path == "/favicon.ico"
        )
        if not is_exempt:
            stored = CommunityLicenseService.get_stored_activation()
            if not stored:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=423, # Locked
                    content={
                        "error": "INSTANCIA_BLOQUEADA_REQUIERE_ACTIVACION",
                        "is_activated": False,
                        "message": "Esta instancia auto-hospedada de Aikrofy Community requiere un Token de Activación Oficial gratuito. Regístrate en app.aikrofy.com/community para desbloquearla.",
                        "activation_url": "https://aikrofy.com/community",
                        "activate_endpoint": "/api/community/activate"
                    }
                )
    return await call_next(request)

# Custom Domain Routing Middleware
@app.middleware("http")
async def custom_domain_middleware(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0].strip().lower()
    path = request.url.path
    
    # List of system domains that should NOT trigger landing page resolution
    system_domains = {
        "localhost", "127.0.0.1", "aikrofy.com", "www.aikrofy.com", "app.aikrofy.com",
        "api.aikrofy.com", "mcp.aikrofy.com", "pymai.click", "app.pymai.click", "pymai.com",
        "app.pymai.com", "aikrofy.fundacionunderlife.org", "fundacionunderlife.org"
    }
    
    # Exclude system API routes, static assets, socket.io, etc.
    is_system_path = path.startswith("/api/") or path.startswith("/socket.io/") or path.startswith("/_next/") or path.startswith("/static/") or path == "/health"
    
    if host and host not in system_domains and not is_system_path:
        # Internally rewrite route to serve custom domain landing page
        # Note: In FastAPI/Starlette, request.scope["path"] handles routing
        logger.info(f"Custom Domain Route matched! Host: {host}, path: {path} -> rewriting internally to serve landing page.")
        
        # Modify scope variables to transparently route to serve_custom_domain
        request.scope["path"] = f"/api/landing-pages/custom-domain/{path.lstrip('/')}"
        
        # Inject the custom domain header so the target controller knows which domain to look up
        headers = dict(request.scope.get("headers", []))
        headers[b"x-custom-domain"] = host.encode("utf-8")
        request.scope["headers"] = [(k, v) for k, v in headers.items()]

    return await call_next(request)

# Include native FastAPI routers (including ERP routes)
app.include_router(api_router, prefix="/api")

# Include Attributions API router
from routes.attributions import router as attributions_router
app.include_router(attributions_router)

# Include Skills API router (dynamic agent skill management)
from routes.skills import router as skills_router
app.include_router(skills_router)

# Include MCP API router (dynamic Model Context Protocol connection management)
from routes.mcp import router as mcp_router
app.include_router(mcp_router)

# V1 Public API - API-First external access
from routes.v1.agents import router as v1_agents_router
from routes.v1.knowledge import router as v1_knowledge_router
app.include_router(v1_agents_router)
app.include_router(v1_knowledge_router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "app": "Aikrofy FastAPI Backend",
            "database": "connected",
            "timestamp": time.time(),
            "celery": "available" if celery else "unavailable",
            "realtime": "enabled"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

# ---------------------------------------------------------------------------
# Webhook Proxy (Surgical Migration)
# ---------------------------------------------------------------------------

@app.post("/api/webhooks/whatsapp")
async def whatsapp_webhook_async(request: Request):
    """
    Asynchronous receiver for WhatsApp Webhooks.
    Acknowledges receipt immediately and dispatches logic to Celery.
    """
    try:
        data = await request.json()
    except:
        form_data = await request.form()
        data = dict(form_data)

    if not data:
        return {"status": "ignored", "reason": "empty_payload"}

    try:
        company_id_raw = data.get('companyId') or data.get('company_id')
        if not company_id_raw:
            return {"status": "error", "message": "Missing companyId"}
        company_id = int(company_id_raw)
        logger.info(f"Incoming WhatsApp webhook for company {company_id}")
        
        # Support both flattened payload and original Baileys object
        msg_data = data.get('rawMessage') or data.get('message')
        if not msg_data or isinstance(msg_data, str):
            # Fallback if rawMessage is missing and message is just text
            msg_data = data
            
        # Parse Baileys Message
        key = msg_data.get('key', {})
        remote_jid = key.get('remoteJid', '')
        remote_jid_alt = key.get('remoteJidAlt', '')
        
        if not remote_jid or 'status@broadcast' in remote_jid:
             logger.info(f"Ignored broadcast/empty JID: {remote_jid}")
             return {"status": "ignored", "reason": "broadcast_or_empty_jid"}

        # FIX-AIKROFY-001: Filter group, newsletter and channel messages.
        # Baileys returns 'not-acceptable' (406) when trying to reply to @g.us or @newsletter JIDs
        # as if they were individual chats. Only process direct (1:1) WhatsApp messages.
        if '@g.us' in remote_jid:
            logger.info(f"Ignored WhatsApp group message from: {remote_jid}")
            return {"status": "ignored", "reason": "group_message_not_supported"}
        if '@newsletter' in remote_jid:
            logger.info(f"Ignored WhatsApp newsletter/channel message from: {remote_jid}")
            return {"status": "ignored", "reason": "newsletter_message_not_supported"}

        participant = key.get('participant', '') or key.get('participantAlt', '')
        participant_alt = key.get('participantAlt', '')

        # Broadcast list message support:
        # If remote_jid is a broadcast list (e.g. 1790119353@broadcast), the actual sender is in 'participant'
        if '@broadcast' in remote_jid and participant:
            logger.info(f"Broadcast list message detected. Unwrapping sender participant: {participant} (broadcast JID was: {remote_jid})")
            target_jid = participant
            if '@lid' in participant and participant_alt and '@s.whatsapp.net' in participant_alt:
                target_jid = participant_alt
        else:
            target_jid = remote_jid
            if '@lid' in remote_jid and remote_jid_alt and '@s.whatsapp.net' in remote_jid_alt:
                target_jid = remote_jid_alt
                logger.info(f"LID resolved: {remote_jid} -> {target_jid}")

        # Cache and persist the LID -> phone mapping if both are known
        from services.customer_service import CustomerService
        if '@lid' in remote_jid and remote_jid_alt and '@s.whatsapp.net' in remote_jid_alt:
            CustomerService.save_lid_mapping(company_id, remote_jid, remote_jid_alt)
        elif '@lid' in participant and participant_alt and '@s.whatsapp.net' in participant_alt:
            CustomerService.save_lid_mapping(company_id, participant, participant_alt)
        elif '@lid' in target_jid:
            # Check cached or DB mapping
            resolved_p = CustomerService.resolve_real_phone(company_id, target_jid)
            if resolved_p:
                target_jid = f"{resolved_p}@s.whatsapp.net"
                logger.info(f"LID resolved from DB/cache: {target_jid}")
             
        # Extract clean phone number without @s.whatsapp.net or @lid suffix
        from_phone = target_jid.split('@')[0]
        logger.info(f"Message from phone: {from_phone} (raw JID: {remote_jid}, target: {target_jid})")

        # Cache active raw JID (especially if LID) so we can always reply to the exact WhatsApp entity
        active_lid_jid = target_jid if '@lid' in target_jid else (participant if '@lid' in participant else (remote_jid if '@lid' in remote_jid else target_jid))
        if '@lid' in active_lid_jid:
            try:
                from services.cache_service import CacheService
                CacheService.set(f"wa:raw_jid:{company_id}:{from_phone}", active_lid_jid, ttl=86400 * 30)
                CacheService.set(f"wa:raw_jid:{company_id}:{active_lid_jid.split('@')[0]}", active_lid_jid, ttl=86400 * 30)
            except Exception:
                pass
        
        # Extract text content
        message_text = data.get('message', '') if isinstance(data.get('message'), str) else ''
        if not message_text:
            w_message = msg_data.get('message', {})
            if 'conversation' in w_message:
                message_text = w_message['conversation']
            elif 'extendedTextMessage' in w_message:
                message_text = w_message['extendedTextMessage'].get('text', '')
        
        attachment = data.get('attachment')
        is_voice_input = False
        if attachment and attachment.get('type') == 'audio' and attachment.get('local_path'):
            from services.voice_service import VoiceService
            try:
                import anyio
                transcription = await anyio.to_thread.run_sync(
                    VoiceService.transcribe,
                    attachment.get('local_path')
                )
                if transcription:
                    message_text = transcription
                    is_voice_input = True
                    logger.info(f"WhatsApp voice note transcribed: {message_text}")
            except Exception as ve:
                logger.error(f"Error transcribing voice note in webhook: {ve}")
            finally:
                try:
                    if os.path.exists(attachment.get('local_path')):
                        os.remove(attachment.get('local_path'))
                        logger.info(f"Cleaned up temp WhatsApp audio file: {attachment.get('local_path')}")
                except Exception as clean_err:
                    logger.warning(f"Failed to delete temp audio: {clean_err}")
        
        if not message_text:
            return {"status": "ignored", "reason": "no_text_or_audio_content"}

        # ─── Deduplication (WhatsApp Multi-Device / Burst / LID protection) ───
        try:
            import hashlib
            from services.cache_service import CacheService
            msg_id = key.get('id') or data.get('messageId')
            if msg_id:
                dedup_key = f"wa:dedup:msg:{company_id}:{msg_id}"
                if CacheService.get(dedup_key):
                    logger.info(f"Ignored duplicate WhatsApp message ID: {msg_id}")
                    return {"status": "ignored", "reason": "duplicate_message_id"}
                CacheService.set(dedup_key, "1", ttl=60)
            
            # Content-hash deduplication with small burst window (2s) so repeated or quick follow-up messages are not lost
            content_hash = hashlib.md5(f"{company_id}:{from_phone}:{message_text.strip().lower()}".encode('utf-8')).hexdigest()
            hash_key = f"wa:dedup:hash:{content_hash}"
            if CacheService.get(hash_key):
                logger.info(f"Ignored duplicate WhatsApp burst message by content hash: {hash_key}")
                return {"status": "ignored", "reason": "duplicate_content_burst"}
            CacheService.set(hash_key, "1", ttl=2)
        except Exception as dedup_err:
            logger.warning(f"Dedup check warning: {dedup_err}")

        # ─── Employee Detection for Conversation Routing ───
        from services.employee_detection_service import EmployeeDetectionService
        employee = EmployeeDetectionService.detect_employee(company_id, from_phone)
        is_employee = employee is not None

        with SessionLocal() as db_session_local:
            from models.conversation import Conversation, Message, MessageRole, ConversationType
            from datetime import datetime

            conversation = db_session_local.query(Conversation).filter_by(
                company_id=company_id,
                channel='whatsapp',
                contact_phone=from_phone,
                is_active=True
            ).first()

            customer = None
            if not is_employee:
                from services.customer_service import CustomerService
                customer = CustomerService.get_customer(company_id, phone=from_phone)
                if not customer:
                    real_phone = CustomerService.resolve_real_phone(company_id, from_phone)
                    customer_data = {'phone': real_phone} if real_phone else {}
                    from_name = data.get('fromName', '')
                    if from_name:
                        parts = from_name.strip().split(' ', 1)
                        customer_data['first_name'] = parts[0]
                        if len(parts) > 1:
                            customer_data['last_name'] = parts[1]
                    try:
                        customer = CustomerService.upsert_customer(company_id, customer_data)
                    except Exception as cust_create_err:
                        logger.warning(f"Auto-creating customer failed in webhook: {cust_create_err}")

            if not conversation:
                conv_type = ConversationType.EMPLOYEE if is_employee else ConversationType.CUSTOMER
                if is_employee:
                    contact_display = employee.name
                elif customer and (customer.first_name or customer.last_name):
                    contact_display = f"{customer.first_name or ''} {customer.last_name or ''}".strip()
                else:
                    contact_display = data.get('fromName', '')

                conversation = Conversation(
                    company_id=company_id,
                    channel='whatsapp',
                    contact_phone=from_phone,
                    type=conv_type,
                    contact_name=contact_display,
                    customer_id=customer.id if customer and not is_employee else None,
                    conv_metadata={
                        'is_employee': is_employee,
                        'employee_id': employee.id if is_employee else None,
                        'raw_jid': remote_jid,
                        'target_jid': target_jid,
                        'push_name': data.get('fromName', '')
                    }
                )
                db_session_local.add(conversation)
                db_session_local.flush()
            else:
                # Update existing conversation if employee status or customer link changed
                conv_meta = dict(conversation.conv_metadata or {})
                conv_meta.update({'raw_jid': remote_jid, 'target_jid': target_jid})
                if data.get('fromName'):
                    conv_meta['push_name'] = data.get('fromName')
                if is_employee:
                    if conversation.type != ConversationType.EMPLOYEE:
                        conversation.type = ConversationType.EMPLOYEE
                        conversation.contact_name = employee.name
                    conv_meta.update({'is_employee': True, 'employee_id': employee.id})
                else:
                    if not conversation.customer_id and customer:
                        conversation.customer_id = customer.id
                        if not conversation.contact_name:
                            conversation.contact_name = f"{customer.first_name or ''} {customer.last_name or ''}".strip()
                conversation.conv_metadata = conv_meta
                db_session_local.flush()

            user_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=message_text,
                channel='whatsapp'
            )
            db_session_local.add(user_msg)
            conversation.last_message_at = datetime.utcnow()
            db_session_local.commit()
            conv_id = conversation.id

        # Preserve active reply destination (raw_jid if LID, else from_phone)
        reply_destination = target_jid if '@lid' in target_jid else (remote_jid if '@lid' in remote_jid else from_phone)

        # Trigger instant typing status so the user immediately sees the three dots (...)
        try:
            from services.messaging_service import messaging_service
            messaging_service.send_typing(to_phone=reply_destination, company_id=company_id, provider='baileys')
        except Exception as typ_fastapi_err:
            logger.debug(f"FastAPI instant typing error: {typ_fastapi_err}")

        celery.send_task('tasks.process_webhook_message', args=[
            company_id,
            conv_id,
            message_text,
            'whatsapp',
            reply_destination
        ], kwargs={'is_voice_input': is_voice_input, 'provider': 'baileys'})
        
        return {"status": "received", "async": True, "conversation_id": conv_id}
    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/v2/test")
def test_async():
    return {
        "message": "FastAPI is running for Aikrofy",
        "features": ["async_webhooks", "celery_bridge", "shared_db_pool", "pure_fastapi_backend", "socketio_ready"]
    }

# Mount legacy routes
mount_legacy_blueprints(app)

# Combine Socket.IO ASGI app with FastAPI app
app = pysocketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    import uvicorn
    # Port 5010 matches client and nginx routing configuration
    uvicorn.run(app, host="0.0.0.0", port=5010)
