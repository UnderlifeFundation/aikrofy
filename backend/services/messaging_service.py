"""
Messaging Service - Universal multi-provider dispatcher.
Supports: Baileys (WhatsApp Web), Meta Cloud API, and Twilio.
Designed for PymAI / Aikrofy backend.
"""
import os
import re
import requests
import logging

logger = logging.getLogger(__name__)


def format_whatsapp_text(text: str) -> str:
    """
    Transforms markdown formatting to WhatsApp native formatting:
    - Converts markdown headers (### Header) to bold (*Header*)
    - Converts markdown links ([title](url)) to *title*: url
    - Ensures clean rendering without raw symbols
    """
    if not text:
        return text
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        m = re.match(r'^(#{1,6})\s+(.*)$', line.strip())
        if m:
            content = m.group(2).strip()
            if not (content.startswith('*') and content.endswith('*')):
                cleaned_lines.append(f"*{content}*")
            else:
                cleaned_lines.append(content)
        else:
            cleaned_lines.append(line)
    result = '\n'.join(cleaned_lines)
    # Convert markdown links [text](url) -> *text*: url
    result = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'*\1*: \2', result)
    return result


def _resolve_company_provider(company_id: int):
    """
    Resolve the active WhatsApp provider and credentials for a company.
    Returns (provider, credentials_dict) where provider is one of:
    'baileys', 'meta', 'twilio'.
    """
    try:
        from models.channel import Channel, ChannelType
        from models.company import Company

        channel = Channel.query.filter_by(
            company_id=company_id,
            type=ChannelType.WHATSAPP
        ).first()

        provider = None
        creds = {}

        if channel and channel.credentials:
            provider = channel.credentials.get('provider')
            creds = dict(channel.credentials)

        if not provider:
            company = Company.query.get(company_id)
            if company and company.api_keys:
                provider = company.api_keys.get('whatsapp_provider')
                # Merge api_keys into creds for fallback lookups
                creds.update(company.api_keys)

        return (provider or 'baileys'), creds
    except Exception as e:
        logger.warning(f"[MessagingService] Could not resolve provider for company {company_id}: {e}")
        return 'baileys', {}


