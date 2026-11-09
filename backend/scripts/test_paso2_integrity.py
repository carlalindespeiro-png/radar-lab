import os, sys
from pathlib import Path
_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))
TEST_DB = "test_paso2.db"
def main() -> int:
    os.chdir(_backend_dir)
    if os.path.exists(TEST_DB): os.remove(TEST_DB)
    os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB}"
    from app.infrastructure.persistence.database import Base, SessionLocal, engine
    from app.infrastructure.persistence.models import ResearchRun, Sector, Territory, User
    from scripts.seed_master_data import seed
    print("[1] Creando esquema...")
    Base.metadata.create_all(engine)
    print("[2] Semilla 1...")
    with SessionLocal() as db: print(f"    {seed(db)}")
    print("[3] Semilla 2...")
    with SessionLocal() as db: print(f"    {seed(db)}")
    print("[4] Verificando...")
    with SessionLocal() as db:
        n_s = db.query(Sector).count(); n_t = db.query(Territory).count()
        print(f"    sectores={n_s} territorios={n_t}")
    print("[5] Limpieza...")
    engine.dispose(); os.remove(TEST_DB)
    print("TODAS LAS PRUEBAS PASARON")
    return 0
if __name__ == "__main__": sys.exit(main())