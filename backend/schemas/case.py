"""
Pydantic schemas — case-related request and response models.

All response models set ``from_attributes=True`` so they can be built
directly from SQLAlchemy ORM objects. Field names follow the snake_case
public API convention; the ``validation_alias`` maps the database
column name to the snake_case field on input.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.common import PaginationMeta

# ---------------------------------------------------------------------
# Reference models — used inside summary and detail responses
# ---------------------------------------------------------------------


class DistrictRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    district_id: int = Field(validation_alias="DistrictID")
    district_name: str = Field(validation_alias="DistrictName")


class PoliceStationRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    unit_id: int = Field(validation_alias="UnitID")
    unit_name: str = Field(validation_alias="UnitName")
    district: DistrictRef | None = None


class CaseCategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    case_category_id: int = Field(validation_alias="CaseCategoryID")
    lookup_value: str = Field(validation_alias="LookupValue")


class GravityRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    gravity_offence_id: int = Field(validation_alias="GravityOffenceID")
    lookup_value: str = Field(validation_alias="LookupValue")


class CaseStatusRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    case_status_id: int = Field(validation_alias="CaseStatusID")
    case_status_name: str = Field(validation_alias="CaseStatusName")


class CrimeHeadRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    crime_head_id: int = Field(validation_alias="CrimeHeadID")
    crime_group_name: str = Field(validation_alias="CrimeGroupName")


class CrimeSubHeadRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    crime_sub_head_id: int = Field(validation_alias="CrimeSubHeadID")
    crime_head_name: str = Field(validation_alias="CrimeHeadName")


class CourtRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    court_id: int = Field(validation_alias="CourtID")
    court_name: str = Field(validation_alias="CourtName")


# ---------------------------------------------------------------------
# Person sub-models
# ---------------------------------------------------------------------


class ComplainantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    complainant_id: int = Field(validation_alias="ComplainantID")
    case_master_id: int | None = Field(default=None, validation_alias="CaseMasterID")
    complainant_name: str = Field(validation_alias="ComplainantName")
    age_year: int | None = Field(default=None, validation_alias="AgeYear")
    gender_id: int | None = Field(default=None, validation_alias="GenderID")
    occupation_id: int | None = Field(default=None, validation_alias="OccupationID")
    religion_id: int | None = Field(default=None, validation_alias="ReligionID")
    caste_id: int | None = Field(default=None, validation_alias="CasteID")


class VictimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    victim_master_id: int = Field(validation_alias="VictimMasterID")
    case_master_id: int | None = Field(default=None, validation_alias="CaseMasterID")
    victim_name: str = Field(validation_alias="VictimName")
    age_year: int | None = Field(default=None, validation_alias="AgeYear")
    gender_id: int | None = Field(default=None, validation_alias="GenderID")
    victim_police: str | None = Field(default=None, validation_alias="VictimPolice")
    photo_url: str | None = None


class AccusedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    accused_master_id: int = Field(validation_alias="AccusedMasterID")
    case_master_id: int | None = Field(default=None, validation_alias="CaseMasterID")
    accused_name: str = Field(validation_alias="AccusedName")
    age_year: int | None = Field(default=None, validation_alias="AgeYear")
    gender_id: int | None = Field(default=None, validation_alias="GenderID")
    person_id: str | None = Field(default=None, validation_alias="PersonID")
    address: str | None = None
    is_known_criminal: bool | None = None
    criminal_history: str | None = None
    photo_url: str | None = None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    evidence_id: int = Field(validation_alias="EvidenceID")
    case_master_id: int | None = Field(default=None, validation_alias="CaseMasterID")
    evidence_type: str | None = None
    file_url: str | None = None
    description: str | None = None
    gps_lat: float | None = None
    gps_lng: float | None = None
    collected_at: datetime | None = None
    uploaded_by: int | None = None


class RecoveredItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    recovery_id: int = Field(validation_alias="RecoveryID")
    case_master_id: int | None = Field(default=None, validation_alias="CaseMasterID")
    accused_master_id: int | None = Field(
        default=None, validation_alias="AccusedMasterID"
    )
    item_description: str
    quantity: str | None = None
    estimated_value: float | None = None
    photo_url: str | None = None
    recovery_date: datetime | None = None
    recovery_location: str | None = None
    recovered_by: int | None = None
    witness_name: str | None = None
    seizure_memo_ref: str | None = None


class ChargesheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    csid: int = Field(validation_alias="CSID")
    case_master_id: int | None = Field(default=None, validation_alias="CaseMasterID")
    csdate: datetime | None = None
    cstype: str | None = None
    police_person_id: int | None = Field(
        default=None, validation_alias="PolicePersonID"
    )


class ActSectionOut(BaseModel):
    """A single Act+Section charged on a case."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    act_code: str = Field(validation_alias="ActID")
    section_code: str = Field(validation_alias="SectionID")
    act_order_id: int | None = Field(default=None, validation_alias="ActOrderID")
    section_order_id: int | None = Field(
        default=None, validation_alias="SectionOrderID"
    )
    act_short_name: str | None = None
    act_description: str | None = None
    section_description: str | None = None


