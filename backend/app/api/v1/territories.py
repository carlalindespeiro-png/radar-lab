from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.territory_repository import TerritoryRepository
from app.shared.schemas import TerritoryRead
router = APIRouter(prefix="/territories", tags=["territories"])
@router.get("", response_model=List[TerritoryRead])
def list_territories(level: Optional[str] = Query(None, pattern="^(comunidad|provincia)$"), parent_id: Optional[int] = Query(None, ge=1), db: Session = Depends(get_db)) -> List[TerritoryRead]:
    repo = TerritoryRepository(db)
    return repo.list(level=level, parent_id=parent_id)