"""Serialized aggregate transactions for the small pilot network.

One database row lock protects capacity, funding and offer reservations together.
SQLite uses BEGIN IMMEDIATE; PostgreSQL uses SELECT FOR UPDATE. This deliberately
trades throughput for simple cross-resource atomicity in a 5–10 provider pilot.
The versioned JSON aggregate contains canonical entities, immutable snapshots,
append-only audit events and idempotency receipts. No process-local lock is used.
"""

from contextlib import contextmanager
from copy import deepcopy
from sqlalchemy import JSON, select, text
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class PilotState(Base):
    __tablename__ = "pilot_state"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(default=1)
    payload: Mapped[dict] = mapped_column(JSON)


@contextmanager
def transaction(db):
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    row = db.scalar(select(PilotState).where(PilotState.id == 1).with_for_update())
    if row is None:
        raise RuntimeError("Pilot not initialized. Run python scripts/seed_demo.py.")
    state = deepcopy(row.payload)
    try:
        yield state
        validate_state(state)
        if state != row.payload:
            row.payload = state
            row.version += 1
        db.commit()
    except Exception:
        db.rollback()
        raise


def validate_state(s):
    from collections import Counter
    from .common import ACTIVE, available, budget_view

    for month in s["budgets"]:
        if budget_view(s, month)["remaining"] < 0:
            raise RuntimeError("Budget invariant violated; transaction rolled back")
    counts = Counter(a["request_id"] for a in s["referrals"].values() if a["status"] in ACTIVE)
    if any(n > 1 for n in counts.values()):
        raise RuntimeError("Duplicate active request allocation")
    for c in s["capacities"].values():
        if (
            any(
                not isinstance(c[k], int) or c[k] < 0
                for k in ["quota", "held", "committed", "completed", "forfeited"]
            )
            or available(c) < 0
        ):
            raise RuntimeError("Capacity invariant violated; transaction rolled back")
    for e in s["ledger"].values():
        if (
            not isinstance(e["amount"], int)
            or e["amount"] < 0
            or e["state"] not in ["HELD", "COMMITTED", "SETTLED", "RELEASED"]
        ):
            raise RuntimeError("Ledger invariant violated; transaction rolled back")
    for a in s["referrals"].values():
        if a["status"] in ["CONFIRMED", "ARRIVED", "COMPLETED"] and not all(
            a[k] for k in ["partner_accepted", "patient_agreed", "funding_approved"]
        ):
            raise RuntimeError("Confirmation invariant violated")
