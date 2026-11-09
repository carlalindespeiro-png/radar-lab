from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
class HealthResponse(BaseModel):
    status: str
    version: str
class SectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    cnae_code: Optional[str] = None
    status: str
    parent_id: Optional[int] = None
    created_at: datetime
class TerritoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    level: str
    parent_id: Optional[int] = None
    created_at: datetime