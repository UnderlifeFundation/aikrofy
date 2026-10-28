from routing import APIRouter, jsonify, request, jwt_required, get_jwt_identity
from models.user import User
from services.livekit_service import LiveKitService
import os

livekit_bp = APIRouter('livekit', __name__, url_prefix='/api/livekit')

@livekit_bp.route('/token', methods=['GET'])
@jwt_required()
def get_token():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    company = user.company
    livekit_service = LiveKitService(company)
    
    # Room name: for simplicity, we can use a fixed room or dynamic per user
    # Ideally, detailed logic for rooms. here: "call-{user_id}"
    room_name = f"call-user-{user.id}"
    
    # Identity: user email or name
    participant_identity = f"user-{user.id}"
    
    try:
        token = livekit_service.create_token(
            room_name=room_name, 
            identity=participant_identity
        )
        return jsonify({
            'token': token,
            'url': livekit_service._get_credential('livekit_url'),
            'room': room_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
