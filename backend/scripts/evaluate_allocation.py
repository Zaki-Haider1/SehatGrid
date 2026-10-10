"""Independent exhaustive checker and constrained greedy baseline for tiny fixtures."""

from itertools import product
from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.mvp.seed import make_seed  # noqa: E402
from app.mvp.intelligence import snapshot  # noqa: E402
from app.mvp.planning import solve  # noqa: E402
from app.mvp.common import capacity_key, now  # noqa: E402


def tiny_case(kind):
    s = make_seed()
    s["requests"] = {k: v for k, v in s["requests"].items() if k in ["A-01", "B-01", "C-01"]}
    s["referrals"] = {}
    s["reservations"] = {}
    s["subsidy_rule"]["amount"] = 1
    for c in s["capacities"].values():
        c.update(quota=0, held=0, committed=0, completed=0, forfeited=0)
    s["capacities"][capacity_key("P01", s["service_date"])]["quota"] = 1
    s["offers"]["QUOTA-7"].update(units=1, cost=2)
    s["offers"]["MOBILE-5"].update(units=1, cost=3)
    if kind == "overlap":
        other = deepcopy(s["offers"]["QUOTA-7"])
        other.update(id="QUOTA-OTHER", eligible_zones=["North"], cost=1)
        s["offers"][other["id"]] = other
    if kind == "mobile_overlap":
        other = deepcopy(s["offers"]["MOBILE-5"])
        other.update(id="MOBILE-OTHER", eligible_zones=["Central"], cost=2)
        s["offers"][other["id"]] = other
    if kind == "mixed":
        s["requests"]["B-01"]["needs_funding"] = True
        s["facilities"]["P02"]["subsidy_required"] = True
        s["offers"]["QUOTA-7"]["funding_included"] = False
    if kind == "wrong_date":
        from datetime import timedelta

        s["offers"]["MOBILE-5"]["date"] = (now().date() + timedelta(days=8)).isoformat()
    if kind == "stale":
        from datetime import timedelta

        for c in s["capacities"].values():
            c["updated_at"] = (now() - timedelta(days=3)).isoformat()
        for o in s["offers"].values():
            o["updated_at"] = (now() - timedelta(days=3)).isoformat()
    return snapshot(s, s["users"]["planner"], s["service_date"][:7])


def choices(snap):
    # A separate small reference enumerator; never invokes the CP-SAT model builder.
    resources = []
    for c in snap["inputs"]["capacities"].values():
        f = snap["inputs"]["facilities"][c["facility_id"]]
        age = (now() - __import__("datetime").datetime.fromisoformat(c["updated_at"])).total_seconds()
        capacity = c["quota"] - c["held"] - c["committed"] - c["completed"] - c["forfeited"]
        if age <= 86400 and capacity > 0 and f["participation"] == "ACTIVE" and f["service_reviewed"]:
            resources.append(
                dict(
                    id=c["id"],
                    facility=c["facility_id"],
                    day=c["date"],
                    zones=f["eligible_zones"],
                    units=capacity,
                    fixed=0,
                    included=False,
                    subsidy=f["subsidy_required"],
                    group=None,
                    mobile=None,
                )
            )
    for o in snap["inputs"]["offers"].values():
        f = snap["inputs"]["facilities"][o["facility_id"]]
        age = (now() - __import__("datetime").datetime.fromisoformat(o["updated_at"])).total_seconds()
        if (
            o["status"] == "AVAILABLE"
            and age <= 86400
            and f["participation"] == "ACTIVE"
            and f["service_reviewed"]
        ):
            resources.append(
                dict(
                    id=o["id"],
                    facility=o["facility_id"],
                    day=o["date"],
                    zones=o["eligible_zones"],
                    units=o["units"],
                    fixed=o["cost"],
                    included=o["funding_included"],
                    subsidy=f["subsidy_required"],
                    group=o.get("spare_group"),
                    mobile=o.get("mobile_unit"),
                )
            )
    options = []
    for r in snap["requests"]:
        row = [None]
        for index, resource in enumerate(resources):
            if (
                r["zone"] in resource["zones"]
                and r["date_from"] <= resource["day"] <= r["date_to"]
                and resource["day"][:7] == snap["month"]
            ):
                cost = (
                    snap["inputs"]["subsidy_rule"]["amount"]
                    if r["needs_funding"] and resource["subsidy"] and not resource["included"]
                    else 0
                )
                if cost == 0 or r["funding_eligible"]:
                    row.append((index, cost))
        options.append(row)
    return resources, options


def feasible(resources, assignment, budget):
    used = Counter(a[0] for a in assignment if a is not None)
    if any(n > resources[i]["units"] for i, n in used.items()):
        return None
    groups = []
    mobiles = []
    for i in used:
        r = resources[i]
        if r["group"]:
            groups.append((r["group"], r["day"]))
        if r["mobile"]:
            mobiles.append((r["mobile"], r["day"]))
    if len(groups) != len(set(groups)) or len(mobiles) != len(set(mobiles)):
        return None
    cost = sum(resources[i]["fixed"] for i in used) + sum(a[1] for a in assignment if a is not None)
    return (sum(a is not None for a in assignment), cost) if cost <= budget else None


def exhaustive(snap, budget):
    resources, options = choices(snap)
    best = (0, 0)
    for assignment in product(*options):
        result = feasible(resources, assignment, budget)
        if result and (result[0], -result[1]) > (best[0], -best[1]):
            best = result
    return best


def greedy(snap, budget):
    resources, options = choices(snap)
    assignment = [None] * len(options)
    while True:
        current = feasible(resources, assignment, budget)
        candidates = []
        for i, row in enumerate(options):
            if assignment[i] is not None:
                continue
            for choice in row[1:]:
                proposed = assignment.copy()
                proposed[i] = choice
                result = feasible(resources, proposed, budget)
                if result:
                    candidates.append((result[1] - current[1], i, choice, proposed))
        if not candidates:
            return feasible(resources, assignment, budget)
        assignment = min(candidates, key=lambda c: (c[0], c[1], c[2][0]))[3]


def evaluate():
    rows = []
    for kind in ["standard", "overlap", "mobile_overlap", "mixed", "wrong_date", "stale"]:
        snap = tiny_case(kind)
        for budget in [0, 1, 2, 3, 4, 5, 6]:
            start = time.perf_counter()
            actual = solve(snap, budget)
            elapsed = time.perf_counter() - start
            expected = exhaustive(snap, budget)
            assert (actual["coverage"], actual["cost"]) == expected, (kind, budget, actual, expected)
            rows.append(
                {
                    "case": kind,
                    "budget": budget,
                    "solver_status": actual["status"],
                    "solver_coverage": actual["coverage"],
                    "solver_cost": actual["cost"],
                    "exhaustive_coverage": expected[0],
                    "exhaustive_cost": expected[1],
                    "greedy_coverage": greedy(snap, budget)[0],
                    "greedy_cost": greedy(snap, budget)[1],
                    "runtime_seconds": round(elapsed, 6),
                }
            )
    output = {
        "cases": rows,
        "passed": len(rows),
        "seed": "islamabad-primary-care-v1",
        "limitation": "Tiny synthetic fixtures only. No general superiority claim over greedy allocation.",
    }
    dest = ROOT.parent / "outputs"
    dest.mkdir(exist_ok=True)
    (dest / "allocation-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"{len(rows)} independent exhaustive checks passed; constrained greedy results recorded.")
    return output


if __name__ == "__main__":
    evaluate()
