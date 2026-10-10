"""Planner draft edits reuse solver eligibility and never reserve resources."""

from collections import Counter
from copy import deepcopy

from .common import audit, budget_view, get, planner, require, stamp
from .intelligence import fingerprint
from .planning import assignment_choices, eligible_resources, solve
from .routing import test_groups


DECISION_FIELDS = (
    "assignments",
    "actions",
    "cost",
    "subsidy_cost",
    "projected",
    "additional",
    "additional_request_ids",
    "unresolved_remaining",
)


def current_snapshot(s, p):
    require(p["status"] == "DRAFT", "INVALID_TRANSITION", "Only a draft may be revised")
    require(
        p["input_hash"] == fingerprint(s, p["month"]),
        "STALE_INPUT",
        "Operational inputs changed; create a new snapshot and plan",
    )
    return get(s, "snapshots", p["snapshot_id"])


def selection_for(a):
    return {
        "request_id": a["request_id"],
        "resource_id": a["resource_id"] + (":funded" if not a["offer_id"] and a["funding_included"] else ""),
    }


def validate_selection(snap, selections, budget):
    resources = {r["id"]: r for r in eligible_resources(snap)}
    choices = {(a["request_id"], rid): a for rid, a in assignment_choices(snap, list(resources.values()))}
    require(
        len({a["request_id"] for a in selections}) == len(selections),
        "DUPLICATE_ASSIGNMENT",
        "A request may be assigned only once",
        422,
    )
    assignments = []
    for a in selections:
        key = (a["request_id"], a["resource_id"])
        require(
            key in choices,
            "INELIGIBLE_ASSIGNMENT",
            "Selection violates request, service, zone, date, funding or resource freshness rules",
            422,
        )
        assignments.append(deepcopy(choices[key]))
    counts = Counter(a["resource_id"] for a in selections)
    for rid, count in counts.items():
        require(count <= resources[rid]["units"], "CAPACITY_CONFLICT", "Resource units exceeded")
    offer_ids = sorted(rid for rid in counts if resources[rid]["offer_id"])
    groups = set()
    for oid in offer_ids:
        resource = resources[oid]
        for field in ("spare_group", "mobile_unit"):
            if not resource.get(field):
                continue
            key = (field, resource[field], resource["date"])
            committed = any(
                o["status"] in ["HELD", "ACTIVE"] and o["date"] == key[2] and o.get(field) == key[1]
                for o in snap["inputs"]["offers"].values()
            )
            require(
                key not in groups and not committed,
                "OFFER_CONFLICT",
                "Selected offers overlap a spare-capacity group or mobile unit",
            )
            groups.add(key)
    actions = [
        {
            "id": oid,
            "offer_id": oid,
            "kind": resources[oid]["kind"],
            "cost": resources[oid]["cost"],
            "status": "DRAFT",
        }
        for oid in offer_ids
    ]
    for values, remaining in test_groups(snap, [(1, a) for a in assignments]):
        require(sum(values) <= remaining, "TEST_CAPACITY_CONFLICT", "Required test daily capacity exceeded")
    subsidy = sum(a["subsidy"] for a in assignments)
    cost = sum(a["cost"] for a in actions) + subsidy
    require(cost <= budget, "BUDGET_EXCEEDED", "Selection exceeds remaining monthly funds")
    return {
        "assignments": sorted(assignments, key=lambda a: a["request_id"]),
        "actions": actions,
        "cost": cost,
        "subsidy_cost": subsidy,
        "projected": len(assignments),
        "unresolved_remaining": len(snap["requests"]) - len(assignments),
    }


def validate_draft(s, p):
    snap = current_snapshot(s, p)
    derived = validate_selection(
        snap,
        [selection_for(a) for a in p["assignments"]],
        budget_view(s, p["month"])["remaining"],
    )
    require(
        derived["assignments"] == sorted(p["assignments"], key=lambda a: a["request_id"])
        and derived["actions"] == sorted(p["actions"], key=lambda a: a["id"])
        and all(derived[k] == p[k] for k in ("cost", "subsidy_cost", "projected", "unresolved_remaining"))
        and p["additional"] == max(0, derived["projected"] - p["baseline"]),
        "INVALID_PLAN",
        "Draft allocations and totals must match validated selections",
    )


def revision_options(s, u, pid):
    planner(u)
    p = get(s, "plans", pid)
    snap = current_snapshot(s, p)
    resources = eligible_resources(snap)
    choices = assignment_choices(snap, resources)
    valid = {rid for rid, _ in choices}
    return {
        "contract_version": "plan-revision-v1",
        "plan_id": pid,
        "version": p["version"],
        "input_hash": p["input_hash"],
        "remaining_budget": budget_view(s, p["month"])["remaining"],
        "current_assignments": [selection_for(a) for a in p["assignments"]],
        "resources": [r for r in resources if r["id"] in valid],
        "choices": [{**a, "resource_id": rid} for rid, a in choices],
    }


def revise(s, u, pid, data):
    planner(u)
    p = get(s, "plans", pid)
    snap = current_snapshot(s, p)
    require(data["version"] == p["version"], "STALE_INPUT", "Draft was edited; refresh before revising")
    derived = validate_selection(snap, data["assignments"], budget_view(s, p["month"])["remaining"])
    original = p.get("original_solver_result")
    if original is None:  # Existing stored drafts remain editable after upgrading the API.
        baseline = solve(snap, 0, True)
        original = {
            "status": p["solver_status"],
            "coverage": p["projected"],
            "baseline_assignments": baseline["assignments"],
            "baseline": p["baseline"],
            "runtime_seconds": p["runtime_seconds"],
            **{k: deepcopy(p[k]) for k in DECISION_FIELDS},
        }
    derived["additional"] = max(0, derived["projected"] - p["baseline"])
    derived["additional_request_ids"] = sorted(
        {a["request_id"] for a in derived["assignments"]}
        - {a["request_id"] for a in original["baseline_assignments"]}
    )[: derived["additional"]]
    before = {k: deepcopy(p[k]) for k in DECISION_FIELDS}
    revision = {
        "version": p["version"] + 1,
        "actor": u["id"],
        "timestamp": stamp(),
        "reason": data["reason"],
        "before": before,
        "after": deepcopy(derived),
    }
    p.update(derived, version=revision["version"], decision_source="HUMAN_REVISION")
    p.setdefault("original_solver_result", deepcopy(original))
    p.setdefault("revisions", []).append(revision)
    audit(s, u, "PLAN_REVISED", pid, before=before, after=deepcopy(derived), reason=data["reason"])
    return p
