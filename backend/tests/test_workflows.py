from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from app.main import today


def test_ci_container_build_uses_repository_root_context():
    workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"
    assert (
        "      - name: Build deployment container\n"
        "        working-directory: .\n"
        "        run: docker build -f backend/Dockerfile -t sehat-grid-api ."
    ) in workflow.read_text(encoding="utf-8")


def new_request(api, service_id=1, zone="Central", priority="routine"):
    result = api.post(
        "/api/requests",
        json={"service_id": service_id, "zone": zone, "priority": priority, "day": today().isoformat()},
    )
    assert result.status_code == 201, result.text
    return result.json()


def reserve_request(api):
    request = new_request(api)
    provider = request["recommendations"][0]["facility_id"]
    result = api.post(f"/api/requests/{request['id']}/reserve", json={"facility_id": provider})
    assert result.status_code == 201, result.text
    return request, result.json(), provider


def capacity(api, provider, service=1):
    facility = next(f for f in api.get("/api/facilities").json() if f["id"] == provider)
    return next(c for c in facility["capacities"] if c["service_id"] == service)


def test_referral_journey_and_completion_consumes_slot(client):
    api, _ = client
    request, referral, provider = reserve_request(api)
    before = capacity(api, provider)
    assert api.post(f"/api/referrals/{referral['id']}/complete").status_code == 409
    assert api.post(f"/api/referrals/{referral['id']}/confirm").status_code == 200
    assert api.post(f"/api/referrals/{referral['id']}/complete").status_code == 200
    after = capacity(api, provider)
    assert after["reserved"] == before["reserved"] - 1
    assert after["consumed"] == before["consumed"] + 1
    assert after["available"] == before["available"]
    assert api.post(f"/api/referrals/{referral['id']}/complete").status_code == 409
    row = next(r for r in api.get("/api/requests").json() if r["id"] == request["id"])
    assert row["status"] == "completed"


def test_duplicate_reservation_does_not_consume_another_slot(client):
    api, _ = client
    request, _, provider = reserve_request(api)
    before = capacity(api, provider)
    assert (
        api.post(f"/api/requests/{request['id']}/reserve", json={"facility_id": provider}).status_code == 409
    )
    assert capacity(api, provider) == before


def test_cancel_releases_slot_and_reopens_request(client):
    api, _ = client
    request, referral, provider = reserve_request(api)
    before = capacity(api, provider)
    assert api.post(f"/api/referrals/{referral['id']}/cancel").status_code == 200
    assert api.post(f"/api/referrals/{referral['id']}/cancel").status_code == 409
    assert capacity(api, provider)["available"] == before["available"] + 1
    assert (
        api.post(f"/api/requests/{request['id']}/reserve", json={"facility_id": provider}).status_code == 201
    )


def test_capacity_cannot_be_reduced_below_bookings(client):
    api, _ = client
    _, _, provider = reserve_request(api)
    result = api.put(
        f"/api/facilities/{provider}/capacity", json={"service_id": 1, "total": 0, "day": today().isoformat()}
    )
    assert result.status_code == 409
    assert capacity(api, provider)["reserved"] == 1


def test_failed_reservation_rolls_back_request(client):
    api, _ = client
    request = new_request(api, 5, "South")
    assert api.post(f"/api/requests/{request['id']}/reserve", json={"facility_id": 1}).status_code == 409
    row = next(r for r in api.get("/api/requests").json() if r["id"] == request["id"])
    assert row["status"] == "pending"


