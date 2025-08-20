from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Initial tables created by SQLAlchemy on first run; this migration reserved for future
    pass


def downgrade():
    pass

