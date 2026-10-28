from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
"""
Company Management Routes
"""


from extensions import db
from models.user import User, UserRole
from models.company import Company, AgentGender

companies_bp = APIRouter('companies', __name__)


def get_user_company():
    """Helper to get current user's company"""
    user_id = get_jwt_identity()
    print(f"DEBUG: get_user_company() - JWT Identity: {user_id}")
    try:
        uid = int(user_id)
        user = User.query.get(uid)
        print(f"DEBUG: User query result: {user}")
        if not user:
            print(f"DEBUG: User {uid} not found in DB")
            return None, None
        
        print(f"DEBUG: User found: {user.email}, Company: {user.company}")
        if user:
            from decorators import get_current_company_context
            active_comp = get_current_company_context(user, request)
            if active_comp:
                return user, active_comp
            
        return user, user.company if user else None
    except Exception as e:
        print(f"DEBUG: Error in get_user_company: {e}")
        return None, None


@companies_bp.route('/', methods=['GET'])
@jwt_required()
def get_company():
    """Get current user's company"""
    user, company = get_user_company()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    return jsonify({'company': company.to_dict()})


@companies_bp.route('/', methods=['PUT'])
@companies_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_company():
    """Update company details"""
    print("DEBUG: update_company() called!")
    user, company = get_user_company()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json() or {}
    print(f"DEBUG: Received data: {data}")
    
    # Update basic info
    if 'name' in data and data['name']:
        company.name = data['name'].strip()
    if 'industry' in data:
        company.industry = data['industry'][:100] if data.get('industry') else None
    if 'country' in data:
        company.country = data['country']
    if 'city' in data:
        company.city = data['city']
    if 'timezone' in data:
        company.timezone = data['timezone']
    if 'language' in data:
        company.language = data['language']
    if 'email' in data:
        company.email = data['email']
    if 'phone' in data:
        company.phone = data['phone']
    if 'website' in data:
        company.website = data['website']
    if 'initial_setup_completed' in data:
        company.initial_setup_completed = bool(data['initial_setup_completed'])
    else:
        # If updating company name from setup and it's not a placeholder, mark setup completed
        is_placeholder = not company.name or company.name.lower().strip() in ['', 'mi empresa', 'my company', 'nueva empresa', 'company']
        if not is_placeholder:
            company.initial_setup_completed = True

    # Save business goals and products/services to company custom_instructions or personality_prompt
    if data.get('products_services') or data.get('business_goals'):
        extra_ctx = []
        if data.get('products_services'):
            extra_ctx.append(f"Productos/Servicios: {data['products_services']}")
        if data.get('business_goals'):
            extra_ctx.append(f"Metas de negocio: {data['business_goals']}")
        added_text = "\n".join(extra_ctx)
        if company.custom_instructions:
            if added_text not in company.custom_instructions:
                company.custom_instructions = f"{company.custom_instructions}\n\n{added_text}"
        else:
            company.custom_instructions = added_text

    # Recompute smart default modules during onboarding if not explicitly customized yet
    current_keys = dict(company.api_keys or {})
    if 'enabled_modules' in data and isinstance(data['enabled_modules'], list):
        current_keys['enabled_modules'] = [str(m) for m in data['enabled_modules'] if m]
        current_keys['modules_customized'] = True
        company.api_keys = current_keys
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(company, "api_keys")
    elif not current_keys.get('modules_customized'):
        current_keys['enabled_modules'] = Company.compute_default_modules(
            business_category=company.business_category or 'emprendimiento',
            industry=company.industry or '',
            extra_context=f"{company.personality_prompt or ''} {company.custom_instructions or ''}",
            plan_type=company.plan_type or 'pyme'
        )
        company.api_keys = current_keys
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(company, "api_keys")
    
    db.session.commit()
    
    return jsonify({
        'message': 'Company updated',
        'company': company.to_dict()
    })


@companies_bp.route('/agent-settings', methods=['PUT'])
@jwt_required()
def update_agent_settings():
    """Update agent personalization settings"""
    user, company = get_user_company()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json()
    
    if 'agent_name' in data:
        company.agent_name = data['agent_name']
    
    if 'agent_gender' in data:
        try:
            company.agent_gender = AgentGender(data['agent_gender'])
        except ValueError:
            return jsonify({'error': 'Invalid agent gender'}), 400
    
    if 'personality_prompt' in data:
        company.personality_prompt = data['personality_prompt']
    
    if 'custom_instructions' in data:
        company.custom_instructions = data['custom_instructions']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Agent settings updated',
        'company': company.to_dict()
    })


