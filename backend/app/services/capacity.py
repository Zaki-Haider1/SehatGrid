"""Current dated capacity persistence helpers.

These functions preserve the legacy API behavior. Target freshness and version
rules are documented separately and are not implemented by this module yet.
"""

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..models import Capacity


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
