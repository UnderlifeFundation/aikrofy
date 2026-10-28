"""
IP Tracking and Security Models - Real-time IP Geolocation & Blacklist Enforcement
"""
from datetime import datetime
from extensions import db


class UserIpLog(db.Model):
    """Logs IP addresses, precise geolocation, ISP and user agent telemetry."""
    __tablename__ = 'user_ip_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(64), nullable=False, index=True)
    
    # Real-Time Geolocation
    city = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    country_code = db.Column(db.String(10), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    isp = db.Column(db.String(255), nullable=True)
    
    # Telemetry
    user_agent = db.Column(db.Text, nullable=True)
    endpoint = db.Column(db.String(255), nullable=True)
    request_count = db.Column(db.Integer, default=1, nullable=False)
    
    # Timestamps
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'ip_address': self.ip_address,
            'city': self.city,
            'region': self.region,
            'country': self.country,
            'country_code': self.country_code,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'isp': self.isp,
            'user_agent': self.user_agent,
            'endpoint': self.endpoint,
            'request_count': self.request_count,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class BlockedIp(db.Model):
    """Stores permanently or temporarily blocked IP addresses for security enforcement."""
    __tablename__ = 'blocked_ips'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(64), unique=True, nullable=False, index=True)
    reason = db.Column(db.String(255), nullable=True, default='Bloqueo por Super Admin')
    blocked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'ip_address': self.ip_address,
            'reason': self.reason,
            'blocked_by': self.blocked_by,
            'blocked_at': self.blocked_at.isoformat() if self.blocked_at else None,
            'is_active': self.is_active,
        }


class UserDevice(db.Model):
    """
    Physical hardware device telemetry model.
    Tracks individual physical hardware (laptops, phones, tablets) distinct from the shared WiFi IP.
    """
    __tablename__ = 'user_devices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)
    
    # Device Identification
    device_id = db.Column(db.String(100), nullable=False, index=True)
    device_name = db.Column(db.String(255), nullable=True) # e.g. "MacBook Pro (Chrome on macOS)"
    device_type = db.Column(db.String(50), default='desktop', nullable=False) # desktop, mobile, tablet
    
    # Network Layer (WiFi / Shared Router)
    network_ip = db.Column(db.String(64), nullable=False, index=True) # Public WiFi IP
    isp = db.Column(db.String(255), nullable=True)
    
    # GPS Telemetry (Physical Device GPS / HTML5 Geolocation vs IP fallback)
    gps_lat = db.Column(db.Float, nullable=True)
    gps_lng = db.Column(db.Float, nullable=True)
    has_hardware_gps = db.Column(db.Boolean, default=False, nullable=False)
    gps_accuracy = db.Column(db.Float, nullable=True)
    gps_speed = db.Column(db.Float, nullable=True)
    gps_heading = db.Column(db.Float, nullable=True)
    location_consent = db.Column(db.String(50), default='unknown', nullable=True)
    
    city = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    country_code = db.Column(db.String(10), nullable=True)
    
    user_agent = db.Column(db.Text, nullable=True)
    request_count = db.Column(db.Integer, default=1, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'network_ip': self.network_ip,
            'isp': self.isp,
            'gps_lat': self.gps_lat,
            'gps_lng': self.gps_lng,
            'has_hardware_gps': self.has_hardware_gps,
            'location_consent': self.location_consent or 'unknown',
            'city': self.city,
            'country': self.country,
            'country_code': self.country_code,
            'request_count': self.request_count,
            'is_active': self.is_active,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
        }
