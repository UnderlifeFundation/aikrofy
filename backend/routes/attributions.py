"""
Attribution Routes - Public and administrative endpoints for campaign tracking.
"""
import random
import string
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db

from services.attribution_service import AttributionService
from models.contact_attribution import ContactAttribution

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/attributions", tags=["attribution"])

def generate_reference_code(db: Session, company_id: int) -> str:
    """Generate a unique 4-character uppercase alphanumeric reference code prefixed with REF-."""
    from models.contact_attribution import WebReferralSession
    
    while True:
        code_chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        ref_id = f"REF-{code_chars}"
        
        # Ensure uniqueness
        exists = db.query(WebReferralSession).filter_by(
            company_id=company_id,
            reference_id=ref_id
        ).first()
        
        if not exists:
            return ref_id

@router.post("/track-click")
async def track_click(request: Request, db: Session = Depends(get_db)):
    """
    Public endpoint for client website landing pages to log UTMs/GCLID.
    Returns a unique REF-XXXX code to be pre-filled in the WhatsApp click URL.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    company_id = data.get("company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")

    utm_data = {
        "utm_source": data.get("utm_source"),
        "utm_medium": data.get("utm_medium"),
        "utm_campaign": data.get("utm_campaign"),
        "utm_term": data.get("utm_term"),
        "utm_content": data.get("utm_content")
    }
    gclid = data.get("gclid")

    # Generate reference code
    ref_code = generate_reference_code(db, int(company_id))

    try:
        # Create session mapping
        AttributionService.create_web_session(
            company_id=int(company_id),
            reference_id=ref_code,
            utm_data=utm_data,
            gclid=gclid
        )
        logger.info(f"Registered web referral session {ref_code} for company {company_id}")
        return {
            "success": True,
            "reference_id": ref_code,
            "whatsapp_prefilled_text": f"Hola, vengo de su anuncio. Ref: {ref_code}"
        }
    except Exception as e:
        logger.error(f"Error registering web click attribution session: {e}")
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {str(e)}")


@router.get("/customer/{customer_id}")
async def get_customer_attribution(customer_id: int, db: Session = Depends(get_db)):
    """
    Retrieve campaign attribution data for a specific customer.
    """
    attribution = db.query(ContactAttribution).filter_by(customer_id=customer_id).first()
    if not attribution:
        return {"success": True, "attribution": None}
    
    return {
        "success": True,
        "attribution": attribution.to_dict()
    }
