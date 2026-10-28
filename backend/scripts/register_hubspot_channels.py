"""
One-time setup script to register custom Telegram and WhatsApp channels in HubSpot
for Aikrofy.
"""
import sys
import os
import requests

# Add backend to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config

def register_channel(name: str, app_id: str, access_token: str, webhook_url: str, logo_url: str, description: str):
    """
    Registers a custom channel in HubSpot.
    API: POST https://api.hubapi.com/conversations/2026-03/custom-channels
    """
    url = f"https://api.hubapi.com/conversations/2026-03/custom-channels?appId={app_id}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "webhookUrl": webhook_url,
        "capabilities": {
            "deliveryIdentifierTypes": ["HS_PHONE_NUMBER" if "whatsapp" in name.lower() else "CHANNEL_SPECIFIC_OPAQUE_ID"],
            "richText": [],
            "allowInlineImages": True,
            "allowOutgoingMessages": True,
            "outgoingAttachmentTypes": ["FILE"],
            "maxFileAttachmentCount": 10,
            "maxFileAttachmentSizeBytes": 10 * 1024 * 1024,
            "maxTotalFileAttachmentSizeBytes": 50 * 1024 * 1024,
            "threadingModel": "INTEGRATION_THREAD_ID"
        },
        "channelDescription": description,
        "channelLogoUrl": logo_url
    }
    
    print(f"Registering channel '{name}'...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code in (200, 201):
            data = response.json()
            print(f"✅ Success! Registered channel '{name}'. Channel ID: {data.get('id')}")
            return data.get('id')
        else:
            print(f"❌ Failed to register '{name}'. Status: {response.status_code}. Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection error while registering '{name}': {e}")
        return None

if __name__ == "__main__":
    # Get values from env or arguments
    # Note: Requires developer credentials or app installation OAuth token.
    app_id = os.getenv("HUBSPOT_APP_ID")
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    base_webhook_url = os.getenv("PYMAI_BASE_WEBHOOK_URL", "https://api.aikrofy.com")
    
    if not app_id or not access_token:
        print("⚠️  Error: HUBSPOT_APP_ID and HUBSPOT_ACCESS_TOKEN must be configured in environment variables.")
        sys.exit(1)
        
    webhook_endpoint = f"{base_webhook_url.rstrip('/')}/api/integrations/hubspot/webhooks"
    
    # 1. Register WhatsApp
    register_channel(
        name="WhatsApp - Aikrofy",
        app_id=app_id,
        access_token=access_token,
        webhook_url=webhook_endpoint,
        logo_url="https://aikrofy.com/assets/logos/whatsapp.png",
        description="Canal de WhatsApp Business unificado para Aikrofy"
    )
    
    # 2. Register Telegram
    register_channel(
        name="Telegram - Aikrofy",
        app_id=app_id,
        access_token=access_token,
        webhook_url=webhook_endpoint,
        logo_url="https://aikrofy.com/assets/logos/telegram.png",
        description="Canal de Telegram unificado para Aikrofy"
    )
