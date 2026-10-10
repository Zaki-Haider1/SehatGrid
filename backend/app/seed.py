import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import (
    AuditEvent,
    BudgetLedgerEntry,
    Capacity,
    CapacityReservation,
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
    Referral,
    ReferralAttempt,
    SeedMetadata,
    Service,
    SubsidyRule,
    UserFacility,
    Zone,
)


_REPOSITORY_FIXTURE = Path(__file__).resolve().parents[2] / "data" / "seed" / "primary-care-demo-v1.json"
_PACKAGED_FIXTURE = Path(__file__).resolve().parents[1] / "data" / "seed" / "primary-care-demo-v1.json"
SEED_FIXTURE_PATH = _REPOSITORY_FIXTURE if _REPOSITORY_FIXTURE.is_file() else _PACKAGED_FIXTURE


class DemoResetConflict(Exception):
    """Raised when app activity depends on demo rows selected for reset."""


def load_seed_fixture():
    return json.loads(SEED_FIXTURE_PATH.read_text(encoding="utf-8"))


def _owned_public_ids(fixture):
    request_count = sum(cohort["count"] for cohort in fixture["cohorts"])
    review_ids = [
        "MATCH-DEMO-REVIEW-PRIMARY-CARE-OUTPATIENT",
        "MATCH-DEMO-REVIEW-PRIMARY-CARE",
        "MATCH-DEMO-REVIEW-UNSUPPORTED",
        "MATCH-DEMO-EXAMPLE-CANDIDATE",
        "MATCH-DEMO-EXAMPLE-UNSUPPORTED",
    ]
    return {
        "facilities": [provider["public_id"] for provider in fixture["providers"]]
        + [fixture["unknown_source"]["public_id"]],
        "requests": [f"REQ-DEMO-{index:03}" for index in range(1, request_count + 1)]
        + [f"REQ-EXC-{item['key']}" for item in fixture["exclusions"]],
        "match_reviews": review_ids,
        "offers": [f"OFFER-DEMO-{name.upper()}" for name in fixture["offers"]],
    }


def reset_seed(session: Session, day, clock, fixture=None):
    """Remove only this fixture's demo rows; preserve legacy and unrelated records."""
    fixture = fixture or load_seed_fixture()
    metadata = session.scalar(select(SeedMetadata).where(SeedMetadata.seed_key == fixture["seed_key"]))
    if metadata is None:
        return False

    provider_ids = [provider["public_id"] for provider in fixture["providers"]]
    owned_public_ids = metadata.metadata_json.get("owned_public_ids") or _owned_public_ids(fixture)
    fixture_facility_ids = owned_public_ids["facilities"]
    facility_ids = select(Facility.id).where(Facility.public_id.in_(fixture_facility_ids))
    request_ids = select(CareRequest.id).where(CareRequest.public_id.in_(owned_public_ids["requests"]))
    capacity_ids = select(Capacity.id).where(Capacity.facility_id.in_(facility_ids))
    offer_ids = select(Offer.id).where(Offer.public_id.in_(owned_public_ids["offers"]))
    budget_id = metadata.metadata_json.get("monthly_budget_id")
    service_id = session.scalar(select(Service.id).where(Service.code == fixture["service"]["code"]))
    subsidy_id = session.scalar(select(SubsidyRule.id).where(SubsidyRule.public_id == "SUBSIDY-DEMO-001"))
    has_activity = any((
        session.scalar(select(Referral.id).where(
            (Referral.request_id.in_(request_ids)) | (Referral.capacity_id.in_(capacity_ids))
        ).limit(1)),
        session.scalar(select(ReferralAttempt.id).where(
            (ReferralAttempt.request_id.in_(request_ids))
            | (ReferralAttempt.capacity_id.in_(capacity_ids))
            | (ReferralAttempt.facility_id.in_(facility_ids))
        ).limit(1)),
        session.scalar(select(CapacityReservation.id).where(
            (CapacityReservation.request_id.in_(request_ids))
            | (CapacityReservation.capacity_id.in_(capacity_ids))
        ).limit(1)),
        session.scalar(select(CareRequest.id).where(
            CareRequest.source_facility_id.in_(facility_ids)
            & CareRequest.id.not_in(request_ids)
        ).limit(1)),
        session.scalar(select(PlanAction.id).where(
            (PlanAction.offer_id.in_(offer_ids))
            | (PlanAction.subsidy_rule_id == subsidy_id)
            | (PlanAction.service_id == service_id)
        ).limit(1)),
        session.scalar(select(BudgetLedgerEntry.id).where(BudgetLedgerEntry.budget_id == budget_id).limit(1))
        if budget_id is not None else None,
        session.scalar(select(UserFacility.id).where(UserFacility.facility_id.in_(facility_ids)).limit(1)),
        session.scalar(select(AuditEvent.id).where(
            AuditEvent.facility_id.in_(facility_ids)
            | AuditEvent.object_id.in_(select(Facility.public_id).where(Facility.id.in_(facility_ids)))
            | AuditEvent.object_id.in_(select(CareRequest.public_id).where(CareRequest.id.in_(request_ids)))
        ).limit(1)),
    ))
    if has_activity:
        raise DemoResetConflict(
            "Reset was refused because persisted referral, reservation, plan, budget, "
            "user-facility, or audit activity references the demo fixture."
        )

    session.execute(delete(MatchReview).where(MatchReview.public_id.in_(owned_public_ids["match_reviews"])))
    session.execute(delete(CareRequest).where(CareRequest.public_id.in_(owned_public_ids["requests"])))
    capacity_ids = select(Capacity.id).where(
        Capacity.origin_type == "synthetic", Capacity.facility_id.in_(facility_ids)
    )
    session.execute(delete(Capacity).where(Capacity.id.in_(capacity_ids)))
    session.execute(delete(FacilityService).where(
        FacilityService.facility_id.in_(select(Facility.id).where(Facility.public_id.in_(provider_ids)))
    ))
    session.execute(delete(FacilityParticipationEvent).where(
        FacilityParticipationEvent.facility_id.in_(select(Facility.id).where(Facility.public_id.in_(provider_ids)))
    ))
    demo_offers = select(Offer.id).where(Offer.public_id.in_(owned_public_ids["offers"]))
    session.execute(delete(MobileUnitOffer).where(MobileUnitOffer.offer_id.in_(demo_offers)))
    session.execute(delete(PartnerQuotaOffer).where(PartnerQuotaOffer.offer_id.in_(demo_offers)))
    session.execute(delete(Offer).where(Offer.public_id.in_(owned_public_ids["offers"])))
    session.execute(delete(SubsidyRule).where(SubsidyRule.public_id == "SUBSIDY-DEMO-001"))
    if budget_id is not None:
        session.execute(delete(MonthlyBudget).where(MonthlyBudget.id == budget_id))
    session.execute(delete(Facility).where(Facility.public_id.in_(provider_ids + [fixture["unknown_source"]["public_id"]])))
    session.execute(delete(Zone).where(Zone.origin_type == "synthetic", Zone.origin_label == "SEHAT GRID demo"))
    session.delete(metadata)
    session.flush()
    return True


