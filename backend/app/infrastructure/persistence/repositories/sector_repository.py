from typing import List, Optional
from sqlalchemy.orm import Session
from app.infrastructure.persistence.models import Sector
class SectorRepository:
    def __init__(self, db: Session) -> None: self.db = db
    def list(self, status: Optional[str] = None) -> List[Sector]:
        q = self.db.query(Sector)
        if status is not None: q = q.filter(Sector.status == status)
        return q.order_by(Sector.id.asc()).all()
    def get_by_code(self, code: str) -> Optional[Sector]: return self.db.query(Sector).filter(Sector.code == code).one_or_none()
    def get_by_id(self, sector_id: int) -> Optional[Sector]: return self.db.query(Sector).filter(Sector.id == sector_id).one_or_none()