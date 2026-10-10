from datetime import date, datetime, timezone

from sqlalchemy import func, select
import pytest

from app import models
from app.seed import DemoResetConflict, load_seed_fixture, seed


DEMO_CLOCK = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


def entity(name):
    assert hasattr(models, name), f"shared schema model {name} is missing"
    return getattr(models, name)


def test_seed_fixture_resolves_outside_repository_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fixture = load_seed_fixture()
    assert fixture["service"]["code"] == "PRIMARY_CARE_OPD"
    assert [row["zone_id"] for row in fixture["zones"]] == ["Central", "East", "South", "West", "North"]


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
    ownership = session.scalar(select(SeedMetadata.metadata_json))["owned_row_ids"]
    assert set(ownership) == {
        "zones", "facilities", "services", "facility_services", "participation_events",
        "capacities", "care_requests", "match_reviews", "offers", "partner_quota_offers",
        "mobile_unit_offers", "subsidy_rules", "monthly_budgets",
    }
    for table, model_name in {
        "zones": "Zone", "facilities": "Facility", "services": "Service",
        "facility_services": "FacilityService", "participation_events": "FacilityParticipationEvent",
        "capacities": "Capacity", "care_requests": "CareRequest", "match_reviews": "MatchReview",
        "offers": "Offer", "partner_quota_offers": "PartnerQuotaOffer",
        "mobile_unit_offers": "MobileUnitOffer", "subsidy_rules": "SubsidyRule",
        "monthly_budgets": "MonthlyBudget",
    }.items():
        model = entity(model_name)
        assert set(ownership[table]) == set(session.scalars(select(model.id)).all())
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == 0
    assert session.scalar(select(func.count()).select_from(AllocationPlan)) == 0
    assert session.scalar(select(func.count()).select_from(Budget)) == 0
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
    assert all(request.service_review_id for request in requests)
    reviews = {review.public_id: review for review in session.scalars(select(entity("MatchReview"))).all()}
    assert all(request.service_review_id in reviews for request in requests)
    assert all(reviews[request.service_review_id].decision == "ACCEPTED" for request in requests)
    assert all(reviews[request.service_review_id].selected_canonical_id == "PRIMARY_CARE_OPD" for request in requests)
    assert {reviews[request.service_review_id].model_id for request in requests} == {"manual-seed-review"}
    assert {reviews[request.service_review_id].reviewed_at.replace(tzinfo=timezone.utc)
            for request in requests} == {DEMO_CLOCK}

    counts = {
        table: session.scalar(select(func.count()).select_from(table))
        for table in (Facility, Service, Capacity, CareRequest, Offer, SeedMetadata)
    }
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    assert counts == {
        table: session.scalar(select(func.count()).select_from(table))
        for table in (Facility, Service, Capacity, CareRequest, Offer, SeedMetadata)
    }