@companies_bp.route('/llm-config', methods=['GET'])
@jwt_required()
def get_llm_config():
    """Get LLM configuration"""
    user, company = get_user_company()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    return jsonify({
        'llm_provider': company.llm_provider,
        'llm_model': company.llm_model,
        'llm_routing_mode': getattr(company, 'llm_routing_mode', 'core_pool') or 'core_pool',
        'voice_provider': company.voice_provider,
        'voice_model': company.voice_model,
        'api_keys': {
            # LLM Keys (return actual values for display)
            'openai': company.api_keys.get('openai'),
            'anthropic': company.api_keys.get('anthropic'),
            'google': company.api_keys.get('google'),
            'groq': company.api_keys.get('groq'),
            'deepseek': company.api_keys.get('deepseek'),
            'openrouter': company.api_keys.get('openrouter'),
            'elevenlabs': company.api_keys.get('elevenlabs'),
            
            # Telephony Provider
            'telephony_provider': company.api_keys.get('telephony_provider'),
            
            # Twilio (All values)
            'twilio_sid': company.api_keys.get('twilio_sid'),
            'twilio_token': company.api_keys.get('twilio_token'),
            'twilio_whatsapp_number': company.api_keys.get('twilio_whatsapp_number'),
            'twilio_voice_number': company.api_keys.get('twilio_voice_number'),
            'twilio_phone': company.api_keys.get('twilio_phone'), # Legacy
            
            # LiveKit (All values)
            'livekit_url': company.api_keys.get('livekit_url'),
            'livekit_api_key': company.api_keys.get('livekit_api_key'),
            'livekit_api_secret': company.api_keys.get('livekit_api_secret'),
            'livekit_caller_id': company.api_keys.get('livekit_caller_id'),
            
            # PayPal (All values)
            'paypal_id': company.api_keys.get('paypal_id'),
            'paypal_secret': company.api_keys.get('paypal_secret'), # Frontend should mask this if needed, or we mask here
            'paypal_mode': company.api_keys.get('paypal_mode'),
            
            # Google Service Account (Full JSON for editing)
            'google_service_account': company.api_keys.get('google_service_account'),
            'google_service_account_configured': bool(company.api_keys.get('google_service_account')),
            
            # Google OAuth (New)
            'google_oauth_credentials': bool(company.api_keys.get('google_oauth_credentials')),
            'google_calendar_id': company.api_keys.get('google_calendar_id'),
            'google_sheet_id': company.api_keys.get('google_sheet_id'),
            
            # HubSpot (New)
            'hubspot_access_token': bool(company.api_keys.get('hubspot_access_token')),
            'hubspot_portal_id': company.api_keys.get('hubspot_portal_id')
        }
    })


@companies_bp.route('/llm-config', methods=['PUT'])
@jwt_required()
def update_llm_config():
    """Update LLM configuration and API keys"""
    user, company = get_user_company()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json()
    
    if 'llm_provider' in data:
        company.llm_provider = data['llm_provider']
    
    if 'llm_model' in data:
        company.llm_model = data['llm_model']
    
    if 'llm_routing_mode' in data:
        mode = str(data['llm_routing_mode']).lower().strip()
        if mode in ['core_pool', 'byok']:
            company.llm_routing_mode = mode
    
    if 'voice_provider' in data:
        company.voice_provider = data['voice_provider']
    
    if 'voice_model' in data:
        company.voice_model = data['voice_model']
    
    # Update API keys
    # Acceptable keys to update
    ALLOWED_KEYS = [
        'openai', 'anthropic', 'google', 'groq', 'deepseek', 'openrouter', 'lem_api_key', 'elevenlabs',
        'telephony_provider',
        'twilio_sid', 'twilio_token', 'twilio_whatsapp_number', 'twilio_voice_number', 'twilio_phone',
        'livekit_url', 'livekit_api_key', 'livekit_api_secret', 'livekit_caller_id',
        'paypal_id', 'paypal_secret', 'paypal_mode',
        'google_service_account',
        'hubspot_access_token', 'hubspot_portal_id',
    ]
    
    if 'api_keys' in data:
        current_keys = company.api_keys or {}
        # Make a copy to avoid modification issues if it's a tracked dict
        new_keys = dict(current_keys) 
        
        for key, value in data['api_keys'].items():
            if key in ALLOWED_KEYS:  # Allow clearing keys by sending "" or null
                new_keys[key] = value
                
        company.api_keys = new_keys
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "api_keys")
    db.session.commit()
    
    return jsonify({
        'message': 'LLM configuration updated',
        'llm_provider': company.llm_provider,
        'llm_model': company.llm_model
    })


