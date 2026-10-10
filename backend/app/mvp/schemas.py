from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Input):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class FacilityInput(Input):
    name: str = Field(min_length=3, max_length=120)
    ownership: Literal["Public", "Private"]
    address: str = Field(min_length=3, max_length=250)
    zone: str
    latitude: float = Field(ge=33.4, le=33.9)
    longitude: float = Field(ge=72.7, le=73.4)
    version: int | None = None


class Participation(Input):
    status: Literal["ACTIVE", "SUSPENDED"]
    version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)


class ServiceInput(Input):
    service_id: Literal["PRIMARY_CARE_OPD"] = "PRIMARY_CARE_OPD"
    eligible_zones: list[str] = Field(max_length=5)
    reviewed: Literal[True]
    subsidy_required: bool = False
    version: int = Field(ge=1)


class CapacityInput(Input):
    quota: int = Field(ge=0, le=10000)
    version: int = Field(ge=0)


class MatchInput(Input):
    text: str = Field(min_length=2, max_length=300)
    zone: str | None = None
    ownership: str | None = None


class ReviewInput(Input):
    match_id: str
    decision: Literal["ACCEPT", "CORRECT", "DECLINE"]
    candidate_id: str | None = None
    record_id: str | None = None
    reason: str = Field(min_length=3, max_length=500)


class RequestInput(Input):
    reference: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    source_facility_id: str
    zone: str
    original_text: str = Field(min_length=2, max_length=300)
    review_id: str | None = None
    date_from: date
    date_to: date
    suitable: bool
    needs_funding: bool = False
    funding_eligible: bool = False

    @model_validator(mode="after")
    def dates(self):
        if self.date_to < self.date_from or (self.date_to - self.date_from).days > 31:
            raise ValueError("Choose an ordered service date range of at most 31 days")
        return self


class ReserveInput(Input):
    request_id: str
    capacity_id: str
    capacity_version: int = Field(ge=1)
    facility_version: int = Field(ge=1)


class ResponseInput(Input):
    accepted: bool = True
    reason: str | None = Field(default=None, max_length=500)


class ReasonInput(Input):
    reason: str = Field(min_length=3, max_length=500)


class MonthInput(Input):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class BudgetInput(MonthInput):
    authorized: int = Field(ge=0, le=100000000)
    version: int = Field(ge=0)


class OptimizeInput(Input):
    snapshot_id: str


class OfferInput(Input):
    facility_id: str
    date: date
    eligible_zones: list[str] = Field(min_length=1, max_length=5)
    units: int = Field(ge=1, le=1000)
    cost: int = Field(ge=0, le=100000000)
    funding_included: bool
    spare_group: str | None = Field(default=None, max_length=100)
    mobile_unit: str | None = Field(default=None, max_length=100)
    site: str | None = Field(default=None, max_length=150)
    latitude: float = Field(ge=33.4, le=33.9)
    longitude: float = Field(ge=72.7, le=73.4)


class SubsidyInput(MonthInput):
    amount: int = Field(ge=0, le=1000000)
    version: int = Field(ge=1)


class Empty(Input):
    pass