class AssignedOfficerOut(BaseModel):
    """An officer (IO or chargesheet filer) on a case."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    employee_id: int = Field(validation_alias="EmployeeID")
    kgid: str | None = Field(default=None, validation_alias="KGID")
    first_name: str = Field(validation_alias="FirstName")
    role: str


# ---------------------------------------------------------------------
# Top-level case responses
# ---------------------------------------------------------------------


class CaseSummaryOut(BaseModel):
    """Lightweight row used by the list endpoint."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    case_id: int = Field(validation_alias="CaseMasterID")
    crime_no: str = Field(validation_alias="CrimeNo")
    case_no: str | None = Field(default=None, validation_alias="CaseNo")
    crime_registered_date: date = Field(validation_alias="CrimeRegisteredDate")
    case_status: CaseStatusRef | None = None
    case_category: CaseCategoryRef | None = None
    gravity: GravityRef | None = None
    crime_major_head: CrimeHeadRef | None = None
    crime_minor_head: CrimeSubHeadRef | None = None
    police_station: PoliceStationRef | None = None
    brief_facts: str | None = Field(default=None, validation_alias="BriefFacts")
    is_series_crime: bool | None = None
    series_id: int | None = None


class CaseDetailOut(BaseModel):
    """Everything attached to one case."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    case_id: int = Field(validation_alias="CaseMasterID")
    crime_no: str = Field(validation_alias="CrimeNo")
    case_no: str | None = Field(default=None, validation_alias="CaseNo")
    crime_registered_date: date = Field(validation_alias="CrimeRegisteredDate")
    incident_from_date: datetime | None = Field(
        default=None, validation_alias="IncidentFromDate"
    )
    incident_to_date: datetime | None = Field(
        default=None, validation_alias="IncidentToDate"
    )
    info_received_ps_date: datetime | None = Field(
        default=None, validation_alias="InfoReceivedPSDate"
    )
    latitude: float | None = None
    longitude: float | None = None
    brief_facts: str | None = Field(default=None, validation_alias="BriefFacts")
    is_series_crime: bool | None = None
    series_id: int | None = None
    created_at: datetime | None = None

    case_status: CaseStatusRef | None = None
    case_category: CaseCategoryRef | None = None
    gravity: GravityRef | None = None
    crime_major_head: CrimeHeadRef | None = None
    crime_minor_head: CrimeSubHeadRef | None = None
    court: CourtRef | None = None
    police_station: PoliceStationRef | None = None

    # People
    complainants: list[ComplainantOut] = Field(default_factory=list)
    victims: list[VictimOut] = Field(default_factory=list)
    accused: list[AccusedOut] = Field(default_factory=list)

    # Documents and items
    evidence: list[EvidenceOut] = Field(default_factory=list)
    recovered_items: list[RecoveredItemOut] = Field(default_factory=list)
    act_sections: list[ActSectionOut] = Field(default_factory=list)
    chargesheet: ChargesheetOut | None = None
    assigned_officers: list[AssignedOfficerOut] = Field(default_factory=list)


# Concrete list response used by the route (so Swagger has a named schema).
class CaseListResponse(BaseModel):
    items: list[CaseSummaryOut]
    pagination: PaginationMeta

    @classmethod
    def build(
        cls,
        items: list[CaseSummaryOut],
        meta: PaginationMeta,
    ) -> "CaseListResponse":
        return cls(items=items, pagination=meta)
