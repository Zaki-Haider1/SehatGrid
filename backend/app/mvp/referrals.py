from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .common import (
    SERVICE,
    ACTIVE,
    now,
    stamp,
    require,
    get,
    add,
    operator,
    planner,
    audit,
    fresh,
    available,
    ledger,
    ledger_state,
    budget_view,
)
from ..config import get_settings

STALE_PROPOSAL_REASON = "Proposal inputs changed; refresh recommendations"


def compatible(r, f, day):
    return (
        f["participation"] == "ACTIVE"
        and f.get("canonical_id", f["id"]) == f["id"]
        and f["service_reviewed"]
        and f["service_id"] == SERVICE
        and r["zone"] in f["eligible_zones"]
        and r["date_from"] <= day <= r["date_to"]
        and day >= now().astimezone(ZoneInfo("Asia/Karachi")).date().isoformat()
    )


def active_attempt(s, rid):
    return next(
        (a for a in s["referrals"].values() if a["request_id"] == rid and a["status"] in ACTIVE), None
    )


def subsidy(s, r, f):
    return s["subsidy_rule"]["amount"] if r["needs_funding"] and f["subsidy_required"] else 0


def entitlement(s, rid, fid, day):
    for p in s["plans"].values():
        if p["status"] not in ["APPROVED", "ACTIVE"]:
            continue
        for a in p["assignments"]:
            if (
                a["request_id"] == rid
                and a["facility_id"] == fid
                and a["date"] == day
                and not a.get("consumed")
                and not a.get("cancelled")
            ):
                action = next((x for x in p["actions"] if x["offer_id"] == a.get("offer_id")), None)
                if not action or action["status"] == "ACTIVE":
                    return p, a
    return None, None


def recommendations(s, r, allow_attempt=None):
    ranking_policy = s["ranking_policy"]
    if not r["suitable"]:
        return {"candidates": [], "reasons": ["OUT_OF_SCOPE"]}
    if not r["service_reviewed"] or r["service_id"] != SERVICE:
        return {"candidates": [], "reasons": ["SERVICE_UNREVIEWED"]}
    active = active_attempt(s, r["id"])
    if (active and active["id"] != allow_attempt) or r["status"] in ["FULFILLED", "CANCELLED"]:
        reason = "REFERRAL_PROPOSED" if active and active["status"] == "PROPOSED" else "ALREADY_ACCOMMODATED"
        return {"candidates": [], "reasons": [reason]}
    options = []
    reasons = set()
    eligible = False
    for c in s["capacities"].values():
        f = s["facilities"][c["facility_id"]]
        if not compatible(r, f, c["date"]):
            continue
        eligible = True
        if not fresh(c):
            reasons.add("CAPACITY_UNKNOWN_OR_STALE")
            continue
        p, a = entitlement(s, r["id"], f["id"], c["date"])
        entitled = bool(a and a.get("capacity_held"))
        if available(c) <= 0 and not entitled:
            reasons.add("CAPACITY_EXHAUSTED")
            continue
        protected_funded = sum(
            1
            for plan in s["plans"].values()
            if plan["status"] in ["APPROVED", "ACTIVE"]
            for assignment in plan["assignments"]
            if assignment.get("capacity_held")
            and assignment["facility_id"] == f["id"]
            and assignment["date"] == c["date"]
            and assignment.get("funding_included")
            and not assignment.get("consumed")
            and not assignment.get("cancelled")
        )
        package_funded = (
            bool(a and a.get("funding_included")) or c.get("funding_included_available", 0) > protected_funded
        )
        cost = 0 if package_funded else a["subsidy"] if a else subsidy(s, r, f)
        if cost and not a and s["subsidy_rule"]["month"] != c["date"][:7]:
            reasons.add("FUNDING_UNAVAILABLE")
            continue
        funding_ok = not cost or (
            r["funding_eligible"]
            and (
                bool(a and a.get("subsidy"))
                or c["date"][:7] in s["budgets"]
                and budget_view(s, c["date"][:7])["remaining"] >= cost
            )
        )
        if not funding_ok:
            reasons.add("FUNDING_UNAVAILABLE")
            continue
        options.append(
            {
                "facility_id": f["id"],
                "name": f["name"],
                "capacity_id": c["id"],
                "date": c["date"],
                "available": available(c) + int(entitled),
                "capacity_version": c["version"],
                "facility_version": f["version"],
                "subsidy": cost,
                "package_funded": package_funded,
                "same_zone": f["zone"] == r["zone"],
                "policy_version": s["policy_version"],
                "ranking_policy_version": f"referral-ranking-v{ranking_policy['version']}",
                "plan_id": p["id"] if p else None,
                "funding_authorization_required": bool(cost),
                "explanation": f"Reviewed primary-care service; declared zone eligibility; {available(c) + int(entitled)} eligible units (including any reserved plan unit). Receiving acceptance and patient agreement required.",
            }
        )
    criterion_keys = {
        "same_zone": lambda x: not x["same_zone"],
        "subsidy": lambda x: x["subsidy"],
        "available": lambda x: -x["available"],
    }
    options.sort(
        key=lambda x: tuple(criterion_keys[name](x) for name in ranking_policy["criteria"])
        + (x["facility_id"], x["date"])
    )
    if not eligible:
        reasons.add("NO_ELIGIBLE_PARTNER")
    return {
        "candidates": options,
        "ranking_policy_version": f"referral-ranking-v{ranking_policy['version']}",
        "reasons": sorted(reasons)
        if not options
        else (["FUNDING_UNAVAILABLE"] if all(o["subsidy"] and not o["plan_id"] for o in options) else []),
        "policy_version": s["policy_version"],
    }


