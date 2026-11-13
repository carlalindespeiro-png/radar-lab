"""add analyzing v1 fields and partial_reason
Revision ID: 0006
Revises: 0005_add_research_run_sources_and_extract_status
"""
from alembic import op
import sqlalchemy as sa
revision = "0006"
down_revision = "0005_add_research_run_sources_and_extract_status"
branch_labels = None
depends_on = None
def _foreign_key_check(bind):
    violations = bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise RuntimeError(f"foreign_key_check failed: {violations}")
def upgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table("evidence", recreate="always") as batch:
        batch.add_column(sa.Column("clasificacion_evidencia", sa.String(32), nullable=True))
        batch.add_column(sa.Column("limitaciones_evidencia", sa.Text(), nullable=True))
        batch.add_column(sa.Column("posicion_inicio", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("posicion_fin", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("cita_hash", sa.String(64), nullable=True))
        batch.create_index(
            "ix_evidence_cita_unique", ["assertion_id", "cita_hash"], unique=True,
        )
    with op.batch_alter_table("assertions", recreate="always") as batch:
        batch.add_column(sa.Column(
            "extract_id", sa.Integer(),
            sa.ForeignKey("extracts.id", ondelete="CASCADE", name="fk_assertions_extract_id"),
            nullable=True,
        ))
        batch.add_column(sa.Column("assertion_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("nivel_inferencia", sa.String(32), nullable=True))
        batch.create_index(
            "ix_assertions_idem_unique",
            ["problem_id", "extract_id", "assertion_hash"], unique=True,
        )
    with op.batch_alter_table("problems", recreate="always") as batch:
        batch.add_column(sa.Column(
            "es_empresa_competidora", sa.Integer(),
            nullable=False, server_default="0",
        ))
        batch.add_column(sa.Column("normalized_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("normalized_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("solucion_existente_mencionada", sa.Text(), nullable=True))
        batch.add_column(sa.Column("necesidad_software_inferida", sa.Integer(), nullable=True))
        batch.create_index("ix_problems_normalized_hash", ["normalized_hash"])
    op.add_column("research_runs", sa.Column("partial_reason", sa.String(64), nullable=True))
    _foreign_key_check(bind)
def downgrade() -> None:
    bind = op.get_bind()
    op.drop_column("research_runs", "partial_reason")
    with op.batch_alter_table("problems", recreate="always") as batch:
        batch.drop_index("ix_problems_normalized_hash")
        batch.drop_column("necesidad_software_inferida")
        batch.drop_column("solucion_existente_mencionada")
        batch.drop_column("normalized_hash")
        batch.drop_column("normalized_text")
        batch.drop_column("es_empresa_competidora")
    with op.batch_alter_table("assertions", recreate="always") as batch:
        batch.drop_index("ix_assertions_idem_unique")
        batch.drop_column("nivel_inferencia")
        batch.drop_column("assertion_hash")
        batch.drop_column("extract_id")
    with op.batch_alter_table("evidence", recreate="always") as batch:
        batch.drop_index("ix_evidence_cita_unique")
        batch.drop_column("cita_hash")
        batch.drop_column("posicion_fin")
        batch.drop_column("posicion_inicio")
        batch.drop_column("limitaciones_evidencia")
        batch.drop_column("clasificacion_evidencia")
    _foreign_key_check(bind)