@companies_bp.route('/test-llm-connection', methods=['POST'])
@jwt_required()
def test_llm_connection():
    """Validates if custom API credentials work properly with the provider."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    provider = data.get('provider', company.llm_provider or 'openai')
    api_key = data.get('api_key') or (company.api_keys or {}).get(provider)

    if not api_key:
        return jsonify({'success': False, 'message': f'No API key provided for {provider}'}), 400

    try:
        if provider == 'openai':
            import urllib.request
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return jsonify({'success': True, 'message': 'Conexión exitosa con OpenAI API'})
        elif provider == 'anthropic':
            import urllib.request
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return jsonify({'success': True, 'message': 'Conexión exitosa con Anthropic API'})
        elif provider == 'google':
            import urllib.request
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return jsonify({'success': True, 'message': 'Conexión exitosa con Google Gemini API'})
        elif provider == 'groq':
            import urllib.request
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return jsonify({'success': True, 'message': 'Conexión exitosa con Groq LPU API'})
        elif provider == 'deepseek':
            import urllib.request
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return jsonify({'success': True, 'message': 'Conexión exitosa con DeepSeek API'})
        elif provider == 'openrouter':
            import urllib.request
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    return jsonify({'success': True, 'message': 'Conexión exitosa con OpenRouter API'})
        elif provider == 'lem':
            # LEM is exclusively available on Weblifetech Cloud infrastructure
            is_cloud = os.environ.get('AIKROFY_DEPLOYMENT_MODE') == 'cloud' or os.environ.get('WEBLIFETECH_CLOUD') == 'true'
            if not is_cloud:
                return jsonify({
                    'success': False,
                    'message': 'LEM (Latent Equilibrium Models) es una tecnología propietaria disponible exclusivamente en la infraestructura Cloud de Weblifetech.'
                }), 403
            try:
                from services.lem_guardrail_service import LEMGuardrailService
                z = LEMGuardrailService.build_agent_state_vector(500)
                client = LEMGuardrailService.get_client()
                ok, verdict = client.verify(z)
                return jsonify({
                    'success': True,
                    'message': f'LEM Gateway respondió. Energía={verdict.energy}, Aceptado={ok}'
                })
            except Exception as e_lem:
                return jsonify({'success': False, 'message': f'Error conectando con LEM Cloud Gateway: {str(e_lem)}'}), 500
        else:
            return jsonify({'success': False, 'message': f'Proveedor no soportado: {provider}'}), 400

        return jsonify({'success': True, 'message': f'Conexión validada con {provider}'})
    except Exception as ex:
        logger.warning(f"[TEST_LLM_CONN] Connection failed: {ex}")
        return jsonify({'success': False, 'message': f'Error validando credenciales: {str(ex)[:150]}'}), 400


# Available LLM models for reference
LLM_MODELS = {
    'openai': [
        {'id': 'gpt-4', 'name': 'GPT-4'},
        {'id': 'gpt-4-turbo', 'name': 'GPT-4 Turbo'},
        {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5 Turbo'},
    ],
    'anthropic': [
        {'id': 'claude-3-opus', 'name': 'Claude 3 Opus'},
        {'id': 'claude-3-sonnet', 'name': 'Claude 3 Sonnet'},
        {'id': 'claude-3-haiku', 'name': 'Claude 3 Haiku'},
    ],
    'google': [
        {'id': 'gemini-pro', 'name': 'Gemini Pro'},
        {'id': 'gemini-1.5-pro', 'name': 'Gemini 1.5 Pro'},
    ]
}

VOICE_MODELS = {
    'elevenlabs': [
        {'id': 'eleven_multilingual_v2', 'name': 'Multilingual V2'},
        {'id': 'eleven_turbo_v2', 'name': 'Turbo V2'},
    ],
    'openai': [
        {'id': 'tts-1', 'name': 'TTS-1'},
        {'id': 'tts-1-hd', 'name': 'TTS-1 HD'},
    ]
}


# ─── Company Settings Alias ─────────────────────────────────────────
# The frontend Settings page calls /api/companies/settings.
# Instead of creating a separate blueprint, we register these under companies_bp
# and let app.py mount an additional prefix.

# Use the existing companies_bp defined at the top of the file


@companies_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_company_settings():
    """Return company data in the shape the Settings page expects."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    google_creds = company.api_keys.get('google_oauth_credentials') if company.api_keys else None
    logo_url = company.logo_url or (company.api_keys.get('logo_url') if company.api_keys else None)
    agent_gender_val = company.agent_gender.value if company.agent_gender else 'neutral'

    return jsonify({'data': {
        'id': company.id,
        'name': company.name,
        'logo_url': logo_url,
        'tax_id': None,
        'business_type': None,
        'business_name': company.name,
        'country': company.country,
        'city': company.city,
        'timezone': company.timezone,
        'language': company.language,
        'email': company.email,
        'phone': company.phone,
        'website': company.website,
        'instagram': company.api_keys.get('instagram') if company.api_keys else None,
        'facebook': company.api_keys.get('facebook') if company.api_keys else None,
        'personal_story': company.personality_prompt,
        'api_key': None,
        'agent_name': company.agent_name,
        'agent_gender': agent_gender_val,
        'voice_model': company.voice_model or 'smart',
        'llm_provider': company.llm_provider or 'openai',
        'llm_model': company.llm_model or 'gpt-5-nano',
        'api_keys': {
            'openai': company.api_keys.get('openai') if company.api_keys else None,
            'anthropic': company.api_keys.get('anthropic') if company.api_keys else None,
            'google': company.api_keys.get('google') if company.api_keys else None,
            'groq': company.api_keys.get('groq') if company.api_keys else None,
            'deepseek': company.api_keys.get('deepseek') if company.api_keys else None,
            'lem_api_key': company.api_keys.get('lem_api_key') if company.api_keys else None,
        },
        'lem_config': {
            'lem_enabled': (company.api_keys or {}).get('lem_enabled', True),
            'lem_strict_mode': (company.api_keys or {}).get('lem_strict_mode', True),
            'lem_sensitivity': (company.api_keys or {}).get('lem_sensitivity', 0.20),
            'is_byok': bool((company.api_keys or {}).get(company.llm_provider or 'openai')),
            'protection_credits': company.credit_balance if company.credit_balance is not None else 0
        },
        'google_connected': bool(google_creds),
        'google_calendar_id': company.api_keys.get('google_calendar_id') if company.api_keys else None,
        'meeting_provider': (company.api_keys or {}).get('meeting_provider', 'google' if google_creds else 'none'),
        'zoom_connected': bool((company.api_keys or {}).get('zoom_credentials') or ((company.api_keys or {}).get('zoom_client_id') and (company.api_keys or {}).get('zoom_client_secret'))),
        'teams_connected': bool((company.api_keys or {}).get('teams_credentials') or ((company.api_keys or {}).get('teams_client_id') and (company.api_keys or {}).get('teams_client_secret'))),
        'enabled_modules': company.get_enabled_modules(),
        'business_category': company.business_category or 'emprendimiento',
    }})