def test_seed_cohorts_match_persisted_capacity_and_offer_facts(empty_session):
    from app.models import Capacity, Facility, FacilityService, MobileUnitOffer, Offer, Service, SubsidyRule

    session = empty_session
    day = date(2026, 10, 10)
    seed(session, day, clock=DEMO_CLOCK)
    requests = session.scalars(select(entity("CareRequest")).where(entity("CareRequest").status == "UNRESOLVED")).all()
    by_cohort = {cohort: [request for request in requests if request.cohort == cohort]
                 for cohort in ("AFFORDABILITY", "QUOTA", "MOBILE")}
    assert {name: len(rows) for name, rows in by_cohort.items()} == {"AFFORDABILITY": 8, "QUOTA": 7, "MOBILE": 5}
    service = session.scalar(select(Service).where(Service.code == "PRIMARY_CARE_OPD"))

    assert {request.zone_id for request in by_cohort["AFFORDABILITY"]} == {"Central"}
    central_capacity = session.scalar(
        select(Capacity).join(Facility).where(Facility.public_id == "FAC-P03", Capacity.day == day)
    )
    central_service = session.scalar(
        select(FacilityService).join(Facility).where(Facility.public_id == "FAC-P03", FacilityService.service_id == service.id)
    )
    subsidy = session.scalar(select(SubsidyRule).where(SubsidyRule.service_id == service.id))
    assert central_service.active and "Central" in central_service.eligible_zone_ids
    assert central_capacity.freshness_status == "CURRENT" and central_capacity.total >= 8
    assert subsidy.amount_per_unit_pkr == 1_000 and "Central" in subsidy.eligible_zone_ids
    assert all(request.funding_eligible and request.funding_required and not request.funding_approved
               for request in by_cohort["AFFORDABILITY"])

    assert {request.zone_id for request in by_cohort["QUOTA"]} == {"West"}
    west_fixed = session.scalars(
        select(FacilityService).join(Facility).where(
            FacilityService.service_id == service.id,
            FacilityService.active.is_(True),
        )
    ).all()
    west_eligible = [row for row in west_fixed if "West" in row.eligible_zone_ids]
    assert len(west_eligible) == 1
    west_provider = session.get(Facility, west_eligible[0].facility_id)
    west_capacity = session.scalar(select(Capacity).where(
        Capacity.facility_id == west_provider.id, Capacity.service_id == service.id, Capacity.day == day,
    ))
    assert west_provider.public_id == "FAC-P07" and west_capacity.total == 0
    quota_offer = session.scalar(select(Offer).where(Offer.offer_type == "PARTNER_QUOTA"))
    quota_link = session.scalar(select(entity("PartnerQuotaOffer")).where(entity("PartnerQuotaOffer").offer_id == quota_offer.id))
    assert quota_link.facility_id == west_provider.id
    assert quota_offer.units == 7 and quota_offer.cost_pkr == 7_000 and quota_offer.funding_included
    assert quota_offer.start_date <= day <= quota_offer.end_date and "West" in quota_offer.eligible_zone_ids

    assert {request.zone_id for request in by_cohort["MOBILE"]} == {"South"}
    assert not any("South" in row.eligible_zone_ids for row in session.scalars(
        select(FacilityService).where(FacilityService.service_id == service.id, FacilityService.active.is_(True))
    ))
    mobile_offer = session.scalar(select(Offer).where(Offer.offer_type == "MOBILE_UNIT"))
    mobile_site = session.scalar(select(MobileUnitOffer).where(MobileUnitOffer.offer_id == mobile_offer.id))
    assert mobile_site.site_zone_id == "South" and mobile_site.service_date == day
    assert mobile_offer.units == 5 and mobile_offer.cost_pkr == 10_000 and mobile_offer.funding_included
    assert mobile_offer.start_date <= day <= mobile_offer.end_date
    assert session.scalar(select(func.count()).select_from(entity("PlanAction"))) == 0


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
    Service = entity("Service")
    CapacityReservation = entity("CapacityReservation")
    shared_service = Service(
        name="Primary care outpatient", display_name="Primary care outpatient",
        code="PRIMARY_CARE_OPD", aliases="primary care outpatient general consultation opd",
        unit_cost=1_000, origin_type="legacy", origin_label="shared catalog",
    )
    session.add(shared_service)
    session.flush()
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    same_label_zone = entity("Zone")(
        zone_id="Extra Synthetic Zone", display_name="Independent synthetic zone",
        latitude=33.7, longitude=73.0, origin_type="synthetic", origin_label="SEHAT GRID demo",
    )
    session.add(same_label_zone)
    session.flush()
    unrelated_facility = Facility(
        name="Unrelated Facility", zone="Legacy", kind="Clinic", latitude=1, longitude=1,
        public_id="FAC-UNRELATED", ownership=None, participation_status="PENDING", origin_type="legacy",
    )
    session.add(unrelated_facility)
    session.flush()
    service_id = session.scalar(select(Service.id))
    unrelated_capacity = Capacity(facility_id=unrelated_facility.id, service_id=service_id,
                                  day=date(2026, 10, 10), total=1, reserved=1, consumed=0)
    unrelated_request = CareRequest(
        public_id="REQ-UNRELATED", reference="REQ-UNRELATED", service_id=service_id,
        zone="Legacy", zone_id="Legacy", day=date(2026, 10, 10), priority="routine", status="reserved",
        origin_type="legacy",
    )
    session.add_all([unrelated_capacity, unrelated_request])
    session.flush()
    session.add(entity("Referral")(request_id=unrelated_request.id, capacity_id=unrelated_capacity.id, status="confirmed"))
    unrelated_budget = MonthlyBudget(month=date(2027, 1, 1), total_pkr=25_000, committed_pkr=5_000, version=1, origin_type="synthetic")
    session.add(unrelated_budget)
    session.commit()
    next_clock = datetime(2026, 10, 11, 9, 0, tzinfo=timezone.utc)
    seed(session, date(2026, 10, 11), clock=next_clock, reset=True)
    demo_ids = {facility.public_id for facility in session.scalars(
        select(Facility).where(Facility.public_id.like("FAC-P%"))
    ) if facility.public_id in {f"FAC-P{i:02}" for i in range(1, 9)}}
    assert demo_ids == {f"FAC-P{i:02}" for i in range(1, 9)}
    assert session.scalar(select(func.count()).select_from(CareRequest).where(CareRequest.status == "UNRESOLVED")) == 20
    capacities = session.scalars(select(Capacity)).all()
    assert len(capacities) == 9
    assert {capacity.day for capacity in capacities if capacity.facility_id != unrelated_facility.id} == {date(2026, 10, 11)}
    assert session.scalar(select(SeedMetadata.seed_clock)).replace(tzinfo=timezone.utc) == next_clock
    assert session.get(MonthlyBudget, unrelated_budget.id) is not None
    assert session.get(MonthlyBudget, unrelated_budget.id).committed_pkr == 5_000
    assert session.get(Facility, unrelated_facility.id) is not None
    assert session.get(entity("Zone"), same_label_zone.id) is not None
    assert session.get(CareRequest, unrelated_request.id) is not None
    assert session.scalar(select(func.count()).select_from(entity("Referral")).where(
        entity("Referral").request_id == unrelated_request.id,
    )) == 1
    assert session.scalar(select(func.count()).select_from(CapacityReservation)) == 0


