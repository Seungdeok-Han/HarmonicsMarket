"""add_is_featured_to_myinstrument

Revision ID: a1b2c3d4e5f6
Revises: fcacdba52970
Create Date: 2025-12-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fcacdba52970'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('my_instrument', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_featured', sa.Boolean(), nullable=True))
        # Optional: set default False for existing rows
        # Note: For SQLite, server_default may not be applied retroactively
    

def downgrade():
    with op.batch_alter_table('my_instrument', schema=None) as batch_op:
        batch_op.drop_column('is_featured')
