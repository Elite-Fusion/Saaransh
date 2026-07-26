from backend.models.case import CaseMaster
from backend.models.geography import District
from backend.models.organisation import Unit
from backend.models.taxonomy import CaseStatusMaster


def test_postgres_compatible_table_names_use_lowercase_identifiers() -> None:
    assert CaseMaster.__table__.name == "casemaster"
    assert District.__table__.name == "district"
    assert Unit.__table__.name == "unit"
    assert CaseStatusMaster.__table__.name == "casestatusmaster"
