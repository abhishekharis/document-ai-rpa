from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    document_id: str
    event: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
