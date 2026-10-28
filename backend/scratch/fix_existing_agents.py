import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.agent import Agent, AgentFeature, AgentTone, AgentObjective, DEFAULT_FEATURES
from models.company_skill import CompanySkill

app = create_app()
with app.app_context():
    # Update CSO Sales
    sales_agent = Agent.query.filter_by(company_id=1, name='cso_sales').first()
    sales_skill = CompanySkill.query.filter_by(company_id=1, category='sales').first()
    if sales_agent and sales_skill:
        print("Updating sales agent with skill prompt...")
        sales_agent.system_prompt = sales_skill.system_prompt_block
        sales_agent.tone = AgentTone.SALES
        sales_agent.objective = AgentObjective.SALES
        
        # Enable features
        enabled_feats = ["whatsapp", "webchat", "rag_memory", "conversation_history", "process_payment", "paypal", "ecommerce"]
        existing_feats = {f.name: f for f in sales_agent.features.all()}
        for feat_data in DEFAULT_FEATURES:
            feat_name = feat_data['name']
            is_enabled = feat_name in enabled_feats
            if feat_name in existing_feats:
                existing_feats[feat_name].is_enabled = is_enabled
            else:
                db.session.add(AgentFeature(
                    agent_id=sales_agent.id, 
                    name=feat_name, 
                    category=feat_data['category'], 
                    label=feat_data['label'], 
                    description=feat_data['description'], 
                    is_enabled=is_enabled, 
                    order=feat_data['order']
                ))
                
    # Update COO Operations
    coo_agent = Agent.query.filter_by(company_id=1, name='coo_operations').first()
    support_skill = CompanySkill.query.filter_by(company_id=1, category='support').first()
    if coo_agent and support_skill:
        print("Updating operations agent with skill prompt...")
        coo_agent.system_prompt = support_skill.system_prompt_block
        coo_agent.tone = AgentTone.SUPPORT
        coo_agent.objective = AgentObjective.SUPPORT
        
        # Enable features
        enabled_feats = ["whatsapp", "webchat", "rag_memory", "conversation_history", "calendar", "schedule_meeting", "check_inventory", "crm_sync"]
        existing_feats = {f.name: f for f in coo_agent.features.all()}
        for feat_data in DEFAULT_FEATURES:
            feat_name = feat_data['name']
            is_enabled = feat_name in enabled_feats
            if feat_name in existing_feats:
                existing_feats[feat_name].is_enabled = is_enabled
            else:
                db.session.add(AgentFeature(
                    agent_id=coo_agent.id, 
                    name=feat_name, 
                    category=feat_data['category'], 
                    label=feat_data['label'], 
                    description=feat_data['description'], 
                    is_enabled=is_enabled, 
                    order=feat_data['order']
                ))
                
    db.session.commit()
    print("Agent updates committed successfully.")
