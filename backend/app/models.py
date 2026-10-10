from datetime import date, datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    origin_label: Mapped[str] = mapped_column(String(120), default="")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("role IN ('OPERATOR', 'PLANNER')"),)


class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    zone: Mapped[str] = mapped_column(String(50), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[float]
    longitude: Mapped[float]
    source_key: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    public_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    ownership: Mapped[str | None] = mapped_column(String(20), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    participation_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    participation_version: Mapped[int] = mapped_column(Integer, default=1)
    origin_type: Mapped[str] = mapped_column(String(30), default="legacy")
    origin_label: Mapped[str] = mapped_column(String(120), default="")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_status: Mapped[str] = mapped_column(String(24), default="UNREVIEWED")
    __table_args__ = (
        UniqueConstraint("name", "zone"),
        CheckConstraint("ownership IS NULL OR ownership IN ('PUBLIC', 'PRIVATE')", name="ck_facilities_ownership"),
        CheckConstraint("participation_status IN ('PENDING', 'ACTIVE', 'SUSPENDED')", name="ck_facilities_participation_status"),
        CheckConstraint("participation_version >= 1", name="ck_facilities_participation_version"),
    )


class UserFacility(Base):
    __tablename__ = "user_facilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    __table_args__ = (UniqueConstraint("user_id", "facility_id"),)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    aliases: Mapped[str] = mapped_column(String(500))
    unit_cost: Mapped[int]
    code: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="legacy")
    origin_label: Mapped[str] = mapped_column(String(120), default="")
    review_status: Mapped[str] = mapped_column(String(24), default="NEEDS_REVIEW")
    __table_args__ = (CheckConstraint("unit_cost > 0"),)


class FacilityService(Base):
    __tablename__ = "facility_services"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    eligible_zone_ids: Mapped[list] = mapped_column(JSON, default=list)
    suitability_restrictions: Mapped[list] = mapped_column(JSON, default=list)
    review_id: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("facility_id", "service_id"),
        CheckConstraint("version >= 1", name="ck_facility_services_version"),
    )


class FacilityParticipationEvent(Base):
    __tablename__ = "facility_participation_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(String(250), default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'ACTIVE', 'SUSPENDED')"),
        CheckConstraint("version >= 1"),
    )


class Capacity(Base):
    __tablename__ = "capacities"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    day: Mapped[date] = mapped_column(Date, index=True)
    total: Mapped[int]
    reserved: Mapped[int] = mapped_column(default=0)
    consumed: Mapped[int] = mapped_column(default=0)
    forfeited_units: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    freshness_status: Mapped[str] = mapped_column(String(12), default="UNKNOWN")
    version: Mapped[int] = mapped_column(Integer, default=1)
    origin_type: Mapped[str] = mapped_column(String(30), default="legacy")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_status: Mapped[str] = mapped_column(String(24), default="UNREVIEWED")
    __table_args__ = (
        UniqueConstraint("facility_id", "service_id", "day"),
        CheckConstraint("total >= 0 AND reserved >= 0 AND consumed >= 0 AND total >= reserved + consumed", name="ck_capacities_legacy_nonnegative"),
        CheckConstraint("forfeited_units >= 0", name="ck_capacities_forfeited_nonnegative"),
        CheckConstraint("total >= reserved + consumed + forfeited_units", name="ck_capacities_target_available"),
        CheckConstraint("freshness_status IN ('CURRENT', 'STALE', 'UNKNOWN')", name="ck_capacities_freshness_status"),
        CheckConstraint("version >= 1", name="ck_capacities_version"),
    )


