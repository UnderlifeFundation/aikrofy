"""
Media Service - Aikrofy
Handles upload, storage, search, and deletion of company media assets.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import os
import uuid
import logging
from typing import Optional, List

from extensions import db
from models.media_asset import CompanyMediaAsset

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB hard limit

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
ALLOWED_DOCUMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
    '.ppt', '.pptx', '.txt', '.md', '.markdown', '.json'
}
ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS
    | ALLOWED_VIDEO_EXTENSIONS
    | ALLOWED_AUDIO_EXTENSIONS
    | ALLOWED_DOCUMENT_EXTENSIONS
)

IMAGE_MIME_TYPES = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.webp': 'image/webp', '.gif': 'image/gif', '.svg': 'image/svg+xml',
}
VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
}
AUDIO_MIME_TYPES = {
    '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4', '.aac': 'audio/aac',
}
DOCUMENT_MIME_TYPES = {
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.csv': 'text/csv',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.markdown': 'text/markdown',
    '.json': 'application/json',
}
ALL_MIME_TYPES = {
    **IMAGE_MIME_TYPES,
    **VIDEO_MIME_TYPES,
    **AUDIO_MIME_TYPES,
    **DOCUMENT_MIME_TYPES,
}

import re
import unicodedata

# Base upload directory — relative to backend root
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_MEDIA_BASE = os.path.join(_BACKEND_ROOT, 'uploads', 'media')


def sanitize_folder(folder: str) -> str:
    """
    Sanitize folder name by converting accents/diacritics to ASCII,
    replacing spaces/symbols with underscores, and preventing directory traversal.
    Example: 'campaña landing page + agente' -> 'campana_landing_page_agente'
    """
    if not folder:
        return 'general'
    # Normalize unicode (decompose ñ -> n + ~, etc.)
    folder = unicodedata.normalize('NFKD', str(folder)).encode('ASCII', 'ignore').decode('utf-8')
    folder = folder.strip('/').replace('..', '').strip()
    # Replace non-alphanumeric (except underscores and hyphens) with underscores
    folder = re.sub(r'[^a-zA-Z0-9_\-]', '_', folder)
    # Collapse multiple consecutive underscores
    folder = re.sub(r'_+', '_', folder).strip('_')
    return folder.lower() or 'general'


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename to safe ASCII characters while preserving extension."""
    base, ext = os.path.splitext(filename)
    base = unicodedata.normalize('NFKD', str(base)).encode('ASCII', 'ignore').decode('utf-8')
    base = re.sub(r'[^a-zA-Z0-9_\-]', '_', base)
    base = re.sub(r'_+', '_', base).strip('_')
    clean_ext = re.sub(r'[^a-zA-Z0-9]', '', ext.lower())
    return f"{base or 'file'}.{clean_ext}" if clean_ext else (base or 'file')


def get_media_token(asset: CompanyMediaAsset) -> str:
    """
    Extract the unguessable unique token (UUID) from the asset's stored filename.
    Stored filename format: '<uuid4_hex>_<safe_original_name>'
    Example: '791bc0ec09d24d70b60a1568006d15f1_video-demo.mp4' -> '791bc0ec09d24d70b60a1568006d15f1'
    """
    if not asset or not asset.filename:
        return ''
    parts = asset.filename.split('_', 1)
    return parts[0] if len(parts[0]) == 32 else asset.filename


def _get_upload_dir(company_id: int, folder: str) -> str:
    """Return and ensure the upload directory for a company/folder pair."""
    safe_folder = sanitize_folder(folder)
    upload_dir = os.path.join(UPLOAD_MEDIA_BASE, f'company_{company_id}', safe_folder)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _determine_media_type(ext: str) -> Optional[str]:
    """Determine media category ('image', 'video', 'audio', 'document'). Returns None if unsupported."""
    ext_lower = ext.lower()
    if ext_lower in ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    elif ext_lower in ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    elif ext_lower in ALLOWED_AUDIO_EXTENSIONS:
        return 'audio'
    elif ext_lower in ALLOWED_DOCUMENT_EXTENSIONS:
        return 'document'
    return None


# ─── Upload ───────────────────────────────────────────────────────────────────

