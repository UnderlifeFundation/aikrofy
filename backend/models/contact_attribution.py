"""
ContactAttribution Model - Stores traffic source, campaign, and referral details for customers.
Also handles web session tracking for Google Ads (GCLID) reference mappings.
"""
from datetime import datetime
from extensions import db


class ContactAttribution(db.Model):
    """UTM tracking and referral details (One-to-Many/One-to-One with Customer)."""
    __tablename__ = 'contact_attributions'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)

    # Standard UTM parameters
    utm_source = db.Column(db.String(100), nullable=True)
    utm_medium = db.Column(db.String(100), nullable=True)
    utm_campaign = db.Column(db.String(100), nullable=True)
    utm_term = db.Column(db.String(100), nullable=True)
    utm_content = db.Column(db.String(100), nullable=True)

    # Ad Click Identifiers
    meta_click_id = db.Column(db.String(255), nullable=True)  # ctwa_clid / fbclid
    google_click_id = db.Column(db.String(255), nullable=True)  # gclid

    # Full referral dump from webhooks or external pages
    referral_data = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('attributions', lazy='dynamic', cascade='all, delete-orphan'))
    customer = db.relationship('Customer', backref=db.backref('attributions', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'customer_id': self.customer_id,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'utm_term': self.utm_term,
            'utm_content': self.utm_content,
            'meta_click_id': self.meta_click_id,
            'google_click_id': self.google_click_id,
            'referral_data': self.referral_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ContactAttribution source={self.utm_source} campaign={self.utm_campaign} customer={self.customer_id}>'


class WebReferralSession(db.Model):
    """Temporary web session mapping for GCLID and offline conversion tracking."""
    __tablename__ = 'web_referral_sessions'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    reference_id = db.Column(db.String(50), nullable=False, unique=True, index=True)  # REF-9821
    
    utm_source = db.Column(db.String(100), nullable=True)
    utm_medium = db.Column(db.String(100), nullable=True)
    utm_campaign = db.Column(db.String(100), nullable=True)
    utm_term = db.Column(db.String(100), nullable=True)
    utm_content = db.Column(db.String(100), nullable=True)
    
    google_click_id = db.Column(db.String(255), nullable=True)  # gclid
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    company = db.relationship('Company', backref=db.backref('web_referral_sessions', lazy='dynamic', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'reference_id': self.reference_id,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.utm_campaign,
            'utm_term': self.utm_term,
            'utm_content': self.utm_content,
            'google_click_id': self.google_click_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<WebReferralSession ref={self.reference_id} company={self.company_id}>'
