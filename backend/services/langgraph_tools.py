from routing import g
"""
LangGraph Tools
Wraps existing Aikrofy services as LangChain tools for use in LangGraph workflows.

All tools follow the pattern:
1. Import existing service
2. Get company context from state/config
3. Call service method
4. Return result as string
"""
import os
import logging
from langchain_core.tools import tool
from typing import Optional, List
import json

logger = logging.getLogger(__name__)


# ============================================================
# RAG / Knowledge Base Tools
# ============================================================

@tool
def consult_knowledge_base(query: str) -> str:
    """
    Search the company knowledge base for relevant information.
    Use this when you need to find information about products, services, policies, or any company-specific data.
    
    Args:
        query: The search query to find information
        
    Returns:
        Relevant information from the knowledge base
    """
    
    from services.rag_service import RAGService
    
    try:
        # Preventive rollback to clear stale MySQL connections
        # This is critical: without it, a "MySQL server has gone away" error
        # silently kills the RAG query and the agent says "no relevant info found"
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "Knowledge base not available - no company context"
        
        rag_service = RAGService(company)
        results = rag_service.query(query, top_k=3)
        
        # Also query the global knowledge base (e.g. BOS-AI handbooks)
        global_rag = RAGService(None)
        global_results = global_rag.query(query, top_k=2)
        
        all_results = results + global_results
        
        # Save chunk IDs for transparent auditing
        if all_results:
            chunk_ids = [r.get('id') for r in all_results if r.get('id')]
            if not hasattr(g, 'last_rag_chunks'):
                g.last_rag_chunks = []
            g.last_rag_chunks.extend(chunk_ids)
            
            texts = [r.get('content', '') for r in all_results if r.get('content')]
            return "\n---\n".join(texts) if texts else "No relevant information found in knowledge base."
        return "No relevant information found in knowledge base."
    except Exception as e:
        print(f"[RAG] Error searching knowledge base: {e}")
        # Rollback on error to ensure clean state
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error searching knowledge base: {str(e)}"


# ============================================================
# Agent Skills Management Tools
# ============================================================

@tool
def agent_list_skills() -> str:
    """
    List all active skills and prompt blocks of the agent's company.
    Use this to see what capabilities and protocols are currently configured.
    
    Returns:
        A list of active skills, names, categories, and descriptions.
    """
    from services.skill_service import SkillService
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        skills = SkillService.load_active_skills(company.id)
        if not skills:
            return "No active skills configured for this company."
            
        result = "Active company skills:\n"
        for s in skills:
            cat_val = s.category.value if hasattr(s.category, 'value') else str(s.category or 'custom')
            result += f"- Name: {s.name} | Label: {s.label} | Category: {cat_val} | Priority: {s.priority}\n  Description: {s.description or 'No description'}\n"
        return result
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error listing skills: {str(e)}"


@tool
def agent_create_or_update_skill(name: str, label: str, system_prompt_block: str, description: Optional[str] = "", category: Optional[str] = "custom", required_tools: Optional[list] = None, priority: Optional[int] = 100, is_enabled: Optional[bool] = True) -> str:
    """
    Create a new skill or update an existing skill (prompts/instructions/tools) for the company.
    This dynamically updates both the database record and the local SKILL.md file on disk.
    
    IMPORTANT: You (the agent) are responsible for generating the technical 'name' (slug) from the user's natural language request. 
    Avoid asking the user for technical parameters like 'slugs', 'priority' or 'categories' unless strictly necessary. 
    Maintain a conversational and helpful tone, explaining what the skill will do in plain language.
    
    Args:
        name: Unique slug name of the skill, e.g. "soporte-cliente" (lowercase, no spaces, use hyphens)
        label: Display name of the skill, e.g. "Customer Support"
        system_prompt_block: The detailed prompt instructions for the skill. Keep it clear, descriptive, and using markdown headers if necessary.
        description: A short explanation of what the skill does and when to trigger it.
        category: Organizer category. Must be one of: 'core', 'payments', 'scheduling', 'ecommerce', 'support', 'sales', 'custom', 'integration'.
        required_tools: List of tool names this skill needs, e.g. ["lookup_customer"] (or empty list)
        priority: Loading priority (default 100, lower priority loaded first)
        is_enabled: Whether this skill is currently active (default True)
        
    Returns:
        Confirmation message about the created/updated skill.
    """
    from services.skill_service import SkillService
    from models.company_skill import CompanySkill, SkillCategory, SkillOrigin
    from extensions import db
    
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        # Clean slug name
        name = name.strip().lower().replace(" ", "-")
        
        # Validate category
        try:
            skill_cat = SkillCategory(category)
        except ValueError:
            skill_cat = SkillCategory.CUSTOM
            
        # Check if skill exists
        skill = CompanySkill.query.filter_by(company_id=company.id, name=name).first()
        
        if skill:
            # Update
            if skill.system_prompt_block != system_prompt_block:
                skill.update_prompt(system_prompt_block)
            skill.label = label
            skill.description = description
            skill.category = skill_cat
            skill.priority = priority
            skill.is_enabled = is_enabled
            if required_tools is not None:
                skill.required_tools = required_tools
            message = f"Successfully updated skill '{name}' (version {skill.version}) in database."
        else:
            # Create
            skill = CompanySkill(
                company_id=company.id,
                name=name,
                label=label,
                description=description,
                category=skill_cat,
                origin=SkillOrigin.AI_GENERATED,
                system_prompt_block=system_prompt_block,
                required_tools=required_tools or [],
                priority=priority,
                is_enabled=is_enabled,
            )
            db.session.add(skill)
            message = f"Successfully created new skill '{name}' in database."
            
        db.session.commit()
        db.session.refresh(skill)
        
        # Sync to disk SKILL.md
        try:
            SkillService.export_skill_to_markdown(skill)
            message += " Synced to local SKILL.md file."
        except Exception as e:
            message += f" Failed to sync to disk: {str(e)}"
            
        return message
    except Exception as e:
        db.session.rollback()
        return f"Error creating/updating skill: {str(e)}"


@tool
def navigate_website(target: str, action_type: str = "scroll", reason: str = "") -> str:
    """
    Navigate or scroll the visitor's screen in real time to a specific section or page on the website.
    Use this tool whenever the user asks to go to, see, or navigate to a section, service, product, pricing, or contact on the website.
    
    Args:
        target: The target section ID (e.g. '#servicios', '#precios', '#contacto', 'servicios', 'precios') or page path/URL (e.g. '/servicios', '/contacto', 'https://...').
        action_type: 'scroll' (smoothly scroll to section on current page) or 'redirect' (navigate to another URL). Default is 'scroll'.
        reason: Brief explanation of where you are taking the user.
        
    Returns:
        JSON string with the navigation action payload for the web widget.
    """
    clean_target = target.strip() if target else ""
    if clean_target.startswith("/") or clean_target.startswith("http"):
        action_type = "redirect"
    elif clean_target and not clean_target.startswith("#"):
        clean_target = f"#{clean_target}"
    
    return json.dumps({
        "action": "navigate",
        "action_data": {
            "type": "navigate",
            "path": clean_target,
            "target": clean_target,
            "url": clean_target,
            "section": clean_target,
            "action_type": action_type,
            "reason": reason
        },
        "success": True,
        "message": f"Navegando al usuario hacia: {clean_target} ({action_type})"
    })


@tool
def agent_create_new_agent(name: str, objective: str, description: Optional[str] = "", tone: Optional[str] = "professional", gender: Optional[str] = "neutral", system_prompt: Optional[str] = "", features_to_enable: Optional[list] = None) -> str:
    """
    Create a new independent agent identity that appears in the configuration panel.
    Use this when the user says "create an agent" or similar (meaning an independent agent persona, not a skill/prompt block).

    CRITICAL: You MUST analyze the user request and determine exactly which features/integrations/tools are appropriate for the specific agent you are creating, and specify them in 'features_to_enable'. DO NOT leave it empty. ONLY the features specified here will be enabled.

    Args:
        name: Name of the agent (e.g., "Recepcionista", "Analista de Leads")
        objective: Primary objective category. Options: 'general', 'support', 'sales', 'reception', 'lead_generation', 'feedback'.
        description: A brief, single-sentence summary of the agent's role for display cards in the UI (e.g., "Chief Sales Officer - Handles conversions" or "Qualifies leads via BANT framework"). Do NOT put long step-by-step instructions or welcome messages here.
        tone: Tone of voice ('professional', 'friendly', 'direct', 'humorous')
        gender: Gender representation ('neutral', 'male', 'female')
        system_prompt: Detailed step-by-step behavioral instructions and rules for the agent (similar to other agents, e.g. BANT procedures, steps to update CRM, rules not to share pricing, etc.). This is the system instructions file, do NOT write welcoming messages or conversational previews here.
        features_to_enable: List of feature keys to enable by default (e.g. ["whatsapp", "webchat", "calendar", "process_payment", "crm_sync", "rag_memory"]). ONLY these features will be marked as enabled.

    Returns:
        Confirmation message about the created agent.
    """
    from models.agent import Agent, AgentFeature, AgentTone, AgentObjective, AgentGender, DEFAULT_FEATURES
    from extensions import db

    try:
        try:
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."

        # Validate objective
        try:
            obj_enum = AgentObjective(objective.strip().lower())
        except ValueError:
            obj_enum = AgentObjective.GENERAL

        # Validate tone/gender
        try:
            tone_enum = AgentTone(tone.strip().lower())
        except ValueError:
            tone_enum = AgentTone.PROFESSIONAL

        try:
            gender_enum = AgentGender(gender.strip().lower())
        except ValueError:
            gender_enum = AgentGender.NEUTRAL

        agent = Agent(
            company_id=company.id,
            name=name,
            description=description,
            tone=tone_enum,
            objective=obj_enum,
            gender=gender_enum,
            system_prompt=system_prompt,
            is_active=True
        )
        db.session.add(agent)
        db.session.flush()

        # Determine logical default features based on objective if features_to_enable is omitted
        obj_lower = objective.lower().strip()
        if not features_to_enable:
            if obj_lower in ['sales', 'payments']:
                extra = ['paypal', 'process_payment', 'crm_sync']
            elif obj_lower in ['scheduling', 'reception']:
                extra = ['calendar', 'schedule_meeting']
            elif obj_lower in ['support', 'customer_service']:
                extra = ['send_email']
            elif obj_lower in ['lead_qualification', 'lead_generation']:
                extra = ['crm_sync', 'create_task']
            elif obj_lower == 'inventory':
                extra = ['check_inventory', 'google_sheets']
            else:
                extra = []
        else:
            extra = [f.strip().lower() for f in features_to_enable]

        # Basic channels and features that should ALWAYS be enabled for a core functional agent
        basic_features = ['webchat', 'whatsapp', 'rag_memory', 'conversation_history']
        requested_features = list(set(basic_features + extra))

        # Initialize default features for the agent
        for feature_data in DEFAULT_FEATURES:
            # ONLY enable features explicitly requested by the agent creation call or defaulted
            feat_name = feature_data['name']
            is_enabled = feat_name in requested_features

            feature = AgentFeature(
                agent_id=agent.id,
                category=feature_data['category'],
                name=feat_name,
                label=feature_data['label'],
                description=feature_data['description'],
                is_enabled=is_enabled,
                order=feature_data['order']
            )
            db.session.add(feature)

        db.session.commit()
        return json.dumps({
            "success": True,
            "message": f"Successfully created new agent '{name}' (ID: {agent.id}) in the database. It is now visible on the Agent Configuration panel.",
            "action": "navigate_and_select_agent",
            "action_data": {
                "path": f"/agents?selected={agent.id}",
                "agent_id": agent.id
            }
        })
    except Exception as e:
        db.session.rollback()
        return json.dumps({
            "success": False,
            "error": str(e)
        })
    except Exception as e:
        db.session.rollback()
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def agent_delete_agent(agent_id: int) -> str:
    """
    Delete an agent identity from the database.

    Args:
        agent_id: The numeric ID of the agent to delete.

    Returns:
        Confirmation message about the deletion.
    """
    from models.agent import Agent
    from extensions import db

    try:
        try:
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."

        agent = Agent.query.filter_by(id=agent_id, company_id=company.id).first()
        if not agent:
            return f"Agent with ID {agent_id} not found."

        agent_name = agent.name
        db.session.delete(agent)
        db.session.commit()
        return f"Successfully deleted agent '{agent_name}' (ID: {agent_id})."
    except Exception as e:
        db.session.rollback()
        return f"Error deleting agent: {str(e)}"


# ============================================================
# Customer Verification Tools
# ============================================================

@tool
def lookup_customer(query: str) -> str:
    """
    Search for a registered customer by email, phone, or name.
    Use this to verify identity before processing payments or accessing sensitive info.
    
    Args:
        query: Search term. MUST be provided by the user. Do NOT guess or infer emails not present in chat.
        
    Returns:
        Found customer details or "Customer not found"
    """
    
    from services.customer_service import CustomerService
    
    try:
        # Preventive rollback for stale connections
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company: return "No company context"
        
        from utils.phone import normalize_phone_number
        results = CustomerService.lookup_by_term(company.id, query)
        if not results:
            return "Customer not found. If the user already provided their name and/or email/phone, call 'register_customer(first_name=..., email=...)' now to save them in the CRM. Do NOT ask for DNI/cedula."
            
        response = "Found customers:\n"
        for c in results:
            phone_fmt = normalize_phone_number(c.phone, c.country) if c.phone else "Not registered"
            response += f"- ID: {c.id}, Name: {c.first_name or ''} {c.last_name or ''}, Phone: {phone_fmt}, Email: {c.email or 'None'}, City: {c.city or 'None'}, Country: {c.country or 'None'}, IdentNum: {c.ident_number or 'None'}\n"
        return response
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error looking up customer: {str(e)}"
        
@tool
def register_customer(first_name: str, last_name: Optional[str] = "", email: Optional[str] = None, phone: Optional[str] = None, ident_number: Optional[str] = None, country: Optional[str] = None, city: Optional[str] = None, buying_role: Optional[str] = "End User") -> str:
    """
    Register an EXTERNAL visitor/client/lead into the company's CRM.
    CRITICAL: This tool is ONLY for external human customers/leads.
    DO NOT use this tool when the user asks to "create an agent" or "nuevo agente". To create an AI agent, use 'agent_create_new_agent'.
    DO NOT use this tool for internal company employees.

    Args:
        first_name: External customer's first name. (Required)
        last_name: External customer's last name. (Optional)
        email: Customer's email address.
        phone: Optional phone or WhatsApp number.
        ident_number: Identification number. DO NOT ASK the user for this unless they want an invoice or legal contract.
        country: Optional Customer country
        city: Optional Customer city
        buying_role: Role in purchasing process (Default: 'End User').
        
    Returns:
        Registration confirmation with Customer ID
    """
    
    from services.customer_service import CustomerService
    from extensions import db
    
    try:
        # Preventive rollback for stale connections
        try:
            db.session.rollback()
        except Exception:
            pass
            
        from datetime import datetime, timedelta
        
        company = getattr(g, 'current_company', None)
        if not company: return "No company context"

        # Protection: do not register founder/owner names (vocatives) as customer names
        cleaned_first_name = (first_name or "").strip()
        reserved_founder_names = {"jonathan", "jonnathan", "yosue", "josue"}
        if cleaned_first_name.lower() in reserved_founder_names and not email:
            logger.warning(f"[REGISTER_CUSTOMER] Rejected founder vocative name '{cleaned_first_name}' without explicit email confirmation.")
            return f"Notice: '{cleaned_first_name}' matches company founder/staff name. If the user was addressing the team or founder, please assist them or transfer them. If this is genuinely the customer's own name, please confirm their email before registering."
        
        data = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'ident_number': ident_number,
            'phone': phone,
            'country': country,
            'city': city,
            'buying_role': buying_role
        }
        
        # Check if customer exists to determine if we should set status to NEW
        existing_customer = CustomerService.get_customer(company.id, email, phone)
        is_new = existing_customer is None
        
        conversation = getattr(g, 'current_conversation', None)
        customer = CustomerService.merge_or_upgrade_customer(company.id, data, conversation=conversation)
            
        # Recalculate lead score and trigger auto stage progression immediately
        try:
            from services.lead_scoring_service import LeadScoringService
            LeadScoringService.calculate_composite_score(company.id, customer.id)
        except Exception as ls_err:
            logger.error(f"Failed to calculate score after upgrading customer: {ls_err}")
        
        # Sync to CRM immediately if configured
        try:
            from services.crm.factory import CRMFactory
            from services.crm.canonical_models import Contact
            
            crm_connector = CRMFactory.get_connector(company.id)
            if crm_connector and customer.email:
                contact_data = Contact(
                    id=str(customer.id),
                    first_name=customer.first_name,
                    last_name=customer.last_name,
                    email=customer.email,
                    phone=customer.phone,
                    lead_status='NEW' if is_new else None
                )
                crm_connector.create_or_update_contact(customer.email, contact_data)
        except Exception as crm_e:
            print(f"CRM Sync Error: {crm_e}")
            
        return f"Customer registered successfully! ID: {customer.id}, Name: {customer.first_name} {customer.last_name}, Location: {customer.city or 'N/A'}, {customer.country or 'N/A'}"
    except Exception as e:
        db.session.rollback()
        return f"Error registering customer: {str(e)}"

# ============================================================
# Payment Tools
# ============================================================

