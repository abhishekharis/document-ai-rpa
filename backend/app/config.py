from pydantic_settings import BaseSettings
from typing import List


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
        env_file = ".env"
        case_sensitive = False


settings = Settings()
