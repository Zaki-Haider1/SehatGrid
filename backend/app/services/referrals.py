"""Legacy referral reservation and transition operations."""

from fastapi import HTTPException
from sqlalchemy import update

from ..models import Capacity, CareRequest, Referral


def require(session, model, object_id):
    obj = session.get(model, object_id)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


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
