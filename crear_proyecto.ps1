<#
.SYNOPSIS
    Crea la estructura completa de RADAR LAB (Paso 1 + Paso 2).
.DESCRIPTION
    - No sobrescribe archivos existentes.
    - Crea backend (FastAPI + SQLite + Alembic) y frontend (React + Vite).
    - No ejecuta migraciones ni toca bases de datos existentes.
#>
param(
    [switch]$RunSetup,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
function Write-FileIfNotExists {
    param([string]$Path, [string]$Content)
    if (Test-Path $Path) {
        Write-Host "  [EXISTE, no sobrescrito] $Path" -ForegroundColor Yellow
        return
    }
    $dir = Split-Path $Path -Parent
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
    Write-Host "  [creado] $Path" -ForegroundColor Green
}

function Write-EmptyFile {
    param([string]$Path)
    Write-FileIfNotExists $Path ""
}

function Section {
    param([string]$Name)
    Write-Host "`n== $Name ==" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# 0. Verificación del entorno
# ---------------------------------------------------------------------------
Write-Host "RADAR LAB - Creando estructura desde cero" -ForegroundColor Magenta
Write-Host "Directorio actual: $(Get-Location)"

if ((Test-Path "backend") -and (Test-Path "frontend")) {
    Write-Host "AVISO: ya existen 'backend' y 'frontend'." -ForegroundColor Yellow
    Write-Host "Los archivos existentes NO se sobrescribirán." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 1. BACKEND - archivos raíz
# ---------------------------------------------------------------------------
Section "Backend - archivos raíz"

Write-FileIfNotExists "backend\pyproject.toml" @'
[project]
name = "radar-lab-backend"
version = "0.1.0"
description = "RADAR LAB - Fundacion (Paso 1 + Paso 2)"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy>=2.0.30",
    "alembic>=1.13.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "scripts*"]
'@

Write-FileIfNotExists "backend\.env.example" @'
DATABASE_URL=sqlite:///./radar_lab.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
SEARXNG_BASE_URL=http://localhost:8080
MAX_QUERIES_PER_RESEARCH=10
MAX_SOURCES_PER_RESEARCH=30
LOG_LEVEL=INFO
'@

Write-FileIfNotExists "backend\alembic.ini" @'
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///./radar_lab.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'@

# ---------------------------------------------------------------------------
# 2. BACKEND - Alembic
# ---------------------------------------------------------------------------
Section "Backend - Alembic"

Write-FileIfNotExists "backend\alembic\env.py" @'
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings  # noqa: E402
from app.infrastructure.persistence.database import Base  # noqa: E402
from app.infrastructure.persistence import models  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'@

Write-FileIfNotExists "backend\alembic\script.py.mako" @'
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'@

Write-FileIfNotExists "backend\alembic\versions\0001_initial_users.py" @'
"""initial users

Revision ID: 0001_initial_users
Revises:
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
'@

Write-FileIfNotExists "backend\alembic\versions\0002_add_sectors_territories_research_runs.py" @'
"""add sectors, territories and research_runs

Revision ID: 0002_add_sectors_territories_research_runs
Revises: 0001_initial_users
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_sectors_territories_research_runs"
down_revision = "0001_initial_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sectors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cnae_code", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sectors_code", "sectors", ["code"], unique=True)
    op.create_index("ix_sectors_status", "sectors", ["status"])

    op.create_table(
        "territories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("territories.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_territories_code", "territories", ["code"], unique=True)
    op.create_index("ix_territories_level", "territories", ["level"])
    op.create_index("ix_territories_parent", "territories", ["parent_id"])

    op.create_table(
        "research_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sector_id", sa.Integer(), sa.ForeignKey("sectors.id"), nullable=False),
        sa.Column("territory_id", sa.Integer(), sa.ForeignKey("territories.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("max_queries", sa.Integer(), nullable=False),
        sa.Column("max_sources", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_runs_user_status", "research_runs", ["user_id", "status"])
    op.create_index("ix_runs_sector_territory", "research_runs", ["sector_id", "territory_id"])


def downgrade() -> None:
    op.drop_index("ix_runs_sector_territory", table_name="research_runs")
    op.drop_index("ix_runs_user_status", table_name="research_runs")
    op.drop_table("research_runs")
    op.drop_index("ix_territories_parent", table_name="territories")
    op.drop_index("ix_territories_level", table_name="territories")
    op.drop_index("ix_territories_code", table_name="territories")
    op.drop_table("territories")
    op.drop_index("ix_sectors_status", table_name="sectors")
    op.drop_index("ix_sectors_code", table_name="sectors")
    op.drop_table("sectors")
'@

# ---------------------------------------------------------------------------
# 3. BACKEND - paquete app y núcleo
# ---------------------------------------------------------------------------
Section "Backend - core"

Write-EmptyFile "backend\app\__init__.py"
Write-EmptyFile "backend\app\core\__init__.py"

Write-FileIfNotExists "backend\app\core\config.py" @'
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "sqlite:///./radar_lab.db"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    SEARXNG_BASE_URL: str = "http://localhost:8080"
    MAX_QUERIES_PER_RESEARCH: int = 10
    MAX_SOURCES_PER_RESEARCH: int = 30
    LOG_LEVEL: str = "INFO"


settings = Settings()
'@

Write-FileIfNotExists "backend\app\core\logging.py" @'
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from app.core.config import settings


def configure_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    file_handler = TimedRotatingFileHandler(
        log_dir / "radar_lab.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(console)
    if not any(isinstance(h, TimedRotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)
'@

Write-FileIfNotExists "backend\app\core\exceptions.py" @'
class DomainError(Exception):
    code = "domain_error"
    status_code = 500

    def __init__(self, detail: str = "Error de dominio"):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(DomainError):
    code = "not_found"
    status_code = 404


class ValidationError(DomainError):
    code = "validation_error"
    status_code = 400


class InfrastructureError(DomainError):
    code = "infrastructure_error"
    status_code = 503
'@

Write-FileIfNotExists "backend\app\core\security.py" @'
from dataclasses import dataclass


@dataclass
class CurrentUser:
    id: int
    email: str
    display_name: str


class AuthProvider:
    def get_current_user(self) -> CurrentUser:
        raise NotImplementedError


class LocalSingleUserProvider(AuthProvider):
    """Proveedor de autenticacion para uso local de un unico usuario.

    No valida tokens. Retorna siempre el usuario local.
    Sustituir por JWTProvider en la fase online.
    """

    def __init__(self) -> None:
        self._user = CurrentUser(
            id=1, email="local@radar-lab", display_name="Local User"
        )

    def get_current_user(self) -> CurrentUser:
        return self._user


_provider: AuthProvider = LocalSingleUserProvider()


def get_current_user() -> CurrentUser:
    return _provider.get_current_user()
'@

# ---------------------------------------------------------------------------
# 4. BACKEND - infraestructura - persistencia
# ---------------------------------------------------------------------------
Section "Backend - persistencia"

Write-EmptyFile "backend\app\infrastructure\__init__.py"
Write-EmptyFile "backend\app\infrastructure\persistence\__init__.py"

Write-FileIfNotExists "backend\app\infrastructure\persistence\database.py" @'
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    future=True,
)

if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'@

Write-FileIfNotExists "backend\app\infrastructure\persistence\models.py" @'
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.infrastructure.persistence.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_users_email", "email", unique=True),)


class Sector(Base):
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    cnae_code = Column(String(16), nullable=True)
    status = Column(String(32), nullable=False, default="preparado")
    parent_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    parent = relationship("Sector", remote_side=[id], backref="children")

    __table_args__ = (
        Index("ix_sectors_code", "code", unique=True),
        Index("ix_sectors_status", "status"),
    )


class Territory(Base):
    __tablename__ = "territories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    level = Column(String(32), nullable=False)
    parent_id = Column(Integer, ForeignKey("territories.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    parent = relationship("Territory", remote_side=[id], backref="children")

    __table_args__ = (
        Index("ix_territories_code", "code", unique=True),
        Index("ix_territories_level", "level"),
        Index("ix_territories_parent", "parent_id"),
    )


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    territory_id = Column(Integer, ForeignKey("territories.id"), nullable=False)
    status = Column(String(32), nullable=False, default="queued")
    max_queries = Column(Integer, nullable=False, default=10)
    max_sources = Column(Integer, nullable=False, default=30)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_runs_user_status", "user_id", "status"),
        Index("ix_runs_sector_territory", "sector_id", "territory_id"),
    )
'@

Write-EmptyFile "backend\app\infrastructure\persistence\repositories\__init__.py"

Write-FileIfNotExists "backend\app\infrastructure\persistence\repositories\sector_repository.py" @'
from typing import List, Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Sector


class SectorRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, status: Optional[str] = None) -> List[Sector]:
        q = self.db.query(Sector)
        if status is not None:
            q = q.filter(Sector.status == status)
        return q.order_by(Sector.id.asc()).all()

    def get_by_code(self, code: str) -> Optional[Sector]:
        return self.db.query(Sector).filter(Sector.code == code).one_or_none()

    def get_by_id(self, sector_id: int) -> Optional[Sector]:
        return self.db.query(Sector).filter(Sector.id == sector_id).one_or_none()
'@

Write-FileIfNotExists "backend\app\infrastructure\persistence\repositories\territory_repository.py" @'
from typing import List, Optional

from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Territory


class TerritoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        level: Optional[str] = None,
        parent_id: Optional[int] = None,
    ) -> List[Territory]:
        q = self.db.query(Territory)
        if level is not None:
            q = q.filter(Territory.level == level)
        if parent_id is not None:
            q = q.filter(Territory.parent_id == parent_id)
        return q.order_by(Territory.id.asc()).all()

    def get_by_code(self, code: str) -> Optional[Territory]:
        return self.db.query(Territory).filter(Territory.code == code).one_or_none()

    def get_by_id(self, territory_id: int) -> Optional[Territory]:
        return self.db.query(Territory).filter(Territory.id == territory_id).one_or_none()
'@

# ---------------------------------------------------------------------------
# 5. BACKEND - interfaces
# ---------------------------------------------------------------------------
Section "Backend - interfaces"

Write-EmptyFile "backend\app\infrastructure\interfaces\__init__.py"

Write-FileIfNotExists "backend\app\infrastructure\interfaces\llm_provider.py" @'
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self, prompt: str, schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Genera una respuesta estructurada. Reservado para el Paso 4."""
        raise NotImplementedError
'@

Write-FileIfNotExists "backend\app\infrastructure\interfaces\search_provider.py" @'
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Ejecuta una busqueda. Reservado para el Paso 5."""
        raise NotImplementedError
'@

# ---------------------------------------------------------------------------
# 6. BACKEND - shared, modules, api
# ---------------------------------------------------------------------------
Section "Backend - shared y modulos"

Write-EmptyFile "backend\app\shared\__init__.py"

Write-FileIfNotExists "backend\app\shared\schemas.py" @'
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
'@

Write-EmptyFile "backend\app\modules\__init__.py"
Write-EmptyFile "backend\app\modules\opportunity_engine\__init__.py"
Write-EmptyFile "backend\app\modules\market_research\__init__.py"

Section "Backend - API"

Write-EmptyFile "backend\app\api\__init__.py"
Write-EmptyFile "backend\app\api\v1\__init__.py"

Write-FileIfNotExists "backend\app\api\health.py" @'
from fastapi import APIRouter

from app.shared.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy", version="0.1.0")
'@

Write-FileIfNotExists "backend\app\api\v1\router.py" @'
from fastapi import APIRouter

from app.api import health as health_module
from app.api.v1 import sectors, territories

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_module.router)
api_router.include_router(sectors.router)
api_router.include_router(territories.router)
'@

Write-FileIfNotExists "backend\app\api\v1\sectors.py" @'
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.sector_repository import (
    SectorRepository,
)
from app.shared.schemas import SectorRead

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("", response_model=List[SectorRead])
def list_sectors(
    status: Optional[str] = Query(None, pattern="^(activo|preparado|archivado)$"),
    db: Session = Depends(get_db),
) -> List[SectorRead]:
    repo = SectorRepository(db)
    return repo.list(status=status)
'@

Write-FileIfNotExists "backend\app\api\v1\territories.py" @'
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories.territory_repository import (
    TerritoryRepository,
)
from app.shared.schemas import TerritoryRead

router = APIRouter(prefix="/territories", tags=["territories"])


@router.get("", response_model=List[TerritoryRead])
def list_territories(
    level: Optional[str] = Query(None, pattern="^(comunidad|provincia)$"),
    parent_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
) -> List[TerritoryRead]:
    repo = TerritoryRepository(db)
    return repo.list(level=level, parent_id=parent_id)
'@

Write-FileIfNotExists "backend\app\main.py" @'
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.exceptions import DomainError
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="RADAR LAB", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.detail},
    )


app.include_router(health_router)
app.include_router(api_router)
'@

# ---------------------------------------------------------------------------
# 7. BACKEND - scripts
# ---------------------------------------------------------------------------
Section "Backend - scripts"

Write-EmptyFile "backend\scripts\__init__.py"

Write-FileIfNotExists "backend\scripts\backup_db.py" @'
"""Copia de seguridad de radar_lab.db."""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    backend_dir = Path(__file__).resolve().parent.parent
    source = backend_dir / "radar_lab.db"
    if not source.exists():
        print(f"ERROR: {source} no existe. Nada que copiar.")
        return 1

    backups_dir = backend_dir.parent / "backups"
    backups_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backups_dir / f"radar_lab_{timestamp}.db"
    shutil.copy2(source, dest)

    conn = sqlite3.connect(str(dest))
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
    finally:
        conn.close()

    if result and result[0] == "ok":
        print(f"backup OK: {dest}")
        return 0
    print(f"ERROR: integridad fallida en {dest}: {result}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
'@

Write-FileIfNotExists "backend\scripts\seed_master_data.py" @'
"""Semilla idempotente de sectores y territorios.

Usa 'code' como identificador estable. No fija IDs numericos.
Ejecutar varias veces no duplica registros ni modifica los existentes.
"""
from typing import Dict

from sqlalchemy.orm import Session

from app.infrastructure.persistence.database import SessionLocal
from app.infrastructure.persistence.models import Sector, Territory

SECTORS = [
    {
        "code": "mantenimiento_reparacion_inmuebles",
        "name": "Mantenimiento y reparacion de inmuebles",
        "status": "activo",
    },
    {
        "code": "administracion_fincas",
        "name": "Administracion de fincas",
        "status": "preparado",
    },
    {
        "code": "instalaciones_eficiencia_energetica",
        "name": "Instalaciones y eficiencia energetica",
        "status": "preparado",
    },
    {
        "code": "reformas_integrales",
        "name": "Reformas integrales",
        "status": "preparado",
    },
    {
        "code": "mantenimiento_industrial",
        "name": "Mantenimiento industrial",
        "status": "preparado",
    },
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
    {"code": "sevilla", "name": "Sevilla", "level": "provincia", "parent_code": "andalucia"},
]


def seed(db: Session) -> Dict[str, int]:
    inserted_s = existing_s = 0
    for data in SECTORS:
        obj = db.query(Sector).filter(Sector.code == data["code"]).one_or_none()
        if obj is None:
            db.add(Sector(code=data["code"], name=data["name"], status=data["status"]))
            inserted_s += 1
        else:
            existing_s += 1
    db.flush()

    inserted_t = existing_t = 0
    for data in TERRITORIES:
        obj = db.query(Territory).filter(Territory.code == data["code"]).one_or_none()
        if obj is not None:
            existing_t += 1
            continue
        parent_id = None
        if data["parent_code"] is not None:
            parent = (
                db.query(Territory)
                .filter(Territory.code == data["parent_code"])
                .one_or_none()
            )
            if parent is None:
                raise RuntimeError(
                    f"parent_code no encontrado: {data['parent_code']}"
                )
            parent_id = parent.id
        db.add(
            Territory(
                code=data["code"],
                name=data["name"],
                level=data["level"],
                parent_id=parent_id,
            )
        )
        inserted_t += 1

    db.commit()
    return {
        "sectores_insertados": inserted_s,
        "sectores_existentes": existing_s,
        "territorios_insertados": inserted_t,
        "territorios_existentes": existing_t,
    }


if __name__ == "__main__":
    with SessionLocal() as db:
        result = seed(db)
        print(result)
'@

Write-FileIfNotExists "backend\scripts\test_paso2_integrity.py" @'
"""Pruebas de integridad del Paso 2 sobre una BD temporal.

No toca backend/radar_lab.db.
"""
import os
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

TEST_DB = "test_paso2.db"


def main() -> int:
    os.chdir(_backend_dir)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB}"

    from app.infrastructure.persistence.database import (  # noqa: E402
        Base,
        SessionLocal,
        engine,
    )
    from app.infrastructure.persistence.models import (  # noqa: F401, E402
        ResearchRun,
        Sector,
        Territory,
        User,
    )
    from scripts.seed_master_data import seed  # noqa: E402

    print("[1] Creando esquema en BD temporal...")
    Base.metadata.create_all(engine)

    print("[2] Semilla primera ejecucion...")
    with SessionLocal() as db:
        r1 = seed(db)
        print(f"    {r1}")

    print("[3] Semilla segunda ejecucion (idempotencia)...")
    with SessionLocal() as db:
        r2 = seed(db)
        print(f"    {r2}")

    print("[4] Verificando conteos y relaciones...")
    with SessionLocal() as db:
        n_s = db.query(Sector).count()
        n_t = db.query(Territory).count()
        n_prov = db.query(Territory).filter(Territory.level == "provincia").count()
        n_act = db.query(Sector).filter(Sector.status == "activo").count()
        assert n_s == 5, f"sectores={n_s}"
        assert n_t == 9, f"territorios={n_t}"
        assert n_prov == 8, f"provincias={n_prov}"
        assert n_act == 1, f"activos={n_act}"
        andalucia = db.query(Territory).filter(Territory.code == "andalucia").one()
        provincias_hijas = (
            db.query(Territory).filter(Territory.parent_id == andalucia.id).count()
        )
        assert provincias_hijas == 8, f"provincias_hijas={provincias_hijas}"
        print(
            f"    sectores={n_s} territorios={n_t} provincias={n_prov} "
            f"activos={n_act} provincias_hijas={provincias_hijas} OK"
        )

    print("[5] Verificando FK activas...")
    from sqlalchemy import text

    with SessionLocal() as db:
        try:
            db.execute(
                text(
                    "INSERT INTO research_runs "
                    "(user_id, sector_id, territory_id, status, max_queries, "
                    " max_sources, created_at, updated_at) "
                    "VALUES (999, 1, 1, 'queued', 10, 30, "
                    "        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                )
            )
            db.commit()
            raise AssertionError("FK no activa: se permitio user_id=999 inexistente")
        except AssertionError:
            raise
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "FOREIGN KEY" in msg:
                print("    FK OK (insercion invalida rechazada)")
            else:
                raise

    print("[6] Limpieza...")
    engine.dispose()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    print("\nTODAS LAS PRUEBAS PASARON")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'@

# ---------------------------------------------------------------------------
# 8. FRONTEND
# ---------------------------------------------------------------------------
Section "Frontend"

Write-FileIfNotExists "frontend\package.json" @'
{
  "name": "radar-lab-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
'@

Write-FileIfNotExists "frontend\tsconfig.json" @'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
'@

Write-FileIfNotExists "frontend\tsconfig.node.json" @'
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
'@

Write-FileIfNotExists "frontend\vite.config.ts" @'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
'@

Write-FileIfNotExists "frontend\index.html" @'
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>RADAR LAB</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
'@

Write-FileIfNotExists "frontend\src\main.tsx" @'
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
'@

Write-FileIfNotExists "frontend\src\App.tsx" @'
import { useEffect, useState } from "react";
import { fetchHealth } from "./api/client";
import type { HealthResponse } from "./types/health";

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>RADAR LAB</h1>
      <p>Fundacion - Paso 1 + Paso 2</p>
      {error && <p style={{ color: "red" }}>Error: {error}</p>}
      {health && (
        <p style={{ color: "green" }}>
          Backend: {health.status} (v{health.version})
        </p>
      )}
      {!health && !error && <p>Cargando estado del backend...</p>}
    </div>
  );
}
'@

Write-FileIfNotExists "frontend\src\api\client.ts" @'
import type { HealthResponse } from "../types/health";

const BASE = "/api";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/v1/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as HealthResponse;
}
'@

Write-FileIfNotExists "frontend\src\types\health.ts" @'
export interface HealthResponse {
  status: string;
  version: string;
}
'@

# ---------------------------------------------------------------------------
# 9. RAÍZ
# ---------------------------------------------------------------------------
Section "Raiz"

Write-FileIfNotExists ".gitignore" @'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
.venv/
*.egg-info/
.pytest_cache/

# Database
*.db
*.db-journal
*.db-shm
*.db-wal

# Logs
logs/

# Env
.env

# Backups
backups/

# Frontend
node_modules/
dist/

# VS Code
.vscode/

# OS
.DS_Store
Thumbs.db
'@

Write-FileIfNotExists "README.md" @'
# RADAR LAB

Plataforma de inteligencia empresarial. Estado actual: **Paso 1 (Fundacion) + Paso 2 (Datos maestros)**.

## Requisitos

- Windows 10 22H2 o superior
- Python 3.12 (añadir al PATH durante la instalacion)
- Node.js 20 LTS

## Ejecucion local

### Backend

    cd backend
    python -m venv venv
    .\venv\Scripts\Activate
    pip install -e .

    # Copiar .env.example a .env si es la primera vez
    Copy-Item .env.example .env

    # Migraciones
    alembic upgrade head
    alembic check

    # Semilla (idempotente, se puede ejecutar varias veces)
    python scripts\seed_master_data.py

    # Arrancar backend
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

### Frontend

    cd frontend
    npm install
    npm run dev

Abrir http://localhost:5173

### Pruebas de integridad (BD temporal, no toca radar_lab.db)

    cd backend
    python scripts\test_paso2_integrity.py

### Endpoints disponibles

- GET /health
- GET /api/v1/health
- GET /api/v1/sectors
- GET /api/v1/sectors?status=activo
- GET /api/v1/territories
- GET /api/v1/territories?level=provincia
- GET /api/v1/territories?parent_id=1

### Backup

    cd backend
    python scripts\backup_db.py
'@

# ---------------------------------------------------------------------------
# 10. Resumen y pasos siguientes
# ---------------------------------------------------------------------------
Write-Host "`n== Estructura creada ==" -ForegroundColor Magenta
Write-Host ""
Write-Host "Pasos siguientes (NO ejecutados automaticamente):" -ForegroundColor Yellow
Write-Host "  1. cd backend"
Write-Host "  2. python -m venv venv"
Write-Host "  3. .\venv\Scripts\Activate"
Write-Host "  4. pip install -e ."
Write-Host "  5. Copy-Item .env.example .env"
Write-Host "  6. alembic upgrade head"
Write-Host "  7. alembic check"
Write-Host "  8. python scripts\seed_master_data.py"
Write-Host "  9. python scripts\seed_master_data.py     (segunda vez, idempotencia)"
Write-Host " 10. python scripts\test_paso2_integrity.py"
Write-Host " 11. uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "Frontend (opcional, en otra terminal):" -ForegroundColor Yellow
Write-Host "  cd frontend"
Write-Host "  npm install"
Write-Host "  npm run dev"
Write-Host ""

if ($RunSetup) {
    Write-Host "`n== Ejecutando setup backend ==" -ForegroundColor Green
    Push-Location backend
    try {
        if (-not (Test-Path "venv")) { python -m venv venv }
        & ".\venv\Scripts\Activate.ps1"
        pip install -e .
        if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
        alembic upgrade head
        alembic check
        python scripts\seed_master_data.py
        python scripts\seed_master_data.py
        if ($RunTests) { python scripts\test_paso2_integrity.py }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "Setup no ejecutado. Usa -RunSetup o sigue los pasos anteriores manualmente." -ForegroundColor Yellow
}