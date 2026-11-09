"""add reports and watchdog fields

Revision ID: 0004_add_reports_and_watchdog_fields
Revises: 0003_add_research_tables
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_add_reports_and_watchdog_fields"
down_revision = "0003_add_research_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Añadir columnas de Watchdog a research_runs
    op.add_column("research_runs", sa.Column("lock_id", sa.String(length=36), nullable=True))
    op.add_column("research_runs", sa.Column("locked_at", sa.DateTime(), nullable=True))

    # 2. Añadir restricción UNIQUE a queries usando batch_alter_table (necesario en SQLite)
    with op.batch_alter_table("queries", schema=None) as batch_op:
        batch_op.create_unique_constraint("uq_query_run_text", ["research_run_id", "query_text"])

    # 3. Crear la tabla reports (historial de PDFs)
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("research_run_id", sa.Integer(), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_reports_run_id", "reports", ["research_run_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_run_id", table_name="reports")
    op.drop_table("reports")
    
    with op.batch_alter_table("queries", schema=None) as batch_op:
        batch_op.drop_constraint("uq_query_run_text", type_="unique")
        
    op.drop_column("research_runs", "locked_at")
    op.drop_column("research_runs", "lock_id")