from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select
from .models import (
    AllocationPlan,
    Budget,
    Capacity,
    CareRequest,
    Facility,
    FacilityParticipationEvent,
    FacilityService,
    MatchReview,
    MobileUnitOffer,
    MonthlyBudget,
    Offer,
    PartnerQuotaOffer,
    PlanAction,
    ReferralAttempt,
    SeedMetadata,
    Service,
    SubsidyRule,
    Zone,
)


def reset_seed(session, day, clock):
    """Rebuild rows owned by this demo seed; unrelated and legacy rows survive."""
    metadata = session.scalar(select(SeedMetadata).where(SeedMetadata.seed_key == "islamabad-primary-care-v1"))
    if metadata is None:
        return False
    session.execute(delete(PlanAction).where(PlanAction.public_id.like("ACTION-DEMO-%")))
    session.execute(delete(AllocationPlan).where(AllocationPlan.public_id.like("PLAN-DEMO-%")))
    session.execute(delete(ReferralAttempt).where(ReferralAttempt.public_id.like("ATTEMPT-DEMO-%")))
    session.execute(delete(MatchReview).where(MatchReview.public_id.like("MATCH-DEMO-%")))
    session.execute(delete(CareRequest).where(
        (CareRequest.public_id.like("REQ-DEMO-%")) | (CareRequest.public_id.like("REQ-EXC-%"))
    ))
    capacity_ids = select(Capacity.id).where(Capacity.origin_type == "synthetic", Capacity.facility_id.in_(
        select(Facility.id).where(Facility.public_id.like("FAC-P%"))
    ))
    session.execute(delete(Capacity).where(Capacity.id.in_(capacity_ids)))
    session.execute(delete(FacilityService).where(FacilityService.facility_id.in_(
        select(Facility.id).where(Facility.public_id.like("FAC-P%"))
    )))
    session.execute(delete(FacilityParticipationEvent).where(FacilityParticipationEvent.facility_id.in_(
        select(Facility.id).where(Facility.public_id.like("FAC-P%"))
    )))
    session.execute(delete(MobileUnitOffer).where(MobileUnitOffer.offer_id.in_(
        select(Offer.id).where(Offer.public_id.like("OFFER-DEMO-%"))
    )))
    session.execute(delete(PartnerQuotaOffer).where(PartnerQuotaOffer.offer_id.in_(
        select(Offer.id).where(Offer.public_id.like("OFFER-DEMO-%"))
    )))
    session.execute(delete(Offer).where(Offer.public_id.like("OFFER-DEMO-%")))
    session.execute(delete(SubsidyRule).where(SubsidyRule.public_id == "SUBSIDY-DEMO-001"))
    seeded_budget_id = metadata.metadata_json.get("monthly_budget_id")
    if seeded_budget_id is not None:
        session.execute(delete(MonthlyBudget).where(MonthlyBudget.id == seeded_budget_id))
    session.execute(delete(Facility).where(
        (Facility.public_id.like("FAC-P%")) | (Facility.public_id == "FAC-EXC-01")
    ))
    session.execute(delete(Service).where(Service.code == "PRIMARY_CARE_OPD"))
    session.execute(delete(Zone).where(Zone.origin_type == "synthetic", Zone.origin_label == "SEHAT GRID demo"))
    session.delete(metadata)
    session.flush()
    return True


