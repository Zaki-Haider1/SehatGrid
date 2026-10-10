from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from app.mvp.common import capacity_key, now, SERVICE


def make_plan(p):
    month = p.state()["config"]["month"]
    snap = p.ok("intelligence/snapshots", {"month": month})
    return p.ok("plans/optimize", {"snapshot_id": snap["id"]})


def reserve(p, rid="A-01"):
    choice = p.ok(f"requests/{rid}/recommendations", user="operator-p01")["candidates"][0]
    return p.ok(
        "referrals",
        {k: choice[k] for k in ["capacity_id", "capacity_version", "facility_version"]} | {"request_id": rid},
        "operator-p01",
    )


def test_planner_can_configure_referral_ranking(pilot):
    p = pilot
    current = p.call("referral-ranking", user="planner")
    assert current.status_code == 200
    policy = current.json()
    assert policy["criteria"] == ["same_zone", "subsidy", "available"]

    updated = p.ok(
        "referral-ranking",
        {
            "criteria": ["subsidy", "same_zone", "available"],
            "version": policy["version"],
            "reason": "Prefer lower subsidy before zone proximity",
        },
        method="PUT",
    )
    assert updated["version"] == policy["version"] + 1
    assert updated["criteria"] == ["subsidy", "same_zone", "available"]

    request_id = "A-01"
    result = p.ok(f"requests/{request_id}/recommendations", user="operator-p01")
    candidates = result["candidates"]

    def key(candidate):
        values = {
            "same_zone": not candidate["same_zone"],
            "subsidy": candidate["subsidy"],
            "available": -candidate["available"],
        }
        return tuple(values[name] for name in updated["criteria"]) + (
            candidate["facility_id"],
            candidate["date"],
        )

    assert candidates == sorted(candidates, key=key)
    assert result["ranking_policy_version"] == updated["policy_version"]
    assert p.call("referral-ranking", {"criteria": ["same_zone", "subsidy", "available"], "version": 1, "reason": "Operator cannot change planner policy"}, "operator-p01", "PUT").status_code == 403


def test_worked_example_and_closed_loop(pilot):
    p = pilot
    plan = make_plan(p)
    assert (plan["additional"], plan["cost"], plan["baseline"], plan["subsidy_cost"]) == (20, 25000, 0, 8000)
    assert plan["solver_status"] == "OPTIMAL"
    assert len([a for a in plan["assignments"] if a["subsidy"] == 1000]) == 8
    approved = p.ok(f"plans/{plan['id']}/approve", {}, key="approve-unique")
    assert approved["status"] == "APPROVED"
    assert p.ok(f"plans/{plan['id']}/approve", {}, key="approve-unique") == approved
    budget = p.state()["budgets"][0]
    assert budget["remaining"] == 0 and budget["COMMITTED"] == 25000 and budget["SETTLED"] == 0
    assert p.ok("requests/B-01/recommendations", user="operator-p01")["candidates"] == []
    for action, user in [("QUOTA-7", "operator-p02"), ("MOBILE-5", "operator-p08")]:
        p.ok(f"plans/{plan['id']}/actions/{action}/activate", {}, user, key="activate-" + action)
        p.ok(f"plans/{plan['id']}/actions/{action}/activate", {}, user, key="activate-" + action)
    budget = p.state()["budgets"][0]
    assert budget["SETTLED"] == 17000 and budget["COMMITTED"] == 8000
    for rid, receiver in [("A-01", "operator-p01"), ("B-01", "operator-p02"), ("C-01", "operator-p08")]:
        a = reserve(p, rid)
        assert a["status"] == "AWAITING_CONFIRMATIONS"
        p.ok(f"referrals/{a['id']}/patient-agreement", {"accepted": True}, "operator-p01")
        confirmed = p.ok(f"referrals/{a['id']}/partner-response", {"accepted": True}, receiver)
        assert confirmed["status"] == "CONFIRMED"
        p.ok(f"referrals/{a['id']}/arrival", {}, receiver)
        p.ok(f"referrals/{a['id']}/completion", {}, receiver, key="complete-" + rid)
        p.ok(f"referrals/{a['id']}/completion", {}, receiver, key="complete-" + rid)
    state = p.state()
    assert state["summary"]["post_activation_confirmed"] == 3
    assert state["summary"]["post_activation_completed"] == 3
    assert state["summary"]["completed"] == 23
    assert state["budgets"][0]["SETTLED"] == 18000 and state["budgets"][0]["COMMITTED"] == 7000
    output = p.ok(f"plans/{plan['id']}/export")
    assert "A-01" not in str(output) and "request_id" not in str(output)
    assert output["additional"] == 20 and output["input_versions"]