def refresh_request(s, r):
    if r["status"] in ["FULFILLED", "CANCELLED"]:
        return
    active = active_attempt(s, r["id"])
    if active:
        r["status"] = "OPEN" if active["status"] == "PROPOSED" else "IN_PROGRESS"
        r["reasons"] = ["REFERRAL_PROPOSED"] if active["status"] == "PROPOSED" else []
    elif not r["suitable"]:
        r["status"] = "OUT_OF_SCOPE"
        r["reasons"] = ["OUT_OF_SCOPE"]
    else:
        result = recommendations(s, r)
        r["status"] = "OPEN" if result["candidates"] else "UNRESOLVED"
        # A patient decline needs explicit reprocessing before funding may address it.
        r["reasons"] = list(dict.fromkeys(r.get("blocked_reasons", []) + result["reasons"]))


def release(s, a, status, reason, actor):
    was = a["status"]
    reservation_state = None
    if was != "PROPOSED":
        c = get(s, "capacities", a["capacity_id"])
        if was == "AWAITING_CONFIRMATIONS":
            c["held"] -= 1
            reservation_state = "RELEASED"
        else:
            c["committed"] -= 1
            cutoff = datetime.fromisoformat(a["date"] + "T" + get_settings().cancellation_cutoff_local).replace(
                tzinfo=ZoneInfo("Asia/Karachi")
            )
            forfeited = status == "NO_SHOW" or now() >= cutoff
            if forfeited:
                c["forfeited"] += 1
            reservation_state = "FORFEITED" if forfeited else "RELEASED"
        if a.get("package_funded") and reservation_state == "RELEASED":
            c["funding_included_available"] = c.get("funding_included_available", 0) + 1
        c["version"] += 1
        ledger_state(s, a.get("ledger_id"), "RELEASED")
    a.update(status=status, reason=reason, updated_at=stamp(), version=a["version"] + 1)
    if reservation_state is not None:
        s["reservations"][a["id"]]["state"] = reservation_state
    if a.get("plan_id"):
        for assignment in s["plans"][a["plan_id"]]["assignments"]:
            if assignment.get("referral_id") == a["id"]:
                assignment["cancelled"] = True
    r = s["requests"][a["request_id"]]
    if reason == "PATIENT_DECLINED":
        r["blocked_reasons"] = ["PATIENT_DECLINED"]
    r["last_attempt_reason"] = "PARTNER_REJECTED" if status == "REJECTED" else reason
    refresh_request(s, r)
    audit(s, actor, status, a["id"], before=was, after=status, reason=reason)


