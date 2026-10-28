from routing import APIRouter, copy_current_request_context, current_app, get_jwt_identity, jsonify, jwt_required, request
"""
RAG Document Management Routes
"""
import os
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


from werkzeug.utils import secure_filename
from extensions import db
from models.user import User, UserRole
from models.document import Document, DocumentType, DocumentStatus

rag_bp = APIRouter('rag', __name__)

# Thread pool for background document processing
# max_workers=3 limits concurrent processing to avoid overloading
document_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix='rag_processor')


def get_user_company():
    """Helper to get current user's company"""
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            print(f"DEBUG: RAG - User {user_id} not found")
            return None
        if user.company:
            return user.company
        if user.role == UserRole.SUPER_ADMIN:
            from models.company import Company
            return Company.query.filter(Company.name.ilike('%aikrofy%')).first() or Company.query.get(1)
        print(f"DEBUG: RAG - User {user.id} has no company")
        return None
    except Exception as e:
        print(f"DEBUG: RAG - Error getting company: {e}")
        return None


ALLOWED_RAG_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'txt', 'md', 'markdown', 'csv', 'json', 'xlsx', 'xls',
    'mp3', 'wav', 'ogg', 'm4a', 'opus', 'aac', 'webm', 'oga', 'flac'
}

AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a', 'opus', 'aac', 'webm', 'oga', 'flac'}

EXTENSION_TO_DOCTYPE = {
    'pdf': DocumentType.PDF,
    'docx': DocumentType.DOCX,
    'doc': DocumentType.DOCX,
    'txt': DocumentType.TXT,
    'md': DocumentType.TXT,
    'markdown': DocumentType.TXT,
    'csv': DocumentType.CSV,
    'json': DocumentType.TXT,
    'xlsx': DocumentType.XLSX,
    'xls': DocumentType.XLSX,
    'mp3': DocumentType.TXT,
    'wav': DocumentType.TXT,
    'ogg': DocumentType.TXT,
    'm4a': DocumentType.TXT,
    'opus': DocumentType.TXT,
    'aac': DocumentType.TXT,
    'webm': DocumentType.TXT,
    'oga': DocumentType.TXT,
    'flac': DocumentType.TXT,
}


def allowed_file(filename):
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    config_allowed = current_app.config.get('ALLOWED_EXTENSIONS') or ALLOWED_RAG_EXTENSIONS
    return ext in config_allowed or ext in ALLOWED_RAG_EXTENSIONS


