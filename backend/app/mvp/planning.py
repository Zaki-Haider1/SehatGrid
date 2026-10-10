from copy import deepcopy

from collections import defaultdict

from ortools.sat.python import cp_model

from .common import (
    SERVICE,
    add,
    stamp,
    require,
    get,
    planner,
    operator,
    audit,
    fresh,
    available,
    budget_view,
    ledger,
    ledger_state,
    capacity_key,
    local_today,
)

from .intelligence import fingerprint
from .routing import catalog_available, test_groups

from ..config import get_settings


def eligible_resources(snapshot, baseline=False):

    inputs = snapshot["inputs"]

    resources = []

    for c in sorted(inputs["capacities"].values(), key=lambda c: c["id"]):
        f = inputs["facilities"][c["facility_id"]]

        if (
            fresh(c)
            and available(c) > 0
            and f["participation"] == "ACTIVE"
            and f["service_reviewed"]
            and f["service_id"] == SERVICE
            and c["service_id"] == SERVICE
            and f.get("canonical_id", f["id"]) == f["id"]
        ):
            covered = min(available(c), c.get("funded_free", 0))

            for included, units in [(False, available(c) - covered), (True, covered)]:
                if units:
                    resources.append(
                        {
                            "id": c["id"] + (":funded" if included else ""),
                            "capacity_id": c["id"],
                            "facility_id": f["id"],
                            "date": c["date"],
                            "zones": f["eligible_zones"],
                            "units": units,
                            "offer_id": None,
                            "cost": 0,
                            "funding_included": included,
                            "subsidy_required": f["subsidy_required"],
                        }
                    )

    if not baseline:
        for o in sorted(inputs["offers"].values(), key=lambda o: o["id"]):
            f = inputs["facilities"][o["facility_id"]]

            if (
                o["status"] == "AVAILABLE"
                and fresh(o)
                and o["date"][:7] == snapshot["month"]
                and f["participation"] == "ACTIVE"
                and f["service_reviewed"]
                and f["service_id"] == SERVICE
                and o["service_id"] == SERVICE
                and f.get("canonical_id", f["id"]) == f["id"]
            ):
                resources.append(
                    {
                        "id": o["id"],
                        "facility_id": ("site:" + o["id"]) if o["kind"] == "MOBILE" else f["id"],
                        "date": o["date"],
                        "zones": o["eligible_zones"],
                        "units": o["units"],
                        "offer_id": o["id"],
                        "cost": o["cost"],
                        "funding_included": o["funding_included"],
                        "subsidy_required": f["subsidy_required"],
                        "kind": o["kind"],
                        "spare_group": o.get("spare_group"),
                        "mobile_unit": o.get("mobile_unit"),
                    }
                )

    return resources


def assignment_choices(snapshot, resources, baseline=False):
    inputs = snapshot["inputs"]
    choices = []

    for request in sorted(snapshot["requests"], key=lambda r: r["id"]):
        if (
            not request["suitable"]
            or inputs["facilities"].get(request["source_facility_id"], {}).get("ownership") != "Public"
            or inputs["facilities"].get(request["source_facility_id"], {}).get("participation") != "ACTIVE"
            or not request["service_reviewed"]
            or request["service_id"] != SERVICE
            or request.get("blocked_reasons")
            or request["status"] not in ["OPEN", "UNRESOLVED"]
            or request["needs_funding"]
            and not request["funding_eligible"]
        ):
            continue
        for resource in resources:
            destination = inputs["facilities"].get(resource["facility_id"])
            if request.get("required_tests") and (
                not destination or not catalog_available(inputs, request, destination, resource["date"])
            ):
                continue
            if (
                resource["facility_id"] == request["source_facility_id"]
                or request["zone"] not in resource["zones"]
                or not request["date_from"] <= resource["date"] <= request["date_to"]
                or resource["date"][:7] != snapshot["month"]
                or resource["date"] < local_today()
            ):
                continue

            sub = (
                inputs["subsidy_rule"]["amount"]
                if request["needs_funding"]
                and resource["subsidy_required"]
                and not resource["funding_included"]
                else 0
            )

            if sub and (
                baseline
                or not request["funding_eligible"]
                or inputs["subsidy_rule"]["month"] != snapshot["month"]
            ):
                continue

            assignment = {
                "request_id": request["id"],
                "resource_id": resource.get("capacity_id", resource["id"]),
                "facility_id": resource["facility_id"],
                "date": resource["date"],
                "offer_id": resource["offer_id"],
                "subsidy": sub,
                "funding_included": resource["funding_included"],
            }

            choices.append((resource["id"], assignment))
    return choices