def test_concurrent_requests_cannot_overbook(client):
    api, _ = client
    assert (
        api.put(
            "/api/facilities/2/capacity", json={"service_id": 1, "total": 1, "day": today().isoformat()}
        ).status_code
        == 200
    )
    requests = [new_request(api) for _ in range(12)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(
            pool.map(
                lambda r: api.post(f"/api/requests/{r['id']}/reserve", json={"facility_id": 2}).status_code,
                requests,
            )
        )
    assert statuses.count(201) == 1
    assert statuses.count(409) == 11
    assert capacity(api, 2)["reserved"] == 1


def test_same_request_concurrently_reserves_only_once(client):
    api, _ = client
    request = new_request(api)
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(
            pool.map(
                lambda _: (
                    api.post(f"/api/requests/{request['id']}/reserve", json={"facility_id": 2}).status_code
                ),
                range(8),
            )
        )
    assert statuses.count(201) == 1
    assert statuses.count(409) == 7


def test_optimizer_prioritizes_urgent_within_budget(client):
    api, _ = client
    result = api.post("/api/plans", json={"day": today().isoformat(), "limit": 2600})
    assert result.status_code == 201, result.text
    plan = result.json()
    assert plan["cost"] == 2600 and plan["units"] == 2
    assert {(a["zone"], a["service_id"]) for a in plan["allocations"]} == {("East", 4), ("West", 1)}


def test_plan_approval_is_atomic_and_reprocesses(client):
    api, _ = client
    plan = api.post("/api/plans", json={"day": today().isoformat(), "limit": 50000}).json()
    result = api.post(f"/api/plans/{plan['id']}/approve")
    assert result.status_code == 200, result.text
    assert result.json()["reprocessed"] == 6
    dashboard = api.get("/api/dashboard").json()
    assert dashboard["budget"]["committed"] == plan["cost"]
    assert dashboard["pending"] == 0
    assert api.post(f"/api/plans/{plan['id']}/approve").status_code == 409
    assert api.get("/api/dashboard").json() == dashboard


def test_concurrent_plans_cannot_overspend(client):
    api, _ = client
    assert api.put("/api/budget", json={"total": 10000}).status_code == 200
    plans = [
        api.post("/api/plans", json={"day": today().isoformat(), "limit": 10000}).json() for _ in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda p: api.post(f"/api/plans/{p['id']}/approve").status_code, plans))
    assert sorted(statuses) == [200, 409]
    budget = api.get("/api/dashboard").json()["budget"]
    assert 0 < budget["committed"] <= budget["total"]
    assert api.put("/api/budget", json={"total": 0}).status_code == 409
    assert api.get("/api/dashboard").json()["budget"] == budget


def test_stale_budget_approval_rolls_back_plan(client):
    api, _ = client
    plan = api.post("/api/plans", json={"day": today().isoformat(), "limit": 50000}).json()
    api.put("/api/budget", json={"total": 100})
    assert api.post(f"/api/plans/{plan['id']}/approve").status_code == 409
    assert api.get("/api/plans").json()[0]["status"] == "draft"
    assert api.get("/api/dashboard").json()["budget"]["committed"] == 0


def test_dated_capacity_is_isolated(client):
    api, _ = client
    day = (today() + timedelta(days=1)).isoformat()
    api.put("/api/facilities/2/capacity", json={"service_id": 1, "total": 77, "day": day})
    assert capacity(api, 2)["total"] == 12
    facility = next(f for f in api.get(f"/api/facilities?day={day}").json() if f["id"] == 2)
    assert next(c for c in facility["capacities"] if c["service_id"] == 1)["total"] == 77


def test_validation_and_missing_entities(client):
    api, _ = client
    assert (
        api.post(
            "/api/requests", json={"service_id": 1, "zone": "Unknown", "day": today().isoformat()}
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/api/requests", json={"service_id": 999, "zone": "Central", "day": today().isoformat()}
        ).status_code
        == 404
    )
    assert (
        api.post(
            "/api/requests",
            json={"service_id": 1, "zone": "Central", "day": (today() - timedelta(days=1)).isoformat()},
        ).status_code
        == 422
    )
    assert (
        api.put(
            "/api/facilities/2/capacity", json={"service_id": 1, "total": -1, "day": today().isoformat()}
        ).status_code
        == 422
    )


def test_service_suggestions_and_duplicate_review(client):
    api, _ = client
    match = api.post("/api/services/match", json={"description": "blood test"}).json()[0]
    assert match["service_id"] == 3 and match["requires_review"]
    result = api.post(
        "/api/facilities",
        json={
            "name": "Central Care Hospital",
            "zone": "Central",
            "kind": "Hospital",
            "latitude": 24.9,
            "longitude": 67.0,
        },
    )
    assert result.status_code == 409


def test_no_provider_demand_not_fabricated_by_optimizer(client):
    api, _ = client
    new_request(api, 5, "North")
    gaps = api.get("/api/dashboard").json()["gaps"]
    assert any(g["zone"] == "North" and g["reason"] == "No local provider" for g in gaps)
    plan = api.post("/api/plans", json={"day": today().isoformat(), "limit": 50000}).json()
    assert all(a["zone"] != "North" for a in plan["allocations"])


