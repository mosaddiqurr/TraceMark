"""Initial TraceMark relational schema.

Revision ID: 0001
Revises: None
"""

from alembic import op
from tracemark_api import models  # noqa: F401
from tracemark_api.database import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)