def solve(snapshot, budget, baseline=False):
    inputs = snapshot["inputs"]
    resources = eligible_resources(snapshot, baseline)
    model = cp_model.CpModel()
    ys = {r["id"]: model.new_bool_var("buy_" + r["id"]) for r in resources if r["offer_id"]}
    xs = []
    by_request = defaultdict(list)
    by_resource = defaultdict(list)
    for resource_id, assignment in assignment_choices(snapshot, resources, baseline):
        v = model.new_bool_var(f"assign_{assignment['request_id']}_{resource_id}")
        xs.append((v, assignment))
        by_request[assignment["request_id"]].append(v)
        by_resource[resource_id].append(v)

    for values in by_request.values():
        model.add(sum(values) <= 1)
    for values, remaining in test_groups(snapshot, xs):
        model.add(sum(values) <= remaining)

    for resource in resources:
        variables = by_resource[resource["id"]]

        if resource["offer_id"]:
            model.add(sum(variables) <= resource["units"] * ys[resource["id"]])

            model.add(ys[resource["id"]] <= sum(variables))

        else:
            model.add(sum(variables) <= resource["units"])

    groups = defaultdict(list)

    for resource in resources:
        if resource.get("spare_group"):
            groups[("spare", resource["spare_group"], resource["date"])].append(ys[resource["id"]])

        if resource.get("mobile_unit"):
            groups[("mobile", resource["mobile_unit"], resource["date"])].append(ys[resource["id"]])

    # An available offer can still overlap an already committed different offer.

    for key, values in groups.items():
        used = any(
            o["status"] in ["HELD", "ACTIVE"]
            and o["date"] == key[2]
            and o.get("spare_group" if key[0] == "spare" else "mobile_unit") == key[1]
            for o in inputs["offers"].values()
        )

        model.add(sum(values) <= 0 if used else sum(values) <= 1)

    cost = sum(r["cost"] * ys[r["id"]] for r in resources if r["offer_id"]) + sum(
        v * a["subsidy"] for v, a in xs
    )

    coverage = sum(v for v, _ in xs)

    model.add(cost <= budget)

    model.maximize(coverage)

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = get_settings().optimizer_time_limit_seconds

    solver.parameters.num_search_workers = 1

    solver.parameters.random_seed = 0

    status = solver.solve(model)

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return {
            "status": solver.status_name(status),
            "assignments": [],
            "offer_ids": [],
            "coverage": 0,
            "cost": 0,
            "runtime_seconds": solver.wall_time,
        }

    optimal = status == cp_model.OPTIMAL

    if optimal:
        model.add(coverage == int(solver.value(coverage)))

        model.minimize(cost)

        status = solver.solve(model)

        optimal = status == cp_model.OPTIMAL

        if optimal:
            model.add(cost == int(solver.value(cost)))

            model.minimize(sum((i + 1) * v for i, (v, _) in enumerate(xs)))

            status = solver.solve(model)

            optimal = status == cp_model.OPTIMAL

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return {
            "status": solver.status_name(status),
            "assignments": [],
            "offer_ids": [],
            "coverage": 0,
            "cost": 0,
            "runtime_seconds": solver.wall_time,
        }

    assignments = [a for v, a in xs if solver.value(v)]

    return {
        "status": "OPTIMAL" if optimal else "FEASIBLE",
        "assignments": assignments,
        "offer_ids": [key for key, v in ys.items() if solver.value(v)],
        "coverage": len(assignments),
        "cost": int(solver.value(cost)),
        "runtime_seconds": solver.wall_time,
    }