def upload_media_file(
    company_id: int,
    folder: str,
    file_obj,          # FlaskFileStorage-like object with .filename and .save()
    title: str = '',
    description: str = '',
    keywords: list = None,
    base_url: str = '',
) -> dict:
    """
    Upload a media file (image, video, document, audio) for a company.
    
    Args:
        company_id: Company ID for multi-tenancy.
        folder: Logical folder name (e.g. 'demos', 'productos', 'general', 'documentos').
        file_obj: File-like object with .filename attribute.
        title: Human-readable title.
        description: Description of the asset.
        keywords: List of keyword strings for AI search.
        base_url: Server base URL for constructing the public file_url.
    
    Returns:
        dict with the created CompanyMediaAsset.to_dict()
    
    Raises:
        ValueError: If file type is invalid or file is too large.
    """
    filename_original = getattr(file_obj, 'filename', '') or 'upload'
    ext = '.' + filename_original.rsplit('.', 1)[-1].lower() if '.' in filename_original else ''
    
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f'Tipo de archivo no permitido: {ext}. '
            f'Formatos admitidos: imágenes, videos, audio y documentos ({", ".join(sorted(ALLOWED_EXTENSIONS))})'
        )
    
    media_type = _determine_media_type(ext) or 'document'
    mime_type = ALL_MIME_TYPES.get(ext, 'application/octet-stream')
    
    # Safe folder name
    safe_folder = sanitize_folder(folder)
    
    # Build unique filename with sanitized original name
    unique_id = uuid.uuid4().hex
    safe_original = sanitize_filename(filename_original)
    stored_filename = f"{unique_id}_{safe_original}"
    
    upload_dir = _get_upload_dir(company_id, safe_folder)
    file_path = os.path.join(upload_dir, stored_filename)
    
    # Save file
    file_obj.save(file_path)
    
    # Verify size after saving
    size_bytes = os.path.getsize(file_path)
    if size_bytes > MAX_FILE_SIZE:
        os.remove(file_path)
        raise ValueError(
            f'El archivo pesa {size_bytes / 1024 / 1024:.1f} MB. '
            f'El máximo permitido es 10 MB.'
        )
    
    # Persist to DB first to obtain asset ID
    asset = CompanyMediaAsset(
        company_id=company_id,
        folder=safe_folder,
        filename=stored_filename,
        file_url='',
        media_type=media_type,
        size_bytes=size_bytes,
        mime_type=mime_type,
        title=title or filename_original,
        description=description or '',
        keywords=keywords or [],
    )
    db.session.add(asset)
    db.session.flush()

    # Build reliable and secure API file URL using unguessable token
    # /api/media/file/<token> streams directly through FastAPI with range request support
    token = get_media_token(asset)
    rel_path = f'/api/media/file/{token}'
    file_url = f'{base_url.rstrip("/")}{rel_path}' if base_url else rel_path
    asset.file_url = file_url
    db.session.commit()
    
    logger.info(f'[Media] Uploaded {media_type} for company {company_id}: {stored_filename} ({size_bytes} bytes)')
    asset_dict = asset.to_dict()
    asset_dict['token'] = token
    return asset_dict


# ─── List & Search ────────────────────────────────────────────────────────────

