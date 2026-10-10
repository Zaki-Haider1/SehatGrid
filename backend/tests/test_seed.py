from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app import models
from app.seed import seed


DEMO_CLOCK = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


def entity(name):
    assert hasattr(models, name), f"shared schema model {name} is missing"
    return getattr(models, name)


def test_default_seed_is_narrow_and_repeatable(empty_session):
    session = empty_session
    Zone = entity("Zone")
    Facility = entity("Facility")
    Service = entity("Service")
    FacilityService = entity("FacilityService")
    CareRequest = entity("CareRequest")
    Offer = entity("Offer")
    SubsidyRule = entity("SubsidyRule")
    PartnerQuotaOffer = entity("PartnerQuotaOffer")
    MobileUnitOffer = entity("MobileUnitOffer")
    MonthlyBudget = entity("MonthlyBudget")
    SeedMetadata = entity("SeedMetadata")
    AuditEvent = entity("AuditEvent")
    AllocationPlan = entity("AllocationPlan")
    Budget = entity("Budget")
    Capacity = entity("Capacity")

    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    assert session.scalar(select(func.count()).select_from(Zone)) == 5
    facilities = session.scalars(select(Facility).order_by(Facility.public_id)).all()
    providers = [facility for facility in facilities if facility.public_id and facility.public_id.startswith("FAC-P")]
    assert len(providers) == 8
    assert {facility.public_id for facility in providers} == {f"FAC-P{i:02}" for i in range(1, 9)}
    assert {facility.participation_status for facility in providers} == {"ACTIVE"}
    assert session.scalar(select(func.count()).select_from(Service)) == 1
    assert session.scalar(select(Service.code)) == "PRIMARY_CARE_OPD"
    assert session.scalar(select(func.count()).select_from(FacilityService)) == 8
    assert session.scalar(select(func.count()).select_from(CareRequest).where(CareRequest.status == "UNRESOLVED")) == 20
    assert session.scalar(select(func.count()).select_from(Offer)) == 3
    assert session.scalar(select(func.count()).select_from(SubsidyRule)) == 1
    assert session.scalar(select(func.count()).select_from(PartnerQuotaOffer)) == 1
    assert session.scalar(select(func.count()).select_from(MobileUnitOffer)) == 1
    assert session.scalar(select(func.count()).select_from(MonthlyBudget)) == 1
    assert session.scalar(select(MonthlyBudget.total_pkr)) == 25_000
    assert session.scalar(select(func.count()).select_from(SeedMetadata)) == 1
    assert session.scalar(select(SeedMetadata.seed_clock)).replace(tzinfo=timezone.utc) == DEMO_CLOCK
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == 0
    assert session.scalar(select(func.count()).select_from(AllocationPlan)) == 0
    assert session.scalar(select(func.count()).select_from(Budget)) == 1
    assert session.scalar(select(func.count()).select_from(Capacity)) > 0

    requests = session.scalars(select(CareRequest).where(CareRequest.status == "UNRESOLVED")).all()
    cohorts = [request.cohort for request in requests]
    assert {name: cohorts.count(name) for name in set(cohorts)} == {"AFFORDABILITY": 8, "MOBILE": 5, "QUOTA": 7}
    assert all(request.status == "UNRESOLVED" for request in requests)
    service_id = session.scalar(select(Service.id))
    assert all(request.service_id == service_id for request in requests)
    assert all(request.public_id.startswith("REQ-") for request in requests)
    assert all(request.day == date(2026, 10, 10) for request in requests)
    assert all(not request.funding_approved for request in requests)
    affordability = [request for request in requests if request.cohort == "AFFORDABILITY"]
    assert all(request.funding_required and request.funding_eligible for request in affordability)
    assert all(not request.funding_approved for request in affordability)
    assert all(not request.funding_required and not request.funding_eligible for request in requests if request.cohort in {"QUOTA", "MOBILE"})
    assert all(request.status == "UNRESOLVED" and request.unresolved_reason == "AFFORDABILITY_GAP" for request in affordability)
    assert all(request.unresolved_reason == "NO_PARTNER_CAPACITY" for request in requests if request.cohort == "QUOTA")
    assert all(request.unresolved_reason == "NO_MOBILE_SITE_CAPACITY" for request in requests if request.cohort == "MOBILE")
    unsupported = session.scalar(select(CareRequest).where(CareRequest.public_id == "REQ-EXC-SERVICE"))
    assert unsupported.service_id is None
    assert unsupported.status == "OUT_OF_SCOPE"

    offers = session.scalars(select(Offer).order_by(Offer.offer_type)).all()
    assert {(offer.offer_type, offer.units, offer.cost_pkr, offer.funding_included) for offer in offers} == {
        ("SUBSIDY", 8, 8_000, False),
        ("PARTNER_QUOTA", 7, 7_000, True),
        ("MOBILE_UNIT", 5, 10_000, True),
    }

    counts = {
        table: session.scalar(select(func.count()).select_from(table))
        for table in (Facility, Service, Capacity, CareRequest, Offer, SeedMetadata)
    }
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    assert counts == {
        table: session.scalar(select(func.count()).select_from(table))
        for table in (Facility, Service, Capacity, CareRequest, Offer, SeedMetadata)
    }


def test_default_seed_includes_stale_exhausted_and_explicit_exclusions(empty_session):
    session = empty_session
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    Facility = entity("Facility")
    Capacity = entity("Capacity")
    CareRequest = entity("CareRequest")
    facilities = session.scalars(select(Facility)).all()
    assert any(f.origin_type == "synthetic" and f.zone_id == "Unknown" for f in facilities)
    capacities = session.scalars(select(Capacity)).all()
    assert any(capacity.freshness_status == "STALE" for capacity in capacities)
    assert any(capacity.total - capacity.reserved - capacity.consumed - capacity.forfeited_units == 0 for capacity in capacities)
    requests = session.scalars(select(CareRequest)).all()
    assert any(request.status == "OUT_OF_SCOPE" for request in requests)
    assert any(request.zone_id == "Unknown" for request in requests)
    assert any(request.service_text_review_status == "NEEDS_REVIEW" for request in requests)
    assert any(request.unresolved_reason for request in requests)






def test_explicit_seed_reset_rebuilds_only_seed_owned_demo_rows(empty_session):
    session = empty_session
    Facility = entity("Facility")
    Capacity = entity("Capacity")
    CareRequest = entity("CareRequest")
    SeedMetadata = entity("SeedMetadata")
    MonthlyBudget = entity("MonthlyBudget")
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    unrelated_budget = MonthlyBudget(month=date(2027, 1, 1), total_pkr=25_000, committed_pkr=0, version=1, origin_type="synthetic")
    session.add(unrelated_budget)
    session.commit()
    next_clock = datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)
    seed(session, date(2026, 10, 11), clock=next_clock, reset=True)
    assert session.scalar(select(func.count()).select_from(Facility).where(Facility.public_id.like("FAC-P%"))) == 8
    assert session.scalar(select(func.count()).select_from(CareRequest).where(CareRequest.status == "UNRESOLVED")) == 20
    capacities = session.scalars(select(Capacity)).all()
    assert len(capacities) == 8
    assert {capacity.day for capacity in capacities} == {date(2026, 10, 11)}
    assert session.scalar(select(SeedMetadata.seed_clock)).replace(tzinfo=timezone.utc) == next_clock
    assert session.get(MonthlyBudget, unrelated_budget.id) is not None
