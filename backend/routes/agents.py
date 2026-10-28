from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Agent Configuration Routes
"""


from extensions import db
from models.user import User, UserRole
from models.agent import Agent, AgentFeature, AgentGender, AgentTone, AgentObjective, FeatureCategory, DEFAULT_FEATURES

agents_bp = APIRouter('agents', __name__)


def get_user_company():
    """Helper to get current user's company (supports Agency context)"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return None
        from decorators import get_current_company_context
        return get_current_company_context(user, request)
    except Exception as e:
        print(f"DEBUG: Agents - Error: {e}")
        return None


@agents_bp.route('/', methods=['GET'])
@jwt_required()
def list_agents():
    """List all agents for the company"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agents = Agent.query.filter(
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).all()
    return jsonify({'agents': [a.to_dict() for a in agents]})


@agents_bp.route('/', methods=['POST'])
@jwt_required()
def create_agent():
    """Create a new agent"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    # Unlimited agents across all plans per user request
    pass
    
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Agent name is required'}), 400
    
    try:
        agent = Agent(
            company_id=company.id,
            name=data['name'],
            description=data.get('description'),
            tone=AgentTone(data.get('tone', 'professional')),
            objective=AgentObjective(data.get('objective', 'general')),
            gender=AgentGender(data.get('gender', 'neutral')),
            system_prompt=data.get('system_prompt'),
            telephony_provider=data.get('telephony_provider'),
            is_active=data.get('is_active', True)
        )
        db.session.add(agent)
        db.session.flush()
        
        # Initialize default features
        for feature_data in DEFAULT_FEATURES:
            feature = AgentFeature(
                agent_id=agent.id,
                **feature_data
            )
            db.session.add(feature)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Agent created',
            'agent': agent.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@agents_bp.route('/<int:agent_id>', methods=['GET'])
@jwt_required()
def get_agent(agent_id):
    """Get agent details"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agent = Agent.query.filter(
        Agent.id == agent_id,
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    return jsonify({'agent': agent.to_dict()})


@agents_bp.route('/<int:agent_id>', methods=['PUT'])
@jwt_required()
def update_agent(agent_id):
    """Update agent settings"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agent = Agent.query.filter(
        Agent.id == agent_id,
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        agent.name = data['name']
    if 'description' in data:
        agent.description = data['description']
    if 'system_prompt' in data:
        agent.system_prompt = data['system_prompt']
    if 'telephony_provider' in data:
        agent.telephony_provider = data['telephony_provider']
    if 'is_active' in data:
        agent.is_active = data['is_active']
    if 'priority' in data:
        agent.priority = data['priority']
    
    try:
        if 'tone' in data:
            agent.tone = AgentTone(data['tone'])
        if 'objective' in data:
            agent.objective = AgentObjective(data['objective'])
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if 'campaign_id' in data:
        import re
        camp_id = data['campaign_id']
        current_prompt = agent.system_prompt or ''
        # Strip existing campaign marker
        cleaned_prompt = re.sub(r'\s*\[CAMPAIGN_ID:\d+\]', '', current_prompt).strip()
        if camp_id:
            agent.system_prompt = f"{cleaned_prompt}\n[CAMPAIGN_ID:{camp_id}]".strip()
        else:
            agent.system_prompt = cleaned_prompt
    
    db.session.commit()
    
    return jsonify({
        'message': 'Agent updated',
        'agent': agent.to_dict()
    })


@agents_bp.route('/<int:agent_id>', methods=['DELETE'])
@jwt_required()
def delete_agent(agent_id):
    """Delete an agent"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agent = Agent.query.filter(
        Agent.id == agent_id,
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    db.session.delete(agent)
    db.session.commit()
    
    return jsonify({'message': 'Agent deleted'})


@agents_bp.route('/<int:agent_id>/features', methods=['GET'])
@jwt_required()
def get_agent_features(agent_id):
    """Get all features for an agent"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agent = Agent.query.filter(
        Agent.id == agent_id,
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    # Backfill missing features (e.g. new channels added to system)
    existing_features = AgentFeature.query.filter_by(agent_id=agent.id).all()
    existing_names = {f.name for f in existing_features}
    modified = False
    
    for default_feat in DEFAULT_FEATURES:
        if default_feat['name'] not in existing_names:
            new_f = AgentFeature(
                agent_id=agent.id,
                **default_feat
            )
            db.session.add(new_f)
            modified = True
            
    if modified:
        db.session.commit()
    
    # Group features by category
    features_by_category = {}
    for category in FeatureCategory:
        features = AgentFeature.query.filter_by(
            agent_id=agent.id,
            category=category
        ).order_by(AgentFeature.order).all()
        features_by_category[category.value] = [f.to_dict() for f in features]
    
    return jsonify({
        'agent_id': agent_id,
        'features': features_by_category
    })


