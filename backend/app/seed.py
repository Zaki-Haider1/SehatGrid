from datetime import timedelta
from sqlalchemy import select
from .models import Facility, Service, Capacity, CareRequest, Budget
from .directory import sync_directory


def seed(session, day):
    already_seeded = session.scalar(select(Facility.id).limit(1)) is not None
    facilities = sync_directory(session)
    if already_seeded:
        session.commit()
        return
    services = [
        Service(
            name="General consultation",
            aliases="doctor checkup physician primary care outpatient",
            unit_cost=800,
        ),
        Service(name="Diagnostic imaging", aliases="xray x-ray scan ultrasound radiology", unit_cost=2500),
        Service(name="Lab testing", aliases="blood test pathology laboratory cbc", unit_cost=1200),
        Service(
            name="Maternal care", aliases="pregnancy antenatal prenatal maternity obstetrics", unit_cost=1800
        ),
        Service(name="Dialysis", aliases="kidney renal dialysis", unit_cost=5000),
        Service(
            name="Mental health",
            aliases="counselling counseling psychology therapy psychiatry",
            unit_cost=1500,
        ),
    ]
    session.add_all(services)
    session.flush()
    offers = [
        (0, 0, 8),
        (0, 1, 3),
        (0, 4, 0),
        (1, 0, 12),
        (1, 2, 8),
        (1, 3, 2),
        (2, 0, 5),
        (2, 3, 0),
        (3, 1, 6),
        (3, 2, 10),
        (4, 0, 0),
        (4, 5, 3),
        (5, 0, 6),
        (5, 5, 4),
    ]
    for offset in range(7):
        for fi, si, total in offers:
            session.add(
                Capacity(
                    facility_id=facilities[fi].id,
                    service_id=services[si].id,
                    day=day + timedelta(days=offset),
                    total=total,
                )
            )
    pending = [
        (4, "South", "urgent"),
        (4, "South", "routine"),
        (3, "East", "urgent"),
        (3, "East", "routine"),
        (0, "West", "routine"),
        (0, "West", "urgent"),
    ]
    for index, (si, zone, priority) in enumerate(pending):
        session.add(
            CareRequest(
                reference=f"SG-DEMO-{index + 1:03}",
                service_id=services[si].id,
                zone=zone,
                day=day,
                priority=priority,
                reason="Local capacity exhausted",
            )
        )
    session.add(Budget(id=1, total=50000, committed=0))
    session.commit()
