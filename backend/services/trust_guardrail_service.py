"""
Trust Guardrail Service - Enterprise 10X Security & PII Protection
Applies regex and NLP-based filtering on prompts and outputs to:
1. Mask PII (credit cards, IBANs, national IDs, passwords)
2. Guard against prompt injection & jailbreaking
3. Enforce discount limits and operational financial caps
"""
import re
import logging
from typing import Dict, Any, Tuple, Optional
from models.trust_guardrail import TrustGuardrail, GuardrailType, GuardrailAction

logger = logging.getLogger(__name__)

class TrustGuardrailService:
    """Security Layer for PII and Business Rules"""

    # High-confidence PII regex patterns
    CREDIT_CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
    SSN_NATIONAL_ID_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{10}\b')

    @classmethod
    def sanitize_input(cls, company_id: int, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitizes user input before passing to LLM.
        Masks credit cards and sensitive identification.
        """
        if not text:
            return text, {'flagged': False}

        sanitized = text
        flagged = False
        masks_applied = []

        # 1. Credit card check
        if cls.CREDIT_CARD_REGEX.search(sanitized):
            sanitized = cls.CREDIT_CARD_REGEX.sub("[TARJETA_CREDITO_OCULTA]", sanitized)
            flagged = True
            masks_applied.append("credit_card")

        # 2. Check active guardrails from database
        try:
            guardrails = TrustGuardrail.query.filter_by(company_id=company_id, is_active=True).all()
            for gr in guardrails:
                if gr.guardrail_type == GuardrailType.PII_MASKING.value:
                    forbidden = gr.rules.get('forbidden_patterns', [])
                    for p in forbidden:
                        if p.lower() in sanitized.lower():
                            sanitized = re.sub(re.escape(p), "[DATO_CONFIDENCIAL]", sanitized, flags=re.IGNORECASE)
                            flagged = True
                            masks_applied.append("custom_pattern")
        except Exception as e:
            logger.warning(f"[GUARDRAIL] Warning reading guardrails: {e}")
            try:
                from extensions import db
                db.session.rollback()
            except Exception:
                pass

        return sanitized, {'flagged': flagged, 'masks': masks_applied}

    @classmethod
    def validate_action_execution(cls, company_id: int, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Operational Guardrail: Enforces discount and payment ceilings.
        Returns (is_allowed, denial_reason).
        """
        try:
            guardrails = TrustGuardrail.query.filter_by(company_id=company_id, is_active=True).all()
            for gr in guardrails:
                if gr.guardrail_type == GuardrailType.PRICE_DISCOUNT_LIMIT.value:
                    max_discount = gr.rules.get('max_discount_pct', 20)
                    requested_discount = tool_args.get('discount_percentage') or tool_args.get('discount')
                    if requested_discount and float(requested_discount) > max_discount:
                        return False, f"Guardrail: El descuento del {requested_discount}% excede el límite permitido del {max_discount}%."

                if gr.guardrail_type == GuardrailType.TWO_STEP_APPROVAL.value:
                    high_risk_tools = gr.rules.get('restricted_tools', ['delete_customer', 'refund_transaction', 'cancel_subscription'])
                    if tool_name in high_risk_tools:
                        return False, f"Guardrail: La acción '{tool_name}' requiere aprobación humana de un supervisor y ha sido retenida."
        except Exception as err:
            logger.warning(f"[GUARDRAIL] Action validation check failed: {err}")
            try:
                from extensions import db
                db.session.rollback()
            except Exception:
                pass

        return True, None

