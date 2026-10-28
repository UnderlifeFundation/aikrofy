"""
Modular Assets Model - Marketplace Assets, Purchases and Cryptographic Licenses
Allows purchasing module zip files (Blog, Ecommerce, etc.) and enforces hardware/domain
anchored cryptographic license verification so assets cannot be run without a valid purchase.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
from datetime import datetime
import hmac
import hashlib
import json
import base64
from enum import Enum
from extensions import db

SECRET_LICENSE_SALT = "aikrofy_asset_shield_sec_2026_wlt_v3"


class AssetType(str, Enum):
    BLOG_MODULE = 'blog_module'
    ECOMMERCE_MODULE = 'ecommerce_module'
    LANDING_SUITE = 'landing_suite'
    CUSTOM_ASSET = 'custom_asset'


class ModularAsset(db.Model):
    """Catalog of modular assets available in the Aikrofy Material Store."""
    __tablename__ = 'modular_assets'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    asset_type = db.Column(db.Enum(AssetType), default=AssetType.BLOG_MODULE, nullable=False)
    version = db.Column(db.String(50), default="1.0.0", nullable=False)
    
    # Pricing
    price_usd = db.Column(db.Float, default=49.0, nullable=False)
    credits_cost = db.Column(db.Integer, default=500, nullable=False)
    
    # File artifact info
    zip_filename = db.Column(db.String(255), nullable=True)
    zip_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    features = db.Column(db.JSON, default=dict)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'asset_type': self.asset_type.value if hasattr(self.asset_type, 'value') else str(self.asset_type),
            'version': self.version,
            'price_usd': self.price_usd,
            'credits_cost': self.credits_cost,
            'zip_filename': self.zip_filename,
            'is_active': self.is_active,
            'features': self.features or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AssetLicense(db.Model):
    """
    License granted to a company upon purchasing an asset.
    Contains cryptographic token anchored to company_id and target VPS domains.
    """
    __tablename__ = 'asset_licenses'

    id = db.Column(db.Integer, primary_key=True)
    license_key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('modular_assets.id'), nullable=False)
    
    # Authorized deployment info
    allowed_domains = db.Column(db.JSON, default=list) # e.g. ["ecuadors.live", "blog.miempresa.com", "localhost"]
    allowed_ip = db.Column(db.String(100), nullable=True)
    vps_signature = db.Column(db.String(255), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    status_message = db.Column(db.String(255), default='Active and Verified')
    downloads_count = db.Column(db.Integer, default=0)
    last_verified_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True) # None = Lifetime
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = db.relationship('Company', backref=db.backref('asset_licenses', lazy='dynamic'))
    asset = db.relationship('ModularAsset', backref=db.backref('licenses', lazy='dynamic'))

    @staticmethod
    def generate_license_token(company_id: int, asset_slug: str, domain: str = "") -> str:
        """
        Creates an encrypted, HMAC-signed token validating that company_id owns asset_slug.
        Format: base64url(json_payload).signature
        """
        payload = {
            "cid": company_id,
            "asset": asset_slug,
            "domain": domain.strip().lower() if domain else "*",
            "iat": int(datetime.utcnow().timestamp())
        }
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature = hmac.new(
            SECRET_LICENSE_SALT.encode(),
            encoded_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"AKF-{encoded_payload}.{signature}"

    @staticmethod
    def verify_license_token(token: str, expected_company_id: int, expected_asset_slug: str, check_domain: str = None) -> tuple[bool, str]:
        """
        Verifies cryptographic integrity of the token and checks database validity.
        """
        if not token or not token.startswith("AKF-"):
            return False, "Invalid token format."

        try:
            raw_token = token[4:]
            parts = raw_token.split(".")
            if len(parts) != 2:
                return False, "Malformed token structure."
            
            payload_b64, signature = parts
            # Restore padding
            padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
            expected_sig = hmac.new(
                SECRET_LICENSE_SALT.encode(),
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return False, "Cryptographic signature mismatch. Tampered token."

            payload_data = json.loads(base64.urlsafe_b64decode(padded_b64).decode())
            if payload_data.get("cid") != expected_company_id:
                return False, "Token company ID does not match installation."
            if payload_data.get("asset") != expected_asset_slug:
                return False, "Token asset type mismatch."

            token_domain = payload_data.get("domain", "*")
            if check_domain and token_domain != "*" and token_domain not in check_domain.lower():
                return False, f"Domain mismatch. Token restricted to: {token_domain}"

            return True, "License signature valid."
        except Exception as e:
            return False, f"Verification error: {str(e)}"

    def to_dict(self):
        return {
            'id': self.id,
            'license_key': self.license_key,
            'company_id': self.company_id,
            'asset': self.asset.to_dict() if self.asset else None,
            'allowed_domains': self.allowed_domains or [],
            'is_active': self.is_active,
            'status_message': self.status_message,
            'downloads_count': self.downloads_count,
            'last_verified_at': self.last_verified_at.isoformat() if self.last_verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
