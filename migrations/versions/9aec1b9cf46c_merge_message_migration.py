"""merge message migration

Revision ID: 9aec1b9cf46c
Revises: b946f6cbdc93, f3a9b1c2d4e5
Create Date: 2025-12-20 04:53:44.439318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9aec1b9cf46c'
down_revision = ('b946f6cbdc93', 'f3a9b1c2d4e5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