class CareRequest(Base):
    __tablename__ = "care_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id"), nullable=True)
    zone: Mapped[str] = mapped_column(String(50), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    public_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    source_facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    original_service_text: Mapped[str] = mapped_column(Text, default="")
    service_review_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service_text_review_status: Mapped[str] = mapped_column(String(24), default="NEEDS_REVIEW")
    acceptable_service_dates: Mapped[list] = mapped_column(JSON, default=list)
    in_scope_suitability: Mapped[bool] = mapped_column(Boolean, default=False)
    patient_agreement_required: Mapped[bool] = mapped_column(Boolean, default=True)
    patient_agreed: Mapped[bool] = mapped_column(Boolean, default=False)
    funding_required: Mapped[bool] = mapped_column(Boolean, default=False)
    funding_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    funding_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    unresolved_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unresolved_reasons: Mapped[list] = mapped_column(JSON, default=list)
    cohort: Mapped[str | None] = mapped_column(String(24), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("priority IN ('routine', 'urgent')"),
        CheckConstraint("status IN ('pending', 'reserved', 'confirmed', 'completed', 'cancelled', 'OPEN', 'IN_PROGRESS', 'UNRESOLVED', 'FULFILLED', 'CANCELLED', 'OUT_OF_SCOPE')"),
    )


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("care_requests.id"), index=True)
    capacity_id: Mapped[int] = mapped_column(ForeignKey("capacities.id"))
    status: Mapped[str] = mapped_column(String(20), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("status IN ('reserved', 'confirmed', 'completed', 'cancelled')"),)


class ReferralAttempt(Base):
    __tablename__ = "referral_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("care_requests.id"), index=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    capacity_id: Mapped[int | None] = mapped_column(ForeignKey("capacities.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("status IN ('PROPOSED', 'AWAITING_CONFIRMATIONS', 'CONFIRMED', 'ARRIVED', 'COMPLETED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'NO_SHOW')"),
        CheckConstraint("version >= 1", name="ck_referral_attempts_version"),
    )


class CapacityReservation(Base):
    __tablename__ = "capacity_reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("care_requests.id"), index=True)
    attempt_id: Mapped[int | None] = mapped_column(ForeignKey("referral_attempts.id"), nullable=True)
    capacity_id: Mapped[int] = mapped_column(ForeignKey("capacities.id"), index=True)
    service_date: Mapped[date] = mapped_column(Date)
    units: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("units > 0"),
        CheckConstraint("state IN ('HELD', 'COMMITTED', 'COMPLETED', 'FORFEITED', 'RELEASED')"),
        CheckConstraint("version >= 1"),
    )


class MatchReview(Base):
    __tablename__ = "match_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    match_kind: Mapped[str] = mapped_column(String(24))
    original_input: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(String(100))
    model_revision: Mapped[str] = mapped_column(String(100))
    policy_version: Mapped[str] = mapped_column(String(80))
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    decision: Mapped[str] = mapped_column(String(24))
    selected_canonical_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewer_actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (CheckConstraint("decision IN ('NEEDS_REVIEW', 'NO_SUPPORTED_MATCH', 'ACCEPTED', 'REJECTED')"),)


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    total: Mapped[int]
    committed: Mapped[int] = mapped_column(default=0)
    __table_args__ = (CheckConstraint("total >= committed AND committed >= 0"),)


class MonthlyBudget(Base):
    __tablename__ = "monthly_budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    month: Mapped[date] = mapped_column(Date, unique=True)
    total_pkr: Mapped[int] = mapped_column(Integer)
    committed_pkr: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("total_pkr >= committed_pkr AND committed_pkr >= 0"),
        CheckConstraint("version >= 1"),
    )


class BudgetLedgerEntry(Base):
    __tablename__ = "budget_ledger_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("monthly_budgets.id"), index=True)
    amount_pkr: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(20))
    transfer_from_id: Mapped[int | None] = mapped_column(ForeignKey("budget_ledger_entries.id"), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    reason: Mapped[str] = mapped_column(String(250), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("amount_pkr >= 0"),
        CheckConstraint("state IN ('HELD', 'COMMITTED', 'SETTLED', 'RELEASED')"),
        CheckConstraint("transfer_from_id IS NULL OR transfer_from_id != id"),
    )


class SubsidyRule(Base):
    __tablename__ = "subsidy_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    amount_per_unit_pkr: Mapped[int] = mapped_column(Integer)
    eligible_zone_ids: Mapped[list] = mapped_column(JSON, default=list)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("amount_per_unit_pkr >= 0"),
        CheckConstraint("valid_to >= valid_from"),
        CheckConstraint("version >= 1"),
    )


