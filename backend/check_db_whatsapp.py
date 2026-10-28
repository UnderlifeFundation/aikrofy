from app import create_app
from extensions import db
from models.channel import Channel
from models.company import Company
from models.user import User

app = create_app()

with app.app_context():
    # Assuming user ID 1 for Jonnathan/WebLifeTech based on logs
    user = User.query.get(1)
    if not user:
        print("User ID 1 not found")
        exit()
        
    company = user.company
    print(f"Checking configuration for Company: {company.name} (ID: {company.id})")
    print("-" * 50)
    
    # Check Channel
    channel = Channel.query.filter_by(company_id=company.id, type='whatsapp').first()
    
    if channel:
        print(f"FOUND WhatsApp Channel:")
        print(f"  - Status: {channel.status}")
        print(f"  - Credentials: {channel.credentials}")
        
        creds = channel.credentials or {}
        if creds.get('provider') == 'baileys':
            print("  ✅ CORRECT: Provider is set to 'baileys' in Channel credentials.")
        else:
            print(f"  ❌ WARNING: Provider is '{creds.get('provider')}' (Expected 'baileys')")
    else:
        print("❌ WhatsApp Channel NOT found in database.")

    print("-" * 50)
    
    # Check Company API Keys
    api_keys = company.api_keys or {}
    print(f"Company API Keys (whatsapp_provider): {api_keys.get('whatsapp_provider')}")
    
    if api_keys.get('whatsapp_provider') == 'baileys':
        print("✅ CORRECT: 'whatsapp_provider' is set to 'baileys' in Company settings.")
    else:
        print(f"❌ WARNING: 'whatsapp_provider' is '{api_keys.get('whatsapp_provider')}'")
