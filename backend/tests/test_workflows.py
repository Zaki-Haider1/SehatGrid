from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from app.main import today


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
