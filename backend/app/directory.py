"""Curated directory facts; never imports capacity, patient or funding data."""

import json
from pathlib import Path
from sqlalchemy import select
from .models import Facility

CATALOG = Path(__file__).parent / "data" / "islamabad_hospitals.json"

# Upgrade only the six original, explicitly synthetic seed records. Preserve IDs
# so existing demonstration referrals, capacities and approved plans still work.
LEGACY_NAMES = [
    "Harbor General Hospital",
    "Central Care Hospital",
    "Eastside Community Clinic",
    "North Diagnostic Center",
    "West Wellness Clinic",
    "Hope Community Center",
]


def load_directory():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def sync_directory(session):
    facilities = []
    for index, record in enumerate(load_directory()):
        facility = session.scalar(select(Facility).where(Facility.source_key == record["source_key"]))
        if facility is None and index < len(LEGACY_NAMES):
            facility = session.scalar(
                select(Facility).where(Facility.name == LEGACY_NAMES[index], Facility.zone == record["zone"])
            )
        if facility is None:
            facility = session.scalar(
                select(Facility).where(Facility.name == record["name"], Facility.zone == record["zone"])
            )
        if facility is None:
            facility = Facility()
            session.add(facility)
        for field in ("source_key", "name", "zone", "latitude", "longitude", "profile"):
            setattr(facility, field, record[field])
        facility.kind = "Hospital"
        facilities.append(facility)
    session.flush()
    return facilities