def proposal_is_stale(s, a):
    c = s["capacities"].get(a["capacity_id"])
    f = s["facilities"].get(a["facility_id"])
    r = s["requests"].get(a["request_id"])
    if not c or not f or not r:
        return True
    if (
        c["version"] != a["capacity_version_at_proposal"]
        or f["version"] != a["facility_version_at_proposal"]
        or not fresh(c)
        or not compatible(r, f, c["date"])
    ):
        return True
    return not any(
        option["capacity_id"] == a["capacity_id"]
        for option in recommendations(s, r, allow_attempt=a["id"])["candidates"]
    )


def expire(s, include_proposals=True):
    from .planning import cancel_plan

    for p in s["plans"].values():
        if (
            p["status"] in ["APPROVED", "ACTIVE"]
            and p["assignments"]
            and max(a["date"] for a in p["assignments"])
            < now().astimezone(ZoneInfo("Asia/Karachi")).date().isoformat()
        ):
            cancel_plan(s, {"id": "system", "role": "planner"}, p["id"], "Dated plan resources expired")
    for a in s["referrals"].values():
        if include_proposals and a["status"] == "PROPOSED" and proposal_is_stale(s, a):
            release(s, a, "EXPIRED", STALE_PROPOSAL_REASON, {"id": "system"})
        if a["status"] == "AWAITING_CONFIRMATIONS" and datetime.fromisoformat(a["expires_at"]) <= now():
            release(s, a, "EXPIRED", "Response deadline elapsed", {"id": "system"})


def propose(s, u, data):
    r = get(s, "requests", data["request_id"])
    operator(u, r["source_facility_id"])
    require(
        not r.get("blocked_reasons"),
        "PATIENT_DECLINED",
        "Record a new agreement through reprocessing before retrying",
    )
    require(
        not active_attempt(s, r["id"]), "CAPACITY_CONFLICT", "This request already has an active referral attempt"
    )
    option = next(
        (x for x in recommendations(s, r)["candidates"] if x["capacity_id"] == data["capacity_id"]), None
    )
    require(option, "CAPACITY_CONFLICT", "The selected resource is no longer eligible; refresh recommendations")
    require(
        option["capacity_version"] == data["capacity_version"],
        "STALE_INPUT",
        "Quota changed; refresh recommendations",
    )
    require(
        option["facility_version"] == data["facility_version"],
        "STALE_INPUT",
        "Participation or service eligibility changed",
    )
    a = add(
        s,
        "referrals",
        {
            "request_id": r["id"],
            "facility_id": option["facility_id"],
            "capacity_id": option["capacity_id"],
            "date": option["date"],
            "status": "PROPOSED",
            "partner_accepted": False,
            "patient_agreed": False,
            "funding_approved": not option["subsidy"],
            "subsidy": option["subsidy"],
            "package_funded": option["package_funded"],
            "ledger_id": None,
            "plan_id": option["plan_id"],
            "created_at": stamp(),
            "version": 1,
            "policy_version": s["policy_version"],
            "ranking_policy_version": option["ranking_policy_version"],
            "capacity_version_at_proposal": option["capacity_version"],
            "facility_version_at_proposal": option["facility_version"],
            "proposed_by": u["id"],
        },
    )
    r["status"] = "OPEN"
    r["reasons"] = ["REFERRAL_PROPOSED"]
    r["version"] += 1
    audit(s, u, "REFERRAL_PROPOSED", a["id"], after=deepcopy(a))
    return a


