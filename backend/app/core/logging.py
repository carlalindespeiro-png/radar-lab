import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from app.core.config import settings
def configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    file_handler = TimedRotatingFileHandler(log_dir / "radar_lab.log", when="midnight", backupCount=7, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers): root.addHandler(console)
    if not any(isinstance(h, TimedRotatingFileHandler) for h in root.handlers): root.addHandler(file_handler)