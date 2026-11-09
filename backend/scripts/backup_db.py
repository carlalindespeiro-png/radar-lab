import shutil, sqlite3, sys
from datetime import datetime
from pathlib import Path
def main() -> int:
    backend_dir = Path(__file__).resolve().parent.parent
    source = backend_dir / "radar_lab.db"
    if not source.exists():
        print(f"ERROR: {source} no existe.")
        return 1
    backups_dir = backend_dir.parent / "backups"
    backups_dir.mkdir(exist_ok=True)
    dest = backups_dir / f"radar_lab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(source, dest)
    print(f"backup OK: {dest}")
    return 0
if __name__ == "__main__": sys.exit(main())