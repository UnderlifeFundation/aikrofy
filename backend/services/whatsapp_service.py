"""
WhatsApp Baileys Service - Client for the WhatsApp Node.js API
"""
import os
import requests
from typing import Optional, Dict, Any


class WhatsAppBaileysService:
    """
    Service to communicate with the WhatsApp Baileys API (Node.js microservice).
    Each instance is tied to a specific company_id.
    """
    
    def __init__(self, company_id: str):
        self.company_id = str(company_id)
        self.base_url = os.getenv('WHATSAPP_API_URL', 'http://localhost:3011')
        self.timeout = 30  # seconds
    
    def init_session(self) -> Dict[str, Any]:
        """
        Initialize a new WhatsApp session for this company.
        Returns: {"status": "initializing", "message": "..."}
        """
        try:
            response = requests.post(
                f"{self.base_url}/session/init",
                json={"companyId": self.company_id},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "status": "error"}
    
    def get_qr(self) -> Optional[str]:
        """
        Get the current QR code SVG for this company's session.
        Returns: SVG string or None if not available
        """
        try:
            response = requests.get(
                f"{self.base_url}/session/qr/{self.company_id}",
                timeout=self.timeout
            )
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'svg' in content_type or 'xml' in content_type:
                    return response.text
                # If JSON response (already connected)
                return None
            return None
        except requests.RequestException:
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current session status.
        Returns: {"companyId": "...", "connected": bool, "state": "..."}
        """
        try:
            response = requests.get(
                f"{self.base_url}/session/status/{self.company_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"connected": False, "state": None, "error": str(e)}
    
    def get_status_with_auto_restore(self) -> Dict[str, Any]:
        """
        Get the current session status and attempt auto-restore if possible.
        """
        try:
            response = requests.get(
                f"{self.base_url}/session/status-restore/{self.company_id}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"connected": False, "state": None, "error": str(e)}
    
    def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp.
        """
        try:
            response = requests.post(
                f"{self.base_url}/lead",
                json={
                    "companyId": self.company_id,
                    "phone": phone,
                    "message": message
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "success": False}
    
    def send_media(self, phone: str, media_url: str, media_type: str, 
                   caption: Optional[str] = None, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Send media (image, video, audio, document) via WhatsApp.
        media_type: 'image', 'video', 'audio', 'document'
        """
        try:
            payload = {
                "companyId": self.company_id,
                "phone": phone,
                "mediaUrl": media_url,
                "mediaType": media_type
            }
            if caption:
                payload["caption"] = caption
            if file_name:
                payload["fileName"] = file_name
                
            response = requests.post(
                f"{self.base_url}/lead/media",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "success": False}
    
    def send_typing(self, phone: str) -> Dict[str, Any]:
        """
        Send typing indicator via WhatsApp.
        """
        try:
            response = requests.post(
                f"{self.base_url}/lead/typing",
                json={
                    "companyId": self.company_id,
                    "phone": phone
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "success": False}
    
    def logout(self) -> Dict[str, Any]:
        """
        Logout and disconnect the WhatsApp session.
        """
        try:
            response = requests.post(
                f"{self.base_url}/session/logout",
                json={"companyId": self.company_id},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "status": "error"}

    def send_interactive(self, phone: str, body: str, title: Optional[str] = None, 
                         footer: Optional[str] = None, buttons: Optional[list] = None) -> Dict[str, Any]:
        """
        Send interactive menu or quick buttons via WhatsApp.
        """
        try:
            payload = {
                "companyId": self.company_id,
                "phone": phone,
                "body": body
            }
            if title:
                payload["title"] = title
            if footer:
                payload["footer"] = footer
            if buttons:
                payload["buttons"] = buttons

            response = requests.post(
                f"{self.base_url}/lead/interactive",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e), "success": False}
    
    @staticmethod
    def is_available() -> bool:
        """Check if the WhatsApp API service is reachable."""
        base_url = os.getenv('WHATSAPP_API_URL', 'http://localhost:3011')
        try:
            response = requests.get(f"{base_url}/session/list", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
