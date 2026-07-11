"""
ORM models package.

Importing this package makes SQLAlchemy aware of every model so that
``Base.metadata`` is complete (used by Alembic for autogenerate later).

All models are split into logical sub-modules:

  - geography      : State, District
  - organisation   : UnitType, Unit, Rank, Designation, Employee, Court
  - taxonomy       : CaseCategory, GravityOffence, CaseStatusMaster, CrimeHead,
                     CrimeSubHead, Act, Section, CrimeHeadActSection,
                     OccupationMaster, ReligionMaster, CasteMaster
  - case           : CaseMaster, ComplainantDetails, Victim, Accused,
                     ArrestSurrender, ActSectionAssociation, ChargesheetDetails,
                     Evidence, RecoveredItems
  - ai             : AuditLog, Users
"""
from backend.models.ai import AuditLog, Users
from backend.models.case import (
    Accused,
    ActSectionAssociation,
    ArrestSurrender,
    CaseMaster,
    ChargesheetDetails,
    ComplainantDetails,
    Evidence,
    RecoveredItems,
    Victim,
)
from backend.models.geography import District, State
from backend.models.organisation import (
    Court,
    Designation,
    Employee,
    Rank,
    Unit,
    UnitType,
)
from backend.models.taxonomy import (
    Act,
    CasteMaster,
    CaseCategory,
    CaseStatusMaster,
    CrimeHead,
    CrimeHeadActSection,
    CrimeSubHead,
    GravityOffence,
    OccupationMaster,
    ReligionMaster,
    Section,
)

# Explicit __all__ so ``import backend.models`` is well-defined.
__all__ = [
    # geography
    "State",
    "District",
    # organisation
    "UnitType",
    "Unit",
    "Rank",
    "Designation",
    "Employee",
    "Court",
    # taxonomy
    "CaseCategory",
    "GravityOffence",
    "CaseStatusMaster",
    "CrimeHead",
    "CrimeSubHead",
    "Act",
    "Section",
    "CrimeHeadActSection",
    "OccupationMaster",
    "ReligionMaster",
    "CasteMaster",
    # case core
    "CaseMaster",
    "ComplainantDetails",
    "Victim",
    "Accused",
    "ArrestSurrender",
    "ActSectionAssociation",
    "ChargesheetDetails",
    "Evidence",
    "RecoveredItems",
    # ai / security
    "AuditLog",
    "Users",
]