def reserve(s, u, data, attempt=None):
    r = get(s, "requests", data["request_id"])
    operator(u, r["source_facility_id"])
    require(
        not r.get("blocked_reasons"),
        "PATIENT_DECLINED",
        "Record a new agreement through reprocessing before retrying",
    )
    active = active_attempt(s, r["id"])
    require(
        not active or (attempt and active["id"] == attempt["id"]),
        "CAPACITY_CONFLICT",
        "This request already has an active reservation",
    )
    options = recommendations(s, r, allow_attempt=attempt["id"] if attempt else None)["candidates"]
    option = next((x for x in options if x["capacity_id"] == data["capacity_id"]), None)
    require(
        option, "CAPACITY_CONFLICT", "The selected resource is no longer eligible; refresh recommendations"
    )
    c = s["capacities"][option["capacity_id"]]
    require(c["version"] == data["capacity_version"], "STALE_INPUT", "Quota changed; refresh recommendations")
    f = s["facilities"][c["facility_id"]]
    require(
        f["version"] == data["facility_version"],
        "STALE_INPUT",
        "Participation or service eligibility changed",
    )
    if attempt:
        a = attempt
        a.update(
            status="AWAITING_CONFIRMATIONS",
            expires_at=(now() + timedelta(minutes=get_settings().referral_hold_minutes)).isoformat(),
            subsidy=option["subsidy"],
            package_funded=option["package_funded"],
            funding_approved=not option["subsidy"],
            plan_id=option["plan_id"],
            capacity_version_at_hold=c["version"],
            facility_version_at_hold=f["version"],
            version=a["version"] + 1,
        )
    else:
        a = add(
            s,
            "referrals",
            {
                "request_id": r["id"],
                "facility_id": f["id"],
                "capacity_id": c["id"],
                "date": c["date"],
                "status": "AWAITING_CONFIRMATIONS",
                "partner_accepted": False,
                "patient_agreed": False,
                "funding_approved": not option["subsidy"],
                "subsidy": option["subsidy"],
                "package_funded": option["package_funded"],
                "ledger_id": None,
                "plan_id": option["plan_id"],
                "created_at": stamp(),
                "version": 1,
                "expires_at": (now() + timedelta(minutes=get_settings().referral_hold_minutes)).isoformat(),
                "policy_version": s["policy_version"],
                "capacity_version_at_hold": c["version"],
                "facility_version_at_hold": f["version"],
            },
        )
    p, assignment = entitlement(s, r["id"], f["id"], c["date"])
    if a["subsidy"]:
        if assignment and assignment.get("subsidy"):
            pool = get(s, "ledger", p["pool_ledger_id"])
            require(
                pool["state"] == "COMMITTED" and pool["amount"] >= a["subsidy"],
                "BUDGET_EXCEEDED",
                "Plan subsidy pool is unavailable",
            )
            pool["amount"] -= a["subsidy"]
            a["ledger_id"] = ledger(s, c["date"][:7], a["subsidy"], "HELD", a["id"], pool["id"])
            a["funding_approved"] = True
        else:
            a["ledger_id"] = ledger(s, c["date"][:7], a["subsidy"], "HELD", a["id"])
    if assignment:
        assignment["consumed"] = True
        assignment["referral_id"] = a["id"]
    if not (assignment and assignment.get("capacity_held")):
        c["held"] += 1
    if a["package_funded"]:
        c["funding_included_available"] -= 1
    c["version"] += 1
    s["reservations"][a["id"]] = {
        "id": a["id"],
        "attempt_id": a["id"],
        "request_id": r["id"],
        "capacity_id": c["id"],
        "units": 1,
        "state": "HELD",
        "expires_at": a["expires_at"],
    }
    r["status"] = "IN_PROGRESS"
    r["reasons"] = []
    r["version"] += 1
    audit(s, u, "SENDING_APPROVAL", a["id"], after=deepcopy(a))
    return a


def reserve_proposal(s, u, aid):
    a = get(s, "referrals", aid)
    r = get(s, "requests", a["request_id"])
    operator(u, r["source_facility_id"])
    if a["status"] == "EXPIRED" and a.get("reason") == STALE_PROPOSAL_REASON:
        return a
    require(a["status"] == "PROPOSED", "INVALID_TRANSITION", "Referral is not proposed")
    return reserve(
        s,
        u,
        {
            "request_id": r["id"],
            "capacity_id": a["capacity_id"],
            "capacity_version": a["capacity_version_at_proposal"],
            "facility_version": a["facility_version_at_proposal"],
        },
        attempt=a,
    )


