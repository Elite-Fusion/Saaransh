from backend.models.ai import AuditLog, Users
from backend.models.case import CaseMaster, ComplainantDetails, Victim, Accused, ArrestSurrender, ActSectionAssociation, ChargesheetDetails, Evidence, RecoveredItems
from backend.models.geography import District, State
from backend.models.organisation import Court, Designation, Employee, Rank, Unit, UnitType
from backend.models.taxonomy import (
    Act,
    CaseCategory,
    CaseStatusMaster,
    CasteMaster,
    CrimeHead,
    CrimeHeadActSection,
    CrimeSubHead,
    GravityOffence,
    OccupationMaster,
    ReligionMaster,
    Section,
)


def test_models_use_lowercase_postgresql_table_names() -> None:
    assert CaseMaster.__tablename__ == "casemaster"
    assert ComplainantDetails.__tablename__ == "complainantdetails"
    assert Victim.__tablename__ == "victim"
    assert Accused.__tablename__ == "accused"
    assert ArrestSurrender.__tablename__ == "arrestsurrender"
    assert ActSectionAssociation.__tablename__ == "actsectionassociation"
    assert ChargesheetDetails.__tablename__ == "chargesheetdetails"
    assert Evidence.__tablename__ == "evidence"
    assert RecoveredItems.__tablename__ == "recovereditems"

    assert State.__tablename__ == "state"
    assert District.__tablename__ == "district"
    assert UnitType.__tablename__ == "unittype"
    assert Unit.__tablename__ == "unit"
    assert Rank.__tablename__ == "rank"
    assert Designation.__tablename__ == "designation"
    assert Employee.__tablename__ == "employee"
    assert Court.__tablename__ == "court"

    assert CaseCategory.__tablename__ == "casecategory"
    assert GravityOffence.__tablename__ == "gravityoffence"
    assert CaseStatusMaster.__tablename__ == "casestatusmaster"
    assert CrimeHead.__tablename__ == "crimehead"
    assert CrimeSubHead.__tablename__ == "crimesubhead"
    assert Act.__tablename__ == "act"
    assert Section.__tablename__ == "section"
    assert CrimeHeadActSection.__tablename__ == "crimeheadactsection"
    assert OccupationMaster.__tablename__ == "occupationmaster"
    assert ReligionMaster.__tablename__ == "religionmaster"
    assert CasteMaster.__tablename__ == "castemaster"

    assert AuditLog.__tablename__ == "auditlog"
    assert Users.__tablename__ == "users"
