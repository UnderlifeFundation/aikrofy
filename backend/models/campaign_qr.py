"""
Campaign QR Code & Scan Telemetry Models
Provides permanent, multi-tenant QR code management with infinite redirect capabilities,
visual styling presets, and audit-grade scan event tracking.

Integrated with Aikrofy's Multi-Company & Agency isolation architecture.
Copyright © 2026 WEBLIFETECH / AIKROFY. All Rights Reserved.
"""
from datetime import datetime
import uuid
from extensions import db

def generate_short_slug():
    """Generates an 8-character url-safe unique slug."""
    return uuid.uuid4().hex[:8]

class CampaignQRCode(db.Model):
    """
    Campaign QR Code entity strictly bounded to a Company.
    Works as an immutable physical code with dynamic backend redirection.
    """
    __tablename__ = 'campaign_qr_codes'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('company_campaigns.id', ondelete='SET NULL'), nullable=True, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Identifiers & Targeting
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(64), unique=True, index=True, nullable=False, default=generate_short_slug)
    
    # Types: 'url', 'whatsapp', 'telegram', 'form', 'file', 'landing_page', 'vcard'
    target_type = db.Column(db.String(50), default='url', nullable=False)
    target_destination = db.Column(db.Text, nullable=False) # e.g. target URL, https://wa.me/..., etc.
    fallback_destination = db.Column(db.Text, nullable=True) # Used if campaign expired or inactive
    
    # Intended distribution channels: 'omnichannel', 'email', 'whatsapp', 'telegram', 'print', 'web_embed'
    intended_channel = db.Column(db.String(50), default='omnichannel', nullable=False)
    
    # Visual configuration compatible with qr-code-styling from qrcodly
    # Holds: dotsOptions, cornersSquareOptions, cornersDotOptions, image (logo), backgroundOptions, etc.
    visual_config = db.Column(db.JSON, default=dict)
    
    # Status & Life Cycle (Dynamic QR Codes NEVER physically expire)
    is_dynamic = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Aggregated Quick Metrics
    total_scans = db.Column(db.Integer, default=0, nullable=False)
    unique_scans = db.Column(db.Integer, default=0, nullable=False)
    last_scanned_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('campaign_qr_codes', lazy='dynamic', cascade='all, delete-orphan'))
    campaign = db.relationship('CompanyCampaign', backref=db.backref('qr_codes', lazy='dynamic'))
    scan_events = db.relationship('QRCodeScanEvent', backref='qr_code', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, base_redirect_url=""):
        full_short_url = f"{base_redirect_url}/r/{self.slug}" if base_redirect_url else f"/r/{self.slug}"
        return {
            'id': self.id,
            'company_id': self.company_id,
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign.name if self.campaign else None,
            'name': self.name,
            'slug': self.slug,
            'short_url': full_short_url,
            'target_type': self.target_type,
            'target_destination': self.target_destination,
            'fallback_destination': self.fallback_destination,
            'intended_channel': self.intended_channel,
            'visual_config': self.visual_config or {},
            'is_dynamic': self.is_dynamic,
            'is_active': self.is_active,
            'total_scans': self.total_scans,
            'unique_scans': self.unique_scans,
            'last_scanned_at': self.last_scanned_at.isoformat() if self.last_scanned_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class QRCodeScanEvent(db.Model):
    """
    Granular audit telemetries recorded upon scanning a CampaignQRCode.
    Tracks geographic, client agent, channel attribution, and device signatures.
    """
    __tablename__ = 'qr_code_scan_events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    qr_code_id = db.Column(db.String(36), db.ForeignKey('campaign_qr_codes.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('company_campaigns.id', ondelete='SET NULL'), nullable=True, index=True)

    # Telemetry
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    device_type = db.Column(db.String(50), nullable=True) # mobile, desktop, tablet
    os_family = db.Column(db.String(50), nullable=True) # iOS, Android, Windows, macOS, Linux
    browser_family = db.Column(db.String(50), nullable=True) # Chrome, Safari, Firefox, Edge
    
    # Geolocation metadata
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    
    # Inbound attribution
    referrer = db.Column(db.Text, nullable=True)
    utm_source = db.Column(db.String(100), nullable=True)
    utm_medium = db.Column(db.String(100), nullable=True)
    utm_campaign = db.Column(db.String(100), nullable=True)

    scanned_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'qr_code_id': self.qr_code_id,
            'company_id': self.company_id,
            'campaign_id': self.campaign_id,
            'device_type': self.device_type,
            'os_family': self.os_family,
            'browser_family': self.browser_family,
            'country': self.country,
            'city': self.city,
            'referrer': self.referrer,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'scanned_at': self.scanned_at.isoformat() if self.scanned_at else None
        }