def optimize(s, u, data):

    planner(u)

    snap = get(s, "snapshots", data["snapshot_id"])

    month = snap["month"]

    require(
        snap["input_hash"] == fingerprint(s, month),
        "STALE_INPUT",
        "Create a new snapshot; operational inputs changed",
    )

    b = budget_view(s, month)

    baseline = solve(snap, 0, True)

    result = solve(snap, b["remaining"])

    require(
        result["status"] in ["OPTIMAL", "FEASIBLE"],
        "SOLVER_FAILED",
        f"Solver returned {result['status']}; no plan was fabricated",
        422,
    )

    actions = [
        {
            "id": oid,
            "offer_id": oid,
            "kind": s["offers"][oid]["kind"],
            "cost": s["offers"][oid]["cost"],
            "status": "DRAFT",
        }
        for oid in result["offer_ids"]
    ]

    p = add(
        s,
        "plans",
        {
            "snapshot_id": snap["id"],
            "month": month,
            "status": "DRAFT",
            "version": 1,
            "created_at": stamp(),
            "input_hash": snap["input_hash"],
            "budget_version": b["version"],
            "solver_status": result["status"],
            "solver": "OR-Tools CP-SAT",
            "solver_parameters": {
                "workers": 1,
                "seed": 0,
                "time_limit_seconds": get_settings().optimizer_time_limit_seconds,
            },
            "assignments": result["assignments"],
            "actions": actions,
            "cost": result["cost"],
            "projected": result["coverage"],
            "baseline": baseline["coverage"],
            "additional_request_ids": sorted(
                {a["request_id"] for a in result["assignments"]}
                - {a["request_id"] for a in baseline["assignments"]}
            )[: max(0, result["coverage"] - baseline["coverage"])],
            "additional": max(0, result["coverage"] - baseline["coverage"]),
            "unresolved_remaining": len(snap["requests"]) - result["coverage"],
            "excluded": snap["excluded"],
            "subsidy_cost": sum(a["subsidy"] for a in result["assignments"]),
            "pool_ledger_id": None,
            "runtime_seconds": result["runtime_seconds"],
            "origin_type": "synthetic",
            "assumptions": [
                "Non-emergency general primary-care only",
                "Declared zone eligibility, not travel access",
                "Manual quota freshness; no forecasts",
                "Synthetic costs and agreements; no real payments",
                "Projected accommodation is not a completed service",
                "Partner/mobile resources require operator activation",
            ],
        },
    )

    p["decision_source"] = "SOLVER"
    p["revisions"] = []
    p["original_solver_result"] = {
        **deepcopy(result),
        "actions": deepcopy(actions),
        "baseline_assignments": deepcopy(baseline["assignments"]),
        "baseline": p["baseline"],
        "additional": p["additional"],
        "subsidy_cost": p["subsidy_cost"],
        "unresolved_remaining": p["unresolved_remaining"],
    }

    audit(s, u, "PLAN_GENERATED", p["id"], after={"cost": p["cost"], "additional": p["additional"]})

    return p


