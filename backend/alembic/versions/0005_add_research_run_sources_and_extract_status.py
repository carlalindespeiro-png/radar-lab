"""add research_run_sources and extract status

Revision ID: 0005_add_research_run_sources_and_extract_status
Revises: 0004_add_reports_and_watchdog_fields
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_add_research_run_sources_and_extract_status"
down_revision = "0004_add_reports_and_watchdog_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Comprobación de duplicados (bloqueante)
    conn = op.get_bind()
    duplicates = conn.execute(
        sa.text("SELECT source_id, COUNT(*) FROM extracts GROUP BY source_id HAVING COUNT(*) > 1")
    ).fetchall()
    if duplicates:
        raise RuntimeError(f"Migración 0005 abortada: existen source_id duplicados en extracts: {duplicates}")

    # 2. Añadir columna status a extracts (nullable inicialmente para el backfill)
    op.add_column("extracts", sa.Column("status", sa.String(length=32), nullable=True))

    # 3. Backfill de datos (los >= 200 caracteres y con contenido válido son 'valid')
    conn.execute(sa.text(
        "UPDATE extracts SET status = 'valid' "
        "WHERE char_count >= 200 AND content IS NOT NULL AND LENGTH(TRIM(content)) > 0"
    ))
    conn.execute(sa.text("UPDATE extracts SET status = 'invalid' WHERE status IS NULL"))

    # 4. Hacer status NOT NULL y añadir UNIQUE(source_id) usando batch_alter_table
    with op.batch_alter_table("extracts", schema=None) as batch_op:
        batch_op.alter_column("status", existing_type=sa.String(length=32), nullable=False)
        batch_op.create_unique_constraint("uq_extracts_source_id", ["source_id"])

    # 5. Crear tabla intermedia research_run_sources
    op.create_table(
        "research_run_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("research_run_id", sa.Integer(), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("research_run_id", "source_id", name="uq_run_source")
    )
    op.create_index("ix_run_sources_run_id", "research_run_sources", ["research_run_id"])


def downgrade() -> None:
    # 1. Eliminar tabla research_run_sources
    op.drop_index("ix_run_sources_run_id", table_name="research_run_sources")
    op.drop_table("research_run_sources")

    # 2. Revertir cambios en extracts
    with op.batch_alter_table("extracts", schema=None) as batch_op:
        batch_op.drop_constraint("uq_extracts_source_id", type_="unique")
        batch_op.drop_column("status")