from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator

ZONES = ["Central", "East", "South", "West", "North"]
TARGET_SERVICE_CODE = "PRIMARY_CARE_OPD"
REQUEST_STATES = ("OPEN", "IN_PROGRESS", "UNRESOLVED", "FULFILLED", "CANCELLED", "OUT_OF_SCOPE")
REFERRAL_ATTEMPT_STATES = (
    "PROPOSED", "AWAITING_CONFIRMATIONS", "CONFIRMED", "ARRIVED", "COMPLETED",
    "REJECTED", "CANCELLED", "EXPIRED", "NO_SHOW",
)
PLAN_ACTION_STATES = ("DRAFT", "APPROVED", "PENDING_ACTIVATION", "ACTIVE", "CLOSED", "REJECTED", "CANCELLED")
LEDGER_STATES = ("HELD", "COMMITTED", "SETTLED", "RELEASED")


class FacilityInput(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    zone: str
    kind: Literal["Hospital", "Clinic", "Diagnostic center", "Community center"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("Name must contain at least three characters")
        return value

    @field_validator("zone")
    @classmethod
    def known_zone(cls, value):
        if value not in ZONES:
            raise ValueError("Choose a supported zone")
        return value


class CapacityInput(BaseModel):
    service_id: int = Field(gt=0)
    day: date
    total: int = Field(ge=0, le=10000)


class RequestInput(BaseModel):
    service_id: int = Field(gt=0)
    zone: Literal["Central", "East", "South", "West", "North"]
    day: date
    priority: Literal["routine", "urgent"] = "routine"


class ReserveInput(BaseModel):
    facility_id: int = Field(gt=0)


class BudgetInput(BaseModel):
    total: int = Field(ge=0, le=100000000)


class PlanInput(BaseModel):
    day: date
    limit: int = Field(gt=0, le=100000000)


class MatchInput(BaseModel):
    description: str = Field(min_length=2, max_length=300)
