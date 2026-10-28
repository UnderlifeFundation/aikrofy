"""
Document Model - RAG documents and vector memory
"""
from datetime import datetime
from enum import Enum
from extensions import db


class DocumentType(str, Enum):
    PDF = 'pdf'
    DOCX = 'docx'
    TXT = 'txt'
    CSV = 'csv'
    XLSX = 'xlsx'
    URL = 'url'


class DocumentStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    INDEXED = 'indexed'
    ERROR = 'error'


class Document(db.Model):
    """RAG document for vector memory"""
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    # Department-level RAG containment (optional — if set, document is indexed
    # to the department's isolated Pinecone namespace instead of the global one)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

    # File Info
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.Enum(DocumentType), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # bytes
    file_path = db.Column(db.String(512), nullable=True)
    
    # Content
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Pinecone Reference
    pinecone_ids = db.Column(db.JSON, default=list)  # List of vector IDs
    chunk_count = db.Column(db.Integer, default=0)
    
    # Processing Status
    status = db.Column(db.Enum(DocumentStatus), default=DocumentStatus.PENDING)
    error_message = db.Column(db.Text, nullable=True)
    
    # Metadata
    doc_metadata = db.Column(db.JSON, default=dict)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    company = db.relationship('Company', back_populates='documents')
    department = db.relationship(
        'Department',
        foreign_keys=[department_id],
        backref=db.backref('documents', lazy='dynamic'),
    )

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'company_id': self.company_id,
            'department_id': self.department_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type.value,
            'file_size': self.file_size,
            'title': self.title,
            'description': self.description,
            'chunk_count': self.chunk_count,
            'status': self.status.value,
            'error_message': self.error_message,
            'doc_metadata': self.doc_metadata,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }
    
    def __repr__(self):
        return f'<Document {self.filename}>'
