from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta

import pytest
import json
from fastapi import HTTPException

from app.mvp import common, planning
from app.mvp.common import capacity_key, now
from app.mvp.plan_revision import validate_selection
from tests.test_mvp import make_plan, reserve


def payload(p, plan, keep=None):
    options = p.ok(f"plans/{plan['id']}/revision-options")
    return {
        "version": options["version"],
        "reason": "Planner prioritizes the smaller pilot cohort",
        "assignments": [a for a in options["current_assignments"] if keep is None or keep(a)],
    }


def protected(s):
    return deepcopy({k: s[k] for k in ("capacities", "offers", "budgets", "ledger", "snapshots")})


def test_revision_preserves_solver_and_approves_revised_totals(pilot):
    p = pilot
    plan = make_plan(p)
    before = p.edit(protected)
    data = payload(p, plan, lambda a: a["request_id"].startswith("A-"))
    revised = p.ok(f"plans/{plan['id']}/revise", data, key="revise-once")
    assert revised["version"] == 2 and revised["decision_source"] == "HUMAN_REVISION"
    assert (revised["projected"], revised["cost"], revised["subsidy_cost"], revised["additional"]) == (
        8,
        8000,
        8000,
        8,
    )
    assert revised["actions"] == [] and revised["unresolved_remaining"] == 12
    assert revised["original_solver_result"] == plan["original_solver_result"]
    assert revised["revisions"][0]["before"]["projected"] == 20
    assert revised["revisions"][0]["after"]["projected"] == 8
    assert revised["revisions"][0]["actor"] and revised["revisions"][0]["timestamp"]
    assert p.edit(protected) == before
    assert p.ok(f"plans/{plan['id']}/revise", data, key="revise-once") == revised
    assert len(p.ok(f"plans/{plan['id']}")["revisions"]) == 1
    audit = [a for a in p.ok("audit") if a["action"] == "PLAN_REVISED"]
    assert len(audit) == 1 and audit[0]["reason"] == data["reason"]
    export = p.ok(f"plans/{plan['id']}/export")
    assert export["decision_source"] == "HUMAN_REVISION" and export["cost"] == 8000
    assert export["solver_status_applies_to"] == "original_solver_result"
    assert export["original_solver_result"]["projected"] == 20
    assert sum(a["units"] for a in export["allocations"]) == 8
    assert sum(a["units"] for a in export["revisions"][0]["before"]["allocations"]) == 20
    assert "request_id" not in str(export) and "A-01" not in str(export)
    csv = p.call(f"plans/{plan['id']}/export?format=csv")
    assert csv.status_code == 200 and "HUMAN_REVISION" in csv.text and "A-01" not in csv.text
    assert p.call(f"plans/{plan['id']}/approve", {}).status_code == 409
    assert p.call(f"plans/{plan['id']}/approve", {"version": 1}).status_code == 409
    approved = p.ok(f"plans/{plan['id']}/approve", {"version": revised["version"]})
    assert approved["cost"] == 8000 and p.state()["budgets"][0]["COMMITTED"] == 8000
    assert p.state()["summary"]["projected_additional"] == 8
    a = reserve(p)
    assert a["plan_id"] == plan["id"] and a["subsidy"] == 1000


def test_revision_keeps_fixed_offer_cost_and_activation(pilot):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan, lambda a: a["request_id"] == "C-01")
    revised = p.ok(f"plans/{plan['id']}/revise", data)
    assert revised["cost"] == 10000 and revised["subsidy_cost"] == 0
    p.ok(f"plans/{plan['id']}/approve", {"version": revised["version"]})
    p.ok(f"plans/{plan['id']}/actions/MOBILE-5/activate", {}, "operator-p08")
    assert reserve(p, "C-01")["facility_id"] == "site:MOBILE-5"
    scoped = p.ok("state", user="operator-p08")["plans"][0]
    assert "original_solver_result" not in scoped and "revisions" not in scoped


def test_versioned_handoff_fixture(pilot):
    from pathlib import Path

    p = pilot
    plan = make_plan(p)
    day = p.state()["config"]["service_date"]
    fixture = json.loads(
        (Path(__file__).resolve().parents[2] / "data/contracts/plan-revision-v1.json")
        .read_text()
        .replace("{{service_date}}", day)
    )
    result = p.ok(f"plans/{plan['id']}/revise", fixture["request"])
    assert {k: result[k] for k in fixture["expected"]} == fixture["expected"]
    assert {k: result["original_solver_result"][k] for k in fixture["original_solver_expected"]} == fixture[
        "original_solver_expected"
    ]


