import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import select, text
from app.directory import load_directory, LEGACY_NAMES
from app.models import Facility
from app.seed import seed
from app.main import today
from app.database import make_engine


def test_real_directory_export_and_unreported_capacity(client):
    api, _ = client
    exported = api.get("/api/export").json()["facilities"]
    pims = next(f for f in exported if "PIMS" in f["name"])
    assert pims["latitude"] == 33.7022691 and pims["longitude"] == 73.0525291
    assert pims["profile"]["coordinate_source"] == "https://www.openstreetmap.org/way/22328601"
    assert pims["profile"]["sector"] == "G-8/3"
    assert pims["capacity_mode"] == "simulated"
    assert all(f["profile"]["checked_on"] and f["profile"]["directory_sources"] for f in exported)
    # Additional directory hospitals have unknown demo availability, not zero real capacity.
    cda = next(f for f in exported if "CDA" in f["name"])
    assert cda["capacities"] == []
    config = api.get("/api/config").json()
    assert config["city"] == "Islamabad" and config["capacity_mode"] == "simulated"


def test_directory_sync_preserves_demo_state_and_upgrades_legacy_ids(client):
    api, factory = client
    day = today().isoformat()
    api.put("/api/facilities/2/capacity", json={"service_id": 1, "day": day, "total": 77})
    before = api.get("/api/export").json()
    with factory() as db:
        pims = db.get(Facility, 2)
        pims.name, pims.source_key = LEGACY_NAMES[1], None
        pims.latitude, pims.longitude, pims.profile = 24.916, 67.052, {}
        db.commit()
        seed(db, today())
        seed(db, today())
        assert len(db.scalars(select(Facility)).all()) == 12
        assert db.get(Facility, 2).name == "Pakistan Institute of Medical Sciences (PIMS)"
    after = api.get("/api/export").json()
    assert before == after


def test_directory_rejects_duplicate_and_out_of_city_research_records():
    records = load_directory()
    assert len({r["source_key"] for r in records}) == len(records)
    assert len({(r["latitude"], r["longitude"]) for r in records}) == len(records)
    assert all(33.60 < r["latitude"] < 33.75 and 72.95 < r["longitude"] < 73.20 for r in records)
    assert all(r["profile"]["ownership"] in {"Public", "Private"} for r in records)
    fgh = next(r for r in records if r["source_key"] == "federal-general-chak-shahzad")
    # Keep the hospital's explicit DMS pin, not the Google embed's viewport centre.
    assert fgh["longitude"] == 73.1381667


def test_existing_sqlite_migration_preserves_foreign_keys(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing.db'}"
    backend = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": database_url}

    def upgrade(revision):
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=backend,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

    upgrade("763866885016")
    engine = make_engine(database_url)
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO facilities (id,name,zone,kind,latitude,longitude) VALUES (1,'Legacy','Central','Hospital',24.9,67.0)"
            )
        )
        db.execute(
            text("INSERT INTO services (id,name,aliases,unit_cost) VALUES (1,'Consultation','checkup',800)")
        )
        db.execute(
            text(
                "INSERT INTO capacities (id,facility_id,service_id,day,total,reserved,consumed) VALUES (1,1,1,'2026-10-10',8,1,2)"
            )
        )
    upgrade("head")
    with engine.connect() as db:
        assert db.execute(text("SELECT total,reserved,consumed FROM capacities")).one() == (8, 1, 2)
        assert db.execute(text("SELECT profile FROM facilities")).scalar() == "{}"
        assert db.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()
