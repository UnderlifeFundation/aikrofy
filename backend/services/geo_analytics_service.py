"""
GeoAnalyticsService - Aggregation and geolocation engine for Super Admin radar.
Provides geospatial intelligence on Companies, Beta Leads, Live Users, Usage Time,
Lead Scoring, Real-time IP Tracking and Triangulation/Security Anomalies using OpenStreetMap.
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
import requests

from extensions import db
from models.company import Company
from models.user import User, UserRole
from models.beta_lead import BetaLead, BetaLeadStatus
from models.conversation import Conversation, Message
from models.subscription import Subscription, Plan
from models.ip_tracking import UserIpLog, BlockedIp
from services.ip_security_service import IpSecurityService

logger = logging.getLogger(__name__)

# Fallback Country & City Centroids for when no real-time IP exists
GEO_DICTIONARY = {
    # Countries
    "ECUADOR": {"lat": -1.8312, "lng": -78.1834, "country": "Ecuador", "code": "EC"},
    "EC": {"lat": -1.8312, "lng": -78.1834, "country": "Ecuador", "code": "EC"},
    "MEXICO": {"lat": 23.6345, "lng": -102.5528, "country": "México", "code": "MX"},
    "MX": {"lat": 23.6345, "lng": -102.5528, "country": "México", "code": "MX"},
    "COLOMBIA": {"lat": 4.5709, "lng": -74.2973, "country": "Colombia", "code": "CO"},
    "CO": {"lat": 4.5709, "lng": -74.2973, "country": "Colombia", "code": "CO"},
    "UNITED STATES": {"lat": 37.0902, "lng": -95.7129, "country": "United States", "code": "US"},
    "USA": {"lat": 37.0902, "lng": -95.7129, "country": "United States", "code": "US"},
    "US": {"lat": 37.0902, "lng": -95.7129, "country": "United States", "code": "US"},
    "SPAIN": {"lat": 40.4637, "lng": -3.7492, "country": "España", "code": "ES"},
    "ESPAÑA": {"lat": 40.4637, "lng": -3.7492, "country": "España", "code": "ES"},
    "ES": {"lat": 40.4637, "lng": -3.7492, "country": "España", "code": "ES"},
    "ARGENTINA": {"lat": -38.4161, "lng": -63.6167, "country": "Argentina", "code": "AR"},
    "AR": {"lat": -38.4161, "lng": -63.6167, "country": "Argentina", "code": "AR"},
    "PERU": {"lat": -9.1900, "lng": -75.0152, "country": "Perú", "code": "PE"},
    "PERÚ": {"lat": -9.1900, "lng": -75.0152, "country": "Perú", "code": "PE"},
    "PE": {"lat": -9.1900, "lng": -75.0152, "country": "Perú", "code": "PE"},
    "CHILE": {"lat": -35.6751, "lng": -71.5430, "country": "Chile", "code": "CL"},
    "CL": {"lat": -35.6751, "lng": -71.5430, "country": "Chile", "code": "CL"},
    "BRAZIL": {"lat": -14.2350, "lng": -51.9253, "country": "Brasil", "code": "BR"},
    "BRASIL": {"lat": -14.2350, "lng": -51.9253, "country": "Brasil", "code": "BR"},
    "BR": {"lat": -14.2350, "lng": -51.9253, "country": "Brasil", "code": "BR"},
    "PANAMA": {"lat": 8.5379, "lng": -80.7821, "country": "Panamá", "code": "PA"},
    "PANAMÁ": {"lat": 8.5379, "lng": -80.7821, "country": "Panamá", "code": "PA"},
    "COSTA RICA": {"lat": 9.7489, "lng": -83.7534, "country": "Costa Rica", "code": "CR"},
    "GUATEMALA": {"lat": 15.7835, "lng": -90.2308, "country": "Guatemala", "code": "GT"},
    "VENEZUELA": {"lat": 6.4238, "lng": -66.5897, "country": "Venezuela", "code": "VE"},
    "GERMANY": {"lat": 51.1657, "lng": 10.4515, "country": "Alemania", "code": "DE"},
    "FRANCE": {"lat": 46.2276, "lng": 2.2137, "country": "Francia", "code": "FR"},
    "UK": {"lat": 55.3781, "lng": -3.4360, "country": "Reino Unido", "code": "GB"},
    
    # Major Cities & Cantons in Ecuador & International
    "MILAGRO": {"lat": -2.1340, "lng": -79.5940, "city": "Milagro", "country": "Ecuador", "code": "EC"},
    "MILAGRO_BOHORQUEZ": {"lat": -2.1315, "lng": -79.5910, "city": "Milagro", "country": "Ecuador", "code": "EC"},
    "SAMBORONDON": {"lat": -2.1068, "lng": -79.7226, "city": "Samborondón", "country": "Ecuador", "code": "EC"},
    "SAMBORONDÓN": {"lat": -2.1068, "lng": -79.7226, "city": "Samborondón", "country": "Ecuador", "code": "EC"},
    "DAULE": {"lat": -1.8624, "lng": -79.9774, "city": "Daule", "country": "Ecuador", "code": "EC"},
    "DURAN": {"lat": -2.1706, "lng": -79.8458, "city": "Durán", "country": "Ecuador", "code": "EC"},
    "DURÁN": {"lat": -2.1706, "lng": -79.8458, "city": "Durán", "country": "Ecuador", "code": "EC"},
    "QUITO": {"lat": -0.1807, "lng": -78.4678, "city": "Quito", "country": "Ecuador", "code": "EC"},
    "GUAYAQUIL": {"lat": -2.1894, "lng": -79.8891, "city": "Guayaquil", "country": "Ecuador", "code": "EC"},
    "CUENCA": {"lat": -2.9001, "lng": -79.0059, "city": "Cuenca", "country": "Ecuador", "code": "EC"},
    "MACHALA": {"lat": -3.2581, "lng": -79.9554, "city": "Machala", "country": "Ecuador", "code": "EC"},
    "MANTA": {"lat": -0.9677, "lng": -80.7089, "city": "Manta", "country": "Ecuador", "code": "EC"},
    "PORTOVIEJO": {"lat": -1.0546, "lng": -80.4545, "city": "Portoviejo", "country": "Ecuador", "code": "EC"},
    "AMBATO": {"lat": -1.2491, "lng": -78.6168, "city": "Ambato", "country": "Ecuador", "code": "EC"},
    "SANTO DOMINGO": {"lat": -0.2530, "lng": -79.1754, "city": "Santo Domingo", "country": "Ecuador", "code": "EC"},
    "LOJA": {"lat": -3.9931, "lng": -79.2042, "city": "Loja", "country": "Ecuador", "code": "EC"},
    "IBARRA": {"lat": 0.3517, "lng": -78.1223, "city": "Ibarra", "country": "Ecuador", "code": "EC"},
    "RIOBAMBA": {"lat": -1.6636, "lng": -78.6546, "city": "Riobamba", "country": "Ecuador", "code": "EC"},
    "ESMERALDAS": {"lat": 0.9592, "lng": -79.6539, "city": "Esmeraldas", "country": "Ecuador", "code": "EC"},
    "QUEVEDO": {"lat": -1.0286, "lng": -79.4635, "city": "Quevedo", "country": "Ecuador", "code": "EC"},
    "BABAHOYO": {"lat": -1.8022, "lng": -79.5344, "city": "Babahoyo", "country": "Ecuador", "code": "EC"},
    "LATACUNGA": {"lat": -0.9352, "lng": -78.6155, "city": "Latacunga", "country": "Ecuador", "code": "EC"},
    "SANTA ELENA": {"lat": -2.2262, "lng": -80.8587, "city": "Santa Elena", "country": "Ecuador", "code": "EC"},
    "SALINAS": {"lat": -2.2234, "lng": -80.9585, "city": "Salinas", "country": "Ecuador", "code": "EC"},
    "TULCAN": {"lat": 0.8119, "lng": -77.7173, "city": "Tulcán", "country": "Ecuador", "code": "EC"},
    "TULCÁN": {"lat": 0.8119, "lng": -77.7173, "city": "Tulcán", "country": "Ecuador", "code": "EC"},
    "CIUDAD DE MÉXICO": {"lat": 19.4326, "lng": -99.1332, "city": "CDMX", "country": "México", "code": "MX"},
    "CDMX": {"lat": 19.4326, "lng": -99.1332, "city": "CDMX", "country": "México", "code": "MX"},
    "MONTERREY": {"lat": 25.6866, "lng": -100.3161, "city": "Monterrey", "country": "México", "code": "MX"},
    "GUADALAJARA": {"lat": 20.6597, "lng": -103.3496, "city": "Guadalajara", "country": "México", "code": "MX"},
    "BOGOTA": {"lat": 4.7110, "lng": -74.0721, "city": "Bogotá", "country": "Colombia", "code": "CO"},
    "BOGOTÁ": {"lat": 4.7110, "lng": -74.0721, "city": "Bogotá", "country": "Colombia", "code": "CO"},
    "MEDELLIN": {"lat": 6.2442, "lng": -75.5812, "city": "Medellín", "country": "Colombia", "code": "CO"},
    "MEDELLÍN": {"lat": 6.2442, "lng": -75.5812, "city": "Medellín", "country": "Colombia", "code": "CO"},
    "CALI": {"lat": 3.4516, "lng": -76.5320, "city": "Cali", "country": "Colombia", "code": "CO"},
    "LIMA": {"lat": -12.0464, "lng": -77.0428, "city": "Lima", "country": "Perú", "code": "PE"},
    "BUENOS AIRES": {"lat": -34.6037, "lng": -58.3816, "city": "Buenos Aires", "country": "Argentina", "code": "AR"},
    "SANTIAGO": {"lat": -33.4489, "lng": -70.6693, "city": "Santiago", "country": "Chile", "code": "CL"},
    "MADRID": {"lat": 40.4168, "lng": -3.7038, "city": "Madrid", "country": "España", "code": "ES"},
    "BARCELONA": {"lat": 41.3851, "lng": 2.1734, "city": "Barcelona", "country": "España", "code": "ES"},
    "MIAMI": {"lat": 25.7617, "lng": -80.1918, "city": "Miami", "country": "United States", "code": "US"},
    "NEW YORK": {"lat": 40.7128, "lng": -74.0060, "city": "New York", "country": "United States", "code": "US"},
    "LOS ANGELES": {"lat": 34.0522, "lng": -118.2437, "city": "Los Angeles", "country": "United States", "code": "US"},
}

PHONE_PREFIX_TO_GEO = {
    "+593": "ECUADOR",
    "593": "ECUADOR",
    "+52": "MEXICO",
    "52": "MEXICO",
    "+57": "COLOMBIA",
    "57": "COLOMBIA",
    "+1": "USA",
    "1": "USA",
    "+34": "ESPAÑA",
    "34": "ESPAÑA",
    "+54": "ARGENTINA",
    "54": "ARGENTINA",
    "+51": "PERU",
    "51": "PERU",
    "+56": "CHILE",
    "56": "CHILE",
    "+55": "BRAZIL",
    "55": "BRAZIL",
    "+507": "PANAMA",
    "507": "PANAMA",
    "+506": "COSTA RICA",
    "506": "COSTA RICA",
    "+502": "GUATEMALA",
    "502": "GUATEMALA",
    "+58": "VENEZUELA",
    "58": "VENEZUELA",
    "+49": "GERMANY",
    "+33": "FRANCE",
    "+44": "UK",
}

class GeoAnalyticsService:
    """Service to generate real-time geospatial intelligence for Super Admins."""

    @classmethod
    def resolve_location(
        cls,
        hardware_lat: float = None,
        hardware_lng: float = None,
        real_ip: str = None,
        city: str = None,
        country: str = None,
        phone: str = None,
        company_name: str = None
    ) -> dict:
        """
        Multi-tier precision coordinate resolver:
        Tier 1: Physical Device Hardware GPS (Highest precision: meters)
        Tier 2: Physical City / Address (Street level / City center)
        Tier 3: ISP Router Node Geolocation (Network fallback)
        """
        # Tier 1: True hardware GPS from physical device
        if hardware_lat is not None and hardware_lng is not None and (hardware_lat != 0 or hardware_lng != 0):
            return {
                "lat": hardware_lat,
                "lng": hardware_lng,
                "city": city or "Ubicación GPS Físico",
                "country": country or "Ecuador",
                "country_code": "EC",
                "is_live_ip": True,
                "has_hardware_gps": True,
                "precision_tier": "hardware_gps"
            }

        # Tier 2: Physical City / Canton / Address Match
        if city:
            city_clean = city.strip().upper()
            if city_clean in GEO_DICTIONARY:
                info = GEO_DICTIONARY[city_clean]
                return {
                    "lat": info["lat"],
                    "lng": info["lng"],
                    "city": info.get("city", city),
                    "country": info.get("country", country or "Ecuador"),
                    "country_code": info.get("code", "EC"),
                    "is_live_ip": False,
                    "has_hardware_gps": False,
                    "precision_tier": "city_address"
                }

        # Special heuristic: if company is Fundación Underlife or Weblifetech, default to Milagro
        if company_name and any(k in company_name.lower() for k in ["underlife", "weblifetech"]):
            info = GEO_DICTIONARY["MILAGRO_BOHORQUEZ"]
            return {
                "lat": info["lat"],
                "lng": info["lng"],
                "city": "Milagro (Calle Dr. José Bohórquez y Javier Romero)",
                "country": "Ecuador",
                "country_code": "EC",
                "is_live_ip": False,
                "has_hardware_gps": False,
                "precision_tier": "city_address"
            }

        # Tier 3: ISP Router Network Node lookup
        if real_ip and real_ip not in ("127.0.0.1", "localhost", "::1", ""):
            geo_ip = IpSecurityService.resolve_ip_geolocation(real_ip)
            if geo_ip.get("lat") and geo_ip.get("lng"):
                return {
                    "lat": geo_ip["lat"],
                    "lng": geo_ip["lng"],
                    "city": geo_ip.get("city", city or "IP City"),
                    "country": geo_ip.get("country", country or "Ecuador"),
                    "country_code": geo_ip.get("country_code", "EC"),
                    "isp": geo_ip.get("isp"),
                    "is_live_ip": True,
                    "has_hardware_gps": False,
                    "precision_tier": "isp_node"
                }

        # 3. Direct City match
        if city:
            city_upper = city.strip().upper()
            if city_upper in GEO_DICTIONARY:
                info = GEO_DICTIONARY[city_upper]
                import random
                jitter = (random.random() - 0.5) * 0.02
                return {
                    "lat": info["lat"] + jitter,
                    "lng": info["lng"] + jitter,
                    "city": info.get("city", city),
                    "country": info.get("country", country or "Ecuador"),
                    "country_code": info.get("code", "EC"),
                    "is_live_ip": False
                }

        # 4. Direct Country match
        if country:
            country_upper = country.strip().upper()
            if country_upper in GEO_DICTIONARY:
                info = GEO_DICTIONARY[country_upper]
                import random
                jitter = (random.random() - 0.5) * 0.04
                return {
                    "lat": info["lat"] + jitter,
                    "lng": info["lng"] + jitter,
                    "city": city or info.get("country"),
                    "country": info.get("country", country),
                    "country_code": info.get("code", "EC"),
                    "is_live_ip": False
                }

        # 5. Phone Prefix match
        if phone:
            clean_phone = phone.strip().replace(" ", "").replace("-", "")
            for prefix, key in PHONE_PREFIX_TO_GEO.items():
                if clean_phone.startswith(prefix):
                    info = GEO_DICTIONARY.get(key)
                    if info:
                        import random
                        jitter = (random.random() - 0.5) * 0.04
                        return {
                            "lat": info["lat"] + jitter,
                            "lng": info["lng"] + jitter,
                            "city": city or info.get("country"),
                            "country": info.get("country"),
                            "country_code": info.get("code", "EC"),
                            "is_live_ip": False
                        }

        # Default HQ centroid
        return {
            "lat": -0.1807,
            "lng": -78.4678,
            "city": "Quito",
            "country": "Ecuador",
            "country_code": "EC",
            "is_live_ip": False
        }

    @classmethod
    def calculate_lead_score(cls, entity_type: str, item_data: dict) -> int:
        """Calculates a dynamic 0-100 Lead / Engagement score for the entity."""
        score = 40

        if entity_type == 'company':
            tier = (item_data.get('subscription_tier') or '').lower()
            plan = (item_data.get('plan_type') or '').lower()
            if 'enterprise' in tier or 'enterprise' in plan:
                score += 35
            elif 'pyme' in tier or 'pro' in tier or 'plus' in plan:
                score += 25
            elif 'trial' in tier or 'beta' in tier:
                score += 15

            conv_count = item_data.get('total_conversations', 0)
            if conv_count > 50:
                score += 20
            elif conv_count > 10:
                score += 10
            elif conv_count > 0:
                score += 5

            credits = item_data.get('credit_balance', 0)
            if credits > 500:
                score += 10

        elif entity_type == 'beta_lead':
            status = item_data.get('status', 'pending')
            if status == BetaLeadStatus.APPROVED:
                score += 30
            elif status == BetaLeadStatus.PENDING:
                score += 15

            size = str(item_data.get('employee_count', ''))
            if '50+' in size or '100' in size or '200' in size:
                score += 20
            elif '10' in size or '20' in size:
                score += 10

            exp = (item_data.get('ai_experience') or '').lower()
            if 'avanzado' in exp or 'intermedio' in exp or 'implementado' in exp:
                score += 15

        return min(100, max(10, score))

    @classmethod
    def get_geo_radar_data(cls) -> dict:
        """
        Gathers comprehensive geographic and behavioral data on:
        - All Tenant Companies
        - Active Beta Leads
        - Real-Time Live Users, IP Geolocation, and Security Blacklist status
        """
        now = datetime.utcnow()
        recent_threshold = now - timedelta(minutes=25)

        points = []
        country_counts = {}
        stage_counts = {
            'live_active': 0,
            'clients_paying': 0,
            'beta_active': 0,
            'beta_pending': 0,
            'security_alert': 0
        }
        total_usage_hours = 0

        # -------------------------------------------------------------
        # 1. TENANT COMPANIES
        # -------------------------------------------------------------
        companies = Company.query.all()
        for comp in companies:
            # Primary user
            admin_user = User.query.filter_by(company_id=comp.id).order_by(User.role.asc(), User.id.asc()).first()
            user_email = admin_user.email if admin_user else (comp.email or 'N/A')
            user_name = admin_user.name if admin_user else comp.name
            last_login = admin_user.last_login if admin_user else None

            # Conversations & Activity
            conv_count = comp.conversations.count()
            last_conv = comp.conversations.order_by(Conversation.last_message_at.desc()).first()
            last_activity = last_conv.last_message_at if (last_conv and last_conv.last_message_at) else (last_login or comp.created_at)

            is_online = bool(last_activity and last_activity >= recent_threshold)
            if is_online:
                stage_counts['live_active'] += 1

            plan_label = (comp.plan_type or comp.subscription_tier or 'Free').capitalize()
            is_paying = comp.subscription_tier not in ('free', 'trial', 'beta')
            if is_paying:
                stage_counts['clients_paying'] += 1
            else:
                stage_counts['beta_active'] += 1

            estimated_hours = round(max(0.5, (conv_count * 0.25) + (comp.id * 1.8)), 1)
            total_usage_hours += estimated_hours

            # Real-Time IP detection
            real_ip = getattr(comp, "last_ip", None) or (getattr(admin_user, "last_ip", None) if admin_user else None)
            real_lat = getattr(comp, "last_ip_lat", None) or (getattr(admin_user, "last_ip_lat", None) if admin_user else None)
            real_lng = getattr(comp, "last_ip_lng", None) or (getattr(admin_user, "last_ip_lng", None) if admin_user else None)
            isp_name = getattr(comp, "last_ip_isp", None) or (getattr(admin_user, "last_ip_isp", None) if admin_user else None) or "Red de Telecomunicaciones"

            # Check if IP is blacklisted
            is_blocked = IpSecurityService.is_ip_blocked(real_ip) if real_ip else False

            # Check if admin user or any connected company device has active hardware GPS
            from models.ip_tracking import UserDevice
            company_devices = UserDevice.query.filter(
                (UserDevice.company_id == comp.id) | (UserDevice.network_ip == real_ip)
            ).all() if real_ip else UserDevice.query.filter_by(company_id=comp.id).all()

            hardware_device = next((d for d in company_devices if d.has_hardware_gps and d.gps_lat), None)
            hardware_lat = getattr(admin_user, "last_gps_lat", None) or (hardware_device.gps_lat if hardware_device else None)
            hardware_lng = getattr(admin_user, "last_gps_lng", None) or (hardware_device.gps_lng if hardware_device else None)
            has_hw_gps = bool(getattr(admin_user, "has_hardware_gps", False) or (hardware_device is not None))

            # Resolve coordinates (prioritizing true device GPS, then physical address/city, then WiFi IP)
            geo = cls.resolve_location(
                hardware_lat=hardware_lat if has_hw_gps else None,
                hardware_lng=hardware_lng if has_hw_gps else None,
                real_ip=real_ip,
                city=comp.city,
                country=comp.country,
                phone=comp.phone,
                company_name=comp.name
            )

            country_code = geo.get("country_code", "EC")
            country_counts[country_code] = country_counts.get(country_code, 0) + 1

            # Lead Scoring
            lead_score = cls.calculate_lead_score('company', {
                'subscription_tier': comp.subscription_tier,
                'plan_type': comp.plan_type,
                'total_conversations': conv_count,
                'credit_balance': comp.credit_balance
            })

            # Anomaly Security Flag
            has_anomaly = False
            anomaly_reason = None
            if is_blocked:
                has_anomaly = True
                anomaly_reason = "IP Bloqueada por Administración"
                stage_counts['security_alert'] += 1
            elif comp.credit_balance < 0:
                has_anomaly = True
                anomaly_reason = "Saldo de créditos negativo detectado"
                stage_counts['security_alert'] += 1

            # Physical Hardware Device & WiFi Network Cluster
            from models.ip_tracking import UserDevice
            company_devices = UserDevice.query.filter(
                (UserDevice.company_id == comp.id) | (UserDevice.network_ip == real_ip)
            ).all() if real_ip else UserDevice.query.filter_by(company_id=comp.id).all()
            
            cluster_devices = [
                {
                    "device_id": d.device_id,
                    "device_name": d.device_name or "Dispositivo Físico",
                    "device_type": d.device_type or "desktop",
                    "network_ip": d.network_ip,
                    "has_hardware_gps": d.has_hardware_gps,
                    "gps_lat": d.gps_lat,
                    "gps_lng": d.gps_lng,
                    "last_seen_at": d.last_seen_at.strftime("%Y-%m-%d %H:%M:%S") if d.last_seen_at else None
                }
                for d in company_devices
            ]
            
            primary_device_name = getattr(admin_user, "last_device_name", None) or (cluster_devices[0]["device_name"] if cluster_devices else "Equipo de Trabajo")
            primary_device_type = getattr(admin_user, "last_device_type", None) or (cluster_devices[0]["device_type"] if cluster_devices else "desktop")
            has_hardware_gps = bool(getattr(admin_user, "has_hardware_gps", False) or any(d["has_hardware_gps"] for d in cluster_devices))

            # Match with beta lead if existing to enrich demographic profile
            beta_profile = BetaLead.query.filter(
                (BetaLead.email == user_email) | (BetaLead.company_name == comp.name)
            ).first()

            role_in_company = getattr(admin_user, "job_title", None) or (beta_profile.role_in_company if beta_profile else "Administrador / Decision Maker")
            employee_count = getattr(comp, "employee_count", None) or (beta_profile.employee_count if beta_profile else "10-50")
            products_services = beta_profile.products_services if beta_profile else "Soluciones y Servicios Empresariales"
            ai_expectations = beta_profile.ai_expectations if beta_profile else "Automatización con IA y atención 360°"
            ai_experience = beta_profile.ai_experience if beta_profile else "Intermedio"

            is_demo = getattr(comp, "is_demo", False)
            demo_expires_at = comp.demo_expires_at.strftime("%Y-%m-%d") if getattr(comp, "demo_expires_at", None) else None

            # Accurate pipeline stage categorization
            if is_paying:
                pipeline_stage = "Cliente Activo"
            elif is_demo:
                pipeline_stage = "Demo Activa (Interacción)"
                stage_counts['beta_active'] += 1
            elif comp.subscription_tier == 'courtesy':
                pipeline_stage = "Plan Cortesía Activo"
                stage_counts['clients_paying'] += 1
            else:
                pipeline_stage = "Demo / Explorador"
                stage_counts['beta_active'] += 1

            points.append({
                "id": f"company_{comp.id}",
                "entity_type": "company",
                "name": comp.name,
                "user_name": user_name,
                "email": user_email,
                "phone": comp.phone or "N/A",
                "industry": comp.industry or "Tecnología / SaaS",
                "role_in_company": role_in_company,
                "employee_count": employee_count,
                "products_services": products_services,
                "ai_expectations": ai_expectations,
                "ai_experience": ai_experience,
                "is_demo": is_demo,
                "demo_expires_at": demo_expires_at,
                "ip_address": real_ip or "No registrada aún",
                "isp": isp_name,
                "is_ip_blocked": is_blocked,
                "device_name": primary_device_name,
                "device_type": primary_device_type,
                "has_hardware_gps": has_hardware_gps,
                "gps_accuracy": getattr(admin_user, "last_gps_accuracy", None),
                "gps_speed": getattr(admin_user, "last_gps_speed", None),
                "gps_heading": getattr(admin_user, "last_gps_heading", None),
                "network_cluster_count": max(1, len(cluster_devices)),
                "devices": cluster_devices,
                "lat": geo["lat"],
                "lng": geo["lng"],
                "city": geo["city"],
                "country": geo["country"],
                "country_code": country_code,
                "is_live_ip": geo.get("is_live_ip", False),
                "is_online": is_online,
                "plan": plan_label,
                "tier": comp.subscription_tier,
                "credit_balance": comp.credit_balance,
                "conversations_count": conv_count,
                "usage_time_hours": estimated_hours,
                "lead_score": lead_score,
                "pipeline_stage": pipeline_stage,
                "last_active": last_activity.strftime("%Y-%m-%d %H:%M:%S") if last_activity else "Reciente",
                "created_at": comp.created_at.strftime("%Y-%m-%d") if comp.created_at else "2026-01-01",
                "security_alert": has_anomaly,
                "security_reason": anomaly_reason,
                "logo_url": comp.logo_url
            })

        # -------------------------------------------------------------
        # 2. BETA LEADS
        # -------------------------------------------------------------
        beta_leads = BetaLead.query.all()
        for lead in beta_leads:
            real_ip = getattr(lead, "submission_ip", None)
            real_lat = getattr(lead, "ip_lat", None)
            real_lng = getattr(lead, "ip_lng", None)
            is_blocked = IpSecurityService.is_ip_blocked(real_ip) if real_ip else False

            geo = cls.resolve_location(
                real_ip=real_ip,
                city=getattr(lead, "ip_city", None),
                country=getattr(lead, "ip_country", None),
                phone=lead.phone,
                company_name=lead.company_name
            )

            country_code = geo.get("country_code", "EC")
            country_counts[country_code] = country_counts.get(country_code, 0) + 1

            if lead.status == BetaLeadStatus.APPROVED:
                stage_counts['beta_active'] += 1
                pipeline_stage = "Demo Activa (Aprobado)"
            elif lead.status == BetaLeadStatus.PENDING:
                stage_counts['beta_pending'] += 1
                pipeline_stage = "En Espera de Aprobación Demo"
            else:
                pipeline_stage = "Demo Rechazada"

            lead_score = cls.calculate_lead_score('beta_lead', {
                'status': lead.status,
                'employee_count': lead.employee_count,
                'ai_experience': lead.ai_experience
            })

            points.append({
                "id": f"beta_{lead.id}",
                "entity_type": "beta_lead",
                "name": lead.company_name,
                "user_name": lead.contact_name,
                "email": lead.email,
                "phone": lead.phone,
                "industry": lead.industry,
                "role_in_company": lead.role_in_company or "Solicitante de Demo",
                "employee_count": lead.employee_count or "1-10",
                "products_services": lead.products_services or "Servicios / Productos en Evaluación",
                "ai_expectations": lead.ai_expectations or "Atención y automatización comercial con IA",
                "ai_experience": lead.ai_experience or "Inicial / Explorando",
                "is_demo": lead.status == BetaLeadStatus.APPROVED,
                "demo_expires_at": None,
                "ip_address": real_ip or "No registrada aún",
                "isp": "Proveedor ISP Local",
                "is_ip_blocked": is_blocked,
                "lat": geo["lat"],
                "lng": geo["lng"],
                "city": geo["city"],
                "country": geo["country"],
                "country_code": country_code,
                "is_live_ip": geo.get("is_live_ip", False),
                "is_online": False,
                "plan": "Demo Beta Prospect",
                "tier": "beta_lead",
                "credit_balance": lead.credits_granted or 100,
                "conversations_count": 0,
                "usage_time_hours": 0.0,
                "lead_score": lead_score,
                "pipeline_stage": pipeline_stage,
                "last_active": lead.created_at.strftime("%Y-%m-%d") if lead.created_at else "Reciente",
                "created_at": lead.created_at.strftime("%Y-%m-%d") if lead.created_at else "2026-01-01",
                "security_alert": is_blocked,
                "security_reason": "IP Bloqueada" if is_blocked else None,
                "logo_url": None
            })

        # List of blocked IPs
        blocked_records = BlockedIp.query.filter_by(is_active=True).all()

        return {
            "success": True,
            "timestamp": now.isoformat(),
            "summary": {
                "total_points": len(points),
                "total_companies": len(companies),
                "total_beta_leads": len(beta_leads),
                "live_online_now": stage_counts['live_active'],
                "total_usage_hours": round(total_usage_hours, 1),
                "anomalies_count": stage_counts['security_alert'],
                "blocked_ips_count": len(blocked_records),
                "countries_count": len(country_counts),
                "country_distribution": country_counts,
                "stage_distribution": stage_counts
            },
            "points": points,
            "blocked_ips": [b.to_dict() for b in blocked_records]
        }
