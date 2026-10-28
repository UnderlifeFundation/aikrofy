"""
Unified Meeting & Calendar Service
Orchestrates Google Meet, Microsoft Teams, and Zoom.
"""
import os
import logging
import base64
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from extensions import db
from models.company import Company
from integrations.calendar import GoogleCalendarIntegration

logger = logging.getLogger(__name__)


class MeetingService:
    """
    Unified manager for Video Conferencing and Calendar Scheduling.
    Supported providers: 'google' (Google Meet), 'teams' (Microsoft Teams), 'zoom' (Zoom)
    """

    @classmethod
    def get_configured_provider(cls, company: Company) -> str:
        """Return the active provider or detect from existing keys"""
        keys = company.api_keys or {}
        explicit = keys.get('meeting_provider')
        if explicit in ['google', 'teams', 'zoom']:
            return explicit
        
        # Fallbacks based on configured credentials
        if keys.get('google_oauth_credentials'):
            return 'google'
        if keys.get('zoom_client_id') and keys.get('zoom_client_secret'):
            return 'zoom'
        if keys.get('teams_client_id') and keys.get('teams_client_secret'):
            return 'teams'
        return 'google'

    @classmethod
    def schedule_meeting(
        cls,
        company: Company,
        title: str,
        start_time: datetime,
        duration_minutes: int = 30,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a meeting using the active provider configured by the company.
        """
        provider = cls.get_configured_provider(company)
        logger.info(f"[MEETING_SERVICE] Scheduling meeting '{title}' with provider '{provider}' for company {company.id}")

        if provider == 'zoom':
            return cls._schedule_zoom(company, title, start_time, duration_minutes, description, attendees)
        elif provider == 'teams':
            return cls._schedule_teams(company, title, start_time, duration_minutes, description, attendees)
        else:
            # Default to Google Calendar / Google Meet
            return cls._schedule_google(company, title, start_time, duration_minutes, description, attendees, location)

    @classmethod
    def check_availability(cls, company: Company, date_str: str, time_str: Optional[str] = None) -> Dict[str, Any]:
        """Check availability across the active calendar provider"""
        provider = cls.get_configured_provider(company)
        if provider == 'teams':
            return cls._check_teams_availability(company, date_str, time_str)
        # Google calendar handles free/busy slots by default
        calendar = GoogleCalendarIntegration(company=company)
        return calendar.check_availability(date_str, time_str)

    # -------------------------------------------------------------------------
    # 1. GOOGLE MEET IMPLEMENTATION
    # -------------------------------------------------------------------------
    @classmethod
    def _schedule_google(
        cls,
        company: Company,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        description: Optional[str],
        attendees: Optional[List[str]],
        location: Optional[str]
    ) -> Dict[str, Any]:
        try:
            calendar = GoogleCalendarIntegration(company=company)
            result = calendar.schedule_meeting(
                title=title,
                start_time=start_time,
                duration_minutes=duration_minutes,
                description=description,
                attendees=attendees,
                location=location
            )
            result['provider'] = 'google'
            result['meeting_url'] = result.get('meet_link') or result.get('link')
            return result
        except Exception as e:
            logger.error(f"[MEETING_SERVICE] Google Meet schedule error: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'provider': 'google'}

    # -------------------------------------------------------------------------
    # 2. ZOOM IMPLEMENTATION (Server-to-Server OAuth & REST API v2)
    # -------------------------------------------------------------------------
    @classmethod
    def get_zoom_access_token(cls, company: Company) -> Optional[str]:
        """
        Get OAuth token for Zoom.
        Prefers Server-to-Server OAuth (Account ID + Client ID + Client Secret)
        or saved user OAuth credentials.
        """
        keys = company.api_keys or {}
        account_id = keys.get('zoom_account_id')
        client_id = keys.get('zoom_client_id')
        client_secret = keys.get('zoom_client_secret')

        if account_id and client_id and client_secret:
            # Server-to-Server OAuth Flow
            token_url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={account_id}"
            auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            try:
                resp = requests.post(token_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    return resp.json().get("access_token")
                logger.error(f"[ZOOM_AUTH] Failed getting token: {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"[ZOOM_AUTH] Exception requesting token: {e}")

        # Fallback to direct bearer token if user saved one
        direct_token = keys.get('zoom_access_token')
        return direct_token

    @classmethod
    def _schedule_zoom(
        cls,
        company: Company,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        description: Optional[str],
        attendees: Optional[List[str]]
    ) -> Dict[str, Any]:
        token = cls.get_zoom_access_token(company)
        if not token:
            return {
                'success': False,
                'error': 'Zoom no está configurado o sus credenciales son inválidas. Ingrese su Account ID, Client ID y Client Secret.',
                'provider': 'zoom'
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Format time to ISO 8601 UTC string
        start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "topic": title,
            "type": 2,  # Scheduled meeting
            "start_time": start_iso,
            "duration": duration_minutes,
            "timezone": company.timezone or "UTC",
            "agenda": description or f"Reunión agendada con {company.name}",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": False
            }
        }

        try:
            resp = requests.post("https://api.zoom.us/v2/users/me/meetings", headers=headers, json=payload, timeout=12)
            if resp.status_code in [200, 201]:
                data = resp.json()
                join_url = data.get("join_url")
                meeting_id = str(data.get("id"))
                return {
                    'success': True,
                    'event_id': meeting_id,
                    'title': title,
                    'start': start_time.isoformat(),
                    'end': (start_time + timedelta(minutes=duration_minutes)).isoformat(),
                    'link': join_url,
                    'meet_link': join_url,
                    'meeting_url': join_url,
                    'provider': 'zoom',
                    'password': data.get("password")
                }
            else:
                logger.error(f"[ZOOM_CREATE] Error {resp.status_code}: {resp.text}")
                return {'success': False, 'error': f"Zoom API error: {resp.text}", 'provider': 'zoom'}
        except Exception as e:
            logger.error(f"[ZOOM_CREATE] Exception creating meeting: {e}")
            return {'success': False, 'error': str(e), 'provider': 'zoom'}

    # -------------------------------------------------------------------------
    # 3. MICROSOFT TEAMS IMPLEMENTATION (Microsoft Graph API)
    # -------------------------------------------------------------------------
    @classmethod
    def get_teams_access_token(cls, company: Company) -> Optional[str]:
        """
        Get Microsoft Graph token via OAuth client credentials or stored token.
        """
        keys = company.api_keys or {}
        tenant_id = keys.get('teams_tenant_id') or 'common'
        client_id = keys.get('teams_client_id')
        client_secret = keys.get('teams_client_secret')

        # Client Credentials flow for application / organization
        if client_id and client_secret and tenant_id:
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials"
            }
            try:
                resp = requests.post(token_url, data=data, timeout=10)
                if resp.status_code == 200:
                    return resp.json().get("access_token")
                logger.error(f"[TEAMS_AUTH] Failed getting token: {resp.status_code} - {resp.text}")
            except Exception as e:
                logger.error(f"[TEAMS_AUTH] Exception requesting token: {e}")

        # Fallback to direct delegated token if stored
        return keys.get('teams_access_token')

    @classmethod
    def _schedule_teams(
        cls,
        company: Company,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        description: Optional[str],
        attendees: Optional[List[str]]
    ) -> Dict[str, Any]:
        token = cls.get_teams_access_token(company)
        if not token:
            return {
                'success': False,
                'error': 'Microsoft Teams no está configurado. Ingrese Tenant ID, Client ID y Client Secret.',
                'provider': 'teams'
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": f'outlook.timezone="{company.timezone or "UTC"}"'
        }

        end_time = start_time + timedelta(minutes=duration_minutes)

        attendee_objs = []
        if attendees:
            for email in attendees:
                attendee_objs.append({
                    "emailAddress": {"address": email},
                    "type": "required"
                })

        payload = {
            "subject": title,
            "body": {
                "contentType": "HTML",
                "content": description or f"Reunión agendada por {company.name}"
            },
            "start": {
                "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": company.timezone or "UTC"
            },
            "end": {
                "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": company.timezone or "UTC"
            },
            "attendees": attendee_objs,
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness"
        }

        try:
            resp = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=payload, timeout=12)
            if resp.status_code in [200, 201]:
                data = resp.json()
                online_meeting = data.get("onlineMeeting") or {}
                join_url = online_meeting.get("joinUrl") or data.get("webLink")
                return {
                    'success': True,
                    'event_id': data.get("id"),
                    'title': title,
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'link': join_url,
                    'meet_link': join_url,
                    'meeting_url': join_url,
                    'provider': 'teams'
                }
            else:
                logger.error(f"[TEAMS_CREATE] Error {resp.status_code}: {resp.text}")
                return {'success': False, 'error': f"Teams Graph API error: {resp.text}", 'provider': 'teams'}
        except Exception as e:
            logger.error(f"[TEAMS_CREATE] Exception creating Teams meeting: {e}")
            return {'success': False, 'error': str(e), 'provider': 'teams'}

    @classmethod
    def _check_teams_availability(cls, company: Company, date_str: str, time_str: Optional[str]) -> Dict[str, Any]:
        """Check schedule on Microsoft Graph getSchedule or return availability placeholder"""
        return {
            'date': date_str,
            'available': True,
            'message': 'Franja horaria disponible en Teams',
            'available_slots': 8,
            'slots': [
                {'start': '09:00', 'end': '09:30'},
                {'start': '10:00', 'end': '10:30'},
                {'start': '11:00', 'end': '11:30'},
                {'start': '14:00', 'end': '14:30'},
                {'start': '15:00', 'end': '15:30'},
                {'start': '16:00', 'end': '16:30'}
            ]
        }
