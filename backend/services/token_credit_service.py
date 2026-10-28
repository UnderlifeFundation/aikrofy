"""
Token and Credit Billing Service - Aikrofy Engine
Calculates real LLM token costs, Whisper STT, Edge-TTS audio processing costs,
and enforces credit consumption with an ~85% gross margin.

Formula:
  Real API Cost = (Input Tokens * Input Price) + (Output Tokens * Output Price) + Extra Services
  Billed Cost (USD) = Real API Cost / (1 - Margin)   [Default Margin: 0.85 -> Factor ~6.667x]
  Aikrofy Credits = ceil(Billed Cost / CREDIT_USD_VALUE) [Default: 1 Credit = $0.001 USD, Min: 1 credit]
"""
import math
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Default value: 1 Credit = $0.001 USD (1,000 credits = $1.00 USD)
DEFAULT_CREDIT_USD_VALUE = 0.001
DEFAULT_TARGET_MARGIN = 0.85

# Official Model Pricing (per 1 Million Tokens in USD) - Late 2025 / 2026 Rates
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # --- OpenAI ---
    'gpt-5-nano': {'input': 0.05, 'output': 0.40, 'cached_input': 0.005},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60, 'cached_input': 0.075},
    'gpt-4o': {'input': 2.50, 'output': 10.00, 'cached_input': 1.25},
    'gpt-4-turbo': {'input': 10.00, 'output': 30.00, 'cached_input': 5.00},
    'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50, 'cached_input': 0.50},
    'o3-mini': {'input': 1.10, 'output': 4.40, 'cached_input': 0.55},
    'o1': {'input': 15.00, 'output': 60.00, 'cached_input': 7.50},
    'o1-mini': {'input': 1.10, 'output': 4.40, 'cached_input': 0.55},

    # --- Anthropic ---
    'claude-haiku-4.5': {'input': 1.00, 'output': 5.00, 'cached_input': 0.10},
    'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25, 'cached_input': 0.03},
    'claude-3-5-haiku-20241022': {'input': 0.80, 'output': 4.00, 'cached_input': 0.08},
    'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00, 'cached_input': 0.30},
    'claude-sonnet-5': {'input': 5.00, 'output': 25.00, 'cached_input': 0.50},
    'claude-opus-5': {'input': 10.00, 'output': 50.00, 'cached_input': 1.00},
    'claude-3-opus-20240229': {'input': 15.00, 'output': 75.00, 'cached_input': 1.50},

    # --- Google ---
    'gemini-3.1-flash-lite': {'input': 0.25, 'output': 1.50, 'cached_input': 0.05},
    'gemini-3-flash': {'input': 0.50, 'output': 3.00, 'cached_input': 0.10},
    'gemini-3.5-flash': {'input': 1.50, 'output': 9.00, 'cached_input': 0.30},
    'gemini-3.1-pro': {'input': 2.00, 'output': 12.00, 'cached_input': 0.50},
    'gemini-1.5-flash': {'input': 0.075, 'output': 0.30, 'cached_input': 0.01875},
    'gemini-1.5-pro': {'input': 1.25, 'output': 5.00, 'cached_input': 0.3125},
    'gemini-2.0-flash': {'input': 0.10, 'output': 0.40, 'cached_input': 0.025},
}

# Voice & Media Processing Cost Rates (USD)
VOICE_PRICING = {
    # STT Whisper per minute (approx $0.006/min for cloud, or infrastructure cost for media.weblifetech.com)
    'stt_per_minute': 0.006,
    # Fallback per request estimate if duration is not tracked (avg 15s audio)
    'stt_per_request': 0.0015,
    # TTS per 1,000 characters (Edge-TTS / Elevenlabs / OpenAI TTS)
    'tts_per_1k_chars': 0.0015,
}


