"""
Aikrofy Configuration Module
Manages application settings from environment variables
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5010/api').rstrip('/')
    
    # Meta WhatsApp & Facebook Login
    META_VERIFY_TOKEN = os.getenv('META_VERIFY_TOKEN', 'aikrofy_meta_secret_2026')
    META_APP_ID = os.getenv('META_APP_ID', '')
    META_APP_SECRET = os.getenv('META_APP_SECRET', '')
    META_CONFIG_ID = os.getenv('META_CONFIG_ID', '')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Database
    # For development, uses SQLite by default. Set DATABASE_URL for MySQL in production.
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'aikrofy')
    
    # Default to SQLite for easy development
    _default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aikrofy.db')
    
    # Database Connection Logic
    # 1. Check for explicit DATABASE_URL
    # 2. Check for MySQL attributes (if HOST is set and not default/localhost or if explicitly configured)
    if os.getenv('DATABASE_URL'):
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    elif os.getenv('MYSQL_HOST') and os.getenv('MYSQL_USER') and os.getenv('MYSQL_PASSWORD'):
        # Construct MySQL URL from variables
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
            f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT', '3306')}/{os.getenv('MYSQL_DATABASE', 'aikrofy')}"
        )
    else:
        # Fallback to SQLite
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_default_db}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 120,        # Recycle connections every 2 min (AI calls can take 60-90s)
        'pool_pre_ping': True,      # Validate connection before checkout from pool
        'pool_timeout': 30,
        'pool_size': 5,
        'max_overflow': 5,
        'pool_use_lifo': True,      # Reuse most-recently-used connections first (less likely to expire)
    }
    
    # Pinecone
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY', '')
    PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT', '')
    PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'aikrofy-rag')
    
    # LLM Providers
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY', '')
    
    DEFAULT_LLM_PROVIDER = os.getenv('DEFAULT_LLM_PROVIDER', 'openai')
    DEFAULT_LLM_MODEL = os.getenv('DEFAULT_LLM_MODEL', 'gpt-5-nano')
    
    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
    
    # SendGrid
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', '')

    # SMTP Default Configuration
    SMTP_HOST = os.getenv('SMTP_HOST', '')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    SMTP_USER = os.getenv('SMTP_USER', 'hello@aikrofy.com')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    SMTP_ENCRYPTION = os.getenv('SMTP_ENCRYPTION', 'ssl')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'hello@aikrofy.com')
    
    # Google APIs
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'https://app.aikrofy.com/api/auth/google/callback')
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://app.aikrofy.com')
    
    # PayPal
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')
    
    # ElevenLabs
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY', '')
    DEFAULT_VOICE_PROVIDER = os.getenv('DEFAULT_VOICE_PROVIDER', 'elevenlabs')
    
    # Additional AI Providers
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    
    # Media WebLifeTech Central Microservices (Dedicated FFmpeg, Whisper STT & Edge-TTS)
    MEDIA_MICRO_STT_URL = os.getenv('MEDIA_MICRO_STT_URL', 'https://media.weblifetech.com/api/micro/audio/transcribe')
    MEDIA_TTS_URL = os.getenv('MEDIA_TTS_URL', 'https://media.weblifetech.com/api/tts/speak')
    MEDIA_STT_URL = os.getenv('MEDIA_STT_URL', 'https://media.weblifetech.com/api/external/transcribe')
    EXTERNAL_API_KEY = os.getenv('EXTERNAL_API_KEY', '')
    
    # File Uploads
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {
        'pdf', 'docx', 'doc', 'txt', 'md', 'markdown', 'csv', 'json', 'xlsx', 'xls',
        'mp3', 'wav', 'ogg', 'm4a', 'opus', 'aac', 'webm', 'oga', 'flac'
    }
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6380/0').rstrip('/')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6380/0').rstrip('/')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
