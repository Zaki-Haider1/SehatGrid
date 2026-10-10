"""Legacy plan approval and guarded capacity/funding effects."""

from fastapi import HTTPException
from sqlalchemy import select, update

from ..models import AllocationPlan, Budget, CareRequest
from .capacity import capacity_upsert
from .eligibility import recommendations
from .referrals import require, reserve


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
    # Keep the existing request-before-capacity lock order for competing writes.
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
            # Savepoint lets a race-lost request be skipped without losing the plan.
            try:
                with session.begin_nested():
                    reserve(session, request.id, options[0]["facility_id"])
                reprocessed += 1
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
    return {"plan_id": plan_id, "status": "approved", "cost": plan.cost, "reprocessed": reprocessed}
