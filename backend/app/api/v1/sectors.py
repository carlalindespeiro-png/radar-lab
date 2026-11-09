from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.sector_repository import SectorRepository
from app.shared.schemas import SectorRead
router = APIRouter(prefix="/sectors", tags=["sectors"])
@router.get("", response_model=List[SectorRead])
def list_sectors(status: Optional[str] = Query(None, pattern="^(activo|preparado|archivado)$"), db: Session = Depends(get_db)) -> List[SectorRead]:
    repo = SectorRepository(db)
    return repo.list(status=status)