def test_reset_refuses_older_seed_metadata_without_exact_row_ownership(empty_session):
    from app.models import SeedMetadata
    from app.seed import DemoResetConflict

    session = empty_session
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK)
    metadata = session.scalar(select(SeedMetadata))
    metadata.metadata_json = {
        key: value for key, value in metadata.metadata_json.items() if key != "owned_row_ids"
    }
    session.commit()
    session.expire_all()
    metadata = session.scalar(select(SeedMetadata))
    assert "owned_row_ids" not in metadata.metadata_json
    with pytest.raises(DemoResetConflict, match="ownership manifest"):
        seed(session, date(2026, 10, 11), clock=DEMO_CLOCK, reset=True)
    assert session.scalar(select(func.count()).select_from(entity("Facility"))) == 9
    assert session.scalar(select(func.count()).select_from(entity("CareRequest"))) == 24
    assert session.get(SeedMetadata, metadata.id) is not None


@pytest.mark.parametrize(
    "reference_kind",
    [
        "snapshot_public_request", "snapshot_internal_request",
        "snapshot_public_capacity_version", "snapshot_internal_capacity_version",
        "snapshot_public_offer_version", "snapshot_internal_offer_version",
        "plan_public_request", "plan_internal_request",
        "action_public_request", "action_internal_request",
    ],
)
def test_reset_refuses_persisted_json_references_to_owned_rows(empty_session, reference_kind):
    from app.models import AllocationPlan, Capacity, CareRequest, DemandSnapshot, Offer, PlanAction, SeedMetadata, Service

    session = empty_session
    day = date(2026, 10, 10)
    # Shared catalog rows keep a plan action's ordinary service/zone FKs from masking
    # the JSON dependency under test.
    session.add(Service(
        name="Primary care outpatient", display_name="Primary care outpatient",
        code="PRIMARY_CARE_OPD", aliases="primary care outpatient",
        unit_cost=1_000, origin_type="legacy", origin_label="shared catalog",
    ))
    for zone in load_seed_fixture()["zones"]:
        session.add(entity("Zone")(**zone, origin_type="synthetic", origin_label="shared catalog"))
    session.flush()
    seed(session, day, clock=DEMO_CLOCK, reset=True)
    request = session.scalar(select(CareRequest).where(CareRequest.public_id == "REQ-DEMO-001"))
    capacity = session.scalar(select(Capacity).where(Capacity.facility_id ==
        select(entity("Facility").id).where(entity("Facility").public_id == "FAC-P03").scalar_subquery()))
    offer = session.scalar(select(Offer).where(Offer.public_id == "OFFER-DEMO-QUOTA"))
    assert request is not None and capacity is not None and offer is not None

    snapshot_fields = {"request_ids": [], "capacity_versions": [], "offer_versions": []}
    if reference_kind == "snapshot_public_request":
        snapshot_fields["request_ids"] = ["REQ-DEMO-001"]
    elif reference_kind == "snapshot_internal_request":
        snapshot_fields["request_ids"] = [request.id]
    elif reference_kind == "snapshot_public_capacity_version":
        snapshot_fields["capacity_versions"] = {"FAC-P03:PRIMARY_CARE_OPD:2026-10-12": 1}
    elif reference_kind == "snapshot_internal_capacity_version":
        snapshot_fields["capacity_versions"] = {str(capacity.id): 1}
    elif reference_kind == "snapshot_public_offer_version":
        snapshot_fields["offer_versions"] = {"OFFER-DEMO-QUOTA": 1}
    elif reference_kind == "snapshot_internal_offer_version":
        snapshot_fields["offer_versions"] = {str(offer.id): 1}

    if reference_kind.startswith("snapshot_"):
        row = DemandSnapshot(
            public_id=f"SNAP-{reference_kind}", captured_at=DEMO_CLOCK,
            local_month=day.replace(day=1), service_date_start=day,
            service_date_end=day, input_hash="independent-snapshot",
            cohorts=[], exclusions=[], **snapshot_fields,
        )
    else:
        reference = "REQ-DEMO-001" if "public" in reference_kind else request.id
        plan = AllocationPlan(day=day, cost=0, units=0, allocations=[], status="DRAFT")
        session.add(plan)
        session.flush()
        if reference_kind.startswith("plan_"):
            plan.allocations = [{"request_id": reference}]
            row = plan
        else:
            row = PlanAction(
                public_id=f"ACT-{reference_kind}", plan_id=plan.id,
                action_type="SUBSIDY", service_id=request.service_id,
                zone_id="Central", service_date=day, units=0, cost_pkr=0,
                status="DRAFT", assignments=[{"request_id": reference}],
            )
    session.add(row)
    session.commit()
    row_id, request_id = row.id, request.id
    row_type = type(row)
    session.expire_all()

    with pytest.raises(DemoResetConflict, match="Reset was refused"):
        seed(session, day, clock=DEMO_CLOCK, reset=True)
    session.expire_all()
    assert session.get(row_type, row_id) is not None
    assert session.get(CareRequest, request_id) is not None
    assert session.scalar(select(SeedMetadata.id)) is not None


