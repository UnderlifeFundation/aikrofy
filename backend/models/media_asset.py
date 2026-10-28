"""
CompanyMediaAsset Model - Media Library for Aikrofy
Stores metadata for images and videos uploaded by companies.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from datetime import datetime
from extensions import db
from sqlalchemy.dialects.mysql import JSON


class MediaAssetType(str):
    IMAGE = 'image'
    VIDEO = 'video'
    AUDIO = 'audio'
    DOCUMENT = 'document'


class CompanyMediaAsset(db.Model):
    """
    Media asset (image, video, document, audio, etc.) uploaded by a company.
    Used for the AI media library: agents can search and send these assets.
    """
    __tablename__ = 'company_media_assets'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey('companies.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # File organization
    folder = db.Column(db.String(255), default='general', nullable=False, index=True)
    filename = db.Column(db.String(500), nullable=False)

    # Public-accessible URL (served via /static/uploads/...)
    file_url = db.Column(db.String(1000), nullable=False)

    # Type: 'image', 'video', 'document', 'audio'
    media_type = db.Column(
        db.String(50),
        nullable=False,
        default='image',
        index=True
    )

    # File info
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    mime_type = db.Column(db.String(100), nullable=True)

    # AI-searchable metadata
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    keywords = db.Column(JSON, default=list, nullable=True)  # ["demo", "producto", "presentación"]

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship(
        'Company',
        backref=db.backref('media_assets', lazy=True, cascade='all, delete-orphan')
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'company_id': self.company_id,
            'folder': self.folder,
            'filename': self.filename,
            'file_url': self.file_url,
            'media_type': self.media_type,
            'size_bytes': self.size_bytes,
            'mime_type': self.mime_type,
            'title': self.title,
            'description': self.description,
            'keywords': self.keywords or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f'<CompanyMediaAsset {self.filename!r} ({self.media_type})>'
