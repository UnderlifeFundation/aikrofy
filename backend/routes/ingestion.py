"""
Ingestion Routes - Bulk data upload for leads, employees, and sales.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from fastapi.responses import Response

from routing import APIRouter, get_jwt_identity, jsonify, jwt_required, request
from extensions import db
from models.user import User, UserRole
from services.ingestion_service import (
    ENTITY_DEFINITIONS, generate_csv_template, generate_xlsx_template, process_upload
)

logger = logging.getLogger(__name__)

ingestion_bp = APIRouter('ingestion', __name__)


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


@ingestion_bp.route('/entities', methods=['GET'])
@jwt_required()
def list_entities():
    """List all supported importable entity types."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    entities = [
        {
            'key': key,
            'label': definition['label'],
            'description': definition['description'],
            'columns': definition['columns'],
        }
        for key, definition in ENTITY_DEFINITIONS.items()
    ]
    return jsonify({'data': entities}), 200


@ingestion_bp.route('/template/<entity>', methods=['GET'])
@jwt_required()
def download_template(entity):
    """Download a CSV or XLSX template for the given entity."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    if entity not in ENTITY_DEFINITIONS:
        return jsonify({'error': f'Entidad desconocida: {entity}'}), 400
    
    fmt = request.args.get('format', 'csv').lower()
    
    try:
        if fmt == 'xlsx':
            content = generate_xlsx_template(entity)
            return Response(
                content=content,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={
                    'Content-Disposition': f'attachment; filename="template_{entity}.xlsx"',
                    'Content-Length': str(len(content)),
                }
            )
        else:
            content = generate_csv_template(entity)
            return Response(
                content=content,
                media_type='text/csv; charset=utf-8',
                headers={
                    'Content-Disposition': f'attachment; filename="template_{entity}.csv"',
                    'Content-Length': str(len(content)),
                }
            )
    except ImportError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"[Ingestion] Template generation error for {entity}: {e}")
        return jsonify({'error': 'Error generando template'}), 500


@ingestion_bp.route('/upload/<entity>', methods=['POST'])
@jwt_required()
def upload_bulk(entity):
    """Upload a CSV or XLSX file for bulk import of the given entity."""
    user, company = _get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    if entity not in ENTITY_DEFINITIONS:
        return jsonify({'error': f'Entidad desconocida: {entity}'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo. Usa el campo "file" en el form-data.'}), 400
    
    uploaded_file = request.files['file']
    filename = uploaded_file.filename or 'upload.csv'
    
    # Extension check
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': f'Tipo de archivo no soportado: {ext}. Usa .csv o .xlsx'}), 400
    
    # Read file content
    try:
        uploaded_file._upload_file.file.seek(0)
        file_content = uploaded_file._upload_file.file.read()
    except Exception:
        try:
            import tempfile, os
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            uploaded_file.save(tmp.name)
            tmp.close()
            with open(tmp.name, 'rb') as f:
                file_content = f.read()
            os.unlink(tmp.name)
        except Exception as e:
            return jsonify({'error': f'Error leyendo el archivo: {str(e)}'}), 500
    
    # File size check: max 10MB
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_size:
        return jsonify({'error': 'El archivo excede el tamaño máximo de 10MB'}), 413
    
    try:
        result = process_upload(file_content, filename, entity, company.id)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except ImportError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"[Ingestion] Upload error for {entity}: {e}")
        return jsonify({'error': f'Error durante la importación: {str(e)}'}), 500
    
    entity_label = ENTITY_DEFINITIONS[entity]['label']
    logger.info(f"User {user.email} bulk imported {result['imported']} {entity} records for company {company.id}")
    
    return jsonify({
        'message': f'Importación completada para {entity_label}',
        'data': result
    }), 200