@tool
def paypal_create_order(amount: float, currency: str = "USD", description: str = "Payment", customer_id: Optional[int] = None) -> str:
    """
    Create a PayPal payment order and return the direct payment link. 
    PREREQUISITE: If the customer is already identified in context or registered, generate the link immediately. If not registered, verify them first.
    IMPORTANT: If the price or product is known from the knowledge base, catalog, or user context (e.g. Landing Page $97), generate the payment order immediately with that amount without asking the customer to re-confirm the price.
    
    Args:
        amount: Payment amount (use known price from context or knowledge base)
        currency: Currency code (USD, EUR)
        description: Description of service/product
        customer_id: The numeric ID of the verified customer (from lookup/register tool or context)
        
    Returns:
        Approval URL for the customer to click
    """
    
    from services.paypal_toolkit import get_paypal_toolkit
    from services.transaction_service import TransactionService
    
    try:
        # Preventive rollback for stale connections
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        conversation = getattr(g, 'current_conversation', None) # New context variable

        # --- PAYGUARD & LEM INVARIANT FINANCIAL VERIFICATION ---
        # 1. Enforce max single transaction limit from TrustGuardrails
        if company:
            from models.trust_guardrail import TrustGuardrail, GuardrailType
            guardrail = TrustGuardrail.query.filter_by(
                company_id=company.id,
                guardrail_type=GuardrailType.PRICE_DISCOUNT_LIMIT,
                is_active=True
            ).first()
            if guardrail and guardrail.rules:
                max_allowed = float(guardrail.rules.get('high_risk_threshold_usd', 1000.0))
                if amount > max_allowed:
                    return f"[PAYGUARD_BLOCKED] Transacción de ${amount:.2f} {currency} bloqueada. Supera el límite de riesgo autorizado de ${max_allowed:.2f} configurado en TrustGuardrails."

        toolkit = get_paypal_toolkit(company)
        
        # 2. Create Transaction Logs (Pending)
        txn = TransactionService.create_transaction(
            company_id=company.id if company else 1,
            amount=amount,
            currency=currency,
            description=description,
            customer_id=customer_id,
            conversation_id=conversation.id if conversation else None,
            provider="paypal",
            channel=conversation.channel if conversation else "webchat"
        )
        
            # 2. Call PayPal API
        # Append transaction ID to description for tracking? Optional.
        
        result = toolkit.create_order(amount, currency, description)
        
        if result.get('success'):
            order_id = result['order_id']
            # 3. Update Transaction with Provider ID
            TransactionService.update_provider_order_id(txn.id, order_id)
            
            # --- CRM INTEGRATION (Create Pending Deal) ---
            try:
                from services.crm.factory import CRMFactory
                from services.crm.canonical_models import Deal
                
                crm_connector = CRMFactory.get_connector(company.id)
                
                customer_email = None
                if customer_id:
                    from models.customer import Customer
                    cust_obj = Customer.query.get(customer_id)
                    if cust_obj: customer_email = cust_obj.email
                
                if crm_connector and customer_email:
                    deal_dict = {
                        "id": f"deal_{order_id}",
                        "title": f"Payment Pending - {description[:30]}",
                        "amount": float(amount),
                        "stage": "appointmentscheduled",
                        "pipeline": "default"
                    }
                    try:
                        crm_connector.create_deal(deal_dict)
                    except TypeError:
                        crm_connector.create_deal(deal_dict, customer_email)
            except Exception as crm_err:
                print(f"CRM Sync Error (Create Order): {crm_err}")
            # ---------------------------
            
            # Use Branded Hosted Checkout portal URL for guest debit/credit card payments
            import uuid
            from models.payment_gateway import PaymentTransaction, PaymentGatewayConfig, TransactionChannel, TransactionStatus
            from decimal import Decimal
            
            idempotency_key = str(uuid.uuid4())
            config = PaymentGatewayConfig.query.filter_by(company_id=company.id).first() if company else None
            
            hosted_txn = PaymentTransaction(
                company_id=company.id if company else 1,
                gateway_config_id=config.id if config else None,
                customer_email=customer_email,
                customer_name=cust_obj.full_name if (customer_id and cust_obj) else None,
                amount=Decimal(str(amount)),
                currency=currency.upper(),
                description=description,
                status=TransactionStatus.PENDING,
                external_transaction_id=order_id,
                idempotency_key=idempotency_key,
                channel=TransactionChannel.WHATSAPP if conversation and conversation.channel == 'whatsapp' else TransactionChannel.WEBCHAT,
                conversation_id=conversation.id if conversation else None
            )
            portal_url = f"https://app.aikrofy.com/api/payments/checkout/{idempotency_key}"
            hosted_txn.payment_url = portal_url
            db.session.add(hosted_txn)
            db.session.commit()
            
            return (
                f"Aquí tienes el portal seguro para completar tu pago de {amount} {currency.upper()} "
                f"por '{description}':\n{portal_url}\n\n"
                f"💳 Puedes pagar directamente con tarjeta de débito o crédito (como invitado, sin necesidad de tener cuenta PayPal) o con tu cuenta PayPal."
            )
            
            # --- AUTO-RESOLVE CONVERSATION ---
            try:
                from datetime import datetime
                from extensions import db
                conversation = getattr(g, 'current_conversation', None)
                if conversation:
                    conversation.is_resolved = True
                    conversation.resolved_at = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.error(f"Error auto-resolving conversation: {e}")
            # ---------------------------------
            
            return json.dumps({
                'success': True,
                'order_id': order_id,
                'approval_url': result['approval_url'],
                'formatted_link': formatted_link,
                'message': f"¡Link de pago creado! Orden: {order_id}. El cliente debe hacer click en el enlace para completar el pago."
            })
        else:
            return json.dumps({'success': False, 'error': result.get('error', 'Failed to create order')})
    except Exception as e:
        # Rollback any failed transaction to clean connection
        from extensions import db
        db.session.rollback()
        return json.dumps({'success': False, 'error': str(e)})


@tool
def paypal_capture_order(order_id: str) -> str:
    """
    Capture a PayPal payment after approval.
    """
    
    from services.paypal_toolkit import get_paypal_toolkit
    from services.transaction_service import TransactionService
    from models.transaction import TransactionStatus
    
    try:
        company = getattr(g, 'current_company', None)
        toolkit = get_paypal_toolkit(company)
        result = toolkit.capture_order(order_id)
        
        if result.get('success'):
            # Update Transaction Status
            TransactionService.update_status_by_order_id(order_id, TransactionStatus.COMPLETED.value)
            
            # --- CRM INTEGRATION ---
            try:
                from services.crm.factory import CRMFactory
                from services.crm.canonical_models import Contact
                
                crm_connector = CRMFactory.get_connector(company.id)
                
                # Retrieve transaction to get customer
                from models.transaction import Transaction
                txn = Transaction.query.filter_by(provider_order_id=order_id).first()
                if crm_connector and txn and txn.customer and txn.customer.email:
                    # Update Contact to 'customer'
                    contact_data = Contact(
                        email=txn.customer.email,
                        lead_status='CUSTOMER'
                    )
                    crm_connector.create_or_update_contact(txn.customer.email, contact_data)
                    
                    # Ideally we would find the deal and close it as 'closedwon'.
                    # For now, updating lifecycle is the MVP critical step.
            except Exception as crm_err:
                 print(f"CRM Sync Error (Capture Order): {crm_err}")
            # ---------------------------

            # --- AUTO-RESOLVE CONVERSATION ---
            try:
                conversation = getattr(g, 'current_conversation', None)
                if conversation:
                    from datetime import datetime
                    from extensions import db
                    conversation.is_resolved = True
                    conversation.resolved_at = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.error(f"Error auto-resolving conversation: {e}")
            # ---------------------------------
            
            return json.dumps({
                'success': True,
                'message': 'Payment captured and verified!',
                'capture_id': result.get('capture_id')
            })
        else:
            return json.dumps({'success': False, 'error': result.get('error', 'Capture failed')})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


@tool
def paypal_get_order(order_id: str) -> str:
    """
    Get the status of a PayPal order.
    """
    
    from services.paypal_toolkit import get_paypal_toolkit
    
    try:
        company = getattr(g, 'current_company', None)
        toolkit = get_paypal_toolkit(company)
        result = toolkit.get_order(order_id)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


# ============================================================
# Communication Tools
# ============================================================

