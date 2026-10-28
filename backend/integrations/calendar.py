"""
Google Calendar Integration
Meeting scheduling and availability
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError


class GoogleCalendarIntegration:
    """Google Calendar integration for scheduling (supports OAuth and Service Account)"""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(
        self,
        company=None,
        credentials_path: Optional[str] = None,
        calendar_id: str = 'primary'
    ):
        """
        Initialize Google Calendar integration
        
        Args:
            company: Company model instance (for OAuth from DB)
            credentials_path: Path to service account JSON file (fallback)
            calendar_id: Calendar ID to use (default: primary)
        """
        self.company = company
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self._service = None
        
        # If company provided, get calendar_id and credentials from company settings
        if company and company.api_keys:
            self.calendar_id = company.api_keys.get('google_calendar_id', 'primary')
            self._oauth_creds = company.api_keys.get('google_oauth_credentials')
        else:
            self.calendar_id = calendar_id
            self._oauth_creds = None
    
    def _refresh_and_save_credentials(self, credentials: Credentials) -> Credentials:
        """
        Attempt to refresh expired credentials and save to database
        
        Args:
            credentials: The expired Google credentials
            
        Returns:
            Refreshed credentials
            
        Raises:
            RefreshError: If refresh fails
        """
        print("DEBUG: Token expired, attempting refresh...")
        try:
            credentials.refresh(Request())
            print("DEBUG: Token refreshed successfully!")
            
            # Save the refreshed credentials back to the database
            if self.company and self._oauth_creds:
                # Import here to avoid circular imports
                from extensions import db
                
                # Update the stored credentials with new token
                updated_creds = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': list(credentials.scopes) if credentials.scopes else self.SCOPES
                }
                
                # Update company api_keys
                api_keys = self.company.api_keys.copy() if self.company.api_keys else {}
                api_keys['google_oauth_credentials'] = updated_creds
                self.company.api_keys = api_keys
                
                db.session.commit()
                print("DEBUG: Refreshed token saved to database!")
                
            return credentials
            
        except RefreshError as e:
            print(f"DEBUG: Token refresh failed: {e}")
            raise RefreshError(
                f"Google Calendar token refresh failed. Please re-connect your Google account in Settings. Error: {e}"
            )
    
    def _get_service(self):
        """Get or create Calendar service (OAuth or Service Account)"""
        if self._service:
            return self._service
        
        # Try OAuth first (from company credentials)
        if self._oauth_creds:
            credentials = Credentials(
                token=self._oauth_creds.get('token'),
                refresh_token=self._oauth_creds.get('refresh_token'),
                token_uri=self._oauth_creds.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=self._oauth_creds.get('client_id'),
                client_secret=self._oauth_creds.get('client_secret'),
                scopes=self._oauth_creds.get('scopes', self.SCOPES)
            )
            
            # Check if token is expired and try to refresh
            if credentials.expired and credentials.refresh_token:
                credentials = self._refresh_and_save_credentials(credentials)
            elif not credentials.valid and credentials.refresh_token:
                # Token may be invalid for other reasons, try refresh
                credentials = self._refresh_and_save_credentials(credentials)
            
            self._service = build('calendar', 'v3', credentials=credentials)
            return self._service
        
        # Fallback to service account
        if self.credentials_path and os.path.exists(self.credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            self._service = build('calendar', 'v3', credentials=credentials)
            return self._service
        
        raise ValueError("No Google credentials configured - set OAuth in company settings or provide service account path")
    
    def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events
        
        Args:
            start_time: Start of time range (default: now)
            end_time: End of time range (default: 7 days from now)
            max_results: Maximum number of events to return
        
        Returns:
            List of calendar events
        """
        service = self._get_service()
        
        if not start_time:
            start_time = datetime.utcnow()
        if not end_time:
            end_time = start_time + timedelta(days=7)
        
        # Format datetime for Google API (must be RFC3339)
        # If timezone-aware, use isoformat() directly (has offset)
        # If naive, assume UTC and add 'Z'
        def format_for_google(dt):
            if dt.tzinfo is not None:
                # Already has timezone, use isoformat (will include +00:00 or similar)
                # But Google prefers 'Z' for UTC, so convert +00:00 to Z
                iso = dt.isoformat()
                return iso.replace('+00:00', 'Z')
            else:
                # Naive datetime, assume UTC
                return dt.isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=self.calendar_id,
            timeMin=format_for_google(start_time),
            timeMax=format_for_google(end_time),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return [{
            'id': event['id'],
            'summary': event.get('summary', 'No title'),
            'start': event['start'].get('dateTime', event['start'].get('date')),
            'end': event['end'].get('dateTime', event['end'].get('date')),
            'description': event.get('description', ''),
            'attendees': [a.get('email') for a in event.get('attendees', [])]
        } for event in events]
    
    def get_free_slots(
        self,
        date: datetime,
        duration_minutes: int = 30,
        start_hour: int = 9,
        end_hour: int = 17
    ) -> List[Dict[str, datetime]]:
        """
        Get available time slots for a given date
        
        Args:
            date: Date to check
            duration_minutes: Length of slots in minutes
            start_hour: Start of business hours
            end_hour: End of business hours
        
        Returns:
            List of available time slots
        """
        # Get events for the day
        # Ensure date is timezone-aware or treat as UTC
        if date.tzinfo is None:
            # If naive, assume it represents the intended time in UTC for simplicity of calculation internally
            # or simply attach UTC timezone
            from datetime import timezone
            date = date.replace(tzinfo=timezone.utc)
            
        start_of_day = date.replace(hour=start_hour, minute=0, second=0)
        end_of_day = date.replace(hour=end_hour, minute=0, second=0)
        
        # We need events from Google (which are UTC/Offset aware)
        events = self.get_events(start_time=start_of_day, end_time=end_of_day, max_results=50)
        
        # Build list of busy times (normalized to UTC for comparison)
        busy_times = []
        for event in events:
            # Parse Google ISO format
            start_str = event['start'].replace('Z', '+00:00')
            end_str = event['end'].replace('Z', '+00:00')
            
            start = datetime.fromisoformat(start_str)
            end = datetime.fromisoformat(end_str)
            
            # Ensure they are comparable with our start_of_day (convert to same timezone)
            if start.tzinfo is None:
                 start = start.replace(tzinfo=timezone.utc)
            else:
                 start = start.astimezone(timezone.utc)
                 
            if end.tzinfo is None:
                 end = end.replace(tzinfo=timezone.utc)
            else:
                 end = end.astimezone(timezone.utc)
                 
            busy_times.append((start, end))
        
        # Find free slots
        free_slots = []
        current_time = start_of_day
        slot_duration = timedelta(minutes=duration_minutes)
        
        while current_time + slot_duration <= end_of_day:
            slot_end = current_time + slot_duration
            
            # Check if slot is free
            is_free = True
            for busy_start, busy_end in busy_times:
                # Standard intersection check: (StartA <= EndB) and (EndA >= StartB)
                # Here: (current_time < busy_end) and (slot_end > busy_start)
                if current_time < busy_end and slot_end > busy_start:
                    is_free = False
                    break
            
            if is_free:
                free_slots.append({
                    'start': current_time,
                    'end': slot_end
                })
            
            current_time += slot_duration
        
        return free_slots
    
    def schedule_meeting(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int = 30,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a new meeting
        
        Args:
            title: Meeting title
            start_time: Start time
            duration_minutes: Duration in minutes
            description: Meeting description
            attendees: List of attendee email addresses
            location: Meeting location
        
        Returns:
            Created event details
        """
        service = self._get_service()
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC'
            }
        }
        
        if description:
            event['description'] = description
        
        if location:
            event['location'] = location
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        # Add Google Meet conference data
        event['conferenceData'] = {
            'createRequest': {
                'requestId': f"meet-{int(start_time.timestamp())}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
        
        created_event = service.events().insert(
            calendarId=self.calendar_id,
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        return {
            'success': True,
            'event_id': created_event['id'],
            'title': title,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'link': created_event.get('htmlLink'),
            'meet_link': created_event.get('hangoutLink'),
            'attendees': attendees or []
        }
    
    def cancel_meeting(self, event_id: str) -> Dict[str, Any]:
        """
        Cancel/delete a meeting
        
        Args:
            event_id: Event ID to cancel
        
        Returns:
            Cancellation result
        """
        service = self._get_service()
        
        try:
            service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            
            return {
                'success': True,
                'message': 'Meeting cancelled'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_availability(
        self,
        date_str: str,
        time_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check availability for a specific date/time
        
        Args:
            date_str: Date string (YYYY-MM-DD)
            time_str: Optional time string (HH:MM)
        
        Returns:
            Availability information
        """
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return {
                'available': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }
        
        free_slots = self.get_free_slots(date)
        
        if time_str:
            try:
                time = datetime.strptime(time_str, '%H:%M').time()
                requested_datetime = datetime.combine(date.date(), time)
                
                for slot in free_slots:
                    if slot['start'] <= requested_datetime < slot['end']:
                        return {
                            'available': True,
                            'date': date_str,
                            'time': time_str,
                            'message': f'Time slot is available!'
                        }
                
                return {
                    'available': False,
                    'date': date_str,
                    'time': time_str,
                    'message': 'Requested time is not available',
                    'alternative_slots': [
                        {'start': s['start'].strftime('%H:%M'), 'end': s['end'].strftime('%H:%M')}
                        for s in free_slots[:5]
                    ]
                }
            except ValueError:
                return {
                    'available': False,
                    'error': 'Invalid time format. Use HH:MM'
                }
        
        return {
            'date': date_str,
            'available_slots': len(free_slots),
            'slots': [
                {'start': s['start'].strftime('%H:%M'), 'end': s['end'].strftime('%H:%M')}
                for s in free_slots
            ]
        }
