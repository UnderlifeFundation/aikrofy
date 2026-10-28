from routing import current_app
"""
Twilio Service - Unified interface for WhatsApp, SMS, and Voice
"""
import os
from typing import Optional, Dict, Any, List

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

class TwilioService:
    """
    Unified Twilio Integration Service
    Supports: WhatsApp, SMS, Voice
    Architecture: Multi-tenant (Company keys > Platform keys)
    """
    
    def __init__(self, company=None):
        self.company = company
        self._client = None
        self._from_number = None
        self._whatsapp_number = None
    
    def _get_credential(self, key: str) -> Optional[str]:
        """Resolve credential: Checks Company API Keys first, then Environment"""
        # 1. Check Company Keys
        if self.company and self.company.api_keys:
            value = self.company.api_keys.get(key)
            if value:
                return value
        
        # 2. Check Environment Variables (Platform Default)
        env_map = {
            'twilio_account_sid': 'TWILIO_ACCOUNT_SID',
            'twilio_auth_token': 'TWILIO_AUTH_TOKEN',
            'twilio_phone_number': 'TWILIO_PHONE_NUMBER',
            'twilio_voice_number': 'TWILIO_VOICE_NUMBER',
            'twilio_whatsapp_number': 'TWILIO_WHATSAPP_NUMBER'
        }
        return os.getenv(env_map.get(key, ''))

    def _get_client(self):
        """Lazy initialization of Twilio Client"""
        if not self._client:
            sid = self._get_credential('twilio_account_sid')
            token = self._get_credential('twilio_auth_token')
            
            if not sid or not token:
                raise ValueError("Twilio credentials not configured")
            
            self._client = Client(sid, token)
            
            # Cache numbers
            # Voice: Try specific key first, then generic phone number
            self._from_number = self._get_credential('twilio_voice_number') or self._get_credential('twilio_phone_number')
            
            # WhatsApp: Try specific key
            self._whatsapp_number = self._get_credential('twilio_whatsapp_number')
            
        return self._client

    # ----------------------------------------------------------------
    # 📨 Messaging (WhatsApp & SMS)
    # ----------------------------------------------------------------
    
    def send_whatsapp(self, to_number: str, message: str, media_url: Optional[str] = None) -> Dict[str, Any]:
        """Send WhatsApp message"""
        client = self._get_client()
        from_wa = self._whatsapp_number
        
        # Add 'whatsapp:' prefix if missing
        if not from_wa.startswith('whatsapp:'):
            from_wa = f"whatsapp:{from_wa}"
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
            
        msg_data = {
            'body': message,
            'from_': from_wa,
            'to': to_number
        }
        
        if media_url:
            msg_data['media_url'] = [media_url]
            
        try:
            message = client.messages.create(**msg_data)
            return {'sid': message.sid, 'status': message.status}
        except TwilioRestException as e:
            return {'error': str(e), 'code': e.code}

    def send_sms(self, to_number: str, message: str) -> Dict[str, Any]:
        """Send standard SMS"""
        client = self._get_client()
        from_sms = self._from_number
        
        try:
            message = client.messages.create(
                body=message,
                from_=from_sms,
                to=to_number
            )
            return {'sid': message.sid, 'status': message.status}
        except TwilioRestException as e:
            return {'error': str(e), 'code': e.code}

    # ----------------------------------------------------------------
    # 📞 Voice Calls
    # ----------------------------------------------------------------
    
    def make_call(self, to_number: str, twiml: str) -> Dict[str, Any]:
        """
        Initiate an outbound call
        Args:
            to_number: Recipient number
            twiml: TwiML instructions for the call (XML or URL)
        """
        client = self._get_client()
        from_voice = self._from_number
        
        try:
            call = client.calls.create(
                twiml=twiml,
                to=to_number,
                from_=from_voice
            )
            return {'sid': call.sid, 'status': call.status}
        except TwilioRestException as e:
            return {'error': str(e), 'code': e.code}

    def list_recordings(self, limit: int = 10) -> List[Dict]:
        """List recent call recordings"""
        client = self._get_client()
        recordings = client.recordings.list(limit=limit)
        return [{'sid': r.sid, 'duration': r.duration, 'url': r.media_url} for r in recordings]