def list_media_assets(
    company_id: int,
    folder: Optional[str] = None,
    media_type: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """
    List media assets for a company with optional filters.
    
    Args:
        company_id: Company ID.
        folder: Filter by folder name.
        media_type: 'image' or 'video'.
        keyword: Search in title, description, folder, and keywords JSON.
        page: Pagination page.
        per_page: Items per page.
    
    Returns:
        dict with 'data' (list) and 'pagination'.
    """
    query = CompanyMediaAsset.query.filter_by(company_id=company_id)
    
    if folder and folder != 'all':
        query = query.filter_by(folder=sanitize_folder(folder))
    
    if media_type and media_type in ('image', 'video'):
        query = query.filter_by(media_type=media_type)
    
    if keyword:
        kw = f'%{keyword}%'
        from sqlalchemy import or_, cast, String
        query = query.filter(
            or_(
                CompanyMediaAsset.title.ilike(kw),
                CompanyMediaAsset.description.ilike(kw),
                CompanyMediaAsset.folder.ilike(kw),
                cast(CompanyMediaAsset.keywords, String).ilike(kw),
            )
        )
    
    pagination = query.order_by(CompanyMediaAsset.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    def _serialize_asset(a):
        d = a.to_dict()
        tok = get_media_token(a)
        d['token'] = tok
        if not d.get('file_url') or '/api/media/file/' in d.get('file_url', ''):
            d['file_url'] = f'/api/media/file/{tok}'
        return d

    return {
        'data': [_serialize_asset(a) for a in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
        }
    }


def list_folders(company_id: int) -> list:
    """Return distinct folder names used by a company."""
    rows = (
        db.session.query(CompanyMediaAsset.folder)
        .filter_by(company_id=company_id)
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


def find_media_for_ai(company_id: int, keyword: str, media_type: Optional[str] = None) -> list:
    """
    Search media assets by keyword — used by the AI agent to find relevant media.
    Returns a list of asset dicts.
    """
    result = list_media_assets(
        company_id=company_id,
        media_type=media_type,
        keyword=keyword,
        per_page=5,
    )
    return result.get('data', [])


def get_media_asset(identifier, company_id: Optional[int] = None) -> Optional[CompanyMediaAsset]:
    """
    Retrieve a media asset securely by either:
      1. integer primary key id (e.g. 1)
      2. unique file token / uuid (e.g. '791bc0ec09d24d70b60a1568006d15f1')
      3. stored unique filename
    Optionally verifies company_id.
    """
    from sqlalchemy import or_
    str_ident = str(identifier).strip()
    query = CompanyMediaAsset.query

    if company_id is not None:
        query = query.filter_by(company_id=company_id)

    if str_ident.isdigit():
        asset = query.filter_by(id=int(str_ident)).first()
        if asset:
            return asset

    # Look up by exact filename match or prefix token match
    return query.filter(
        or_(
            CompanyMediaAsset.filename == str_ident,
            CompanyMediaAsset.filename.like(f"{str_ident}%")
        )
    ).first()


def resolve_asset_file_path(asset: CompanyMediaAsset) -> Optional[str]:
    """
    Resolve the physical filesystem path for a media asset.
    Handles both sanitized folder names and legacy folder paths.
    """
    # 1. Standard upload dir with sanitized folder
    safe_folder = sanitize_folder(asset.folder)
    path = os.path.join(UPLOAD_MEDIA_BASE, f'company_{asset.company_id}', safe_folder, asset.filename)
    if os.path.exists(path):
        return path
    
    # 2. Try raw folder as stored in DB (in case of legacy assets before sanitization)
    raw_path = os.path.join(UPLOAD_MEDIA_BASE, f'company_{asset.company_id}', asset.folder, asset.filename)
    if os.path.exists(raw_path):
        return raw_path

    # 3. Fallback: Search in all company subfolders
    company_dir = os.path.join(UPLOAD_MEDIA_BASE, f'company_{asset.company_id}')
    if os.path.exists(company_dir):
        for root, _, files in os.walk(company_dir):
            if asset.filename in files:
                return os.path.join(root, asset.filename)
    
    return None


# ─── Update ───────────────────────────────────────────────────────────────────

def update_media_asset(
    asset_id: int,
    company_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    keywords: Optional[list] = None,
    folder: Optional[str] = None,
) -> dict:
    """Update metadata for a media asset."""
    asset = CompanyMediaAsset.query.filter_by(id=asset_id, company_id=company_id).first()
    if not asset:
        raise LookupError(f'Asset {asset_id} not found')
    
    if title is not None:
        asset.title = title
    if description is not None:
        asset.description = description
    if keywords is not None:
        asset.keywords = keywords
    if folder is not None:
        safe_folder = sanitize_folder(folder)
        # If folder changed, move physical file
        if safe_folder != asset.folder:
            current_path = resolve_asset_file_path(asset)
            if current_path and os.path.exists(current_path):
                new_dir = _get_upload_dir(company_id, safe_folder)
                new_path = os.path.join(new_dir, asset.filename)
                try:
                    os.rename(current_path, new_path)
                except OSError as e:
                    logger.warning(f'[Media] Could not move file to new folder: {e}')
            asset.folder = safe_folder
    
    db.session.commit()
    return asset.to_dict()


# ─── Delete ───────────────────────────────────────────────────────────────────

def delete_media_asset(asset_id: int, company_id: int) -> bool:
    """
    Delete a media asset: removes the physical file and the DB record.
    Returns True if deleted, False if not found.
    """
    asset = CompanyMediaAsset.query.filter_by(id=asset_id, company_id=company_id).first()
    if not asset:
        return False
    
    # Try to remove physical file using resilient path resolver
    file_path = resolve_asset_file_path(asset)
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            logger.warning(f'[Media] Could not delete file {file_path}: {e}')
    
    db.session.delete(asset)
    db.session.commit()
    logger.info(f'[Media] Deleted asset {asset_id} for company {company_id}')
    return True
