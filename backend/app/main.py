from contextlib import asynccontextmanager
from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
from collections import Counter
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from rapidfuzz import fuzz
from sqlalchemy import select, update, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .config import get_settings
from .database import SessionLocal, get_db
from .models import Facility, Service, Capacity, CareRequest, Referral, Budget, AllocationPlan
from .schemas import (
    FacilityInput,
    CapacityInput,
    RequestInput,
    ReserveInput,
    BudgetInput,
    PlanInput,
    MatchInput,
    ZONES,
)
from .seed import DemoResetConflict, seed
from .workflows import require, capacity_upsert, recommendations, reserve, transition, optimize, approve

settings = get_settings()


def today():
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def valid_day(day):
    if day < today():
        raise HTTPException(422, "Choose today or a future date")


@asynccontextmanager
async def lifespan(app):
    if settings.seed_on_start:
        with SessionLocal() as session:
            seed(session, today())
    yield


app = FastAPI(
    title="Sehat Grid",
    version="0.1.0",
    lifespan=lifespan,
    description="Synthetic healthcare coordination MVP. No real patient data.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {"today": today(), "zones": ZONES, "demo_reset_enabled": settings.enable_demo_reset}


@app.get("/api/services")
def services(db: Session = Depends(get_db)):
    return db.scalars(select(Service).order_by(Service.id)).all()


@app.post("/api/services/match")
def match(body: MatchInput, db: Session = Depends(get_db)):
    scored = []
    for service in db.scalars(select(Service)):
        terms = [service.name] + service.aliases.split()
        score = max(fuzz.WRatio(body.description.lower().strip(), term.lower()) for term in terms)
        scored.append(
            {"service_id": service.id, "name": service.name, "score": round(score), "requires_review": True}
        )
    return sorted(scored, key=lambda item: -item["score"])[:3]


@app.get("/api/facilities")
def facilities(day: date | None = None, db: Session = Depends(get_db)):
    day = day or today()
    result = []
    for facility in db.scalars(select(Facility).order_by(Facility.id)):
        rows = db.execute(
            select(Capacity, Service)
            .join(Service)
            .where(Capacity.facility_id == facility.id, Capacity.day == day)
            .order_by(Service.id)
        ).all()
        result.append(
            {
                "id": facility.id,
                "name": facility.name,
                "zone": facility.zone,
                "kind": facility.kind,
                "latitude": facility.latitude,
                "longitude": facility.longitude,
                "capacities": [
                    {
                        "service_id": s.id,
                        "service_name": s.name,
                        "total": c.total,
                        "reserved": c.reserved,
                        "consumed": c.consumed,
                        "available": c.total - c.reserved - c.consumed,
                    }
                    for c, s in rows
                ],
            }
        )
    return result


@app.post("/api/facilities", status_code=201)
def register(body: FacilityInput, db: Session = Depends(get_db)):
    existing = db.scalars(select(Facility).where(Facility.zone == body.zone)).all()
    duplicate = [f for f in existing if fuzz.ratio(f.name.lower(), body.name.lower()) >= 92]
    if duplicate:
        raise HTTPException(409, f"Possible duplicate: {duplicate[0].name}. Review the directory first")
    facility = Facility(**body.model_dump())
    db.add(facility)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A facility with this name and zone already exists")
    return facility


@app.put("/api/facilities/{facility_id}/capacity")
def update_capacity(facility_id: int, body: CapacityInput, db: Session = Depends(get_db)):
    valid_day(body.day)
    require(db, Facility, facility_id)
    require(db, Service, body.service_id)
    capacity_upsert(db, facility_id, body.service_id, body.day, body.total)
    db.commit()
    return {"status": "updated"}


def request_rows(db, day=None):
    query = select(CareRequest, Service).join(Service).order_by(CareRequest.id.desc())
    if day:
        query = query.where(CareRequest.day == day)
    rows = []
    for request, service in db.execute(query):
        referral = db.scalar(
            select(Referral).where(Referral.request_id == request.id).order_by(Referral.id.desc()).limit(1)
        )
        provider = None
        if referral:
            capacity = db.get(Capacity, referral.capacity_id)
            provider = db.get(Facility, capacity.facility_id).name
        rows.append(
            {
                "id": request.id,
                "reference": request.reference,
                "service_id": service.id,
                "service_name": service.name,
                "zone": request.zone,
                "day": request.day,
                "priority": request.priority,
                "status": request.status,
                "reason": request.reason,
                "referral_id": referral.id if referral and referral.status != "cancelled" else None,
                "provider": provider if referral and referral.status != "cancelled" else None,
            }
        )
    return rows


@app.get("/api/requests")
def requests(day: date | None = None, db: Session = Depends(get_db)):
    return request_rows(db, day)


@app.post("/api/requests", status_code=201)
def intake(body: RequestInput, db: Session = Depends(get_db)):
    valid_day(body.day)
    require(db, Service, body.service_id)
    request = CareRequest(**body.model_dump(), reference=f"SG-{uuid4().hex[:10].upper()}")
    db.add(request)
    db.flush()
    choices = recommendations(db, request)
    request.reason = "Awaiting provider selection" if choices else "No available capacity"
    db.commit()
    return {"id": request.id, "reference": request.reference, "recommendations": choices}


@app.get("/api/requests/{request_id}/recommendations")
def recommend(request_id: int, db: Session = Depends(get_db)):
    request = require(db, CareRequest, request_id)
    if request.status != "pending":
        raise HTTPException(409, "Recommendations are only available for pending requests")
    return recommendations(db, request)


@app.post("/api/requests/{request_id}/reserve", status_code=201)
def reserve_slot(request_id: int, body: ReserveInput, db: Session = Depends(get_db)):
    valid_day(require(db, CareRequest, request_id).day)
    referral = reserve(db, request_id, body.facility_id)
    db.commit()
    return {"id": referral.id, "status": referral.status}


@app.post("/api/referrals/{referral_id}/{action}")
def referral_action(referral_id: int, action: str, db: Session = Depends(get_db)):
    if action not in ("confirm", "complete", "cancel"):
        raise HTTPException(404, "Unknown referral action")
    result = transition(db, referral_id, action)
    db.commit()
    return result


@app.get("/api/dashboard")
def dashboard(day: date | None = None, db: Session = Depends(get_db)):
    day = day or today()
    caps = db.scalars(select(Capacity).where(Capacity.day == day)).all()
    reqs = db.scalars(select(CareRequest).where(CareRequest.day == day)).all()
    pending = [r for r in reqs if r.status == "pending"]
    groups = Counter((r.zone, r.service_id) for r in pending)
    gaps = []
    for (zone, service_id), count in sorted(groups.items()):
        local = (
            db.execute(
                select(Capacity)
                .join(Facility)
                .where(Facility.zone == zone, Capacity.service_id == service_id, Capacity.day == day)
            )
            .scalars()
            .all()
        )
        free = sum(c.total - c.reserved - c.consumed for c in local)
        gaps.append(
            {
                "zone": zone,
                "service": db.get(Service, service_id).name,
                "pending": count,
                "available": free,
                "reason": "No local provider"
                if not local
                else ("Local capacity exhausted" if free == 0 else "Awaiting referral"),
            }
        )
    budget = require(db, Budget, 1)
    return {
        "day": day,
        "facilities": len(db.scalars(select(Facility)).all()),
        "available": sum(c.total - c.reserved - c.consumed for c in caps),
        "active_referrals": sum(r.status in ("reserved", "confirmed") for r in reqs),
        "completed": sum(r.status == "completed" for r in reqs),
        "pending": len(pending),
        "gaps": gaps,
        "budget": {
            "total": budget.total,
            "committed": budget.committed,
            "remaining": budget.total - budget.committed,
        },
    }


@app.put("/api/budget")
def set_budget(body: BudgetInput, db: Session = Depends(get_db)):
    changed = db.execute(
        update(Budget).where(Budget.id == 1, Budget.committed <= body.total).values(total=body.total)
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "Budget cannot be lower than committed funds")
    db.commit()
    return {"status": "updated"}


@app.get("/api/plans")
def plans(day: date | None = None, db: Session = Depends(get_db)):
    query = select(AllocationPlan).order_by(AllocationPlan.id.desc())
    if day:
        query = query.where(AllocationPlan.day == day)
    return db.scalars(query).all()


@app.post("/api/plans", status_code=201)
def plan(body: PlanInput, db: Session = Depends(get_db)):
    valid_day(body.day)
    result = optimize(db, body.day, body.limit)
    db.commit()
    return result


@app.post("/api/plans/{plan_id}/approve")
def approve_plan(plan_id: int, db: Session = Depends(get_db)):
    valid_day(require(db, AllocationPlan, plan_id).day)
    result = approve(db, plan_id)
    db.commit()
    return result


@app.get("/api/export")
def export(day: date | None = None, db: Session = Depends(get_db)):
    day = day or today()
    return {
        "dashboard": dashboard(day, db),
        "facilities": facilities(day, db),
        "requests": request_rows(db, day),
        "plans": plans(day, db),
    }


@app.post("/api/demo/reset")
def reset(confirm: str = Query(), db: Session = Depends(get_db)):
    if not settings.enable_demo_reset:
        raise HTTPException(403, "Demo reset is disabled on this deployment")
    if confirm != "RESET_SYNTHETIC_DATA":
        raise HTTPException(422, "Explicit reset confirmation is required")
    try:
        seed(db, today(), reset=True)
    except DemoResetConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"status": "reset"}