def confirm_if_ready(s, a):
    if not all(a[k] for k in ["partner_accepted", "patient_agreed", "funding_approved"]):
        return
    c = get(s, "capacities", a["capacity_id"])
    f = get(s, "facilities", a["facility_id"])
    r = get(s, "requests", a["request_id"])
    require(
        fresh(c) and compatible(r, f, c["date"]),
        "STALE_INPUT",
        "Refresh capacity and confirm current partner eligibility first",
    )
    require(s["reservations"][a["id"]]["state"] == "HELD", "CAPACITY_CONFLICT", "Reservation is unavailable")
    c["held"] -= 1
    c["committed"] += 1
    c["version"] += 1
    ledger_state(s, a["ledger_id"], "COMMITTED")
    a["status"] = "CONFIRMED"
    a["confirmed_at"] = stamp()
    s["reservations"][a["id"]]["state"] = "COMMITTED"


def transition(s, u, aid, action, data):
    a = get(s, "referrals", aid)
    r = get(s, "requests", a["request_id"])
    if action in ["partner-response", "arrival", "completion", "no-show"]:
        operator(u, a["facility_id"])
    elif action == "funding-approval":
        planner(u)
    else:
        require(
            u["role"] == "operator"
            and (r["source_facility_id"] in u["facility_ids"] or a["facility_id"] in u["facility_ids"]),
            "ROLE_FORBIDDEN",
            "Sending or receiving facility permission required",
            403,
        )
    before = deepcopy(a)
    if action in ["partner-response", "patient-agreement", "funding-approval"]:
        require(
            a["status"] == "AWAITING_CONFIRMATIONS",
            "INVALID_TRANSITION",
            "Referral is not awaiting confirmations",
        )
        accepted = data["accepted"]
        if not accepted:
            require(bool(data.get("reason")), "REASON_REQUIRED", "Provide the reason", 422)
            release(
                s,
                a,
                "REJECTED" if action == "partner-response" else "CANCELLED",
                "PATIENT_DECLINED" if action == "patient-agreement" else data["reason"],
                u,
            )
            return a
        field = {
            "partner-response": "partner_accepted",
            "patient-agreement": "patient_agreed",
            "funding-approval": "funding_approved",
        }[action]
        a[field] = True
        a[field + "_by"] = u["id"]
        a[field + "_at"] = stamp()
        confirm_if_ready(s, a)
    elif action == "arrival":
        require(a["status"] == "CONFIRMED", "INVALID_TRANSITION", "Only a confirmed referral can arrive")
        require(
            now().astimezone(ZoneInfo("Asia/Karachi")).date().isoformat() <= a["date"],
            "INVALID_TRANSITION",
            "Service date has passed",
        )
        a["status"] = "ARRIVED"
        a["arrived_at"] = stamp()
    elif action == "completion":
        require(a["status"] == "ARRIVED", "INVALID_TRANSITION", "Record arrival before completion")
        c = s["capacities"][a["capacity_id"]]
        c["committed"] -= 1
        c["completed"] += 1
        c["version"] += 1
        ledger_state(s, a["ledger_id"], "SETTLED")
        a.update(status="COMPLETED", completed_at=stamp(), recorded_by=u["id"])
        r["status"] = "FULFILLED"
        s["reservations"][a["id"]]["state"] = "COMPLETED"
    elif action in ["cancel", "no-show"]:
        require(a["status"] in ACTIVE, "INVALID_TRANSITION", "Only an active referral can be closed")
        require(bool(data.get("reason")), "REASON_REQUIRED", "Provide the reason", 422)
        if action == "no-show":
            require(
                a["status"] == "CONFIRMED"
                and now().astimezone(ZoneInfo("Asia/Karachi")).date().isoformat() > a["date"],
                "INVALID_TRANSITION",
                "No-show requires a confirmed referral after its service date",
            )
        release(s, a, "NO_SHOW" if action == "no-show" else "CANCELLED", data["reason"], u)
        return a
    else:
        require(False, "INVALID_TRANSITION", "Unknown action", 422)
    a["version"] += 1
    audit(s, u, action.upper(), aid, before=before, after=deepcopy(a), reason=data.get("reason"))
    return a