def test_confirmation_permissions_and_approvals(pilot):
    p = pilot
    a = reserve(p)
    assert p.call(f"referrals/{a['id']}/arrival", {}, "operator-p01").status_code == 409
    assert (
        p.call(f"referrals/{a['id']}/funding-approval", {"accepted": True}, "operator-p01").status_code == 403
    )
    assert (
        p.call(f"referrals/{a['id']}/partner-response", {"accepted": True}, "operator-p02").status_code == 403
    )
    p.ok(f"referrals/{a['id']}/partner-response", {"accepted": True}, "operator-p01")
    waiting = p.ok(f"referrals/{a['id']}/patient-agreement", {"accepted": True}, "operator-p01")
    assert waiting["status"] == "AWAITING_CONFIRMATIONS"
    confirmed = p.ok(f"referrals/{a['id']}/funding-approval", {"accepted": True})
    assert confirmed["status"] == "CONFIRMED"
    assert p.state()["budgets"][0]["HELD"] == 0
    assert p.state()["budgets"][0]["COMMITTED"] == 1000
    assert p.call(f"referrals/{a['id']}/completion", {}, "operator-p01").status_code == 409


def test_last_unit_concurrency(pilot):
    p = pilot
    p.edit(lambda s: s["capacities"][capacity_key("P01", s["service_date"])].update(quota=1))
    payloads = []
    for rid in ["A-01", "A-02"]:
        c = p.ok(f"requests/{rid}/recommendations", user="operator-p01")["candidates"][0]
        payloads.append(
            {k: c[k] for k in ["capacity_id", "capacity_version", "facility_version"]} | {"request_id": rid}
        )
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda d: p.call("referrals", d, "operator-p01"), payloads))
    assert sorted(r.status_code for r in responses) == [200, 409]
    c = p.edit(lambda s: deepcopy(s["capacities"][capacity_key("P01", s["service_date"])]))
    assert c["held"] == 1 and c["quota"] == 1


def test_concurrent_budget_holds(pilot):
    p = pilot
    p.edit(lambda s: s["budgets"][s["service_date"][:7]].update(authorized=1000))
    payloads = []
    for rid in ["A-01", "A-02"]:
        c = p.ok(f"requests/{rid}/recommendations", user="operator-p01")["candidates"][0]
        payloads.append(
            {k: c[k] for k in ["capacity_id", "capacity_version", "facility_version"]} | {"request_id": rid}
        )
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda d: p.call("referrals", d, "operator-p01"), payloads))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert p.state()["budgets"][0]["remaining"] == 0
    assert p.state()["budgets"][0]["HELD"] == 1000


def test_concurrent_plan_approval(pilot):
    p = pilot
    plans = [make_plan(p), make_plan(p)]
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda plan: p.call(f"plans/{plan['id']}/approve", {}), plans))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert p.state()["budgets"][0]["COMMITTED"] == 25000


def test_expiry_rejection_cancel_and_deduplication(pilot):
    p = pilot
    a = reserve(p)
    p.ok(
        f"referrals/{a['id']}/partner-response",
        {"accepted": False, "reason": "No suitable resource"},
        "operator-p01",
    )
    a2 = reserve(p)
    p.edit(lambda s: s["referrals"][a2["id"]].update(expires_at=(now() - timedelta(minutes=1)).isoformat()))
    state = p.state()
    assert state["budgets"][0]["HELD"] == 0
    assert state["summary"]["unresolved"] == 20
    a3 = reserve(p)
    p.ok(
        f"referrals/{a3['id']}/cancel", {"reason": "Operator cancellation"}, "operator-p01", key="cancel-once"
    )
    p.ok(
        f"referrals/{a3['id']}/cancel", {"reason": "Operator cancellation"}, "operator-p01", key="cancel-once"
    )
    assert p.state()["summary"]["unresolved"] == 20
    assert p.state()["budgets"][0]["remaining"] == 25000