@companies_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_company_settings():
    """Update company data from Settings page."""
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}

    if 'name' in data:
        company.name = data['name']
    if 'business_name' in data:
        company.name = data['business_name']
    if 'logo_url' in data:
        company.logo_url = data['logo_url']
    if 'voice_model' in data:
        company.voice_model = data['voice_model']
    if 'llm_provider' in data:
        company.llm_provider = data['llm_provider']
    if 'llm_model' in data:
        company.llm_model = data['llm_model']
    if 'country' in data:
        company.country = data['country']
    if 'city' in data:
        company.city = data['city']
    if 'timezone' in data:
        company.timezone = data['timezone']
    if 'language' in data:
        company.language = data['language']
    if 'email' in data:
        company.email = data['email']
    if 'phone' in data:
        company.phone = data['phone']
    if 'website' in data:
        company.website = data['website']
    if 'personal_story' in data:
        company.personality_prompt = data['personal_story']
    if 'agent_name' in data:
        company.agent_name = data['agent_name']
    if 'tax_id' in data:
        pass
    if 'public_slug' in data:
        company.public_slug = data['public_slug']
    if 'agent_gender' in data:
        try:
            company.agent_gender = AgentGender(data['agent_gender'])
        except ValueError:
            return jsonify({'error': 'Invalid agent gender'}), 400

    # Keys & LEM Config stored securely in api_keys JSON
    current_keys = dict(company.api_keys or {})
    if 'instagram' in data:
        current_keys['instagram'] = data['instagram']
    if 'facebook' in data:
        current_keys['facebook'] = data['facebook']
    if 'logo_url' in data:
        current_keys['logo_url'] = data['logo_url']
    if 'meeting_provider' in data:
        current_keys['meeting_provider'] = data['meeting_provider']
    if 'enabled_modules' in data and isinstance(data['enabled_modules'], list):
        cleaned_modules = [str(m).strip() for m in data['enabled_modules'] if m]
        if 'dashboard' not in cleaned_modules:
            cleaned_modules.insert(0, 'dashboard')
        if 'settings' not in cleaned_modules:
            cleaned_modules.append('settings')
        current_keys['enabled_modules'] = cleaned_modules
        current_keys['modules_customized'] = True

    # Update Provider API Keys if provided
    if 'api_keys' in data and isinstance(data['api_keys'], dict):
        for k, v in data['api_keys'].items():
            if k in ['openai', 'anthropic', 'google', 'groq', 'deepseek', 'openrouter', 'lem_api_key']:
                if v is not None:
                    current_keys[k] = v.strip() if isinstance(v, str) else v

    # Update LEM-Ops Deterministic Invariant Settings
    if 'lem_config' in data and isinstance(data['lem_config'], dict):
        lem_c = data['lem_config']
        if 'lem_enabled' in lem_c:
            current_keys['lem_enabled'] = bool(lem_c['lem_enabled'])
        if 'lem_strict_mode' in lem_c:
            current_keys['lem_strict_mode'] = bool(lem_c['lem_strict_mode'])
        if 'lem_sensitivity' in lem_c:
            try:
                current_keys['lem_sensitivity'] = float(lem_c['lem_sensitivity'])
            except (ValueError, TypeError):
                pass

    company.api_keys = current_keys

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(company, "api_keys")
    db.session.commit()

    return jsonify({'message': 'Settings updated', 'data': company.to_dict()})


