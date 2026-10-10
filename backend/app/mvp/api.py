from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import date
import csv
import io
import json
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import get_db, SessionLocal
from .store import transaction
from .seed import seed
from .common import (
    SERVICE,
    get,
    add,
    require,
    planner,
    operator,
    facility_admin,
    audit,
    stamp,
    local_today,
    cap_view,
    capacity_key,
    budget_view,
    digest,
    available,
)
from .auth import authenticate, issue, password_valid, public_user
from .matching import matcher, review
from .referrals import (
    active_attempt,
    expire,
    recommendations,
    reserve_proposal,
    propose,
    transition,
    refresh_request,
)
from .intelligence import intelligence, snapshot
from .planning import optimize, approve, activate, cancel_plan, reject_action
from .plan_revision import revise, revision_options
from . import schemas

settings = get_settings()


@asynccontextmanager
async def lifespan(app):
    if len(settings.jwt_secret) < 32 or len(settings.demo_password) < 12:
        raise RuntimeError("Set JWT_SECRET (32+ chars) and DEMO_PASSWORD (12+ chars) outside source control.")
    if (
        settings.app_timezone != "Asia/Karachi"
        or settings.capacity_freshness_minutes <= 0
        or settings.referral_hold_minutes <= 0
        or settings.optimizer_time_limit_seconds <= 0
        or not 0 < settings.match_review_threshold <= 1
    ):
        raise RuntimeError("Invalid time, freshness, optimizer or matcher configuration")
    __import__("datetime").time.fromisoformat(settings.cancellation_cutoff_local)
    matcher()  # Fail visibly at startup; never silently replace embeddings with fuzzy matching.
    if settings.seed_on_start:
        with SessionLocal() as db:
            seed(db)
    yield


app = FastAPI(title="SEHAT GRID — scoped primary-care MVP", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "scope_version": "1.0"}


def validate(cls, body):
    try:
        return cls.model_validate(body).model_dump(mode="json")
    except ValidationError as e:
        raise HTTPException(
            422, {"code": "INVALID_INPUT", "message": "; ".join(x["msg"] for x in e.errors())}
        )


def own_requests(s, u):
    if u["role"] in {"planner", "onboarder"}:
        return []
    incoming = {a["request_id"] for a in s["referrals"].values() if a["facility_id"] in u["facility_ids"]}
    return [
        r
        for r in s["requests"].values()
        if r["source_facility_id"] in u["facility_ids"] or r["id"] in incoming
    ]


def view(s, u, month, day):
    summary = intelligence(s, month)
    facilities = []
    for f in s["facilities"].values():
        row = deepcopy(f)
        row["capacities"] = [
            cap_view(s, c)
            for c in s["capacities"].values()
            if c["facility_id"] == f["id"]
            and c["date"] == day
            and (u["role"] == "planner" or f["id"] in u["facility_ids"])
        ]
        facilities.append(row)
    requests = own_requests(s, u)
    ids = {r["id"] for r in requests}
    referrals = [a for a in s["referrals"].values() if u["role"] == "planner" or a["request_id"] in ids]
    plans = (
        list(s["plans"].values())
        if u["role"] == "planner"
        else [
            p
            for p in s["plans"].values()
            if any(s["offers"][a["offer_id"]]["facility_id"] in u["facility_ids"] for a in p["actions"])
        ]
    )
    if u["role"] != "planner":
        plans = deepcopy(plans)
        for p in plans:
            p.pop("original_solver_result", None)
            p.pop("revisions", None)
            p["assignments"] = [a for a in p["assignments"] if a["facility_id"] in u["facility_ids"]]
            p["actions"] = [
                a for a in p["actions"] if s["offers"][a["offer_id"]]["facility_id"] in u["facility_ids"]
            ]
    if u["role"] == "onboarder":
        plans = []
    return {
        "user": public_user(u),
        "config": {
            "today": local_today(),
            "service_date": s["service_date"],
            "month": month,
            "scope_version": s["scope_version"],
            "dataset_version": s["dataset_version"],
            "freshness_minutes": settings.capacity_freshness_minutes,
            "hold_minutes": settings.referral_hold_minutes,
            "cutoff": settings.cancellation_cutoff_local,
            "model": matcher().version,
            "zones": list(s["zones"].values()),
        },
        "facilities": facilities,
        "services": list(s["services"].values()),
        "requests": requests,
        "referrals": referrals,
        "summary": summary if u["role"] == "planner" else None,
        "budgets": [budget_view(s, m) for m in s["budgets"]] if u["role"] == "planner" else [],
        "ledger": list(s["ledger"].values()) if u["role"] == "planner" else [],
        "plans": plans,
        "offers": [
            o for o in s["offers"].values() if u["role"] == "planner" or o["facility_id"] in u["facility_ids"]
        ],
        "reviews": [r for r in s["reviews"].values() if u["role"] == "planner" or r["actor"] == u["id"]],
        "audit": [a for a in s["audit"].values() if u["role"] == "planner" or a["actor"] == u["id"]][-100:],
        "subsidy_rule": s["subsidy_rule"] if u["role"] == "planner" else None,
    }


