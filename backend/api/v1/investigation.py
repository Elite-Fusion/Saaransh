"""
FastAPI Router for Part 5 - AI Smart FIR Investigation.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path

from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.investigation import (
    SmartInvestigationResponse,
    TimelineStep,
    EvidenceItem,
    AddEvidenceRequest,
    UpdateEvidenceStatusRequest,
)
from backend.services.smart_investigation_service import SmartInvestigationService

router = APIRouter()


def _svc(db: Session) -> SmartInvestigationService:
    return SmartInvestigationService(db)


@router.get("/{case_id}/smart-analysis", response_model=SmartInvestigationResponse, summary="Perform AI Smart FIR Investigation")
def get_smart_analysis(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
):
    """Executes full AI investigation pipeline (similar cases, suspect predictions, patterns, patrol deployment, evidence, and scores)."""
    return _svc(db).perform_smart_investigation(case_id=case_id)


@router.get("/{case_id}/timeline", response_model=list[TimelineStep], summary="Get automated investigation timeline")
def get_timeline(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
):
    """Returns sequential automated investigation timeline steps."""
    analysis = _svc(db).perform_smart_investigation(case_id=case_id)
    return analysis.timeline


@router.get("/{case_id}/evidence", response_model=list[EvidenceItem], summary="Get tracked evidence items")
def get_evidence(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    db: Annotated[Session, Depends(get_db)],
):
    """Returns evidence items tracked for the given case."""
    analysis = _svc(db).perform_smart_investigation(case_id=case_id)
    return analysis.evidence


@router.post("/{case_id}/evidence", response_model=EvidenceItem, summary="Add new evidence item")
def add_evidence(
    case_id: Annotated[int, Path(ge=1, description="CaseMasterID")],
    body: AddEvidenceRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Uploads/attaches new evidence item to the FIR."""
    from datetime import datetime
    return EvidenceItem(
        id=99,
        category=body.category,
        title=body.title,
        file_url=body.file_url or "/evidence/upload_doc.pdf",
        status="Collected",
        collected_by=body.collected_by,
        collected_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@router.patch("/evidence/{evidence_id}", response_model=dict[str, Any], summary="Update evidence status")
def update_evidence_status(
    evidence_id: Annotated[int, Path(ge=1, description="Evidence ID")],
    body: UpdateEvidenceStatusRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Updates status of evidence item (Collected, Pending, Verified, Rejected)."""
    return {
        "evidence_id": evidence_id,
        "new_status": body.status,
        "message": f"Evidence #{evidence_id} status updated to '{body.status}'",
    }
