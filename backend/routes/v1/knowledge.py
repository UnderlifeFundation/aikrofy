"""
V1 Public API - Knowledge Base Router
Provides external/developer access to PymAI RAG knowledge base via API key auth.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/v1/knowledge', tags=['V1 - Knowledge Base'])

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class KnowledgeQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    include_global: bool = True


# ── Auth Dependency ───────────────────────────────────────────────────────────

def get_company_from_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Validate X-API-Key header and return the associated Company."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail='Missing X-API-Key header.')

    from database import db_session
    from models.company import Company

    companies = db_session.query(Company).filter(Company.api_keys.isnot(None)).all()
    for company in companies:
        if company.api_keys and company.api_keys.get('public_api_key') == x_api_key:
            return company

    raise HTTPException(status_code=401, detail='Invalid API key.')


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post('/query')
def query_knowledge(body: KnowledgeQueryRequest, x_api_key: Optional[str] = Header(default=None)):
    """
    Query the RAG knowledge base for the authenticated company.

    - **query**: Natural-language question to search.
    - **top_k**: Maximum number of results to return (default 5).
    - **include_global**: Whether to also query the global PymAI knowledge namespace.
    """
    company = get_company_from_api_key(x_api_key)

    try:
        from services.rag_service import RAGService

        company_results = RAGService.query(
            company_id=company.id,
            query=body.query,
            top_k=body.top_k,
            namespace=company.pinecone_namespace,
        )

        global_results = []
        if body.include_global:
            try:
                global_results = RAGService.query(
                    company_id=None,
                    query=body.query,
                    top_k=body.top_k,
                    namespace='global',
                )
            except Exception as eg:
                logger.warning(f'Global namespace query failed (non-fatal): {eg}')

        combined = company_results + global_results

    except Exception as e:
        logger.error(f'RAG query error for company {company.id}: {e}')
        raise HTTPException(status_code=500, detail=f'RAG query failed: {str(e)}')

    return {
        'company_id': company.id,
        'query': body.query,
        'results': combined,
        'total': len(combined),
    }


@router.post('/ingest')
async def ingest_document(
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Ingest a text document into the company's RAG knowledge base.

    Reads the uploaded file as UTF-8 text, creates a Document record,
    indexes it via RAGService, and returns the chunk count.
    """
    company = get_company_from_api_key(x_api_key)

    try:
        raw_bytes = await file.read()
        text_content = raw_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Could not read file: {str(e)}')

    try:
        from database import db_session
        from models.document import Document
        from services.rag_service import RAGService

        doc = Document(
            company_id=company.id,
            name=file.filename or 'uploaded_document',
            content=text_content,
            source='v1_api_ingest',
        )
        db_session.add(doc)
        db_session.flush()  # get doc.id before indexing

        chunks_count = RAGService.index_document(
            company_id=company.id,
            document_id=doc.id,
            content=text_content,
            namespace=company.pinecone_namespace,
        )

        db_session.commit()

    except Exception as e:
        logger.error(f'Ingest error for company {company.id}: {e}')
        try:
            db_session.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f'Ingest failed: {str(e)}')

    return {
        'success': True,
        'document_id': doc.id,
        'filename': file.filename,
        'chunks_indexed': chunks_count,
        'message': 'Document ingested and indexed successfully.',
    }
