"""Add scope-v1 pilot aggregate without destroying legacy demo records."""

from alembic import op
import sqlalchemy as sa

revision = "d100_scope_v1"
down_revision = "c0e52422dfe5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pilot_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table("pilot_state")
