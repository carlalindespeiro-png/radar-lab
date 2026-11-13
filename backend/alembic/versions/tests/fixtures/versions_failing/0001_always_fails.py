"""always fails"""
from alembic import op  # noqa: F401

revision = "0001_always_fails"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    raise RuntimeError("migración ficticia forzada a fallar")


def downgrade() -> None:
    pass