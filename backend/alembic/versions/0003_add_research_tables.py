"""add research tables

Revision ID: 0003_add_research_tables
Revises: 0002_add_sectors_territories_research_runs
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_add_research_tables"
down_revision = "0002_add_sectors_territories_research_runs"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("research_run_id", sa.Integer(), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.String(length=500), nullable=False),
        sa.Column("engine", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_queries_run_id", "queries", ["research_run_id"])

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("normalized_url", sa.String(length=1000), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sources_normalized_url", "sources", ["normalized_url"], unique=True)

    op.create_table(
        "extracts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(length=50), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_extracts_source_id", "extracts", ["source_id"])

    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("research_run_id", sa.Integer(), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("software_solvable", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_problems_run_id", "problems", ["research_run_id"])

    op.create_table(
        "assertions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("assertion_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_assertions_problem_id", "assertions", ["problem_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("assertion_id", sa.Integer(), sa.ForeignKey("assertions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extract_id", sa.Integer(), sa.ForeignKey("extracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_evidence_assertion_id", "evidence", ["assertion_id"])
    op.create_index("ix_evidence_unique", "evidence", ["assertion_id", "source_id", "extract_id"], unique=True)

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("research_run_id", sa.Integer(), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("problems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("proposed_solution", sa.Text(), nullable=True),
        sa.Column("score_total", sa.Integer(), nullable=False),
        sa.Column("score_breakdown", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_opportunities_run_id", "opportunities", ["research_run_id"])

def downgrade() -> None:
    op.drop_index("ix_opportunities_run_id", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index("ix_evidence_unique", table_name="evidence")
    op.drop_index("ix_evidence_assertion_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_assertions_problem_id", table_name="assertions")
    op.drop_table("assertions")
    op.drop_index("ix_problems_run_id", table_name="problems")
    op.drop_table("problems")
    op.drop_index("ix_extracts_source_id", table_name="extracts")
    op.drop_table("extracts")
    op.drop_index("ix_sources_normalized_url", table_name="sources")
    op.drop_table("sources")
    op.drop_index("ix_queries_run_id", table_name="queries")
    op.drop_table("queries")