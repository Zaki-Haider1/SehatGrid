"""Legacy recommendation query, retained for behavior compatibility.

This is not the target eligibility policy: future eligibility must apply the
reviewed service, scope, zone, freshness, funding, and participation rules in
``docs/api-contracts.md``.
"""

from sqlalchemy import select

from ..models import Capacity, Facility


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
            "facility_id": facility.id,
            "name": facility.name,
            "zone": facility.zone,
            "available": capacity.total - capacity.reserved - capacity.consumed,
            "local": facility.zone == request.zone,
        }
        for capacity, facility in rows
    ]
