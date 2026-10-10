from collections import Counter
from copy import deepcopy
from .common import add, stamp, digest, SERVICE, ACTIVE, cap_view, budget_view
from .referrals import refresh_request


def operational_rules(s):
    from ..config import get_settings

    settings = get_settings()
    rules = {
        "freshness_minutes": settings.capacity_freshness_minutes,
        "hold_minutes": settings.referral_hold_minutes,
        "cutoff": settings.cancellation_cutoff_local,
        "match_threshold": settings.match_review_threshold,
        "policy_version": s["policy_version"],
    }
    return rules


def fingerprint(s, month):
    rules = operational_rules(s)
    return digest(
        {
            "rules": rules,
            **{
                k: s[k]
                for k in [
                    "facilities",
                    "capacities",
                    "requests",
                    "referrals",
                    "offers",
                    "budgets",
                    "ledger",
                    "subsidy_rule",
                ]
            },
        }
    )


def intelligence(s, month):
    for r in s["requests"].values():
        refresh_request(s, r)
    requests = [r for r in s["requests"].values() if r["date_from"][:7] <= month <= r["date_to"][:7]]
    active = {
        a["request_id"]
        for a in s["referrals"].values()
        if a["status"] in ACTIVE and a["status"] != "PROPOSED"
    }
    unresolved = [
        r for r in requests if r["id"] not in active and r["status"] not in ["FULFILLED", "CANCELLED"]
    ]
    zones = []
    for zone in list(s["zones"]) + ["Unknown zone"]:
        rows = [r for r in unresolved if (r["zone"] if r["zone"] in s["zones"] else "Unknown zone") == zone]
        zones.append(
            {
                "zone": zone,
                "count": len(rows),
                "reasons": dict(
                    Counter(reason for r in rows for reason in (r["reasons"] or ["AWAITING_COORDINATION"]))
                ),
            }
        )
    attempts = [a for a in s["referrals"].values() if a["date"][:7] == month]
    confirmed = {a["request_id"] for a in attempts if a.get("confirmed_at")}
    completed = {a["request_id"] for a in attempts if a["status"] == "COMPLETED"}
    arrived = {a["request_id"] for a in attempts if a.get("arrived_at") or a["status"] == "COMPLETED"}
    plans = [
        p
        for p in s["plans"].values()
        if p["month"] == month and p["status"] in ["APPROVED", "ACTIVE", "CLOSED"]
    ]
    post = [a for a in attempts if a.get("plan_id")]
    return {
        "month": month,
        "origin_type": "synthetic",
        "label": "Recorded unmet network demand",
        "zones": zones,
        "unresolved": len(unresolved),
        "registered": len(requests),
        "confirmed": len(confirmed),
        "arrived": len(arrived),
        "completed": len(completed),
        "pending_confirmations": len(
            {a["request_id"] for a in attempts if a["status"] == "AWAITING_CONFIRMATIONS"}
        ),
        "cancelled": sum(r["status"] == "CANCELLED" for r in requests),
        "projected_additional": len(
            {
                a["request_id"]
                for p in plans
                for a in p["assignments"]
                if a["request_id"] in p.get("additional_request_ids", []) and not a.get("cancelled")
            }
        ),
        "post_activation_confirmed": len({a["request_id"] for a in post if a.get("confirmed_at")}),
        "post_activation_completed": len({a["request_id"] for a in post if a["status"] == "COMPLETED"}),
        "completion_rate": {
            "numerator": len(completed),
            "denominator": len(confirmed),
            "period": month,
            "note": "Includes pending referrals; not a mature-cohort outcome estimate",
        },
        "capacities": [cap_view(s, c) for c in s["capacities"].values() if c["date"][:7] == month],
        "budget": budget_view(s, month) if month in s["budgets"] else None,
    }


def snapshot(s, u, month):
    summary = intelligence(s, month)
    eligible = []
    excluded = Counter()
    committed = {
        a["request_id"]
        for p in s["plans"].values()
        if p["status"] in ["APPROVED", "ACTIVE"]
        for a in p["assignments"]
        if not a.get("consumed") and not a.get("cancelled")
    }
    for r in s["requests"].values():
        if not (r["date_from"][:7] <= month <= r["date_to"][:7]):
            continue
        if r["status"] in ["FULFILLED", "CANCELLED", "IN_PROGRESS"] or r["id"] in committed:
            excluded["ALREADY_ACCOMMODATED_OR_PLANNED"] += 1
        elif (
            not r["suitable"]
            or s["facilities"].get(r["source_facility_id"], {}).get("ownership") != "Public"
            or s["facilities"].get(r["source_facility_id"], {}).get("participation") != "ACTIVE"
            or not r["service_reviewed"]
            or r["service_id"] != SERVICE
            or r.get("blocked_reasons")
        ):
            excluded[(r["reasons"] or ["SERVICE_UNREVIEWED"])[0]] += 1
        elif r["reasons"] == ["CAPACITY_UNKNOWN_OR_STALE"]:
            excluded["CAPACITY_UNKNOWN_OR_STALE"] += 1
        elif r["needs_funding"] and not r["funding_eligible"]:
            excluded["FUNDING_INELIGIBLE"] += 1
        else:
            eligible.append({k: deepcopy(v) for k, v in r.items() if k != "whatsapp_phone"})
    inputs = {
        k: deepcopy(s[k])
        for k in ["facilities", "capacities", "offers", "subsidy_rule", "requests", "referrals", "plans"]
    }
    for request in inputs["requests"].values():
        request.pop("whatsapp_phone", None)
    for c in inputs["capacities"].values():
        protected = sum(
            1
            for p in s["plans"].values()
            if p["status"] in ["APPROVED", "ACTIVE"]
            for a in p["assignments"]
            if a.get("capacity_held")
            and a.get("funding_included")
            and not a.get("consumed")
            and not a.get("cancelled")
            and a["facility_id"] == c["facility_id"]
            and a["date"] == c["date"]
        )
        c["funded_free"] = max(0, c.get("funding_included_available", 0) - protected)
    return add(
        s,
        "snapshots",
        {
            "month": month,
            "timestamp": stamp(),
            "actor": u["id"],
            "requests": eligible,
            "excluded": dict(excluded),
            "summary": summary,
            "inputs": inputs,
            "input_hash": fingerprint(s, month),
            "dataset_version": s["dataset_version"],
            "policy_version": s["policy_version"],
            "operational_rules": operational_rules(s),
            "origin_type": "synthetic",
            "immutable": True,
        },
    )
