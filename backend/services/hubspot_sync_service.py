"""
HubSpot Synchronization Service
Handles forwarding and syncing incoming and outgoing conversation messages to HubSpot Conversations.
"""
import logging
from typing import Optional

from extensions import db
from models.crm_config import CRMConfig, CRMPlatform
from models.conversation import Conversation, Message, MessageRole, MessageChannel
from services.crm.factory import get_crm_connector
from services.crm.hubspot_connector import HubSpotConnector

logger = logging.getLogger(__name__)


class HubSpotSyncService:
    @staticmethod
    def sync_message_to_hubspot(company_id: int, conversation: Conversation, message: Message) -> None:
        """
        Syncs a single message to HubSpot Conversations if the company has a connected HubSpot integration
        and has custom channel IDs configured in their credentials.
        """
        try:
            # 1. Fetch CRM Configuration
            crm_config = CRMConfig.query.filter_by(company_id=company_id).first()
            if not crm_config or crm_config.platform != CRMPlatform.HUBSPOT or not crm_config.is_connected:
                # HubSpot is not connected for this company; skip silently
                return

            credentials = crm_config.credentials or {}
            
            # 2. Map channel and get registered channel ID from credentials
            if conversation.channel == MessageChannel.WHATSAPP:
                channel_id = credentials.get("whatsapp_channel_id")
                is_whatsapp = True
                thread_prefix = "chat_whatsapp_"
            elif conversation.channel == MessageChannel.TELEGRAM:
                channel_id = credentials.get("telegram_channel_id")
                is_whatsapp = False
                thread_prefix = "chat_telegram_"
            elif conversation.channel == MessageChannel.WEBCHAT or conversation.channel == 'webchat':
                channel_id = credentials.get("webchat_channel_id") or credentials.get("whatsapp_channel_id")
                is_whatsapp = False
                thread_prefix = "chat_webchat_"
            else:
                # Other channels ignored
                return

            if not channel_id:
                channel_name = conversation.channel.value if hasattr(conversation.channel, 'value') else str(conversation.channel)
                logger.warning(
                    f"HubSpot is connected for company {company_id}, but no channel_id configured "
                    f"for {channel_name} in CRM credentials."
                )
                return

            # 3. Instantiate HubSpot Connector via Factory
            connector = get_crm_connector(conversation.company)
            if not connector or not isinstance(connector, HubSpotConnector):
                logger.error(f"Failed to resolve HubSpotConnector for company {company_id}.")
                return

            # 4. Prepare message details
            direction = "INCOMING" if message.role == MessageRole.USER else "OUTGOING"
            
            # Form thread ID to match HubSpot Custom Channel model
            thread_id = f"{thread_prefix}{conversation.contact_phone}"
            
            # Determine sender details
            if direction == "INCOMING":
                sender_identifier = conversation.contact_phone
                sender_name = conversation.contact_name or "Usuario"
            else:
                sender_identifier = "aikrofy_system_sender"
                sender_name = conversation.company.agent_name or "Asistente Aikrofy"

            # 5. Publish to HubSpot Custom Channel
            logger.info(
                f"Syncing {direction} message to HubSpot (Channel: {channel_id}, Thread: {thread_id})"
            )
            connector.publish_custom_channel_message(
                channel_id=channel_id,
                thread_id=thread_id,
                message_text=message.content or "",
                sender_identifier=sender_identifier,
                sender_name=sender_name,
                is_whatsapp=is_whatsapp,
                direction=direction,
                idempotency_id=f"msg_{message.id}" if message.id else None
            )

        except Exception as e:
            logger.error(f"Failed to sync message to HubSpot for company {company_id}: {e}", exc_info=True)