def seed(session, day, *, clock=None, reset=False):
    """Seed the narrow synthetic Islamabad demo without altering existing data."""
    clock = clock or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("seed clock must be timezone-aware")
    clock = clock.astimezone(timezone.utc)
    seed_key = "islamabad-primary-care-v1"
    seeded = session.scalar(select(SeedMetadata.id).where(SeedMetadata.seed_key == seed_key))
    if seeded and reset:
        reset_seed(session, day, clock)
        seeded = None
    if session.scalar(select(Facility.id).limit(1)) and not seeded:
        return
    if seeded:
        return

    zone_specs = [
        ("Central", "Islamabad Central", 33.704, 73.055),
        ("East", "Islamabad East", 33.711, 73.081),
        ("South", "Islamabad South", 33.665, 73.085),
        ("West", "Islamabad West", 33.716, 72.990),
        ("North", "Islamabad North", 33.779, 73.062),
    ]
    zones = [
        Zone(zone_id=zone_id, display_name=label, latitude=latitude, longitude=longitude,
             origin_type="synthetic", origin_label="SEHAT GRID demo")
        for zone_id, label, latitude, longitude in zone_specs
    ]
    service = Service(
        name="Primary care outpatient", display_name="Primary care outpatient",
        code="PRIMARY_CARE_OPD", aliases="primary care outpatient general consultation opd",
        unit_cost=1000, origin_type="synthetic", origin_label="SEHAT GRID demo",
        review_status="SYNTHETIC",
    )
    providers = [
        ("Central Public Health Centre", "Central", "PUBLIC", 33.704, 73.055),
        ("Central Family Clinic", "Central", "PRIVATE", 33.699, 73.063),
        ("East Public Dispensary", "East", "PUBLIC", 33.711, 73.081),
        ("East Community Clinic", "East", "PRIVATE", 33.718, 73.089),
        ("South Public Clinic", "South", "PUBLIC", 33.665, 73.085),
        ("South Family Practice", "South", "PRIVATE", 33.658, 73.078),
        ("West Public Health Centre", "West", "PUBLIC", 33.716, 72.990),
        ("North Community Clinic", "North", "PRIVATE", 33.779, 73.062),
    ]
    facilities = [
        Facility(
            public_id=f"FAC-P{index:02}", name=name, zone=zone_id, zone_id=zone_id,
            kind="Clinic", ownership=ownership, latitude=latitude, longitude=longitude,
            participation_status="ACTIVE", participation_version=1, origin_type="synthetic",
            origin_label="SEHAT GRID Islamabad demo", review_status="SYNTHETIC",
        )
        for index, (name, zone_id, ownership, latitude, longitude) in enumerate(providers, 1)
    ]
    unknown = Facility(
        public_id="FAC-EXC-01", name="Unreviewed External Clinic", zone="Unknown", zone_id="Unknown",
        kind="Clinic", ownership="PRIVATE", latitude=33.740, longitude=73.100,
        participation_status="PENDING", participation_version=1, origin_type="synthetic",
        origin_label="SEHAT GRID exclusion example", review_status="NEEDS_REVIEW",
    )
    session.add_all([*zones, service, *facilities, unknown])
    session.flush()
    for facility, (_, zone_id, _, _, _) in zip(facilities, providers):
        session.add(FacilityService(
            facility_id=facility.id, service_id=service.id, active=True,
            eligible_zone_ids=[zone_id], suitability_restrictions=[],
            review_id=f"SERVICE-REV-{facility.public_id[-2:]}", version=1,
            updated_by="USR-PLANNER-01", updated_at=clock,
        ))
        session.add(FacilityParticipationEvent(
            facility_id=facility.id, status="ACTIVE", version=1, actor_id="USR-PLANNER-01",
            reason="Synthetic demonstration partner", occurred_at=clock, origin_type="synthetic",
        ))

    for index, facility in enumerate(facilities):
        is_stale = index == 7
        total = 0 if index == 6 else 8 + (index % 3)
        report_time = clock - timedelta(minutes=61) if is_stale else clock
        session.add(Capacity(
            facility_id=facility.id, service_id=service.id, day=day, total=total,
            reserved=0, consumed=0, forfeited_units=0, updated_by="USR-PLANNER-01", updated_at=report_time,
            freshness_status="STALE" if is_stale else "CURRENT", version=1,
            origin_type="synthetic", retrieved_at=report_time, review_status="SYNTHETIC",
        ))

    cohort_specs = [
        ("AFFORDABILITY", 8, "AFFORDABILITY_GAP", True, True),
        ("QUOTA", 7, "NO_PARTNER_CAPACITY", False, False),
        ("MOBILE", 5, "NO_MOBILE_SITE_CAPACITY", False, False),
    ]
    request_index = 1
    for cohort, count, reason, funding_required, funding_eligible in cohort_specs:
        for offset in range(count):
            zone_id = zone_specs[(offset + request_index) % len(zone_specs)][0]
            source = facilities[(offset + request_index) % len(facilities)]
            session.add(CareRequest(
                public_id=f"REQ-DEMO-{request_index:03}", reference=f"SG-DEMO-{request_index:03}",
                source_facility_id=source.id, service_id=service.id,
                zone=zone_id, zone_id=zone_id,
                day=day, priority="routine", status="UNRESOLVED", reason=reason,
                created_at=clock, original_service_text="primary care outpatient",
                service_review_id=f"MATCH-DEMO-SVC-{request_index:03}",
                service_text_review_status="REVIEWED", acceptable_service_dates=[day.isoformat()],
                in_scope_suitability=True, patient_agreement_required=True, patient_agreed=False,
                funding_required=funding_required, funding_eligible=funding_eligible, funding_approved=False,
                unresolved_reason=reason, unresolved_reasons=[reason], cohort=cohort, origin_type="synthetic",
            ))
            request_index += 1

    # Source and review exclusions stay visible outside the immutable 20-request cohort.
    exclusion_specs = [
        ("REQ-EXC-UNKNOWN", "SG-EXC-UNKNOWN", "Unknown", "OUT_OF_SCOPE", "Unknown zone; review required"),
        ("REQ-EXC-SERVICE", "SG-EXC-SERVICE", "Central", "OUT_OF_SCOPE", "Unsupported service text"),
        ("REQ-EXC-SCOPE", "SG-EXC-SCOPE", "East", "OUT_OF_SCOPE", "Outside demo service scope"),
        ("REQ-EXC-FUNDING", "SG-EXC-FUNDING", "South", "OUT_OF_SCOPE", "Funding not approved"),
    ]
    for public_id, reference, zone_id, status, reason in exclusion_specs:
        session.add(CareRequest(
            public_id=public_id, reference=reference, source_facility_id=unknown.id,
            service_id=None if "SERVICE" in public_id else service.id,
            zone=zone_id, zone_id=zone_id, day=day,
            priority="routine", status=status, created_at=clock,
            original_service_text="unclassified community request" if "SERVICE" in public_id else "primary care",
            service_text_review_status="NEEDS_REVIEW" if "SERVICE" in public_id else "REVIEWED",
            acceptable_service_dates=[], in_scope_suitability=False, patient_agreement_required=True,
            patient_agreed=False, funding_required=True,
            funding_eligible=False, funding_approved=False,
            unresolved_reason=reason, unresolved_reasons=[reason], cohort=None, origin_type="synthetic",
        ))

    service_match = MatchReview(
        public_id="MATCH-DEMO-SVC-001", match_kind="SERVICE", original_input="general checkup",
        model_id="demo-alias", model_revision="1", policy_version="review-v1",
        candidates=[{"canonical_id": "PRIMARY_CARE_OPD", "score": 0.78, "support": "general checkup"}],
        decision="NEEDS_REVIEW", origin_type="synthetic",
    )
    unsupported_match = MatchReview(
        public_id="MATCH-DEMO-SVC-002", match_kind="SERVICE", original_input="specialist procedure",
        model_id="demo-alias", model_revision="1", policy_version="review-v1",
        candidates=[], decision="NO_SUPPORTED_MATCH", origin_type="synthetic",
    )
    valid_from = clock
    valid_to = clock + timedelta(days=31)
    dates_end = day + timedelta(days=30)
    offers = [
        Offer(
            public_id="OFFER-DEMO-SUBSIDY", offer_type="SUBSIDY", service_id=service.id,
            start_date=day, end_date=dates_end, units=8, eligible_zone_ids=[z[0] for z in zone_specs],
            cost_pkr=8_000, funding_included=False, version=1, valid_from=valid_from,
            valid_to=valid_to, origin_type="synthetic",
        ),
        Offer(
            public_id="OFFER-DEMO-QUOTA", offer_type="PARTNER_QUOTA", service_id=service.id,
            start_date=day, end_date=dates_end, units=7, eligible_zone_ids=[z[0] for z in zone_specs],
            cost_pkr=7_000, funding_included=True, version=1, valid_from=valid_from,
            valid_to=valid_to, origin_type="synthetic",
        ),
        Offer(
            public_id="OFFER-DEMO-MOBILE", offer_type="MOBILE_UNIT", service_id=service.id,
            start_date=day, end_date=dates_end, units=5, eligible_zone_ids=[z[0] for z in zone_specs],
            cost_pkr=10_000, funding_included=True, version=1, valid_from=valid_from,
            valid_to=valid_to, origin_type="synthetic",
        ),
    ]
    subsidy = SubsidyRule(
        public_id="SUBSIDY-DEMO-001", service_id=service.id, amount_per_unit_pkr=1_000,
        eligible_zone_ids=[z[0] for z in zone_specs], valid_from=day, valid_to=dates_end,
        version=1, active=True, origin_type="synthetic",
    )
    budget = MonthlyBudget(
        month=day.replace(day=1), total_pkr=25_000, committed_pkr=0, version=1, origin_type="synthetic"
    )
    session.add_all([service_match, unsupported_match, *offers, subsidy, budget])
    session.flush()
    session.add(PartnerQuotaOffer(
        offer_id=offers[1].id, facility_id=facilities[0].id, spare_capacity_group_id="SPARE-GROUP-DEMO-01"
    ))
    session.add(MobileUnitOffer(
        offer_id=offers[2].id, mobile_unit_id="MOBILE-DEMO-01", site_zone_id="South", service_date=day
    ))
    legacy_budget = session.get(Budget, 1)
    if legacy_budget is None:
        session.add(Budget(id=1, total=25_000, committed=0))
    else:
        legacy_budget.total = max(legacy_budget.total, legacy_budget.committed, 25_000)
    session.add(SeedMetadata(
        seed_key=seed_key, seed_version="1", seed_clock=clock, declared_timezone="Asia/Karachi",
        metadata_json={
            "service_code": "PRIMARY_CARE_OPD", "zone_ids": [z[0] for z in zone_specs],
            "unresolved_cohorts": {"AFFORDABILITY": 8, "QUOTA": 7, "MOBILE": 5},
            "budget_pkr": 25_000, "monthly_budget_id": budget.id,
            "offers": {"affordability": {"units": 8, "cost_pkr": 8_000},
                       "quota": {"units": 7, "cost_pkr": 7_000, "funding_included": True},
                       "mobile": {"units": 5, "cost_pkr": 10_000, "funding_included": True}},
        },
    ))
    session.commit()
