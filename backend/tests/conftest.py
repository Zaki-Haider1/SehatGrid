import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("JWT_SECRET", "test-secret-for-isolated-pilot-only-32-characters")
os.environ.setdefault("DEMO_PASSWORD", "SehatPilotDemo2026!")

from app import models  # noqa: E402,F401
from app.database import Base, get_db, make_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.mvp import store  # noqa: E402,F401
from app.mvp.seed import seed  # noqa: E402
from tests.legacy_app import app as legacy_app, today  # noqa: E402
from tests.seed_helpers import seed_legacy  # noqa: E402


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
        engine = make_engine(f"sqlite:///{tmp_path / 'legacy-test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        seed_legacy(session, today())

    def override():
        with factory() as session:
            yield session

    legacy_app.dependency_overrides[get_db] = override
    try:
        yield TestClient(legacy_app), factory
    finally:
        legacy_app.dependency_overrides.clear()
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


@pytest.fixture(params=["sqlite"] + (["postgresql"] if os.environ.get("TEST_DATABASE_URL") else []))
def pilot(request, tmp_path):
    schema = None
    admin = None
    if request.param == "postgresql":
        admin = make_engine(os.environ["TEST_DATABASE_URL"])
        schema = "test_" + uuid4().hex
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = admin.execution_options(schema_translate_map={None: schema})
    else:
        engine = make_engine(f"sqlite:///{tmp_path / 'pilot.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        seed(db)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    client = TestClient(app)

    class Pilot:
        def __init__(self):
            self.client = client
            self.factory = factory
            self.tokens = {}

        def token(self, user="planner"):
            if user not in self.tokens:
                response = client.post(
                    "/api/v1/auth/login", json={"username": user, "password": os.environ["DEMO_PASSWORD"]}
                )
                assert response.status_code == 200, response.text
                self.tokens[user] = response.json()["token"]
            return self.tokens[user]

        def call(self, path, body=None, user="planner", method=None, key=None):
            return client.request(
                method or ("GET" if body is None else "POST"),
                "/api/v1/" + path,
                json=body,
                headers={
                    "Authorization": "Bearer " + self.token(user),
                    "Idempotency-Key": key or str(uuid4()),
                },
            )

        def ok(self, path, body=None, user="planner", method=None, key=None):
            response = self.call(path, body, user, method, key)
            assert response.status_code == 200, response.text
            return response.json()

        def edit(self, fn):
            with factory() as db, store.transaction(db) as state:
                return fn(state)

        def state(self):
            return self.ok("state")

    try:
        yield Pilot()
    finally:
        app.dependency_overrides.clear()
        if schema:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()