def _review_rows(fixture, clock):
    canonical_code = fixture["service"]["code"]
    review_ids = {
        "AFFORDABILITY": "MATCH-DEMO-REVIEW-PRIMARY-CARE-OUTPATIENT",
        "QUOTA": "MATCH-DEMO-REVIEW-PRIMARY-CARE-OUTPATIENT",
        "MOBILE": "MATCH-DEMO-REVIEW-PRIMARY-CARE-OUTPATIENT",
        "UNKNOWN": "MATCH-DEMO-REVIEW-PRIMARY-CARE",
        "SCOPE": "MATCH-DEMO-REVIEW-PRIMARY-CARE",
        "FUNDING": "MATCH-DEMO-REVIEW-PRIMARY-CARE",
        "SERVICE": "MATCH-DEMO-REVIEW-UNSUPPORTED",
    }
    records = [
        MatchReview(
            public_id=public_id, match_kind="SERVICE", original_input=original,
            model_id="manual-seed-review", model_revision=fixture["seed_version"],
            policy_version="manual-review", candidates=[], decision="ACCEPTED",
            selected_canonical_id=canonical_code, reviewer_actor_id="USR-PLANNER-01",
            reviewed_at=clock, origin_type="synthetic",
        )
        for public_id, original in (
            ("MATCH-DEMO-REVIEW-PRIMARY-CARE-OUTPATIENT", "primary care outpatient"),
            ("MATCH-DEMO-REVIEW-PRIMARY-CARE", "primary care"),
        )
    ]
    records.append(MatchReview(
        public_id="MATCH-DEMO-REVIEW-UNSUPPORTED", match_kind="SERVICE",
        original_input="unclassified community request", model_id="manual-seed-review",
        model_revision=fixture["seed_version"], policy_version="manual-review",
        candidates=[], decision="NO_SUPPORTED_MATCH", origin_type="synthetic",
    ))
    # These examples are intentionally separate from the accepted manual seed review.
    records.extend([
        MatchReview(
            public_id="MATCH-DEMO-EXAMPLE-CANDIDATE", match_kind="SERVICE",
            original_input="general checkup", model_id="demo-candidate-example",
            model_revision="example-v1", policy_version="example-only",
            candidates=[{"canonical_id": canonical_code, "score": 0.78, "support": "general checkup"}],
            decision="NEEDS_REVIEW", origin_type="synthetic",
        ),
        MatchReview(
            public_id="MATCH-DEMO-EXAMPLE-UNSUPPORTED", match_kind="SERVICE",
            original_input="specialist procedure", model_id="demo-candidate-example",
            model_revision="example-v1", policy_version="example-only",
            candidates=[], decision="NO_SUPPORTED_MATCH", origin_type="synthetic",
        ),
    ])
    return records, review_ids


