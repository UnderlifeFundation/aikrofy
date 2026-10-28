import os
import json
import requests
import sys
try:
    from google.oauth2 import service_account
    import google.auth.transport.requests
except ImportError:
    print("ERROR: missing 'google-auth' library. Run: pip install google-auth")
    sys.exit(1)

def register_risc():
    # Path relative to backend root
    json_path = 'service-account.json'
    
    if not os.path.exists(json_path):
        print("\n❌ ERROR: No se encontró el archivo 'service-account.json'.")
        print("💡 Por favor, coloca el archivo JSON de tu Cuenta de Servicio en la carpeta 'backend/'.")
        print("⚠️ Asegúrate de que la cuenta de servicio tenga el rol: 'RISC Configuration Admin'.\n")
        return

    # 1. Load credentials
    # Scopes for RISC configuration and status management
    scopes = [
        'https://www.googleapis.com/auth/risc.configuration.readwrite',
        'https://www.googleapis.com/auth/risc.status.readwrite'
    ]
    try:
        creds = service_account.Credentials.from_service_account_file(json_path, scopes=scopes)
    except Exception as e:
        print(f"❌ ERROR: Error al leer las credenciales del JSON: {e}")
        return
    
    # 2. Get auth token
    print("🔐 Autenticando con Google...")
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    token = creds.token
    
    # 3. Configuration
    # We use the production URL for registration to appease Google's verification bot
    webhook_url = "https://api.aikrofy.com/api/webhooks/google-risc"
    
    print(f"🌐 Registrando URL de Webhook: {webhook_url}")
    
    # 4. API Request to update stream
    api_url = "https://risc.googleapis.com/v1beta/stream:update"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "delivery": {
            "delivery_method": "https://schemas.openid.net/secevent/risc/delivery-method/push",
            "url": webhook_url
        },
        "events_requested": [
            "https://schemas.openid.net/secevent/risc/event-type/account-disabled",
            "https://schemas.openid.net/secevent/risc/event-type/sessions-revoked",
            "https://schemas.openid.net/secevent/oauth/event-type/tokens-revoked",
            "https://schemas.openid.net/secevent/risc/event-type/account-credential-change-required",
            "https://schemas.openid.net/secevent/risc/event-type/verification"
        ]
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=data)
        if response.status_code == 200:
            print("\n✅ ÉXITO: El Webhook de RISC ha sido registrado correctamente.")
            print("🚀 Google comenzará a enviar eventos de seguridad a production.")
            
            # Sub-step: Send verification test
            print("\n🧪 Enviando prueba de verificación...")
            verify_url = "https://risc.googleapis.com/v1beta/stream:verify"
            v_res = requests.post(verify_url, headers=headers, json={"state": "aikrofy_verification_test"})
            if v_res.status_code == 200:
                print("✨ Prueba enviada! Revisa los logs de tu servidor en production.")
            else:
                print(f"⚠️ Error al enviar prueba: {v_res.text}")
                
        else:
            print(f"\n❌ FALLÓ EL REGISTRO: {response.status_code}")
            print(f"Detalle: {response.text}")
    except Exception as e:
        print(f"\n❌ ERROR: Ocurrió una excepción: {e}")

if __name__ == "__main__":
    register_risc()
