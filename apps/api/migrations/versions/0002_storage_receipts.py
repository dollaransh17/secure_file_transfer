"""Durable inbox for idempotent exact-version storage notifications."""
from alembic import op
from prooflane.db import StorageReceipt
revision='0002'
down_revision='0001'

def upgrade():StorageReceipt.__table__.create(bind=op.get_bind(),checkfirst=True)
def downgrade():StorageReceipt.__table__.drop(bind=op.get_bind(),checkfirst=True)
