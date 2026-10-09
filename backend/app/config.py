from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "document_ai_rpa"
    
    # Storage
    storage_path: str = "./storage"
    max_upload_size_mb: int = 10
    
    # Processing
    confidence_threshold: float = 0.80
    
    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    # RPA
    accounting_app_url: str = "http://localhost:3001"
    rpa_api_key: str = "change-me"
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        # Later files take priority, so the shared project-root .env wins over backend/.env,
        # matching the RPA processor. Real environment variables override both.
        env_file = [
            str(BACKEND_DIR / ".env"),
            str(PROJECT_ROOT / ".env"),
        ]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
