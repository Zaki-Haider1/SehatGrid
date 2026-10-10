"""Public-origin routing, declared test capacity and explainable preference points."""

from .common import ACTIVE, available, operator, require


def sender(s, u, facility_id):
    operator(u, facility_id)
    require(
        s["facilities"][facility_id]["ownership"] == "Public",
        "PUBLIC_SENDER_REQUIRED",
        "Only a government hospital receptionist may originate or reroute patients",
        403,
    )
    require(
        s["facilities"][facility_id]["participation"] == "ACTIVE",
        "SOURCE_INACTIVE",
        "Sending hospital must be approved and active",
        403,
    )


def test_key(value):
    return " ".join(value.casefold().split())


def catalog_available(s, r, f, day, exclude=None):
    for name in r.get("required_tests", []):
        if test_remaining(s, f, day, name, exclude, r["id"]) <= 0:
            return False
    return True


def test_remaining(s, f, day, name, exclude=None, request_id=None):
    item = next((i for i in f.get("catalog", []) if test_key(i["name"]) == test_key(name)), None)
    if not item or not item["active"]:
        return 0
    used = sum(
        1
        for a in s.get("referrals", {}).values()
        if a["id"] != exclude
        and a["facility_id"] == f["id"]
        and a["date"] == day
        and a["status"] in (ACTIVE | {"COMPLETED"})
        and a["status"] != "PROPOSED"
        and any(
            test_key(t) == test_key(name) for t in s["requests"][a["request_id"]].get("required_tests", [])
        )
    )
    used += sum(
        1
        for p in s.get("plans", {}).values()
        if p["status"] in {"APPROVED", "ACTIVE"}
        for a in p["assignments"]
        if a["facility_id"] == f["id"]
        and a["date"] == day
        and a["request_id"] != request_id
        and not a.get("consumed")
        and not a.get("cancelled")
        and any(
            test_key(t) == test_key(name) for t in s["requests"][a["request_id"]].get("required_tests", [])
        )
    )
    return max(0, item["daily_capacity"] - used)


def test_groups(snapshot, assignments):
    """Shared constraints for solver and manually revised allocations."""
    requests = {r["id"]: r for r in snapshot["requests"]}
    groups = {}
    for value, a in assignments:
        for name in requests[a["request_id"]].get("required_tests", []):
            key = (a["facility_id"], a["date"], test_key(name))
            groups.setdefault(key, []).append(value)
    for (fid, day, name), values in groups.items():
        f = snapshot["inputs"]["facilities"][fid]
        yield values, test_remaining(snapshot["inputs"], f, day, name)


def routing_score(s, f, c):
    headroom = max(0, available(c)) / max(1, c["quota"])
    policy = f.get("routing_points", 50)
    # Headroom continuously changes with each hold, without waiting for saturation.
    return round(60 * headroom + 0.4 * policy, 2)


def hospital_metrics(s, fid):
    attempts = [a for a in s["referrals"].values() if a["facility_id"] == fid]
    finished = [a for a in attempts if a["status"] in {"COMPLETED", "NO_SHOW", "CANCELLED", "REJECTED"}]
    return {
        "referrals": len(attempts),
        "completed": sum(a["status"] == "COMPLETED" for a in attempts),
        "completion_rate": round(100 * sum(a["status"] == "COMPLETED" for a in finished) / len(finished), 1)
        if finished
        else None,
    }
