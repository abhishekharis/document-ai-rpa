from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path


class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "document_ai_rpa"
    
    # Storage
    storage_path: str = str(Path(__file__).parent / "storage")
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
        # Try to load .env from parent directory first, then current directory
        env_file = [
            str(Path(__file__).parent.parent / ".env"),  # Project root .env
            ".env"  # Current directory .env
        ]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