def test_reset_preserves_snapshot_with_only_unrelated_json_references(empty_session):
    from app.models import DemandSnapshot, SeedMetadata

    session = empty_session
    day = date(2026, 10, 10)
    seed(session, day, clock=DEMO_CLOCK)
    snapshot = DemandSnapshot(
        public_id="SNAP-UNRELATED", captured_at=DEMO_CLOCK,
        local_month=day.replace(day=1), service_date_start=day,
        service_date_end=day, input_hash="independent-snapshot",
        request_ids=["REQ-UNRELATED"], cohorts=[], exclusions=[],
        capacity_versions={"FAC-UNRELATED:OTHER_SERVICE:2026-10-10": 1},
        offer_versions={"OFFER-UNRELATED": 1}, rule_versions=[],
    )
    session.add(snapshot)
    session.commit()
    snapshot_id = snapshot.id
    seed(session, day, clock=DEMO_CLOCK, reset=True)
    session.expire_all()
    assert session.get(DemandSnapshot, snapshot_id) is not None
    assert session.scalar(select(SeedMetadata.id)) is not None


def test_explicit_reset_seeds_demo_even_when_database_has_only_unrelated_rows(empty_session):
    Facility = entity("Facility")
    session = empty_session
    unrelated = Facility(name="Preexisting", zone="Legacy", kind="Clinic", latitude=1, longitude=1,
                         public_id="FAC-PREEXISTING", participation_status="PENDING", origin_type="legacy")
    session.add(unrelated)
    session.commit()
    seed(session, date(2026, 10, 10), clock=DEMO_CLOCK, reset=True)
    assert session.get(Facility, unrelated.id) is not None
    assert session.scalar(select(func.count()).select_from(Facility).where(Facility.public_id.like("FAC-P0%"))) == 8


