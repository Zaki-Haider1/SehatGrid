import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("JWT_SECRET", "test-secret-for-isolated-pilot-only-32-characters")
os.environ.setdefault("DEMO_PASSWORD", "SehatPilotDemo2026!")
from app.database import Base, make_engine, get_db
from app.main import app
from app.mvp.seed import seed
from app.mvp.store import transaction


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
            r = self.call(path, body, user, method, key)
            assert r.status_code == 200, r.text
            return r.json()

        def edit(self, fn):
            with factory() as db, transaction(db) as s:
                return fn(s)

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