@agents_bp.route('/<int:agent_id>/features/<int:feature_id>', methods=['PUT'])
@jwt_required()
def toggle_feature(agent_id, feature_id):
    """Toggle a feature on/off (checkbox update)"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agent = Agent.query.filter(
        Agent.id == agent_id,
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    feature = AgentFeature.query.filter_by(id=feature_id, agent_id=agent.id).first()
    if not feature:
        return jsonify({'error': 'Feature not found'}), 404
    
    data = request.get_json()
    
    if 'is_enabled' in data:
        feature.is_enabled = data['is_enabled']
    
    if 'config' in data:
        feature.config = data['config']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Feature updated',
        'feature': feature.to_dict()
    })


@agents_bp.route('/<int:agent_id>/features/bulk', methods=['PUT'])
@jwt_required()
def bulk_update_features(agent_id):
    """Bulk update multiple features"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    agent = Agent.query.filter(
        Agent.id == agent_id,
        Agent.company_id == company.id,
        Agent.objective != AgentObjective.INTERNAL
    ).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    data = request.get_json()
    features_data = data.get('features', [])
    
    for feature_update in features_data:
        feature_id = feature_update.get('id')
        if not feature_id:
            continue
        
        feature = AgentFeature.query.filter_by(id=feature_id, agent_id=agent.id).first()
        if feature:
            if 'is_enabled' in feature_update:
                feature.is_enabled = feature_update['is_enabled']
            if 'config' in feature_update:
                feature.config = feature_update['config']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Features updated',
        'agent': agent.to_dict()
    })


@agents_bp.route('/tones', methods=['GET'])
@jwt_required()
def get_available_tones():
    """Get available agent tones"""
    return jsonify({
        'tones': [{'id': t.value, 'name': t.value.replace('_', ' ').title()} for t in AgentTone]
    })


@agents_bp.route('/objectives', methods=['GET'])
@jwt_required()
def get_available_objectives():
    """Get available agent objectives"""
    exclude_objectives = {AgentObjective.INTERNAL, AgentObjective.ANALYTICS}
    return jsonify({
        'objectives': [
            {'id': o.value, 'name': o.value.replace('_', ' ').title()}
            for o in AgentObjective
            if o not in exclude_objectives
        ]
    })


@agents_bp.route('/chat', methods=['POST'])
@jwt_required()
def agent_playground_chat():
    """
    Playground Chat Endpoint.
    Receives message history and processes the latest message using AgentService.
    """
    from datetime import datetime
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    data = request.get_json()
    messages_payload = data.get('messages', [])
    
    if not messages_payload:
        return jsonify({'error': 'No messages provided'}), 400
        
    # Get the latest user message
    latest_msg = messages_payload[-1]
    if latest_msg.get('role') != 'user':
        return jsonify({'error': 'Latest message must be from user'}), 400
        
    user_message = latest_msg.get('content', '').strip()
    if not user_message:
        return jsonify({'error': 'Message content cannot be empty'}), 400
        
    try:
        from models.conversation import Conversation, ConversationType
        
        # Find or create a transient conversation for the playground
        conversation = Conversation.query.filter_by(
            company_id=company.id,
            type=ConversationType.INTERNAL,
            channel='playground'
        ).first()
        
        if not conversation:
            conversation = Conversation(
                company_id=company.id,
                type=ConversationType.INTERNAL,
                channel='playground',
                contact_name="Playground User",
                contact_phone="playground_user"
            )
            db.session.add(conversation)
            db.session.flush()
            
        conversation.last_message_at = datetime.utcnow()
        db.session.commit()
        
        # Invoke Agent Service
        from services.agent_service import AgentService
        agent_service = AgentService(company)
        
        # We can pass the active agent
        from models.agent import Agent, AgentObjective
        agent_id = data.get('agent_id')
        if agent_id:
            agent = Agent.query.filter(
                Agent.id == agent_id,
                Agent.company_id == company.id,
                Agent.objective != AgentObjective.INTERNAL
            ).first()
        else:
            agent = Agent.query.filter(
                Agent.company_id == company.id,
                Agent.is_active == True,
                Agent.objective != AgentObjective.INTERNAL
            ).first()
        
        response_data = agent_service.process_message(
            conversation=conversation,
            user_message=user_message,
            agent=agent,
            channel='webchat'  # Use webchat channel behaviors for tools
        )
        
        assistant_response = response_data.get('content')
        
        if not assistant_response and response_data.get('tool_calls'):
            tool_names = [t.get('tool', 'unknown') for t in response_data['tool_calls']]
            assistant_response = f"I am performing the following actions: {', '.join(tool_names)}..."
            
        if not assistant_response:
            assistant_response = "I apologize, but I couldn't generate a verbal response."
            
        return jsonify({
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': assistant_response
                }
            }],
            'content': assistant_response,
            'tool_calls': response_data.get('tool_calls', [])
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

