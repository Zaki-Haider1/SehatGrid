from alembic import context
from app.config import get_settings
from app.database import Base, make_engine
from app import models  # noqa: F401
from app.mvp import store  # noqa: F401

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(get_settings().database_url)
    with engine.connect() as connection:
        if engine.dialect.name == "sqlite":
            # SQLite table rebuilds need FK enforcement paused while dependent
            # tables continue to reference the table being copied. The rebuilt
            # tables retain their declared foreign keys, which are re-enabled
            # for every application connection by make_engine.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=engine.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
