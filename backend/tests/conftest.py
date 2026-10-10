import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.database import Base, make_engine, get_db
from app.main import app, today
from tests.seed_helpers import seed_legacy


@pytest.fixture(params=["sqlite"] + (["postgresql"] if os.environ.get("TEST_DATABASE_URL") else []))
def client(request, tmp_path):
    schema = None
    admin = None
    if request.param == "postgresql":
        admin = make_engine(os.environ["TEST_DATABASE_URL"])
        schema = f"test_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = admin.execution_options(schema_translate_map={None: schema})
    else:
        engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        seed_legacy(session, today())

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    # No lifespan: isolate fixtures from the real app database and startup seed.
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.clear()
        if schema:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


@pytest.fixture(params=["sqlite"] + (["postgresql"] if os.environ.get("TEST_DATABASE_URL") else []))
def empty_session(request, tmp_path):
    admin = None
    schema = None
    if request.param == "postgresql":
        admin = make_engine(os.environ["TEST_DATABASE_URL"])
        schema = f"test_{uuid4().hex}"
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = admin.execution_options(schema_translate_map={None: schema})
    else:
        engine = make_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        with factory() as session:
            yield session
    finally:
        if schema:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
