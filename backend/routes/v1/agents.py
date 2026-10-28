"""
V1 Public API - Agents Router
Provides external/developer access to Aikrofy executive agents via API key auth.
"""
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/v1/agents', tags=['V1 - Agents'])

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class AgentInvokeRequest(BaseModel):
    prompt: str
    agent_role: str = 'ceo'


# ── Plan-gated agent catalogue ────────────────────────────────────────────────

AGENT_CATALOGUE = [
    {'role': 'ceo', 'name': 'CEO Orchestrator',   'file': 'ceo_orchestrator.md',  'plan': 'pyme'},
    {'role': 'coo', 'name': 'COO Operations',     'file': 'coo_operations.md',    'plan': 'pyme'},
    {'role': 'cso', 'name': 'CSO Sales',          'file': 'cso_sales.md',         'plan': 'pyme'},
    {'role': 'cmo', 'name': 'CMO Marketing',      'file': 'cmo_marketing.md',     'plan': 'enterprise'},
    {'role': 'cto', 'name': 'CTO Technology',     'file': 'cto_technology.md',    'plan': 'enterprise'},
    {'role': 'cro', 'name': 'CRO Revenue',        'file': 'cro_revenue.md',       'plan': 'enterprise'},
    {'role': 'cfo', 'name': 'CFO Finance',        'file': 'cfo_finance.md',       'plan': 'enterprise'},
]

ENTERPRISE_ONLY_ROLES = {'cmo', 'cto', 'cro', 'cfo'}


# ── Auth Dependency ───────────────────────────────────────────────────────────

def get_company_from_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Validate X-API-Key header and return the associated Company."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail='Missing X-API-Key header.')

    from database import db_session
    from models.company import Company

    # Look up company whose api_keys JSON contains the provided public_api_key
    companies = db_session.query(Company).filter(Company.api_keys.isnot(None)).all()
    for company in companies:
        if company.api_keys and company.api_keys.get('public_api_key') == x_api_key:
            return company

    raise HTTPException(status_code=401, detail='Invalid API key.')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_agent_prompt(filename: str) -> str:
    """Load agent system prompt from the agents/ directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    agent_path = os.path.join(base_dir, 'agents', filename)
    try:
        with open(agent_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f'Agent definition not found: {filename}')


def _find_agent_entry(role: str) -> dict:
    """Return catalogue entry for the given role or raise 404."""
    for entry in AGENT_CATALOGUE:
        if entry['role'] == role:
            return entry
    raise HTTPException(status_code=404, detail=f'Unknown agent role: {role}')


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post('/invoke')
def invoke_agent(
    body: AgentInvokeRequest,
    company=None,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Invoke an Aikrofy executive agent with a natural-language prompt.

    - **prompt**: The user's input/question.
    - **agent_role**: One of ceo, coo, cso, cmo, cto, cro, cfo.

    Enterprise-only roles (cfo, cro) require plan_type == 'enterprise'.
    """
    company = get_company_from_api_key(x_api_key)
    role = body.agent_role.lower()

    # Feature-flag gate: enterprise-only roles
    if role in ENTERPRISE_ONLY_ROLES:
        plan = (company.plan_type or 'pyme').lower()
        if plan != 'enterprise':
            raise HTTPException(
                status_code=403,
                detail=f"Agent '{role}' requires an enterprise plan. Current plan: {plan}."
            )

    agent_entry = _find_agent_entry(role)
    system_prompt = _load_agent_prompt(agent_entry['file'])

    # Call LLM
    try:
        from langchain_openai import ChatOpenAI

        openai_api_key = (company.api_keys or {}).get('openai') or os.getenv('OPENAI_API_KEY')
        llm = ChatOpenAI(model='gpt-5-nano', openai_api_key=openai_api_key)
        response = llm.invoke([
            {'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': body.prompt},
        ])
        answer = response.content
    except Exception as e:
        logger.error(f'LLM invocation error for agent {role}: {e}')
        raise HTTPException(status_code=500, detail=f'LLM error: {str(e)}')

    return {
        'agent_role': role,
        'agent_name': agent_entry['name'],
        'response': answer,
    }


@router.get('/list')
def list_agents(x_api_key: Optional[str] = Header(default=None)):
    """
    List available agents filtered by the company's plan_type.

    - **pyme**: ceo, coo, cso
    - **enterprise**: all 7 agents
    """
    company = get_company_from_api_key(x_api_key)
    plan = (company.plan_type or 'pyme').lower()

    if plan == 'enterprise':
        available = AGENT_CATALOGUE
    else:
        available = [a for a in AGENT_CATALOGUE if a['plan'] == 'pyme']

    return {
        'plan_type': plan,
        'agents': [{'role': a['role'], 'name': a['name']} for a in available],
    }


@router.get('/skills')
def list_skills(x_api_key: Optional[str] = Header(default=None)):
    """Return active skills for the authenticated company."""
    company = get_company_from_api_key(x_api_key)

    try:
        from services.skill_service import SkillService
        skills = SkillService.load_active_skills(company.id)
        skills_list = [
            {
                'id': s.id,
                'name': s.name,
                'label': s.label,
                'category': s.category.value if hasattr(s.category, 'value') else s.category,
                'is_enabled': s.is_enabled,
            }
            for s in skills
        ]
    except Exception as e:
        logger.error(f'Error loading skills for company {company.id}: {e}')
        raise HTTPException(status_code=500, detail=f'Could not load skills: {str(e)}')

    return {'company_id': company.id, 'skills': skills_list}
