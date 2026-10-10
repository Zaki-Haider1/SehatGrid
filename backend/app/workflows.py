from collections import Counter
from fastapi import HTTPException
from ortools.sat.python import cp_model
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from .models import Facility, Service, Capacity, CareRequest, Referral, Budget, AllocationPlan


def require(session, model, object_id):
    obj = session.get(model, object_id)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


def capacity_upsert(session, facility_id, service_id, day, value, additive=False):
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(Capacity).values(
        facility_id=facility_id, service_id=service_id, day=day, total=value, reserved=0, consumed=0
    )
    statement = statement.on_conflict_do_update(
        index_elements=[Capacity.facility_id, Capacity.service_id, Capacity.day],
        set_={"total": Capacity.total + value if additive else value},
        where=True if additive else Capacity.reserved + Capacity.consumed <= value,
    ).returning(Capacity.id)
    if session.scalar(statement) is None:
        raise HTTPException(409, "Capacity cannot be lower than reserved and completed slots")


def recommendations(session, request):
    rows = session.execute(
        select(Capacity, Facility)
        .join(Facility)
        .where(
            Capacity.service_id == request.service_id,
            Capacity.day == request.day,
            Capacity.total > Capacity.reserved + Capacity.consumed,
        )
    ).all()
    rows.sort(
        key=lambda row: (
            row.Facility.zone != request.zone,
            -(row.Capacity.total - row.Capacity.reserved - row.Capacity.consumed),
            row.Facility.id,
        )
    )
    return [
        {
            "facility_id": f.id,
            "name": f.name,
            "zone": f.zone,
            "available": c.total - c.reserved - c.consumed,
            "local": f.zone == request.zone,
        }
        for c, f in rows
    ]


def reserve(session, request_id, facility_id):
    request = require(session, CareRequest, request_id)
    claimed = session.execute(
        update(CareRequest)
        .where(CareRequest.id == request_id, CareRequest.status == "pending")
        .values(status="reserved", reason=None)
    )
    if claimed.rowcount != 1:
        raise HTTPException(409, "This request already has a referral or is closed")
    capacity_id = session.scalar(
        update(Capacity)
        .where(
            Capacity.facility_id == facility_id,
            Capacity.service_id == request.service_id,
            Capacity.day == request.day,
            Capacity.total > Capacity.reserved + Capacity.consumed,
        )
        .values(reserved=Capacity.reserved + 1)
        .returning(Capacity.id)
    )
    if capacity_id is None:
        raise HTTPException(409, "No slot available. Refresh recommendations and try again")
    referral = Referral(request_id=request_id, capacity_id=capacity_id)
    session.add(referral)
    session.flush()
    return referral


def transition(session, referral_id, action):
    referral = require(session, Referral, referral_id)
    allowed = {"confirm": ["reserved"], "complete": ["confirmed"], "cancel": ["reserved", "confirmed"]}
    target = {"confirm": "confirmed", "complete": "completed", "cancel": "cancelled"}[action]
    changed = session.execute(
        update(Referral)
        .where(Referral.id == referral_id, Referral.status.in_(allowed[action]))
        .values(status=target)
    )
    if changed.rowcount != 1:
        raise HTTPException(409, f"Cannot {action} a referral in its current state")
    if action == "complete":
        session.execute(
            update(Capacity)
            .where(Capacity.id == referral.capacity_id)
            .values(reserved=Capacity.reserved - 1, consumed=Capacity.consumed + 1)
        )
    elif action == "cancel":
        session.execute(
            update(Capacity).where(Capacity.id == referral.capacity_id).values(reserved=Capacity.reserved - 1)
        )
    # Cancellation reopens demand and frees the slot; a later referral can serve it.
    session.execute(
        update(CareRequest)
        .where(CareRequest.id == referral.request_id)
        .values(
            status="pending" if action == "cancel" else target,
            reason="Partner cancelled" if action == "cancel" else None,
        )
    )
    return {"id": referral_id, "status": target}


