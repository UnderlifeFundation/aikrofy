import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.company import Company
from models.document import Document, DocumentStatus, DocumentType
from services.rag_service import RAGService

def import_bos_ai_handbooks():
    app = create_app()
    with app.app_context():
        print("Importing BOS-AI Handbooks into Global RAG Knowledge Base...")
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bos_ai_path = os.path.join(backend_dir, 'BOS-AI', 'agents')
        if not os.path.exists(bos_ai_path):
            bos_ai_path = os.path.join(backend_dir, 'agents')
            if not os.path.exists(bos_ai_path):
                print(f"BOS-AI path not found: {bos_ai_path}")
                return
            
        rag_service = RAGService(None)

        for root, dirs, files in os.walk(bos_ai_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    department = os.path.basename(root)
                    title = f"BOS-AI Handbook: {department.upper()} - {file.replace('.md', '')}"
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check if already imported globally
                    existing = Document.query.filter_by(company_id=None, title=title).first()
                    if existing:
                        print(f"Skipping (already exists globally): {title}")
                        continue

                    # Write content to backend/uploads/global
                    upload_dir = os.path.join(backend_dir, 'uploads', 'global')
                    os.makedirs(upload_dir, exist_ok=True)
                    dest_file_path = os.path.join(upload_dir, file)
                    with open(dest_file_path, 'w', encoding='utf-8') as df:
                        df.write(content)

                    # Create Document in DB
                    doc = Document(
                        company_id=None,
                        filename=file,
                        original_filename=file,
                        file_type=DocumentType.TXT,
                        file_size=len(content.encode('utf-8')),
                        file_path=dest_file_path,
                        title=title,
                        description=f"BOS-AI Handbook: {file}",
                        status=DocumentStatus.INDEXED,
                        doc_metadata={'department': department, 'source': 'BOS-AI'}
                    )
                    db.session.add(doc)
                    db.session.commit()

                    # Index in RAG
                    try:
                        rag_service.index_document(doc.id, content, metadata=doc.doc_metadata)
                        print(f"Successfully indexed globally: {title}")
                    except Exception as e:
                        print(f"Error indexing {title}: {e}")
                        db.session.rollback()

        print("Finished importing BOS-AI Handbooks to RAG.")

if __name__ == "__main__":
    import_bos_ai_handbooks()
