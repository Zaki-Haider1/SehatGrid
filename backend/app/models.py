from datetime import date, datetime, timezone
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


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
    __table_args__ = (UniqueConstraint("name", "zone"),)


class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    aliases: Mapped[str] = mapped_column(String(500))
    unit_cost: Mapped[int]
    __table_args__ = (CheckConstraint("unit_cost > 0"),)


class Capacity(Base):
    __tablename__ = "capacities"
    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    day: Mapped[date] = mapped_column(Date, index=True)
    total: Mapped[int]
    reserved: Mapped[int] = mapped_column(default=0)
    consumed: Mapped[int] = mapped_column(default=0)
    __table_args__ = (
        UniqueConstraint("facility_id", "service_id", "day"),
        CheckConstraint("total >= 0 AND reserved >= 0 AND consumed >= 0 AND total >= reserved + consumed"),
    )


class CareRequest(Base):
    __tablename__ = "care_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    zone: Mapped[str] = mapped_column(String(50), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        CheckConstraint("priority IN ('routine', 'urgent')"),
        CheckConstraint("status IN ('pending', 'reserved', 'confirmed', 'completed', 'cancelled')"),
    )


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("care_requests.id"), index=True)
    capacity_id: Mapped[int] = mapped_column(ForeignKey("capacities.id"))
    status: Mapped[str] = mapped_column(String(20), default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (CheckConstraint("status IN ('reserved', 'confirmed', 'completed', 'cancelled')"),)


class Budget(Base):
    __tablename__ = "budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    total: Mapped[int]
    committed: Mapped[int] = mapped_column(default=0)
    __table_args__ = (CheckConstraint("total >= committed AND committed >= 0"),)


class AllocationPlan(Base):
    __tablename__ = "allocation_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date)
    cost: Mapped[int]
    units: Mapped[int]
    allocations: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        CheckConstraint("cost >= 0 AND units >= 0"),
        CheckConstraint("status IN ('draft', 'approved')"),
    )
