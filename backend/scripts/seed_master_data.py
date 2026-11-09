from typing import Dict
from sqlalchemy.orm import Session
from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import Sector, Territory
SECTORS = [
    {"code": "mantenimiento_reparacion_inmuebles", "name": "Mantenimiento y reparacion de inmuebles", "status": "activo"},
    {"code": "administracion_fincas", "name": "Administracion de fincas", "status": "preparado"},
    {"code": "instalaciones_eficiencia_energetica", "name": "Instalaciones y eficiencia energetica", "status": "preparado"},
    {"code": "reformas_integrales", "name": "Reformas integrales", "status": "preparado"},
    {"code": "mantenimiento_industrial", "name": "Mantenimiento industrial", "status": "preparado"}
]
TERRITORIES = [
    {"code": "andalucia", "name": "Andalucia", "level": "comunidad", "parent_code": None},
    {"code": "almeria", "name": "Almeria", "level": "provincia", "parent_code": "andalucia"},
    {"code": "cadiz", "name": "Cadiz", "level": "provincia", "parent_code": "andalucia"},
    {"code": "cordoba", "name": "Cordoba", "level": "provincia", "parent_code": "andalucia"},
    {"code": "granada", "name": "Granada", "level": "provincia", "parent_code": "andalucia"},
    {"code": "huelva", "name": "Huelva", "level": "provincia", "parent_code": "andalucia"},
    {"code": "jaen", "name": "Jaen", "level": "provincia", "parent_code": "andalucia"},
    {"code": "malaga", "name": "Malaga", "level": "provincia", "parent_code": "andalucia"},
    {"code": "sevilla", "name": "Sevilla", "level": "provincia", "parent_code": "andalucia"}
]
def seed(db: Session) -> Dict[str, int]:
    inserted_s = existing_s = 0
    for data in SECTORS:
        obj = db.query(Sector).filter(Sector.code == data["code"]).one_or_none()
        if obj is None: db.add(Sector(code=data["code"], name=data["name"], status=data["status"])); inserted_s += 1
        else: existing_s += 1
    db.flush()
    inserted_t = existing_t = 0
    for data in TERRITORIES:
        obj = db.query(Territory).filter(Territory.code == data["code"]).one_or_none()
        if obj is not None: existing_t += 1; continue
        parent_id = None
        if data["parent_code"]:
            parent = db.query(Territory).filter(Territory.code == data["parent_code"]).one_or_none()
            if parent: parent_id = parent.id
        db.add(Territory(code=data["code"], name=data["name"], level=data["level"], parent_id=parent_id))
        inserted_t += 1
    db.commit()
    return {"sectores_insertados": inserted_s, "sectores_existentes": existing_s, "territorios_insertados": inserted_t, "territorios_existentes": existing_t}
if __name__ == "__main__":
    with SessionLocal() as db: print(seed(db))