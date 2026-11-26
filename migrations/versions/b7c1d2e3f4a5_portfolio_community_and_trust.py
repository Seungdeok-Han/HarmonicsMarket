"""portfolio: community tables, trust fields, constraints

Revision ID: b7c1d2e3f4a5
Revises: 3275a3e64fe2
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7c1d2e3f4a5'
down_revision = '3275a3e64fe2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=128),
            type_=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column('bio', sa.String(length=280), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('related_post_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_message_related_post',
            'instrument_post',
            ['related_post_id'],
            ['id'],
        )

    op.create_table(
        'community_post',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('image', sa.String(length=255), nullable=True),
        sa.Column('media', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.add_column(sa.Column('community_post_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_notification_community_post',
            'community_post',
            ['community_post_id'],
            ['id'],
        )

    op.create_table(
        'community_like',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['community_post.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', name='uix_community_like'),
    )

    op.create_table(
        'community_comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['community_comment.id']),
        sa.ForeignKeyConstraint(['post_id'], ['community_post.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'community_comment_like',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['comment_id'], ['community_comment.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'comment_id', name='uix_community_comment_like'),
    )

    # Deduplicate likes before unique constraint (keep lowest id)
    op.execute(
        """
        DELETE FROM "like"
        WHERE id NOT IN (
            SELECT MIN(id) FROM "like" GROUP BY user_id, post_id
        )
        """
    )
    with op.batch_alter_table('like', schema=None) as batch_op:
        batch_op.create_unique_constraint('uix_like_user_post', ['user_id', 'post_id'])


def downgrade():
    with op.batch_alter_table('like', schema=None) as batch_op:
        batch_op.drop_constraint('uix_like_user_post', type_='unique')

    op.drop_table('community_comment_like')
    op.drop_table('community_comment')
    op.drop_table('community_like')

    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_constraint('fk_notification_community_post', type_='foreignkey')
        batch_op.drop_column('community_post_id')

    op.drop_table('community_post')

    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_constraint('fk_message_related_post', type_='foreignkey')
        batch_op.drop_column('related_post_id')

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('bio')
        batch_op.alter_column(
            'password_hash',
            existing_type=sa.String(length=255),
            type_=sa.String(length=128),
            existing_nullable=False,
        )