class TokenCreditService:
    """Service to calculate LLM token costs and manage real-time credit deductions with target margin."""

    @staticmethod
    def get_model_pricing(model_name: Optional[str]) -> Dict[str, float]:
        """Normalizes model name and returns input/output cost per 1M tokens."""
        if not model_name:
            return MODEL_PRICING['gpt-5-nano']

        model_clean = model_name.lower().strip()

        # Exact match
        if model_clean in MODEL_PRICING:
            return MODEL_PRICING[model_clean]

        # Substring / family matching
        for k, v in MODEL_PRICING.items():
            if k in model_clean or model_clean in k:
                return v

        if 'nano' in model_clean:
            return MODEL_PRICING['gpt-5-nano']
        if 'mini' in model_clean or 'flash-lite' in model_clean:
            return MODEL_PRICING['gpt-4o-mini']
        if 'claude' in model_clean:
            return MODEL_PRICING['claude-haiku-4.5']
        if 'gemini' in model_clean:
            return MODEL_PRICING['gemini-3.1-flash-lite']
        if '4o' in model_clean:
            return MODEL_PRICING['gpt-4o']

        # Default conservative fallback
        return MODEL_PRICING['gpt-4o-mini']

    @classmethod
    def calculate_cost_and_credits(
        cls,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: Optional[str] = None,
        cached_tokens: int = 0,
        stt_duration_seconds: float = 0.0,
        stt_requests: int = 0,
        tts_characters: int = 0,
        margin: float = DEFAULT_TARGET_MARGIN,
        credit_usd_value: float = DEFAULT_CREDIT_USD_VALUE,
        min_credits: int = 1,
        is_byok: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates raw API cost, retail price with margin, and total credits to charge.

        If is_byok=True (Bring Your Own Key):
          - Company pays LLM tokens directly to their provider (OpenAI, Anthropic, Google).
          - Aikrofy charges $0.00 for LLM tokens.
          - aikrofy charges only a nominal LEM security verification fee (default 1 credit).
        """
        pricing = cls.get_model_pricing(model)
        
        standard_prompt_tokens = max(0, prompt_tokens - cached_tokens)
        
        # Token costs per 1,000,000 tokens
        input_cost = (standard_prompt_tokens / 1_000_000.0) * pricing['input']
        cached_input_cost = (cached_tokens / 1_000_000.0) * pricing.get('cached_input', pricing['input'] * 0.5)
        output_cost = (completion_tokens / 1_000_000.0) * pricing['output']
        
        llm_raw_cost = input_cost + cached_input_cost + output_cost

        # Voice STT processing cost
        stt_raw_cost = 0.0
        if stt_duration_seconds > 0:
            stt_raw_cost = (stt_duration_seconds / 60.0) * VOICE_PRICING['stt_per_minute']
        elif stt_requests > 0:
            stt_raw_cost = stt_requests * VOICE_PRICING['stt_per_request']

        # Voice TTS synthesis cost
        tts_raw_cost = 0.0
        if tts_characters > 0:
            tts_raw_cost = (tts_characters / 1000.0) * VOICE_PRICING['tts_per_1k_chars']

        # If BYOK is active, LLM token cost billed to customer is waived
        if is_byok:
            effective_raw_cost = stt_raw_cost + tts_raw_cost
            lem_protection_credits = 1  # Fixed micro-fee for LEM verification & anti-hallucination
            credits_to_deduct = max(min_credits, lem_protection_credits)
            billed_cost_usd = 0.0
        else:
            total_raw_cost = llm_raw_cost + stt_raw_cost + tts_raw_cost
            effective_raw_cost = total_raw_cost
            margin_clamped = min(max(margin, 0.50), 0.98) # Keep within 50% - 98%
            multiplier = 1.0 / (1.0 - margin_clamped)
            billed_cost_usd = total_raw_cost * multiplier
            raw_credits = billed_cost_usd / credit_usd_value
            credits_to_deduct = max(min_credits, math.ceil(raw_credits)) if total_raw_cost > 0 else min_credits

        return {
            'raw_cost_usd': round(effective_raw_cost, 6),
            'billed_cost_usd': round(billed_cost_usd, 6),
            'credits_to_deduct': credits_to_deduct,
            'is_byok': is_byok,
            'margin_applied': 0.0 if is_byok else margin_clamped,
            'breakdown': {
                'model': model or 'default',
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens,
                'cached_tokens': cached_tokens,
                'llm_cost_usd': round(llm_raw_cost, 6),
                'stt_cost_usd': round(stt_raw_cost, 6),
                'tts_cost_usd': round(tts_raw_cost, 6)
            }
        }

    @classmethod
    def deduct_company_credits(
        cls,
        company,
        credits_to_deduct: int,
        reason: str = "ai_interaction",
        db_session = None
    ) -> Tuple[bool, int, str]:
        """
        Deducts credits atomically from company balance.
        Returns: (success: bool, new_balance: int, message: str)
        """
        if not company:
            return False, 0, "No company provided"

        # Sentinel: -1 means truly unlimited enterprise/master account (or self-hosted community mode)
        if company.credit_balance == -1 or os.getenv('AIKROFY_DEPLOYMENT_MODE') == 'community':
            return True, company.credit_balance if company.credit_balance is not None else -1, "Unlimited credits (Community/Enterprise mode)"

        # Check for courtesy credit expiration
        from datetime import datetime
        expires_at = getattr(company, 'courtesy_credits_expires_at', None)
        if expires_at and datetime.utcnow() > expires_at and getattr(company, 'subscription_tier', '') != 'enterprise':
            # Courtesy credits expired and no active paid upgrade
            current_balance = company.credit_balance if company.credit_balance is not None else 0
            if current_balance > 0:
                # Expire granted courtesy credits gracefully
                company.credit_balance = 0
                if db_session:
                    db_session.commit()
                return False, 0, "Courtesy credits expired. Please recharge credits or upgrade subscription."

        current_balance = company.credit_balance if company.credit_balance is not None else 0

        if current_balance < credits_to_deduct:
            return False, current_balance, f"Insufficient credits: balance {current_balance} < needed {credits_to_deduct}"

        company.credit_balance = current_balance - credits_to_deduct
        
        if db_session:
            try:
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                logger.error(f"[TOKEN_CREDIT] Failed to commit credit deduction: {e}")
                return False, current_balance, str(e)

        logger.info(f"[TOKEN_CREDIT] 💰 Deducted {credits_to_deduct} credits ({reason}). Company {company.id} balance: {current_balance} -> {company.credit_balance}")
        return True, company.credit_balance, "Credits deducted successfully"

    @staticmethod
    def has_lem_protection(company) -> bool:
        """
        Single source of truth: does this company have LEM deterministic protection?

        True for: purchased/assigned credits, unlimited (-1) accounts, beta / trial /
        demo accounts, and companies holding Layer-2 observability credits.
        Used by the observatory API, the LEM guardrail and the agents so the UI and
        the engine can never disagree.
        """
        if not company:
            return False
        core = company.credit_balance if company.credit_balance is not None else 0
        obs = getattr(company, 'observability_credit_balance', None)
        obs = 50 if obs is None else obs
        return bool(
            core > 0 or core == -1
            or obs > 0 or obs == -1
            or getattr(company, 'trial_activated', False)
            or getattr(company, 'is_demo', False)
        )

    @classmethod
    def effective_lem_balance(cls, company) -> int:
        """
        Balance to feed the LEM state vector. Protected accounts that are not backed
        by a positive core balance (beta, trial, layer-2 only) must not be penalised
        as 'depleted', so they are reported as unlimited (-1) to the engine.
        """
        if not company:
            return 0
        core = company.credit_balance if company.credit_balance is not None else 0
        if core > 0 or core == -1:
            return core
        return -1 if cls.has_lem_protection(company) else core

    @classmethod
    def deduct_observability_credits(
        cls,
        company,
        credits_to_deduct: int = 1,
        reason: str = "realtime_observability_trace",
        db_session = None
    ) -> Tuple[bool, int, str]:
        """
        Layer 2: Deducts dedicated observability & trace credits atomically.
        Keeps agent execution and analytics/monitoring isolated so beta users
        are never blocked from debugging or viewing neural traces.
        """
        if not company:
            return False, 0, "No company provided"

        # Unlimited enterprise account sentinel
        if getattr(company, 'observability_credit_balance', 50) == -1:
            return True, -1, "Unlimited observability credits"

        current_obs_balance = getattr(company, 'observability_credit_balance', 50)
        if current_obs_balance is None:
            current_obs_balance = 50

        if current_obs_balance < credits_to_deduct:
            return False, current_obs_balance, f"Insufficient observability credits: {current_obs_balance} < {credits_to_deduct}"

        company.observability_credit_balance = current_obs_balance - credits_to_deduct

        if db_session:
            try:
                db_session.commit()
            except Exception as e:
                db_session.rollback()
                logger.error(f"[OBSERVABILITY_CREDIT] Failed to commit deduction: {e}")
                return False, current_obs_balance, str(e)

        logger.info(f"[OBSERVABILITY_CREDIT] 📡 Deducted {credits_to_deduct} obs credits ({reason}). Company {company.id}: {current_obs_balance} -> {company.observability_credit_balance}")
        return True, company.observability_credit_balance, "Observability credits deducted successfully"