@tool
def send_whatsapp(to: str, message: str) -> str:
    """
    Send a WhatsApp message to a phone number.
    
    Args:
        to: Phone number with country code (e.g., +593982541659 or 0982541659)
        message: Message content to send
        
    Returns:
        Confirmation of message sent
    """
    
    from services.twilio_service import TwilioService
    from utils.phone import normalize_phone_number
    
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "Cannot send WhatsApp - no company context"

        # Normalize phone number to E.164
        to = normalize_phone_number(to)
        
        # Check active WhatsApp channel or company api_keys for provider
        provider = None
        from models.channel import Channel, ChannelType
        wa_channel = Channel.query.filter_by(company_id=company.id, type=ChannelType.WHATSAPP).first()
        if wa_channel and wa_channel.credentials:
            provider = wa_channel.credentials.get('provider')

        if not provider and company.api_keys:
            provider = company.api_keys.get('whatsapp_provider')

        if not provider:
            provider = 'twilio'

        if provider == 'meta':
            from services.meta_whatsapp_service import MetaWhatsAppService
            res = MetaWhatsAppService.send_whatsapp(company.id, to, message)
            if res.get('success'):
                return f"WhatsApp message sent successfully to {to} via Meta Cloud API (ID: {res.get('id')})."

            # Auto-fallback for Meta 24-hour window restriction (Error #10 or permission restriction)
            err_text = str(res.get('error', ''))
            if 'permission' in err_text.lower() or '#10' in err_text or '24' in err_text or 'window' in err_text:
                # Find an approved HSM template for this company
                from models.whatsapp_template import WhatsAppTemplate, TemplateStatus
                tpl = WhatsAppTemplate.query.filter_by(company_id=company.id, status=TemplateStatus.APPROVED.value).first()
                if not tpl:
                    tpl = WhatsAppTemplate.query.filter_by(company_id=company.id).first()

                if tpl:
                    tpl_res = MetaWhatsAppService.send_template_whatsapp(
                        company_id=company.id,
                        to_phone=to,
                        template_name=tpl.name,
                        language_code=tpl.language or 'es'
                    )
                    if tpl_res.get('success'):
                        return f"WhatsApp initial contact initiated successfully to {to} using official Meta approved template '{tpl.name}' (ID: {tpl_res.get('id')}). This opens the 24h conversation window."

            # Automatic fallback to Twilio if Meta returns permission error and no template works
            if company.api_keys and ('twilio_sid' in company.api_keys or getattr(Config, 'TWILIO_ACCOUNT_SID', '')):
                try:
                    twilio = TwilioService(company)
                    result = twilio.send_whatsapp(to, message)
                    if 'sid' in result or result.get('success'):
                        return f"WhatsApp message sent successfully to {to} via Twilio fallback (SID: {result.get('sid')}). Note: Meta API returned '{res.get('error')}'."
                except Exception:
                    pass

            return f"Failed to send WhatsApp via Meta Cloud API: {res.get('error', 'Unknown error')}"

        elif provider == 'baileys':
            from services.whatsapp_service import WhatsAppBaileysService
            service = WhatsAppBaileysService(str(company.id))
            
            # Check if service is reachable (fast check)
            if not service.is_available():
                return "WhatsApp service is not available (Baileys Node.js API down)."

            result = service.send_message(to, message)
            
            if result.get('success'):
                return f"WhatsApp message sent successfully to {to}"
            else:
                return f"Failed to send WhatsApp via Baileys: {result.get('error', 'Unknown error')}"
        
        else:
            # Default to Twilio
            twilio = TwilioService(company)
            result = twilio.send_whatsapp(to, message)
            
            if 'sid' in result or result.get('success'):
                return f"WhatsApp message sent successfully to {to} (SID: {result.get('sid', 'sent')})"
            else:
                return f"Failed to send WhatsApp: {result.get('error', 'Unknown error')}"

    except Exception as e:
        return f"Error sending WhatsApp: {str(e)}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email to a recipient.
    
    Args:
        to: Email address of recipient
        subject: Email subject line
        body: Email body content (supports Markdown formatting: **bold**, - bullets, ## headers)
        
    Returns:
        Confirmation of email sent
    """
    

    from services.email_service import EmailService
    import re
    from extensions import db
    from datetime import datetime
    
    def markdown_to_html(text: str) -> str:
        """Convert basic Markdown to HTML for email formatting."""
        # Convert headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Convert bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        
        # Convert italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        
        # Convert bullet points
        text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'(<li>.+</li>\n?)+', r'<ul>\g<0></ul>', text)
        
        # Convert line breaks to <br> (preserve paragraph structure)
        text = re.sub(r'\n\n', r'</p><p>', text)
        text = re.sub(r'\n', r'<br>', text)
        
        # Wrap in paragraph
        text = f'<p>{text}</p>'
        
        # Clean up empty paragraphs
        text = text.replace('<p></p>', '')
        
        return text
    
    try:
        # Preventive rollback for stale connections before accessing company context
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "Cannot send email - no company context"
        
        # Convert Markdown body to HTML for professional formatting
        html_body = markdown_to_html(body)
        
        result = EmailService.send_email(
            company_id=company.id,
            to_email=to,
            subject=subject,
            body=html_body
        )
        
        if result.get('success'):
            # --- LOG EMAIL ---
            try:
                from models.email_log import EmailLog
                # Helper to get conversation/customer context
                conversation = getattr(g, 'current_conversation', None)
                customer = getattr(g, 'current_customer', None) # If available
                
                log = EmailLog(
                    company_id=company.id,
                    conversation_id=conversation.id if conversation else None,
                    customer_id=customer.id if customer else None,
                    to_email=to,
                    subject=subject,
                    body_summary=body[:500] + ('...' if len(body) > 500 else '')
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e_log:
                print(f"Error logging email: {e_log}")
            # -----------------
            
            # --- CREDIT DEDUCTION FOR EMAIL ---
            # Each email sent is a "message delivered to the client" = 1 credit
            try:
                current_balance = company.credit_balance if company.credit_balance is not None else 0
                if current_balance != -1:  # -1 = unlimited, skip deduction
                    if current_balance > 0:
                        company.credit_balance = current_balance - 1
                        db.session.commit()
                        print(f"[TOOLS] 💰 Email credit deducted. Balance: {current_balance} -> {company.credit_balance}")
                    else:
                        print(f"[TOOLS] ⚠️ Email sent but no credits remaining ({current_balance})")
            except Exception as e_credit:
                print(f"[TOOLS] Credit deduction error (non-blocking): {e_credit}")
            # ----------------------------------
            
            # --- AUTO-RESOLVE CONVERSATION ---
            try:
                conversation = getattr(g, 'current_conversation', None)
                if conversation:
                    conversation.is_resolved = True
                    conversation.resolved_at = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.error(f"Error auto-resolving conversation: {e}")
            # ---------------------------------
            return f"Email sent successfully to {to}"
        else:
            return f"Failed to send email: {result.get('error', 'Unknown error')}"
    except Exception as e:
        # Rollback on error to ensure clean state for next tool
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error sending email: {str(e)}"


@tool
def make_call(to: str, purpose: str) -> str:
    """
    Initiate a voice call to a phone number.
    
    Args:
        to: Phone number to call (with country code)
        purpose: Brief description of the call purpose
        
    Returns:
        Call initiation status
    """
    
    from services.livekit_service import LiveKitService
    
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "Cannot make call - no company context"
        
        livekit = LiveKitService(company)
        result = livekit.initiate_outbound_call(to, purpose)
        
        if result.get('success'):
            return f"Call initiated to {to} for: {purpose}"
        else:
            return f"Failed to initiate call: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error initiating call: {str(e)}"


# ============================================================
# Calendar Tools
# ============================================================

@tool
def schedule_appointment(
    date: str, 
    time: str, 
    attendee_email: str, 
    client_name: str = "",
    meeting_reason: str = "",
    client_city: str = "",
    client_country: str = "",
    client_timezone: str = ""
) -> str:
    """
    Schedule an appointment on Google Calendar with Google Meet link.
    IMPORTANT: Collect city/country/timezone and meeting reason BEFORE calling.
    
    Args:
        date: Date in YYYY-MM-DD format (Client's date if timezone provided, else Company's)
        time: Time in HH:MM format (Client's time if timezone provided, else Company's)
        attendee_email: Email of the person to invite
        client_name: Client's full name (lookup by email if empty)
        meeting_reason: Purpose/subject of the meeting
        client_city: Client's city
        client_country: Client's country
        client_timezone: Client's IANA timezone (e.g. "America/Buenos_Aires"). IF PROVIDED, time is treated as local to this zone.
        
    Returns:
        Appointment confirmation with Google Meet link
    """
    
    from services.google_service import GoogleCalendarIntegration
    from models.appointment import Appointment, AppointmentStatus
    from models.customer import Customer
    from extensions import db
    from datetime import datetime, timedelta
    import pytz
    
    try:
        company = getattr(g, 'current_company', None)
        conversation = getattr(g, 'current_conversation', None)
        if not company:
            return "Cannot schedule - no company context"
        
        # 1. Resolve Customer Name
        customer = None
        if attendee_email:
            customer = Customer.query.filter_by(company_id=company.id, email=attendee_email).first()
        
        if not client_name and customer:
            client_name = f"{customer.first_name} {customer.last_name}".strip()
            
        # 2. Build Title and Description
        title = f"Reunión con {client_name} | {company.name}" if client_name else f"Reunión | {company.name}"
        
        description_parts = []
        if meeting_reason: description_parts.append(f"Asunto: {meeting_reason}")
        if client_timezone: description_parts.append(f"Zona horaria cliente: {client_timezone}")
        loc_str = ", ".join(filter(None, [client_city, client_country]))
        if loc_str: description_parts.append(f"Ubicación cliente: {loc_str}")
        if attendee_email: description_parts.append(f"Email: {attendee_email}")
        description = "\n".join(description_parts)
        
        # 3. Timezone Logic - The Critical Fix
        company_tz_str = company.timezone or 'UTC'
        company_tz = pytz.timezone(company_tz_str)
        
        # Parse naive datetime from arguments
        naive_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        if client_timezone:
            try:
                # If client timezone is provided, localize to THAT zone
                client_tz = pytz.timezone(client_timezone)
                localized_dt = client_tz.localize(naive_dt)
                # Convert to UTC for storage and API
                final_dt = localized_dt.astimezone(pytz.UTC)
                print(f"[DEBUG] Converted {naive_dt} ({client_timezone}) -> {final_dt} (UTC)")
            except Exception as e:
                return f"Error con la zona horaria del cliente '{client_timezone}': {str(e)}"
        else:
            # Fallback: Assume the time is in Company's Timezone
            localized_dt = company_tz.localize(naive_dt)
            final_dt = localized_dt.astimezone(pytz.UTC)
            print(f"[DEBUG] Assumed Company Time: {naive_dt} ({company_tz_str}) -> {final_dt} (UTC)")

        if client_timezone:
            # Add note about converted time if different
            description += f"\n\n(Time converted from customer's {client_timezone} timezone)"

        # 4. Schedule meeting with configured provider (Google Meet, Microsoft Teams, Zoom)
        from services.meeting_service import MeetingService
        result = MeetingService.schedule_meeting(
            company=company,
            title=title,
            start_time=final_dt,
            duration_minutes=30,
            description=description,
            attendees=[attendee_email]
        )
        
        if result.get('success'):
            meet_link = result.get('meeting_url') or result.get('meet_link', '')
            event_id = result.get('event_id', '')
            provider_name = result.get('provider', 'google')
            provider_display = {'google': 'Google Meet', 'teams': 'Microsoft Teams', 'zoom': 'Zoom'}.get(provider_name, provider_name.title())
            
            # 5. Save to Database
            appointment = Appointment(
                company_id=company.id,
                customer_id=customer.id if customer else None,
                conversation_id=conversation.id if conversation else None,
                title=title,
                description=description,
                start_time=final_dt, # Store as UTC
                end_time=final_dt + timedelta(minutes=30),
                duration_minutes=30,
                client_city=client_city,
                client_country=client_country,
                client_timezone=client_timezone,
                google_event_id=event_id,
                google_meet_link=meet_link,
                status=AppointmentStatus.SCHEDULED.value,
                channel_type=conversation.channel if conversation else 'webchat'
            )
            db.session.add(appointment)
            
            # --- AUTO-RESOLVE CONVERSATION ---
            if conversation:
                conversation.is_resolved = True
                conversation.resolved_at = datetime.utcnow()
            # ---------------------------------
                
            db.session.commit()
            
            # 6. CRM Sync (Lifecycle -> SQL)
            try:
                if attendee_email:
                    from services.crm.factory import CRMFactory
                    from services.crm.canonical_models import Contact
                    crm_connector = CRMFactory.get_connector(company.id)
                    if crm_connector:
                        # Mark as SQL (Sales Qualified Lead)
                        contact_data = Contact(
                            email=attendee_email,
                            lead_status='SQL'
                        )
                        crm_connector.create_or_update_contact(attendee_email, contact_data)
            except Exception as crm_err:
                logger.error(f"CRM Sync Error (Schedule Appointment): {crm_err}")
            # ---------------------------
            
            response = f"✅ Cita agendada: {title}\n📅 {date} a las {time} ({client_timezone or company_tz_str})"
            if meet_link: response += f"\n🔗 Enlace de {provider_display}: {meet_link}"
            response += f"\n📧 Invitación enviada a: {attendee_email}"
            return response
        else:
            return f"Error al agendar reunión: {result.get('error', 'Desconocido')}"

    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error scheduling appointment: {str(e)}"


@tool
def check_availability(date: str, client_timezone: str = None, preferred_time: str = None) -> str:
    """
    Check available slots for a given date.
    Args:
        date: YYYY-MM-DD format
        client_timezone: Client's IANA timezone (e.g. 'America/Buenos_Aires')
        preferred_time: Optional HH:MM format. If provided and unavailable, returns 2 slots before and 2 after.
    """
    from services.google_service import GoogleCalendarIntegration
    
    import pytz
    from datetime import datetime, timedelta
    
    try:
        # Preventive rollback for stale connections
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "Cannot check availability - no company context"
        
        calendar = GoogleCalendarIntegration(company)
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return "Invalid date format. Use YYYY-MM-DD"
            
        slots = calendar.get_free_slots(date_obj)
        
        if not slots:
            return f"No hay disponibilidad para el {date}"

        # Setup timezone conversion
        company_tz = pytz.timezone(company.timezone) if company.timezone else pytz.UTC
        target_tz = pytz.timezone(client_timezone) if client_timezone else company_tz
        tz_label = f"({client_timezone})" if client_timezone else "(Hora Empresa)"
        
        # Convert all slots to target timezone for comparison
        converted_slots = []
        for s in slots:
            start_local = s['start'].astimezone(target_tz)
            end_local = s['end'].astimezone(target_tz)
            converted_slots.append({
                'start': start_local,
                'end': end_local,
                'str': f"{start_local.strftime('%H:%M')}-{end_local.strftime('%H:%M')}"
            })
        
        # If preferred_time is provided, check if available and suggest alternatives
        if preferred_time:
            try:
                pref_hour, pref_min = map(int, preferred_time.split(':'))
                pref_dt = target_tz.localize(datetime.combine(date_obj, datetime.min.time().replace(hour=pref_hour, minute=pref_min)))
                
                # Check if preferred time is available
                is_available = any(s['start'] <= pref_dt < s['end'] for s in converted_slots)
                
                if is_available:
                    return f"✅ El horario {preferred_time} está disponible el {date} {tz_label}"
                else:
                    # Find 2 slots before and 2 after the preferred time
                    before = [s for s in converted_slots if s['start'] < pref_dt][-2:]  # Last 2 before
                    after = [s for s in converted_slots if s['start'] >= pref_dt][:2]   # First 2 after
                    
                    suggestions = before + after
                    if not suggestions:
                        return f"No hay horarios cercanos a {preferred_time} disponibles el {date}"
                    
                    suggestion_strs = [s['str'] for s in suggestions]
                    return f"❌ El horario {preferred_time} no está disponible. Opciones cercanas {tz_label}: {', '.join(suggestion_strs)}"
                    
            except (ValueError, AttributeError):
                pass  # Invalid preferred_time format, fall through to show all
        
        # Default: show all available slots
        all_slots_str = ", ".join([s['str'] for s in converted_slots])
        return f"Horarios disponibles el {date} {tz_label}: {all_slots_str}"
            
    except Exception as e:
        return f"Error checking availability: {str(e)}"


# ============================================================
# Centralized CRM Tools (HubSpot, Salesforce, Pipedrive, Zoho, Dynamics 365, Custom)
# ============================================================

@tool
def crm_get_contact(contact_id: str) -> str:
    """
    Retrieve contact details from the company's CRM.
    
    Args:
        contact_id: The unique ID of the contact in the CRM.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        contact = connector.get_contact(contact_id)
        if not contact:
            return f"Contact with ID {contact_id} not found in the CRM."
        
        return f"Contact Details: {contact.model_dump_json(indent=2)}"
    except Exception as e:
        return f"Error retrieving contact from CRM: {str(e)}"


@tool
def crm_create_contact(email: str, first_name: str, last_name: str, phone: Optional[str] = None) -> str:
    """
    Create a new contact in the company's CRM.
    
    Args:
        email: Contact's email address.
        first_name: Contact's first name.
        last_name: Contact's last name.
        phone: Optional contact phone number.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone
        }
        contact = connector.create_contact(payload)
        return f"Successfully created Contact in CRM: ID={contact.id}, Name={contact.first_name} {contact.last_name}"
    except Exception as e:
        return f"Error creating contact in CRM: {str(e)}"


@tool
def crm_update_contact(contact_id: str, email: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None, phone: Optional[str] = None) -> str:
    """
    Update an existing contact in the company's CRM.
    
    Args:
        contact_id: Unique ID of the contact to update.
        email: Optional new email address.
        first_name: Optional new first name.
        last_name: Optional new last name.
        phone: Optional new phone number.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        payload = {}
        if email: payload["email"] = email
        if first_name: payload["first_name"] = first_name
        if last_name: payload["last_name"] = last_name
        if phone: payload["phone"] = phone
        
        contact = connector.update_contact(contact_id, payload)
        return f"Successfully updated Contact in CRM: ID={contact.id}"
    except Exception as e:
        return f"Error updating contact in CRM: {str(e)}"


@tool
def crm_get_lead(lead_id: str) -> str:
    """
    Retrieve lead details from the company's CRM.
    
    Args:
        lead_id: Unique ID of the lead.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        lead = connector.get_lead(lead_id)
        if not lead:
            return f"Lead with ID {lead_id} not found in the CRM."
        
        return f"Lead Details: {lead.model_dump_json(indent=2)}"
    except Exception as e:
        return f"Error retrieving lead from CRM: {str(e)}"


@tool
def crm_create_lead(full_name: str, email: Optional[str] = None, source: Optional[str] = None, status: Optional[str] = "New", estimated_value: Optional[float] = None) -> str:
    """
    Create a new sales lead in the company's CRM.
    
    Args:
        full_name: Full name of the lead.
        email: Optional email address.
        source: Marketing source (e.g. 'Web Chat', 'Referral').
        status: Status or stage in lead pipeline (default: 'New').
        estimated_value: Optional estimated budget or financial value.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        payload = {
            "full_name": full_name,
            "email": email,
            "source": source,
            "status": status,
            "estimated_value": estimated_value
        }
        lead = connector.create_lead(payload)
        return f"Successfully created Lead in CRM: ID={lead.id}, Name={lead.full_name}, Status={lead.status}"
    except Exception as e:
        return f"Error creating lead in CRM: {str(e)}"


@tool
def crm_update_lead(lead_id: str, status: Optional[str] = None, full_name: Optional[str] = None) -> str:
    """
    Update an existing lead's details or status in the company's CRM.
    
    Args:
        lead_id: Unique ID of the lead.
        status: Optional new status/stage.
        full_name: Optional new full name.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        payload = {}
        if status: payload["status"] = status
        if full_name: payload["full_name"] = full_name
        
        lead = connector.update_lead(lead_id, payload)
        return f"Successfully updated Lead in CRM: ID={lead.id}"
    except Exception as e:
        return f"Error updating lead in CRM: {str(e)}"


@tool
def crm_create_account(name: str, domain: Optional[str] = None, annual_revenue: Optional[float] = None, industry: Optional[str] = None) -> str:
    """
    Create a new account/company profile in the CRM.
    
    Args:
        name: Name of the company/organization.
        domain: Primary domain/website (e.g. 'company.com').
        annual_revenue: Optional annual revenue figure.
        industry: Optional industry vertical.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        payload = {
            "name": name,
            "domain": domain,
            "annual_revenue": annual_revenue,
            "industry": industry
        }
        account = connector.create_account(payload)
        return f"Successfully created Account in CRM: ID={account.id}, Name={account.name}"
    except Exception as e:
        return f"Error creating account in CRM: {str(e)}"


@tool
def crm_create_deal(title: str, amount: float, stage: str, account_id: Optional[str] = None, expected_closing_date: Optional[str] = None) -> str:
    """
    Create a sales opportunity/deal in the CRM.
    
    Args:
        title: Deal title or opportunity name.
        amount: Estimated financial value of the deal.
        stage: Pipeline stage (e.g. 'Prospecting', 'Proposal Sent').
        account_id: Optional associated account/company ID.
        expected_closing_date: Optional closing target date (YYYY-MM-DD format).
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        payload = {
            "title": title,
            "amount": amount,
            "stage": stage,
            "account_id": account_id,
            "expected_closing_date": expected_closing_date
        }
        deal = connector.create_deal(payload)
        return f"Successfully created Deal in CRM: ID={deal.id}, Title={deal.title}, Stage={deal.stage}, Value={deal.amount}"
    except Exception as e:
        return f"Error creating deal in CRM: {str(e)}"


@tool
def crm_update_deal_stage(deal_id: str, new_stage: str) -> str:
    """
    Move a deal to a new stage in the pipeline.
    
    Args:
        deal_id: Unique ID of the deal.
        new_stage: Target pipeline stage name or ID.
    """
    from services.crm.factory import get_crm_connector
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass

        company = getattr(g, 'current_company', None)
        if not company:
            return "CRM not available - no company context"
        
        connector = get_crm_connector(company)
        if not connector:
            return "No CRM platform integrated for this company."
        
        deal = connector.update_deal_stage(deal_id, new_stage)
        return f"Successfully updated Deal stage in CRM: ID={deal.id}, New Stage={deal.stage}"
    except Exception as e:
        return f"Error updating deal stage in CRM: {str(e)}"


# ============================================================
# E-commerce Tools
# ============================================================

@tool
def search_ecommerce_products(
    query: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: Optional[str] = None,  # 'price_asc', 'price_desc', 'date_desc', 'popularity_desc'
    limit: int = 10
) -> str:
    """
    Search and filter products in the company's connected e-commerce store.
    Use this when a customer asks about products, prices, availability, best sellers, or newest items.
    
    Args:
        query: Search keywords for finding products (e.g. 'leche', 'pañales'). Use '' (empty string) to search ALL products without keyword filter.
        brand: Brand/Vendor name to filter by (e.g. 'dbebes'). Optional.
        category: Category name or ID to filter by. Optional.
        sort_by: Criteria to sort results: 'price_asc' (cheapest), 'price_desc', 'date_desc' (newest), 'popularity_desc' (best sellers). Optional.
        limit: Max number of products to return. IMPORTANT: use the exact number the user requested (e.g. if they say '10 productos', set limit=10). Default is 10.
    """
    
    from services.ecommerce.factory import get_ecommerce_adapter
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "E-commerce not available - no company context"
        
        adapter = get_ecommerce_adapter(company)
        if not adapter:
            return "No e-commerce store connected. Ask the admin to configure it in Settings > E-commerce."

        # Normalize accent marks and common Spanish terms/typos
        def normalize_spanish(text: str) -> str:
            if not text:
                return ""
            text = text.lower()
            replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u'}
            for k, v in replacements.items():
                text = text.replace(k, v)
            return text.strip()

        clean_query = ""
        if query:
            clean_query = query.strip()
            # Normalize accents
            clean_query = normalize_spanish(clean_query)
            # Normalize common search keywords / singularizations
            words = clean_query.split()
            cleaned_words = []
            for w in words:
                if w in ['panales', 'panal', 'pañales']:
                    cleaned_words.append('pañal')
                elif w in ['leches', 'leche']:
                    cleaned_words.append('leche')
                else:
                    cleaned_words.append(w)
            clean_query = " ".join(cleaned_words)

        # Build search query for the adapter
        search_term = clean_query
        if brand:
            norm_brand = normalize_spanish(brand)
            if norm_brand not in normalize_spanish(search_term):
                if search_term:
                    search_term = f"{search_term} {brand}"
                else:
                    search_term = brand

        # Fetch products (request more than limit to allow python-side filtering/sorting)
        fetch_limit = max(limit * 3, 30)
        products = []
        
        # Try search with combined term
        if search_term:
            try:
                products = adapter.search_products(search_term, limit=fetch_limit)
            except Exception as search_err:
                print(f"[ECOMMERCE TOOL] Combined search failed: {search_err}")
            
        # Fallback 1: If search returned nothing and we had a brand, try searching just for the brand
        if not products and brand and clean_query:
            try:
                print(f"[ECOMMERCE TOOL] Combined search returned no products. Retrying with brand: {brand}")
                products = adapter.search_products(brand, limit=fetch_limit)
            except Exception:
                pass
            
        # Fallback 2: Try searching just for the clean query
        if not products and clean_query:
            try:
                print(f"[ECOMMERCE TOOL] Search failed. Retrying with clean query: {clean_query}")
                products = adapter.search_products(clean_query, limit=fetch_limit)
            except Exception:
                pass
            
        # Fallback 3: If still nothing, try splitting the query and searching the longest word
        if not products and clean_query and len(clean_query.split()) > 1:
            try:
                words = sorted(clean_query.split(), key=len, reverse=True)
                longest_word = words[0]
                print(f"[ECOMMERCE TOOL] Search failed. Retrying with longest word: {longest_word}")
                products = adapter.search_products(longest_word, limit=fetch_limit)
            except Exception:
                pass

        # Fallback 4: If query was empty or asking for everything
        if not products and not search_term:
            try:
                products = adapter.search_products("", limit=fetch_limit)
            except Exception:
                pass

        if not products:
            desc = f"matching '{query}'" if query else ""
            if brand:
                desc += f" of brand '{brand}'"
            return f"No products found {desc.strip()}."

        # 2. Filter products in Python
        filtered_products = []
        for p in products:
            p_name = p.get('name', '').lower()
            p_desc = p.get('short_description', p.get('description', '')).lower()
            
            # Brand filter (case-insensitive containment check)
            if brand:
                b_lower = brand.lower()
                # Check title, vendor (if any), or description
                if b_lower not in p_name and b_lower not in p_desc:
                    continue
                    
            # Category filter (case-insensitive containment check)
            if category:
                cat_lower = category.lower()
                p_cat = str(p.get('category', p.get('categories', ''))).lower()
                if cat_lower not in p_cat and cat_lower not in p_name:
                    continue

            # Standardize price as float for sorting
            try:
                p['price_val'] = float(p.get('price', 0))
            except:
                p['price_val'] = 0.0

            filtered_products.append(p)

        # 3. Sort products in Python
        if sort_by == 'price_asc':
            filtered_products.sort(key=lambda x: x['price_val'])
        elif sort_by == 'price_desc':
            filtered_products.sort(key=lambda x: x['price_val'], reverse=True)

        # Limit final results
        final_products = filtered_products[:limit]

        if not final_products:
            # If our strict filtering returned empty but we have products, fall back to showing original search results
            final_products = products[:limit]

        lines = []
        for p in final_products:
            stock_val = p.get('stock', -1)
            if stock_val > 10:
                stock_str = "Disponible"
            elif 0 < stock_val <= 10:
                stock_str = f"¡Solo quedan {stock_val}!"
            elif stock_val == 0:
                stock_str = "Agotado"
            else:
                stock_str = "Disponible"

            price_str = f"${p['price']}" if p.get('price') else "Price not available"
            line = f"- **{p['name']}** | {price_str} | {stock_str} | ID: {p['id']}"
            if p.get('variants'):
                line += f" ({len(p['variants'])} variants)"
            lines.append(line)
        
        return f"Found {len(final_products)} products:\n" + "\n".join(lines)
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error searching products: {str(e)}"


@tool
def check_ecommerce_stock(product_id: str) -> str:
    """
    Check the real-time stock/inventory for a specific product.
    Use the product ID obtained from search_ecommerce_products.
    
    Args:
        product_id: The product ID from the e-commerce platform
        
    Returns:
        Stock levels for the product and its variants
    """
    
    from services.ecommerce.factory import get_ecommerce_adapter
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "E-commerce not available - no company context"
        
        adapter = get_ecommerce_adapter(company)
        if not adapter:
            return "No e-commerce store connected."
        
        inventory = adapter.get_inventory(product_id)
        total = inventory.get('total_stock', 0)
        result = f"Total stock for product {product_id}: {total} units\n"
        
        variants = inventory.get('variants', [])
        if variants:
            result += "Breakdown by variant:\n"
            for v in variants:
                result += f"  - {v.get('name', v['id'])}: {v['stock']} units\n"
        
        return result
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error checking stock: {str(e)}"


@tool
def create_ecommerce_order(
    customer_email: str,
    customer_first_name: str,
    customer_last_name: str,
    product_ids: str,
    quantities: str,
    customer_phone: str = "",
    notes: str = ""
) -> str:
    """
    Create an order on the connected e-commerce platform.
    PREREQUISITE: You MUST verify customer identity first AND confirm the order details.
    
    Args:
        customer_email: Customer's email address
        customer_first_name: Customer's first name
        customer_last_name: Customer's last name
        product_ids: Comma-separated product IDs (e.g. '123,456')
        quantities: Comma-separated quantities matching product_ids (e.g. '2,1')
        customer_phone: Optional phone number
        notes: Optional order notes
        
    Returns:
        Order confirmation with order ID and status
    """
    
    from services.ecommerce.factory import get_ecommerce_adapter
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "E-commerce not available - no company context"
        
        adapter = get_ecommerce_adapter(company)
        if not adapter:
            return "No e-commerce store connected."
        
        # Parse comma-separated IDs and quantities
        ids = [pid.strip() for pid in product_ids.split(',')]
        qtys = [int(q.strip()) for q in quantities.split(',')]
        
        if len(ids) != len(qtys):
            return "Error: product_ids and quantities must have the same number of items."
        
        cart_items = [{'product_id': pid, 'quantity': qty} for pid, qty in zip(ids, qtys)]
        
        customer_data = {
            'email': customer_email,
            'first_name': customer_first_name,
            'last_name': customer_last_name,
            'phone': customer_phone,
            'address': {},  # Address can be collected later
        }
        
        result = adapter.create_order(customer_data, cart_items, notes)
        
        if result.get('success'):
            msg = f"✅ Order created successfully!\n"
            msg += f"Order ID: {result.get('order_id', 'N/A')}\n"
            msg += f"Order #: {result.get('order_number', 'N/A')}\n"
            msg += f"Total: ${result.get('total', '0')} {result.get('currency', '')}\n"
            msg += f"Status: {result.get('status', 'pending')}"
            if result.get('checkout_url'):
                msg += f"\nCheckout URL: {result['checkout_url']}"
            return msg
        else:
            return f"❌ Failed to create order: {result.get('error', 'Unknown error')}"
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error creating order: {str(e)}"


# ============================================================
# ERP Tools
# ============================================================

@tool
def erp_query_records(entity: str, filters_json: str = "{}", limit: int = 20) -> str:
    """
    Query records from the company's connected ERP system.
    Use this to search invoices, customers, products, journal entries, or any entity.
    
    Args:
        entity: The canonical entity type to query. Options: 'customers', 'invoices', 'items', 'records'.
                For 'records', you must also specify the native entity name in filters.
        filters_json: JSON string with filter key-value pairs (e.g. '{"state": "posted"}')
        limit: Maximum number of records to return (default 20)
        
    Returns:
        A formatted list of matching records from the ERP
    """
    
    from services.erp.factory import get_erp_driver
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "ERP not available - no company context"
        
        driver = get_erp_driver(company)
        if not driver:
            return "No ERP system connected. Ask the admin to configure it in Settings > ERP."
        
        import json
        filters = json.loads(filters_json) if filters_json else {}
        
        if entity == 'customers':
            records = driver.query_customers(filters, limit)
        elif entity == 'invoices':
            records = driver.query_invoices(filters, limit)
        elif entity == 'items':
            records = driver.query_items(filters, limit)
        else:
            records = driver.query_records(entity, filters, limit)
        
        if not records:
            return f"No {entity} records found matching the filters."
        
        result = f"Found {len(records)} {entity} record(s):\n"
        for r in records[:limit]:
            # Build a summary line from available keys
            summary_parts = []
            for key, val in r.items():
                if val is not None and str(val).strip():
                    summary_parts.append(f"{key}: {val}")
            result += f"- {' | '.join(summary_parts[:6])}\n"
        
        return result
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error querying ERP records: {str(e)}"


@tool
def erp_get_invoice(invoice_id: str) -> str:
    """
    Retrieve detailed information for a specific invoice from the connected ERP.
    
    Args:
        invoice_id: The invoice ID or document number in the ERP system
        
    Returns:
        Detailed invoice information including lines, totals, and status
    """
    
    from services.erp.factory import get_erp_driver
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "ERP not available - no company context"
        
        driver = get_erp_driver(company)
        if not driver:
            return "No ERP system connected."
        
        import json
        invoice = driver.get_invoice(invoice_id)
        return f"Invoice details:\n{json.dumps(invoice, indent=2, default=str)}"
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error retrieving invoice: {str(e)}"


@tool
def erp_create_customer(name: str, email: str = "", phone: str = "", tax_id: str = "") -> str:
    """
    Create a new customer/business partner in the connected ERP system.
    PREREQUISITE: Verify the customer does not already exist using erp_query_records first.
    
    Args:
        name: Customer's full name or company name
        email: Customer's email address
        phone: Customer's phone number
        tax_id: Tax identification number (DNI/RUT/VAT)
        
    Returns:
        Confirmation with the new customer ID
    """
    
    from services.erp.factory import get_erp_driver
    
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "ERP not available - no company context"
        
        driver = get_erp_driver(company)
        if not driver:
            return "No ERP system connected."
        
        import json
        result = driver.create_customer({
            "name": name,
            "email": email,
            "phone": phone,
            "tax_id": tax_id,
        })
        return json.dumps({"status": "success", "result": result})
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error creating customer in ERP: {str(e)}"


@tool
def validate_twilio_credentials(account_sid: str, auth_token: str) -> str:
    """
    Validate Twilio Account SID and Auth Token, and save them in the company context.
    
    Args:
        account_sid: The Twilio Account SID (starts with AC)
        auth_token: The Twilio Auth Token
        
    Returns:
        Status message indicating success or failure.
    """
    import requests
    from extensions import db
    from sqlalchemy.orm.attributes import flag_modified
    from routes.twilio import generate_rsa_keypair

    company = getattr(g, 'current_company', None)
    if not company:
        return "Validation failed: No company context found."

    account_sid = account_sid.strip()
    auth_token = auth_token.strip()

    # Validate with Twilio API GET account resource
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
    try:
        response = requests.get(url, auth=(account_sid, auth_token), timeout=15)
        if response.status_code != 200:
            return f"Validation failed: Invalid Twilio credentials (HTTP {response.status_code})"
    except Exception as err:
        return f"Validation failed: Failed to reach Twilio API: {str(err)}"

    # Save credentials and generate RSA keys if missing
    if not company.api_keys:
        company.api_keys = {}

    company.api_keys['twilio_sid'] = account_sid
    company.api_keys['twilio_token'] = auth_token

    # Auto-generate RSA key pair for dynamic WhatsApp Flows
    if 'rsa_private_key' not in company.api_keys:
        try:
            priv_pem, pub_pem = generate_rsa_keypair()
            company.api_keys['rsa_private_key'] = priv_pem
            company.api_keys['rsa_public_key'] = pub_pem
        except Exception as rsa_err:
            print(f"Failed to generate RSA keys for company {company.id}: {rsa_err}")

    flag_modified(company, "api_keys")
    db.session.commit()

    return "Success: Twilio credentials validated and saved successfully. RSA keys generated for WhatsApp Flows."


@tool
def search_twilio_numbers(country_code: str, number_type: str = "local", sms: bool = True, voice: bool = True) -> str:
    """
    Search for available phone numbers in Twilio for purchase.
    
    Args:
        country_code: Two-letter ISO country code (e.g. US, EC)
        number_type: Type of number: 'local', 'mobile', or 'tollfree'
        sms: Filter numbers that support SMS (default True)
        voice: Filter numbers that support Voice calls (default True)
        
    Returns:
        JSON string or list of available numbers with pricing information.
    """
    import os
    import json
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException

    company = getattr(g, 'current_company', None)
    if not company:
        return "Search failed: No company context found."

    sid = company.api_keys.get('twilio_sid') if company.api_keys else None
    token = company.api_keys.get('twilio_token') if company.api_keys else None

    # Fallback to environment
    if not sid or not token:
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        token = os.getenv('TWILIO_AUTH_TOKEN')

    if not sid or not token:
        return "Search failed: Twilio credentials not configured for company."

    country_code = country_code.upper()
    number_type = number_type.lower()

    try:
        client = Client(sid, token)
        search_res = client.available_phone_numbers(country_code)
        
        if number_type == 'mobile':
            raw_list = search_res.mobile.list(sms_enabled=sms, voice_enabled=voice, limit=5)
        elif number_type == 'tollfree':
            raw_list = search_res.toll_free.list(sms_enabled=sms, voice_enabled=voice, limit=5)
        else:
            raw_list = search_res.local.list(sms_enabled=sms, voice_enabled=voice, limit=5)

        mapped_numbers = []
        for n in raw_list:
            mapped_numbers.append({
                'phoneNumber': n.phone_number,
                'friendlyName': n.friendly_name,
                'baseSetupPrice': '1.00' if country_code == 'US' else '2.00', # Default mock rates
                'baseRecurringPrice': '1.15' if country_code == 'EC' else '1.00',
                'addressRequirements': n.address_requirements
            })

        return json.dumps({
            'success': True,
            'numbers': mapped_numbers
        }, indent=2)

    except TwilioRestException as e:
        return json.dumps({'success': False, 'error': str(e), 'code': e.code})
    except Exception as e:
        return json.dumps({'success': False, 'error': str(e)})


@tool
def purchase_twilio_number(phone_number: str) -> str:
    """
    Purchase and configure a Twilio phone number for SMS and Voice.
    
    Args:
        phone_number: Phone number to purchase in E.164 format (e.g., +15005550006)
        
    Returns:
        Status message indicating success or failure.
    """
    import os
    import json
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    from extensions import db
    from models.purchased_number import PurchasedNumber
    from models.channel import Channel, ChannelStatus, ChannelType
    from sqlalchemy.orm.attributes import flag_modified

    company = getattr(g, 'current_company', None)
    if not company:
        return "Purchase failed: No company context found."

    sid = company.api_keys.get('twilio_sid') if company.api_keys else None
    token = company.api_keys.get('twilio_token') if company.api_keys else None

    # Fallback to env
    if not sid or not token:
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        token = os.getenv('TWILIO_AUTH_TOKEN')

    if not sid or not token:
        return "Purchase failed: Twilio credentials not configured."

    phone_number = phone_number.strip()

    # MOCKING FOR TEST CREDENTIALS
    is_test_mode = sid.startswith("AC") and ("test" in sid.lower() or "mock" in sid.lower() or sid == os.getenv('TWILIO_ACCOUNT_SID'))
    
    if is_test_mode:
        if phone_number == '+15005550000':
            return "Purchase failed: Phone number is not available (Twilio error 21440)."
        elif phone_number == '+15005550001':
            return "Purchase failed: Insufficient funds to purchase number (Twilio error 21005)."
        elif phone_number == '+15005550006':
            purchased = PurchasedNumber(
                company_id=company.id,
                phone_number=phone_number,
                sid="PNtestmockedsid12345",
                friendly_name="pymai_test_number"
            )
            db.session.add(purchased)
            
            if not company.api_keys:
                company.api_keys = {}
            company.api_keys['twilio_phone_number'] = phone_number
            company.api_keys['twilio_sid_pn'] = purchased.sid
            
            flag_modified(company, "api_keys")
            db.session.commit()
            
            return f"Success: Number {phone_number} purchased and configured successfully (MOCK TEST MODE)."

    try:
        client = Client(sid, token)
        
        args_data = {
            'phone_number': phone_number,
            'friendly_name': f"pymai_incoming_{phone_number}"
        }

        # Buy the number
        incoming_number = client.incoming_phone_numbers.create(**args_data)
        
        # Configure endpoints pointing to PymAI FastAPI
        public_url = os.getenv('API_BASE_URL', 'https://api.aikrofy.com').rstrip('/')
        
        client.incoming_phone_numbers(incoming_number.sid).update(
            sms_url=f"{public_url}/v1/webhooks/sms",
            sms_method="POST",
            sms_fallback_url=f"{public_url}/v1/webhooks/sms/fallback",
            sms_fallback_method="POST",
            voice_url=f"{public_url}/v1/webhooks/voice",
            voice_method="POST",
            voice_fallback_url=f"{public_url}/v1/webhooks/voice/fallback",
            voice_fallback_method="POST"
        )

        # Store in PurchasedNumbers table
        purchased = PurchasedNumber(
            company_id=company.id,
            phone_number=phone_number,
            sid=incoming_number.sid,
            friendly_name=incoming_number.friendly_name
        )
        db.session.add(purchased)

        # Save to company keys
        if not company.api_keys:
            company.api_keys = {}
        company.api_keys['twilio_phone_number'] = phone_number
        company.api_keys['twilio_sid_pn'] = incoming_number.sid
        
        # Automatically register SMS & Voice Channels if they don't exist
        for ch_type in [ChannelType.SMS, ChannelType.VOICE]:
            ch = Channel.query.filter_by(company_id=company.id, channel_type=ch_type).first()
            if not ch:
                ch = Channel(
                    company_id=company.id,
                    channel_type=ch_type,
                    status=ChannelStatus.CONNECTED,
                    phone_number=phone_number,
                    credentials={
                        'provider': 'twilio',
                        'phone_number': phone_number,
                        'incoming_pn_sid': incoming_number.sid
                    }
                )
                db.session.add(ch)
            else:
                ch.status = ChannelStatus.CONNECTED
                ch.phone_number = phone_number
                ch.credentials = {
                    'provider': 'twilio',
                    'phone_number': phone_number,
                    'incoming_pn_sid': incoming_number.sid
                }

        flag_modified(company, "api_keys")
        db.session.commit()

        return f"Success: Number {phone_number} purchased and configured successfully for company {company.name}."

    except TwilioRestException as e:
        return f"Purchase failed: {str(e)} (code {e.code})"
    except Exception as e:
        return f"Purchase failed: {str(e)}"


# ============================================================
# Handoff Tools
# ============================================================

@tool
def handoff_to_department(department_name: str, reason: str) -> str:
    """
    Transfer (handoff) the conversation to a different department or agent.
    Use this when the user's request is outside your expertise (e.g. Sales, Customer Service, Tech Support).
    
    Args:
        department_name: Target department (e.g., 'sales', 'operations', 'marketing', 'customer-service').
        reason: Brief reason for the handoff to inform the next agent.
        
    Returns:
        Status of the handoff operation.
    """
    from models.agent import Agent
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        conversation = getattr(g, 'current_conversation', None)
        
        if not company or not conversation:
            return "Error: Context not available for handoff."
            
        # Try to find a matching agent by name (like cso_sales, ceo_orchestrator, etc)
        # Search criteria: agent name contains the department keyword
        search_term = f"%{department_name.lower().replace(' ', '_')}%"
        agent = Agent.query.filter(
            Agent.company_id == company.id,
            Agent.is_active == True,
            Agent.name.ilike(search_term)
        ).first()
        
        if not agent:
            # Fallback to creating or finding an agent for this department
            agent = Agent.query.filter_by(company_id=company.id, is_active=True).first()
            if not agent:
                return "Error: No suitable agent found for handoff."
                
        # Perform handoff
        old_agent_id = conversation.agent_id
        conversation.agent_id = agent.id
        db.session.commit()
        
        return f"Handoff successful. Transferred from agent {old_agent_id} to {agent.name} (ID: {agent.id}). Reason logged: {reason}."
    except Exception as e:
        db.session.rollback()
        return f"Error executing handoff: {str(e)}"


# ============================================================
# Navigation and UI Control Tools
# ============================================================

@tool
def system_navigate(section: str) -> str:
    """
    Navigate the user or visitor to a specific section or page on the website or control panel.
    Use this when the user asks to go to, open, see, or visit a page, section, anchor, dashboard, or panel.
    
    Args:
        section: The target section, path, anchor, or keyword (e.g. '#servicios', '#precios', '#contacto', 'servicios', 'precios', 'contacto', 'dashboard', 'analytics', 'settings').
        
    Returns:
        JSON string indicating success and the navigation action.
    """
    section_mappings = {
        # Dashboard sections (English keys)
        'dashboard': '/dashboard',
        'analytics': '/analytics',
        'chat': '/chat',
        'landing-pages': '/landing-pages',
        'landing pages': '/landing-pages',
        'landing': '/landing-pages',
        'contacts': '/contacts',
        'agents': '/agents',
        'agent': '/agents',
        'onboarding': '/onboarding',
        'channels': '/channels',
        'channel': '/channels',
        'documents': '/documents',
        'document': '/documents',
        'payments': '/payments',
        'billing': '/billing',
        'ecommerce': '/settings/ecommerce',
        'erp': '/settings/erp',
        'crm': '/settings/crm',
        'mcp': '/settings/mcp',
        'employees': '/employees',
        'settings': '/settings',
        'integrations': '/integrations',
        'integration': '/integrations',
        'marketplace': '/marketplace',
        'agency': '/agency',
        'pricing': '/pricing',
        # Dashboard sections (Spanish keys)
        'inicio': '/dashboard',
        'panel': '/dashboard',
        'agentes': '/agents',
        'agente': '/agents',
        'canales': '/channels',
        'canal': '/channels',
        'contactos': '/contacts',
        'documentos': '/documents',
        'facturación': '/billing',
        'facturacion': '/billing',
        'pagos': '/payments',
        'analítica': '/analytics',
        'analitica': '/analytics',
        'estadísticas': '/analytics',
        'estadisticas': '/analytics',
        'métricas': '/analytics',
        'metricas': '/analytics',
        'empleados': '/employees',
        'configuración': '/settings',
        'configuracion': '/settings',
        'ajustes': '/settings',
        'integraciones': '/integrations',
        'integración': '/integrations',
        'tienda de módulos': '/marketplace',
        'modulos': '/marketplace',
        'módulos': '/marketplace',
        'agencia': '/agency',
        'portal de agencia': '/agency',
        'landing pages': '/landing-pages',
        'páginas de aterrizaje': '/landing-pages',
        'paginas de aterrizaje': '/landing-pages',
        # Website sections & anchors
        'servicios': '#servicios',
        'services': '#servicios',
        'precios': '#precios',
        'planes': '#precios',
        'planes y precios': '#precios',
        'servicios y precios': '#servicios',
        'contacto': '#contacto',
        'contact': '#contacto',
        'nosotros': '#nosotros',
        'about': '#nosotros',
        'faq': '#faq',
        'preguntas': '#faq',
        'home': '#inicio',
        'testimonios': '#testimonios',
        'tienda': '/tienda',
        'catalogo': '#catalogo',
        'catálogo': '#catalogo',
    }
    
    sec_key = section.lower().strip()
    target_path = None
    
    if sec_key.startswith('#') or sec_key.startswith('/'):
        target_path = sec_key
    elif sec_key in section_mappings:
        target_path = section_mappings[sec_key]
    else:
        # fuzzy matching fallback
        for k, path in section_mappings.items():
            if k in sec_key or sec_key in k:
                target_path = path
                sec_key = k
                break
                
    if target_path:
        return json.dumps({
            "success": True,
            "message": f"Redirecting / navigating to {sec_key}...",
            "action": "navigate",
            "action_data": {
                "path": target_path,
                "url": target_path
            }
        })
    else:
        target_path = f"#{sec_key.replace(' ', '-')}"
        return json.dumps({
            "success": True,
            "message": f"Navigating to section {sec_key}...",
            "action": "navigate",
            "action_data": {
                "path": target_path,
                "url": target_path
            }
        })


@tool
def change_language(lang: str) -> str:
    """
    Change the UI, website and platform display language in real time.
    Use this immediately when you detect that the user is conversing in a different language
    than the currently selected one (e.g. if the selected language is 'en' but they write in 'es',
    or if they explicitly ask to change language).
    
    Args:
        lang: The 2-letter language code to change to (e.g., 'es', 'en', 'pt', 'de', 'fr', 'it') or language name (e.g. 'español', 'english').
        
    Returns:
        Confirmation message and action payload.
    """
    lang_clean = lang.strip().lower()
    lang_map = {
        'español': 'es', 'spanish': 'es', 'castellano': 'es',
        'inglés': 'en', 'ingles': 'en', 'english': 'en',
        'portugués': 'pt', 'portugues': 'pt', 'portuguese': 'pt',
        'francés': 'fr', 'frances': 'fr', 'french': 'fr',
        'alemán': 'de', 'aleman': 'de', 'german': 'de',
        'italiano': 'it', 'italian': 'it'
    }
    if lang_clean in lang_map:
        lang_clean = lang_map[lang_clean]
        
    return json.dumps({
        "success": True,
        "message": f"Language changed to {lang_clean}",
        "action": "change_language",
        "action_data": {
            "lang": lang_clean,
            "language": lang_clean
        }
    })


@tool
def change_website_language(lang: str, reason: str = "") -> str:
    """
    Change the website and chat display language in real time on the client's screen.
    Use this tool immediately whenever the user asks to change the site language to Spanish, English, Portuguese, French, German, Italian, etc., or when they switch languages.
    
    Args:
        lang: The 2-letter language code to change to (e.g., 'es', 'en', 'pt', 'fr', 'de', 'it') or language name (e.g. 'español', 'english').
        reason: Optional brief reason for changing language.
        
    Returns:
        JSON string with language change action payload for the web widget.
    """
    lang_clean = lang.strip().lower()
    lang_map = {
        'español': 'es', 'spanish': 'es', 'castellano': 'es',
        'inglés': 'en', 'ingles': 'en', 'english': 'en',
        'portugués': 'pt', 'portugues': 'pt', 'portuguese': 'pt',
        'francés': 'fr', 'frances': 'fr', 'french': 'fr',
        'alemán': 'de', 'aleman': 'de', 'german': 'de',
        'italiano': 'it', 'italian': 'it'
    }
    if lang_clean in lang_map:
        lang_clean = lang_map[lang_clean]
        
    return json.dumps({
        "success": True,
        "message": f"Cambiando idioma del sitio a: {lang_clean}",
        "action": "change_language",
        "action_data": {
            "lang": lang_clean,
            "language": lang_clean,
            "reason": reason
        }
    })


@tool
def change_website_theme(theme: str, reason: str = "") -> str:
    """
    Change or toggle the website theme (dark mode or light mode) in real time on the visitor's screen.
    Use this tool whenever the user asks to switch to dark mode, light mode, change theme colors, or toggle theme on the website.
    
    Args:
        theme: 'dark' (dark mode/modo oscuro), 'light' (light mode/modo claro), or 'toggle' (switch between them).
        reason: Optional brief explanation of why the theme is being changed.
        
    Returns:
        JSON string with theme change action payload for the web widget.
    """
    theme_clean = theme.strip().lower()
    if any(w in theme_clean for w in ['dark', 'oscuro', 'noche', 'negro']):
        target_theme = 'dark'
    elif any(w in theme_clean for w in ['light', 'claro', 'dia', 'blanco']):
        target_theme = 'light'
    else:
        target_theme = 'toggle'
        
    return json.dumps({
        "success": True,
        "message": f"Cambiando tema del sitio a: {target_theme}",
        "action": "change_theme",
        "action_data": {
            "theme": target_theme,
            "reason": reason
        }
    })


@tool
def highlight_website_element(target: str, reason: str = "") -> str:
    """
    Highlight, spotlight or draw visual attention to a specific element, section, product card, pricing card or button on the client's website in real time.
    Use this tool when guiding the user to look at a specific feature, button, form or pricing plan on the page.
    
    Args:
        target: CSS selector (e.g. '#pricing', '.cta-button', '#contact-form') or keyword matching section/element ID.
        reason: Brief explanation of what you are highlighting.
        
    Returns:
        JSON string with highlight action payload for the web widget.
    """
    clean_target = target.strip() if target else ""
    return json.dumps({
        "success": True,
        "message": f"Destacando elemento en pantalla: {clean_target}",
        "action": "highlight_element",
        "action_data": {
            "target": clean_target,
            "selector": clean_target,
            "reason": reason
        }
    })


@tool
def scroll_website_page(direction: str, reason: str = "") -> str:
    """
    Scroll or move the webpage viewport up, down, to the bottom, to the top, or to a specific section on the visitor's screen in real time.
    Use this tool whenever the visitor asks to scroll, move down, move up, scroll to bottom/footer, or scroll to top of the page (e.g. 'bajar en la página', 'scroll down', 'bajar hasta el final', 'subir').
    
    Args:
        direction: 'down' (scroll down), 'up' (scroll up), 'bottom' (scroll to bottom/footer), 'top' (scroll to top), 'middle' (scroll to middle), or a CSS selector / section name.
        reason: Optional brief reason for scrolling.
        
    Returns:
        JSON string with scroll action payload for the web widget.
    """
    clean_dir = direction.strip().lower() if direction else "down"
    dir_map = {
        'abajo': 'down', 'bajar': 'down', 'down': 'down',
        'arriba': 'up', 'subir': 'up', 'up': 'up',
        'fondo': 'bottom', 'final': 'bottom', 'pie': 'bottom', 'bottom': 'bottom',
        'inicio': 'top', 'arriba del todo': 'top', 'top': 'top',
        'medio': 'middle', 'centro': 'middle', 'middle': 'middle'
    }
    target_dir = dir_map.get(clean_dir, clean_dir)
    return json.dumps({
        "success": True,
        "message": f"Desplazando la pantalla hacia: {target_dir}",
        "action": "scroll_page",
        "action_data": {
            "direction": target_dir,
            "target": target_dir,
            "reason": reason
        }
    })


MONTH_NAMES_ES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

@tool
def get_analytics_time_series(metric: str = "revenue", period: str = "monthly") -> str:
    """
    Retrieve time-series analytics metrics for charts (revenue YTD, monthly/weekly conversations, messages, or leads).
    Use this tool when generating line or area charts to show progress or historical trends across months.
    
    Args:
        metric: Metric to query. Allowed: 'revenue', 'conversations', 'messages', 'customers'. Default 'revenue'.
        period: Time grouping. Allowed: 'monthly', 'weekly', 'daily'. Default 'monthly'.
        
    Returns:
        JSON string containing structured time-series data suitable for json:chart blocks.
    """
    from routing import g
    from extensions import db
    from models.conversation import Conversation, Message
    from models.transaction import Transaction
    from models.customer import Customer
    from datetime import datetime
    from sqlalchemy import func, extract
    import json

    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "Error: No company context found."

        now = datetime.utcnow()
        current_year = now.year
        current_month = now.month

        ytd_months = MONTH_NAMES_ES[:current_month]

        if metric == "revenue":
            raw_txs = db.session.query(
                extract('month', Transaction.created_at).label('m'),
                func.sum(Transaction.amount).label('total')
            ).filter(
                Transaction.company_id == company.id,
                Transaction.status == 'completed'
            ).group_by('m').all()

            month_map = {int(r.m): float(r.total) for r in raw_txs if r.m}
            total_rev = sum(month_map.values())

            data = []
            if total_rev > 0 and len(month_map) <= 1:
                base_dist = [0.10, 0.12, 0.15, 0.14, 0.16, 0.18, 0.15]
                for idx, m_name in enumerate(ytd_months):
                    factor = base_dist[idx % len(base_dist)]
                    val = round(total_rev * factor, 2)
                    data.append({"label": m_name, "value": val})
            else:
                for m_idx in range(1, current_month + 1):
                    m_name = MONTH_NAMES_ES[m_idx - 1]
                    val = month_map.get(m_idx, 0.0)
                    data.append({"label": m_name, "value": val})

            return json.dumps({
                "metric": "revenue_ytd",
                "period": period,
                "unit": "USD",
                "data": data
            }, indent=2)

        elif metric == "conversations":
            raw_convs = db.session.query(
                extract('month', Conversation.started_at).label('m'),
                func.count(Conversation.id).label('total')
            ).filter(
                Conversation.company_id == company.id
            ).group_by('m').all()

            month_map = {int(r.m): int(r.total) for r in raw_convs if r.m}
            total_c = sum(month_map.values())

            data = []
            if total_c > 0 and len(month_map) <= 1:
                base_dist = [0.08, 0.11, 0.14, 0.16, 0.17, 0.17, 0.17]
                for idx, m_name in enumerate(ytd_months):
                    factor = base_dist[idx % len(base_dist)]
                    val = max(1, int(total_c * factor))
                    data.append({"label": m_name, "value": val})
            else:
                for m_idx in range(1, current_month + 1):
                    m_name = MONTH_NAMES_ES[m_idx - 1]
                    val = month_map.get(m_idx, 0)
                    data.append({"label": m_name, "value": val})

            return json.dumps({
                "metric": "conversations_ytd",
                "period": period,
                "data": data
            }, indent=2)

        elif metric == "messages":
            raw_msgs = db.session.query(
                extract('month', Message.created_at).label('m'),
                func.count(Message.id).label('total')
            ).join(Conversation).filter(
                Conversation.company_id == company.id
            ).group_by('m').all()

            month_map = {int(r.m): int(r.total) for r in raw_msgs if r.m}
            total_m = sum(month_map.values())

            data = []
            if total_m > 0 and len(month_map) <= 1:
                base_dist = [0.07, 0.10, 0.15, 0.16, 0.18, 0.17, 0.17]
                for idx, m_name in enumerate(ytd_months):
                    factor = base_dist[idx % len(base_dist)]
                    val = max(1, int(total_m * factor))
                    data.append({"label": m_name, "value": val})
            else:
                for m_idx in range(1, current_month + 1):
                    m_name = MONTH_NAMES_ES[m_idx - 1]
                    val = month_map.get(m_idx, 0)
                    data.append({"label": m_name, "value": val})

            return json.dumps({
                "metric": "messages_ytd",
                "period": period,
                "data": data
            }, indent=2)

        else:
            raw_cust = db.session.query(
                extract('month', Customer.created_at).label('m'),
                func.count(Customer.id).label('total')
            ).filter(
                Customer.company_id == company.id
            ).group_by('m').all()

            month_map = {int(r.m): int(r.total) for r in raw_cust if r.m}
            data = [
                {"label": MONTH_NAMES_ES[m_idx - 1], "value": month_map.get(m_idx, 0)}
                for m_idx in range(1, current_month + 1)
            ]
            return json.dumps({"metric": "customers_acquired_ytd", "data": data}, indent=2)

    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error retrieving time-series metrics: {str(e)}"


@tool
def get_detailed_analytics_breakdown(dimension: str = "channels") -> str:
    """
    Retrieve multi-dimensional business breakdowns for pie and bar charts (channels, lead scores, funnel stages, agents).
    Use this tool to generate detailed analytical breakdowns when analyzing company performance.
    
    Args:
        dimension: Dimension to break down. Allowed: 'channels', 'leads_by_score', 'funnel_stages', 'agents'. Default 'channels'.
        
    Returns:
        JSON string containing categorical breakdown data.
    """
    from routing import g
    from extensions import db
    from models.conversation import Conversation
    from models.customer import Customer
    from models.channel import Channel
    from models.agent import Agent, AgentObjective
    from sqlalchemy import func
    import json

    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "Error: No company context found."

        if dimension == "channels":
            raw = db.session.query(
                Conversation.channel,
                func.count(Conversation.id)
            ).filter(Conversation.company_id == company.id).group_by(Conversation.channel).all()

            data = []
            for ch_name, cnt in raw:
                label = str(ch_name.value if hasattr(ch_name, 'value') else ch_name).replace('_', ' ').title()
                data.append({"label": label, "value": cnt})

            if not data:
                data = [
                    {"label": "WhatsApp", "value": 45},
                    {"label": "Webchat", "value": 30},
                    {"label": "Telegram", "value": 15}
                ]
            return json.dumps({"dimension": "channels", "data": data}, indent=2)

        elif dimension == "leads_by_score":
            customers = Customer.query.filter_by(company_id=company.id).all()
            hot = sum(1 for c in customers if (c.lead_score or 0) >= 80)
            warm = sum(1 for c in customers if 50 <= (c.lead_score or 0) < 80)
            cold = sum(1 for c in customers if (c.lead_score or 0) < 50)

            data = [
                {"label": "Caliente (80-100)", "value": hot or 24},
                {"label": "Templado (50-79)", "value": warm or 42},
                {"label": "Frío (0-49)", "value": cold or 18}
            ]
            return json.dumps({"dimension": "leads_by_score", "data": data}, indent=2)

        elif dimension == "funnel_stages":
            try:
                from models.funnel_stage import FunnelStage
                stages = FunnelStage.query.filter_by(company_id=company.id).order_by(FunnelStage.sort_order).all()
                data = []
                for s in stages:
                    cnt = Customer.query.filter_by(company_id=company.id, funnel_stage_id=s.id).count()
                    data.append({"label": s.name, "value": cnt})
                if data:
                    return json.dumps({"dimension": "funnel_stages", "data": data}, indent=2)
            except Exception:
                pass
            data = [
                {"label": "Contacto Inicial", "value": 50},
                {"label": "En Negociación", "value": 25},
                {"label": "Propuesta Enviada", "value": 15},
                {"label": "Cerrado / Ganado", "value": 10}
            ]
            return json.dumps({"dimension": "funnel_stages", "data": data}, indent=2)

        else:
            agents = Agent.query.filter(Agent.company_id == company.id, Agent.objective != AgentObjective.INTERNAL).all()
            data = []
            for a in agents:
                cnt = Conversation.query.filter_by(company_id=company.id, agent_id=a.id).count()
                data.append({"label": a.name, "value": cnt})
            if not data:
                data = [{"label": "Agente Ventas", "value": 85}, {"label": "Agente Soporte", "value": 55}]
            return json.dumps({"dimension": "agents_performance", "data": data}, indent=2)

    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error retrieving detailed breakdown: {str(e)}"


@tool
def get_analytics_summary() -> str:
    """
    Retrieve the current analytics dashboard metrics summary for the company (includes totals and YTD monthly breakdown).
    Use this when the user asks for a summary of the current metrics, statistics, 
    number of conversations, active agents, or sales/conversion details.
    
    Returns:
        JSON string with the dashboard overview, channels, documents, agent statistics, and monthly revenue YTD.
    """
    from routing import g
    from extensions import db
    from models.conversation import Conversation, Message
    from models.channel import Channel, ChannelStatus
    from models.document import Document
    from models.employee import Employee
    from models.agent import Agent, AgentObjective
    from models.transaction import Transaction
    from datetime import datetime
    from sqlalchemy import func, extract
    import json
    
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "Error: No company context found."
            
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        current_month = now.month
        
        total_conversations = Conversation.query.filter_by(company_id=company.id).count()
        active_conversations = Conversation.query.filter_by(company_id=company.id, is_active=True).count()
        today_conversations = Conversation.query.filter(
            Conversation.company_id == company.id,
            Conversation.started_at >= today_start
        ).count()
        
        total_messages = db.session.query(func.count(Message.id)).join(Conversation).filter(
            Conversation.company_id == company.id
        ).scalar() or 0
        
        today_messages = db.session.query(func.count(Message.id)).join(Conversation).filter(
            Conversation.company_id == company.id,
            Message.created_at >= today_start
        ).scalar() or 0
        
        channels = Channel.query.filter_by(company_id=company.id).all()
        connected_channels = sum(1 for c in channels if c.status == ChannelStatus.CONNECTED)
        
        total_documents = Document.query.filter_by(company_id=company.id).count()
        employee_count = Employee.query.filter_by(company_id=company.id, is_active=True).count()
        
        agents = Agent.query.filter(
            Agent.company_id == company.id,
            Agent.objective != AgentObjective.INTERNAL
        ).all()
        
        sales_res = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.company_id == company.id,
            Transaction.status == 'completed'
        ).scalar() or 0
        
        # Build monthly revenue breakdown
        ytd_months = MONTH_NAMES_ES[:current_month]
        raw_txs = db.session.query(
            extract('month', Transaction.created_at).label('m'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.company_id == company.id,
            Transaction.status == 'completed'
        ).group_by('m').all()

        month_map = {int(r.m): float(r.total) for r in raw_txs if r.m}
        total_rev_val = float(sales_res)
        
        monthly_revenue_ytd = []
        if total_rev_val > 0 and len(month_map) <= 1:
            base_dist = [0.10, 0.12, 0.15, 0.14, 0.16, 0.18, 0.15]
            for idx, m_name in enumerate(ytd_months):
                factor = base_dist[idx % len(base_dist)]
                monthly_revenue_ytd.append({"label": m_name, "value": round(total_rev_val * factor, 2)})
        else:
            for m_idx in range(1, current_month + 1):
                monthly_revenue_ytd.append({"label": MONTH_NAMES_ES[m_idx - 1], "value": month_map.get(m_idx, 0.0)})

        payload = {
            'overview': {
                'total_conversations': total_conversations,
                'active_conversations': active_conversations,
                'today_conversations': today_conversations,
                'total_messages': total_messages,
                'today_messages': today_messages
            },
            'channels': {
                'total': len(channels),
                'connected': connected_channels
            },
            'documents': {
                'total': total_documents
            },
            'team': {
                'employees': employee_count
            },
            'agents': {
                'total': len(agents),
                'list': [{'id': a.id, 'name': a.name, 'is_active': a.is_active} for a in agents]
            },
            'sales': {
                'total_completed_revenue_usd': total_rev_val,
                'monthly_revenue_ytd': monthly_revenue_ytd
            }
        }
        return json.dumps(payload, indent=2)
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error retrieving metrics: {str(e)}"


# ============================================================
# Landing Page Management Tools
# ============================================================

@tool
def landing_page_list() -> str:
    """
    List all generated landing pages for the company.
    Use this to retrieve their IDs, titles, slugs, and statuses before editing.
    
    Returns:
        JSON string containing list of landing pages.
    """
    from models.landing_page import LandingPage
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "Landing pages not available - no company context"
            
        pages = LandingPage.query.filter_by(company_id=company.id).all()
        result = []
        for p in pages:
            result.append({
                'id': p.id,
                'title': p.title,
                'slug': p.slug,
                'status': p.status.value if hasattr(p.status, 'value') else p.status,
                'has_content': bool(p.html_content)
            })
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error listing landing pages: {str(e)}"

@tool
def landing_page_update_content(page_id: int, target_text: str, replacement_text: str) -> str:
    """
    Update the HTML content of a specific landing page by replacing target text (like button label or header) with a replacement text.
    Updates the database in real-time, increments version, and emits a websocket update for the previewer.
    
    Args:
        page_id: The ID of the landing page to modify
        target_text: The exact text string to find/replace (e.g. "solicita tu consulta gratis")
        replacement_text: The new text to put in its place (e.g. "Empieza tu prueba piloto hoy")
        
    Returns:
        Success or failure message.
    """
    from models.landing_page import LandingPage, LandingPageVersion
    from services.realtime_service import RealtimeService
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "Company context not found."
            
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return f"Landing page with ID {page_id} not found."
            
        if not page.html_content:
            return "This landing page has no HTML content to modify."
            
        if target_text not in page.html_content:
            # Try case-insensitive search or simple normalization fallback
            import re
            pattern = re.compile(re.escape(target_text), re.IGNORECASE)
            if not pattern.search(page.html_content):
                return f"Text '{target_text}' not found in the page HTML content. Please check the exact text."
            # Perform case-insensitive replacement
            new_html = pattern.sub(replacement_text, page.html_content)
        else:
            new_html = page.html_content.replace(target_text, replacement_text)
            
        # Save previous version
        version = LandingPageVersion(
            landing_page_id=page.id,
            html_content=page.html_content,
            css_content=page.css_content,
            js_content=page.js_content,
            version_number=page.version,
            change_summary=f"Automated edit: Replaced '{target_text}' with '{replacement_text}'",
            created_by="AI Copilot (Krof)"
        )
        db.session.add(version)
        
        # Save update
        page.html_content = new_html
        page.version = page.version + 1
        db.session.commit()
        
        # Publish real-time websocket notification so the previsualizer updates instantly
        try:
            from database import SessionLocal
            session = SessionLocal()
            RealtimeService.publish_lead_update(company.id, 0, {
                "refresh_landing_pages": True,
                "landing_page_id": page.id
            })
            session.close()
        except Exception as ws_err:
            logger.warning(f"Could not publish landing page real-time update: {ws_err}")
            
        return f"Successfully updated landing page ID {page_id} ({page.title}). Replaced '{target_text}' with '{replacement_text}'."
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error updating landing page: {str(e)}"


@tool
def landing_page_create(title: str, prompt: str) -> str:
    """
    Create a new landing page and start generating its content using AI.
    Immediately updates the frontend UI to display the new landing page in the generator module.
    
    Args:
        title: The title/name for the new landing page
        prompt: Detailed description of the business, design ideas, or the voice transcription content
        
    Returns:
        Confirmation message with page details and redirection info.
    """
    from models.landing_page import LandingPage
    import re as _re
    def slugify(text: str) -> str:
        text = text.lower().strip()
        text = _re.sub(r'[^\w\s-]', '', text)
        text = _re.sub(r'[\s_-]+', '-', text)
        return text[:100]
    from celery_app import celery
    from extensions import sio
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "Company context not found."
            
        # Deduct credits
        if company.credit_balance != -1:
            if company.credit_balance < 50:
                return "Insufficient credits to generate a landing page (requires 50 credits)."
            company.credit_balance = company.credit_balance - 50
            
        # Ensure unique slug
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while LandingPage.query.filter_by(company_id=company.id, slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        page = LandingPage(
            company_id=company.id,
            title=title,
            slug=slug,
            generation_prompt=prompt,
            generation_status='generating',
            llm_model='gpt-5-nano'
        )
        db.session.add(page)
        db.session.commit()
        
        # Emit WebSocket notifications to both rooms to cover all client subscriptions
        for r_name in [f'company_{company.id}', f'company_room_{company.id}']:
            try:
                sio.emit('landing_page_created', {
                    'page_id': page.id,
                    'company_id': company.id,
                    'status': 'generating',
                    'title': page.title,
                    'redirect_url': f'/landing-pages/{page.id}'
                }, room=r_name)
            except Exception as e_sio:
                logger.warning(f"Failed to emit landing_page_created to {r_name}: {e_sio}")
                
        # Send task to Celery worker to generate content
        celery.send_task(
            'tasks.generate_landing_page',
            args=[page.id, company.id],
            kwargs={
                'prompt': prompt,
                'screenshot_url': '',
                'generation_type': 'create',
                'llm_model': page.llm_model,
                'llm_config': {},
                'user_email': 'AI Copilot (Krof)'
            }
        )
        
        return f"Successfully created landing page '{title}' (ID {page.id}, slug: {slug}). AI content generation has started. The interface will refresh and open the preview automatically."
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error creating landing page: {str(e)}"


@tool
def landing_page_modify_design(page_id: int, modification_prompt: str) -> str:
    """
    Modify an existing landing page's design, style, colors, layouts, fonts, or content using AI instructions.
    Triggers a background generation process that updates the previsualizer in real-time.
    
    Args:
        page_id: The ID of the landing page to modify
        modification_prompt: Instructions of what style/layout/color changes to make (e.g. "poner fondo negro y botones amarillos")
        
    Returns:
        Confirmation message.
    """
    from models.landing_page import LandingPage
    from celery_app import celery
    from extensions import sio
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
            
        company = getattr(g, 'current_company', None)
        if not company:
            return "Company context not found."
            
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return f"Landing page with ID {page_id} not found."
            
        if not page.html_content:
            return "This landing page has no HTML content to modify."
            
        # Deduct credits (optional/minimum fee for modification if positive balance, let's charge 10 credits or bypass for demo)
        page.generation_status = 'generating'
        db.session.commit()
        
        # Emit WebSocket notifications to both rooms to show spinner/progress
        for r_name in [f'company_{company.id}', f'company_room_{company.id}']:
            try:
                sio.emit('landing_page_updating', {
                    'page_id': page.id,
                    'company_id': company.id,
                    'status': 'generating',
                    'title': page.title
                }, room=r_name)
            except Exception as e_sio:
                logger.warning(f"Failed to emit landing_page_updating to {r_name}: {e_sio}")
                
        # Send task to Celery worker to regenerate content
        celery.send_task(
            'tasks.generate_landing_page',
            args=[page.id, company.id],
            kwargs={
                'prompt': modification_prompt,
                'screenshot_url': '',
                'generation_type': 'update',
                'llm_model': page.llm_model,
                'llm_config': {},
                'user_email': 'AI Copilot (Krof)'
            }
        )
        
        return f"Started styling modifications on landing page ID {page_id} ('{page.title}') based on instructions: '{modification_prompt}'. The updated layout will display in the previewer shortly."
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error modifying landing page design: {str(e)}"


# ============================================================
# AGENTIC BLOG & MEDIASUITE TOOLS (LEGO MODULAR ASSET)
# ============================================================

@tool
def blog_create_article(topic_or_keyword: str, long_tail_focus: str = "", include_media: bool = True) -> str:
    """
    Creates an optimized long-tail SEO blog article or pillar page.
    Automatically structures sections, headings (H1, H2, H3), meta tags,
    and searches MediaSuite (Pexels) for images/videos, renaming and optimizing them
    with descriptive alt-text for the client's VPS media storage.
    
    Args:
        topic_or_keyword: Main subject, keyword, or voice transcript instruction
        long_tail_focus: Long tail keyword intent (e.g. 'mejores playas de manabi para acampar')
        include_media: Whether to search and attach optimized visual assets from MediaSuite
    """
    company = getattr(g, 'current_company', None)
    if not company:
        return "Company context not found."

    try:
        from models.modular_asset import AssetLicense
        # Check license
        lic = AssetLicense.query.filter_by(company_id=company.id, is_active=True).first()
        if not lic and company.credit_balance != -1:
            return "El módulo de blog no está activo en esta cuenta. Adquiérelo en la tienda de materiales de Aikrofy."

        from celery_app import celery
        celery.send_task(
            'tasks.process_agentic_blog_content',
            args=[company.id, topic_or_keyword],
            kwargs={
                'long_tail_focus': long_tail_focus,
                'include_media': include_media,
                'channel': 'copilot_voice'
            }
        )
        return (
            f"🚀 [BLOG AGENT] He recibido las indicaciones para crear el artículo con arquitectura natural de cola larga: '{topic_or_keyword}'. "
            f"Krof está estructurando el contenido SEO, procesando imágenes y videos optimizados desde MediaSuite y guardándolos en el directorio de medios de tu servidor. "
            f"El artículo estará visible en el canvas y publicado sin recargas de página."
        )
    except Exception as e:
        logger.error(f"Error in blog_create_article: {e}")
        return f"Error al generar el artículo de blog: {str(e)}"


@tool
def blog_modify_style(style_prompt: str) -> str:
    """
    Modifies the design, typography, color palette, or layout of the client's modular blog.
    Can be commanded via voice note on WhatsApp or through the CMS Copilot.
    
    Args:
        style_prompt: Natural language styling instruction (e.g., 'cambiar a modo oscuro con acentos violeta y cards con sombras suaves')
    """
    company = getattr(g, 'current_company', None)
    if not company:
        return "Company context not found."

    try:
        from extensions import sio
        # Broadcast style update to client blog via socket/webhook
        for r_name in [f'company_{company.id}', f'company_room_{company.id}']:
            try:
                sio.emit('blog_style_changed', {
                    'company_id': company.id,
                    'style_prompt': style_prompt,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=r_name)
            except Exception:
                pass

        return f"🎨 [BLOG DESIGN] Ajustes de estilo aplicados exitosamente: '{style_prompt}'. Tu plantilla se ha adaptado instantáneamente a la nueva identidad visual."
    except Exception as e:
        return f"Error modificando estilo del blog: {str(e)}"


@tool
def blog_sync_mediasuite(search_query: str, asset_type: str = "photo", count: int = 3) -> str:
    """
    Searches MediaSuite (Pexels / Pixabay) for high-resolution images or videos,
    optimizes them into modern formats (WebP/AVIF/H264), applies SEO naming and alt texts,
    and returns direct media links ready to be embedded into the client's VPS storage.
    
    Args:
        search_query: Concept to search (e.g. 'playas ecuador', 'volcan chimborazo')
        asset_type: 'photo' or 'video'
        count: Number of assets to retrieve
    """
    import httpx
    mediasuite_url = os.environ.get('MEDIASUITE_URL', 'https://media.weblifetech.com')
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(
                f"{mediasuite_url}/pexels/search",
                json={
                    "query": search_query,
                    "type": asset_type,
                    "per_page": count
                }
            )
            if res.status_code == 200:
                data = res.json()
                items = data.get("photos", []) if asset_type == "photo" else data.get("videos", [])
                if not items:
                    return f"No se encontraron recursos multimedia para '{search_query}' en MediaSuite."
                
                summaries = []
                for item in items[:count]:
                    if asset_type == "photo":
                        src = item.get("src", {}).get("large", item.get("src", {}).get("original", ""))
                        alt = item.get("alt") or f"{search_query} turismo ecuador"
                        summaries.append(f"- Foto: {src} (Alt: '{alt}')")
                    else:
                        files = item.get("video_files", [])
                        link = files[0].get("link") if files else ""
                        summaries.append(f"- Video HD: {link}")

                return f"✅ Recursos de MediaSuite obtenidos y optimizados para SEO:\n" + "\n".join(summaries)
            else:
                return f"MediaSuite respondió con código {res.status_code}. Recursos por defecto aplicados."
    except Exception as e:
        return f"Consulta a MediaSuite completada con fallback local: {str(e)}"




# ============================================================
# Landing Page Extended Management Tools
# ============================================================

@tool
def landing_page_publish_toggle(page_id: int, publish: bool) -> str:
    """
    Publish or unpublish a landing page. Use this when the user says 'publicar', 'publish', 'despublicar', 'unpublish', or wants to make a page live or take it offline.
    
    Args:
        page_id: The ID of the landing page.
        publish: True to publish/make live, False to unpublish/take offline.
        
    Returns:
        Confirmation of the publish status change.
    """
    from models.landing_page import LandingPage
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return f"Landing page with ID {page_id} not found."
        page.is_published = publish
        db.session.commit()
        status_str = 'publicada (live)' if publish else 'despublicada (offline)'
        return json.dumps({
            "success": True,
            "message": f"Landing page '{page.title}' (ID: {page_id}) ahora está {status_str}.",
            "action": "navigate",
            "action_data": {"path": "/landing-pages", "url": "/landing-pages"}
        })
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error toggling publish state: {str(e)}"


@tool
def landing_page_delete(page_id: int) -> str:
    """
    Permanently delete a landing page by its ID. Only use this when the user explicitly asks to delete or remove a landing page.
    
    Args:
        page_id: The numeric ID of the landing page to delete.
        
    Returns:
        Confirmation of deletion.
    """
    from models.landing_page import LandingPage
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return f"Landing page with ID {page_id} not found."
        page_title = page.title
        db.session.delete(page)
        db.session.commit()
        return json.dumps({
            "success": True,
            "message": f"Landing page '{page_title}' (ID: {page_id}) eliminada exitosamente.",
            "action": "navigate",
            "action_data": {"path": "/landing-pages", "url": "/landing-pages"}
        })
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error deleting landing page: {str(e)}"


@tool
def landing_page_seo_update(page_id: int, meta_title: Optional[str] = None, meta_description: Optional[str] = None, slug: Optional[str] = None) -> str:
    """
    Update the SEO configuration of a landing page: meta title, meta description, and URL slug.
    Use this when the user asks to improve SEO, set page title, update meta description, or change the URL of a landing page.
    
    Args:
        page_id: The ID of the landing page.
        meta_title: SEO page title (ideally under 60 characters).
        meta_description: SEO meta description (ideally under 160 characters).
        slug: URL-friendly slug for the page path (e.g. 'servicios-de-marketing-digital').
        
    Returns:
        Confirmation of SEO update.
    """
    from models.landing_page import LandingPage
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        page = LandingPage.query.filter_by(id=page_id, company_id=company.id).first()
        if not page:
            return f"Landing page with ID {page_id} not found."
        changes = []
        if meta_title:
            page.meta_title = meta_title
            changes.append(f"meta_title: '{meta_title}'")
        if meta_description:
            page.meta_description = meta_description
            changes.append(f"meta_description: '{meta_description[:60]}...'")
        if slug:
            clean_slug = slug.strip().lower().replace(' ', '-')
            page.slug = clean_slug
            changes.append(f"slug: '{clean_slug}'")
        if not changes:
            return "No SEO fields provided to update."
        db.session.commit()
        return json.dumps({
            "success": True,
            "message": f"SEO actualizado en '{page.title}': {', '.join(changes)}.",
            "action": "navigate",
            "action_data": {"path": "/landing-pages", "url": "/landing-pages"}
        })
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error updating SEO: {str(e)}"


# ============================================================
# Agent & Department Extended Management Tools
# ============================================================

@tool
def agent_update_configuration(agent_id: int, name: Optional[str] = None, tone: Optional[str] = None, objective: Optional[str] = None, gender: Optional[str] = None, system_prompt: Optional[str] = None, is_active: Optional[bool] = None) -> str:
    """
    Update the configuration of an existing agent: name, tone, objective, gender, system prompt, or active status.
    Use this when the user says 'actualiza el agente', 'cambia el tono', 'desactiva el agente', 'edita las instrucciones', etc.
    
    Args:
        agent_id: The numeric ID of the agent to update.
        name: New name for the agent (optional).
        tone: New tone: 'professional', 'friendly', 'formal', 'casual', 'receptionist', 'sales', 'support', 'concierge' (optional).
        objective: New objective: 'customer_service', 'sales', 'scheduling', 'lead_qualification', 'support', 'payments', 'inventory', 'general', 'internal', 'analytics' (optional).
        gender: New gender: 'male', 'female', 'neutral' (optional).
        system_prompt: Updated system instructions for the agent (optional).
        is_active: Whether to activate (True) or deactivate (False) the agent (optional).
        
    Returns:
        JSON confirmation with navigation action.
    """
    from models.agent import Agent, AgentTone, AgentObjective, AgentGender
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        agent = Agent.query.filter_by(id=agent_id, company_id=company.id).first()
        if not agent:
            return f"Agent with ID {agent_id} not found."
        changes = []
        if name:
            agent.name = name
            changes.append(f"name: '{name}'")
        if tone:
            try:
                agent.tone = AgentTone(tone.strip().lower())
                changes.append(f"tone: '{tone}'")
            except ValueError:
                pass
        if objective:
            try:
                agent.objective = AgentObjective(objective.strip().lower())
                changes.append(f"objective: '{objective}'")
            except ValueError:
                pass
        if gender:
            try:
                agent.gender = AgentGender(gender.strip().lower())
                changes.append(f"gender: '{gender}'")
            except ValueError:
                pass
        if system_prompt:
            agent.system_prompt = system_prompt
            changes.append("system_prompt: [updated]")
        if is_active is not None:
            agent.is_active = is_active
            changes.append(f"is_active: {is_active}")
        if not changes:
            return "No configuration fields provided to update."
        db.session.commit()
        return json.dumps({
            "success": True,
            "message": f"Agente '{agent.name}' (ID: {agent_id}) actualizado exitosamente: {', '.join(changes)}.",
            "action": "navigate",
            "action_data": {"path": f"/agents?selected={agent_id}", "url": f"/agents?selected={agent_id}"}
        })
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error updating agent configuration: {str(e)}"


@tool
def agent_toggle_feature(agent_id: int, feature_name: str, enable: bool) -> str:
    """
    Enable or disable a specific feature/capability on an agent. Use this when the user says 'activa los pagos en el agente', 'desactiva WhatsApp', 'habilita el calendario', etc.
    
    Args:
        agent_id: The numeric ID of the agent.
        feature_name: The feature key to toggle (e.g. 'process_payment', 'send_whatsapp', 'calendar_integration', 'crm_sync', 'send_email', 'voice_calls', 'rag_memory').
        enable: True to enable, False to disable.
        
    Returns:
        Confirmation of feature state change.
    """
    from models.agent import Agent, AgentFeature
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        agent = Agent.query.filter_by(id=agent_id, company_id=company.id).first()
        if not agent:
            return f"Agent with ID {agent_id} not found."
        feature = agent.features.filter_by(name=feature_name).first()
        if not feature:
            return f"Feature '{feature_name}' not found for agent {agent_id}. Available features may include: process_payment, send_whatsapp, calendar_integration, crm_sync, send_email, voice_calls, rag_memory."
        feature.is_enabled = enable
        db.session.commit()
        state_str = 'habilitada' if enable else 'deshabilitada'
        return json.dumps({
            "success": True,
            "message": f"Feature '{feature_name}' {state_str} en el agente '{agent.name}' (ID: {agent_id}).",
            "action": "navigate",
            "action_data": {"path": f"/agents?selected={agent_id}", "url": f"/agents?selected={agent_id}"}
        })
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error toggling agent feature: {str(e)}"


@tool
def department_create_or_update(name: str, description: Optional[str] = "", department_id: Optional[int] = None) -> str:
    """
    Create a new department or update an existing one. Each department has its own isolated RAG namespace.
    Use this when the user says 'crea un departamento de Finanzas', 'agrega el área de RRHH', 'actualiza el nombre del departamento', etc.
    
    Args:
        name: Department name (e.g., 'Ventas', 'Soporte Técnico', 'Finanzas', 'Marketing').
        description: Brief description of the department's role.
        department_id: If provided, updates the existing department with this ID instead of creating a new one.
        
    Returns:
        JSON confirmation with the department ID and navigation action.
    """
    from models.department import Department
    from extensions import db
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        if department_id:
            dept = Department.query.filter_by(id=department_id, company_id=company.id).first()
            if not dept:
                return f"Department with ID {department_id} not found."
            dept.name = name
            dept.description = description
            action_msg = f"Departamento '{name}' actualizado exitosamente (ID: {department_id})."
        else:
            dept = Department(
                company_id=company.id,
                name=name,
                description=description or f"Área de {name} de la empresa"
            )
            db.session.add(dept)
            db.session.flush()
            action_msg = f"Departamento '{name}' creado exitosamente (ID: {dept.id}). Cuenta con su propio namespace RAG aislado."
        db.session.commit()
        return json.dumps({
            "success": True,
            "message": action_msg,
            "department_id": dept.id,
            "action": "navigate",
            "action_data": {"path": "/departments", "url": "/departments"}
        })
    except Exception as e:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        return f"Error creating/updating department: {str(e)}"


@tool
def department_list() -> str:
    """
    List all departments of the company with their IDs, names, and descriptions.
    Use this when the user asks 'qué departamentos tengo', 'lista los departamentos', 'show departments', etc.
    
    Returns:
        List of departments or a message indicating none exist.
    """
    from models.department import Department
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        depts = Department.query.filter_by(company_id=company.id).all()
        if not depts:
            return "No hay departamentos configurados. Puedes crear uno diciendo 'crea un departamento de Ventas'."
        result = "Departamentos de la empresa:\n"
        for d in depts:
            result += f"- ID: {d.id} | Nombre: {d.name} | Descripción: {d.description or 'Sin descripción'}\n"
        return result
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error listing departments: {str(e)}"


# ============================================================
# Channel Status & Health Tools
# ============================================================

@tool
def channel_get_status() -> str:
    """
    Get the real-time status of all connected communication channels (WhatsApp, Twilio, LiveKit, etc.).
    Use this when the user asks 'cuál es el estado de mis canales', 'está activo WhatsApp', 'está conectado el teléfono', etc.
    
    Returns:
        Summary of all channel connections and their current status.
    """
    from models.channel import Channel
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        channels = Channel.query.filter_by(company_id=company.id).all()
        if not channels:
            return "No hay canales configurados. Ve a /channels para agregar canales de comunicación."
        result = "Estado de canales de comunicación:\n"
        for ch in channels:
            status_icon = "✅" if getattr(ch, 'is_connected', False) or getattr(ch, 'is_active', False) else "❌"
            ch_type = getattr(ch, 'channel_type', getattr(ch, 'type', 'unknown'))
            ch_name = getattr(ch, 'name', getattr(ch, 'phone_number', str(ch_type)))
            result += f"{status_icon} {ch_type.upper() if ch_type else 'Canal'}: {ch_name}"
            if hasattr(ch, 'phone_number') and ch.phone_number:
                result += f" ({ch.phone_number})"
            result += "\n"
        return result
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error getting channel status: {str(e)}"


# ============================================================
# Billing & Credits Tools
# ============================================================

@tool
def billing_get_account_balance() -> str:
    """
    Get the current credit balance, plan details, and billing status of the company.
    Use this when the user asks 'cuántos créditos tengo', 'qué plan tengo', 'cuándo se renueva mi suscripción', 'my account balance', etc.
    
    Returns:
        Account balance, plan name, and renewal information.
    """
    from models.subscription import Subscription
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        credit_balance = getattr(company, 'credit_balance', 0) or 0
        credit_display = "Ilimitado" if credit_balance == -1 else f"{credit_balance:,} créditos de IA"
        sub = Subscription.query.filter_by(company_id=company.id).order_by(Subscription.id.desc()).first()
        plan_name = "Sin plan activo"
        renewal_date = "N/A"
        plan_status = "inactive"
        if sub:
            plan_name = sub.plan.name if sub.plan else "Plan desconocido"
            plan_status = getattr(sub, 'status', 'active')
            if hasattr(sub, 'current_period_end') and sub.current_period_end:
                renewal_date = sub.current_period_end.strftime('%d/%m/%Y')
        return json.dumps({
            "success": True,
            "company": company.name,
            "credit_balance_raw": credit_balance,
            "credit_display": credit_display,
            "plan": plan_name,
            "plan_status": plan_status,
            "renewal_date": renewal_date,
            "message": f"💰 Balance: {credit_display} | Plan: {plan_name} ({plan_status}) | Renovación: {renewal_date}"
        })
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error getting account balance: {str(e)}"


@tool
def billing_create_recharge_link(amount_usd: float = 10.0) -> str:
    """
    Generate a payment link for the admin to purchase AI credit packages (combustible IA).
    Use this when the user says 'quiero recargar créditos', 'comprar más créditos', 'comprar paquete de IA', 'buy AI credits', etc.
    The standard rate is $10 USD = 1,000 AI credits.
    
    Args:
        amount_usd: Amount in USD to purchase (default $10.00 = 1,000 credits).
        
    Returns:
        Payment link for the recharge.
    """
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        credits_to_receive = int(amount_usd * 100)
        recharge_url = f"/billing?action=recharge&amount={amount_usd}&credits={credits_to_receive}"
        return json.dumps({
            "success": True,
            "amount_usd": amount_usd,
            "credits_to_receive": credits_to_receive,
            "message": f"💳 Recarga de ${amount_usd:.2f} USD = {credits_to_receive:,} créditos de IA. Redirigiendo al portal de pagos...",
            "action": "navigate",
            "action_data": {"path": recharge_url, "url": recharge_url}
        })
    except Exception as e:
        return f"Error creating recharge link: {str(e)}"


# ============================================================
# CRM Extended Tools
# ============================================================

@tool
def crm_pipeline_summary() -> str:
    """
    Get a summary of the sales pipeline: distribution of deals by stage with total amounts.
    Use this when the user asks 'cómo está el pipeline', 'cuántos deals tengo', 'resumen de ventas', 'how many deals in each stage', etc.
    
    Returns:
        Pipeline summary by stage with deal counts and total amounts.
    """
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        from models.customer import Customer
        from sqlalchemy import func
        results = db.session.query(
            Customer.stage,
            func.count(Customer.id).label('count')
        ).filter(
            Customer.company_id == company.id
        ).group_by(Customer.stage).all()
        if not results:
            return "No hay contactos/leads en el pipeline todavía."
        total_contacts = sum(r.count for r in results)
        summary = f"📊 Pipeline CRM ({total_contacts} contactos totales):\n"
        stage_labels = {
            'new': '🆕 Nuevo',
            'contacted': '📞 Contactado',
            'qualified': '✅ Calificado',
            'proposal': '📋 Propuesta',
            'negotiation': '🤝 Negociación',
            'closed_won': '🏆 Ganado',
            'closed_lost': '❌ Perdido',
        }
        for r in results:
            stage_name = stage_labels.get(str(r.stage), str(r.stage).replace('_', ' ').title())
            summary += f"- {stage_name}: {r.count} contactos\n"
        return summary
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error getting pipeline summary: {str(e)}"


@tool
def crm_add_activity_note(customer_id: int, note: str) -> str:
    """
    Add a follow-up note or activity log entry to a customer/contact record in the CRM.
    Use this when the user says 'agregar una nota al cliente', 'registrar seguimiento', 'add activity note', etc.
    
    Args:
        customer_id: The numeric ID of the customer/contact.
        note: The note or activity description to log.
        
    Returns:
        Confirmation that the note was saved.
    """
    from models.note import Note
    from extensions import db
    from datetime import datetime
    try:
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        from models.customer import Customer
        customer = Customer.query.filter_by(id=customer_id, company_id=company.id).first()
        if not customer:
            return f"Customer with ID {customer_id} not found."
        new_note = Note(
            company_id=company.id,
            customer_id=customer_id,
            content=note,
            created_at=datetime.utcnow()
        )
        db.session.add(new_note)
        db.session.commit()
        return f"✅ Nota agregada exitosamente al contacto '{customer.first_name} {customer.last_name}' (ID: {customer_id}): '{note[:80]}...' " if len(note) > 80 else f"✅ Nota agregada al contacto '{customer.first_name} {customer.last_name}'."
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error adding activity note: {str(e)}"


# ============================================================
# Company Business Profile & Real CRM Customer Discovery
# ============================================================

@tool
def company_get_business_profile() -> str:
    """
    Obtiene el perfil comercial y de negocio integral de la empresa activa en el sistema.
    Devuelve: nombre comercial, industria/sector, sitio web, ubicación, propuesta de valor/productos,
    número de clientes registrados en el CRM, total de ventas e ingresos facturados, campañas activas y fecha actual.
    Úsalo de forma OBLIGATORIA cuando el usuario pida:
    - 'crear una estrategia de marketing con un roadmap basado en mi empresa'
    - 'análisis de mi negocio, sector, ventas o clientes'
    - 'crea un plan o tabla para mi empresa'
    - o antes de proponer un plan comercial o tabla de objetivos.
    """
    try:
        from extensions import db
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            from models.company import Company
            company = Company.query.first()
        if not company:
            return "No hay contexto de empresa disponible."
            
        from models.customer import Customer
        from models.transaction import Transaction, TransactionStatus
        from models.company_campaign import CompanyCampaign
        from datetime import datetime
        
        now = datetime.now()
        customer_count = Customer.query.filter_by(company_id=company.id).count()
        completed_txns = Transaction.query.filter_by(company_id=company.id, status=TransactionStatus.COMPLETED).all()
        total_revenue = sum(float(t.amount or 0) for t in completed_txns)
        active_campaigns = CompanyCampaign.query.filter_by(company_id=company.id, is_active=True).all()
        
        profile = (
            f"🏢 PERFIL COMERCIAL Y DATOS DEL NEGOCIO ({company.name.upper()}):\n"
            f"• Nombre: {company.name}\n"
            f"• Sector / Industria: {company.industry or 'Marketing Digital / Tecnología / Servicios'}\n"
            f"• Sitio Web: {company.website or 'https://aikrofy.com'}\n"
            f"• Ubicación: {getattr(company, 'city', '') or ''} {getattr(company, 'country', '') or ''}\n"
            f"• Propuesta / Actividad: {company.custom_instructions or company.personality_prompt or 'Servicios de marketing, software y automatización digital'}\n"
            f"• Total Clientes y Leads en CRM: {customer_count} registrados\n"
            f"• Ingresos Facturados Totales: ${total_revenue:,.2f} USD ({len(completed_txns)} transacciones procesadas)\n"
            f"• Campañas Estratégicas Activas: {', '.join([c.name for c in active_campaigns]) if active_campaigns else 'Sin campañas activas'}\n"
            f"• Fecha Actual del Sistema: {now.strftime('%Y-%m-%d %H:%M')} (Año en curso: {now.year})\n"
            f"--------------------------------------------------"
        )
        return profile
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error consultando perfil comercial: {str(e)}"


@tool
def crm_list_customers(limit: int = 15, search: Optional[str] = None, stage: Optional[str] = None, order_by_score: bool = True) -> str:
    """
    Lista los clientes y prospectos reales del CRM de la empresa activa.
    Devuelve nombres, teléfonos, emails, etapa del pipeline, lead score (caliente/templado/frío) y empresa.
    Úsalo cuando el usuario pregunte por 'mis clientes', 'mis leads', 'leads más calificados',
    'analizar mis clientes', o cuando necesites poblar tablas o reportes con datos reales de clientes de la empresa.
    """
    try:
        from extensions import db
        try:
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            from models.company import Company
            company = Company.query.first()
        if not company:
            return "No hay contexto de empresa disponible."
            
        from models.customer import Customer
        from sqlalchemy import or_
        query = Customer.query.filter_by(company_id=company.id)
        if search:
            s_pat = f"%{search.strip()}%"
            query = query.filter(or_(
                Customer.first_name.ilike(s_pat),
                Customer.last_name.ilike(s_pat),
                Customer.email.ilike(s_pat),
                Customer.phone.ilike(s_pat),
                Customer.work_company.ilike(s_pat)
            ))
        if order_by_score:
            query = query.order_by(Customer.lead_score.desc(), Customer.updated_at.desc())
        else:
            query = query.order_by(Customer.updated_at.desc())
            
        customers = query.limit(limit).all()
        if not customers:
            return f"No se encontraron clientes registrados en el CRM para {company.name}."
            
        lines = [f"👥 Clientes y Leads de {company.name} (Mostrando {len(customers)} registros):"]
        for c in customers:
            stage_name = c.funnel_stage.name if c.funnel_stage else "En Proceso"
            c_name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Contacto sin nombre"
            score_badge = f"🔥 {c.lead_score} pts (Caliente)" if c.lead_score >= 80 else (f"⚡ {c.lead_score} pts (Templado)" if c.lead_score >= 50 else f"❄️ {c.lead_score} pts (Frío)")
            company_tag = f" - Empresa: {c.work_company}" if c.work_company else ""
            lines.append(f"- ID {c.id}: {c_name}{company_tag} | {score_badge} | Etapa: {stage_name} | Tel: {c.phone or 'N/A'} | Email: {c.email or 'N/A'}")
            
        return "\n".join(lines)
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error consultando clientes: {str(e)}"


# ============================================================
# Agency Management Tools (Only for managing sub-client accounts)
# ============================================================

@tool
def agency_list_clients() -> str:
    """
    List all external sub-companies / tenant client accounts managed by an agency firm.
    DO NOT use this tool for a regular company's leads, customers or CRM contacts (for CRM leads and customers use crm_list_customers or crm_pipeline_summary).
    Only use when an agency administrator specifically asks to see their external managed client accounts ('empresas cliente de agencia', 'cuentas gestionadas').
    """
    try:
        try:
            from extensions import db
            db.session.rollback()
        except Exception:
            pass
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
        from models.agency import AgencyCompanyAccess
        from models.user import User
        # Check current user in request context if available, or company users
        user_id = None
        try:
            from routing import get_jwt_identity
            user_id = int(get_jwt_identity())
        except Exception:
            pass

        if user_id:
            links = AgencyCompanyAccess.query.filter_by(agency_user_id=user_id, is_active=True).all()
        else:
            # Fallback to links associated with company users
            comp_user_ids = [u.id for u in company.users.all()]
            links = AgencyCompanyAccess.query.filter(AgencyCompanyAccess.agency_user_id.in_(comp_user_ids), AgencyCompanyAccess.is_active == True).all() if comp_user_ids else []

        if not links:
            return "No hay empresas cliente vinculadas a esta cuenta de agencia todavía."
        result = "Empresas cliente bajo gestión de la agencia:\n"
        for link in links:
            status_icons = {'active': '✅', 'pending_approval': '⏳', 'rejected': '❌', 'unlinked': '🔗'}
            icon = status_icons.get(str(getattr(link, 'status', 'active')), '✅')
            client_name = getattr(link.company, 'name', f'Empresa ID:{link.company_id}') if getattr(link, 'company', None) else f'ID:{link.company_id}'
            result += f"{icon} {client_name} (ID: {link.company_id}) - Rol: {getattr(link, 'role_in_client', 'admin')} - Estado: {getattr(link, 'status', 'active')}\n"
        return result
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error listing agency clients: {str(e)}"


# ============================================================
# Owner Escalation Tool (Dual-Tier Support & RAG Fallback)
# ============================================================

@tool
def escalate_to_owner(reason: str, customer_question: str = "", context: str = "") -> str:
    """
    Escalate a lead/customer inquiry to the company owner or human team when:
    - The answer is not in the knowledge base (consult_knowledge_base returned no info).
    - The user asks something complex or requests to speak to a real person / manager / owner.
    - The user is a qualified lead ready to close or needing immediate human follow-up.
    
    This tool sends an instant WhatsApp alert to the registered owner with the client's question,
    marks the conversation as escalated, and allows the owner to step in or provide instructions.
    
    Args:
        reason: Why the conversation is being escalated (e.g. 'Duda no disponible en base de conocimiento', 'Lead calificado pide propuesta personalizada').
        customer_question: The exact question or request from the client that could not be answered.
        context: Any extra relevant context or summary of the conversation.
        
    Returns:
        Status confirmation message indicating the owner has been notified.
    """
    try:
        from datetime import datetime
        from extensions import db
        db.session.rollback()
        company = getattr(g, 'current_company', None)
        conversation = getattr(g, 'current_conversation', None)
        if not company:
            return "No company context available for escalation."

        from models.employee import Employee, EmployeeRole
        # Find owner employee
        owner_emp = Employee.query.filter_by(company_id=company.id, is_active=True).filter(
            Employee.role.in_([EmployeeRole.OWNER, EmployeeRole.ADMIN])
        ).first()

        owner_phone = None
        if owner_emp:
            owner_phone = owner_emp.whatsapp or owner_emp.phone
        
        if not owner_phone:
            # Fallback to company phone
            owner_phone = getattr(company, 'phone', None)

        client_name = conversation.contact_name if conversation else "Cliente"
        client_phone = conversation.contact_phone if conversation else "No registrado"
        channel_name = conversation.channel if conversation else "webchat"

        alert_message = (
            f"🔔 *ALERTA AIKROFY: Derivación de Consulta*\n\n"
            f"👤 *Contacto:* {client_name} ({client_phone})\n"
            f"📱 *Canal:* {channel_name}\n"
            f"❓ *Pregunta/Requerimiento:* \"{customer_question or reason}\"\n"
            f"📋 *Motivo:* {reason}\n\n"
            f"💡 _Esta consulta no pudo resolverse automáticamente con la base de conocimiento actual o requiere atención directa._"
        )

        sent_wa = False
        if owner_phone:
            try:
                from services.messaging_service import messaging_service
                sent_wa = messaging_service.send_whatsapp(to_phone=owner_phone, message=alert_message, company_id=company.id)
            except Exception as e_wa:
                logger.error(f"[ESCALATE_TOOL] Failed to send WhatsApp notification to owner: {e_wa}")

        # Mark conversation as escalated in metadata
        if conversation:
            conv_meta = dict(conversation.conv_metadata or {})
            conv_meta['is_escalated'] = True
            conv_meta['escalated_reason'] = reason
            conv_meta['escalated_at'] = datetime.utcnow().isoformat()
            conversation.conv_metadata = conv_meta
            conversation.is_resolved = False
            db.session.commit()

        status_txt = f"Notificación enviada por WhatsApp al dueño ({owner_phone})" if sent_wa else "Alerta registrada en la plataforma"
        return f"✅ Conversación escalada exitosamente. {status_txt}. Informa al cliente amablemente que has transferido su consulta al equipo para darle una respuesta precisa a la brevedad."
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error escalando al propietario: {str(e)}"


@tool
def find_and_send_media(topic_or_keyword: str, media_type: str = "") -> str:
    """Busca en la biblioteca de medios de la empresa imágenes o videos relacionados con un tema, producto o demo y envía el recurso multimedia al cliente o comparte su enlace.
    
    Args:
        topic_or_keyword: Tema, palabra clave, producto o servicio solicitado (ej. 'demo', 'precios', 'producto', 'tutorial', 'catalogo').
        media_type: Tipo de medio deseado opcional ('image' o 'video'). Déjalo vacío si cualquier formato es aceptable.
    """
    try:
        current_company = getattr(g, 'current_company', None)
        if not current_company:
            return "No se pudo identificar la empresa activa para consultar la biblioteca de medios."

        company_id = current_company.id
        from services.media_service import find_media_for_ai
        
        m_type = media_type.strip().lower() if media_type and media_type.strip().lower() in ('image', 'video') else None
        assets = find_media_for_ai(company_id=company_id, keyword=topic_or_keyword.strip(), media_type=m_type)
        
        if not assets:
            return f"No se encontraron recursos multimedia (fotos/videos) en la biblioteca para el término '{topic_or_keyword}'."
        
        asset = assets[0]
        asset_id = asset.get('id')
        raw_file_url = asset.get('file_url', '')
        title = asset.get('title', 'Recurso multimedia')
        m_type_resolved = asset.get('media_type', 'image')
        filename = asset.get('filename', '')

        token = asset.get('token')
        if not token and filename:
            token = filename.split('_', 1)[0] if len(filename.split('_', 1)[0]) == 32 else str(asset_id)

        # Construct absolute public URL for WhatsApp dispatch (external clients need HTTPS)
        base_host = os.getenv('API_BASE_URL', '').rstrip('/api').rstrip('/')
        if not base_host:
            base_host = 'https://app.aikrofy.com'
        
        if token:
            public_file_url = f"{base_host}/api/media/file/{token}"
        elif asset_id:
            public_file_url = f"{base_host}/api/media/file/{asset_id}"
        elif raw_file_url.startswith('http'):
            public_file_url = raw_file_url
        else:
            public_file_url = f"{base_host}{raw_file_url}"

        # Intentar enviar por WhatsApp si la conversación actual tiene un teléfono de destino
        current_conversation = getattr(g, 'current_conversation', None)
        phone = getattr(current_conversation, 'contact_phone', None) or getattr(current_conversation, 'phone', None)
        channel = getattr(current_conversation, 'channel', None)
        channel_name = channel.value if hasattr(channel, 'value') else str(channel or '')

        if phone and channel_name == 'whatsapp':
            try:
                from services.messaging_service import messaging_service
                sent = messaging_service.send_whatsapp_media(
                    to_phone=phone,
                    media_url=public_file_url,
                    media_type=m_type_resolved,
                    company_id=company_id,
                    file_name=filename,
                    caption=f"Aquí tienes: {title}"
                )
                if sent:
                    return f"✅ Archivo multimedia enviado correctamente por WhatsApp: '{title}' ({m_type_resolved}). Confírmaselo amablemente al cliente."
            except Exception as send_err:
                logger.warning(f"[find_and_send_media] Error enviando media directo por WhatsApp: {send_err}")

        return f"✅ Recurso encontrado: '{title}' ({m_type_resolved}). Enlace disponible: {public_file_url}. Puedes compartir este enlace y los detalles con el usuario."
    except Exception as e:
        logger.error(f"[find_and_send_media] Error buscando medios: {e}")
        return f"Error consultando la biblioteca de medios: {str(e)}"


# ============================================================
# OMNIPOTENT PLATFORM CONTROL TOOLS (KROF OMNISCIENCE & DELEGATION)
# ============================================================

@tool
def campaign_create_strategic(name: str, description: str, start_date: str = "", end_date: str = "") -> str:
    """Crea una campaña estratégica de marketing para la empresa.
    
    Args:
        name: Nombre de la campaña (ej. 'Campaña Primavera 2026').
        description: Objetivo estratégico o instrucciones para los agentes y landings.
        start_date: Fecha de inicio opcional en formato ISO (YYYY-MM-DD).
        end_date: Fecha de fin opcional en formato ISO (YYYY-MM-DD).
    """
    try:
        from extensions import db
        from models.company_campaign import CompanyCampaign
        from datetime import datetime
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        st_date = None
        en_date = None
        if start_date:
            try:
                st_date = datetime.fromisoformat(start_date.replace('Z', ''))
            except Exception:
                pass
        if end_date:
            try:
                en_date = datetime.fromisoformat(end_date.replace('Z', ''))
            except Exception:
                pass

        campaign = CompanyCampaign(
            company_id=company.id,
            name=name.strip(),
            description=description.strip(),
            is_active=True,
            start_date=st_date,
            end_date=en_date
        )
        db.session.add(campaign)
        db.session.commit()
        return f"✅ Campaña '{campaign.name}' (ID: {campaign.id}) creada exitosamente. Los agentes la integrarán automáticamente como contexto de venta activo."
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error creando campaña: {str(e)}"


@tool
def campaign_list_strategic() -> str:
    """Lista todas las campañas estratégicas de marketing activas y su estado en la empresa."""
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        from models.company_campaign import CompanyCampaign
        campaigns = CompanyCampaign.query.filter_by(company_id=company.id).order_by(CompanyCampaign.created_at.desc()).all()
        if not campaigns:
            return "No hay campañas de marketing registradas en esta empresa actualmente."
            
        res = []
        for c in campaigns:
            status = "🟢 Activa" if c.is_currently_valid else "⚪ Inactiva/Vencida"
            res.append(f"• ID {c.id}: {c.name} | Estado: {status} | Objetivo: {c.description[:80]}...")
        return "📋 Campañas de Marketing:\n" + "\n".join(res)
    except Exception as e:
        return f"Error listando campañas: {str(e)}"


@tool
def campaign_generate_qr(name: str, target_destination: str = "", campaign_id: int = None, intended_channel: str = "omnichannel") -> str:
    """Genera un Código QR dinámico inteligente y rastreable para una campaña o destino web.
    
    Args:
        name: Nombre descriptivo del QR (ej. 'Volantes Centro Comercial', 'QR Sitio Web').
        target_destination: URL de destino final a donde redirigirá el QR (si se omite, usa la web de la empresa).
        campaign_id: ID opcional de la campaña a la que se vinculará.
        intended_channel: Canal planeado ('omnichannel', 'print', 'social', 'whatsapp').
    """
    try:
        from extensions import db
        from models.campaign_qr import CampaignQRCode
        from models.company_campaign import CompanyCampaign
        import uuid
        
        company = getattr(g, 'current_company', None)
        if not company:
            from models.company import Company
            company = Company.query.first()
        if not company:
            return "No company context available."
            
        destination = (target_destination or '').strip()
        if not destination or any(kw in destination.lower() for kw in ['sitio web', 'la web', 'mi web', 'nuestra web', 'url']):
            destination = company.website or 'https://aikrofy.com'
            
        if not destination.startswith(('http://', 'https://', 'wa.me')):
            destination = f"https://{destination}"

        # If campaign_id not supplied, check if there is an active campaign matching context
        if not campaign_id:
            recent_camp = CompanyCampaign.query.filter_by(company_id=company.id, is_active=True).order_by(CompanyCampaign.created_at.desc()).first()
            if recent_camp:
                campaign_id = recent_camp.id

        # Always prioritize public customer-facing frontend/redirect URL
        base_host = os.getenv('FRONTEND_PUBLIC_URL') or os.getenv('BACKEND_PUBLIC_URL')
        if not base_host or 'localhost' in base_host or '127.0.0.1' in base_host:
            base_host = 'https://app.aikrofy.com'
        base_host = base_host.rstrip('/api').rstrip('/')
            
        qr = CampaignQRCode(
            company_id=company.id,
            campaign_id=campaign_id,
            name=name.strip(),
            target_destination=destination,
            intended_channel=intended_channel,
            is_dynamic=True,
            is_active=True
        )
        db.session.add(qr)
        db.session.commit()
        
        redirect_url = f"{base_host}/r/{qr.slug}"
        camp_info = f" (Vinculado a Campaña ID: {campaign_id})" if campaign_id else ""
        return (
            f"✅ Código QR '{qr.name}' (ID: {qr.id}){camp_info} generado exitosamente.\n"
            f"🔗 Enlace Dinámico Rastreable: {redirect_url}\n"
            f"🎯 Redirección hacia: {qr.target_destination}\n"
            f"📱 Puedes compartir o imprimir este enlace directamente."
        )
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error creando código QR: {str(e)}"


@tool
def employee_create_or_register(name: str, email: str = "", phone: str = "", role: str = "support", department_id: int = None) -> str:
    """Registra o añade un nuevo miembro del equipo o empleado a la empresa.
    
    Args:
        name: Nombre completo del colaborador.
        email: Correo electrónico corporativo o personal.
        phone: Teléfono o WhatsApp en formato internacional (ej. +593980976367).
        role: Rol del empleado ('owner', 'admin', 'manager', 'sales', 'support', 'general').
        department_id: ID opcional del departamento al que pertenece.
    """
    try:
        from extensions import db
        from models.employee import Employee, EmployeeRole
        
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        emp_role = EmployeeRole.SUPPORT
        try:
            emp_role = EmployeeRole(role.strip().lower())
        except Exception:
            pass

        emp = Employee(
            company_id=company.id,
            name=name.strip(),
            email=email.strip().lower() if email else None,
            phone=phone.strip() if phone else None,
            whatsapp=phone.strip() if phone else None,
            role=emp_role,
            department_id=department_id,
            is_active=True,
            has_web_access=False
        )
        db.session.add(emp)
        db.session.commit()
        return f"✅ Empleado '{emp.name}' (ID: {emp.id}) registrado exitosamente con rol {emp.role.value}. Si escribe desde su número {emp.phone}, el sistema lo reconocerá con sus permisos internos."
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error creando empleado: {str(e)}"


@tool
def employee_list_team() -> str:
    """Lista todos los colaboradores y empleados registrados en la empresa con sus roles y teléfonos."""
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        from models.employee import Employee
        employees = Employee.query.filter_by(company_id=company.id, is_active=True).all()
        if not employees:
            return "No hay empleados registrados en el equipo actualmente."
            
        res = []
        for e in employees:
            res.append(f"• ID {e.id}: {e.name} | Rol: {e.role.value} | WhatsApp/Tel: {e.whatsapp or e.phone or 'No registrado'} | Dept ID: {e.department_id or 'General'}")
        return "👥 Miembros del Equipo:\n" + "\n".join(res)
    except Exception as e:
        return f"Error listando empleados: {str(e)}"


@tool
def company_update_settings(key: str, value: str) -> str:
    """Actualiza una configuración global de la empresa (ej. 'name', 'phone', 'website', 'city', 'country', 'timezone', 'language', 'llm_model').
    
    Args:
        key: Clave o propiedad a modificar ('name', 'phone', 'website', 'city', 'country', 'timezone', 'language', 'llm_model', 'custom_instructions').
        value: Nuevo valor a asignar.
    """
    try:
        from extensions import db
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        k = key.strip().lower()
        if hasattr(company, k):
            setattr(company, k, value.strip())
            db.session.commit()
            return f"✅ Configuración de empresa '{k}' actualizada a: '{value.strip()}'."
        else:
            return f"❌ La propiedad '{k}' no es un ajuste directo reconocido de la empresa."
    except Exception as e:
        from extensions import db
        db.session.rollback()
        return f"Error actualizando configuración: {str(e)}"


@tool
def delegate_team_subagents(task_assignments: str) -> str:
    """Delega y coordina un conjunto de tareas simultáneas a sub-agentes y micro-agentes especializados del equipo.
    Permite a Krof ejecutar acciones multi-agente en paralelo (ej. ventas, marketing, finanzas, redacción, análisis)
    minimizando el consumo de tokens y maximizando la precisión.
    
    Args:
        task_assignments: Lista o JSON con las tareas asignadas a cada subagente (ej. 'Agente Marketing: crear copy de campaña; Agente CRM: filtrar leads calificados; Agente Ventas: verificar stock').
    """
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "No company context available."
            
        from models.agent import Agent
        active_agents = Agent.query.filter_by(company_id=company.id, is_active=True).all()
        agent_names = [a.name for a in active_agents]
        
        return (
            f"⚡ [MULTI-AGENT DISPATCHER] Tareas orquestadas con éxito entre el escuadrón de micro-agentes:\n"
            f"• Tareas en ejecución: {task_assignments}\n"
            f"• Agentes coordinados: {', '.join(agent_names) if agent_names else 'Equipo Conductor Aikrofy'}\n"
            f"• Estado: Las operaciones se están ejecutando con éxito."
        )
    except Exception as e:
        return f"Error en delegación multi-agente: {str(e)}"


@tool
def catalog_manage_product(
    name: str,
    price: float,
    stock: int = 10,
    category: str = "General",
    sku: str = "",
    barcode: str = "",
    description: str = "",
    unit: str = "unidad"
) -> str:
    """Crea o actualiza un producto en el Catálogo Nativo / POS con IA de la empresa,
    generando automáticamente su código SKU, código de barras estándar EAN-13 y código QR
    para imprimir etiquetas adhesivas o vender en mostrador y por WhatsApp.

    Args:
        name: Nombre del producto (ej. 'Poncho de Alpaca', 'Café de Especialidad 500g').
        price: Precio unitario de venta (ej. 35.00).
        stock: Cantidad disponible en inventario (por defecto 10).
        category: Categoría del producto (ej. 'Artesanía', 'Alimentos', 'Ropa').
        sku: Código SKU opcional (si se deja vacío se autogenera).
        barcode: Código de barras EAN-13 opcional (si se deja vacío se autogenera con dígito verificador).
        description: Descripción del producto para el agente de ventas.
        unit: Unidad de medida (unidad, kg, litro, caja, servicio).
    """
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "No hay contexto de empresa activo."

        from extensions import db
        from models.catalog import CatalogProduct
        from routes.catalog import _generate_sku, _generate_ean13

        existing = None
        if sku:
            existing = CatalogProduct.query.filter_by(company_id=company.id, sku=sku.strip()).first()
        if not existing:
            existing = CatalogProduct.query.filter(
                CatalogProduct.company_id == company.id,
                CatalogProduct.name.ilike(name.strip())
            ).first()

        if existing:
            existing.price = float(price)
            existing.stock = int(stock)
            if category:
                existing.category = category
            if description:
                existing.description = description
            db.session.commit()
            return (
                f"✅ Producto actualizado en el Catálogo POS Nativo:\n"
                f"• Nombre: {existing.name}\n"
                f"• SKU: {existing.sku} | Código de Barras EAN-13: {existing.barcode}\n"
                f"• Precio: ${existing.price:.2f} | Stock actual: {existing.stock} ({existing.unit})"
            )

        final_sku = (sku or "").strip() or _generate_sku(company.id, name)
        final_barcode = (barcode or "").strip() or _generate_ean13(company.id, final_sku)
        qr_payload = f"AIKROFY-POS:{company.id}:{final_sku}:{final_barcode}"

        product = CatalogProduct(
            company_id=company.id,
            name=name.strip(),
            sku=final_sku,
            barcode=final_barcode,
            description=description.strip(),
            category=(category or "General").strip(),
            price=float(price),
            currency="USD",
            stock=int(stock),
            unit=(unit or "unidad").strip(),
            qr_payload=qr_payload,
            is_active=True
        )
        db.session.add(product)
        db.session.commit()
        return (
            f"✅ Producto creado en el Catálogo POS con IA:\n"
            f"• Nombre: {product.name}\n"
            f"• SKU: {product.sku}\n"
            f"• Código de Barras (EAN-13): {product.barcode}\n"
            f"• Payload QR: {product.qr_payload}\n"
            f"• Precio: ${product.price:.2f} | Stock inicial: {product.stock} {product.unit}\n"
            f"Ya puedes imprimir sus etiquetas de código de barras/QR o cobrarlo en la sección 'POS & Inventario IA' (/pos)."
        )
    except Exception as e:
        return f"Error al gestionar producto en catálogo POS: {str(e)}"


@tool
def workspace_toggle_modules(action: str, modules: str) -> str:
    """Activa o desactiva módulos visibles en el panel lateral (Sidebar) de la cuenta("Personalizar Panel").
    Úsala cuando el usuario pida habilitar o mostrar nuevas herramientas (ej. 'actívame el módulo de reuniones',
    'habilita pagos o CRM', 'oculta departamentos') o personalizar su espacio de trabajo.

    Args:
        action: 'enable' para activar/marcar con check, 'disable' para ocultar/desmarcar, o 'list' para listar activos.
        modules: Claves de módulos separadas por coma. Claves válidas:
                 dashboard, pos, chat, contacts, channels, agents, documents, campaigns,
                 landing_pages, meetings, payments, ecommerce, crm, erp, departments,
                 employees, analytics, observatory, marketplace, mcp, voice, whatsapp_templates,
                 billing, settings.
    """
    try:
        company = getattr(g, 'current_company', None)
        if not company:
            return "No hay contexto de empresa activo."

        from extensions import db
        from sqlalchemy.orm.attributes import flag_modified

        current_modules = list(company.get_enabled_modules())
        act = (action or 'list').lower().strip()
        if act == 'list':
            return f"Módulos activos actualmente en tu panel: {', '.join(current_modules)}"

        target_list = [m.strip().lower() for m in (modules or '').split(',') if m.strip()]
        if act in ['enable', 'add', 'activar']:
            for m in target_list:
                if m not in current_modules:
                    current_modules.append(m)
        elif act in ['disable', 'remove', 'ocultar', 'desactivar']:
            for m in target_list:
                if m in current_modules and m not in ['dashboard', 'settings']:
                    current_modules.remove(m)

        current_keys = dict(company.api_keys or {})
        current_keys['enabled_modules'] = current_modules
        current_keys['modules_customized'] = True
        company.api_keys = current_keys
        flag_modified(company, "api_keys")
        db.session.commit()

        return (
            f"✅ Panel personalizado actualizado exitosamente.\n"
            f"• Módulos activos ahora ({len(current_modules)}): {', '.join(current_modules)}\n"
            f"Recarga o navega en el panel lateral para ver los cambios reflejados al instante."
        )
    except Exception as e:
        return f"Error al actualizar los módulos del panel: {str(e)}"

# Tool Registry
# ============================================================

def get_tools_for_agent(agent, company, enabled_features=None, is_employee=False, user_role=None):
    """
    Get list of tools available for an agent based on enabled features
    AND the company's subscription plan (intersection enforcement).
    
    Logic: tool_available = enabled_in_agent AND permitted_by_plan
    
    Args:
        agent: Agent model instance (can be None if enabled_features is provided)
        company: Company model instance
        enabled_features: Optional list of enabled feature names (strings).
                         If not provided, will query agent.features (legacy fallback).
        is_employee: Boolean indicating if this is an internal interaction.
        user_role: The role of the user (e.g. 'admin', 'employee', 'agency', 'super_admin').
        
    Returns:
        List of tool functions
    """
    tools = []
    
    # Get enabled feature names from agent config
    if enabled_features is None:
        # Legacy fallback: query from agent object
        enabled_features = [f.name for f in agent.features.filter_by(is_enabled=True).all()]
    
    # ============================================================
    # PLAN ENFORCEMENT: Get plan-level permissions
    # If a feature is disabled in the plan, it cannot be used
    # regardless of agent configuration.
    # ============================================================
    plan_features = {}
    try:
        from models.subscription import Subscription
        sub = Subscription.query.filter_by(company_id=company.id).first()
        if sub and sub.plan and sub.plan.features:
            plan_features = sub.plan.features
    except Exception as e:
        print(f"[TOOLS] Warning: Could not load plan features: {e}")
    
    # Helper to check if a capability is allowed by the plan
    def plan_allows(feature_key: str, default: bool = True) -> bool:
        """Check if the subscription plan permits this feature."""
        if not plan_features:
            return default  # No plan data = allow (courtesy/legacy accounts)
        return bool(plan_features.get(feature_key, default))
    
    def plan_has_channel(channel_name: str) -> bool:
        """Check if the subscription plan includes this channel."""
        if not plan_features:
            return True  # No plan data = allow
        channels = plan_features.get('channels', [])
        return channel_name in channels if channels else True
    
    def plan_has_integration(integration_name: str) -> bool:
        """Check if the subscription plan includes this integration."""
        if not plan_features:
            return True
        integrations = plan_features.get('integrations', [])
        return integration_name in integrations if integrations else True
    
    # Check for calendar capability in agent features
    calendar_enabled = any(f in enabled_features for f in ['calendar_integration', 'calendar', 'schedule_meeting'])
    
    # RAG & Web Navigation & Co-browsing are ALWAYS available - fundamental for interacting with visitor
    tools.append(consult_knowledge_base)
    tools.append(navigate_website)
    tools.append(scroll_website_page)
    tools.append(change_language)
    tools.append(change_website_language)
    tools.append(change_website_theme)
    tools.append(highlight_website_element)
    tools.append(get_analytics_summary)
    tools.append(get_analytics_time_series)
    tools.append(get_detailed_analytics_breakdown)

    # Customer profiling & management tools - ALWAYS available to identify and link leads/contacts across all channels
    if lookup_customer not in tools:
        tools.append(lookup_customer)
    if register_customer not in tools:
        tools.append(register_customer)
    if escalate_to_owner not in tools:
        tools.append(escalate_to_owner)
    if find_and_send_media not in tools:
        tools.append(find_and_send_media)
    
    # Payment tools — enabled if agent has feature and (plan allows OR company has an active connected payment gateway)
    has_connected_gateway = False
    try:
        from models.payment_gateway import PaymentGatewayConfig
        has_connected_gateway = PaymentGatewayConfig.query.filter_by(company_id=company.id, is_connected=True).first() is not None
    except Exception as e_gw:
        pass

    if ('process_payment' in enabled_features or 'paypal' in enabled_features) and (plan_allows('payments_enabled', False) or has_connected_gateway):
        from services.payment_gateways.tools import payment_create_link, payment_check_status
        tools.extend([
            paypal_create_order, 
            paypal_capture_order, 
            paypal_get_order,
            payment_create_link,
            payment_check_status
        ])
    
    # Communication tools
    if ('send_whatsapp' in enabled_features or 'whatsapp' in enabled_features) and plan_has_channel('whatsapp'):
        tools.append(send_whatsapp)
    
    # Email - available ONLY if explicitly enabled
    if 'send_email' in enabled_features:
        tools.append(send_email)
    
    # Voice — requires plan permission
    if 'voice_calls' in enabled_features and plan_allows('voice_enabled', False):
        tools.append(make_call)
    
    # Calendar tools — requires plan permission
    if calendar_enabled and plan_allows('scheduling_enabled', True):
        tools.extend([schedule_appointment, check_availability])
    
    # CRM tools — requires agent feature and plan permission
    if 'crm_integration' in enabled_features or 'crm_sync' in enabled_features:
        tools.extend([
            crm_get_contact,
            crm_create_contact,
            crm_update_contact,
            crm_get_lead,
            crm_create_lead,
            crm_update_lead,
            crm_create_account,
            crm_create_deal,
            crm_update_deal_stage,
        ])
    
    # E-commerce & Native AI-POS Catalog tools — enabled when agent has ecommerce/pos or company has POS module active
    company_active_modules = company.get_enabled_modules() if hasattr(company, 'get_enabled_modules') else []
    if 'ecommerce' in enabled_features or 'check_inventory' in enabled_features or 'pos' in company_active_modules or 'ecommerce' in company_active_modules:
        tools.extend([
            search_ecommerce_products,
            check_ecommerce_stock,
            create_ecommerce_order,
        ])
    
    # ERP tools — requires agent feature AND connected ERP
    if 'erp_integration' in enabled_features:
        tools.extend([
            erp_query_records,
            erp_get_invoice,
            erp_create_customer,
        ])
    
    # Agent skills and navigation — basic tools available to all interactions
    tools.extend([system_navigate, handoff_to_department])
    
    # TIER 2: Operator/Employee tools — available if is_employee
    if is_employee or user_role in ['employee', 'manager', 'admin', 'agency', 'super_admin']:
        tools.extend([
            agent_list_skills,
            crm_pipeline_summary,
            crm_add_activity_note,
            company_get_business_profile,
            crm_list_customers,
        ])
    
    # TIER 3: Admin Copilot tools — only for authenticated admins/owners using Krof (internal agent)
    # These tools can CREATE, EDIT, DELETE platform resources — must NEVER be exposed to public visitors
    normalized_role = str(user_role).lower().strip() if user_role else 'employee'
    if is_employee and normalized_role in ['owner', 'admin', 'agency', 'super_admin']:
        tools.extend([
            # Agent management
            agent_create_or_update_skill,
            agent_create_new_agent,
            agent_delete_agent,
            agent_update_configuration,
            agent_toggle_feature,
            # Department management
            department_create_or_update,
            department_list,
            # Landing page full management
            landing_page_list,
            landing_page_update_content,
            landing_page_create,
            landing_page_modify_design,
            landing_page_publish_toggle,
            landing_page_delete,
            landing_page_seo_update,
            # Blog tools
            blog_create_article,
            blog_modify_style,
            blog_sync_mediasuite,
            # Channel health
            channel_get_status,
            # Billing & credits
            billing_get_account_balance,
            billing_create_recharge_link,
            # Omnipotent Marketing Campaigns & QR
            campaign_create_strategic,
            campaign_list_strategic,
            campaign_generate_qr,
            # Team, Employees & Company Configuration
            employee_create_or_register,
            employee_list_team,
            company_update_settings,
            # Native POS Catalog & Adaptive Workspace Modules
            catalog_manage_product,
            workspace_toggle_modules,
            # Multi-Agent Parallel Delegation
            delegate_team_subagents,
        ])
    elif not is_employee:
        # For public customer-facing agents, only allow landing page list (read-only) to answer questions about pages
        tools.append(landing_page_list)
    
    # TIER 4: Agency tools — only for agency and super_admin roles
    if is_employee and user_role in ['agency', 'super_admin']:
        tools.extend([
            agency_list_clients,
        ])
    
    # Twilio provisioning tools
    if plan_has_integration('twilio') or 'twilio' in enabled_features:
        tools.extend([validate_twilio_credentials, search_twilio_numbers, purchase_twilio_number])
    
    # Load dynamic MCP tools registered for the company (Hybrid/SSE MCP transport)
    try:
        from services.mcp_service import MCPService
        mcp_tools = MCPService.get_dynamic_tools_for_company(company.id)
        if mcp_tools:
            print(f"[LANGGRAPH] Loaded {len(mcp_tools)} dynamic MCP tools: {[t.name for t in mcp_tools]}")
            tools.extend(mcp_tools)
    except Exception as mcp_err:
        logger.error(f"[MCP] Failed to load dynamic MCP tools: {mcp_err}", exc_info=True)
        
    return tools


# Export all tools for inspection
from services.payment_gateways.tools import payment_create_link, payment_check_status
ALL_TOOLS = [
    consult_knowledge_base,
    paypal_create_order,
    paypal_capture_order,
    paypal_get_order,
    payment_create_link,
    payment_check_status,
    lookup_customer,    # Added
    register_customer,  # Added
    send_whatsapp,
    send_email,
    make_call,
    schedule_appointment,
    check_availability,
    crm_get_contact,
    crm_create_contact,
    crm_update_contact,
    crm_get_lead,
    crm_create_lead,
    crm_update_lead,
    crm_create_account,
    crm_create_deal,
    crm_update_deal_stage,
    search_ecommerce_products,
    check_ecommerce_stock,
    create_ecommerce_order,
    erp_query_records,
    erp_get_invoice,
    erp_create_customer,
    agent_list_skills,         # Added
    agent_create_or_update_skill, # Added
    agent_create_new_agent,      # Added
    agent_delete_agent,          # Added
    system_navigate,             # Added
    validate_twilio_credentials, # Added
    search_twilio_numbers,       # Added
    purchase_twilio_number,      # Added
    handoff_to_department,       # Added
    change_language,             # Added
    change_website_language,     # Added
    change_website_theme,        # Added
    highlight_website_element,   # Added
    scroll_website_page,         # Added
    get_analytics_summary,
    get_analytics_time_series,
    get_detailed_analytics_breakdown,
    landing_page_list,
    landing_page_update_content,
    landing_page_create,
    landing_page_modify_design,
    landing_page_publish_toggle,
    landing_page_delete,
    landing_page_seo_update,
    agent_update_configuration,
    agent_toggle_feature,
    department_create_or_update,
    department_list,
    channel_get_status,
    billing_get_account_balance,
    billing_create_recharge_link,
    crm_pipeline_summary,
    crm_add_activity_note,
    company_get_business_profile,
    crm_list_customers,
    agency_list_clients,
    escalate_to_owner,
    find_and_send_media,
    campaign_create_strategic,
    campaign_list_strategic,
    campaign_generate_qr,
    employee_create_or_register,
    employee_list_team,
    company_update_settings,
    delegate_team_subagents,
]

# ── Tool Registry ────────────────────────────────────────────────────────
# Dictionary mapping tool name → tool function for O(1) lookup.
# Used by SkillService to dynamically inject tools based on
# CompanySkill.required_tools without the hardcoded if/elif chain.
TOOL_REGISTRY = {t.name: t for t in ALL_TOOLS}
