"""
Message Audit Model - Transparent RAG Auditing
"""
from datetime import datetime
from extensions import db

class MessageAudit(db.Model):
    """Stores the specific Pinecone chunk IDs used by the LLM for a given message"""
    __tablename__ = 'message_audits'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # RAG specific data
    pinecone_chunk_ids = db.Column(db.JSON, nullable=False, default=list)
    rag_metadata = db.Column(db.JSON, nullable=True, default=dict)
    
    # Relationships
    message = db.relationship('Message', back_populates='audit', uselist=False)
    company = db.relationship('Company', backref=db.backref('message_audits', lazy='dynamic'))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'company_id': self.company_id,
            'pinecone_chunk_ids': self.pinecone_chunk_ids,
            'rag_metadata': self.rag_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<MessageAudit {self.id} for Message {self.message_id}>'

from sqlalchemy import event
from models.conversation import Message, MessageRole
from routing import g

@event.listens_for(Message, 'after_insert')
def after_message_insert(mapper, connection, target):
    """Automatically create an audit record if RAG chunks were used"""
    if target.role == MessageRole.ASSISTANT:
        rag_chunks = getattr(g, 'last_rag_chunks', None)
        if rag_chunks:
            company = getattr(g, 'current_company', None)
            company_id = company.id if company else None
            
            if not company_id:
                # Fallback to query
                res = connection.execute(
                    db.text("SELECT company_id FROM conversations WHERE id = :conv_id"),
                    {"conv_id": target.conversation_id}
                ).first()
                if res:
                    company_id = res[0]
            
            if company_id:
                connection.execute(
                    MessageAudit.__table__.insert().values(
                        message_id=target.id,
                        company_id=company_id,
                        pinecone_chunk_ids=rag_chunks,
                        rag_metadata={}
                    )
                )
            # Clear for the next message
            g.last_rag_chunks = []