def test_health_export_and_reset_disabled(client):
    api, _ = client
    assert api.get("/health").json()["status"] == "ok"
    assert len(api.get("/api/export").json()["facilities"]) == 6
    assert api.post("/api/demo/reset?confirm=RESET_SYNTHETIC_DATA").status_code == 403


def test_enabled_demo_reset_preserves_legacy_rows(client, monkeypatch):
    from sqlalchemy import func, select
    from app.main import settings
    from app.models import Budget, CareRequest, Facility, SeedMetadata

    api, factory = client
    monkeypatch.setattr(settings, "enable_demo_reset", True)
    with factory() as session:
        old_facility_ids = set(session.scalars(select(Facility.id)).all())
        old_request_ids = set(session.scalars(select(CareRequest.id)).all())
        old_budget = session.get(Budget, 1)
        old_budget_values = (old_budget.total, old_budget.committed)

    response = api.post("/api/demo/reset?confirm=RESET_SYNTHETIC_DATA")
    assert response.status_code == 200, response.text
    with factory() as session:
        assert old_facility_ids <= set(session.scalars(select(Facility.id)).all())
        assert old_request_ids <= set(session.scalars(select(CareRequest.id)).all())
        assert (session.get(Budget, 1).total, session.get(Budget, 1).committed) == old_budget_values
        assert session.scalar(select(func.count()).select_from(SeedMetadata)) == 1
        assert session.scalar(select(func.count()).select_from(CareRequest).where(CareRequest.cohort.is_not(None))) == 20


def test_demo_reset_refuses_linked_activity_atomically(client, monkeypatch):
    from sqlalchemy import select
    from app.main import settings
    from app.models import Capacity, CareRequest, Facility, Referral, SeedMetadata, Zone
    from app.seed import load_seed_fixture, seed

    api, factory = client
    monkeypatch.setattr(settings, "enable_demo_reset", True)
    with factory() as session:
        for row in load_seed_fixture()["zones"]:
            if session.scalar(select(Zone.id).where(Zone.zone_id == row["zone_id"])) is None:
                session.add(Zone(**row, origin_type="synthetic", origin_label="shared existing"))
        session.flush()
        seed(session, today(), reset=True)
        request = session.scalar(select(CareRequest).where(CareRequest.public_id == "REQ-DEMO-001"))
        capacity = session.scalar(select(Capacity).where(Capacity.origin_type == "synthetic"))
        assert request is not None and capacity is not None
        linked_facility = session.get(Facility, capacity.facility_id)
        unrelated_request = CareRequest(
            public_id="REQ-LEGACY-REF-DEMO", reference="SG-LEGACY-REF-DEMO",
            source_facility_id=linked_facility.id, service_id=request.service_id,
            zone="Central", zone_id="Central", day=today(), priority="routine", status="pending",
            origin_type="legacy",
        )
        session.add(unrelated_request)
        session.flush()
        activity = Referral(request_id=request.id, capacity_id=capacity.id, status="reserved")
        session.add(activity)
        session.commit()
        activity_id = activity.id
        demo_request_id = request.id
        unrelated_request_id = unrelated_request.id
        demo_capacity_id = capacity.id
        demo_facility_ids = set(session.scalars(
            select(Facility.id).where(Facility.public_id.like("FAC-P%"))
        ).all())

    response = api.post("/api/demo/reset?confirm=RESET_SYNTHETIC_DATA")
    assert response.status_code == 409, response.text
    assert "Reset was refused" in response.json()["detail"]
    with factory() as session:
        assert session.get(Referral, activity_id) is not None
        assert session.get(CareRequest, demo_request_id) is not None
        assert session.get(CareRequest, unrelated_request_id) is not None
        assert session.get(Capacity, demo_capacity_id) is not None
        assert demo_facility_ids <= set(session.scalars(select(Facility.id)).all())
        assert session.scalar(select(SeedMetadata.id)) is not None


