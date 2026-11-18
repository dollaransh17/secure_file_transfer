"""Separate shared download permission; existing grants remain read-only."""
from alembic import op
import sqlalchemy as sa
revision='0003'
down_revision='0002'
def upgrade():
    # Initial migration imports live metadata, so fresh databases already have this field.
    if 'can_download' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('file_permissions')}:
        op.add_column('file_permissions',sa.Column('can_download',sa.Boolean(),nullable=False,server_default=sa.false()))
def downgrade():
    op.drop_column('file_permissions','can_download')
