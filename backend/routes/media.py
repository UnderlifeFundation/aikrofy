"""
Media Routes - Aikrofy Media Library API

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from fastapi.responses import FileResponse
import os

from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from models.user import User, UserRole
from models.media_asset import CompanyMediaAsset
from services.media_service import (
    upload_media_file, list_media_assets, list_folders,
    update_media_asset, delete_media_asset, get_media_asset,
    resolve_asset_file_path, MAX_FILE_SIZE,
    ALLOWED_IMAGE_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_AUDIO_EXTENSIONS, ALLOWED_DOCUMENT_EXTENSIONS,
    ALLOWED_EXTENSIONS
)

logger = logging.getLogger(__name__)

media_bp = APIRouter('media', __name__)


def _get_user_company():
    """Get current user and their company."""
    user_id = get_jwt_identity()
    if not user_id:
        return None, None
    user = User.query.get(int(user_id))
    if not user:
        return None, None
    if user.company:
        return user, user.company
    if user.role == UserRole.SUPER_ADMIN:
        from models.company import Company
        comp = Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
        return user, comp
    return user, None


@media_bp.route('', methods=['GET'])
@jwt_required()
def list_media():
    """List media assets for the company with optional filters."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    folder = request.args.get('folder', '')
    media_type = request.args.get('media_type', '')
    keyword = request.args.get('q', '') or request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    result = list_media_assets(
        company_id=company.id,
        folder=folder or None,
        media_type=media_type or None,
        keyword=keyword or None,
        page=page,
        per_page=per_page,
    )
    return jsonify(result), 200


@media_bp.route('/folders', methods=['GET'])
@jwt_required()
def get_folders():
    """Get all folders used by the company's media library."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    folders = list_folders(company.id)
    if not folders:
        folders = ['general']
    
    return jsonify({'data': folders}), 200


@media_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_media():
    """Upload a media file (image or video, max 10MB) to a folder."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo. Usa el campo "file" en el form-data.'}), 400
    
    uploaded_file = request.files['file']
    filename = uploaded_file.filename or ''
    
    # Extension validation
    allowed = ALLOWED_EXTENSIONS
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if not ext or ext not in allowed:
        return jsonify({
            'error': f'Tipo de archivo no permitido. Formatos soportados: {", ".join(sorted(allowed))}'
        }), 400
    
    folder = request.form.get('folder', 'general') or 'general'
    title = request.form.get('title', '') or ''
    description = request.form.get('description', '') or ''
    keywords_str = request.form.get('keywords', '') or ''
    campaign_id = request.form.get('campaign_id')
    if campaign_id:
        description = f"{description.strip()} [CAMPAIGN_ID:{campaign_id}]".strip()
    
    # Parse keywords (comma-separated string)
    keywords = [k.strip() for k in keywords_str.split(',') if k.strip()] if keywords_str else []
    
    # Derive base URL from config
    try:
        from config import get_config
        cfg = get_config()
        base_url = getattr(cfg, 'SERVER_BASE_URL', '') or getattr(cfg, 'BASE_URL', '') or ''
    except Exception:
        base_url = ''
    
    try:
        asset = upload_media_file(
            company_id=company.id,
            folder=folder,
            file_obj=uploaded_file,
            title=title,
            description=description,
            keywords=keywords,
            base_url=base_url,
        )
    except ValueError as e:
        status_code = 413 if '10 MB' in str(e) or 'tamaño' in str(e).lower() else 400
        return jsonify({'error': str(e)}), status_code
    except Exception as e:
        logger.error(f'[Media] Upload error for company {company.id}: {e}')
        return jsonify({'error': f'Error al subir el archivo: {str(e)}'}), 500
    
    logger.info(f'User {user.email} uploaded media asset for company {company.id}: {filename}')
    return jsonify({'message': 'Archivo subido exitosamente', 'data': asset}), 201


@media_bp.route('/<int:asset_id>', methods=['PATCH'])
@jwt_required()
def update_media(asset_id):
    """Update metadata for a media asset (title, description, keywords, folder)."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json() or {}
    
    try:
        desc = data.get('description')
        if 'campaign_id' in data:
            import re
            camp_id = data['campaign_id']
            curr_desc = desc if desc is not None else (CompanyMediaAsset.query.get(asset_id).description or '')
            cleaned_desc = re.sub(r'\s*\[CAMPAIGN_ID:\d+\]', '', curr_desc).strip()
            if camp_id:
                desc = f"{cleaned_desc} [CAMPAIGN_ID:{camp_id}]".strip()
            else:
                desc = cleaned_desc

        asset = update_media_asset(
            asset_id=asset_id,
            company_id=company.id,
            title=data.get('title'),
            description=desc,
            keywords=data.get('keywords'),
            folder=data.get('folder'),
        )
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f'[Media] Update error for asset {asset_id}: {e}')
        return jsonify({'error': f'Error actualizando el asset: {str(e)}'}), 500
    
    return jsonify({'message': 'Asset actualizado', 'data': asset}), 200


@media_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_media(asset_id):
    """Delete a media asset and its file."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    deleted = delete_media_asset(asset_id, company.id)
    if not deleted:
        return jsonify({'error': 'Asset no encontrado'}), 404
    
    logger.info(f'User {user.email} deleted media asset {asset_id} for company {company.id}')
    return jsonify({'message': 'Asset eliminado exitosamente', 'id': asset_id}), 200


@media_bp.route('/info', methods=['GET'])
@jwt_required()
def media_info():
    """Return allowed file types and size limits."""
    return jsonify({
        'data': {
            'max_size_mb': MAX_FILE_SIZE // (1024 * 1024),
            'allowed_images': sorted(ALLOWED_IMAGE_EXTENSIONS),
            'allowed_videos': sorted(ALLOWED_VIDEO_EXTENSIONS),
            'allowed_audio': sorted(ALLOWED_AUDIO_EXTENSIONS),
            'allowed_documents': sorted(ALLOWED_DOCUMENT_EXTENSIONS),
            'allowed_all': sorted(ALLOWED_EXTENSIONS),
        }
    }), 200


@media_bp.route('/file/<identifier>', methods=['GET'])
def serve_media_file(identifier):
    """
    Serve a media file directly with full HTTP Range request support.
    Accepts unguessable UUID tokens (e.g. '791bc0ec09d24d70b60a1568006d15f1')
    as well as numeric IDs for backwards compatibility.
    Unguessable tokens prevent IDOR / enumeration attacks.
    Enables smooth streaming for HTML5 <video> and <audio> tags and reliable image display.
    """
    asset = get_media_asset(identifier)
    if not asset:
        return jsonify({'error': 'Archivo multimedia no encontrado'}), 404
    
    file_path = resolve_asset_file_path(asset)
    if not file_path or not os.path.exists(file_path):
        logger.warning(f"[Media] Physical file not found for asset {identifier}: {asset.filename}")
        return jsonify({'error': 'El archivo físico no existe en el servidor'}), 404
    
    mime_type = asset.mime_type or 'application/octet-stream'
    
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=asset.filename,
        content_disposition_type='inline',
        headers={
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=86400',
            'Access-Control-Allow-Origin': '*',
        }
    )