@companies_bp.route('/logo', methods=['POST'])
@jwt_required()
def upload_company_logo():
    """Upload company logo image"""
    import os
    import uuid
    from werkzeug.utils import secure_filename
    
    user, company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Empty file'}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'png'
    allowed_extensions = {'png', 'jpg', 'jpeg', 'webp', 'svg', 'gif'}
    if ext not in allowed_extensions:
        return jsonify({'error': f'Unsupported format. Allowed: {", ".join(allowed_extensions)}'}), 400

    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads', 'logos')
    os.makedirs(upload_dir, exist_ok=True)

    saved_filename = f"logo_comp_{company.id}_{uuid.uuid4().hex[:8]}.{ext}"
    saved_path = os.path.join(upload_dir, saved_filename)
    file.save(saved_path)

    logo_url = f"/api/uploads/logos/{saved_filename}"
    company.logo_url = logo_url
    
    current_keys = dict(company.api_keys or {})
    current_keys['logo_url'] = logo_url
    company.api_keys = current_keys
    
    db.session.commit()

    return jsonify({
        'message': 'Logo uploaded successfully',
        'logo_url': logo_url,
        'success': True
    }), 200


@companies_bp.route('/public/<public_slug>', methods=['GET'])
def get_public_company(public_slug):
    """Get public company details by slug or widget_id for webchat / landing"""
    company = Company.query.filter_by(public_slug=public_slug, is_active=True).first()
    if not company:
        # Fallback: Check if public_slug matches a channel's widget_id
        from models.channel import Channel, ChannelType
        channels = Channel.query.filter_by(type=ChannelType.WEBCHAT).all()
        for ch in channels:
            creds = ch.credentials if isinstance(ch.credentials, dict) else {}
            if creds.get('widget_id') == public_slug or creds.get('legacy_widget_id') == public_slug:
                company = ch.company
                break
    if not company:
        return jsonify({'error': 'Company not found'}), 404
        
    return jsonify({'data': {
        'id': company.id,
        'name': company.name,
        'agent_name': company.agent_name,
        'agent_gender': company.agent_gender.value if company.agent_gender else 'neutral',
        'language': company.language,
        'public_slug': company.public_slug,
        'logo_url': company.logo_url or (company.api_keys.get('logo_url') if company.api_keys else None)
    }})