def test_candidate_mobile_offers_can_overlap_without_activation_semantics(empty_session):
    from app.models import CareRequest, MatchReview, MobileUnitOffer, Offer, Service

    session = empty_session
    day = date(2026, 10, 10)
    service = Service(
        name="Primary care outpatient", display_name="Primary care outpatient",
        code="PRIMARY_CARE_OPD", aliases="primary care outpatient general consultation opd",
        unit_cost=1_000, origin_type="synthetic", origin_label="pre-existing shared service",
        review_status="SYNTHETIC",
    )
    session.add(service)
    session.flush()
    for zone in load_seed_fixture()["zones"]:
        session.add(entity("Zone")(**zone, origin_type="synthetic", origin_label="shared catalog"))
    session.flush()
    seed(session, day, clock=DEMO_CLOCK)
    second_offer = Offer(
        public_id="OFFER-DEMO-MOBILE-ALT", offer_type="MOBILE_UNIT", service_id=service.id,
        start_date=day, end_date=day, units=5, eligible_zone_ids=["West"], cost_pkr=10_000,
        funding_included=True, version=1, valid_from=DEMO_CLOCK,
        valid_to=DEMO_CLOCK + __import__("datetime").timedelta(days=1), origin_type="synthetic",
    )
    session.add(second_offer)
    session.flush()
    session.add(MobileUnitOffer(offer_id=second_offer.id, mobile_unit_id="MOBILE-DEMO-01",
                                site_zone_id="West", service_date=day))
    service_review = MatchReview(
        public_id="MATCH-DEMO-ALT-CANDIDATE", match_kind="SERVICE",
        original_input="alternate candidate", model_id="test-candidate", model_revision="test-v1",
        policy_version="test-only", candidates=[], decision="NEEDS_REVIEW", origin_type="synthetic",
    )
    prefixed_request = CareRequest(
        public_id="REQ-DEMO-ALT-CANDIDATE", reference="SG-ALT-CANDIDATE",
        service_id=service.id, zone="West", zone_id="West", day=day,
        priority="routine", status="pending", origin_type="synthetic",
    )
    session.add_all([service_review, prefixed_request])
    session.commit()
    assert session.scalar(select(func.count()).select_from(MobileUnitOffer).where(
        MobileUnitOffer.mobile_unit_id == "MOBILE-DEMO-01", MobileUnitOffer.service_date == day,
    )) == 2
    seed(session, day, clock=DEMO_CLOCK, reset=True)
    assert session.get(Offer, second_offer.id) is not None
    assert session.get(MatchReview, service_review.id) is not None
    assert session.get(CareRequest, prefixed_request.id) is not None