def mutate(s, u, path, method, body):
    parts = path.split("/")
    if path == "referral-ranking" and method == "PUT":
        planner(u)
        d = validate(schemas.ReferralRankingInput, body)
        current = s["ranking_policy"]
        require(d["version"] == current["version"], "STALE_INPUT", "Refresh referral ranking policy")
        before = deepcopy(current)
        current.update(criteria=d["criteria"], version=current["version"] + 1)
        audit(
            s,
            u,
            "REFERRAL_RANKING_UPDATED",
            "REFERRAL-RANKING",
            before=before,
            after=deepcopy(current),
            reason=d["reason"],
        )
        return {**current, "policy_version": f"referral-ranking-v{current['version']}"}
    if path == "facilities" and method == "POST":
        require(
            u["role"] in {"operator", "onboarder"},
            "ROLE_FORBIDDEN",
            "Hospital setup permission required",
            403,
        )
        d = validate(schemas.FacilityInput, body)
        require(d["zone"] in s["zones"], "INVALID_ZONE", "Choose a pilot zone", 422)
        f = add(
            s,
            "facilities",
            {
                **d,
                "original_name": d["name"],
                "participation": "PENDING",
                "version": 1,
                "origin_type": "synthetic",
                "canonical_id": None,
                "eligible_zones": [],
                "service_reviewed": False,
                "service_id": SERVICE,
                "subsidy_required": False,
                "aliases": [],
                "catalog": [],
            },
        )
        f["canonical_id"] = f["id"]
        u["facility_ids"].append(f["id"])
        audit(s, u, "FACILITY_REGISTERED", f["id"], after=deepcopy(f))
        return f
    if parts[0] == "facilities" and len(parts) >= 2:
        f = get(s, "facilities", parts[1])
        if len(parts) == 2 and method == "PATCH":
            facility_admin(u, f["id"])
            d = validate(schemas.FacilityInput, body)
            require(d["version"] == f["version"], "STALE_INPUT", "Refresh the facility profile")
            require(d["zone"] in s["zones"], "INVALID_ZONE", "Choose a pilot zone", 422)
            before = deepcopy(f)
            f.update(d)
            f["version"] += 1
            audit(s, u, "FACILITY_EDITED", f["id"], before=before, after=deepcopy(f))
            return f
        require(len(parts) >= 3, "NOT_FOUND", "Unknown facility operation", 404)
        if parts[2] == "catalog" and method in {"POST", "PATCH", "DELETE"}:
            require(
                u["role"] == "onboarder" and f["id"] in u["facility_ids"],
                "ROLE_FORBIDDEN",
                "An assigned hospital onboarder must manage the catalog",
                403,
            )
            d = validate(schemas.CatalogInput, body)
            require(d["version"] == f["version"], "STALE_INPUT", "Refresh the hospital catalog")
            before = deepcopy(f.get("catalog", []))
            items = f.setdefault("catalog", [])
            values = {k: v for k, v in d.items() if k != "version"}
            if method == "POST" and len(parts) == 3:
                require(
                    len(items) < 200, "CATALOG_LIMIT", "A hospital catalog supports up to 200 services", 422
                )
                seq = s["sequences"].get("catalog", 0) + 1
                s["sequences"]["catalog"] = seq
                items.append({"id": f"catalog-{seq:04d}", **values})
            else:
                require(len(parts) == 4, "NOT_FOUND", "Choose a catalog service", 404)
                item = next((x for x in items if x["id"] == parts[3]), None)
                require(item is not None, "NOT_FOUND", "Catalog service not found", 404)
                if method == "DELETE":
                    items.remove(item)
                else:
                    item.update(values)
            f["version"] += 1
            audit(s, u, "CATALOG_UPDATED", f["id"], before=before, after=deepcopy(items))
            return f
        if parts[2] == "participation":
            planner(u)
            d = validate(schemas.Participation, body)
            require(d["version"] == f["version"], "STALE_INPUT", "Refresh participation status")
            f["participation"] = d["status"]
            f["version"] += 1
            audit(s, u, "PARTICIPATION", f["id"], after=d["status"], reason=d["reason"])
            return f
        if parts[2] == "services":
            facility_admin(u, f["id"])
            d = validate(schemas.ServiceInput, body)
            require(d["version"] == f["version"], "STALE_INPUT", "Refresh service settings")
            require(
                set(d["eligible_zones"]) <= set(s["zones"]), "INVALID_ZONE", "Use declared pilot zones", 422
            )
            f.update(
                service_id=d["service_id"],
                eligible_zones=d["eligible_zones"],
                service_reviewed=True,
                subsidy_required=d["subsidy_required"],
            )
            f["version"] += 1
            audit(s, u, "SERVICE_REVIEWED", f["id"], after=d)
            return f
        if parts[2] == "capacity" and len(parts) == 5:
            facility_admin(u, f["id"])
            require(parts[3] == SERVICE, "OUT_OF_SCOPE", "Only primary-care OPD is supported", 422)
            try:
                date.fromisoformat(parts[4])
            except ValueError:
                raise HTTPException(422, {"code": "INVALID_DATE", "message": "Use an ISO service date"})
            require(parts[4] >= local_today(), "INVALID_DATE", "Update a current or future service date", 422)
            d = validate(schemas.CapacityInput, body)
            key = capacity_key(f["id"], parts[4])
            c = s["capacities"].get(key)
            require(
                d["version"] == (c["version"] if c else 0),
                "STALE_INPUT",
                "Quota changed; refresh the capacity editor",
            )
            if c:
                require(
                    d["quota"] >= c["quota"] - available(c),
                    "CAPACITY_CONFLICT",
                    "Quota cannot be below held, committed, completed and forfeited units",
                )
            else:
                c = {
                    "id": key,
                    "facility_id": f["id"],
                    "service_id": SERVICE,
                    "date": parts[4],
                    "held": 0,
                    "committed": 0,
                    "completed": 0,
                    "forfeited": 0,
                    "version": 0,
                    "origin_type": "synthetic",
                }
                s["capacities"][key] = c
            before = deepcopy(c)
            c.update(quota=d["quota"], updated_at=stamp(), updated_by=u["id"], version=c["version"] + 1)
            audit(s, u, "CAPACITY_UPDATED", key, before=before, after=deepcopy(c))
            return c
    if path in ["matching/services", "matching/facilities"]:
        d = validate(schemas.MatchInput, body)
        result = matcher().suggest(
            s, "service" if path.endswith("services") else "facility", d["text"], d["zone"], d["ownership"]
        )
        return add(s, "matches", {**result, "actor": u["id"]})
    if path == "matching/reviews":
        return review(s, u, validate(schemas.ReviewInput, body))
    if path == "requests":
        d = validate(schemas.RequestInput, body)
        operator(u, d["source_facility_id"])
        require(
            not any(r["reference"] == d["reference"] for r in s["requests"].values()),
            "DUPLICATE_REQUEST",
            "Synthetic reference already exists",
        )
        require(d["date_from"] >= local_today(), "INVALID_DATE", "Choose a current or future date", 422)
        reviewed = False
        if d["review_id"]:
            rev = get(s, "reviews", d["review_id"])
            require(
                rev["actor"] == u["id"]
                and rev["kind"] == "service"
                and rev["input_text"] == d["original_text"],
                "SERVICE_REVIEW_REQUIRED",
                "Review must belong to this operator and exact service text",
                422,
            )
            reviewed = rev["decision"] != "DECLINE" and rev["candidate_id"] == SERVICE
        r = add(
            s,
            "requests",
            {
                **d,
                "service_id": SERVICE if reviewed else None,
                "service_reviewed": reviewed,
                "status": "OPEN",
                "reasons": [],
                "created_at": stamp(),
                "version": 1,
                "origin_type": "synthetic",
            },
        )
        refresh_request(s, r)
        audit(s, u, "REQUEST_REGISTERED", r["id"], after=deepcopy(r))
        return r
    if parts[0] == "requests" and len(parts) == 3 and parts[2] in ["reprocess", "cancel"]:
        r = get(s, "requests", parts[1])
        operator(u, r["source_facility_id"])
        d = validate(schemas.ReasonInput, body)
        require(
            r["status"] != "FULFILLED" and not active_attempt(s, r["id"]),
            "INVALID_TRANSITION",
            "Close the active referral before changing this request",
        )
        if parts[2] == "cancel":
            r["status"] = "CANCELLED"
        else:
            r["blocked_reasons"] = []
            refresh_request(s, r)
        r["version"] += 1
        audit(s, u, "REQUEST_" + parts[2].upper(), r["id"], reason=d["reason"])
        return r
    if path == "referrals":
        return propose(s, u, validate(schemas.ReferralProposalInput, body))
    if path == "referrals/proposals":
        return propose(s, u, validate(schemas.ReferralProposalInput, body))
    if parts[0] == "referrals" and len(parts) == 3:
        if parts[2] == "reserve":
            validate(schemas.Empty, body)
            return reserve_proposal(s, u, parts[1])
        return transition(
            s,
            u,
            parts[1],
            parts[2],
            validate(
                schemas.ResponseInput
                if parts[2] in ["partner-response", "patient-agreement", "funding-approval"]
                else schemas.ReasonInput
                if parts[2] in ["cancel", "no-show"]
                else schemas.Empty,
                body,
            ),
        )
    if path == "budgets":
        planner(u)
        d = validate(schemas.BudgetInput, body)
        b = s["budgets"].get(d["month"])
        require(d["version"] == (b["version"] if b else 0), "STALE_INPUT", "Refresh the monthly budget")
        if b:
            require(
                d["authorized"] >= b["authorized"] - budget_view(s, d["month"])["remaining"],
                "BUDGET_EXCEEDED",
                "Cannot lower the budget below active expenditure",
            )
        s["budgets"][d["month"]] = {
            "id": d["month"],
            "month": d["month"],
            "authorized": d["authorized"],
            "version": d["version"] + 1,
            "approval_actor": u["id"],
        }
        audit(s, u, "BUDGET_AUTHORIZED", d["month"], after=d)
        return budget_view(s, d["month"])
    if path == "subsidy-rules":
        planner(u)
        d = validate(schemas.SubsidyInput, body)
        require(d["version"] == s["subsidy_rule"]["version"], "STALE_INPUT", "Refresh subsidy policy")
        s["subsidy_rule"] = {**d, "id": "SUBSIDY-1", "service_id": SERVICE, "version": d["version"] + 1}
        audit(s, u, "SUBSIDY_RULE_UPDATED", "SUBSIDY-1", after=d)
        return s["subsidy_rule"]
    if path in ["partner-quota-offers", "mobile-offers"]:
        d = validate(schemas.OfferInput, body)
        operator(u, d["facility_id"])
        require(d["date"] >= local_today(), "INVALID_DATE", "Offer date must be current or future", 422)
        require(set(d["eligible_zones"]) <= set(s["zones"]), "INVALID_ZONE", "Use declared zones", 422)
        kind = "QUOTA" if path == "partner-quota-offers" else "MOBILE"
        require(
            bool(d["spare_group"]) if kind == "QUOTA" else bool(d["mobile_unit"] and d["site"]),
            "INVALID_OFFER",
            "Quota needs a spare-capacity group; mobile needs a unit and site",
            422,
        )
        o = add(
            s,
            "offers",
            {
                **d,
                "kind": kind,
                "service_id": SERVICE,
                "status": "AVAILABLE",
                "version": 1,
                "updated_at": stamp(),
                "origin_type": "synthetic",
            },
        )
        audit(s, u, "OFFER_REGISTERED", o["id"], after=deepcopy(o))
        return o
    if path == "intelligence/snapshots":
        planner(u)
        return snapshot(s, u, validate(schemas.MonthInput, body)["month"])
    if path == "plans/optimize":
        return optimize(s, u, validate(schemas.OptimizeInput, body))
    if parts[0] == "plans" and len(parts) >= 3:
        if len(parts) == 3 and parts[2] == "revise" and method == "POST":
            return revise(s, u, parts[1], validate(schemas.RevisePlanInput, body))
        if parts[2] == "approve":
            return approve(s, u, parts[1], validate(schemas.ApprovePlanInput, body)["version"])
        if parts[2] == "cancel":
            return cancel_plan(s, u, parts[1], validate(schemas.ReasonInput, body)["reason"])
        if len(parts) == 5 and parts[2] == "actions" and parts[4] == "reject":
            return reject_action(s, u, parts[1], parts[3], validate(schemas.ReasonInput, body)["reason"])
        if len(parts) == 5 and parts[2] == "actions" and parts[4] == "activate":
            validate(schemas.Empty, body)
            return activate(s, u, parts[1], parts[3])
    require(False, "NOT_FOUND", "Unknown API operation", 404)


