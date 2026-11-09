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