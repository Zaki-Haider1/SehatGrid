from datetime import timedelta
from pathlib import Path
import json
from sqlalchemy import select
from .auth import password_hash
from .common import SERVICE, capacity_key, now, stamp
from .store import PilotState
from ..config import get_settings


def make_seed():
    config = get_settings()
    day = (
        now().astimezone(__import__("zoneinfo").ZoneInfo("Asia/Karachi")).date() + timedelta(days=1)
    ).isoformat()
    month = day[:7]
    collections = [
        "users",
        "zones",
        "facilities",
        "services",
        "capacities",
        "requests",
        "referrals",
        "reservations",
        "reviews",
        "matches",
        "budgets",
        "ledger",
        "offers",
        "snapshots",
        "plans",
        "audit",
        "receipts",
    ]
    s = {k: {} for k in collections}
    s.update(
        sequences={},
        dataset_version="islamabad-primary-care-v1",
        seed_id="worked-example-8-7-5",
        seeded_at=stamp(),
        service_date=day,
        scope_version="1.0",
        policy_version="same-zone-cost-capacity-id-v1",
        subsidy_rule={"id": "SUBSIDY-1", "service_id": SERVICE, "amount": 1000, "version": 1, "month": month},
    )
    for name, lat, lon in [
        ("Central", 33.702, 73.052),
        ("South", 33.675, 73.066),
        ("East", 33.725, 73.087),
        ("West", 33.684, 73.005),
        ("North", 33.746, 73.03),
    ]:
        s["zones"][name] = {
            "id": name,
            "name": name + " pilot catchment",
            "latitude": lat,
            "longitude": lon,
            "origin_type": "team_derived",
            "note": "Demonstration catchment, not an administrative boundary or travel-access claim",
        }
    s["services"][SERVICE] = {
        "id": SERVICE,
        "name": "General primary-care OPD",
        "in_scope": True,
        "aliases": [
            "primary care",
            "general doctor consultation",
            "general outpatient consultation",
            "family physician visit",
            "routine general medical consultation",
        ],
    }
    directory = json.loads(
        (Path(__file__).resolve().parents[1] / "data/islamabad_hospitals.json").read_text()
    )
    zones = ["South", "Central", "East", "East", "West", "West", "Central", "North"]
    quotas = [8, 0, 4, 60, 3, 0, 2, 0]
    for i, source in enumerate(directory[:8], 1):
        fid = f"P{i:02d}"
        s["facilities"][fid] = {
            "id": fid,
            "name": f"Demo {source['profile']['ownership']} Provider {fid}",
            "original_name": f"Demo Provider {fid}",
            "canonical_id": fid,
            "ownership": source["profile"]["ownership"],
            "address": source["profile"]["address"],
            "zone": zones[i - 1],
            "latitude": source["latitude"],
            "longitude": source["longitude"],
            "participation": "ACTIVE",
            "version": 1,
            "origin_type": "synthetic",
            "eligible_zones": [zones[i - 1]] if i != 8 else [],
            "service_reviewed": True,
            "service_id": SERVICE,
            "subsidy_required": i == 1,
            "directory_context": {
                "name": source["name"],
                "profile": source["profile"],
                "label": "Public directory context — not a confirmed partner",
            },
            "aliases": [fid, f"Demo Provider {fid}"],
        }
        capid = capacity_key(fid, day)
        s["capacities"][capid] = {
            "id": capid,
            "facility_id": fid,
            "service_id": SERVICE,
            "date": day,
            "quota": quotas[i - 1],
            "held": 0,
            "committed": 20 if i == 4 else 0,
            "completed": 20 if i == 4 else 0,
            "forfeited": 0,
            "updated_at": (now() - timedelta(days=3)).isoformat() if i == 5 else stamp(),
            "updated_by": "seed",
            "version": 1,
            "origin_type": "synthetic",
        }
        uid = f"operator-{fid.lower()}"
        s["users"][uid] = {
            "id": uid,
            "name": f"{fid} hospital operator",
            "role": "operator",
            "facility_ids": [fid],
            "active": True,
            "password_hash": password_hash(config.demo_password),
        }
    s["users"]["planner"] = {
        "id": "planner",
        "name": "Network planner",
        "role": "planner",
        "facility_ids": [],
        "active": True,
        "password_hash": password_hash(config.demo_password),
    }

    def request(rid, zone, funding=False, status="UNRESOLVED"):
        return {
            "id": rid,
            "reference": rid,
            "source_facility_id": "P01",
            "zone": zone,
            "original_text": "general doctor consultation",
            "service_id": SERVICE,
            "service_reviewed": True,
            "suitable": True,
            "funding_eligible": True,
            "needs_funding": funding,
            "date_from": day,
            "date_to": day,
            "status": status,
            "reasons": [],
            "created_at": stamp(),
            "version": 1,
            "origin_type": "synthetic",
        }

    for prefix, count, zone, funding in [
        ("A", 8, "South", True),
        ("B", 7, "Central", False),
        ("C", 5, "North", False),
    ]:
        for n in range(1, count + 1):
            rid = f"{prefix}-{n:02d}"
            s["requests"][rid] = request(rid, zone, funding)
    for n in range(1, 41):
        rid = f"ACCOMMODATED-{n:02d}"
        complete = n <= 20
        s["requests"][rid] = request(rid, "East", False, "FULFILLED" if complete else "IN_PROGRESS")
        aid = f"SEEDED-{n:02d}"
        s["referrals"][aid] = {
            "id": aid,
            "request_id": rid,
            "facility_id": "P04",
            "capacity_id": capacity_key("P04", day),
            "date": day,
            "status": "COMPLETED" if complete else "CONFIRMED",
            "partner_accepted": True,
            "patient_agreed": True,
            "funding_approved": True,
            "subsidy": 0,
            "ledger_id": None,
            "plan_id": None,
            "created_at": stamp(),
            "confirmed_at": stamp(),
            "completed_at": stamp() if complete else None,
            "recorded_by": "seed-replay",
            "expires_at": stamp(),
            "version": 1,
        }
        s["reservations"][aid] = {
            "id": aid,
            "attempt_id": aid,
            "request_id": rid,
            "capacity_id": capacity_key("P04", day),
            "units": 1,
            "state": "COMPLETED" if complete else "COMMITTED",
            "expires_at": stamp(),
        }
    # P07 is suspended so it cannot accidentally address the exhausted cohort.
    s["facilities"]["P07"]["participation"] = "SUSPENDED"
    for oid, kind, fid, zone, units, cost in [
        ("QUOTA-7", "QUOTA", "P02", "Central", 7, 7000),
        ("MOBILE-5", "MOBILE", "P08", "North", 5, 10000),
    ]:
        s["offers"][oid] = {
            "id": oid,
            "kind": kind,
            "facility_id": fid,
            "service_id": SERVICE,
            "date": day,
            "eligible_zones": [zone],
            "units": units,
            "cost": cost,
            "funding_included": True,
            "spare_group": "P02-SPARE" if kind == "QUOTA" else None,
            "mobile_unit": "MOBILE-01" if kind == "MOBILE" else None,
            "site": "North pilot site" if kind == "MOBILE" else None,
            "latitude": 33.746 if kind == "MOBILE" else s["facilities"][fid]["latitude"],
            "longitude": 73.03 if kind == "MOBILE" else s["facilities"][fid]["longitude"],
            "status": "AVAILABLE",
            "version": 1,
            "updated_at": stamp(),
            "origin_type": "synthetic",
        }
    s["budgets"][month] = {
        "id": month,
        "month": month,
        "authorized": 25000,
        "version": 1,
        "approval_actor": "seed",
    }
    return s


def seed(db, reset=False):
    row = db.scalar(select(PilotState).where(PilotState.id == 1))
    if row and not reset:
        return
    state = make_seed()
    if row:
        row.payload = state
        row.version += 1
    else:
        db.add(PilotState(id=1, version=1, payload=state))
    db.commit()