def optimize(session, day, limit):
    budget = require(session, Budget, 1)
    cap = min(limit, budget.total - budget.committed)
    demand = session.scalars(
        select(CareRequest)
        .where(CareRequest.day == day, CareRequest.status == "pending")
        .order_by(CareRequest.created_at)
    ).all()
    counts = Counter((r.zone, r.service_id) for r in demand)
    urgent = Counter((r.zone, r.service_id) for r in demand if r.priority == "urgent")
    candidates = []
    for (zone, service_id), count in sorted(counts.items()):
        offer = session.execute(
            select(Capacity, Facility)
            .join(Facility)
            .where(Facility.zone == zone, Capacity.service_id == service_id, Capacity.day == day)
            .order_by(Facility.id)
        ).first()
        if offer:
            capacity, facility = offer
            # Existing free slots cover demand before funding additional resources.
            available = (
                session.execute(
                    select(Capacity)
                    .join(Facility)
                    .where(Facility.zone == zone, Capacity.service_id == service_id, Capacity.day == day)
                )
                .scalars()
                .all()
            )
            unmet = max(0, count - sum(c.total - c.reserved - c.consumed for c in available))
            if unmet:
                service = require(session, Service, service_id)
                candidates.append(
                    {
                        "facility_id": facility.id,
                        "facility_name": facility.name,
                        "service_id": service_id,
                        "service_name": service.name,
                        "zone": zone,
                        "unit_cost": service.unit_cost,
                        "max_units": unmet,
                        "urgent": min(unmet, urgent[(zone, service_id)]),
                    }
                )
    model = cp_model.CpModel()
    variables = [model.new_int_var(0, c["max_units"], f"units_{i}") for i, c in enumerate(candidates)]
    urgent_vars = [model.new_int_var(0, c["urgent"], f"urgent_{i}") for i, c in enumerate(candidates)]
    for units, priority in zip(variables, urgent_vars):
        model.add(priority <= units)
    cost = sum(v * c["unit_cost"] for v, c in zip(variables, candidates))
    model.add(cost <= cap)
    # Lexicographic objective: urgent demand, total served, then lower cost.
    max_demand = len(demand)
    multiplier = cap + 1
    model.maximize(sum(urgent_vars) * (max_demand + 1) * multiplier + sum(variables) * multiplier - cost)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    solver.parameters.num_search_workers = 1
    result = solver.solve(model)
    if result not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise HTTPException(422, "No feasible allocation could be found")
    allocations = [
        {k: v for k, v in c.items() if k not in ("max_units", "urgent")} | {"units": solver.value(var)}
        for var, c in zip(variables, candidates)
        if solver.value(var) > 0
    ]
    plan = AllocationPlan(
        day=day,
        cost=sum(c["units"] * c["unit_cost"] for c in allocations),
        units=sum(c["units"] for c in allocations),
        allocations=allocations,
    )
    session.add(plan)
    session.flush()
    return plan


def approve(session, plan_id):
    plan = require(session, AllocationPlan, plan_id)
    if plan.units == 0:
        raise HTTPException(409, "This plan contains no allocations")
    changed = session.execute(
        update(AllocationPlan)
        .where(AllocationPlan.id == plan_id, AllocationPlan.status == "draft")
        .values(status="approved")
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "This plan has already been approved")
    changed = session.execute(
        update(Budget)
        .where(Budget.id == 1, Budget.total - Budget.committed >= plan.cost)
        .values(committed=Budget.committed + plan.cost)
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "Budget changed. Create a new plan with the remaining funds")
    # Follow manual reservation's request-before-capacity lock order so a planner
    # and an operator cannot deadlock while competing for the same new slot.
    pending = session.scalars(
        select(CareRequest)
        .where(CareRequest.status == "pending", CareRequest.day == plan.day)
        .order_by(CareRequest.priority.desc(), CareRequest.created_at, CareRequest.id)
        .with_for_update()
    ).all()
    for allocation in plan.allocations:
        capacity_upsert(
            session,
            allocation["facility_id"],
            allocation["service_id"],
            plan.day,
            allocation["units"],
            additive=True,
        )
    reprocessed = 0
    for request in pending:
        options = recommendations(session, request)
        if options:
            # Savepoint allows a race-lost request to be skipped without losing the plan.
            try:
                with session.begin_nested():
                    reserve(session, request.id, options[0]["facility_id"])
                reprocessed += 1
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
    return {"plan_id": plan_id, "status": "approved", "cost": plan.cost, "reprocessed": reprocessed}