def test_stale_capacity_refresh_and_quota_floor(pilot):
    p = pilot
    day = p.state()["config"]["service_date"]
    p.edit(
        lambda s: s["capacities"][capacity_key("P01", day)].update(
            updated_at=(now() - timedelta(days=3)).isoformat()
        )
    )
    assert p.ok("requests/A-01/recommendations", user="operator-p01")["reasons"] == [
        "CAPACITY_UNKNOWN_OR_STALE"
    ]
    assert (
        p.call(
            f"facilities/P01/capacity/{SERVICE}/{day}",
            {"quota": 8, "version": 1},
            "operator-p02",
            method="PUT",
        ).status_code
        == 403
    )
    p.ok(f"facilities/P01/capacity/{SERVICE}/{day}", {"quota": 8, "version": 1}, "operator-p01", method="PUT")
    a = reserve(p)
    assert a["status"] == "AWAITING_CONFIRMATIONS"
    c = p.edit(lambda s: deepcopy(s["capacities"][capacity_key("P01", day)]))
    assert (
        p.call(
            f"facilities/P01/capacity/{SERVICE}/{day}",
            {"quota": 0, "version": c["version"]},
            "operator-p01",
            method="PUT",
        ).status_code
        == 409
    )


def test_stale_draft_and_snapshot_immutability(pilot):
    p = pilot
    plan = make_plan(p)
    before = p.edit(lambda s: deepcopy(s["snapshots"][plan["snapshot_id"]]))
    reserve(p)
    assert p.call(f"plans/{plan['id']}/approve", {}).status_code == 409
    after = p.edit(lambda s: deepcopy(s["snapshots"][plan["snapshot_id"]]))
    assert before == after


def test_matching_review_feeds_request(pilot):
    p = pilot
    text = "a routine visit with a family physician"
    m = p.ok("matching/services", {"text": text}, "operator-p01")
    assert "all-MiniLM-L6-v2@" in m["model_version"]
    assert m["candidates"][0]["id"] == SERVICE
    rev = p.ok(
        "matching/reviews",
        {
            "match_id": m["id"],
            "decision": "ACCEPT",
            "candidate_id": SERVICE,
            "reason": "Operator checked scope",
        },
        "operator-p01",
    )
    day = p.state()["config"]["service_date"]
    r = p.ok(
        "requests",
        {
            "reference": "NEW-TEST",
            "source_facility_id": "P01",
            "zone": "East",
            "original_text": text,
            "review_id": rev["id"],
            "date_from": day,
            "date_to": day,
            "suitable": True,
        },
        "operator-p01",
    )
    assert r["service_reviewed"]
    assert p.ok(f"requests/{r['id']}/recommendations", user="operator-p01")["candidates"]
    wrong = p.call(
        "requests",
        {
            "reference": "BAD-REVIEW",
            "source_facility_id": "P02",
            "zone": "East",
            "original_text": text,
            "review_id": rev["id"],
            "date_from": day,
            "date_to": day,
            "suitable": True,
        },
        "operator-p02",
    )
    assert wrong.status_code == 422


def test_unsupported_and_scope_exclusion(pilot):
    p = pilot
    day = p.state()["config"]["service_date"]
    r = p.ok(
        "requests",
        {
            "reference": "UNSUPPORTED",
            "source_facility_id": "P01",
            "zone": "Not mapped",
            "original_text": "Emergency trauma operation",
            "date_from": day,
            "date_to": day,
            "suitable": False,
        },
        "operator-p01",
    )
    assert r["status"] == "OUT_OF_SCOPE"
    summary = p.ok("intelligence/summary")
    assert summary["zones"][-1]["zone"] == "Unknown zone" and summary["zones"][-1]["count"] == 1
    snap = p.ok("intelligence/snapshots", {"month": day[:7]})
    assert snap["excluded"]["OUT_OF_SCOPE"] == 1 and len(snap["requests"]) == 20


def test_idempotency_key_collision(pilot):
    p = pilot
    b = p.state()["budgets"][0]
    p.ok("budgets", {"month": b["month"], "authorized": 25000, "version": b["version"]}, key="unique-key-001")
    r = p.call(
        "budgets", {"month": b["month"], "authorized": 26000, "version": b["version"]}, key="unique-key-001"
    )
    assert r.status_code == 409 and r.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_cancel_plan_releases_pools_and_holds(pilot):
    p = pilot
    plan = make_plan(p)
    p.ok(f"plans/{plan['id']}/approve", {})
    p.ok(f"plans/{plan['id']}/cancel", {"reason": "Recompute all unactivated resources"})
    state = p.state()
    assert state["budgets"][0]["remaining"] == 25000
    assert all(o["status"] == "AVAILABLE" for o in state["offers"])
    assert state["facilities"][0]["capacities"][0]["held"] == 0


def test_operator_views_are_scoped(pilot):
    p = pilot
    state = p.ok("state", user="operator-p02")
    assert state["summary"] is None and state["ledger"] == [] and state["requests"] == []
    assert all(not f["capacities"] for f in state["facilities"] if f["id"] != "P02")
    assert p.call("intelligence/summary", user="operator-p02").status_code == 403
    assert (
        p.call(
            "budgets", {"month": state["config"]["month"], "authorized": 50000, "version": 1}, "operator-p02"
        ).status_code
        == 403
    )


