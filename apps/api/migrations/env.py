from alembic import context
from prooflane.db import Base,engine
config=context.config
def run():
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=True)
        with context.begin_transaction(): context.run_migrations()
run()
