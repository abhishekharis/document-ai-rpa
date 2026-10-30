from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


INSECURE_RPA_KEYS = {"", "change-me", "change-me-in-production"}


class Settings(BaseSettings):
    # Deployment environment: development, staging or production
    environment: str = "development"
    
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
    
    # Rate limiting (requests per minute per client IP)
    upload_rate_limit_per_minute: int = 30
    rpa_rate_limit_per_minute: int = 120
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    @model_validator(mode="after")
    def validate_deployed_settings(self):
        """Refuse to start a staging/production deployment with unsafe defaults."""
        if self.environment == "development":
            return self
        problems = []
        if self.rpa_api_key in INSECURE_RPA_KEYS or len(self.rpa_api_key) < 16:
            problems.append("RPA_API_KEY must be set to a secret of at least 16 characters")
        if any("localhost" in o or "127.0.0.1" in o for o in self.cors_origins):
            problems.append("CORS_ORIGINS must not contain localhost origins")
        if problems:
            raise ValueError(f"Invalid {self.environment} configuration: " + "; ".join(problems))
        return self
    
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
