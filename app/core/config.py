import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from project root even if server is started elsewhere
BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    # Application
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "File Share Network")
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    
    # Security
    # Strip values to avoid accidental whitespace or surrounding quotes from .env
    SECRET_KEY: str = os.getenv("SECRET_KEY", "laptrinhmang").strip()
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256").strip()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin").strip()
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./network_app.db")
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() in ("1", "true", "yes")
    
    # Network Settings
    TCP_HOST: str = os.getenv("TCP_HOST", "0.0.0.0")
    TCP_PORT: int = int(os.getenv("TCP_PORT", "9000"))
    TCP_SSL_PORT: int = int(os.getenv("TCP_SSL_PORT", "9001"))
    
    MULTICAST_GROUP: str = os.getenv("MULTICAST_GROUP", "224.1.1.1")
    MULTICAST_PORT: int = int(os.getenv("MULTICAST_PORT", "5007"))
    
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50051"))

    # Voice call (TCP relay)
    VOICE_PORT: int = int(os.getenv("VOICE_PORT", "6000"))
    VOICE_SAMPLE_RATE: int = int(os.getenv("VOICE_SAMPLE_RATE", "16000"))
    VOICE_CHANNELS: int = int(os.getenv("VOICE_CHANNELS", "1"))
    VOICE_SAMPLE_WIDTH: int = int(os.getenv("VOICE_SAMPLE_WIDTH", "2"))
    VOICE_CHUNK_FRAMES: int = int(os.getenv("VOICE_CHUNK_FRAMES", "1024"))
    
    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")
    
    # File Upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "static/uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "52428800"))
    ALLOWED_EXTENSIONS: str = os.getenv("ALLOWED_EXTENSIONS", ".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.txt")
    
    # SSL
    SSL_CERT_FILE: str = os.getenv("SSL_CERT_FILE", "ssl_certs/server.crt")
    SSL_KEY_FILE: str = os.getenv("SSL_KEY_FILE", "ssl_certs/server.key")

    # Radio (Multicast) - Live audio settings
    RADIO_SOURCE: str = os.getenv("RADIO_SOURCE", "mic")  # mic | wav | dummy | auto
    RADIO_SAMPLE_RATE: int = int(os.getenv("RADIO_SAMPLE_RATE", "16000"))
    RADIO_CHANNELS: int = int(os.getenv("RADIO_CHANNELS", "1"))
    RADIO_SAMPLE_WIDTH: int = int(os.getenv("RADIO_SAMPLE_WIDTH", "2"))  # bytes (int16)
    RADIO_CHUNK_FRAMES: int = int(os.getenv("RADIO_CHUNK_FRAMES", "1024"))
    
    # Dev: allow a debug endpoint to return token claims (set to 'true' to enable)
    DEBUG_TOKEN_ENDPOINT: bool = os.getenv("DEBUG_TOKEN_ENDPOINT", "false").lower() in ("1", "true", "yes")
    
    def get_allowed_extensions_list(self):
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

settings = Settings()