def test_completed_quota_never_releases(pilot):
    p = pilot
    a = reserve(p)
    p.ok(f"referrals/{a['id']}/partner-response", {"accepted": True}, "operator-p01")
    p.ok(f"referrals/{a['id']}/patient-agreement", {"accepted": True}, "operator-p01")
    p.ok(f"referrals/{a['id']}/funding-approval", {"accepted": True})
    p.ok(f"referrals/{a['id']}/arrival", {}, "operator-p01")
    p.ok(f"referrals/{a['id']}/completion", {}, "operator-p01")
    assert (
        p.call(
            f"referrals/{a['id']}/cancel", {"reason": "Attempt to release completed"}, "operator-p01"
        ).status_code
        == 409
    )
    assert p.state()["facilities"][0]["capacities"][0]["completed"] == 1


def test_cancel_cutoff_and_no_show(pilot):
    p = pilot

    def confirmed():
        a = reserve(p)
        p.ok(f"referrals/{a['id']}/partner-response", {"accepted": True}, "operator-p01")
        p.ok(f"referrals/{a['id']}/patient-agreement", {"accepted": True}, "operator-p01")
        p.ok(f"referrals/{a['id']}/funding-approval", {"accepted": True})
        return a

    first = confirmed()
    p.ok(f"referrals/{first['id']}/cancel", {"reason": "Before service cutoff"}, "operator-p01")
    c = p.state()["facilities"][0]["capacities"][0]
    assert c["forfeited"] == 0 and c["available"] == 8
    second = confirmed()
    p.edit(lambda s: s["referrals"][second["id"]].update(date=(now().date() - timedelta(days=1)).isoformat()))
    p.ok(f"referrals/{second['id']}/cancel", {"reason": "After service cutoff"}, "operator-p01")
    c = p.state()["facilities"][0]["capacities"][0]
    assert c["forfeited"] == 1 and c["available"] == 7
    third = confirmed()
    assert (
        p.call(f"referrals/{third['id']}/no-show", {"reason": "Not yet due"}, "operator-p01").status_code
        == 409
    )
    p.edit(lambda s: s["referrals"][third["id"]].update(date=(now().date() - timedelta(days=1)).isoformat()))
    p.ok(f"referrals/{third['id']}/no-show", {"reason": "Service window passed"}, "operator-p01")
    assert p.state()["facilities"][0]["capacities"][0]["forfeited"] == 2
    assert p.state()["budgets"][0]["remaining"] == 25000


def test_rejected_activation_updates_ledger_and_remaining_plan(pilot):
    p = pilot
    plan = make_plan(p)
    p.ok(f"plans/{plan['id']}/approve", {})
    result = p.ok(
        f"plans/{plan['id']}/actions/MOBILE-5/reject",
        {"reason": "Operator cannot offer mobile unit"},
        "operator-p08",
    )
    assert result["cost"] == 15000 and result["additional"] == 15 and result["unresolved_remaining"] == 5
    assert p.state()["budgets"][0]["remaining"] == 10000
    assert p.call(f"plans/{plan['id']}/actions/MOBILE-5/activate", {}, "operator-p08").status_code == 409


def test_mobile_activation_preserves_real_campus_and_requires_receiver(pilot):
    p = pilot
    original = deepcopy(p.state()["facilities"][7])
    plan = make_plan(p)
    p.ok(f"plans/{plan['id']}/approve", {})
    assert p.call(f"plans/{plan['id']}/actions/MOBILE-5/activate", {}, "operator-p01").status_code == 403
    p.ok(f"plans/{plan['id']}/actions/MOBILE-5/activate", {}, "operator-p08")
    facilities = p.state()["facilities"]
    original_after = next(f for f in facilities if f["id"] == "P08")
    mobile = next(f for f in facilities if f["id"] == "site:MOBILE-5")
    assert (original["latitude"], original["longitude"]) == (
        original_after["latitude"],
        original_after["longitude"],
    )
    assert (mobile["latitude"], mobile["longitude"]) == (33.746, 73.03)
    a = reserve(p, "C-01")
    assert a["facility_id"] == "site:MOBILE-5"
    p.ok(f"referrals/{a['id']}/partner-response", {"accepted": True}, "operator-p08")