class MessagingService:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.whatsapp_api_url = os.getenv('WHATSAPP_API_URL', 'http://localhost:3011')

    # ----------------------------------------------------------------
    # 🔵 Universal WhatsApp Dispatcher (auto-detects provider)
    # ----------------------------------------------------------------

    def send_whatsapp(self, to_phone: str, message: str, company_id: int, provider: str = None, check_anti_spam: bool = False, event_tag: str = "general_outbound"):
        """
        Send WhatsApp message via the active provider for the company.
        If provider is explicitly passed (e.g. 'baileys', 'meta', 'twilio'), it uses it directly.
        Otherwise, provider is resolved from Channel.credentials or Company.api_keys:
          - 'baileys'  → Baileys Node.js microservice (localhost:3001)
          - 'meta'     → Meta Cloud API (with 24h window + template fallback)
          - 'twilio'   → Twilio REST API
        Falls back to Baileys if provider cannot be determined.

        Anti-Spam & Anti-Flood:
        If check_anti_spam is True, validates burst, cooldown and duplicate hash guards before sending.
        """
        try:
            if check_anti_spam:
                from services.autonomous_consciousness_service import AutonomousConsciousnessService
                if not AutonomousConsciousnessService.check_anti_spam_guard(
                    company_id=company_id,
                    phone=to_phone,
                    event_tag=event_tag,
                    cooldown_seconds=60,
                    content=message
                ):
                    logger.warning(f"[MessagingService] 🛑 Blocked send_whatsapp to {to_phone} by anti-spam frequency shield.")
                    return False

            creds = {}
            if not provider:
                provider, creds = _resolve_company_provider(company_id)
            elif provider in ('meta', 'twilio'):
                _, creds = _resolve_company_provider(company_id)

            # Clean and convert markdown headers/links for WhatsApp format
            message = format_whatsapp_text(message)

            logger.info(f"[MessagingService] Sending WhatsApp via provider='{provider}' to={to_phone} (company={company_id})")

            success = False
            if provider == 'meta':
                success = self._send_via_meta(company_id, to_phone, message, creds)
            elif provider == 'twilio':
                success = self._send_via_twilio(company_id, to_phone, message, creds)
            else:
                success = self._send_via_baileys(to_phone, message, company_id)

            if success and check_anti_spam:
                from services.autonomous_consciousness_service import AutonomousConsciousnessService
                AutonomousConsciousnessService.record_dispatched_message(
                    company_id=company_id,
                    phone=to_phone,
                    event_tag=event_tag,
                    cooldown_seconds=60,
                    content=message
                )

            return success

        except Exception as e:
            logger.error(f"[MessagingService] send_whatsapp unexpected error to {to_phone} (company={company_id}): {e}")
            return False

    def _send_via_baileys(self, to_phone: str, message: str, company_id: int) -> bool:
        """Send via Baileys Node.js microservice."""
        try:
            url = f"{self.whatsapp_api_url}/lead"
            payload = {
                "phone": to_phone,
                "message": message,
                "companyId": str(company_id)
            }
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"[MessagingService] ✅ Baileys sent to {to_phone} (company={company_id})")
            return True
        except Exception as e:
            logger.error(f"[MessagingService] ❌ Baileys send failed to {to_phone}: {e}")
            return False

    def _send_via_meta(self, company_id: int, to_phone: str, message: str, creds: dict) -> bool:
        """
        Send via Meta WhatsApp Cloud API.
        - If the 24h messaging window is closed (error #131047 or #10), automatically
          retries with the first available approved HSM template to re-open the window.
        - If Meta fails entirely, falls back to Twilio if configured.
        """
        try:
            from services.meta_whatsapp_service import MetaWhatsAppService
            res = MetaWhatsAppService.send_whatsapp(company_id, to_phone, message)
            if res.get('success'):
                logger.info(f"[MessagingService] ✅ Meta sent to {to_phone} (company={company_id}), id={res.get('id')}")
                return True

            err_text = str(res.get('error', ''))
            logger.warning(f"[MessagingService] Meta send failed: {err_text}")

            # Auto-fallback: If outside 24h window, try approved template to re-open it
            if any(k in err_text.lower() for k in ['permission', '#10', '131047', '24', 'window', '60', 'not whatsapp']):
                try:
                    from models.whatsapp_template import WhatsAppTemplate, TemplateStatus
                    tpl = WhatsAppTemplate.query.filter_by(
                        company_id=company_id,
                        status=TemplateStatus.APPROVED.value
                    ).first()
                    if tpl:
                        tpl_res = MetaWhatsAppService.send_template_whatsapp(
                            company_id=company_id,
                            to_phone=to_phone,
                            template_name=tpl.name,
                            language_code=tpl.language or 'es'
                        )
                        if tpl_res.get('success'):
                            logger.info(f"[MessagingService] ✅ Meta template '{tpl.name}' sent to {to_phone} (company={company_id})")
                            return True
                except Exception as tpl_err:
                    logger.warning(f"[MessagingService] Template fallback error: {tpl_err}")

            # Last resort: fall back to Twilio if credentials exist
            return self._meta_to_twilio_fallback(company_id, to_phone, message, creds)

        except Exception as e:
            logger.error(f"[MessagingService] Meta send unexpected error: {e}")
            return self._meta_to_twilio_fallback(company_id, to_phone, message, creds)

    def _meta_to_twilio_fallback(self, company_id: int, to_phone: str, message: str, creds: dict) -> bool:
        """Attempt Twilio as last resort when Meta fails."""
        twilio_sid = creds.get('twilio_sid') or os.getenv('TWILIO_ACCOUNT_SID', '')
        if not twilio_sid:
            return False
        try:
            logger.info(f"[MessagingService] Attempting Twilio fallback for {to_phone} (company={company_id})")
            return self._send_via_twilio(company_id, to_phone, message, creds)
        except Exception as e:
            logger.error(f"[MessagingService] Twilio fallback also failed: {e}")
            return False

    def _send_via_twilio(self, company_id: int, to_phone: str, message: str, creds: dict) -> bool:
        """Send via Twilio REST API."""
        try:
            from models.company import Company
            company = Company.query.get(company_id)
            from services.twilio_service import TwilioService
            twilio = TwilioService(company)
            result = twilio.send_whatsapp(to_phone, message)
            if 'sid' in result or result.get('success'):
                logger.info(f"[MessagingService] ✅ Twilio sent to {to_phone} (company={company_id}), sid={result.get('sid')}")
                return True
            logger.error(f"[MessagingService] ❌ Twilio send failed: {result}")
            return False
        except Exception as e:
            logger.error(f"[MessagingService] Twilio send error to {to_phone}: {e}")
            return False

    # ----------------------------------------------------------------
    # 📎 Media Sending (Baileys only for now; Meta/Twilio TBD)
    # ----------------------------------------------------------------

    def send_whatsapp_media(self, to_phone: str, media_url: str, media_type: str, company_id: int, file_name: str = None, caption: str = None, provider: str = None):
        """Send WhatsApp media message — routes to the provider-specific dispatcher."""
        try:
            creds = {}
            if not provider:
                provider, creds = _resolve_company_provider(company_id)
            elif provider in ('meta', 'twilio'):
                _, creds = _resolve_company_provider(company_id)

            if provider == 'meta':
                # Meta media: fallback to text with URL since full media send requires upload
                logger.info(f"[MessagingService] Meta media (type={media_type}) — sending as text URL to {to_phone}")
                text_msg = caption or f"🎵 {media_url}"
                return self._send_via_meta(company_id, to_phone, text_msg, creds)

            elif provider == 'twilio':
                try:
                    from models.company import Company
                    company = Company.query.get(company_id)
                    from services.twilio_service import TwilioService
                    twilio = TwilioService(company)
                    result = twilio.send_whatsapp(to_phone, caption or '', media_url=media_url)
                    return 'sid' in result or result.get('success', False)
                except Exception as e:
                    logger.error(f"[MessagingService] Twilio media send error: {e}")
                    return False

            else:
                # Baileys
                url = f"{self.whatsapp_api_url}/lead/media"
                payload = {
                    "phone": to_phone,
                    "mediaUrl": media_url,
                    "mediaType": media_type,
                    "companyId": str(company_id)
                }
                if file_name:
                    payload["fileName"] = file_name
                if caption:
                    payload["caption"] = caption

                headers = {"Content-Type": "application/json"}
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                response.raise_for_status()
                logger.info(f"[MessagingService] ✅ Baileys media sent to {to_phone} (company={company_id}, type={media_type})")
                return True

        except Exception as e:
            logger.error(f"[MessagingService] send_whatsapp_media failed to {to_phone}: {e}")
            return False

    # ----------------------------------------------------------------
    # ⌨️ Typing Indicator (best-effort, non-critical)
    # ----------------------------------------------------------------

    def send_typing(self, to_phone: str, company_id: int, provider: str = None):
        """
        Send WhatsApp typing indicator.
        - Baileys: calls api-whatsapp microservice endpoint.
        - Meta: not officially supported via Cloud API; silently ignored.
        - Twilio: not supported; silently ignored.
        Never raises exceptions — purely best-effort UX enhancement.
        """
        try:
            if not provider:
                provider, _ = _resolve_company_provider(company_id)
            if provider in ('meta', 'twilio'):
                # Not supported for these providers — skip silently
                return True

            url = f"{self.whatsapp_api_url}/lead/typing"
            payload = {
                "phone": to_phone,
                "companyId": str(company_id)
            }
            headers = {"Content-Type": "application/json"}
            requests.post(url, json=payload, headers=headers, timeout=3)
            return True
        except Exception as e:
            logger.debug(f"[MessagingService] Non-critical typing error for {to_phone}: {e}")
            return False

    # ----------------------------------------------------------------
    # 📱 Telegram
    # ----------------------------------------------------------------

    def send_telegram(self, chat_id: str, message: str, bot_token: str = None):
        """Send Telegram message via official Bot API."""
        token = bot_token or self.telegram_token
        if not token:
            logger.error("[MessagingService] No Telegram token provided")
            return False

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"[MessagingService] ✅ Telegram sent to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"[MessagingService] ❌ Telegram send failed to {chat_id}: {e}")
            return False


messaging_service = MessagingService()
