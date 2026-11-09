from typing import List, Optional
from sqlalchemy.orm import Session
from app.infrastructure.persistence.models import Territory
class TerritoryRepository:
    def __init__(self, db: Session) -> None: self.db = db
    def list(self, level: Optional[str] = None, parent_id: Optional[int] = None) -> List[Territory]:
        q = self.db.query(Territory)
        if level is not None: q = q.filter(Territory.level == level)
        if parent_id is not None: q = q.filter(Territory.parent_id == parent_id)
        return q.order_by(Territory.id.asc()).all()
    def get_by_code(self, code: str) -> Optional[Territory]: return self.db.query(Territory).filter(Territory.code == code).one_or_none()
    def get_by_id(self, territory_id: int) -> Optional[Territory]: return self.db.query(Territory).filter(Territory.id == territory_id).one_or_none()