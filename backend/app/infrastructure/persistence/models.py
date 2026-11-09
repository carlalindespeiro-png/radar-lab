from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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

    # Campos para el Watchdog (Fase 4.5.1)
    lock_id = Column(String(36), nullable=True)
    locked_at = Column(DateTime, nullable=True)

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


class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    query_text = Column(String(500), nullable=False)
    engine = Column(String(50), nullable=False, default="searxng")
    status = Column(String(32), nullable=False, default="pending")
    result_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_queries_run_id", "research_run_id"),
        UniqueConstraint('research_run_id', 'query_text', name='uq_query_run_text'),
    )


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(1000), nullable=False)
    normalized_url = Column(String(1000), nullable=False)
    domain = Column(String(255), nullable=False)
    title = Column(String(500), nullable=True)
    published_at = Column(DateTime, nullable=True)
    accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source_type = Column(String(50), nullable=False, default="unknown")
    status = Column(String(32), nullable=False, default="accessible")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_sources_normalized_url", "normalized_url", unique=True),)


class ResearchRunSource(Base):
    __tablename__ = "research_run_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("research_run_id", "source_id", name="uq_run_source"),
        Index("ix_run_sources_run_id", "research_run_id"),
    )


class Extract(Base):
    __tablename__ = "extracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    extraction_method = Column(String(50), nullable=False, default="trafilatura")
    char_count = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="invalid")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_extracts_source_id", "source_id"),
        UniqueConstraint('source_id', name='uq_extracts_source_id'),
    )


class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(32), nullable=False, default="media")
    software_solvable = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_problems_run_id", "research_run_id"),)


class Assertion(Base):
    __tablename__ = "assertions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    assertion_type = Column(String(32), nullable=False, default="hipotesis")
    confidence = Column(Integer, nullable=False, default=50)
    created_by = Column(String(32), nullable=False, default="llm")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_assertions_problem_id", "problem_id"),)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assertion_id = Column(Integer, ForeignKey("assertions.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    extract_id = Column(Integer, ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False)
    excerpt = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_evidence_assertion_id", "assertion_id"),
        Index("ix_evidence_unique", "assertion_id", "source_id", "extract_id", unique=True)
    )


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(500), nullable=False)
    proposed_solution = Column(Text, nullable=True)
    score_total = Column(Integer, nullable=False, default=0)
    score_breakdown = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="detectada")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("ix_opportunities_run_id", "research_run_id"),)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    research_run_id = Column(Integer, ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(32), nullable=False, default="pdf")
    file_path = Column(String(1000), nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_reports_run_id", "research_run_id"),
    )