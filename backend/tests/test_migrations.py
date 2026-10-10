from pathlib import Path
from uuid import uuid4

import os
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import make_url

from app.database import make_engine
from app.models import Base


REQUIRED_TABLES = {
    "zones", "users", "user_facilities", "facility_services", "facility_participation_events",
    "capacity_reservations", "match_reviews", "monthly_budgets", "budget_ledger_entries",
    "subsidy_rules", "offers", "partner_quota_offers", "mobile_unit_offers", "demand_snapshots",
    "plan_actions", "audit_events", "seed_metadata",
}


@pytest.fixture(params=["sqlite"] + (["postgresql"] if os.environ.get("TEST_DATABASE_URL") else []))
def migration_urls(request, tmp_path):
    admin = None
    schemas = []
    if request.param == "postgresql":
        admin = make_engine(os.environ["TEST_DATABASE_URL"])
        urls = []
        for _ in range(2):
            schema = f"t01_{uuid4().hex}"
            schemas.append(schema)
            with admin.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            urls.append(
                make_url(os.environ["TEST_DATABASE_URL"])
                .update_query_dict({"options": f"-csearch_path={schema}"})
                .render_as_string(hide_password=False)
            )
    else:
        urls = [f"sqlite:///{tmp_path / f'migration-{index}.db'}" for index in range(2)]
    yield urls
    if admin:
        with admin.begin() as connection:
            for schema in schemas:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def run_migration(url, target, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.upgrade(cfg, target)
    get_settings.cache_clear()


def check_migration(url, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    command.check(cfg)
    get_settings.cache_clear()


def test_alembic_fresh_and_upgrade_preserves_legacy_rows(migration_urls, monkeypatch):
    fresh_url, upgrade_url = migration_urls
    run_migration(fresh_url, "head", monkeypatch)
    check_migration(fresh_url, monkeypatch)
    fresh_engine = make_engine(fresh_url)
    try:
        fresh_tables = set(inspect(fresh_engine).get_table_names())
        assert REQUIRED_TABLES <= fresh_tables
        assert set(Base.metadata.tables) <= fresh_tables
        inspector = inspect(fresh_engine)
        for table_name, table in Base.metadata.tables.items():
            db_columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert {column.name for column in table.columns} <= db_columns
        request_columns = {column["name"]: column for column in inspector.get_columns("care_requests")}
        assert request_columns["service_id"]["nullable"] is True
        capacity_checks = {item["name"] for item in inspector.get_check_constraints("capacities")}
        assert {"ck_capacities_legacy_nonnegative", "ck_capacities_forfeited_nonnegative", "ck_capacities_target_available", "ck_capacities_freshness_status", "ck_capacities_version"} <= capacity_checks
        for table, expected in {
            "facilities": {"ck_facilities_ownership", "ck_facilities_participation_status", "ck_facilities_participation_version"},
            "care_requests": {"ck_care_requests_priority", "ck_care_requests_status"},
            "allocation_plans": {"ck_allocation_plans_nonnegative", "ck_allocation_plans_status", "ck_allocation_plans_version"},
        }.items():
            constraints = {item["name"] for item in inspector.get_check_constraints(table)}
            assert expected <= constraints
    finally:
        fresh_engine.dispose()

    run_migration(upgrade_url, "763866885016", monkeypatch)
    legacy_engine = make_engine(upgrade_url)
    try:
        with legacy_engine.begin() as connection:
            connection.execute(text("INSERT INTO facilities (id, name, zone, kind, latitude, longitude) VALUES (41, 'Legacy Clinic', 'Central', 'Clinic', 33.7, 73.0)"))
            connection.execute(text("INSERT INTO services (id, name, aliases, unit_cost) VALUES (12, 'Legacy Service', 'legacy', 400)"))
            connection.execute(text("INSERT INTO capacities (id, facility_id, service_id, day, total, reserved, consumed) VALUES (21, 41, 12, '2026-10-10', 7, 1, 2)"))
            connection.execute(text("INSERT INTO care_requests (id, reference, service_id, zone, day, priority, status, reason, created_at) VALUES (31, 'LEGACY-REQ', 12, 'Central', '2026-10-10', 'routine', 'pending', NULL, '2026-10-10 00:00:00')"))
            connection.execute(text("INSERT INTO referrals (id, request_id, capacity_id, status, created_at) VALUES (61, 31, 21, 'confirmed', '2026-10-10 00:00:00')"))
            connection.execute(text("INSERT INTO budgets (id, total, committed) VALUES (71, 25000, 1200)"))
            connection.execute(text("INSERT INTO allocation_plans (id, day, cost, units, allocations, status, created_at) VALUES (51, '2026-10-10', 400, 1, '[]', 'draft', '2026-10-10 00:00:00')"))
        legacy_engine.dispose()
        run_migration(upgrade_url, "head", monkeypatch)
        check_migration(upgrade_url, monkeypatch)
        legacy_engine = make_engine(upgrade_url)
        with legacy_engine.connect() as connection:
            facility = connection.execute(text("SELECT id, public_id, participation_status, zone_id FROM facilities WHERE id=41")).one()
            service = connection.execute(text("SELECT id, code, review_status FROM services WHERE id=12")).one()
            capacity = connection.execute(text("SELECT id, total, reserved, consumed, freshness_status, forfeited_units FROM capacities WHERE id=21")).one()
            request = connection.execute(text("SELECT id, reference, status, public_id, zone_id, service_id FROM care_requests WHERE id=31")).one()
            referral = connection.execute(text("SELECT id, request_id, capacity_id, status FROM referrals WHERE id=61")).one()
            budget = connection.execute(text("SELECT id, total, committed FROM budgets WHERE id=71")).one()
            plan = connection.execute(text("SELECT id, status, version FROM allocation_plans WHERE id=51")).one()
        assert facility == (41, "FAC-LEGACY-41", "PENDING", "Central")
        assert service == (12, "LEGACY-SERVICE-12", "NEEDS_REVIEW")
        assert capacity == (21, 7, 1, 2, "UNKNOWN", 0)
        assert request == (31, "LEGACY-REQ", "pending", "REQ-LEGACY-31", "Central", 12)
        assert referral == (61, 31, 21, "confirmed")
        assert budget == (71, 25000, 1200)
        assert plan == (51, "draft", 1)
    finally:
        legacy_engine.dispose()


def test_database_rejects_invalid_shared_integrity_rows(empty_session):
    from datetime import date, datetime, timezone
    from sqlalchemy import func, insert, select
    from app.models import Facility, FacilityService, Service
    from app.seed import seed

    session = empty_session
    seed(session, date(2026, 10, 10), clock=datetime(2026, 10, 10, tzinfo=timezone.utc))
    facility_id = session.scalar(select(Facility.id).limit(1))
    service_id = session.scalar(select(Service.id).limit(1))
    assert facility_id and service_id
    with pytest.raises(IntegrityError) as error:
        session.execute(insert(FacilityService).values(
            facility_id=facility_id, service_id=service_id, active=True,
            eligible_zone_ids=[], suitability_restrictions=[], review_id="invalid",
            version=0, updated_at=datetime(2026, 10, 10, tzinfo=timezone.utc),
        ))
        session.commit()
    session.rollback()
    assert "version" in str(error.value).lower()
    assert session.scalar(select(func.count()).select_from(FacilityService)) == 8
