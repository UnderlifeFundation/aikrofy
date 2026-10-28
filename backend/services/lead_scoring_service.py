"""
Lead Scoring Service - Hybrid calculation engine for lead prioritization.
"""
import json
import logging
from extensions import db
from models.customer import Customer
from models.company import Company
from models.conversation import Conversation, Message
from models.tenant_scoring_config import TenantScoringConfig
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

class LeadScoringService:
    DEFAULT_CONFIG = {
        "weight_ml": 0.50,
        "weight_manual": 0.50,
        "scoring_rules": {
            "decay_enabled": True,
            "decay_interval_days": 7,
            "decay_points": 5,
            "email_domains": {
                "gmail.com": -5,
                "outlook.com": -5,
                "yahoo.com": -10,
                "hotmail.com": -10
            },
            "industries": {
                "technology": 20,
                "software": 20,
                "healthcare": 15,
                "finance": 20,
                "retail": 15,
                "servicios": 15,
                "educación": 15,
                "comercio": 15
            },
            "buying_roles": {
                "ceo": 25,
                "cto": 25,
                "director": 20,
                "manager": 15,
                "founder": 25,
                "decision maker": 25,
                "gerente": 20,
                "administrador": 20,
                "solicitante demo": 15,
                "end user": 5
            },
            "countries": {
                "ec": 15,
                "ecuador": 15,
                "us": 15,
                "mx": 15,
                "co": 15,
                "es": 15,
                "pe": 10,
                "cl": 10
            }
        }
    }

    @staticmethod
    def get_or_create_config(company_id: int) -> TenantScoringConfig:
        """Fetch lead scoring config or initialize default values."""
        config = TenantScoringConfig.query.filter_by(company_id=company_id).first()
        if not config:
            logger.info(f"Creating default scoring config for company {company_id}")
            config = TenantScoringConfig(
                company_id=company_id,
                weight_ml=LeadScoringService.DEFAULT_CONFIG["weight_ml"],
                weight_manual=LeadScoringService.DEFAULT_CONFIG["weight_manual"],
                scoring_rules=LeadScoringService.DEFAULT_CONFIG["scoring_rules"]
            )
            db.session.add(config)
            db.session.commit()
        return config

    @staticmethod
    def calculate_manual_score(customer: Customer, config: TenantScoringConfig) -> int:
        """
        Evaluate manual attributes (email domain, industry, role, country, employee count) based on rules.
        S_Manual = max(0, min(100, Base + Sum(Beta_i) - Sum(Gamma_j)))
        """
        rules = config.scoring_rules or {}
        score = 35  # Base score for any registered lead

        meta = customer.customer_metadata or {}

        # 1. Email Domain Check
        if customer.email:
            email_lower = customer.email.strip().lower()
            if '@' in email_lower:
                domain = email_lower.split('@')[-1]
                email_rules = rules.get("email_domains", {})
                score += email_rules.get(domain, 0)
                # Corporate email bonus (if not in mapped consumer email list)
                if domain not in email_rules and not any(consumer in domain for consumer in ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud']):
                    score += 20  # Strong bonus for custom corporate domain

        # 2. Industry Check
        industry_val = (customer.company.industry if (customer.company and customer.company.industry) else meta.get('industry', ''))
        if industry_val:
            ind_rules = rules.get("industries", {})
            company_ind = industry_val.strip().lower()
            score += next((v for k, v in ind_rules.items() if k in company_ind), 10)

        # 3. Buying Role Check
        role_val = customer.buying_role or meta.get('role_in_company', '')
        if role_val:
            role_rules = rules.get("buying_roles", {})
            role_lower = role_val.strip().lower()
            score += next((v for k, v in role_rules.items() if k in role_lower), 10)

        # 4. Organization Size / Employee Count
        emp_val = str(meta.get('employee_count', ''))
        if '50+' in emp_val or '100' in emp_val or '200' in emp_val:
            score += 15
        elif '10' in emp_val or '20' in emp_val or '5' in emp_val:
            score += 10

        # 5. AI Experience / Expectations
        if meta.get('ai_expectations') or meta.get('products_services'):
            score += 10

        # 6. Country Check
        country_val = customer.country or meta.get('country', '')
        if country_val:
            country_rules = rules.get("countries", {})
            country_lower = country_val.strip().lower()
            score += country_rules.get(country_lower, 5)

        # Clamp between 0 and 100
        return max(0, min(100, score))

    @staticmethod
    def calculate_ai_score(customer: Customer, company: Company) -> float:
        """
        Analyze chat messages to compute conversion probability (P_ML) between 0.0 and 1.0.
        Uses OpenAI/Anthropic/Gemini based on company's configurations.
        """
        # Fetch last messages in the active conversation
        conversation = Conversation.query.filter_by(
            customer_id=customer.id,
            company_id=company.id
        ).order_by(Conversation.last_message_at.desc()).first()

        if not conversation:
            return 0.5

        messages_query = conversation.messages.order_by(Message.created_at.asc()).limit(15).all()
        if not messages_query:
            return 0.5

        # Format chat history
        history = []
        for msg in messages_query:
            history.append({
                "role": "user" if msg.role.value == "user" else "assistant",
                "content": msg.content
            })

        system_prompt = (
            "You are a sales qualification intelligence bot. Your job is to analyze the conversation history "
            "between a client and our AI assistant. Evaluate the client's intent to buy, interest level, "
            "urgency, and likelihood of conversion. "
            "You MUST respond ONLY with a raw JSON object containing these two fields:\n"
            "1. 'probability': a float number between 0.0 and 1.0 representing conversion likelihood.\n"
            "2. 'reason': a brief explanation of the score.\n"
            "Do not output markdown, preambles, or formatting tags. Example output:\n"
            "{\"probability\": 0.85, \"reason\": \"User has selected product and asked for payment links.\"}"
        )

        try:
            llm = LLMService(company)
            # Invoke LLM via standard company chat interface
            response = llm.chat(
                messages=history,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=150
            )
            
            content = response.get("content", "").strip()
            # Clean possible LLM markdown blocks
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            result = json.loads(content)
            probability = float(result.get("probability", 0.5))
            logger.info(f"AI Lead Scoring for customer {customer.id}: P_ML={probability} ({result.get('reason')})")
            return max(0.0, min(1.0, probability))
        except Exception as e:
            logger.error(f"Failed to calculate AI Lead Score: {e}")
            return 0.5  # Fallback to neutral 50% probability

    @staticmethod
    def calculate_composite_score(company_id: int, customer_id: int) -> int:
        """
        Calculates S_composite = (w_ML * P_ML * 100) + (w_Manual * S_Manual).
        Persists lead_score to Customer and Conversation records.
        """
        company = Company.query.get(company_id)
        customer = Customer.query.filter_by(id=customer_id, company_id=company_id).first()

        if not company or not customer:
            logger.error(f"Cannot calculate lead score: company_id={company_id} or customer_id={customer_id} not found")
            return 0

        config = LeadScoringService.get_or_create_config(company_id)

        # 1. Manual Score
        s_manual = LeadScoringService.calculate_manual_score(customer, config)

        # 2. AI Score (Try local ML model first, fallback to LLM zero-shot)
        p_ml = None
        try:
            from services.ml_scoring_pipeline import LocalPredictiveScoringEngine
            p_ml = LocalPredictiveScoringEngine.predict_conversion_probability(company_id, customer)
        except Exception as ml_err:
            logger.error(f"Local ML calculation failed: {ml_err}")

        if p_ml is None:
            p_ml = LeadScoringService.calculate_ai_score(customer, company)

        # 3. Composite Calculation
        w_ml = config.weight_ml
        w_manual = config.weight_manual

        s_composite = (w_ml * (p_ml * 100)) + (w_manual * s_manual)
        final_score = int(round(s_composite))
        final_score = max(0, min(100, final_score))

        # 4. Save to Customer
        customer.lead_score = final_score
        
        # 5. Save to active Conversation (if exists)
        conversation = Conversation.query.filter_by(
            customer_id=customer_id,
            company_id=company_id,
            is_active=True
        ).first()
        if conversation:
            conversation.lead_score = final_score

        db.session.commit()
        logger.info(f"Composite Lead Score for customer {customer.id} calculated: {final_score}/100")
        
        # 5. Auto-progress funnel stage based on milestones & score!
        try:
            LeadScoringService.auto_progress_funnel_stage(company_id, customer_id)
        except Exception as stage_err:
            logger.error(f"Error in auto-progression of stage: {stage_err}")
            
        # 6. Publish update to Redis/WebSocket pipeline if relevant
        try:
            from services.realtime_service import RealtimeService
            # Refresh customer from db session to load newly set stage
            db.session.refresh(customer)
            RealtimeService.publish_lead_update(company_id, customer_id, {
                "lead_score": final_score,
                "funnel_stage_id": customer.funnel_stage_id
            })
        except Exception as ws_err:
            logger.warning(f"Could not publish lead score update: {ws_err}")

        return final_score

    @staticmethod
    def auto_progress_funnel_stage(company_id: int, customer_id: int):
        """
        Evaluate customer interactions, score, and data to auto-progress their funnel stage.
        """
        from models.customer import Customer
        from models.funnel_stage import FunnelStage
        from models.appointment import Appointment
        from models.transaction import Transaction, TransactionStatus

        customer = Customer.query.filter_by(id=customer_id, company_id=company_id).first()
        if not customer:
            return

        stages = FunnelStage.query.filter_by(company_id=company_id).order_by(FunnelStage.sort_order.asc()).all()
        if not stages:
            return

        # Map stages by normalized name or order
        stage_by_name = {}
        for s in stages:
            name_norm = s.name.lower().strip()
            # Normalize accents/special characters
            name_norm = name_norm.replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ú', 'u')
            stage_by_name[name_norm] = s

        stage_by_order = {s.sort_order: s for s in stages}

        # Determine target stage based on customer milestones
        target_stage = None

        # 1. Hito: Ganado (Tiene transacciones completadas)
        has_completed_payment = Transaction.query.filter_by(
            customer_id=customer_id,
            company_id=company_id,
            status=TransactionStatus.COMPLETED.value
        ).first() is not None

        if has_completed_payment:
            target_stage = stage_by_name.get('ganado') or stage_by_order.get(5)
            
        if not target_stage:
            # 2. Hito: Propuesta/Negociación (Tiene citas/agendas creadas)
            has_appointment = Appointment.query.filter_by(
                customer_id=customer_id,
                company_id=company_id
            ).first() is not None
            
            if has_appointment:
                target_stage = stage_by_name.get('propuesta') or stage_by_name.get('negociacion') or stage_by_order.get(3) or stage_by_order.get(4)

        if not target_stage:
            # 3. Hito: Calificado (Score >= 50)
            if customer.lead_score >= 50:
                target_stage = stage_by_name.get('calificado') or stage_by_order.get(2)

        if not target_stage:
            # 4. Hito: Contactado (Tiene nombre real, correo o teléfono, y no es visitante efímero)
            is_registered = customer.first_name and customer.first_name != "Visitante Webchat" and (customer.email or (customer.phone and not customer.phone.startswith('guest')))
            if is_registered:
                target_stage = stage_by_name.get('contactado') or stage_by_order.get(1)

        if not target_stage:
            # 5. Default: Lead / Nuevo
            target_stage = stage_by_name.get('lead') or stage_by_name.get('nuevo') or stage_by_order.get(0)

        # Apply change if it's a forward movement (or keep manual overrides)
        if target_stage and customer.funnel_stage_id != target_stage.id:
            current_stage = FunnelStage.query.get(customer.funnel_stage_id) if customer.funnel_stage_id else None
            current_order = current_stage.sort_order if current_stage else -1
            
            # Auto progression moves forward only to respect manual overrides/demotions
            if target_stage.sort_order > current_order:
                logger.info(f"Auto-progressing customer {customer_id} from stage {current_order} to {target_stage.sort_order} ({target_stage.name})")
                customer.funnel_stage_id = target_stage.id
                db.session.commit()