@companies_bp.route('/available-models', methods=['GET'])
@jwt_required()
def get_available_models():
    """Get list of available LLM and voice models"""
    return jsonify({
        'llm_models': LLM_MODELS,
        'voice_models': VOICE_MODELS
    })


@companies_bp.route('/activate-trial', methods=['POST'])
@jwt_required()
def activate_trial():
    """Activate 24-hour free trial for company (Beta Phase)"""
    import logging
    logger = logging.getLogger(__name__)
    db.session.rollback()
    try:
        user, company = get_user_company()
        if not company:
            return jsonify({'error': 'Company not found'}), 404

        from datetime import datetime
        company.trial_activated = True
        company.created_at = datetime.utcnow()  # Inicia el cronómetro del trial en este instante
        db.session.commit()
        logger.info(f"Company {company.id} free trial activated at {company.created_at}")

        return jsonify({'data': company.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Activate trial error: {e}")
        return jsonify({'error': str(e)}), 500


@companies_bp.route('/submit-feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Submit beta feedback for company and unlock final billing flow"""
    import logging
    logger = logging.getLogger(__name__)
    db.session.rollback()
    try:
        user, company = get_user_company()
        if not company:
            return jsonify({'error': 'Company not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        company.feedback_submitted = True
        company.beta_feedback = data
        db.session.commit()
        logger.info(f"Company {company.id} submitted beta feedback")

        return jsonify({'data': company.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Submit feedback error: {e}")
        return jsonify({'error': str(e)}), 500


@companies_bp.route('/voice-onboarding', methods=['POST'])
@jwt_required()
def voice_onboarding():
    """Receive a voice note, transcribe it, and auto-configure the company skills and agents."""
    import logging
    import os
    import tempfile
    from openai import OpenAI
    from langchain_openai import ChatOpenAI
    from models.company_skill import CompanySkill, SkillOrigin, SkillCategory
    from models.agent import Agent, AgentFeature, DEFAULT_FEATURES, AgentTone, AgentObjective
    from extensions import db
    
    logger = logging.getLogger(__name__)
    db.session.rollback()
    
    try:
        user, company = get_user_company()
        if not company:
            return jsonify({'error': 'Company not found'}), 404
        company_id = company.id
            
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
            
        audio_file = request.files['audio']
        
        # Determine API Key (fallback to env if not in company)
        api_key = company.api_keys.get('openai') if company.api_keys else None
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            
        if not api_key:
            return jsonify({'error': 'No OpenAI API Key configured'}), 400
            
        client = OpenAI(api_key=api_key)
        
        # 1. Save temp audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_audio:
            audio_file.save(tmp_audio.name)
            tmp_audio_path = tmp_audio.name
            
        # 2. Transcribe Audio
        transcript = ""
        try:
            from services.voice_service import VoiceService
            try:
                transcript = VoiceService.transcribe(tmp_audio_path, language="es")
            except Exception as e_vs:
                logger.warning(f"VoiceService transcription failed, falling back to direct OpenAI Whisper: {e_vs}")
                with open(tmp_audio_path, "rb") as audio:
                    transcript_obj = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio,
                        language="es"
                    )
                transcript = transcript_obj.text
        finally:
            if os.path.exists(tmp_audio_path):
                try:
                    os.remove(tmp_audio_path)
                except Exception:
                    pass
                
        if not transcript or not transcript.strip():
            return jsonify({'error': 'No se pudo transcribir el audio. Por favor intenta hablar más claro o graba de nuevo.'}), 400

        # 3. Use LLM to extract CTO configuration (Fallback cascade)
        system_msg = (
            "Eres el CTO Orquestador. Acabas de escuchar una nota de voz del dueño de una empresa "
            "explicando su negocio. Analiza el texto y genera una respuesta ESTRUCTURADA en JSON sin formato adicional. "
            "Debes extraer:\n"
            "- company_name: Nombre del negocio\n"
            "- industry: Industria\n"
            "- products: Lista de productos/servicios\n"
            "- rules: Reglas de negocio importantes (tono, métodos de pago)\n"
            "- generated_skills: Un arreglo de objetos con {name (slug), label, category (sales, support, coordination, etc.), description, system_prompt_block}.\n"
            "El arreglo de skills DEBE incluir al menos un skill general de ventas (sales) y uno de soporte (support) listos para usar."
        )

        response = None
        used_model = "gpt-4o-mini"
        models_to_try = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        
        for candidate_model in models_to_try:
            try:
                llm = ChatOpenAI(model=candidate_model, openai_api_key=api_key)
                response = llm.invoke([
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"Transcripción de voz: {transcript}"}
                ])
                if response and response.content:
                    used_model = candidate_model
                    logger.info(f"Voice onboarding analyzed successfully using model {candidate_model}")
                    break
            except Exception as e_model:
                logger.warning(f"Failed using model {candidate_model} for voice onboarding: {e_model}")

        if not response or not response.content:
            return jsonify({'error': 'No se pudo estructurar la información con el modelo de IA'}), 500
        
        import json
        import re
        # Extract JSON from markdown if wrapped
        raw_content = response.content
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_content, re.DOTALL)
        if match:
            raw_content = match.group(1)
            
        config_data = json.loads(raw_content)
        
        # Re-attach and refresh DB session to guarantee connection is alive after external AI calls
        try:
            db.session.rollback()
            # Reload fresh company instance from DB to avoid detached or stale connection state
            from models.company import Company
            company = Company.query.get(company_id)
            if not company:
                return jsonify({'error': 'Company not found'}), 404
        except Exception as e_refresh:
            logger.warning(f"Session re-fresh attempt: {e_refresh}")
            db.session.rollback()
            from models.company import Company
            company = Company.query.get(company_id)
        
        # 4. Update Company Details
        is_placeholder = not company.name or company.name.lower().strip() in ['', 'my company', 'mi empresa', 'nueva empresa', 'company']
        if config_data.get('company_name') and is_placeholder:
            company.name = config_data['company_name']
        if config_data.get('industry'):
            company.industry = config_data['industry'][:100]
            
        # 5. Create or Update Agents & Skills
        generated_skills = config_data.get('generated_skills', []) if isinstance(config_data.get('generated_skills'), list) else []
        for skill_data in generated_skills:
            if not isinstance(skill_data, dict):
                continue
            try:
                cat_val = str(skill_data.get('category', 'custom')).lower()
                try:
                    category_enum = SkillCategory(cat_val)
                except (ValueError, KeyError):
                    category_enum = SkillCategory.CUSTOM
                    
                skill_name = str(skill_data.get('name') or 'custom_skill')[:100]
                skill_label = str(skill_data.get('label') or skill_name.replace('_', ' ').title())[:255]
                skill_desc = str(skill_data.get('description') or '')
                skill_prompt = str(skill_data.get('system_prompt_block') or f"Help customers with {skill_label}")

                skill = CompanySkill.query.filter_by(company_id=company.id, name=skill_name).first()
                if not skill:
                    skill = CompanySkill(
                        company_id=company.id,
                        name=skill_name,
                        label=skill_label,
                        description=skill_desc,
                        category=category_enum,
                        origin=SkillOrigin.AI_GENERATED,
                        system_prompt_block=skill_prompt,
                        is_enabled=True
                    )
                    db.session.add(skill)
                else:
                    skill.label = skill_label
                    skill.description = skill_desc
                    skill.category = category_enum
                    skill.system_prompt_block = skill_prompt
            except Exception as e_skill:
                logger.error(f"Error creating skill from voice: {e_skill}")
                
        # 6. Ensure default Agents exist (Handoff Targets) and populate them
        default_agents_config = [
            {
                "name": "cso_sales",
                "description": "Chief Sales Officer - Handles conversions",
                "category": "sales",
                "tone": AgentTone.SALES,
                "objective": AgentObjective.SALES,
                "enabled_feats": ["whatsapp", "webchat", "rag_memory", "conversation_history", "process_payment", "paypal", "ecommerce"]
            },
            {
                "name": "coo_operations",
                "description": "Chief Operations Officer - Handles logistics and support",
                "category": "support",
                "tone": AgentTone.SUPPORT,
                "objective": AgentObjective.SUPPORT,
                "enabled_feats": ["whatsapp", "webchat", "rag_memory", "conversation_history", "calendar", "schedule_meeting", "check_inventory", "crm_sync"]
            }
        ]
        
        for da in default_agents_config:
            try:
                agent = Agent.query.filter_by(company_id=company.id, name=da['name']).first()
                if not agent:
                    agent = Agent(
                        company_id=company.id,
                        name=da['name'],
                        description=da['description'],
                        is_active=True
                    )
                    db.session.add(agent)
                    db.session.flush()
                
                # Set tone and objective
                agent.tone = da['tone']
                agent.objective = da['objective']
                
                # Assign prompt from matching generated skill if available
                matching_skill = None
                for skill_data in generated_skills:
                    if isinstance(skill_data, dict):
                        if skill_data.get('category') == da['category'] or da['category'] in str(skill_data.get('name', '')):
                            matching_skill = skill_data
                            break
                
                if matching_skill and matching_skill.get('system_prompt_block'):
                    agent.system_prompt = matching_skill['system_prompt_block']
                elif not agent.system_prompt:
                    agent.system_prompt = f"Help customers with {da['category']} inquiries."
                    
                # Initialize/Update features
                existing_features = {f.name: f for f in agent.features.all()}
                for feat_data in DEFAULT_FEATURES:
                    feat_name = feat_data['name']
                    is_enabled = feat_name in da['enabled_feats']
                    
                    if feat_name in existing_features:
                        existing_features[feat_name].is_enabled = is_enabled
                    else:
                        new_feat = AgentFeature(
                            agent_id=agent.id,
                            category=feat_data['category'],
                            name=feat_name,
                            label=feat_data['label'],
                            description=feat_data['description'],
                            is_enabled=is_enabled,
                            order=feat_data['order']
                        )
                        db.session.add(new_feat)
            except Exception as e_agent:
                logger.error(f"Error configuring agent {da['name']}: {e_agent}")

        # Deduct credits for magic onboarding (Voice STT + LLM analysis) with 85% margin
        try:
            from services.token_credit_service import TokenCreditService
            est_prompt_tokens = max(200, int(len(system_msg + transcript) / 3.8))
            est_completion_tokens = max(100, int(len(raw_content) / 3.8))
            onboarding_credit_calc = TokenCreditService.calculate_cost_and_credits(
                prompt_tokens=est_prompt_tokens,
                completion_tokens=est_completion_tokens,
                model=used_model,
                stt_requests=1
            )
            ob_credits = onboarding_credit_calc.get('credits_to_deduct', 5)
            TokenCreditService.deduct_company_credits(
                company,
                credits_to_deduct=ob_credits,
                reason="magic_voice_onboarding",
                db_session=db.session
            )
        except Exception as e_obcredits:
            logger.warning(f"Onboarding credit deduction error: {e_obcredits}")

        # Update smart enabled_modules based on the voice transcript & extracted config
        current_keys = dict(company.api_keys or {})
        if not current_keys.get('modules_customized'):
            current_keys['enabled_modules'] = Company.compute_default_modules(
                business_category=company.business_category or 'emprendimiento',
                industry=company.industry or '',
                extra_context=f"{transcript} {raw_content}",
                plan_type=company.plan_type or 'pyme'
            )
            company.api_keys = current_keys
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(company, "api_keys")

        db.session.commit()
        
        return jsonify({
            'message': 'Configuration processed successfully',
            'transcript': transcript,
            'extracted_config': config_data
        }), 200

    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        logger.error(f"Voice onboarding error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@companies_bp.route('/companies/<int:company_id>/api-key/generate', methods=['POST'])
@jwt_required()
def generate_public_api_key(company_id):
    """Generate a public API key for V1 external/developer access."""
    import secrets
    company = Company.query.get_or_404(company_id)
    if not company.api_keys:
        company.api_keys = {}
    api_key = f"pymai_{secrets.token_urlsafe(32)}"
    company.api_keys = {**company.api_keys, 'public_api_key': api_key}
    db.session.commit()
    return jsonify({'success': True, 'api_key': api_key, 'message': 'Store this key securely.'})