def test_planner_can_choose_feasible_alternative_to_solver(pilot):
    p = pilot

    def add_alternative(s):
        other = deepcopy(s["offers"]["QUOTA-7"])
        other.update(
            id="QUOTA-SOUTH", eligible_zones=["South"], units=8, cost=2000, spare_group="SOUTH-SPARE"
        )
        s["offers"][other["id"]] = other

    p.edit(add_alternative)
    plan = make_plan(p)
    assert any(a["offer_id"] == "QUOTA-SOUTH" for a in plan["assignments"])
    day = p.state()["config"]["service_date"]
    revised = p.ok(
        f"plans/{plan['id']}/revise",
        {
            "version": plan["version"],
            "reason": "Prefer the existing provider for this pilot request",
            "assignments": [{"request_id": "A-01", "resource_id": capacity_key("P01", day)}],
        },
    )
    assert revised["assignments"][0]["facility_id"] == "P01"
    assert revised["cost"] == 1000 and revised["projected"] == 1


@pytest.mark.parametrize(
    "change,code,status",
    [
        (lambda d: d.update(reason=" "), "INVALID_INPUT", 422),
        (lambda d: d.update(cost=1), "INVALID_INPUT", 422),
        (lambda d: d["assignments"][0].update(subsidy=0), "INVALID_INPUT", 422),
        (lambda d: d["assignments"].append(deepcopy(d["assignments"][0])), "DUPLICATE_ASSIGNMENT", 422),
        (lambda d: d["assignments"][0].update(resource_id="MOBILE-5"), "INELIGIBLE_ASSIGNMENT", 422),
        (lambda d: d["assignments"][0].update(request_id="DONE-01"), "INELIGIBLE_ASSIGNMENT", 422),
        (lambda d: d.update(version=99), "STALE_INPUT", 409),
    ],
)
def test_invalid_revision_is_atomic(pilot, change, code, status):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan)
    change(data)
    before = p.edit(deepcopy)
    response = p.call(f"plans/{plan['id']}/revise", data)
    assert response.status_code == status and response.json()["detail"]["code"] == code
    assert p.edit(deepcopy) == before


def test_revision_role_and_draft_only(pilot):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan)
    assert p.call(f"plans/{plan['id']}/revise", data, "operator-p01").status_code == 403
    assert p.call(f"plans/{plan['id']}/revision-options", user="operator-p01").status_code == 403
    p.ok(f"plans/{plan['id']}/approve", {"version": plan["version"]})
    before = p.edit(deepcopy)
    response = p.call(f"plans/{plan['id']}/revise", data)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "INVALID_TRANSITION"
    assert p.edit(deepcopy) == before


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s["facilities"]["P01"].update(participation="SUSPENDED"),
        lambda s: s["requests"]["A-01"].update(suitable=False),
        lambda s: s["subsidy_rule"].update(amount=2000),
        lambda s: s["capacities"][capacity_key("P01", s["service_date"])].update(quota=1),
        lambda s: s["budgets"][s["service_date"][:7]].update(authorized=1000),
    ],
)
def test_operational_change_blocks_revision_and_approval(pilot, change):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan)
    p.edit(change)
    before = p.edit(deepcopy)
    for path, body in [("revise", data), ("approve", {})]:
        response = p.call(f"plans/{plan['id']}/{path}", body)
        assert response.status_code == 409 and response.json()["detail"]["code"] == "STALE_INPUT"
    assert p.edit(deepcopy) == before


def test_concurrent_revisions_one_version_wins(pilot):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan, lambda a: a["request_id"].startswith("A-"))
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: p.call(f"plans/{plan['id']}/revise", data), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    result = p.ok(f"plans/{plan['id']}")
    assert result["version"] == 2 and len(result["revisions"]) == 1
    assert p.state()["budgets"][0]["COMMITTED"] == 0


def test_revision_and_approval_race(pilot):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan, lambda a: a["request_id"].startswith("A-"))
    with ThreadPoolExecutor(2) as pool:
        revision = pool.submit(p.call, f"plans/{plan['id']}/revise", data)
        approval = pool.submit(p.call, f"plans/{plan['id']}/approve", {"version": 1})
        responses = [revision.result(), approval.result()]
    assert sorted(r.status_code for r in responses) == [200, 409]
    result = p.ok(f"plans/{plan['id']}")
    assert p.state()["budgets"][0]["COMMITTED"] == (25000 if result["status"] == "APPROVED" else 0)


