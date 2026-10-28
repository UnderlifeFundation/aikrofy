"""
Real-time Device Hardware Telemetry & Uber-Precision Live GPS Tracking Route
"""
import logging
from datetime import datetime
from routing import APIRouter, request, jsonify, get_jwt_identity, jwt_required
from database import db_session
from models.user import User
from models.company import Company
from models.ip_tracking import UserDevice
from services.ip_security_service import IpSecurityService

logger = logging.getLogger(__name__)
telemetry_bp = APIRouter('telemetry', __name__)

@telemetry_bp.route('/live-gps', methods=['POST'])
def receive_live_gps():
    """
    Receives high-frequency satellite GPS fix from physical devices (mobile / laptop).
    Provides Uber-grade accuracy, speed, heading, and live movement streaming.
    """
    db_session.rollback()
    data = request.get_json() or {}
    
    try:
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid latitude or longitude'}), 400

    accuracy = data.get('accuracy')
    try:
        accuracy = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        accuracy = None

    speed = data.get('speed')
    try:
        speed = float(speed) if speed is not None else None
    except (TypeError, ValueError):
        speed = None

    heading = data.get('heading')
    try:
        heading = float(heading) if heading is not None else None
    except (TypeError, ValueError):
        heading = None

    device_id = data.get('device_id') or request.headers.get('x-device-id')
    device_name = data.get('device_name') or request.headers.get('x-device-name') or 'Dispositivo Físico'
    device_type = data.get('device_type') or request.headers.get('x-device-type') or 'desktop'

    client_ip = IpSecurityService.extract_client_ip(request)
    now = datetime.utcnow()

    # Identify user from JWT or payload
    user_id = None
    user_identity = get_jwt_identity()
    if user_identity:
        try:
            user_id = int(user_identity)
        except Exception:
            pass

    company_id = None
    user_name = None
    user_email = None

    if user_id:
        user = User.query.get(user_id)
        if user:
            user_name = user.name
            user_email = user.email
            company_id = user.company_id
            user.last_gps_lat = lat
            user.last_gps_lng = lng
            user.has_hardware_gps = True
            user.location_consent = 'granted'
            user.last_gps_accuracy = accuracy
            user.last_gps_speed = speed
            user.last_gps_heading = heading
            user.last_device_id = device_id
            user.last_device_name = device_name
            user.last_device_type = device_type
            user.last_ip = client_ip
            user.last_ip_lat = lat
            user.last_ip_lng = lng
            user.last_ip_updated_at = now

    if company_id:
        comp = Company.query.get(company_id)
        if comp:
            comp.last_ip = client_ip
            comp.last_ip_lat = lat
            comp.last_ip_lng = lng
            comp.last_ip_updated_at = now

    # Upsert UserDevice record
    if device_id:
        device = UserDevice.query.filter_by(device_id=device_id, network_ip=client_ip).first()
        if not device:
            device = UserDevice.query.filter_by(device_id=device_id).first()

        if device:
            device.gps_lat = lat
            device.gps_lng = lng
            device.has_hardware_gps = True
            device.location_consent = 'granted'
            device.gps_accuracy = accuracy
            device.gps_speed = speed
            device.gps_heading = heading
            device.device_name = device_name
            device.device_type = device_type
            device.last_seen_at = now
            device.request_count += 1
            if user_id:
                device.user_id = user_id
            if company_id:
                device.company_id = company_id
        else:
            device = UserDevice(
                user_id=user_id,
                company_id=company_id,
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                network_ip=client_ip,
                gps_lat=lat,
                gps_lng=lng,
                has_hardware_gps=True,
                location_consent='granted',
                gps_accuracy=accuracy,
                gps_speed=speed,
                gps_heading=heading,
                request_count=1,
                first_seen_at=now,
                last_seen_at=now
            )
            db_session.add(device)

    db_session.commit()

    # Invalidate session cache if user updated
    if user_id:
        try:
            from services.cache_service import CacheService
            CacheService.delete(f"user:session:{user_id}")
        except Exception:
            pass

    # Broadcast Live Movement to Super Admin Radar via Socket.IO
    try:
        from extensions import sio
        import asyncio
        payload = {
            "entity_id": f"company_{company_id}" if company_id else f"user_{user_id}",
            "company_id": company_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "device_id": device_id,
            "device_name": device_name,
            "device_type": device_type,
            "lat": lat,
            "lng": lng,
            "accuracy": accuracy,
            "speed": speed,
            "heading": heading,
            "timestamp": now.isoformat()
        }
        # In background event loop
        asyncio.create_task(sio.emit("live_gps_telemetry", payload))
    except Exception as e:
        logger.warning(f"Socket emit failed: {e}")

    return jsonify({
        'success': True,
        'lat': lat,
        'lng': lng,
        'accuracy': accuracy,
        'has_hardware_gps': True,
        'location_consent': 'granted',
        'timestamp': now.isoformat()
    }), 200


@telemetry_bp.route('/consent', methods=['POST'])
def save_location_consent():
    """
    Stores user/device preference for sharing location (Uber-style persistent choice).
    Persists to MySQL and invalidates cache so subsequent requests know consent is granted.
    """
    db_session.rollback()
    data = request.get_json() or {}
    consent = data.get('consent', 'granted') # 'granted' or 'denied'
    device_id = data.get('device_id') or request.headers.get('x-device-id')
    
    user_id = None
    user_identity = get_jwt_identity()
    if user_identity:
        try:
            user_id = int(user_identity)
        except Exception:
            pass

    client_ip = IpSecurityService.extract_client_ip(request)
    now = datetime.utcnow()

    if user_id:
        user = User.query.get(user_id)
        if user:
            user.location_consent = consent
            if consent == 'granted':
                user.has_hardware_gps = True

    if device_id:
        device = UserDevice.query.filter_by(device_id=device_id).first()
        if device:
            device.location_consent = consent
            device.last_seen_at = now
            if user_id and not device.user_id:
                device.user_id = user_id
        else:
            device = UserDevice(
                user_id=user_id,
                device_id=device_id,
                network_ip=client_ip,
                location_consent=consent,
                first_seen_at=now,
                last_seen_at=now
            )
            db_session.add(device)

    db_session.commit()

    if user_id:
        try:
            from services.cache_service import CacheService
            CacheService.delete(f"user:session:{user_id}")
        except Exception:
            pass

    return jsonify({
        'success': True,
        'location_consent': consent,
        'user_id': user_id,
        'device_id': device_id
    }), 200

