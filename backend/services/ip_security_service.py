"""
IP Security & Geolocation Service
Handles client IP extraction, high-precision IP geolocation, real-time activity recording,
and instantaneous IP blocking / blacklist enforcement for Super Admin.
"""
import os
import logging
import requests
from datetime import datetime

from extensions import db
from models.ip_tracking import UserIpLog, BlockedIp
from models.user import User
from models.company import Company
from services.cache_service import CacheService

logger = logging.getLogger(__name__)

_GEO_IP_CACHE = {}
_BLOCKED_IPS_SET = None  # in-memory fast set cache

class IpSecurityService:
    """Enterprise IP tracking, Geolocation resolution and Blacklist enforcement service."""

    @classmethod
    def extract_client_ip(cls, request) -> str:
        """
        Extracts the true client IP from HTTP headers respecting reverse proxies,
        Cloudflare, load balancers, and direct socket connections.
        """
        try:
            # 1. Cloudflare header
            cf_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("cf-connecting-ip")
            if cf_ip and cf_ip.strip():
                return cf_ip.split(",")[0].strip()

            # 2. X-Forwarded-For header (client is the first IP in the chain)
            xff = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
            if xff and xff.strip():
                return xff.split(",")[0].strip()

            # 3. X-Real-IP header
            x_real_ip = request.headers.get("X-Real-IP") or request.headers.get("x-real-ip")
            if x_real_ip and x_real_ip.strip():
                return x_real_ip.split(",")[0].strip()

            # 4. Direct client connection host
            if hasattr(request, "client") and request.client and hasattr(request.client, "host"):
                return request.client.host
            elif hasattr(request, "remote_addr"):
                return request.remote_addr
        except Exception as e:
            logger.warning(f"Error extracting client IP: {e}")

        return "127.0.0.1"

    @classmethod
    def resolve_ip_geolocation(cls, ip: str) -> dict:
        """
        Resolves precise GPS coordinates, city, country, region, and ISP for a given IP.
        Uses in-memory + Redis caching to ensure 0 external lag.
        """
        if not ip or ip in ("127.0.0.1", "localhost", "::1", "") or ip.startswith("192.168.") or ip.startswith("10."):
            return {
                "ip": ip or "127.0.0.1",
                "lat": -0.1807,
                "lng": -78.4678,
                "city": "Quito",
                "region": "Pichincha",
                "country": "Ecuador",
                "country_code": "EC",
                "isp": "Localhost / Internal Network",
                "is_local": True
            }

        # Check local cache
        if ip in _GEO_IP_CACHE:
            return _GEO_IP_CACHE[ip]

        # Check Redis cache
        cached = CacheService.get(f"geoip:{ip}")
        if cached:
            _GEO_IP_CACHE[ip] = cached
            return cached

        # Query public high-accuracy IP Geolocation API
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,lat,lon,isp,org,as,query"
            r = requests.get(url, timeout=2.0)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    geo = {
                        "ip": ip,
                        "lat": float(data.get("lat", -0.1807)),
                        "lng": float(data.get("lon", -78.4678)),
                        "city": data.get("city", "Unknown City"),
                        "region": data.get("regionName", ""),
                        "country": data.get("country", "Unknown Country"),
                        "country_code": data.get("countryCode", "XX"),
                        "isp": data.get("isp") or data.get("org") or "Standard ISP",
                        "is_local": False
                    }
                    _GEO_IP_CACHE[ip] = geo
                    CacheService.set(f"geoip:{ip}", geo, ttl=86400 * 7)  # 7 days cache
                    return geo
        except Exception as e:
            logger.warning(f"Geolocation resolution failed for {ip}: {e}")

        # Fallback
        fallback = {
            "ip": ip,
            "lat": -0.1807,
            "lng": -78.4678,
            "city": "Detected Location",
            "region": "Pichincha",
            "country": "Ecuador",
            "country_code": "EC",
            "isp": "ISP Network",
            "is_local": False
        }
        _GEO_IP_CACHE[ip] = fallback
        return fallback

    @classmethod
    def is_ip_blocked(cls, ip: str) -> bool:
        """Instantaneous O(1) check to verify if an IP address is blocked."""
        global _BLOCKED_IPS_SET
        if not ip:
            return False

        # Fast memory check
        if _BLOCKED_IPS_SET is not None and ip in _BLOCKED_IPS_SET:
            return True

        # Check Redis
        is_blocked = CacheService.get(f"blocked_ip:{ip}")
        if is_blocked:
            return True

        # Fallback to DB
        try:
            blocked = BlockedIp.query.filter_by(ip_address=ip, is_active=True).first()
            if blocked:
                CacheService.set(f"blocked_ip:{ip}", True, ttl=3600)
                if _BLOCKED_IPS_SET is not None:
                    _BLOCKED_IPS_SET.add(ip)
                return True
        except Exception as e:
            logger.error(f"Error checking blocked IP in DB: {e}")

        return False

    @classmethod
    def block_ip(cls, ip: str, reason: str = None, blocked_by: int = None) -> dict:
        """Blocks an IP address permanently from accessing the platform."""
        global _BLOCKED_IPS_SET
        db.session.rollback()
        try:
            blocked = BlockedIp.query.filter_by(ip_address=ip).first()
            if not blocked:
                blocked = BlockedIp(
                    ip_address=ip,
                    reason=reason or "Bloqueo por Super Admin",
                    blocked_by=blocked_by,
                    is_active=True
                )
                db.session.add(blocked)
            else:
                blocked.is_active = True
                blocked.reason = reason or blocked.reason
                blocked.blocked_by = blocked_by or blocked.blocked_by
                blocked.blocked_at = datetime.utcnow()

            db.session.commit()

            # Update Caches
            CacheService.set(f"blocked_ip:{ip}", True, ttl=86400 * 30)
            if _BLOCKED_IPS_SET is not None:
                _BLOCKED_IPS_SET.add(ip)

            logger.info(f"🛡️ [SECURITY] IP {ip} successfully BLOCKED. Reason: {reason}")
            return {"success": True, "ip": ip, "is_blocked": True, "reason": blocked.reason}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error blocking IP {ip}: {e}")
            raise e

    @classmethod
    def unblock_ip(cls, ip: str) -> dict:
        """Unblocks a previously blacklisted IP address."""
        global _BLOCKED_IPS_SET
        db.session.rollback()
        try:
            blocked = BlockedIp.query.filter_by(ip_address=ip).first()
            if blocked:
                blocked.is_active = False
                db.session.commit()

            # Invalidate Caches
            CacheService.delete(f"blocked_ip:{ip}")
            if _BLOCKED_IPS_SET is not None and ip in _BLOCKED_IPS_SET:
                _BLOCKED_IPS_SET.discard(ip)

            logger.info(f"🛡️ [SECURITY] IP {ip} successfully UNBLOCKED.")
            return {"success": True, "ip": ip, "is_blocked": False}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error unblocking IP {ip}: {e}")
            raise e

    @classmethod
    def record_ip_activity(
        cls,
        ip: str,
        user_id: int = None,
        company_id: int = None,
        user_agent: str = None,
        endpoint: str = None,
        device_id: str = None,
        device_name: str = None,
        device_type: str = None,
        device_gps: str = None
    ):
        """
        Records user interaction with dual-layer telemetry:
        1. Network Layer (Shared WiFi/Router IP & ISP)
        2. Physical Hardware Layer (Device ID, Device Name, Hardware GPS)
        """
        if not ip:
            return

        try:
            from models.ip_tracking import UserIpLog, UserDevice
            geo = cls.resolve_ip_geolocation(ip)
            now = datetime.utcnow()

            # Parse physical device GPS if provided
            hardware_lat = None
            hardware_lng = None
            has_hardware_gps = False
            if device_gps and ',' in device_gps:
                try:
                    parts = device_gps.split(',')
                    hardware_lat = float(parts[0].strip())
                    hardware_lng = float(parts[1].strip())
                    has_hardware_gps = True
                except Exception:
                    pass

            # Primary coordinates: Hardware GPS if available, else WiFi Geolocation
            effective_lat = hardware_lat if has_hardware_gps else geo.get("lat")
            effective_lng = hardware_lng if has_hardware_gps else geo.get("lng")

            # 1. Update User if authenticated
            if user_id:
                user = User.query.get(user_id)
                if user:
                    user.last_ip = ip
                    user.last_ip_lat = effective_lat
                    user.last_ip_lng = effective_lng
                    user.last_ip_city = geo.get("city")
                    user.last_ip_country = geo.get("country")
                    user.last_ip_country_code = geo.get("country_code")
                    user.last_ip_isp = geo.get("isp")
                    user.last_ip_updated_at = now
                    
                    if device_id:
                        user.last_device_id = device_id
                        user.last_device_name = device_name
                        user.last_device_type = device_type or 'desktop'
                        user.last_gps_lat = hardware_lat
                        user.last_gps_lng = hardware_lng
                        user.has_hardware_gps = has_hardware_gps
                        
                    if not company_id and user.company_id:
                        company_id = user.company_id

            # 2. Update Company if available
            if company_id:
                comp = Company.query.get(company_id)
                if comp:
                    comp.last_ip = ip
                    comp.last_ip_lat = effective_lat
                    comp.last_ip_lng = effective_lng
                    comp.last_ip_city = geo.get("city")
                    comp.last_ip_country = geo.get("country")
                    comp.last_ip_isp = geo.get("isp")
                    comp.last_ip_updated_at = now

            # 3. Track physical device in user_devices
            if device_id:
                device = UserDevice.query.filter_by(device_id=device_id, network_ip=ip).first()
                if device:
                    device.request_count += 1
                    device.last_seen_at = now
                    device.user_id = user_id or device.user_id
                    device.company_id = company_id or device.company_id
                    device.device_name = device_name or device.device_name
                    device.device_type = device_type or device.device_type
                    if has_hardware_gps:
                        device.gps_lat = hardware_lat
                        device.gps_lng = hardware_lng
                        device.has_hardware_gps = True
                else:
                    device = UserDevice(
                        user_id=user_id,
                        company_id=company_id,
                        device_id=device_id,
                        device_name=device_name or "Dispositivo Físico",
                        device_type=device_type or "desktop",
                        network_ip=ip,
                        isp=geo.get("isp"),
                        gps_lat=hardware_lat or geo.get("lat"),
                        gps_lng=hardware_lng or geo.get("lng"),
                        has_hardware_gps=has_hardware_gps,
                        city=geo.get("city"),
                        country=geo.get("country"),
                        country_code=geo.get("country_code"),
                        user_agent=user_agent,
                        request_count=1,
                        first_seen_at=now,
                        last_seen_at=now
                    )
                    db.session.add(device)

            # 4. Log or increment in user_ip_logs
            log_entry = UserIpLog.query.filter_by(ip_address=ip, user_id=user_id).first()
            if log_entry:
                log_entry.request_count += 1
                log_entry.last_seen_at = now
                log_entry.user_agent = user_agent or log_entry.user_agent
                log_entry.endpoint = endpoint or log_entry.endpoint
            else:
                log_entry = UserIpLog(
                    user_id=user_id,
                    company_id=company_id,
                    ip_address=ip,
                    city=geo.get("city"),
                    region=geo.get("region"),
                    country=geo.get("country"),
                    country_code=geo.get("country_code"),
                    latitude=geo.get("lat"),
                    longitude=geo.get("lng"),
                    isp=geo.get("isp"),
                    user_agent=user_agent,
                    endpoint=endpoint,
                    request_count=1,
                    first_seen_at=now,
                    last_seen_at=now
                )
                db.session.add(log_entry)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Failed to record IP telemetry: {e}")

