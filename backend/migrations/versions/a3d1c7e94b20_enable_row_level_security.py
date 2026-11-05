"""enable row level security

Supabase can serve tables in the public schema through its Data API. With RLS on and no
policies, that API sees no rows, while the app's table-owner connection is unaffected.

Revision ID: a3d1c7e94b20
Revises: f80e7c92a73f
Create Date: 2026-11-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a3d1c7e94b20'
down_revision: Union[str, Sequence[str], None] = 'f80e7c92a73f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('users', 'symptom_entries', 'doctor_access', 'alembic_version')


def upgrade() -> None:
    for table in TABLES:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in TABLES:
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')
