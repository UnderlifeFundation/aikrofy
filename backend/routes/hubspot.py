"""
FastAPI Routes for HubSpot Integration
Handles HubSpot custom channel webhooks (outbound replies) and visitor identification token generation.
"""
import logging
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models.channel import Channel, ChannelType
from models.crm_config import CRMConfig
from routing import APIRouter as LegacyAPIRouter

logger = logging.getLogger(__name__)

# Use standard FastAPI APIRouter wrapped inside LegacyAPIRouter for seamless loading
hubspot_router_bp = LegacyAPIRouter('hubspot_custom', __name__)


@hubspot_router_bp.route('/visitor-token', methods=['POST'])
def get_visitor_token():
    """
    Generate a visitor identification token for the web chat widget.
    Request body: { "widget_id": "...", "email": "...", "firstName": "...", "lastName": "..." }
    """
    from routing import request, jsonify
    data = request.get_json() or {}
    widget_id = data.get("widget_id")
    email = data.get("email")
    first_name = data.get("firstName")
    last_name = data.get("lastName")

    if not widget_id or not email:
        return jsonify({"error": "Missing widget_id or email"}), 400

    # Resolve company from the WEBCHAT channel
    channel = Channel.query.filter_by(type=ChannelType.WEBCHAT).all()
    target_channel = None
    for c in channel:
        credentials = c.credentials if isinstance(c.credentials, dict) else {}
        if credentials.get('widget_id') == widget_id:
            target_channel = c
            break

    if not target_channel:
        return jsonify({"error": "Webchat channel not found for the provided widget_id"}), 404

    # Get CRM Connector
    from services.crm.factory import get_crm_connector
    from services.crm.hubspot_connector import HubSpotConnector

    connector = get_crm_connector(target_channel.company)
    if not connector or not isinstance(connector, HubSpotConnector):
        return jsonify({"error": "HubSpot is not integrated or connected for this company"}), 400

    try:
        token_data = connector.create_visitor_token(email, first_name, last_name)
        return jsonify(token_data), 200
    except Exception as e:
        logger.error(f"Error generating visitor token: {e}")
        return jsonify({"error": str(e)}), 500


@hubspot_router_bp.route('/webhooks', methods=['POST'])
def hubspot_outbound_webhook():
    """
    Process outgoing messages sent from HubSpot Conversations Inbox
    and relay them back to Telegram or WhatsApp.
    """
    from routing import request, jsonify
    payload = request.get_json() or {}
    event_type = payload.get("type")

    if event_type == "OUTGOING_CHANNEL_MESSAGE_CREATED":
        channel_id = payload.get("channelId")
        message_data = payload.get("message", {})
        text = message_data.get("text")
        thread_ids = payload.get("channelIntegrationThreadIds", [])

        if not thread_ids or not text:
            return jsonify({"status": "ignored", "reason": "Missing text or thread ID"}), 200

        target_thread_id = thread_ids[0]

        # Find the company associated with this HubSpot channel ID in CRMConfig
        crm_configs = CRMConfig.query.all()
        target_config = None
        for config in crm_configs:
            creds = config.credentials or {}
            if creds.get("whatsapp_channel_id") == channel_id or creds.get("telegram_channel_id") == channel_id:
                target_config = config
                break

        if not target_config:
            logger.warning(f"No company configured for HubSpot channel ID {channel_id}")
            return jsonify({"error": "Channel not configured on PymAI"}), 404

        company = target_config.company

        # 1. WhatsApp Relay
        if target_thread_id.startswith("chat_whatsapp_"):
            phone = target_thread_id.replace("chat_whatsapp_", "")
            
            # Send message via Twilio or Baileys
            whatsapp_channel = Channel.query.filter_by(
                company_id=company.id,
                type=ChannelType.WHATSAPP
            ).first()

            if whatsapp_channel:
                try:
                    # Attempt Twilio Service first
                    from services.twilio_service import TwilioService
                    twilio_svc = TwilioService(company)
                    twilio_svc.send_whatsapp(phone, text)
                    logger.info(f"Relayed HubSpot message to WhatsApp via Twilio for company {company.id}")
                except Exception as tw_err:
                    logger.warning(f"Twilio relay failed, falling back to Baileys: {tw_err}")
                    try:
                        from services.whatsapp_service import WhatsAppBaileysService
                        baileys = WhatsAppBaileysService(str(company.id))
                        baileys.send_message(phone, text)
                        logger.info(f"Relayed HubSpot message to WhatsApp via Baileys for company {company.id}")
                    except Exception as b_err:
                        logger.error(f"Failed to send WhatsApp message via Baileys: {b_err}")
                        return jsonify({"error": "Failed to relay to WhatsApp"}), 500

        # 2. Telegram Relay
        elif target_thread_id.startswith("chat_telegram_"):
            chat_id = target_thread_id.replace("chat_telegram_", "")
            telegram_channel = Channel.query.filter_by(
                company_id=company.id,
                type=ChannelType.TELEGRAM
            ).first()

            if telegram_channel:
                token = telegram_channel.credentials.get('telegram_token')
                if token:
                    try:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={'chat_id': chat_id, 'text': text},
                            timeout=10
                        )
                        logger.info(f"Relayed HubSpot message to Telegram for company {company.id}")
                    except Exception as tg_err:
                        logger.error(f"Failed to send Telegram message: {tg_err}")
                        return jsonify({"error": "Failed to relay to Telegram"}), 500

        return jsonify({"status": "dispatched"}), 200

    return jsonify({"status": "received", "event": event_type}), 200
