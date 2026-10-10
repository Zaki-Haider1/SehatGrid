"""Add sourced Islamabad hospital profiles

Revision ID: c0e52422dfe5
Revises: 763866885016
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "c0e52422dfe5"
down_revision: Union[str, Sequence[str], None] = "763866885016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Native ADD COLUMN preserves referenced facility rows on SQLite and PostgreSQL.
    op.add_column("facilities", sa.Column("source_key", sa.String(length=80), nullable=True))
    op.add_column(
        "facilities", sa.Column("profile", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
    )
    op.create_index("ix_facilities_source_key", "facilities", ["source_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_facilities_source_key", table_name="facilities")
    op.drop_column("facilities", "profile")
    op.drop_column("facilities", "source_key")