def test_demo_reset_refuses_unowned_provider_children_atomically(client, monkeypatch):
    from datetime import timedelta
    from sqlalchemy import select
    from app.main import settings
    from app.models import (
        Capacity,
        Facility,
        FacilityParticipationEvent,
        FacilityService,
        SeedMetadata,
        Service,
        User,
        UserFacility,
        Zone,
    )
    from app.seed import load_seed_fixture, seed

    api, factory = client
    monkeypatch.setattr(settings, "enable_demo_reset", True)
    with factory() as session:
        for row in load_seed_fixture()["zones"]:
            if session.scalar(select(Zone.id).where(Zone.zone_id == row["zone_id"])) is None:
                session.add(Zone(**row, origin_type="synthetic", origin_label="shared existing"))
        session.flush()
        seed(session, today(), reset=True)
        facility = session.scalar(select(Facility).where(Facility.public_id == "FAC-P01"))
        primary_service = session.scalar(select(Service).where(Service.code == "PRIMARY_CARE_OPD"))
        extra_service = Service(
            name="Unrelated Demo Facility Service", aliases="other", unit_cost=1_500,
            code="UNRELATED-DEMO-SERVICE", display_name="Unrelated Demo Facility Service",
            origin_type="legacy", origin_label="unrelated",
        )
        extra_capacity = Capacity(
            facility_id=facility.id, service_id=primary_service.id,
            day=today() + timedelta(days=7), total=1, reserved=0, consumed=0,
            origin_type="legacy",
        )
        extra_event = FacilityParticipationEvent(
            facility_id=facility.id, status="SUSPENDED", version=2,
            reason="Independent operator action",
            origin_type="legacy",
        )
        extra_zone = Zone(
            zone_id="Synthetic Extra", display_name="Unrelated synthetic zone",
            latitude=33.7, longitude=73.0, origin_type="synthetic", origin_label="SEHAT GRID demo",
        )
        scoped_user = User(
            public_id="USR-EXTRA-SCOPE", username="extra-scope", role="OPERATOR", active=True,
        )
        session.add_all([extra_service, extra_capacity, extra_event, extra_zone, scoped_user])
        session.flush()
        extra_facility_service = FacilityService(
            facility_id=facility.id, service_id=extra_service.id, active=True,
            eligible_zone_ids=["Central"], suitability_restrictions=[],
            review_id="UNRELATED-SERVICE-REVIEW", version=1,
        )
        user_scope = UserFacility(user_id=scoped_user.id, facility_id=facility.id)
        session.add_all([extra_facility_service, user_scope])
        session.commit()
        ids = {
            "facility": facility.id,
            "service": extra_service.id,
            "capacity": extra_capacity.id,
            "event": extra_event.id,
            "zone": extra_zone.id,
            "user_scope": user_scope.id,
        }

    response = api.post("/api/demo/reset?confirm=RESET_SYNTHETIC_DATA")
    assert response.status_code == 409, response.text
    assert "non-owned" in response.json()["detail"].lower()
    with factory() as session:
        assert session.get(Facility, ids["facility"]) is not None
        assert session.get(Service, ids["service"]) is not None
        assert session.get(Capacity, ids["capacity"]) is not None
        assert session.get(FacilityParticipationEvent, ids["event"]) is not None
        assert session.get(Zone, ids["zone"]) is not None
        assert session.get(UserFacility, ids["user_scope"]) is not None
        assert session.scalar(select(FacilityService.id).where(
            FacilityService.facility_id == ids["facility"], FacilityService.service_id == ids["service"],
        )) is not None
        assert session.scalar(select(SeedMetadata.id)) is not None


def test_new_provider_can_offer_capacity_and_receive_referrals(client):
    api, _ = client
    registered = api.post(
        "/api/facilities",
        json={
            "name": "North Community Support",
            "zone": "North",
            "kind": "Community center",
            "latitude": 24.96,
            "longitude": 67.07,
        },
    )
    assert registered.status_code == 201
    provider = registered.json()["id"]
    assert (
        api.put(
            f"/api/facilities/{provider}/capacity",
            json={"service_id": 6, "total": 1, "day": today().isoformat()},
        ).status_code
        == 200
    )
    request = new_request(api, 6, "North")
    assert request["recommendations"][0]["facility_id"] == provider
    assert request["recommendations"][0]["local"]
    assert (
        api.post(f"/api/requests/{request['id']}/reserve", json={"facility_id": provider}).status_code == 201
    )
    assert capacity(api, provider, 6)["available"] == 0


def test_no_demand_creates_empty_plan_without_spending(client):
    api, _ = client
    future_day = (today() + timedelta(days=30)).isoformat()
    result = api.post("/api/plans", json={"day": future_day, "limit": 50000})
    assert result.status_code == 201
    plan = result.json()
    assert plan["units"] == 0 and plan["cost"] == 0 and plan["allocations"] == []
    assert api.post(f"/api/plans/{plan['id']}/approve").status_code == 409
    assert api.get("/api/dashboard").json()["budget"]["committed"] == 0
