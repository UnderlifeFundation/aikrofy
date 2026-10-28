from routing import APIRouter, jsonify, request
"""
Voice Agent Internal API
Used by local voice_agent.py process to fetch context from Flask app
"""
import os
from functools import wraps

from models.company import Company
from models.agent import Agent
from services.rag_service import RAGService
from extensions import db
from datetime import datetime

voice_agent_bp = APIRouter('voice_agent', __name__)


def require_internal_token(f):
    """
    Decorator to verify internal API requests.
    Checks X-Internal-Token header against INTERNAL_API_TOKEN env var.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        expected_token = os.getenv('INTERNAL_API_TOKEN')
        
        # If no token configured, allow request (development mode)
        if not expected_token:
            return f(*args, **kwargs)
        
        # Check header
        provided_token = request.headers.get('X-Internal-Token')
        if not provided_token or provided_token != expected_token:
            return jsonify({'error': 'Unauthorized - Invalid internal token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@voice_agent_bp.route('/api/internal/voice-context/<int:company_id>/<int:agent_id>', methods=['GET'])
@require_internal_token
def get_voice_context(company_id, agent_id):
    """
    Get full context for a voice agent session:
    - Agent configuration (prompt, gender, tone)
    - Enabled features/tools
    - Company API keys (for executing tools)
    - RAG context (optional, if query provided)
    """
    try:
        company = Company.query.get_or_404(company_id)
        agent = Agent.query.get_or_404(agent_id)
        
        # Ensure agent belongs to company
        if agent.company_id != company_id:
            return jsonify({'error': 'Agent does not belong to company'}), 403
            
        # Get enabled tools
        tools = [f.name for f in agent.get_enabled_features(category='tool')]
        
        # Get configured channels (like whatsapp)
        channels = [f.name for f in agent.get_enabled_features(category='channel')]
        
        # Base RAG Context (General company info)
        # We can pass a query param 'rag_query' if we want specific context
        rag_query = request.args.get('rag_query', 'company overview and services')
        rag_service = RAGService(company)
        rag_context = rag_service.get_context(rag_query, top_k=3)
        
        # Build response - filter sensitive keys
        # Only pass keys needed for tool execution, not all secrets
        safe_api_keys = {}
        if company.api_keys:
            # Only include telephony provider selection, not actual secrets
            safe_api_keys['telephony_provider'] = company.api_keys.get('telephony_provider', 'twilio')
        
        response = {
            'agent_name': agent.name,
            'gender': company.agent_gender.value if company.agent_gender else 'neutral',
            'tone': agent.tone.value,
            'instructions': agent.get_full_prompt(),
            'enabled_tools': tools,
            'enabled_channels': channels,
            'api_keys': safe_api_keys,  # Filtered keys only
            'rag_context': rag_context
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"ERROR fetching voice context: {e}")
        return jsonify({'error': str(e)}), 500

@voice_agent_bp.route('/api/internal/execute-tool', methods=['POST'])
@require_internal_token
def execute_tool_endpoint():
    """Execute a tool via AgentService"""
    try:
        data = request.json
        company_id = data.get('company_id')
        agent_id = data.get('agent_id')
        tool_name = data.get('tool_name')
        arguments = data.get('arguments')
        
        company = Company.query.get_or_404(company_id)
        agent = Agent.query.get_or_404(agent_id)
        
        from services.agent_service import AgentService
        agent_service = AgentService(company)
        
        print(f"DEBUG: Executing tool {tool_name} for agent {agent.name}")
        result = agent_service.execute_tool(tool_name, arguments, agent)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR executing tool: {e}")
        return jsonify({'error': str(e)}), 500
        
@voice_agent_bp.route('/api/internal/report-call', methods=['POST'])
@require_internal_token
def report_call_endpoint():
    """Receive call summary and post to admin chat"""
    try:
        data = request.json
        company_id = data.get('company_id')
        agent_id = data.get('agent_id')
        summary = data.get('summary')
        destination = data.get('destination')
        duration = data.get('duration', 'unknown')
        
        if not all([company_id, summary]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        company = Company.query.get_or_404(company_id)
        
        # Format the message for the admin chat
        report_message = (
            f"📞 **Reporte de Llamada Finalizada**\n"
            f"**Destino:** {destination}\n"
            f"**Duración:** {duration}s\n"
            f"**Resumen:**\n{summary}"
        )
        
        # Inject into Admin Chat (same logic as chat.py)
        from models.conversation import Conversation, ConversationType, MessageChannel, Message, MessageRole
        # We need to find the specific contact (Jonnathan or whoever initiated)
        # For outbound calls initiated from chat, we ideally should know the conversation_id.
        # But we can fallback to the general admin chat for the company.
        
        # Find active admin chat
        conversation = Conversation.query.filter_by(
            company_id=company.id,
            type=ConversationType.ADMIN,
            channel=MessageChannel.ADMIN_CHAT
        ).order_by(Conversation.last_message_at.desc()).first()
        
        if not conversation:
            # Create if not exists (fallback)
            conversation = Conversation(
                company_id=company.id,
                type=ConversationType.ADMIN,
                channel=MessageChannel.ADMIN_CHAT,
                contact_name="System Report",
                contact_email="system@internal"
            )
            db.session.add(conversation)
            db.session.flush()
            
        # Add Assistant Message (as if the agent is reporting back)
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=report_message,
            channel=MessageChannel.ADMIN_CHAT
        )
        db.session.add(message)
        conversation.last_message_at = datetime.utcnow()
        db.session.commit()
        
        from extensions import socketio
        room = f"chat_{conversation.id}"
        
        # Emit to specific room
        socketio.emit('new_message', {
            'conversation_id': conversation.id,
            'content': report_message,
            'role': 'assistant',
            'timestamp': datetime.utcnow().isoformat()
        }, room=room)
        
        # Also broadcast to all connected clients for admin chat updates
        socketio.emit('call_report', {
            'conversation_id': conversation.id,
            'content': report_message,
            'role': 'assistant',
            'destination': destination,
            'duration': duration,
            'timestamp': datetime.utcnow().isoformat()
        }, broadcast=True)
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"ERROR reporting call: {e}")
        return jsonify({'error': str(e)}), 500