def test_multiple_revisions_and_legacy_draft(pilot):
    p = pilot
    plan = make_plan(p)
    original_assignments = deepcopy(plan["assignments"])
    p.edit(lambda s: s["plans"][plan["id"]].pop("original_solver_result"))
    first = p.ok(f"plans/{plan['id']}/revise", payload(p, plan, lambda a: a["request_id"] == "A-01"))
    second = p.ok(f"plans/{plan['id']}/revise", payload(p, first, lambda a: False))
    assert second["version"] == 3 and second["cost"] == 0 and second["projected"] == 0
    assert len(second["revisions"]) == 2
    assert second["original_solver_result"]["assignments"] == original_assignments
    assert p.ok(f"plans/{plan['id']}/export")["original_solver_result"]["projected"] == 20
    p.ok(f"plans/{plan['id']}/approve", {"version": second["version"]})


def test_freshness_and_date_are_rechecked_without_input_change(pilot, monkeypatch):
    p = pilot
    plan = make_plan(p)
    data = payload(p, plan)
    before = p.edit(deepcopy)
    now_saved = now()
    monkeypatch.setattr(common, "now", lambda: now_saved + timedelta(hours=25))
    for path, body in [("revise", data), ("approve", {})]:
        response = p.call(f"plans/{plan['id']}/{path}", body)
        assert response.status_code == 422 and response.json()["detail"]["code"] == "INELIGIBLE_ASSIGNMENT"
    assert p.edit(deepcopy) == before
    monkeypatch.undo()
    day = (now() + timedelta(days=3)).date().isoformat()
    monkeypatch.setattr(planning, "local_today", lambda: day)
    assert p.call(f"plans/{plan['id']}/approve", {}).status_code == 422


def test_approval_rechecks_tampered_totals(pilot):
    p = pilot
    plan = make_plan(p)
    revised = p.ok(f"plans/{plan['id']}/revise", payload(p, plan))
    p.edit(lambda s: s["plans"][plan["id"]].update(cost=1))
    before = p.edit(deepcopy)
    response = p.call(f"plans/{plan['id']}/approve", {"version": revised["version"]})
    assert response.status_code == 409 and response.json()["detail"]["code"] == "INVALID_PLAN"
    assert p.edit(deepcopy) == before


@pytest.mark.parametrize(
    "kind,selection,budget,code",
    [
        ("standard", [("A-01", "base"), ("A-02", "base")], 25_000, "CAPACITY_CONFLICT"),
        ("standard", [("A-01", "base")], 0, "BUDGET_EXCEEDED"),
        ("overlap", [("B-01", "QUOTA-7"), ("C-01", "QUOTA-OTHER")], 25_000, "OFFER_CONFLICT"),
        ("mobile_overlap", [("C-01", "MOBILE-5"), ("B-01", "MOBILE-OTHER")], 25_000, "OFFER_CONFLICT"),
        ("wrong_date", [("C-01", "MOBILE-5")], 25_000, "INELIGIBLE_ASSIGNMENT"),
        ("stale", [("B-01", "QUOTA-7")], 25_000, "INELIGIBLE_ASSIGNMENT"),
    ],
)
def test_independent_fixture_constraints(kind, selection, budget, code):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from evaluate_allocation import tiny_case

    snap = tiny_case(kind)
    if kind == "standard":
        other = deepcopy(snap["requests"][0])
        other["id"] = "A-02"
        snap["requests"].append(other)
    data = [
        {
            "request_id": rid,
            "resource_id": capacity_key("P01", snap["requests"][0]["date_from"])
            if resource == "base"
            else resource,
        }
        for rid, resource in selection
    ]
    with pytest.raises(HTTPException) as error:
        validate_selection(snap, data, budget)
    assert error.value.detail["code"] == code


@pytest.mark.parametrize(
    "field,value",
    [
        ("suitable", False),
        ("service_reviewed", False),
        ("service_id", "SURGERY"),
        ("funding_eligible", False),
        ("zone", "East"),
        ("blocked_reasons", ["PATIENT_DECLINED"]),
        ("status", "FULFILLED"),
    ],
)
def test_request_eligibility_cannot_be_overridden(field, value):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from evaluate_allocation import tiny_case

    snap = tiny_case("standard")
    r = next(r for r in snap["requests"] if r["id"] == "A-01")
    r[field] = value
    with pytest.raises(HTTPException) as error:
        validate_selection(
            snap, [{"request_id": "A-01", "resource_id": capacity_key("P01", r["date_from"])}], 25000
        )
    assert error.value.detail["code"] == "INELIGIBLE_ASSIGNMENT"