def allocation_export(snap, assignments):
    cohorts = {}
    for a in assignments:
        if a.get("cancelled"):
            continue
        r = next(r for r in snap["requests"] if r["id"] == a["request_id"])
        key = (r["zone"], a["facility_id"], a["date"], a["offer_id"], a["subsidy"])
        cohorts[key] = cohorts.get(key, 0) + 1
    return [
        {
            "zone": k[0],
            "facility_id": k[1],
            "date": k[2],
            "offer_id": k[3],
            "subsidy_per_unit": k[4],
            "units": v,
        }
        for k, v in cohorts.items()
    ]


def decision_export(snap, decision):
    return {
        **{k: decision[k] for k in ("cost", "subsidy_cost", "additional", "unresolved_remaining")},
        "projected": decision.get("projected", decision.get("coverage")),
        "actions": deepcopy(decision["actions"]),
        "allocations": allocation_export(snap, decision["assignments"]),
    }


def export_plan(s, p):
    snap = s["snapshots"][p["snapshot_id"]]
    original = p.get("original_solver_result")
    return {
        "scope_version": "1.0",
        "label": "Synthetic demo data — recorded network requests only",
        "month": p["month"],
        "plan_id": p["id"],
        "snapshot_id": snap["id"],
        "input_hash": p["input_hash"],
        "snapshot_timestamp": snap["timestamp"],
        "dataset_version": s["dataset_version"],
        "model_version": matcher().version,
        "solver": p["solver"],
        "solver_status": p["solver_status"],
        "solver_status_applies_to": "original_solver_result",
        "decision_source": p.get("decision_source", "SOLVER"),
        "version": p["version"],
        "original_solver_result": (
            {
                **decision_export(snap, original),
                "status": original["status"],
                "runtime_seconds": original["runtime_seconds"],
                "baseline": original["baseline"],
            }
            if original
            else None
        ),
        "revisions": [
            {
                **{k: rev[k] for k in ("version", "actor", "timestamp", "reason")},
                "before": decision_export(snap, rev["before"]),
                "after": decision_export(snap, rev["after"]),
            }
            for rev in p.get("revisions", [])
        ],
        "solver_parameters": p["solver_parameters"],
        "status": p["status"],
        "cost": p["cost"],
        "subsidy_cost": p["subsidy_cost"],
        "baseline": p["baseline"],
        "projected": p["projected"],
        "additional": p["additional"],
        "unresolved_remaining": p["unresolved_remaining"],
        "excluded": p["excluded"],
        "assumptions": p["assumptions"],
        "actions": [{k: a[k] for k in ("id", "offer_id", "kind", "cost", "status")} for a in p["actions"]],
        "operational_rules": snap.get("operational_rules", {}),
        "input_resources": {
            "capacities": snap["inputs"]["capacities"],
            "offers": snap["inputs"]["offers"],
            "subsidy_rule": snap["inputs"]["subsidy_rule"],
        },
        "allocations": allocation_export(snap, p["assignments"]),
        "input_versions": {
            "capacities": {k: c["version"] for k, c in snap["inputs"]["capacities"].items()},
            "offers": {k: o["version"] for k, o in snap["inputs"]["offers"].items()},
            "budget": p["budget_version"],
        },
        "policy_version": snap["policy_version"],
        "actual": {
            k: v
            for k, v in intelligence(s, p["month"]).items()
            if k in ["confirmed", "completed", "post_activation_confirmed", "post_activation_completed"]
        },
    }


