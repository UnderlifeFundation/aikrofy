"""
Attribution Service - Handles UTM tracking, Click-to-WhatsApp Ads (CTWA), and Web Session (GCLID) mappings.
"""
import re
import logging
from urllib.parse import urlparse, parse_qs
from datetime import datetime

from extensions import db
from models.contact_attribution import ContactAttribution, WebReferralSession

logger = logging.getLogger(__name__)

class AttributionService:
    @staticmethod
    def process_webhook_referral(company_id: int, customer_id: int, referral_data: dict) -> ContactAttribution:
        """
        Extract campaign parameters from a Meta webhook referral payload (CTWA) and log the attribution.
        """
        if not referral_data:
            return None

        logger.info(f"Processing CTWA referral for company {company_id}, customer {customer_id}: {referral_data}")

        # 1. Initialize campaign fields
        utm_source = referral_data.get('utm_source')
        utm_medium = referral_data.get('utm_medium')
        utm_campaign = referral_data.get('utm_campaign')
        utm_term = referral_data.get('utm_term')
        utm_content = referral_data.get('utm_content')
        meta_click_id = referral_data.get('ctwa_clid')

        # 2. Extract UTMs from source_url if provided and parameters are missing
        source_url = referral_data.get('source_url')
        if source_url:
            try:
                parsed = urlparse(source_url)
                qs = parse_qs(parsed.query)
                
                # Fetch query parameters if not already present in payload
                if not utm_source and 'utm_source' in qs: utm_source = qs['utm_source'][0]
                if not utm_medium and 'utm_medium' in qs: utm_medium = qs['utm_medium'][0]
                if not utm_campaign and 'utm_campaign' in qs: utm_campaign = qs['utm_campaign'][0]
                if not utm_term and 'utm_term' in qs: utm_term = qs['utm_term'][0]
                if not utm_content and 'utm_content' in qs: utm_content = qs['utm_content'][0]
                if not meta_click_id and 'fbclid' in qs: meta_click_id = qs['fbclid'][0]
                if not meta_click_id and 'gclid' in qs: meta_click_id = qs['gclid'][0]
            except Exception as e:
                logger.error(f"Error parsing source_url in referral: {e}")

        # Default source to Meta Ads if none found
        if not utm_source:
            utm_source = 'facebook_ads' if referral_data.get('source_type') == 'ad' else 'meta'
        if not utm_medium:
            utm_medium = 'cpc' if referral_data.get('source_type') == 'ad' else 'social'

        # 3. Prevent duplicate attributions for the customer
        attribution = ContactAttribution.query.filter_by(
            company_id=company_id,
            customer_id=customer_id
        ).first()

        if not attribution:
            logger.info(f"Creating new ContactAttribution for customer {customer_id}")
            attribution = ContactAttribution(
                company_id=company_id,
                customer_id=customer_id
            )
            db.session.add(attribution)
        else:
            logger.info(f"Updating existing ContactAttribution for customer {customer_id}")

        # Update properties
        attribution.utm_source = utm_source
        attribution.utm_medium = utm_medium
        attribution.utm_campaign = utm_campaign
        attribution.utm_term = utm_term
        attribution.utm_content = utm_content
        attribution.meta_click_id = meta_click_id
        attribution.referral_data = referral_data
        
        db.session.commit()
        return attribution

    @staticmethod
    def process_message_for_reference_code(company_id: int, customer_id: int, message_body: str) -> bool:
        """
        Inspect message body for REF-XXXX code, find matching web session, and link campaign attribution.
        """
        if not message_body:
            return False

        # Match pattern: REF- followed by 4 or more alphanumeric characters
        match = re.search(r'REF-[A-Z0-9]{4,10}', message_body, re.IGNORECASE)
        if not match:
            return False

        ref_code = match.group(0).upper()
        logger.info(f"Detected reference code {ref_code} for customer {customer_id} in company {company_id}")

        # Find matching session
        session = WebReferralSession.query.filter_by(
            company_id=company_id,
            reference_id=ref_code
        ).first()

        if not session:
            logger.warning(f"No active web referral session found for reference code {ref_code}")
            return False

        # Link attribution
        attribution = ContactAttribution.query.filter_by(
            company_id=company_id,
            customer_id=customer_id
        ).first()

        if not attribution:
            attribution = ContactAttribution(
                company_id=company_id,
                customer_id=customer_id
            )
            db.session.add(attribution)

        attribution.utm_source = session.utm_source
        attribution.utm_medium = session.utm_medium
        attribution.utm_campaign = session.utm_campaign
        attribution.utm_term = session.utm_term
        attribution.utm_content = session.utm_content
        attribution.google_click_id = session.google_click_id
        
        # Keep track of GCLID mapping origin
        attribution.referral_data = {
            'resolved_via_ref_code': ref_code,
            'resolved_at': datetime.utcnow().isoformat()
        }

        # Delete the temporary session to avoid re-use
        db.session.delete(session)
        db.session.commit()

        logger.info(f"Attribution successfully linked via Ref Code {ref_code} to customer {customer_id}")
        return True

    @staticmethod
    def create_web_session(company_id: int, reference_id: str, utm_data: dict, gclid: str = None) -> WebReferralSession:
        """
        Create a new temporary web referral session mapping to be resolved later.
        """
        # Enforce uppercase reference code
        ref_code = reference_id.strip().upper()
        
        # Check if reference already exists for company (to prevent duplicate key errors)
        existing = WebReferralSession.query.filter_by(
            company_id=company_id,
            reference_id=ref_code
        ).first()
        
        if existing:
            db.session.delete(existing)
            db.session.commit()

        session = WebReferralSession(
            company_id=company_id,
            reference_id=ref_code,
            utm_source=utm_data.get('utm_source'),
            utm_medium=utm_data.get('utm_medium'),
            utm_campaign=utm_data.get('utm_campaign'),
            utm_term=utm_data.get('utm_term'),
            utm_content=utm_data.get('utm_content'),
            google_click_id=gclid
        )
        db.session.add(session)
        db.session.commit()
        return session
