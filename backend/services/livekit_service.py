from routing import current_app
"""
LiveKit Service - Voice and Real-time Communication
"""
import os
import json
import secrets
import asyncio
from typing import Dict, Any, Optional
from livekit import api


class LiveKitService:
    """
    LiveKit Integration Service
    Handles Room creation, Token generation, and SIP Dispatching
    """
    
    def __init__(self, company=None):
        self.company = company
        self._api_url = None
        self._api_key = None
        self._api_secret = None
        self._lk_api = None
    
    def _get_credential(self, key: str) -> Optional[str]:
        """Resolve credential: Checks Company API Keys first, then Environment"""
        # 1. Check Company Keys
        if self.company and self.company.api_keys:
            # Map standard keys to what might be in api_keys JSON
            company_key_map = {
                'livekit_url': 'livekit_url',
                'livekit_api_key': 'livekit_api_key', 
                'livekit_api_secret': 'livekit_api_secret'
            }
            json_key = company_key_map.get(key, key)
            value = self.company.api_keys.get(json_key)
            if value:
                return value
        
        # 2. Check Environment Variables (Platform Default)
        env_map = {
            'livekit_url': 'LIVEKIT_URL',
            'livekit_api_key': 'LIVEKIT_API_KEY',
            'livekit_api_secret': 'LIVEKIT_API_SECRET'
        }
        return os.getenv(env_map.get(key, ''))

    def _get_api_client(self) -> api.LiveKitAPI:
        """Create a fresh LiveKit API client (for use within async context)"""
        url = self._get_credential('livekit_url')
        key = self._get_credential('livekit_api_key')
        secret = self._get_credential('livekit_api_secret')
        
        if not url or not key or not secret:
            raise ValueError("LiveKit credentials not configured")
        
        return api.LiveKitAPI(url, key, secret)

    async def _create_room_async(self, name: str) -> Dict[str, Any]:
        """Async implementation of create_room"""
        lk = self._get_api_client()
        try:
            room = await lk.room.create_room(api.CreateRoomRequest(name=name))
            return {'sid': room.sid, 'name': room.name}
        finally:
            await lk.aclose()

    def create_room(self, name: str) -> Dict[str, Any]:
        """Create a new LiveKit room (Sync Wrapper)"""
        return asyncio.run(self._create_room_async(name))

    def create_token(self, room_name: str, identity: str) -> str:
        """Create access token for a participant (Sync, local operation)"""
        # Credentials for token generation don't need async API client
        key = self._get_credential('livekit_api_key')
        secret = self._get_credential('livekit_api_secret')
        
        if not key or not secret:
             raise ValueError("LiveKit credentials not configured")

        token = api.AccessToken(key, secret)
        token.with_identity(identity)
        token.with_name(identity)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
        ))
        return token.to_jwt()

    async def _make_call_async(self, to_number: str, purpose: str, 
                                agent_id: int = None, company_id: int = None,
                                metadata_extras: Dict[str, Any] = None) -> Dict[str, Any]:
        """Async implementation of make_call logic with agent context"""
        lk = self._get_api_client()
        try:
            # 1. Create a room for the call with metadata
            print(f"DEBUG: Creating room for outbound call to {to_number}")
            room_name = f"outbound-{to_number.strip('+')}-{secrets.token_hex(4)}"
            
            # Build metadata for voice agent context
            metadata_dict = {
                "company_id": company_id,
                "agent_id": agent_id,
                "purpose": purpose,
                "call_type": "outbound",
                "destination": to_number
            }
            
            # Merge extras (like gender)
            if metadata_extras:
                metadata_dict.update(metadata_extras)
            
            room_metadata = json.dumps(metadata_dict)
            
            await lk.room.create_room(api.CreateRoomRequest(
                name=room_name,
                metadata=room_metadata
            ))
            print(f"DEBUG: Room created with metadata: {room_metadata}")
            
            # 2. Trigger SIP Call using CreateSIPParticipant
            
            # Resolve Caller ID from settings
            caller_id = self._get_credential('livekit_caller_id')
            if not caller_id:
                print("WARNING: No 'livekit_caller_id' configured in settings.")
            
            print(f"DEBUG: Dialing SIP Participant to {to_number} (From: {caller_id})")
            
            request = api.CreateSIPParticipantRequest(
                sip_trunk_id="", 
                sip_call_to=to_number,
                room_name=room_name,
                participant_identity=f"phone-{to_number}",
            )
            
            # List trunks to find a valid one if needed
            trunks = await lk.sip.list_sip_outbound_trunk(api.ListSIPOutboundTrunkRequest())
            trunk_id = ""
            if trunks.items:
                 # Pick the first trunk
                 trunk_id = trunks.items[0].sip_trunk_id
                 request.sip_trunk_id = trunk_id
            
            print(f"DEBUG: Using Trunk ID: {trunk_id}")
            
            participant = await lk.sip.create_sip_participant(request)
            
            return {
                'success': True,
                'provider': 'livekit',
                'room': room_name,
                'message': f"Calling {to_number} using Trunk {trunk_id}...",
                'participant_id': participant.participant_id
            }
        except Exception as e:
            raise e
        finally:
            await lk.aclose()

    def make_call(self, to_number: str, purpose: str, 
                  agent_id: int = None, company_id: int = None,
                  metadata_extras: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initiate an outbound call via LiveKit SIP Dispatch.
        Executes async logic via asyncio.run()
        
        Args:
            to_number: Destination phone number
            purpose: Purpose of the call (for context)
            agent_id: Optional agent ID for voice personalization
            company_id: Optional company ID for context loading
        """
        try:
            return asyncio.run(self._make_call_async(to_number, purpose, agent_id, company_id, metadata_extras))
            
        except Exception as e:
            print(f"ERROR LiveKit make_call: {e}")
            return {'success': False, 'error': str(e), 'code': 'LIVEKIT_SIP_ERROR'}