@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def api(path: str, request: Request, db: Session = Depends(get_db)):
    method = request.method
    try:
        body = await request.json() if method != "GET" else {}
    except (ValueError, TypeError):
        raise HTTPException(422, {"code": "INVALID_INPUT", "message": "Send a valid JSON body"})
    with transaction(db) as s:
        expire(
            s,
            include_proposals=(
                method == "GET"
                or path in {"referrals", "referrals/proposals"}
                or path.endswith("/reserve")
            ),
        )
        if path == "auth/login" and method == "POST":
            d = validate(schemas.Login, body)
            u = s["users"].get(d["username"])
            require(
                u and u["active"] and password_valid(d["password"], u["password_hash"]),
                "UNAUTHENTICATED",
                "Incorrect username or password",
                401,
            )
            return {"token": issue(u), "user": public_user(u)}
        u = authenticate(s, request.headers.get("Authorization", ""))
        month = request.query_params.get("month", s["service_date"][:7])
        day = request.query_params.get("date", s["service_date"])
        validate(schemas.MonthInput, {"month": month})
        try:
            date.fromisoformat(day)
        except ValueError:
            raise HTTPException(422, {"code": "INVALID_DATE", "message": "Use an ISO service date"})
        if method == "GET":
            if path in ["state", "auth/me"]:
                return view(s, u, month, day) if path == "state" else public_user(u)
            if path == "referral-ranking":
                planner(u)
                policy = s["ranking_policy"]
                return {**policy, "policy_version": f"referral-ranking-v{policy['version']}"}
            if path == "services":
                return list(s["services"].values())
            if path.startswith("facilities/") and path.endswith("/services"):
                f = get(s, "facilities", path.split("/")[1])
                return {
                    "service_id": f["service_id"],
                    "reviewed": f["service_reviewed"],
                    "eligible_zones": f["eligible_zones"],
                }
            if path.startswith("intelligence/snapshots/"):
                planner(u)
                return get(s, "snapshots", path.split("/")[-1])
            if path == "requests":
                return own_requests(s, u)
            if path.startswith("requests/") and path.endswith("/recommendations"):
                r = get(s, "requests", path.split("/")[1])
                operator(u, r["source_facility_id"])
                return recommendations(s, r)
            if path in ["intelligence/summary", "intelligence/map"]:
                planner(u)
                return intelligence(s, month)
            if path.startswith("plans/"):
                planner(u)
                p = get(s, "plans", path.split("/")[1])
                if path.endswith("/revision-options"):
                    return revision_options(s, u, p["id"])
                if path.endswith("/export"):
                    output = export_plan(s, p)
                    if request.query_params.get("format") == "csv":
                        stream = io.StringIO()
                        writer = csv.writer(stream)
                        writer.writerow(["section", "data_json"])
                        for key, value in output.items():
                            writer.writerow([key, json.dumps(value, ensure_ascii=False)])
                        return Response(
                            stream.getvalue(),
                            media_type="text/csv",
                            headers={"Content-Disposition": f'attachment; filename="{p["id"]}.csv"'},
                        )
                    return Response(
                        json.dumps(output, indent=2),
                        media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{p["id"]}.json"'},
                    )
                return p
            if path == "facilities":
                return view(s, u, month, day)["facilities"]
            if path in ["budgets", "audit", "partner-quota-offers", "mobile-offers"]:
                v = view(s, u, month, day)
                return v["offers" if path.endswith("offers") else path]
            require(False, "NOT_FOUND", "Unknown API route", 404)
        key = request.headers.get("Idempotency-Key", "")
        require(
            8 <= len(key) <= 160, "IDEMPOTENCY_REQUIRED", "Send a unique Idempotency-Key for each action", 422
        )
        receipt_id = u["id"] + ":" + key
        request_hash = digest({"path": path, "method": method, "body": body})
        receipt = s["receipts"].get(receipt_id)
        if receipt:
            require(
                receipt["hash"] == request_hash,
                "IDEMPOTENCY_CONFLICT",
                "This key was used for a different action",
            )
            return receipt["response"]
        result = mutate(s, u, path, method, body)
        s["receipts"][receipt_id] = {"hash": request_hash, "response": deepcopy(result), "timestamp": stamp()}
        return result
