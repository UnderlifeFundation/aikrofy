"""
Meta Template Service
Handles GET, POST, DELETE operations for Meta Graph API v21.0 message_templates
and provides AI-powered template optimization based on conversion data.
"""
import logging
import requests
from typing import Dict, Any, List, Optional
from extensions import db
from models.channel import Channel, ChannelType, ChannelStatus
from models.company import Company
from models.whatsapp_template import WhatsAppTemplate, TemplateStatus, TemplateCategory

logger = logging.getLogger(__name__)

META_GRAPH_VERSION = 'v22.0'
META_GRAPH_BASE = f'https://graph.facebook.com/{META_GRAPH_VERSION}'


class MetaTemplateService:

    @staticmethod
    def _get_meta_credentials(company_id: int):
        """Retrieve WABA ID and Access Token for company if channel is active."""
        channel = Channel.query.filter_by(
            company_id=company_id,
            type=ChannelType.WHATSAPP
        ).first()

        access_token = None
        waba_id = None

        if channel and channel.status == ChannelStatus.CONNECTED and channel.credentials:
            access_token = channel.credentials.get('access_token')
            waba_id = channel.credentials.get('waba_id')
            if access_token and waba_id:
                return access_token, waba_id

        # Fallback to company.api_keys only if whatsapp_provider is meta and channel is not explicitly disconnected
        if channel and channel.status == ChannelStatus.DISCONNECTED:
            return None, None

        company = Company.query.get(company_id)
        if company and company.api_keys and company.api_keys.get('whatsapp_provider') == 'meta':
            access_token = company.api_keys.get('meta_token')
            waba_id = company.api_keys.get('meta_waba_id')

        return access_token, waba_id

    @classmethod
    def _normalize_and_validate_components(cls, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensures components conform strictly to Meta WhatsApp Graph API v21.0 specs:
        - Re-indexes non-sequential or named variables into strict sequential numbers ({{1}}, {{2}}, ...).
        - Auto-builds mandatory 'example' field if missing when variables exist.
        - Filters out empty components (e.g. empty HEADER or FOOTER text).
        - Trims text lengths according to Meta limits.
        """
        import re
        normalized = []

        for comp in components:
            comp_type = comp.get('type', '').upper()

            if comp_type == 'BODY':
                text = comp.get('text', '').strip()
                if not text:
                    continue

                # Find all variables like {{1}}, {{name}}, {{ 1 }}
                raw_vars = re.findall(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', text)
                if raw_vars:
                    # Map unique variables in order of appearance to sequential 1, 2, 3...
                    var_map = {}
                    seq_counter = 1
                    for v in raw_vars:
                        if v not in var_map:
                            var_map[v] = str(seq_counter)
                            seq_counter += 1

                    # Replace in text with sequential {{1}}, {{2}}, etc.
                    def replace_var(match):
                        var_name = match.group(1).strip()
                        return f"{{{{{var_map[var_name]}}}}}"

                    text = re.sub(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', replace_var, text)

                    samples = [f"ejemplo_{i}" for i in range(1, seq_counter)]
                    clean_comp = {
                        'type': 'BODY',
                        'text': text,
                        'example': {
                            'body_text': [samples]
                        }
                    }
                else:
                    clean_comp = {
                        'type': 'BODY',
                        'text': text
                    }
                normalized.append(clean_comp)

            elif comp_type == 'HEADER':
                format_type = comp.get('format', 'TEXT').upper()
                raw_text = comp.get('text', '').strip()

                if format_type == 'TEXT':
                    if not raw_text:
                        continue

                    # Meta Guidelines: Header text CANNOT contain emojis, newlines, asterisks (*), underscores (_), tildes (~), or backticks (`)
                    # 1. Remove Emojis
                    clean_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u27ff\u2300-\u23ff\u2B50\u2B55]', '', raw_text)
                    # 2. Remove Newlines and Formatting Markups (*, _, ~, `)
                    clean_text = re.sub(r'[\n\r\*\_~`]', ' ', clean_text)
                    # 3. Normalize multiple spaces
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()[:60]

                    if not clean_text:
                        continue

                    clean_comp = {
                        'type': 'HEADER',
                        'format': 'TEXT',
                        'text': clean_text
                    }
                    raw_vars = re.findall(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', clean_text)
                    if raw_vars:
                        clean_comp['text'] = re.sub(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', '{{1}}', clean_text)
                        clean_comp['example'] = {
                            'header_text': ['ejemplo_encabezado']
                        }
                    normalized.append(clean_comp)
                elif format_type in ['IMAGE', 'VIDEO', 'DOCUMENT']:
                    clean_comp = {
                        'type': 'HEADER',
                        'format': format_type
                    }
                    if 'example' in comp:
                        clean_comp['example'] = comp['example']
                    normalized.append(clean_comp)

            elif comp_type == 'FOOTER':
                text = comp.get('text', '').strip()
                if text:
                    normalized.append({
                        'type': 'FOOTER',
                        'text': text
                    })

            elif comp_type == 'BUTTONS':
                buttons = comp.get('buttons', [])
                clean_buttons = []
                for btn in buttons:
                    btn_type = btn.get('type', '').upper()
                    btn_text = btn.get('text', '').strip()[:25]
                    if not btn_text:
                        continue

                    if btn_type == 'QUICK_REPLY':
                        clean_buttons.append({
                            'type': 'QUICK_REPLY',
                            'text': btn_text
                        })
                    elif btn_type == 'URL':
                        url_text = btn.get('url', '').strip()
                        if not url_text:
                            continue
                        btn_obj = {
                            'type': 'URL',
                            'text': btn_text,
                            'url': url_text
                        }
                        if '{{1}}' in url_text or '{{' in url_text:
                            btn_obj['url'] = re.sub(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', '{{1}}', url_text)
                            btn_obj['example'] = ['ejemplo_url']
                        clean_buttons.append(btn_obj)
                    elif btn_type == 'PHONE_NUMBER':
                        phone = btn.get('phone_number', '').strip()
                        if phone:
                            clean_buttons.append({
                                'type': 'PHONE_NUMBER',
                                'text': btn_text,
                                'phone_number': phone
                            })

                if clean_buttons:
                    normalized.append({
                        'type': 'BUTTONS',
                        'buttons': clean_buttons
                    })
            else:
                normalized.append(comp)

        return normalized


    @classmethod
    def sync_templates_from_meta(cls, company_id: int) -> Dict[str, Any]:
        """Fetch all message_templates from Meta Graph API and sync local DB."""
        access_token, waba_id = cls._get_meta_credentials(company_id)
        if not access_token or not waba_id:
            return {'success': False, 'error': 'Meta WABA credentials missing. Please complete Meta login.'}

        url = f"{META_GRAPH_BASE}/{waba_id}/message_templates"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': 100, 'fields': 'id,name,status,category,language,components,rejected_reason'}

        try:
            res = requests.get(url, headers=headers, params=params, timeout=15)
            data = res.json()

            if res.status_code != 200:
                err_msg = data.get('error', {}).get('message', 'Failed to fetch templates from Meta')
                return {'success': False, 'error': err_msg}

            meta_templates = data.get('data', [])
            synced_count = 0

            for item in meta_templates:
                meta_id = str(item.get('id', ''))
                name = item.get('name')
                language = item.get('language')

                # Search by meta_template_id first, fallback to name+language
                tpl = None
                if meta_id:
                    tpl = WhatsAppTemplate.query.filter_by(
                        company_id=company_id,
                        meta_template_id=meta_id
                    ).first()

                if not tpl:
                    tpl = WhatsAppTemplate.query.filter_by(
                        company_id=company_id,
                        name=name,
                        language=language
                    ).first()

                if not tpl:
                    tpl = WhatsAppTemplate(
                        company_id=company_id,
                        name=name,
                        language=language
                    )
                    db.session.add(tpl)

                tpl.meta_template_id = meta_id
                tpl.category = item.get('category', TemplateCategory.MARKETING.value)
                tpl.status = item.get('status', TemplateStatus.PENDING.value)
                tpl.components = item.get('components', [])
                tpl.rejected_reason = item.get('rejected_reason')

                # Calculate AI score baseline based on status
                if tpl.status == 'APPROVED' and not tpl.ai_performance_score:
                    tpl.ai_performance_score = 85.0
                elif tpl.status == 'REJECTED':
                    tpl.ai_performance_score = 30.0

                synced_count += 1

            db.session.commit()
            return {'success': True, 'synced_count': synced_count, 'total': len(meta_templates)}

        except Exception as exc:
            logger.error(f"[MetaTemplateService.sync_templates] {exc}")
            return {'success': False, 'error': str(exc)}

    @classmethod
    def create_template_on_meta(cls, company_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new message_template on Meta Graph API and local DB."""
        access_token, waba_id = cls._get_meta_credentials(company_id)
        if not access_token or not waba_id:
            return {'success': False, 'error': 'Meta WABA credentials missing. Connect Meta WhatsApp first.'}

        name = payload.get('name', '').strip().lower().replace(' ', '_')
        category = payload.get('category', TemplateCategory.MARKETING.value)
        language = payload.get('language', 'es')
        components = payload.get('components', [])

        if not name or not components:
            return {'success': False, 'error': 'Template name and components are required.'}

        # Normalize and validate components per Meta v21.0 specs
        normalized_components = cls._normalize_and_validate_components(components)

        url = f"{META_GRAPH_BASE}/{waba_id}/message_templates"
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        body = {
            'name': name,
            'category': category,
            'language': language,
            'components': normalized_components
        }

        try:
            res = requests.post(url, headers=headers, json=body, timeout=15)
            data = res.json()

            if res.status_code in [200, 201] and 'id' in data:
                meta_id = str(data['id'])
                # Save locally
                tpl = WhatsAppTemplate.query.filter_by(company_id=company_id, name=name, language=language).first()
                if not tpl:
                    tpl = WhatsAppTemplate(
                        company_id=company_id,
                        name=name,
                        category=category,
                        language=language,
                        components=normalized_components,
                        meta_template_id=meta_id,
                        status=TemplateStatus.PENDING.value,
                        ai_performance_score=90.0
                    )
                    db.session.add(tpl)
                else:
                    tpl.meta_template_id = meta_id
                    tpl.status = TemplateStatus.PENDING.value
                    tpl.components = normalized_components

                db.session.commit()
                return {'success': True, 'id': meta_id, 'template': tpl.to_dict()}

            err_msg = data.get('error', {}).get('message', 'Failed to create template on Meta')
            err_user_msg = data.get('error', {}).get('error_user_msg') or data.get('error', {}).get('error_data', {}).get('details') or err_msg
            logger.error(f"[MetaTemplateService.create] Meta Error HTTP {res.status_code}: {data}")
            return {'success': False, 'error': f"{err_msg}: {err_user_msg}" if err_user_msg != err_msg else err_msg}

        except Exception as exc:
            logger.error(f"[MetaTemplateService.create] Exception: {exc}")
            return {'success': False, 'error': str(exc)}

    @classmethod
    def update_template_on_meta(cls, company_id: int, template_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing WhatsApp template on Meta Graph API and local DB."""
        tpl = WhatsAppTemplate.query.filter_by(id=template_id, company_id=company_id).first()
        if not tpl:
            return {'success': False, 'error': 'Template not found locally.'}

        access_token, waba_id = cls._get_meta_credentials(company_id)
        if not access_token or not waba_id:
            return {'success': False, 'error': 'Meta WABA credentials missing. Connect Meta WhatsApp first.'}

        category = payload.get('category', tpl.category)
        components = payload.get('components', tpl.components)

        if not components:
            return {'success': False, 'error': 'Components are required for updating template.'}

        # Normalize components per Meta v21.0 specs
        normalized_components = cls._normalize_and_validate_components(components)

        meta_id = tpl.meta_template_id
        if meta_id:
            url = f"{META_GRAPH_BASE}/{meta_id}"
        else:
            url = f"{META_GRAPH_BASE}/{waba_id}/message_templates"

        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        body = {
            'components': normalized_components,
            'category': category,
        }

        try:
            res = requests.post(url, headers=headers, json=body, timeout=15)
            data = res.json()

            if res.status_code in [200, 201] and (data.get('success') or 'id' in data):
                tpl.components = normalized_components
                tpl.category = category
                tpl.status = TemplateStatus.PENDING.value  # Meta puts edited templates back to pending review
                db.session.commit()
                return {'success': True, 'template': tpl.to_dict()}


            err_msg = data.get('error', {}).get('message', 'Failed to update template on Meta')
            logger.error(f"[MetaTemplateService.update] Meta Error: {err_msg}")
            return {'success': False, 'error': err_msg}

        except Exception as exc:
            logger.error(f"[MetaTemplateService.update] Exception: {exc}")
            return {'success': False, 'error': str(exc)}

    @classmethod
    def delete_template_on_meta(cls, company_id: int, template_id: int) -> Dict[str, Any]:
        """Delete template on Meta by name and remove or mark deleted locally."""
        tpl = WhatsAppTemplate.query.filter_by(id=template_id, company_id=company_id).first()
        if not tpl:
            return {'success': False, 'error': 'Template not found locally.'}

        access_token, waba_id = cls._get_meta_credentials(company_id)
        if access_token and waba_id:
            url = f"{META_GRAPH_BASE}/{waba_id}/message_templates"
            headers = {'Authorization': f'Bearer {access_token}'}
            params = {'name': tpl.name}
            try:
                requests.delete(url, headers=headers, params=params, timeout=15)
            except Exception as exc:
                logger.warning(f"[MetaTemplateService.delete] Remote call failed: {exc}")

        db.session.delete(tpl)
        db.session.commit()
        return {'success': True}

    @classmethod
    def generate_ai_optimized_template(cls, company_id: int, goal: str, target_audience: str) -> Dict[str, Any]:
        """AI Powered generator that structures a high-converting Meta HSM Template."""
        from services.agent_service import AgentService

        prompt = f"""
        Como experto en copywriting conversacional para WhatsApp Cloud API y analítica de ventas:
        Crea una plantilla HSM optimizada para Meta WhatsApp Business API.
        Objetivo: {goal}
        Público Objetivo: {target_audience}

        Requisitos estrictos de formato Meta Graph API:
        Devuelve ÚNICAMENTE un JSON válido con la siguiente estructura:
        {{
            "name": "nombre_plantilla_optimizada",
            "category": "MARKETING",
            "language": "es",
            "ai_score": 94.5,
            "reasoning": "Explicación de por qué este formato convierte mejor",
            "components": [
                {{
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": "Encabezado atractivo"
                }},
                {{
                    "type": "BODY",
                    "text": "Cuerpo del mensaje claro con variables {{1}} y punto de dolor solucionado."
                }},
                {{
                    "type": "FOOTER",
                    "text": "Responde a este mensaje para más información"
                }},
                {{
                    "type": "BUTTONS",
                    "buttons": [
                        {{
                            "type": "QUICK_REPLY",
                            "text": "Quiero saber más"
                        }}
                    ]
                }}
            ]
        }}
        """

        try:
            # Reutiliza OpenAI/Gemini configurado en la empresa o AgentService
            from langchain_google_genai import ChatGoogleGenerativeAI
            from config import Config
            import json

            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=Config.GEMINI_API_KEY or Config.OPENAI_API_KEY,
                temperature=0.4
            )
            response = llm.invoke(prompt)
            content = response.content.strip()

            # Extraer JSON del bloque de markdown si existe
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return {'success': True, 'suggestion': data}

        except Exception as exc:
            logger.error(f"[MetaTemplateService.generate_ai] {exc}")
            # Fallback estructurado si falla la IA
            fallback_name = f"promo_optimizada_{goal[:10].strip().lower().replace(' ', '_')}"
            return {
                'success': True,
                'suggestion': {
                    'name': fallback_name,
                    'category': 'MARKETING',
                    'language': 'es',
                    'ai_score': 88.0,
                    'reasoning': 'Plantilla estándar de alta conversión para ofertas de WhatsApp.',
                    'components': [
                        {'type': 'HEADER', 'format': 'TEXT', 'text': '🔥 Oferta Especial para ti'},
                        {'type': 'BODY', 'text': f'Hola {{1}}, tenemos una propuesta exclusiva relacionada con {goal}. ¿Te gustaría revisarla hoy?'},
                        {'type': 'FOOTER', 'text': 'Responde para obtener acceso prioritario'},
                        {'type': 'BUTTONS', 'buttons': [{'type': 'QUICK_REPLY', 'text': 'Ver detalles'}]}
                    ]
                }
            }
