import pytest
from fastapi import HTTPException
from app.mvp.seed import make_seed
from app.mvp.common import capacity_key, cap_view
from app.mvp.routing import sender, catalog_available, routing_score
from app.mvp.referrals import recommendations
from app.mvp.notifications import queue_update


def test_public_only_sender_and_no_self_referral():
    s = make_seed()
    with pytest.raises(HTTPException) as error:
        sender(s, {"role": "operator", "facility_ids": ["P01"]}, "P01")
    assert error.value.status_code == 403
    sender(s, {"role": "operator", "facility_ids": ["P02"]}, "P02")
    r = s["requests"]["A-01"]
    assert all(o["facility_id"] != "P02" for o in recommendations(s, r)["candidates"])


def test_pressure_and_points_change_score_before_full():
    s = make_seed()
    f = s["facilities"]["P01"]
    c = s["capacities"][capacity_key("P01", s["service_date"])]
    c.update(quota=10, held=0, committed=0, completed=0, forfeited=0)
    empty = routing_score(s, f, c)
    c["held"] = 5
    assert routing_score(s, f, c) < empty
    old = routing_score(s, f, c)
    f["routing_points"] = 100
    assert routing_score(s, f, c) > old
    c["held"] = 8
    assert cap_view(s, c)["status"] == "LIMITED"
    c["held"] = 10
    assert cap_view(s, c)["status"] == "EXHAUSTED"


def test_required_test_capacity_is_consumed_and_released():
    s = make_seed()
    r = s["requests"]["A-01"]
    f = s["facilities"]["P01"]
    r["required_tests"] = ["CBC"]
    assert not catalog_available(s, r, f, s["service_date"])
    f["catalog"] = [{"name": "CBC", "active": True, "daily_capacity": 1, "price": 500}]
    assert catalog_available(s, r, f, s["service_date"])
    s["referrals"]["test"] = {
        "id": "test",
        "request_id": r["id"],
        "facility_id": f["id"],
        "date": s["service_date"],
        "status": "AWAITING_CONFIRMATIONS",
    }
    assert not catalog_available(s, r, f, s["service_date"])
    assert catalog_available(s, r, f, s["service_date"], "test")
    s["referrals"]["test"]["status"] = "CANCELLED"
    assert catalog_available(s, r, f, s["service_date"])


def test_whatsapp_consent_idempotent_confirm_and_cancel_messages():
    s = make_seed()
    r = s["requests"]["A-01"]
    a = {"id": "preview", "request_id": r["id"], "facility_id": "P01", "date": s["service_date"]}
    queue_update(s, a, "CONFIRMED")
    assert not s.get("notifications")
    r.update(whatsapp_consent=True, whatsapp_phone="+923000000000", required_tests=["CBC"])
    queue_update(s, a, "CONFIRMED")
    queue_update(s, a, "CONFIRMED")
    assert len(s["notifications"]) == 1
    n = next(iter(s["notifications"].values()))
    assert "Shifa International Hospital" in n["message"] and "CBC" in n["message"]
    assert n["status"] == "PREVIEW_ONLY"
    queue_update(s, a, "CANCELLED")
    assert len(s["notifications"]) == 2


def test_points_access_and_ownership_privilege_escalation(pilot):
    p = pilot
    f = next(f for f in p.state()["facilities"] if f["id"] == "P01")
    body = {"points": 85, "version": f["version"], "reason": "Reviewed receiving performance"}
    assert p.call("facilities/P01/routing-points", body, "operator-p01", "PUT").status_code == 403
    assert p.ok("facilities/P01/routing-points", body, method="PUT")["routing_points"] == 85
    body = {k: f[k] for k in ["name", "ownership", "address", "zone", "latitude", "longitude"]}
    body.update(ownership="Public", version=f["version"] + 1)
    assert p.call("facilities/P01", body, "onboarder-p01", "PATCH").status_code == 403


def test_test_capacity_constrains_monthly_plan_and_revision(pilot):
    p = pilot

    def setup(s):
        s["facilities"]["P01"]["catalog"] = [
            {"name": "CBC", "active": True, "daily_capacity": 1, "price": 500}
        ]
        for r in s["requests"].values():
            if r["id"].startswith("A-"):
                r["required_tests"] = ["CBC"]

    p.edit(setup)
    snap = p.ok("intelligence/snapshots", {"month": p.state()["config"]["month"]})
    plan = p.ok("plans/optimize", {"snapshot_id": snap["id"]})
    assert len([a for a in plan["assignments"] if a["request_id"].startswith("A-")]) == 1
    options = p.ok(f"plans/{plan['id']}/revision-options")["choices"]
    chosen = [next(a for a in options if a["request_id"] == rid) for rid in ["A-01", "A-02"]]
    response = p.call(
        f"plans/{plan['id']}/revise",
        {
            "version": plan["version"],
            "reason": "Attempt excess test allocations",
            "assignments": [{"request_id": a["request_id"], "resource_id": a["resource_id"]} for a in chosen],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TEST_CAPACITY_CONFLICT"


def test_confirmation_queues_only_after_all_approvals_and_masks_phone(pilot):
    p = pilot
    p.edit(lambda s: s["requests"]["A-01"].update(whatsapp_consent=True, whatsapp_phone="+923000000000"))
    choice = p.ok("requests/A-01/recommendations", user="operator-p08")["candidates"][0]
    a = p.ok(
        "referrals/proposals",
        {k: choice[k] for k in ["capacity_id", "capacity_version", "facility_version"]}
        | {"request_id": "A-01"},
        "operator-p08",
    )
    p.ok(f"referrals/{a['id']}/reserve", {}, "operator-p08")
    p.ok(f"referrals/{a['id']}/partner-response", {"accepted": True}, "operator-p01")
    p.ok(f"referrals/{a['id']}/patient-agreement", {"accepted": True}, "operator-p08")
    assert not p.ok("state", user="operator-p08")["notifications"]
    p.ok(f"referrals/{a['id']}/funding-approval", {"accepted": True})
    messages = p.ok("state", user="operator-p08")["notifications"]
    assert len(messages) == 1 and messages[0]["recipient"] == "***0000"
    assert not p.ok("state", user="operator-p04")["notifications"]
    p.ok(f"referrals/{a['id']}/cancel", {"reason": "Patient needs a replacement destination"}, "operator-p08")
    assert len(p.ok("state", user="operator-p08")["notifications"]) == 2