def seed(session: Session, day, *, clock=None, reset=False):
    """Seed the versioned synthetic fixture; reset touches only its owned rows."""
    fixture = load_seed_fixture()
    clock = clock or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("seed clock must be timezone-aware")
    clock = clock.astimezone(timezone.utc)
    seeded = session.scalar(select(SeedMetadata.id).where(SeedMetadata.seed_key == fixture["seed_key"]))
    if reset:
        reset_seed(session, day, clock, fixture)
        seeded = None
    if seeded:
        return
    # First-time normal startup does not seed into an existing legacy database.
    # Explicit reset is the opt-in path for adding/rebuilding only the demo rows.
    if not reset and session.scalar(select(Facility.id).limit(1)):
        return

    for row in fixture["zones"]:
        if session.scalar(select(Zone.id).where(Zone.zone_id == row["zone_id"])) is None:
            session.add(Zone(**row, origin_type="synthetic", origin_label="SEHAT GRID demo"))

    service_data = fixture["service"]
    service = session.scalar(select(Service).where(Service.code == service_data["code"]))
    if service is None:
        service = Service(
            name=service_data["name"], display_name=service_data["name"],
            code=service_data["code"], aliases=service_data["aliases"],
            unit_cost=service_data["unit_cost_pkr"], origin_type="synthetic",
            origin_label="SEHAT GRID demo", review_status="SYNTHETIC",
        )
        session.add(service)

    providers = {}
    for row in fixture["providers"]:
        provider = Facility(
            public_id=row["public_id"], name=row["name"], zone=row["zone_id"],
            zone_id=row["zone_id"], kind="Clinic", ownership=row["ownership"],
            latitude=row["latitude"], longitude=row["longitude"],
            participation_status="ACTIVE", participation_version=1,
            origin_type="synthetic", origin_label="SEHAT GRID Islamabad demo",
            review_status="SYNTHETIC",
        )
        session.add(provider)
        providers[row["public_id"]] = (provider, row)

    unknown_data = fixture["unknown_source"]
    unknown = Facility(
        public_id=unknown_data["public_id"], name=unknown_data["name"],
        zone=unknown_data["zone_id"], zone_id=unknown_data["zone_id"], kind="Clinic",
        ownership=unknown_data["ownership"], latitude=unknown_data["latitude"],
        longitude=unknown_data["longitude"], participation_status="PENDING",
        participation_version=1, origin_type="synthetic",
        origin_label="SEHAT Grid exclusion example", review_status="NEEDS_REVIEW",
    )
    session.add(unknown)
    session.flush()

    for public_id, (provider, row) in providers.items():
        session.add(FacilityService(
            facility_id=provider.id, service_id=service.id, active=True,
            eligible_zone_ids=row["eligible_zone_ids"], suitability_restrictions=[],
            review_id=f"SERVICE-REV-{public_id[-2:]}", version=1,
            updated_by="USR-PLANNER-01", updated_at=clock,
        ))
        session.add(FacilityParticipationEvent(
            facility_id=provider.id, status="ACTIVE", version=1,
            actor_id="USR-PLANNER-01", reason="Synthetic demonstration partner",
            occurred_at=clock, origin_type="synthetic",
        ))
        age = row.get("report_age_minutes", 0)
        report_time = clock - timedelta(minutes=age)
        session.add(Capacity(
            facility_id=provider.id, service_id=service.id, day=day,
            total=row["quota"], reserved=0, consumed=0, forfeited_units=0,
            updated_by="USR-PLANNER-01", updated_at=report_time,
            freshness_status="STALE" if age > 60 else "CURRENT", version=1,
            origin_type="synthetic", retrieved_at=report_time, review_status="SYNTHETIC",
        ))

    review_records, review_ids = _review_rows(fixture, clock)
    session.add_all(review_records)
    session.flush()

    request_index = 1
    for cohort in fixture["cohorts"]:
        for _ in range(cohort["count"]):
            source = providers.get(cohort["source_provider_id"], (unknown,))[0]
            input_text = "primary care outpatient"
            session.add(CareRequest(
                public_id=f"REQ-DEMO-{request_index:03}", reference=f"SG-ISLAMABAD-{request_index:03}",
                source_facility_id=source.id, service_id=service.id,
                zone=cohort["zone_id"], zone_id=cohort["zone_id"], day=day,
                priority="routine", status="UNRESOLVED", reason=cohort["reason"],
                created_at=clock, original_service_text=input_text,
                service_review_id=review_ids[cohort["name"]], service_text_review_status="REVIEWED",
                acceptable_service_dates=[day.isoformat()], in_scope_suitability=True,
                patient_agreement_required=True, patient_agreed=False,
                funding_required=cohort["funding_required"], funding_eligible=cohort["funding_eligible"],
                funding_approved=False, unresolved_reason=cohort["reason"],
                unresolved_reasons=[cohort["reason"]], cohort=cohort["name"], origin_type="synthetic",
            ))
            request_index += 1

    for item in fixture["exclusions"]:
        original_text = "unclassified community request" if item["key"] == "SERVICE" else "primary care"
        accepted = item["service_review"] == "ACCEPTED"
        session.add(CareRequest(
            public_id=f"REQ-EXC-{item['key']}", reference=item["reference"],
            source_facility_id=unknown.id, service_id=service.id if accepted else None,
            zone=item["zone_id"], zone_id=item["zone_id"], day=day,
            priority="routine", status="OUT_OF_SCOPE", created_at=clock,
            original_service_text=original_text, service_review_id=review_ids[item["key"]],
            service_text_review_status="REVIEWED" if accepted else "NEEDS_REVIEW",
            acceptable_service_dates=[], in_scope_suitability=False,
            patient_agreement_required=True, patient_agreed=False,
            funding_required=item["key"] == "FUNDING", funding_eligible=False,
            funding_approved=False, unresolved_reason=item["reason"],
            unresolved_reasons=[item["reason"]], cohort=None, origin_type="synthetic",
        ))

    offers_data = fixture["offers"]
    dates_end = day + timedelta(days=30)
    valid_to = clock + timedelta(days=31)
    offers = {}
    for name, definition in offers_data.items():
        offer_type = {"subsidy": "SUBSIDY", "quota": "PARTNER_QUOTA", "mobile": "MOBILE_UNIT"}[name]
        offer = Offer(
            public_id=f"OFFER-DEMO-{name.upper()}", offer_type=offer_type,
            service_id=service.id, start_date=day, end_date=dates_end,
            units=definition["units"], eligible_zone_ids=definition["eligible_zone_ids"],
            cost_pkr=definition["cost_pkr"], funding_included=definition.get("funding_included", False),
            version=1, valid_from=clock, valid_to=valid_to, origin_type="synthetic",
        )
        offers[name] = offer
        session.add(offer)

    subsidy = SubsidyRule(
        public_id="SUBSIDY-DEMO-001", service_id=service.id,
        amount_per_unit_pkr=offers_data["subsidy"]["amount_per_unit_pkr"],
        eligible_zone_ids=offers_data["subsidy"]["eligible_zone_ids"],
        valid_from=day, valid_to=dates_end, version=1, active=True, origin_type="synthetic",
    )
    budget = MonthlyBudget(
        month=day.replace(day=1), total_pkr=fixture["monthly_budget_pkr"],
        committed_pkr=0, version=1, origin_type="synthetic",
    )
    session.add_all([subsidy, budget])
    session.flush()
    quota = offers_data["quota"]
    session.add(PartnerQuotaOffer(
        offer_id=offers["quota"].id, facility_id=providers[quota["facility_id"]][0].id,
        spare_capacity_group_id=quota["spare_capacity_group_id"],
    ))
    mobile = offers_data["mobile"]
    session.add(MobileUnitOffer(
        offer_id=offers["mobile"].id, mobile_unit_id=mobile["mobile_unit_id"],
        site_zone_id=mobile["site_zone_id"], service_date=day,
    ))
    session.add(SeedMetadata(
        seed_key=fixture["seed_key"], seed_version=fixture["seed_version"],
        seed_clock=clock, declared_timezone=fixture["declared_timezone"],
        metadata_json={
            "service_code": service_data["code"],
            "zone_ids": [zone["zone_id"] for zone in fixture["zones"]],
            "unresolved_cohorts": {row["name"]: row["count"] for row in fixture["cohorts"]},
            "budget_pkr": fixture["monthly_budget_pkr"], "monthly_budget_id": budget.id,
            "fixture_path": str(SEED_FIXTURE_PATH.name),
            "owned_public_ids": _owned_public_ids(fixture),
        },
    ))
    session.commit()
