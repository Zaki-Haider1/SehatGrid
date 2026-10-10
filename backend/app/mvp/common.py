from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from hashlib import sha256
import json
from fastapi import HTTPException
from ..config import get_settings

SERVICE = "PRIMARY_CARE_OPD"
ACTIVE = {"PROPOSED", "AWAITING_CONFIRMATIONS", "CONFIRMED", "ARRIVED"}


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


def local_today():
    return now().astimezone(ZoneInfo("Asia/Karachi")).date().isoformat()


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def fail(code, message, status=409):
    raise HTTPException(status, {"code": code, "message": message})


def require(condition, code, message, status=409):
    if not condition:
        fail(code, message, status)


def get(s, collection, key):
    item = s[collection].get(str(key))
    require(item is not None, "NOT_FOUND", f"{collection} record not found", 404)
    return item


def add(s, collection, item):
    seq = s["sequences"].get(collection, 0) + 1
    s["sequences"][collection] = seq
    item = {"id": f"{collection[:3]}-{seq:04d}", **item}
    s[collection][item["id"]] = item
    return item


def planner(u):
    require(u["role"] == "planner", "ROLE_FORBIDDEN", "Network planner permission required", 403)


def operator(u, facility):
    require(
        u["role"] == "operator" and facility in u["facility_ids"],
        "ROLE_FORBIDDEN",
        "An operator assigned to this facility must perform this action",
        403,
    )


def audit(s, u, action, entity, before=None, after=None, reason=None):
    add(
        s,
        "audit",
        {
            "actor": u["id"],
            "action": action,
            "object_id": entity,
            "before": before,
            "after": after,
            "reason": reason,
            "timestamp": stamp(),
        },
    )


def capacity_key(facility, day):
    return f"{facility}:{SERVICE}:{day}"


def fresh(c):
    return bool(
        c
        and (now() - datetime.fromisoformat(c["updated_at"])).total_seconds()
        <= get_settings().capacity_freshness_minutes * 60
    )


def available(c):
    return c["quota"] - sum(c[k] for k in ("held", "committed", "completed", "forfeited"))


def cap_view(s, c):
    known = fresh(c) and s["facilities"][c["facility_id"]]["participation"] == "ACTIVE"
    count = available(c) if c else None
    status = (
        "UNKNOWN" if not known else "EXHAUSTED" if count == 0 else "LIMITED" if count <= 3 else "AVAILABLE"
    )
    return {
        **c,
        "available": count if known else None,
        "status": status,
        "freshness": "CURRENT" if known else "UNKNOWN",
    }


def budget_view(s, month):
    b = get(s, "budgets", month)
    totals = {
        k: sum(e["amount"] for e in s["ledger"].values() if e["month"] == month and e["state"] == k)
        for k in ("HELD", "COMMITTED", "SETTLED", "RELEASED")
    }
    return {
        **b,
        **totals,
        "remaining": b["authorized"] - sum(totals[k] for k in ("HELD", "COMMITTED", "SETTLED")),
    }


def ledger(s, month, amount, state, reference, transfer=None):
    require(amount >= 0, "INVALID_AMOUNT", "Amounts must be nonnegative")
    if amount == 0:
        return None
    require(budget_view(s, month)["remaining"] >= amount, "BUDGET_EXCEEDED", "Monthly funds are unavailable")
    entry = add(
        s,
        "ledger",
        {
            "month": month,
            "amount": amount,
            "state": state,
            "reference": reference,
            "transfer_from": transfer,
            "updated_at": stamp(),
        },
    )
    s["budgets"][month]["version"] += 1
    return entry["id"]


def ledger_state(s, key, state):
    if key:
        e = get(s, "ledger", key)
        e["state"] = state
        e["updated_at"] = stamp()
        s["budgets"][e["month"]]["version"] += 1
