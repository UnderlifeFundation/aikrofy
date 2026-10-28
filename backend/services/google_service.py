from routing import current_app, session, url_for
"""
Google Service - Google Workspace Integration (OAuth 2.0)
Handles Authentication, Calendar, and Sheets
"""
import os
import logging

logger = logging.getLogger(__name__)
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

from models.user import User
from extensions import db

class GoogleService:
    """
    Google Integration Service
    Scopes: Calendar, Sheets, Drive (for listing sheets)
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    # Optional extended scopes if sheets are connected separately later
    SHEETS_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    def __init__(self, user: User = None, company=None):
        self.user = user
        self.company = company or (user.company if user else None)
        self.creds = None
        
        # 1. Try User Credentials (Personal)
        if user and user.google_credentials:
            self.creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                user.google_credentials, self.SCOPES)
        
        # 2. Try Company Credentials (System/Shared) -> This is what Agents use
        elif self.company and self.company.api_keys and self.company.api_keys.get('google_oauth_credentials'):
            self.creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                self.company.api_keys.get('google_oauth_credentials'), self.SCOPES)

    @staticmethod
    def create_flow(redirect_uri=None):
        """Create OAuth flow instance"""
        client_config = {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config=client_config,
            scopes=GoogleService.SCOPES
        )
        
        if redirect_uri:
            flow.redirect_uri = redirect_uri
            print(f"DEBUG: Setting redirect_uri to: {redirect_uri}")
            
        return flow

    def is_authenticated(self):
        """Check if user has valid credentials"""
        if not self.creds:
            return False
            
        if self.creds.expired and self.creds.refresh_token:
            try:
                from google.auth.transport.requests import Request
                self.creds.refresh(Request())
                print("DEBUG: GoogleService - Token refreshed successfully!")
                
                # Persist the refreshed credentials
                self._save_refreshed_credentials()
                
            except Exception as e:
                print(f"DEBUG: Token refresh failed in is_authenticated: {e}")
                return False
                
        return self.creds.valid
    
    def _save_refreshed_credentials(self):
        """Save refreshed credentials back to database"""
        try:
            from extensions import db
            
            updated_creds = {
                'token': self.creds.token,
                'refresh_token': self.creds.refresh_token,
                'token_uri': self.creds.token_uri,
                'client_id': self.creds.client_id,
                'client_secret': self.creds.client_secret,
                'scopes': list(self.creds.scopes) if self.creds.scopes else self.SCOPES
            }
            
            # Save to User if available
            if self.user and self.user.google_credentials:
                self.user.google_credentials = updated_creds
                db.session.commit()
                print("DEBUG: Refreshed token saved to User credentials!")
            
            # Save to Company if available
            elif self.company and self.company.api_keys:
                api_keys = self.company.api_keys.copy() if self.company.api_keys else {}
                api_keys['google_oauth_credentials'] = updated_creds
                self.company.api_keys = api_keys
                db.session.commit()
                print("DEBUG: Refreshed token saved to Company credentials!")
                
        except Exception as e:
            print(f"DEBUG: Failed to save refreshed credentials: {e}")

    # ----------------------------------------------------------------
    # 📅 Calendar API
    # ----------------------------------------------------------------
    
    def list_calendars(self):
        """List user's calendars"""
        if not self.is_authenticated():
            raise ValueError("User not authenticated with Google")
        
        service = build('calendar', 'v3', credentials=self.creds)
        result = service.calendarList().list().execute()
        return result.get('items', [])
        
    def list_upcoming_events(self, calendar_id='primary', max_results=10):
        """List upcoming calendar events"""
        if not self.is_authenticated():
            raise ValueError("User not authenticated with Google")
            
        service = build('calendar', 'v3', credentials=self.creds)
        
        events_result = service.events().list(
            calendarId=calendar_id, 
            timeMin='2020-01-01T00:00:00Z', # TODO: Use datetime.utcnow()
            maxResults=max_results, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])

    def create_event(self, summary, start_time, end_time, description=None, calendar_id='primary'):
        """Create a new calendar event"""
        if not self.is_authenticated():
            raise ValueError("User not authenticated with Google")
            
        service = build('calendar', 'v3', credentials=self.creds)
        
        event = {
            'summary': summary,
            'description': description,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        }
        
        return service.events().insert(calendarId=calendar_id, body=event).execute()

    # ----------------------------------------------------------------
    # 📊 Sheets API & Drive API
    # ----------------------------------------------------------------
    
    def list_sheets(self):
        """List Google Sheets files from Drive"""
        if not self.is_authenticated():
            raise ValueError("User not authenticated with Google")
            
        service = build('drive', 'v3', credentials=self.creds)
        
        # MimeType for Google Sheets
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
        
        results = service.files().list(
            q=query,
            pageSize=20,
            fields="nextPageToken, files(id, name)"
        ).execute()
        
        return results.get('files', [])
    
    def get_sheet_values(self, spreadsheet_id, range_name):
        """Read values from a Google Sheet"""
        if not self.is_authenticated():
            raise ValueError("User not authenticated with Google")
            
        service = build('sheets', 'v4', credentials=self.creds)
        
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        return result.get('values', [])


