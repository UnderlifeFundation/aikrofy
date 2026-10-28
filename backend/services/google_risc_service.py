from routing import current_app
import jwt
import logging
import requests
import os

logger = logging.getLogger(__name__)

from extensions import db
from models.user import User
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class GoogleRiscService:
    @staticmethod
    def get_google_public_keys():
        """Fetch Google public keys from JWKS URI as required by RISC protocol"""
        # RISC configuration discovery: https://accounts.google.com/.well-known/risc-configuration
        # Standard certs endpoint for Google Accounts
        jwks_uri = "https://www.googleapis.com/oauth2/v3/certs"
        try:
            response = requests.get(jwks_uri)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"ERROR: GoogleRiscService - Failed to fetch public keys: {e}")
            return None

    @staticmethod
    def validate_risc_token(token):
        """Decode and validate the security event token (JWT) according to RISC/RISC Specs"""
        try:
            # 1. Unverified header to find Key ID (kid)
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            # 2. Get Google public keys
            jwks = GoogleRiscService.get_google_public_keys()
            if not jwks or 'keys' not in jwks:
                return None
            
            # 3. Find the specific key
            key_data = next((k for k in jwks['keys'] if k['kid'] == kid), None)
            if not key_data:
                print(f"ERROR: GoogleRiscService - Key ID {kid} not found in Google certs")
                return None
            
            # 4. Construct public key using python-jose or jwt (PyJWT) with cryptography
            # PyJWT requires the key to be in PEM or similar if not using a jwks client
            from jwt.algorithms import RSAAlgorithm
            public_key = RSAAlgorithm.from_jwk(key_data)

            # 5. Decode and verify payload
            # Important: RS256 signature is required
            # Auditor must be one of our Client IDs
            # Issuer must be https://accounts.google.com
            # Note: RISC tokens represent historical events and do not expire (verify_exp = False)
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            
            payload = jwt.decode(
                token,
                key=public_key,
                algorithms=['RS256'],
                audience=client_id,
                issuer='https://accounts.google.com',
                options={"verify_exp": False}
            )
            return payload
        except Exception as e:
            print(f"ERROR: GoogleRiscService - Token Validation Failure: {e}")
            return None

    @staticmethod
    def handle_event(payload):
        """Handle the verified security event payload"""
        events = payload.get('events', {})
        if not events:
            return
            
        # Example Event Payload Keys:
        # https://schemas.openid.net/secevent/risc/event-type/account-disabled
        # https://schemas.openid.net/secevent/risc/event-type/sessions-revoked
        # https://schemas.openid.net/secevent/oauth/event-type/tokens-revoked
        
        for event_type, details in events.items():
            print(f"INFO: GoogleRiscService - Processing Event: {event_type}")
            subject = details.get('subject', {})
            
            # The subject can be an email or a 'sub' (Google User ID)
            user_id_sub = subject.get('sub')
            email = subject.get('email')
            
            user = None
            if user_id_sub:
                # Optimized search would require a separate sub field, 
                # but for now we look at the JSON if necessary
                # Best first attempt: Check by email if available
                if email:
                    user = User.query.filter_by(email=email).first()
                
                # Fallback: Search in credentials if we store them (TODO)
            
            if user:
                GoogleRiscService._execute_security_action(user, event_type)

    @staticmethod
    def _execute_security_action(user, event_type):
        """Perform remediation based on event type"""
        # Critical events that warrant immediate locking
        if any(keyword in event_type for keyword in ['account-disabled', 'sessions-revoked', 'hijacking']):
            user.is_active = False # Disable account access
            user.google_credentials = None # Revoke stored tokens
            db.session.commit()
            logger.warning(f"GoogleRiscService - Disabled user {user.email} due to {event_type}")
            
        # Token specific revocations
        elif 'tokens-revoked' in event_type or 'token-revoked' in event_type:
            user.google_credentials = None
            db.session.commit()
            logger.info(f"GoogleRiscService - Cleared Google Tokens for user {user.email}")
