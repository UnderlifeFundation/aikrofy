"""
Meta WhatsApp Business Cloud API Service
Dispatches outgoing WhatsApp messages directly via Meta Graph API v21.0
"""
import logging
import requests
from typing import Dict, Any, Optional
from config import Config
from models.channel import Channel, ChannelType, ChannelStatus

logger = logging.getLogger(__name__)

META_GRAPH_VERSION = 'v22.0'
META_GRAPH_BASE = f'https://graph.facebook.com/{META_GRAPH_VERSION}'


class MetaWhatsAppService:
    @staticmethod
    def send_whatsapp(company_id: int, to_phone: str, message: str) -> Dict[str, Any]:
        """
        Send a text message via Meta WhatsApp Cloud API.
        """
        try:
            # 1. Retrieve Meta channel credentials for company
            channel = Channel.query.filter_by(
                company_id=company_id,
                type=ChannelType.WHATSAPP
            ).first()

            access_token = None
            phone_number_id = None

            if channel and channel.credentials:
                access_token = channel.credentials.get('access_token')
                phone_number_id = channel.credentials.get('phone_number_id')

            # Fallback to company.api_keys if not in channel credentials
            if not access_token or not phone_number_id:
                from models.company import Company
                company = Company.query.get(company_id)
                if company and company.api_keys:
                    access_token = access_token or company.api_keys.get('meta_token')
                    phone_number_id = phone_number_id or company.api_keys.get('meta_phone_id')

            if not access_token or not phone_number_id:
                return {
                    'success': False,
                    'error': 'Meta WhatsApp App is not connected for this company. Please complete Meta Embedded Signup in Channels.'
                }

            # Ensure phone number is digits only (E.164 without leading '+')
            clean_to = ''.join(c for c in str(to_phone) if c.isdigit())

            url = f"{META_GRAPH_BASE}/{phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': clean_to,
                'type': 'text',
                'text': {'body': message}
            }

            res = requests.post(url, headers=headers, json=payload, timeout=15)
            data = res.json()

            if res.status_code in [200, 201] and 'messages' in data:
                msg_id = data['messages'][0].get('id') if data.get('messages') else 'meta_sent'
                logger.info(f"[META WA] Message sent to {clean_to} (ID: {msg_id})")
                return {'success': True, 'id': msg_id, 'data': data}

            err_msg = data.get('error', {}).get('message', f"Meta API HTTP {res.status_code}")
            logger.error(f"[META WA Error] {err_msg}")
            return {'success': False, 'error': err_msg}

        except Exception as exc:
            logger.error(f"[META WA Exception] {exc}")
            return {'success': False, 'error': str(exc)}

    @staticmethod
    def send_template_whatsapp(company_id: int, to_phone: str, template_name: str, language_code: str = 'es') -> Dict[str, Any]:
        """
        Send an approved HSM template message via Meta WhatsApp Cloud API (opens 24h window).
        """
        try:
            channel = Channel.query.filter_by(
                company_id=company_id,
                type=ChannelType.WHATSAPP
            ).first()

            access_token = None
            phone_number_id = None

            if channel and channel.credentials:
                access_token = channel.credentials.get('access_token')
                phone_number_id = channel.credentials.get('phone_number_id')

            if not access_token or not phone_number_id:
                from models.company import Company
                company = Company.query.get(company_id)
                if company and company.api_keys:
                    access_token = access_token or company.api_keys.get('meta_token')
                    phone_number_id = phone_number_id or company.api_keys.get('meta_phone_id')

            if not access_token or not phone_number_id:
                return {
                    'success': False,
                    'error': 'Meta WhatsApp App is not connected for this company.'
                }

            clean_to = ''.join(c for c in str(to_phone) if c.isdigit())
            url = f"{META_GRAPH_BASE}/{phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': clean_to,
                'type': 'template',
                'template': {
                    'name': template_name,
                    'language': {'code': language_code}
                }
            }

            res = requests.post(url, headers=headers, json=payload, timeout=15)
            data = res.json()

            if res.status_code in [200, 201] and 'messages' in data:
                msg_id = data['messages'][0].get('id') if data.get('messages') else 'meta_template_sent'
                logger.info(f"[META WA Template] Sent {template_name} to {clean_to} (ID: {msg_id})")
                return {'success': True, 'id': msg_id, 'data': data}

            err_msg = data.get('error', {}).get('message', f"Meta Template API HTTP {res.status_code}")
            logger.error(f"[META WA Template Error] {err_msg}")
            return {'success': False, 'error': err_msg}

        except Exception as exc:
            logger.error(f"[META WA Template Exception] {exc}")
            return {'success': False, 'error': str(exc)}