class GoogleCalendarIntegration:
    """
    Helper class for specific Calendar operations needed by Agents
    """
    def __init__(self, company):
        self.company = company
        self.google_service = GoogleService(company=company)
        
    def get_free_slots(self, date_obj):
        """
        Get free slots for a specific date (9 AM - 5 PM)
        Returns list of dicts with 'start' and 'end' (datetime objects)
        """
        if not self.google_service.is_authenticated():
            logger.debug("Company not authenticated with Google")
            return []
            
        import pytz
        from datetime import datetime, timedelta, time
        
        # Define working hours from Company settings (or defaults)
        COMPANY_TZ = pytz.timezone(self.company.timezone or 'UTC')
        
        # Default working hours: 8 AM - 8 PM (broad range to cover most cases)
        start_hour = 8
        end_hour = 20
        
        # Start and End of working day in Company TZ
        work_start = COMPANY_TZ.localize(datetime.combine(date_obj, time(start_hour, 0)))
        work_end = COMPANY_TZ.localize(datetime.combine(date_obj, time(end_hour, 0)))
        
        # Fetch events for that day
        service = build('calendar', 'v3', credentials=self.google_service.creds)
        
        # Query typical primary calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=work_start.isoformat(),
            timeMax=work_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Calculate Free Slots
        free_slots = []
        current_time = work_start
        
        # Sort events just in case
        events.sort(key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
        
        for event in events:
            # Parse event start/end
            start_str = event['start'].get('dateTime')
            end_str = event['end'].get('dateTime')
            
            if not start_str: # All day event
                continue
            
            # Remove Z if present to handle isoformat correctly with fromisoformat in older pythons if needed, 
            # but usually fromisoformat handles +offsets. Z requires replace.
            if start_str.endswith('Z'): start_str = start_str[:-1] + '+00:00'
            if end_str.endswith('Z'): end_str = end_str[:-1] + '+00:00'

            ev_start = datetime.fromisoformat(start_str)
            
            if ev_start > current_time:
                # Found a gap
                gap_duration = (ev_start - current_time).total_seconds() / 60
                if gap_duration >= 30: # Minimum 30 min slot
                    # Generate slots in 30 min chunks
                    temp = current_time
                    while temp + timedelta(minutes=30) <= ev_start:
                        free_slots.append({
                            'start': temp,
                            'end': temp + timedelta(minutes=30)
                        })
                        temp += timedelta(minutes=30)
            
            # Move pointer
            ev_end = datetime.fromisoformat(end_str)
            if ev_end > current_time:
                current_time = ev_end
                
        # Check remaining time after last event
        if current_time < work_end:
            temp = current_time
            while temp + timedelta(minutes=30) <= work_end:
                free_slots.append({
                    'start': temp,
                    'end': temp + timedelta(minutes=30)
                })
                temp += timedelta(minutes=30)
                
                
        return free_slots

    def schedule_meeting(self, title, start_time, duration_minutes, description, attendees):
        """
        Schedule a meeting on Google Calendar
        start_time: datetime object (should be timezone aware or UTC)
        """
        if not self.google_service.is_authenticated():
            return {'success': False, 'error': 'Not authenticated'}
            
        from datetime import timedelta
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Convert to ISO format strings for the API
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()
        
        # Add attendees
        attendee_list = [{'email': email} for email in attendees]
        
        try:
            service = build('calendar', 'v3', credentials=self.google_service.creds)
            
            event_body = {
                'summary': title,
                'description': description,
                'start': {'dateTime': start_iso}, # Timezone is embedded in iso string if aware
                'end': {'dateTime': end_iso},
                'attendees': attendee_list,
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"req-{int(start_time.timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            }
            
            event = service.events().insert(
                calendarId='primary', 
                body=event_body, 
                conferenceDataVersion=1,
                sendUpdates='all'
            ).execute()
            
            return {
                'success': True,
                'event_id': event.get('id'),
                'meet_link': event.get('hangoutLink')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

