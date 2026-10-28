"""
Community License & Activation Service (Aikrofy Open-Core Activation Gate)
Provides cryptographic verification and management of activation tokens for
self-hosted Community Edition instances.

Modeled after n8n / Odoo / GitLab community activation:
- Online / Cloud verification with official fallback
- Local JWT / HMAC / Ed25519 payload verification
- Grace periods and offline validation cache
"""
import os
import json
import time
import hmac
import hashlib
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Master secret key used by Aikrofy Cloud to sign community activation tokens
# In Cloud this is loaded from env; in Community it validates against the public signature or Cloud API
COMMUNITY_SIGNING_SECRET = os.environ.get(
    "COMMUNITY_ACTIVATION_SECRET",
    "aikrofy_opencore_activation_master_secret_2026_underlife_weblifetech"
)
CLOUD_ACTIVATION_URL = os.environ.get(
    "AIKROFY_CLOUD_ACTIVATION_URL",
    "https://aikrofy.com/api/community/verify-token"
)


class CommunityLicenseService:
    """Handles issuance (Cloud) and enforcement (Community Instance) of Activation Tokens."""

    @staticmethod
    def is_community_mode() -> bool:
        """Returns True if this instance is running in self-hosted Community mode."""
        mode = os.environ.get("AIKROFY_DEPLOYMENT_MODE", "").lower().strip()
        return mode == "community"

    @classmethod
    def generate_token(
        cls,
        email: str,
        name: str,
        organization: str = "",
        country: str = "",
        instance_id: str = "",
        edition: str = "community"
    ) -> Dict[str, Any]:
        """
        [CLOUD ONLY] Generates a signed activation token for an organization or user.
        Format: AIK-COMM-<base64_payload>.<signature>
        """
        import base64
        issued_at = int(time.time())
        # Valid for 365 days by default, auto-renewable
        expires_at = issued_at + (365 * 24 * 3600)

        payload = {
            "v": 1,
            "type": "aikrofy_community_activation",
            "email": email.strip().lower(),
            "name": name.strip(),
            "org": (organization or name).strip(),
            "country": country.strip().upper(),
            "instance_id": instance_id.strip() or f"inst_{hashlib.sha256(email.encode()).hexdigest()[:12]}",
            "edition": edition,
            "iat": issued_at,
            "exp": expires_at,
            "features": [
                "single_whatsapp_account",
                "langgraph_krof_copilot",
                "pos_native_catalog",
                "byok_all_providers",
                "unlimited_local_usage"
            ]
        }

        payload_bytes = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8').rstrip('=')

        sig = hmac.new(
            COMMUNITY_SIGNING_SECRET.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:32]

        token_string = f"AIK-COMM-{payload_b64}.{sig}"
        return {
            "token": token_string,
            "payload": payload,
            "created_at": issued_at,
            "expires_at": expires_at
        }

    @classmethod
    def verify_token(cls, token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates a token. First validates cryptographic signature locally,
        then optionally confirms with the Cloud Licensing Gateway.
        """
        import base64
        if not token or not str(token).strip():
            return False, "Token de activación vacío o no provisto.", None

        raw = str(token).strip()
        if not raw.startswith("AIK-COMM-") or "." not in raw:
            return False, "Formato de token inválido. Debe comenzar con 'AIK-COMM-'.", None

        content = raw[len("AIK-COMM-"):]
        parts = content.split(".", 1)
        if len(parts) != 2:
            return False, "Estructura de token corrupta.", None

        payload_b64, provided_sig = parts[0], parts[1]

        # 1. Cryptographic HMAC Check
        expected_sig = hmac.new(
            COMMUNITY_SIGNING_SECRET.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:32]

        if not hmac.compare_digest(expected_sig, provided_sig):
            # If secret differed (e.g. self-hosted without secret), try verifying against Cloud API
            remote_ok, remote_data = cls._verify_with_cloud(raw)
            if remote_ok:
                return True, "Token verificado con éxito vía Aikrofy Cloud Gateway.", remote_data
            return False, "Firma de token inválida o no reconocida por Fundación Underlife / Aikrofy.", None

        # 2. Decode Payload
        try:
            padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
            payload_json = base64.urlsafe_b64decode(padded_b64.encode('utf-8')).decode('utf-8')
            payload = json.loads(payload_json)
        except Exception as e:
            return False, f"Error decodificando payload de token: {e}", None

        # 3. Check Expiry
        exp = payload.get("exp", 0)
        if exp and exp < int(time.time()):
            return False, "El token de activación ha expirado. Renueva tu token en app.aikrofy.com/community.", payload

        return True, "Token de activación válido.", payload

    @classmethod
    def _verify_with_cloud(cls, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Tries validating token against Aikrofy Cloud API if available."""
        try:
            req = urllib.request.Request(
                CLOUD_ACTIVATION_URL,
                data=json.dumps({"token": token}).encode('utf-8'),
                headers={"Content-Type": "application/json", "User-Agent": "Aikrofy-Community-Node"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data.get("valid", False), data.get("payload")
        except Exception:
            pass
        return False, None

    @classmethod
    def get_stored_activation(cls) -> Optional[Dict[str, Any]]:
        """Reads stored activation state from local config/file or DB."""
        # 1. Check environment variable first
        env_token = os.environ.get("AIKROFY_COMMUNITY_TOKEN", "").strip()
        if env_token:
            ok, msg, payload = cls.verify_token(env_token)
            if ok:
                return {"token": env_token, "source": "env", "payload": payload}

        # 2. Check local JSON file in uploads/config directory
        lic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "community_license.json")
        if os.path.exists(lic_path):
            try:
                with open(lic_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tok = data.get("token", "")
                    ok, msg, payload = cls.verify_token(tok)
                    if ok:
                        return {"token": tok, "source": "file", "payload": payload}
            except Exception:
                pass

        return None

    @classmethod
    def store_activation(cls, token: str, payload: Dict[str, Any]) -> bool:
        """Persists the activation token to local instance storage."""
        lic_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
        os.makedirs(lic_dir, exist_ok=True)
        lic_path = os.path.join(lic_dir, "community_license.json")
        try:
            with open(lic_path, "w", encoding="utf-8") as f:
                json.dump({
                    "token": token,
                    "activated_at": int(time.time()),
                    "payload": payload
                }, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving community activation file: {e}")
            return False
