import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import (
    AllocationPlan,
    AuditEvent,
    BudgetLedgerEntry,
    Capacity,
    CapacityReservation,
    CareRequest,
    DemandSnapshot,
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


_OWNED_ROW_TABLES = {
    "zones", "facilities", "services", "facility_services", "participation_events",
    "capacities", "care_requests", "match_reviews", "offers", "partner_quota_offers",
    "mobile_unit_offers", "subsidy_rules", "monthly_budgets",
}


def _json_references_owned(value, references):
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in references and _json_references_owned(nested, {"value": references[key]}):
                return True
            if _json_references_owned(nested, references):
                return True
    elif isinstance(value, list):
        return any(_json_references_owned(item, references) for item in value)
    elif "value" in references and str(value) in references["value"]:
        return True
    return False


def load_seed_fixture():
    return json.loads(SEED_FIXTURE_PATH.read_text(encoding="utf-8"))


def reset_seed(session: Session, day, clock, fixture=None):
    """Remove only this fixture's demo rows; preserve legacy and unrelated records."""
    fixture = fixture or load_seed_fixture()
    metadata = session.scalar(select(SeedMetadata).where(SeedMetadata.seed_key == fixture["seed_key"]))
    if metadata is None:
        return False

    owned = metadata.metadata_json.get("owned_row_ids")
    if not isinstance(owned, dict) or not _OWNED_ROW_TABLES.issubset(owned):
        raise DemoResetConflict("Reset was refused because this seed has no complete row ownership manifest.")

    for table in _OWNED_ROW_TABLES:
        if not isinstance(owned[table], list):
            raise DemoResetConflict("Reset was refused because this seed has an invalid row ownership manifest.")

    facility_ids = owned["facilities"]
    service_ids = owned["services"]
    facility_service_ids = owned["facility_services"]
    participation_ids = owned["participation_events"]
    capacity_ids = owned["capacities"]
    request_ids = owned["care_requests"]
    review_ids = owned["match_reviews"]
    offer_ids = owned["offers"]
    partner_quota_ids = owned["partner_quota_offers"]
    mobile_offer_ids = owned["mobile_unit_offers"]
    subsidy_ids = owned["subsidy_rules"]
    budget_ids = owned["monthly_budgets"]
    zone_ids = owned["zones"]
    zone_keys = session.scalars(select(Zone.zone_id).where(Zone.id.in_(zone_ids))).all()
    review_public_ids = session.scalars(select(MatchReview.public_id).where(MatchReview.id.in_(review_ids))).all()

    def exists(model, *criteria):
        return session.scalar(select(model.id).where(*criteria).limit(1)) is not None

    # Any non-owned row depending on a row selected for deletion makes reset unsafe.
    has_external_dependency = any((
        exists(Capacity, Capacity.facility_id.in_(facility_ids) | Capacity.service_id.in_(service_ids), Capacity.id.not_in(capacity_ids)),
        exists(FacilityService, (FacilityService.facility_id.in_(facility_ids) | FacilityService.service_id.in_(service_ids)), FacilityService.id.not_in(facility_service_ids)),
        exists(FacilityParticipationEvent, FacilityParticipationEvent.facility_id.in_(facility_ids), FacilityParticipationEvent.id.not_in(participation_ids)),
        exists(CareRequest, (CareRequest.source_facility_id.in_(facility_ids) | CareRequest.service_id.in_(service_ids) | CareRequest.service_review_id.in_(review_public_ids)), CareRequest.id.not_in(request_ids)),
        exists(Referral, Referral.request_id.in_(request_ids) | Referral.capacity_id.in_(capacity_ids)),
        exists(ReferralAttempt, ReferralAttempt.request_id.in_(request_ids) | ReferralAttempt.facility_id.in_(facility_ids) | ReferralAttempt.capacity_id.in_(capacity_ids)),
        exists(CapacityReservation, CapacityReservation.request_id.in_(request_ids) | CapacityReservation.capacity_id.in_(capacity_ids)),
        exists(UserFacility, UserFacility.facility_id.in_(facility_ids)),
        exists(PartnerQuotaOffer, PartnerQuotaOffer.facility_id.in_(facility_ids), PartnerQuotaOffer.id.not_in(partner_quota_ids)),
        exists(AuditEvent, AuditEvent.facility_id.in_(facility_ids)),
        exists(PlanAction, PlanAction.offer_id.in_(offer_ids) | PlanAction.subsidy_rule_id.in_(subsidy_ids) | PlanAction.service_id.in_(service_ids)),
        exists(BudgetLedgerEntry, BudgetLedgerEntry.budget_id.in_(budget_ids)),
        exists(PartnerQuotaOffer, PartnerQuotaOffer.offer_id.in_(offer_ids), PartnerQuotaOffer.id.not_in(partner_quota_ids)),
        exists(MobileUnitOffer, MobileUnitOffer.offer_id.in_(offer_ids), MobileUnitOffer.id.not_in(mobile_offer_ids)),
        exists(Offer, Offer.service_id.in_(service_ids), Offer.id.not_in(offer_ids)),
        exists(SubsidyRule, SubsidyRule.service_id.in_(service_ids), SubsidyRule.id.not_in(subsidy_ids)),
        exists(Facility, (Facility.zone_id.in_(zone_keys) | Facility.zone.in_(zone_keys)), Facility.id.not_in(facility_ids)),
        exists(CareRequest, (CareRequest.zone_id.in_(zone_keys) | CareRequest.zone.in_(zone_keys)), CareRequest.id.not_in(request_ids)),
        exists(PlanAction, PlanAction.zone_id.in_(zone_keys)),
        exists(MobileUnitOffer, MobileUnitOffer.site_zone_id.in_(zone_keys), MobileUnitOffer.id.not_in(mobile_offer_ids)),
    ))
    facility_public_ids = session.scalars(select(Facility.public_id).where(Facility.id.in_(facility_ids))).all()
    request_public_ids = session.scalars(select(CareRequest.public_id).where(CareRequest.id.in_(request_ids))).all()
    service_codes = session.scalars(select(Service.code).where(Service.id.in_(service_ids))).all()
    row_id_references = {
        "facility_id": {str(value) for value in facility_ids},
        "facility_ids": {str(value) for value in facility_ids},
        "request_id": {str(value) for value in request_ids},
        "request_ids": {str(value) for value in request_ids},
        "capacity_id": {str(value) for value in capacity_ids},
        "capacity_ids": {str(value) for value in capacity_ids},
        "service_id": {str(value) for value in service_ids},
        "offer_id": {str(value) for value in offer_ids},
        "subsidy_rule_id": {str(value) for value in subsidy_ids},
        "budget_id": {str(value) for value in budget_ids},
        "zone_id": {str(value) for value in zone_ids} | set(zone_keys),
        "service_review_id": set(review_public_ids),
    }
    nonowned_snapshots = session.scalars(select(DemandSnapshot)).all()
    nonowned_plans = session.scalars(select(AllocationPlan)).all()
    nonowned_actions = session.scalars(select(PlanAction)).all()
    if any(
        _json_references_owned(
            {"request_ids": row.request_ids, "capacity_versions": row.capacity_versions,
             "offer_versions": row.offer_versions, "rule_versions": row.rule_versions,
             "cohorts": row.cohorts, "exclusions": row.exclusions},
            row_id_references,
        )
        for row in nonowned_snapshots
    ) or any(_json_references_owned(row.allocations, row_id_references) for row in nonowned_plans) or any(
        _json_references_owned(row.assignments, row_id_references) for row in nonowned_actions
    ):
        has_external_dependency = True
    if has_external_dependency:
        raise DemoResetConflict(
            "Reset was refused because non-owned provider, service, capacity, scope, "
            "or operational history references the demo fixture."
        )

    public_reference_ids = {
        *(str(row_id) for ids in owned.values() for row_id in ids),
        *(value for value in facility_public_ids + request_public_ids + review_public_ids + service_codes if value),
    }
    if exists(AuditEvent, AuditEvent.object_id.in_(public_reference_ids)):
        raise DemoResetConflict("Reset was refused because audit history references the demo fixture.")

    if any(
        _json_references_owned(row.eligible_zone_ids, {"value": set(zone_keys)})
        for row in session.scalars(select(Offer).where(Offer.id.not_in(offer_ids))).all()
    ) or any(
        _json_references_owned(row.eligible_zone_ids, {"value": set(zone_keys)})
        for row in session.scalars(select(SubsidyRule).where(SubsidyRule.id.not_in(subsidy_ids))).all()
    ) or any(
        _json_references_owned(row.eligible_zone_ids, {"value": set(zone_keys)})
        for row in session.scalars(select(FacilityService).where(FacilityService.id.not_in(facility_service_ids))).all()
    ):
        raise DemoResetConflict("Reset was refused because non-owned scope data references a demo zone.")

    session.execute(delete(MatchReview).where(MatchReview.id.in_(review_ids)))
    session.execute(delete(CareRequest).where(CareRequest.id.in_(request_ids)))
    session.execute(delete(Capacity).where(Capacity.id.in_(capacity_ids)))
    session.execute(delete(FacilityService).where(FacilityService.id.in_(facility_service_ids)))
    session.execute(delete(FacilityParticipationEvent).where(FacilityParticipationEvent.id.in_(participation_ids)))
    session.execute(delete(MobileUnitOffer).where(MobileUnitOffer.id.in_(mobile_offer_ids)))
    session.execute(delete(PartnerQuotaOffer).where(PartnerQuotaOffer.id.in_(partner_quota_ids)))
    session.execute(delete(Offer).where(Offer.id.in_(offer_ids)))
    session.execute(delete(SubsidyRule).where(SubsidyRule.id.in_(subsidy_ids)))
    session.execute(delete(MonthlyBudget).where(MonthlyBudget.id.in_(budget_ids)))
    session.execute(delete(Facility).where(Facility.id.in_(facility_ids)))
    session.execute(delete(Service).where(Service.id.in_(service_ids)))
    session.execute(delete(Zone).where(Zone.id.in_(zone_ids)))
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

    owned_row_ids = {table: [] for table in _OWNED_ROW_TABLES}
    for row in fixture["zones"]:
        zone = session.scalar(select(Zone).where(Zone.zone_id == row["zone_id"]))
        if zone is None:
            zone = Zone(**row, origin_type="synthetic", origin_label="SEHAT GRID demo")
            session.add(zone)
            session.flush()
            owned_row_ids["zones"].append(zone.id)

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
        owns_service = True
    else:
        owns_service = False

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
    owned_row_ids["facilities"] = [provider.id for provider, _ in providers.values()] + [unknown.id]
    if owns_service:
        owned_row_ids["services"].append(service.id)

    service_rows = []
    participation_rows = []
    capacity_rows = []
    for public_id, (provider, row) in providers.items():
        service_row = FacilityService(
            facility_id=provider.id, service_id=service.id, active=True,
            eligible_zone_ids=row["eligible_zone_ids"], suitability_restrictions=[],
            review_id=f"SERVICE-REV-{public_id[-2:]}", version=1,
            updated_by="USR-PLANNER-01", updated_at=clock,
        )
        participation_row = FacilityParticipationEvent(
            facility_id=provider.id, status="ACTIVE", version=1,
            actor_id="USR-PLANNER-01", reason="Synthetic demonstration partner",
            occurred_at=clock, origin_type="synthetic",
        )
        age = row.get("report_age_minutes", 0)
        report_time = clock - timedelta(minutes=age)
        capacity_row = Capacity(
            facility_id=provider.id, service_id=service.id, day=day,
            total=row["quota"], reserved=0, consumed=0, forfeited_units=0,
            updated_by="USR-PLANNER-01", updated_at=report_time,
            freshness_status="STALE" if age > 60 else "CURRENT", version=1,
            origin_type="synthetic", retrieved_at=report_time, review_status="SYNTHETIC",
        )
        service_rows.append(service_row)
        participation_rows.append(participation_row)
        capacity_rows.append(capacity_row)
        session.add_all([service_row, participation_row, capacity_row])
    session.flush()
    owned_row_ids["facility_services"] = [row.id for row in service_rows]
    owned_row_ids["participation_events"] = [row.id for row in participation_rows]
    owned_row_ids["capacities"] = [row.id for row in capacity_rows]

    review_records, review_ids = _review_rows(fixture, clock)
    session.add_all(review_records)
    session.flush()
    owned_row_ids["match_reviews"] = [row.id for row in review_records]

    request_rows = []
    request_index = 1
    for cohort in fixture["cohorts"]:
        for _ in range(cohort["count"]):
            source = providers.get(cohort["source_provider_id"], (unknown,))[0]
            input_text = "primary care outpatient"
            request_rows.append(CareRequest(
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
        request_rows.append(CareRequest(
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
    session.add_all(request_rows)
    session.flush()
    owned_row_ids["care_requests"] = [row.id for row in request_rows]

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
    owned_row_ids["offers"] = [offer.id for offer in offers.values()]
    owned_row_ids["subsidy_rules"] = [subsidy.id]
    owned_row_ids["monthly_budgets"] = [budget.id]
    quota = offers_data["quota"]
    quota_row = PartnerQuotaOffer(
        offer_id=offers["quota"].id, facility_id=providers[quota["facility_id"]][0].id,
        spare_capacity_group_id=quota["spare_capacity_group_id"],
    )
    mobile = offers_data["mobile"]
    mobile_row = MobileUnitOffer(
        offer_id=offers["mobile"].id, mobile_unit_id=mobile["mobile_unit_id"],
        site_zone_id=mobile["site_zone_id"], service_date=day,
    )
    session.add_all([quota_row, mobile_row])
    session.flush()
    owned_row_ids["partner_quota_offers"] = [quota_row.id]
    owned_row_ids["mobile_unit_offers"] = [mobile_row.id]
    session.add(SeedMetadata(
        seed_key=fixture["seed_key"], seed_version=fixture["seed_version"],
        seed_clock=clock, declared_timezone=fixture["declared_timezone"],
        metadata_json={
            "service_code": service_data["code"],
            "zone_ids": [zone["zone_id"] for zone in fixture["zones"]],
            "unresolved_cohorts": {row["name"]: row["count"] for row in fixture["cohorts"]},
            "budget_pkr": fixture["monthly_budget_pkr"], "monthly_budget_id": budget.id,
            "fixture_path": str(SEED_FIXTURE_PATH.name),
            "owned_row_ids": owned_row_ids,
        },
    ))
    session.commit()
