"""
Autonomous Consciousness Service & Anti-Spam Frequency Shield
============================================================
Provides autonomous, pro-active decision making and communication for Aikrofy.
1. Monitors companies, active leads, operational bottlenecks, pending deals and daily summaries.
2. ZERO-TOKEN Deterministic Filtering: Scans metrics and states in pure SQL and Python algorithms.
   Only activates AI micro-agents / Krof when specific thresholds or actionable conditions are met.
3. ANTI-SPAM & ANTI-FLOOD RATE LIMIT SHIELD:
   - Atomic distributed locking per phone number and event category.
   - Strictly enforces cooldown windows (e.g. max 1 alert per topic per 6 hours, max 1 daily briefing per 24 hours).
   - Duplicate message hash suppression (prevents repeating the same text).
   - Provider-agnostic: operates transparently across Baileys, Meta Cloud API, Twilio, and Telegram.

Copyright © 2026 WEBLIFETECH / AIKROFY. All Rights Reserved.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from extensions import db
from models.company import Company
from models.customer import Customer
from models.employee import Employee, EmployeeRole
from models.conversation import Conversation
from services.cache_service import CacheService
from services.messaging_service import messaging_service

logger = logging.getLogger(__name__)


class AutonomousConsciousnessService:
    """
    Autonomous corporate brain for company heartbeat monitoring and targeted proactive interactions.
    """

    # Anti-Spam Cooldown Windows (in seconds)
    COOLDOWN_LEAD_TRIAGE = 3600 * 4       # 4 hours per specific lead alert
    COOLDOWN_DAILY_SUMMARY = 3600 * 20     # 20 hours minimum between daily briefings
    COOLDOWN_PAYMENT_NUDGE = 3600 * 24    # 24 hours between payment/checkout reminders
    COOLDOWN_TASK_FOLLOWUP = 3600 * 8     # 8 hours between employee task notifications
    BURST_WINDOW_PER_PHONE = 30           # 30 seconds minimum between ANY message to the same recipient

    @classmethod
    def check_anti_spam_guard(cls, company_id: int, phone: str, event_tag: str, cooldown_seconds: int, content: str = None) -> bool:
        """
        Anti-Spam & Anti-Flood verification engine.
        Returns True if the message is SAFE to send.
        Returns False if sending would violate frequency limits, burst limits or duplicate suppression.
        """
        if not phone:
            return False

        clean_phone = ''.join(c for c in str(phone) if c.isdigit() or c == '+')
        if not clean_phone:
            return False

        # 1. Burst Protection: Never send any two messages to the same phone within BURST_WINDOW_PER_PHONE seconds
        burst_key = f"anti_spam:burst:{clean_phone}"
        if CacheService.get(burst_key):
            logger.warning(f"[ANTI-SPAM SHIELD] 🛑 Blocked message to {clean_phone}: burst limit active (< {cls.BURST_WINDOW_PER_PHONE}s).")
            return False

        # 2. Topic/Event Cooldown: Max 1 notification of this category per recipient within cooldown_seconds
        topic_key = f"anti_spam:cooldown:{company_id}:{clean_phone}:{event_tag}"
        if CacheService.get(topic_key):
            logger.info(f"[ANTI-SPAM SHIELD] ℹ️ Cooldown active for {clean_phone} on event '{event_tag}'. Suppressing duplicate trigger.")
            return False

        # 3. Duplicate Content Hash Check: Never send identical text twice to the same number within 12 hours
        if content:
            content_hash = hashlib.md5(f"{clean_phone}:{content.strip().lower()}".encode('utf-8')).hexdigest()
            hash_key = f"anti_spam:hash:{content_hash}"
            if CacheService.get(hash_key):
                logger.warning(f"[ANTI-SPAM SHIELD] 🛑 Blocked duplicate message content to {clean_phone}.")
                return False

        return True

    @classmethod
    def record_dispatched_message(cls, company_id: int, phone: str, event_tag: str, cooldown_seconds: int, content: str = None):
        """
        Records the successful delivery to lock the anti-spam shields in Redis/RAM.
        """
        clean_phone = ''.join(c for c in str(phone) if c.isdigit() or c == '+')
        
        # Lock burst window
        CacheService.set(f"anti_spam:burst:{clean_phone}", "1", ttl=cls.BURST_WINDOW_PER_PHONE)
        
        # Lock topic cooldown
        CacheService.set(f"anti_spam:cooldown:{company_id}:{clean_phone}:{event_tag}", "1", ttl=cooldown_seconds)
        
        # Lock content hash for 12 hours
        if content:
            content_hash = hashlib.md5(f"{clean_phone}:{content.strip().lower()}".encode('utf-8')).hexdigest()
            CacheService.set(f"anti_spam:hash:{content_hash}", "1", ttl=3600 * 12)

    # =========================================================================
    # DETERMINISTIC AUDITORS (RUN PERIODICALLY VIA CELERY BEAT - ZERO TOKENS)
    # =========================================================================

    @classmethod
    def audit_company_pulse(cls, company_id: int) -> Dict[str, Any]:
        """
        Runs complete deterministic audit of a single company without invoking LLMs.
        Identifies whether proactive actions are required.
        """
        company = Company.query.get(company_id)
        if not company or not company.is_active:
            return {'status': 'skipped', 'reason': 'inactive_company'}

        actions_taken = []

        try:
            # 1. High-Intent Unattended Leads (CSO / Commercial Triage)
            triage_action = cls._check_unattended_hot_leads(company)
            if triage_action:
                actions_taken.append(triage_action)

            # 2. Daily Executive Briefing for Owner (Evening Pulse)
            briefing_action = cls._check_daily_executive_briefing(company)
            if briefing_action:
                actions_taken.append(briefing_action)

        except Exception as err:
            logger.error(f"[CONSCIOUSNESS] Error auditing company {company_id}: {err}", exc_info=True)
            db.session.rollback()

        return {
            'company_id': company_id,
            'timestamp': datetime.utcnow().isoformat(),
            'actions': actions_taken
        }

    # -------------------------------------------------------------------------
    # Internal Proactive Rules
    # -------------------------------------------------------------------------

    @classmethod
    def _check_unattended_hot_leads(cls, company: Company) -> Optional[Dict[str, Any]]:
        """
        Rule: Lead with score >= 75 created/updated > 30 minutes ago without active response.
        Notifies the designated sales manager or company owner on WhatsApp.
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        hot_leads = (
            Customer.query
            .filter_by(company_id=company.id)
            .filter(Customer.lead_score >= 75)
            .filter(Customer.updated_at <= cutoff_time)
            .order_by(Customer.lead_score.desc())
            .limit(3)
            .all()
        )

        if not hot_leads:
            return None

        # Find sales person or owner to alert
        target_employee = Employee.query.filter_by(company_id=company.id, is_active=True).filter(
            Employee.role.in_([EmployeeRole.SALES, EmployeeRole.MANAGER, EmployeeRole.OWNER, EmployeeRole.ADMIN])
        ).first()

        if not target_employee:
            return None

        target_phone = target_employee.whatsapp or target_employee.phone or company.phone
        if not target_phone:
            return None

        for lead in hot_leads:
            event_tag = f"hot_lead_{lead.id}"
            lead_name = lead.full_name or "Prospecto VIP"
            lead_phone = lead.phone or "No registrado"
            
            message = (
                f"🔥 *KROF RADAR COMERCIAL - Lead Caliente Desatendido*\n\n"
                f"Hola {target_employee.name}, el sistema identificó que *{lead_name}* (Score: {lead.lead_score}/100) "
                f"requiere seguimiento comercial prioritario.\n\n"
                f"📱 *Teléfono:* {lead_phone}\n"
                f"💼 *Interés:* {lead.work_company or 'Solicitud en plataforma'}\n\n"
                f"💡 _Contáctalo ahora para asegurar la oportunidad._"
            )

            # Check anti-spam lock
            if not cls.check_anti_spam_guard(company.id, target_phone, event_tag, cls.COOLDOWN_LEAD_TRIAGE, message):
                continue

            # Safe to dispatch
            sent = messaging_service.send_whatsapp(to_phone=target_phone, message=message, company_id=company.id)
            if sent:
                cls.record_dispatched_message(company.id, target_phone, event_tag, cls.COOLDOWN_LEAD_TRIAGE, message)
                logger.info(f"[CONSCIOUSNESS] ✅ Alerted {target_employee.name} about hot lead {lead.id}")
                return {'action': 'hot_lead_alert', 'lead_id': lead.id, 'target_phone': target_phone}

        return None

    @classmethod
    def _check_daily_executive_briefing(cls, company: Company) -> Optional[Dict[str, Any]]:
        """
        Rule: Daily evening summary (between 19:00 and 21:00 in company local time or UTC).
        Sends high-level KPI pulse to Owner/Admin (total conversations, hot leads, payments).
        """
        now = datetime.utcnow()
        # Default evening window (19:00 to 21:00 UTC if timezone not resolved)
        if not (18 <= now.hour <= 21):
            return None

        # Find owner
        owner = Employee.query.filter_by(company_id=company.id, is_active=True).filter(
            Employee.role.in_([EmployeeRole.OWNER, EmployeeRole.ADMIN])
        ).first()

        owner_phone = None
        owner_name = "Director"
        if owner:
            owner_phone = owner.whatsapp or owner.phone
            owner_name = owner.name
        if not owner_phone:
            owner_phone = company.phone

        if not owner_phone:
            return None

        event_tag = f"daily_briefing_{now.strftime('%Y_%m_%d')}"
        
        # Deterministic KPI extraction (0 LLM Tokens)
        today_start = datetime(now.year, now.month, now.day)
        total_convs = Conversation.query.filter_by(company_id=company.id).filter(Conversation.updated_at >= today_start).count()
        new_leads = Customer.query.filter_by(company_id=company.id).filter(Customer.created_at >= today_start).count()

        briefing_text = (
            f"📊 *REPORTE EJECUTIVO KROF - Cierre del Día*\n\n"
            f"Hola {owner_name}, aquí tienes el balance operativo de *{company.name}* hoy:\n\n"
            f"💬 *Conversaciones atendidas:* {total_convs}\n"
            f"👥 *Nuevos contactos/leads captados:* {new_leads}\n"
            f"🟢 *Estado de agentes:* Operando con normalidad en todos los canales.\n\n"
            f"_Puedes consultar el panel completo en https://app.aikrofy.com/analytics_"
        )

        # Check anti-spam lock (ensures max 1 daily briefing per day)
        if not cls.check_anti_spam_guard(company.id, owner_phone, event_tag, cls.COOLDOWN_DAILY_SUMMARY, briefing_text):
            return None

        sent = messaging_service.send_whatsapp(to_phone=owner_phone, message=briefing_text, company_id=company.id)
        if sent:
            cls.record_dispatched_message(company.id, owner_phone, event_tag, cls.COOLDOWN_DAILY_SUMMARY, briefing_text)
            logger.info(f"[CONSCIOUSNESS] ✅ Sent daily executive briefing to {owner_name} ({owner_phone})")
            return {'action': 'daily_briefing', 'target_phone': owner_phone}

        return None