def test_included_funding_remains_available_after_release(pilot):
    p = pilot
    # Private purchased quota includes funding. Closing a plan releases earmarks but not the paid resource.
    p.edit(
        lambda s: (
            s["facilities"]["P02"].update(subsidy_required=True),
            s["requests"]["B-01"].update(needs_funding=True),
        )
    )
    plan = make_plan(p)
    p.ok(f"plans/{plan['id']}/approve", {})
    p.ok(f"plans/{plan['id']}/actions/QUOTA-7/activate", {}, "operator-p02")
    p.ok(f"plans/{plan['id']}/cancel", {"reason": "Release unassigned earmarks"})
    choice = p.ok("requests/B-01/recommendations", user="operator-p01")["candidates"][0]
    assert choice["subsidy"] == 0
    a = reserve(p, "B-01")
    assert a["subsidy"] == 0 and a["package_funded"]
    before = p.state()["budgets"][0]["remaining"]
    p.ok(f"referrals/{a['id']}/cancel", {"reason": "Retry released included unit"}, "operator-p01")
    assert p.state()["budgets"][0]["remaining"] == before
    assert p.ok("requests/B-01/recommendations", user="operator-p01")["candidates"][0]["subsidy"] == 0


def test_patient_decline_excluded_until_reprocessed(pilot):
    p = pilot
    a = reserve(p)
    p.ok(
        f"referrals/{a['id']}/patient-agreement",
        {"accepted": False, "reason": "Does not agree"},
        "operator-p01",
    )
    snap = p.ok("intelligence/snapshots", {"month": p.state()["config"]["month"]})
    assert snap["excluded"]["PATIENT_DECLINED"] == 1
    p.ok("requests/A-01/reprocess", {"reason": "Operator recorded updated preferences"}, "operator-p01")
    assert p.ok("requests/A-01/recommendations", user="operator-p01")["candidates"]


def test_facility_identity_link_is_non_destructive(pilot):
    p = pilot
    f = p.ok(
        "facilities",
        {
            "name": "Demo duplicate provider",
            "ownership": "Public",
            "address": "Islamabad pilot",
            "zone": "Central",
            "latitude": 33.7,
            "longitude": 73.05,
        },
        "operator-p02",
    )
    match = p.ok("matching/facilities", {"text": "Pakistan Institute of Medical Sciences", "zone": "Central"})
    p.ok(
        "matching/reviews",
        {
            "match_id": match["id"],
            "decision": "ACCEPT",
            "candidate_id": "P02",
            "record_id": f["id"],
            "reason": "Reviewed demo duplicate identity",
        },
    )
    result = p.edit(lambda s: deepcopy(s["facilities"][f["id"]]))
    assert (
        result["canonical_id"] == "P02"
        and result["id"] == f["id"]
        and result["original_name"] == "Demo duplicate provider"
    )


def test_tiny_solver_independent_optimum():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from evaluate_allocation import tiny_case, exhaustive
    from app.mvp.planning import solve

    for kind in ["standard", "overlap", "mobile_overlap", "mixed", "wrong_date", "stale"]:
        snap = tiny_case(kind)
        for budget in [0, 1, 2, 3, 4, 5, 6]:
            result = solve(snap, budget)
            assert (result["coverage"], result["cost"]) == exhaustive(snap, budget)


def test_expired_plan_releases_unactivated_resources(pilot, monkeypatch):
    from app.mvp import referrals

    p = pilot
    plan = make_plan(p)
    p.ok(f"plans/{plan['id']}/approve", {})
    later = now() + timedelta(days=3)
    monkeypatch.setattr(referrals, "now", lambda: later)
    state = p.state()
    assert state["plans"][0]["status"] == "CANCELLED"
    assert state["budgets"][0]["remaining"] == 25000


def test_replan_does_not_double_count_projected_units(pilot):
    p = pilot
    first = make_plan(p)
    p.ok(f"plans/{first['id']}/approve", {})
    a = reserve(p)
    p.ok(f"referrals/{a['id']}/cancel", {"reason": "Retry funded request"}, "operator-p01")
    assert p.state()["summary"]["projected_additional"] == 19
    second = make_plan(p)
    assert second["additional"] == 1
    p.ok(f"plans/{second['id']}/approve", {})
    assert p.state()["summary"]["projected_additional"] == 20


def test_startup_model_files_required():
    from app.mvp.matching import Matcher
    from app.config import get_settings

    settings = get_settings()
    previous = settings.embedding_model_path
    try:
        settings.embedding_model_path = "models/does-not-exist"
        import pytest

        with pytest.raises(FileNotFoundError):
            Matcher()
    finally:
        settings.embedding_model_path = previous