def approve(s, u, pid, version=None):

    planner(u)

    p = get(s, "plans", pid)

    require(p["status"] == "DRAFT", "INVALID_TRANSITION", "Only a draft may be approved")

    require(
        (version is None and p.get("decision_source", "SOLVER") == "SOLVER") or version == p["version"],
        "STALE_INPUT",
        "Refresh the draft and approve its current version",
    )

    require(
        p["input_hash"] == fingerprint(s, p["month"]),
        "STALE_INPUT",
        "Inputs changed; recompute from a new snapshot",
    )

    require(
        budget_view(s, p["month"])["remaining"] >= p["cost"], "BUDGET_EXCEEDED", "Insufficient monthly funds"
    )

    from .plan_revision import validate_draft

    validate_draft(s, p)

    for action in p["actions"]:
        o = get(s, "offers", action["offer_id"])

        require(o["status"] == "AVAILABLE" and fresh(o), "STALE_INPUT", "Offer is unavailable or stale")

        for other in s["offers"].values():
            overlap = other["date"] == o["date"] and (
                (o.get("spare_group") and other.get("spare_group") == o["spare_group"])
                or (o.get("mobile_unit") and other.get("mobile_unit") == o["mobile_unit"])
            )

            require(
                not (overlap and other["status"] in ["HELD", "ACTIVE"]),
                "OFFER_CONFLICT",
                "Overlapping capacity or mobile unit is already committed",
            )

        o["status"] = "HELD"

        o["version"] += 1

        action.update(
            status="PENDING_ACTIVATION",
            ledger_id=ledger(s, p["month"], action["cost"], "COMMITTED", p["id"] + ":" + action["id"]),
            expires_at=o["date"] + "T23:59:59+05:00",
        )

    if p["subsidy_cost"]:
        p["pool_ledger_id"] = ledger(s, p["month"], p["subsidy_cost"], "COMMITTED", p["id"] + ":subsidy-pool")

    for assignment in p["assignments"]:
        if not assignment["offer_id"]:
            c = get(s, "capacities", assignment["resource_id"])

            require(available(c) > 0, "CAPACITY_CONFLICT", "Base capacity was consumed")

            c["held"] += 1

            c["version"] += 1

            assignment["capacity_held"] = True

    p["status"] = "APPROVED"

    p["version"] += 1

    audit(s, u, "PLAN_APPROVED", pid, after={"cost": p["cost"], "actions": deepcopy(p["actions"])})

    return p


def activate(s, u, pid, action_id):

    p = get(s, "plans", pid)

    action = next((a for a in p["actions"] if a["id"] == action_id), None)

    require(action, "NOT_FOUND", "Action not found", 404)

    o = get(s, "offers", action["offer_id"])

    operator(u, o["facility_id"])

    require(
        p["status"] in ["APPROVED", "ACTIVE"] and action["status"] == "PENDING_ACTIVATION",
        "INVALID_TRANSITION",
        "Action is not awaiting activation",
    )

    f = get(s, "facilities", o["facility_id"])

    require(f["participation"] == "ACTIVE", "STALE_INPUT", "Partner is suspended")

    require(o["status"] == "HELD", "OFFER_CONFLICT", "Offer is no longer reserved")

    target_id = o["facility_id"]

    if o["kind"] == "MOBILE":
        target_id = "site:" + o["id"]

        s["facilities"][target_id] = {
            "id": target_id,
            "name": "Demo mobile clinic - " + o["site"],
            "original_name": o["site"],
            "canonical_id": target_id,
            "ownership": "Public",
            "address": o["site"],
            "zone": o["eligible_zones"][0],
            "latitude": o["latitude"],
            "longitude": o["longitude"],
            "participation": "ACTIVE",
            "version": 1,
            "origin_type": "synthetic",
            "eligible_zones": o["eligible_zones"],
            "service_reviewed": True,
            "service_id": SERVICE,
            "subsidy_required": f["subsidy_required"],
            "aliases": [],
        }

        u["facility_ids"].append(target_id)

    key = capacity_key(target_id, o["date"])

    if key not in s["capacities"]:
        s["capacities"][key] = {
            "id": key,
            "facility_id": target_id,
            "service_id": SERVICE,
            "date": o["date"],
            "quota": 0,
            "held": 0,
            "committed": 0,
            "completed": 0,
            "forfeited": 0,
            "version": 0,
            "origin_type": "synthetic",
            "updated_at": stamp(),
            "updated_by": u["id"],
        }

    c = s["capacities"][key]

    require(
        c["quota"] == 0 or fresh(c),
        "STALE_INPUT",
        "Refresh the existing quota before activating additional units",
    )

    c["quota"] += o["units"]

    c["updated_at"] = stamp()

    c["updated_by"] = u["id"]

    c["version"] += 1

    for assignment in p["assignments"]:
        if assignment["offer_id"] == o["id"]:
            c["held"] += 1

            assignment["capacity_held"] = True

    if o["funding_included"]:
        c["funding_included_available"] = c.get("funding_included_available", 0) + o["units"]

    ledger_state(s, action["ledger_id"], "SETTLED")

    o["status"] = "ACTIVE"

    o["version"] += 1

    action.update(status="ACTIVE", activated_by=u["id"], activated_at=stamp())

    p["status"] = "ACTIVE"

    audit(
        s, u, "RESOURCE_ACTIVATED", pid + ":" + action_id, after={"quota": c["quota"], "cost": action["cost"]}
    )

    return p