@rag_bp.route('', methods=['GET'])
@rag_bp.route('/documents', methods=['GET'])
@jwt_required()
def list_documents():
    """
    List RAG documents.
    - Super Admin: lists global docs (company_id IS NULL)
    - Others: list their company's docs
    """
    from models.user import UserRole
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if user.role == UserRole.SUPER_ADMIN:
            documents = Document.query.filter(Document.company_id.is_(None)).order_by(Document.uploaded_at.desc()).all()
        else:
            if not user.company_id:
                return jsonify({'error': 'Company not found'}), 404
            documents = Document.query.filter_by(company_id=user.company_id).order_by(Document.uploaded_at.desc()).all()
            
        return jsonify({'data': [d.to_dict() for d in documents]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def extract_text_content(file_path: str, file_type: str, title: str = None) -> str:
    """
    Extract text content from file.
    Supports: TXT, MD, MARKDOWN, CSV, JSON, PDF, DOCX, XLSX, and Audio (MP3, WAV, OGG, M4A, WEBM, OPUS, AAC, FLAC).
    Uses VoiceService for audio transcription (media.weblifetech.com cascade).
    """
    try:
        ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else file_type.lower()
        
        # Audio file transcription to Markdown
        if ext in AUDIO_EXTENSIONS:
            from services.voice_service import VoiceService
            print(f"🎙️ Transcribing audio file: {file_path} via VoiceService...")
            transcription = VoiceService.transcribe(file_path)
            if not transcription or not transcription.strip():
                print(f"⚠️ Warning: Audio transcription returned empty for {file_path}")
                return None
            
            clean_title = title or os.path.basename(file_path).rsplit('.', 1)[0].replace('_', ' ')
            md_content = f"# Transcripción de Audio: {clean_title}\n\n" \
                         f"- **Archivo Original:** {os.path.basename(file_path)}\n" \
                         f"- **Formato:** {ext.upper()}\n" \
                         f"- **Fecha:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n" \
                         f"---\n\n" \
                         f"## Contenido Transcrito:\n\n{transcription.strip()}\n"
            return md_content

        if ext in ('txt', 'md', 'markdown', 'json') or file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        elif ext == 'csv' or file_type == 'csv':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        elif ext == 'pdf' or file_type == 'pdf':
            from pdfminer.high_level import extract_text
            return extract_text(file_path)
            
        elif ext in ('docx', 'doc') or file_type == 'docx':
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return '\n'.join(paragraphs)

        elif ext in ('xlsx', 'xls') or file_type == 'xlsx':
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            lines = []
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                lines.append(f"--- Sheet: {sheet} ---")
                for row in ws.iter_rows(values_only=True):
                    row_vals = [str(v) if v is not None else '' for v in row]
                    if any(row_vals):
                        lines.append(" | ".join(row_vals))
            return '\n'.join(lines)
            
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
            
    except Exception as e:
        print(f"Error extracting text from {file_type} ({file_path}): {e}")
        return None


def process_document_sync(document_id: int, company_id: int, app=None):
    """
    Process document and index to Pinecone - Background thread safe.
    Creates its own app context for database operations if available.
    
    Args:
        document_id: ID of the document to process
        company_id: ID of the company (for RAG namespace)
        app: Optional application instance for context
    """
    from services.rag_service import RAGService
    from models.company import Company
    
    def _run_processing():
        try:
            db.session.rollback()
            # Fetch fresh instances within this context
            document = Document.query.get(document_id)
            company = Company.query.get(company_id) if company_id else None
            
            if not document or not company:
                print(f"Document {document_id} or Company {company_id} not found")
                return False
            
            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            db.session.commit()
            
            # Extract text content (handles text, pdf, docx, excel, csv, markdown, and audio transcription)
            content = extract_text_content(document.file_path, document.file_type.value, document.title)
            
            if not content:
                document.status = DocumentStatus.ERROR
                document.error_message = f"Could not extract or transcribe text from {document.file_type.value} file. Supported: TXT, MD, CSV, PDF, DOCX, XLSX, and Audio (MP3, WAV, OGG, M4A, WEBM)."
                db.session.commit()
                return False
            
            if len(content.strip()) < 10:
                document.status = DocumentStatus.ERROR
                document.error_message = "Document content is too short"
                db.session.commit()
                return False
            
            # Initialize RAG service with company context
            rag_service = RAGService(company)
            
            # Index document to Pinecone
            # If document has a department, use that namespace for containment
            metadata = {
                'title': document.title,
                'filename': document.original_filename,
                'file_type': document.file_type.value
            }
            if document.department_id:
                metadata['department_id'] = document.department_id
            
            # Use department namespace if set, otherwise use company namespace
            original_get_namespace = rag_service._get_namespace
            dept_ns = rag_service._get_namespace(department_id=document.department_id)
            
            vector_ids = rag_service.index_document(
                document_id=document.id,
                content=content,
                metadata=metadata
            )
            
            # Update document record
            document.pinecone_ids = vector_ids
            document.chunk_count = len(vector_ids)
            document.status = DocumentStatus.INDEXED
            document.processed_at = datetime.utcnow()
            document.error_message = None
            db.session.commit()
            
            print(f"✓ Document {document_id} indexed successfully ({len(vector_ids)} chunks)")
            return True
            
        except Exception as e:
            try:
                document = Document.query.get(document_id)
                if document:
                    document.status = DocumentStatus.ERROR
                    document.error_message = str(e)[:500]
                    db.session.commit()
            except Exception:
                pass
            print(f"✗ Error processing document {document_id}: {e}")
            return False

    if app and hasattr(app, 'app_context'):
        with app.app_context():
            return _run_processing()
    return _run_processing()


@rag_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_document():
    """Upload a document for RAG processing (async)"""
    from models.user import UserRole
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        is_super_admin = user.role == UserRole.SUPER_ADMIN
        company_id = None if is_super_admin else user.company_id
        
        if not is_super_admin and not company_id:
            return jsonify({'error': 'Company not found'}), 404
            
        # Check document quota based on subscription plan
        if not is_super_admin and user.company and user.company.subscription and user.company.subscription.plan:
            is_courtesy = user.company.subscription.status.value == 'courtesy'
            if not is_courtesy:
                plan_features = user.company.subscription.plan.features or {}
                max_documents = plan_features.get('max_documents', 10)
                current_docs = Document.query.filter_by(company_id=company_id).count()
                if current_docs >= max_documents:
                    return jsonify({
                        'error': f'Subscription limit reached. Your plan allows up to {max_documents} documents.'
                    }), 403
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{extension}"
        
        # Create upload directory
        folder_name = 'global' if is_super_admin else str(company_id)
        base_upload = current_app.config.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
        upload_dir = os.path.join(base_upload, folder_name)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        doc_type = EXTENSION_TO_DOCTYPE.get(extension, DocumentType.TXT)
        
        dept_raw = request.form.get('department_id')
        dept_id = int(dept_raw) if (dept_raw is not None and str(dept_raw).isdigit()) else None

        document = Document(
            company_id=company_id,
            department_id=dept_id,
            filename=unique_filename,
            original_filename=original_filename,
            file_type=doc_type,
            file_size=file_size,
            file_path=file_path,
            title=request.form.get('title', original_filename),
            description=request.form.get('description'),
            status=DocumentStatus.PENDING,
            doc_metadata={'is_voice': extension in AUDIO_EXTENSIONS or request.form.get('is_voice_note') == 'true', 'format': extension}
        )
        db.session.add(document)
        db.session.commit()
        
        doc_id = document.id
        app = current_app._get_current_object()
        
        document_executor.submit(process_document_sync, doc_id, company_id, app)
        
        return jsonify({
            'message': 'Document uploaded, processing in background',
            'data': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@rag_bp.route('/upload-voice', methods=['POST'])
@jwt_required()
def upload_voice_note():
    """
    Dedicated endpoint for uploading audio files or browser recorded voice notes.
    Transcribes audio to text (.md) and stores in Pinecone RAG memory.
    """
    return upload_document()


@rag_bp.route('/<int:document_id>', methods=['GET'])
@rag_bp.route('/documents/<int:document_id>', methods=['GET'])
@jwt_required()
def get_document(document_id):
    """Get document details"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if user.role == 'super_admin':
        document = Document.query.filter_by(id=document_id).first()
    else:
        document = Document.query.filter_by(id=document_id, company_id=user.company_id).first()
        
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    return jsonify({'document': document.to_dict()})


@rag_bp.route('/<int:document_id>', methods=['PUT'])
@rag_bp.route('/documents/<int:document_id>', methods=['PUT'])
@jwt_required()
def update_document(document_id):
    """Update document metadata"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if user.role == 'super_admin':
        document = Document.query.filter_by(id=document_id).first()
    else:
        document = Document.query.filter_by(id=document_id, company_id=user.company_id).first()
        
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    data = request.get_json()
    if 'title' in data:
        document.title = data['title']
    if 'description' in data:
        document.description = data['description']
    
    db.session.commit()
    return jsonify({'message': 'Document updated', 'document': document.to_dict()})


@rag_bp.route('/<int:document_id>', methods=['DELETE'])
@rag_bp.route('/documents/<int:document_id>', methods=['DELETE'])
@jwt_required()
def delete_document(document_id):
    """Delete a document"""
    from models.user import UserRole
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    is_super_admin = user.role == UserRole.SUPER_ADMIN
    if is_super_admin:
        document = Document.query.filter_by(id=document_id, company_id=None).first()
    else:
        document = Document.query.filter_by(id=document_id, company_id=user.company_id).first()
        
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    try:
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete vectors from Pinecone
        try:
            from services.rag_service import RAGService
            # For global docs, company is None
            company = user.company if not is_super_admin else None
            rag_service = RAGService(company)
            rag_service.delete_document(document.id)
        except Exception as e:
            print(f"Warning: Could not delete vectors from Pinecone: {e}")
        
        db.session.delete(document)
        db.session.commit()
        return jsonify({'message': 'Document deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@rag_bp.route('/documents/<int:document_id>/reprocess', methods=['POST'])
@jwt_required()
def reprocess_document(document_id):
    """Reprocess a document for RAG"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    document = Document.query.filter_by(id=document_id, company_id=company.id).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    # Mark as pending for reprocessing
    document.status = DocumentStatus.PENDING
    document.error_message = None
    db.session.commit()
    
    # Get IDs and app for background thread
    doc_id = document.id
    company_id = company.id
    app = current_app._get_current_object()
    
    # Submit to background thread pool (non-blocking)
    document_executor.submit(process_document_sync, doc_id, company_id, app)
    
    return jsonify({
        'message': 'Document queued for reprocessing',
        'document': document.to_dict()
    })


@rag_bp.route('/query', methods=['POST'])
@jwt_required()
def query_documents():
    """Query RAG memory"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    data = request.get_json()
    query = data.get('query', '')
    top_k = data.get('top_k', 5)
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        from services.rag_service import RAGService
        rag_service = RAGService(company)
        results = rag_service.query(query, top_k=top_k)
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'query': query,
            'results': [],
            'error': str(e)
        })


@rag_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_rag_stats():
    """Get RAG statistics"""
    company = get_user_company()
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    total_docs = Document.query.filter_by(company_id=company.id).count()
    indexed_docs = Document.query.filter_by(company_id=company.id, status=DocumentStatus.INDEXED).count()
    pending_docs = Document.query.filter_by(company_id=company.id, status=DocumentStatus.PENDING).count()
    error_docs = Document.query.filter_by(company_id=company.id, status=DocumentStatus.ERROR).count()
    
    total_chunks = db.session.query(db.func.sum(Document.chunk_count)).filter_by(company_id=company.id).scalar() or 0
    
    return jsonify({
        'total_documents': total_docs,
        'indexed_documents': indexed_docs,
        'pending_documents': pending_docs,
        'error_documents': error_docs,
        'total_chunks': total_chunks
    })


@rag_bp.route('/crawl-website', methods=['POST'])
@jwt_required()
def crawl_and_index_website():
    """
    Crawls a website URL (including internal pages and sitemap),
    extracts content, indexes vector chunks into Pinecone, and sets up auto-sync.
    """
    from models.user import UserRole
    from services.website_crawler_service import WebsiteCrawlerService
    
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        is_super_admin = user.role == UserRole.SUPER_ADMIN
        company_id = None if is_super_admin else user.company_id
        
        if not is_super_admin and not company_id:
            return jsonify({'error': 'Company not found'}), 404
            
        data = request.get_json() or {}
        raw_url = data.get('url', '').strip()
        if not raw_url:
            return jsonify({'error': 'URL is required'}), 400
            
        if not raw_url.startswith(('http://', 'https://')):
            raw_url = 'https://' + raw_url
            
        if not WebsiteCrawlerService.is_valid_url(raw_url):
            return jsonify({'error': 'Invalid website URL format'}), 400
            
        title = data.get('title', '').strip() or urlparse(raw_url).netloc
        max_pages = min(int(data.get('max_pages', 25)), 100)
        deep_crawl = bool(data.get('deep_crawl', True))
        auto_sync = bool(data.get('auto_sync', True))
        dept_id = data.get('department_id')
        dept_id = int(dept_id) if dept_id and str(dept_id).isdigit() else None
        
        # Check if already registered
        existing = Document.query.filter_by(
            company_id=company_id,
            original_filename=raw_url,
            file_type=DocumentType.URL
        ).first()
        
        if existing:
            document = existing
            document.status = DocumentStatus.PENDING
            document.title = title
            document.department_id = dept_id
        else:
            document = Document(
                company_id=company_id,
                department_id=dept_id,
                filename=f"web_{uuid.uuid4().hex[:12]}",
                original_filename=raw_url,
                file_type=DocumentType.URL,
                file_size=0,
                file_path=raw_url,
                title=title,
                description=f"Sitio web rastreado: {raw_url}",
                status=DocumentStatus.PENDING,
                doc_metadata={
                    'crawl_url': raw_url,
                    'max_pages': max_pages,
                    'deep_crawl': deep_crawl,
                    'auto_sync': auto_sync,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            db.session.add(document)
            
        db.session.commit()
        doc_id = document.id
        app = current_app._get_current_object()
        
        def _bg_crawl():
            with app.app_context():
                WebsiteCrawlerService.index_website_document(
                    document_id=doc_id,
                    company_id=company_id,
                    max_pages=max_pages,
                    deep_crawl=deep_crawl,
                    auto_sync=auto_sync
                )
                
        document_executor.submit(_bg_crawl)
        
        return jsonify({
            'message': 'Website crawling and vector indexing started in background',
            'data': document.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@rag_bp.route('/sync-website/<int:document_id>', methods=['POST'])
@jwt_required()
def sync_website_document_endpoint(document_id: int):
    """
    On-demand sync: checks the website for changes, updates modified vectors in Pinecone,
    and removes stale embeddings.
    """
    from services.website_crawler_service import WebsiteCrawlerService
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        document = Document.query.get(document_id)
        if not document or document.file_type != DocumentType.URL:
            return jsonify({'error': 'Website document not found'}), 404
            
        if user.role != 'super_admin' and document.company_id != user.company_id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        app = current_app._get_current_object()
        
        def _bg_sync():
            with app.app_context():
                WebsiteCrawlerService.sync_website_document(document_id)
                
        document_executor.submit(_bg_sync)
        
        return jsonify({
            'message': 'Website re-sync initiated in background',
            'document_id': document_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@rag_bp.route('/sync-all-websites', methods=['POST'])
@jwt_required()
def sync_all_websites_endpoint():
    """Trigger synchronization for all active websites with auto_sync enabled"""
    from models.user import UserRole
    from services.website_crawler_service import WebsiteCrawlerService
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != UserRole.SUPER_ADMIN:
            return jsonify({'error': 'Super admin required'}), 403
            
        res = WebsiteCrawlerService.sync_all_active_websites()
        return jsonify(res), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