class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    offer_type: Mapped[str] = mapped_column(String(24))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    units: Mapped[int] = mapped_column(Integer)
    eligible_zone_ids: Mapped[list] = mapped_column(JSON, default=list)
    cost_pkr: Mapped[int] = mapped_column(Integer)
    funding_included: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (
        CheckConstraint("offer_type IN ('SUBSIDY', 'PARTNER_QUOTA', 'MOBILE_UNIT')"),
        CheckConstraint("units >= 0 AND cost_pkr >= 0"),
        CheckConstraint("end_date >= start_date"),
        CheckConstraint("valid_to >= valid_from"),
        CheckConstraint("version >= 1"),
    )


class PartnerQuotaOffer(Base):
    __tablename__ = "partner_quota_offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), unique=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    spare_capacity_group_id: Mapped[str] = mapped_column(String(64), index=True)


class MobileUnitOffer(Base):
    __tablename__ = "mobile_unit_offers"
    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), unique=True)
    mobile_unit_id: Mapped[str] = mapped_column(String(64))
    site_zone_id: Mapped[str] = mapped_column(String(50))
    service_date: Mapped[date] = mapped_column(Date)
    __table_args__ = (UniqueConstraint("mobile_unit_id", "site_zone_id", "service_date"),)


class DemandSnapshot(Base):
    __tablename__ = "demand_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    local_month: Mapped[date] = mapped_column(Date)
    service_date_start: Mapped[date] = mapped_column(Date)
    service_date_end: Mapped[date] = mapped_column(Date)
    input_hash: Mapped[str] = mapped_column(String(64))
    request_ids: Mapped[list] = mapped_column(JSON, default=list)
    cohorts: Mapped[list] = mapped_column(JSON, default=list)
    exclusions: Mapped[list] = mapped_column(JSON, default=list)
    capacity_versions: Mapped[list] = mapped_column(JSON, default=list)
    offer_versions: Mapped[list] = mapped_column(JSON, default=list)
    rule_versions: Mapped[list] = mapped_column(JSON, default=list)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")
    __table_args__ = (CheckConstraint("service_date_end >= service_date_start"),)


class AllocationPlan(Base):
    __tablename__ = "allocation_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date)
    cost: Mapped[int]
    units: Mapped[int]
    allocations: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    public_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    input_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("demand_snapshots.id"), nullable=True)
    solver_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    objective_json: Mapped[dict] = mapped_column(JSON, default=dict)
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (
        CheckConstraint("cost >= 0 AND units >= 0"),
        CheckConstraint("status IN ('draft', 'approved', 'DRAFT', 'APPROVED', 'PENDING_ACTIVATION', 'ACTIVE', 'CLOSED', 'REJECTED', 'CANCELLED')"),
        CheckConstraint("version >= 1", name="ck_allocation_plans_version"),
    )


class PlanAction(Base):
    __tablename__ = "plan_actions"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("allocation_plans.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(24))
    offer_id: Mapped[int | None] = mapped_column(ForeignKey("offers.id"), nullable=True)
    subsidy_rule_id: Mapped[int | None] = mapped_column(ForeignKey("subsidy_rules.id"), nullable=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    zone_id: Mapped[str] = mapped_column(String(50))
    service_date: Mapped[date] = mapped_column(Date)
    units: Mapped[int] = mapped_column(Integer)
    cost_pkr: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    version: Mapped[int] = mapped_column(Integer, default=1)
    assignments: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (
        CheckConstraint("action_type IN ('SUBSIDY', 'PARTNER_QUOTA', 'MOBILE_UNIT')"),
        CheckConstraint("units >= 0 AND cost_pkr >= 0"),
        CheckConstraint("status IN ('DRAFT', 'APPROVED', 'PENDING_ACTIVATION', 'ACTIVE', 'CLOSED', 'REJECTED', 'CANCELLED')"),
        CheckConstraint("version >= 1"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(64), unique=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80))
    object_type: Mapped[str] = mapped_column(String(40))
    object_id: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reason: Mapped[str] = mapped_column(String(250), default="")
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), default="synthetic")


class SeedMetadata(Base):
    __tablename__ = "seed_metadata"
    id: Mapped[int] = mapped_column(primary_key=True)
    seed_key: Mapped[str] = mapped_column(String(80), unique=True)
    seed_version: Mapped[str] = mapped_column(String(40))
    seed_clock: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    declared_timezone: Mapped[str] = mapped_column(String(80), default="Asia/Karachi")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
