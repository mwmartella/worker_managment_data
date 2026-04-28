"""absence_reasons_create_table

Revision ID: 344a9c74ed82
Revises: 3393f9d9f724
Create Date: 2026-04-29 06:41:45.196714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '344a9c74ed82'
down_revision: Union[str, Sequence[str], None] = '3393f9d9f724'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TABLE IF NOT EXISTS absence_reasons (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL UNIQUE, notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS absence_reasons")