def cancel_plan(s, u, pid, reason):

    planner(u)

    p = get(s, "plans", pid)

    require(p["status"] in ["DRAFT", "APPROVED", "ACTIVE"], "INVALID_TRANSITION", "Plan is already closed")

    for assignment in p["assignments"]:
        if not assignment.get("consumed"):
            assignment["cancelled"] = True
        if assignment.get("capacity_held") and not assignment.get("consumed"):
            c = get(s, "capacities", capacity_key(assignment["facility_id"], assignment["date"]))

            c["held"] -= 1

            c["version"] += 1

            assignment["capacity_held"] = False

    ledger_state(s, p["pool_ledger_id"], "RELEASED")

    for action in p["actions"]:
        if action["status"] == "PENDING_ACTIVATION":
            ledger_state(s, action.get("ledger_id"), "RELEASED")

            o = s["offers"][action["offer_id"]]

            o["status"] = "AVAILABLE"

            o["version"] += 1

            action["status"] = "CANCELLED"

        elif action["status"] == "ACTIVE":
            action["status"] = "CLOSED"

    p["status"] = "CLOSED" if any(a["status"] == "CLOSED" for a in p["actions"]) else "CANCELLED"

    audit(s, u, "PLAN_CLOSED", pid, reason=reason)

    return p


def reject_action(s, u, pid, action_id, reason):

    p = get(s, "plans", pid)

    action = next((a for a in p["actions"] if a["id"] == action_id), None)

    require(action, "NOT_FOUND", "Action not found", 404)

    offer = get(s, "offers", action["offer_id"])

    operator(u, offer["facility_id"])

    require(
        action["status"] == "PENDING_ACTIVATION",
        "INVALID_TRANSITION",
        "Only pending resources can be rejected",
    )

    ledger_state(s, action.get("ledger_id"), "RELEASED")

    released_subsidy = 0

    removed = 0

    for a in p["assignments"]:
        if a["offer_id"] == offer["id"] and not a.get("consumed"):
            a["cancelled"] = True

            released_subsidy += a["subsidy"]

            removed += 1

    if released_subsidy:
        pool = get(s, "ledger", p["pool_ledger_id"])

        pool["amount"] -= released_subsidy

        ledger(s, p["month"], released_subsidy, "RELEASED", p["id"] + ":rejected-subsidy", pool["id"])

    p.setdefault("original_projected", p["projected"])

    p.setdefault("original_cost", p["cost"])

    p["projected"] -= removed

    p["additional"] = max(0, p["projected"] - p["baseline"])

    p["unresolved_remaining"] += removed

    p["cost"] -= action["cost"] + released_subsidy

    p["subsidy_cost"] -= released_subsidy

    offer.update(status="REJECTED", version=offer["version"] + 1)

    action.update(status="REJECTED", reason=reason)

    audit(s, u, "RESOURCE_REJECTED", pid + ":" + action_id, reason=reason)

    return p
