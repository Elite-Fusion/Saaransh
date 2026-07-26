"""
Pydantic schemas for Part 5 - AI Smart FIR Investigation.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class SimilarCaseMatch(BaseModel):
    case_id: int = Field(..., description="Previous CaseMasterID")
    fir_number: str = Field(..., description="Previous FIR Number")
    crime_type: str = Field(..., description="Crime Major Head")
    similarity_pct: float = Field(..., description="Similarity percentage 0-100")
    reason: str = Field(..., description="Matching rationale (MO, weapon, time, pattern)")
    status: str = Field(..., description="Current status of previous case")
    investigating_officer: str = Field(..., description="Assigned officer name")
    solve_rate_pct: float = Field(85.0, description="Officer solve rate percentage")
    district: str = Field(..., description="District name")


class SuspectPrediction(BaseModel):
    suspect_id: int = Field(..., description="Accused/Suspect Master ID")
    name: str = Field(..., description="Suspect name or alias")
    confidence_pct: float = Field(..., description="Prediction confidence percentage")
    reasoning: str = Field(..., description="AI prediction rationale")
    previous_involvement_count: int = Field(..., description="Number of prior cases/arrests")
    gang_affiliation: str | None = Field(None, description="Known gang or syndicate")
    last_known_location: str = Field(..., description="Last known location / beat zone")
    risk_level: str = Field("high", description="Risk level: high, medium, low")


class CrimePatternAnalysis(BaseModel):
    is_serial_crime: bool = Field(False, description="Flag if part of a serial crime series")
    pattern_type: str = Field(..., description="Detected pattern: Night Burglary, Festival Rush, Cyber Campaign, etc.")
    explanation: str = Field(..., description="AI pattern analysis explanation")
    repeat_crime_indicator: bool = Field(True, description="Repeat crime indicator")
    women_safety_alert: bool = Field(False, description="Women safety alert flag")
    gang_activity_detected: bool = Field(False, description="Gang activity detected")


class DeploymentRecommendation(BaseModel):
    nearest_police_station: str = Field(..., description="Nearest PS name")
    nearest_patrol_unit: str = Field(..., description="Callsign of nearest patrol vehicle")
    extra_officers_required: int = Field(2, description="Additional officers needed")
    vehicle_checkpoints: list[str] = Field(default_factory=list, description="Recommended checkpoint locations")
    night_patrol_recommended: bool = Field(True, description="Night patrol recommendation")
    drone_surveillance_recommended: bool = Field(False, description="Drone surveillance recommendation")
    cctv_monitoring_zones: list[str] = Field(default_factory=list, description="Target CCTV cameras to audit")
    est_response_time_mins: int = Field(8, description="Estimated response time in mins")


class TimelineStep(BaseModel):
    step_id: int = Field(..., description="Sequence step number")
    title: str = Field(..., description="Step title (e.g. Collect CCTV, Interview Witness)")
    status: str = Field("completed", description="Status: completed, in_progress, pending")
    timestamp: str | None = Field(None, description="Completion timestamp")
    assigned_to: str | None = Field(None, description="Officer assigned")
    notes: str | None = Field(None, description="Step notes")


class EvidenceItem(BaseModel):
    id: int = Field(..., description="Evidence ID")
    category: str = Field(..., description="Photos, Videos, Documents, Forensics, Fingerprints, DNA, Vehicle, Weapons, Witness")
    title: str = Field(..., description="Evidence description/title")
    file_url: str | None = Field(None, description="URL or file path")
    status: str = Field("Collected", description="Collected, Pending, Verified, Rejected")
    collected_by: str = Field(..., description="Officer or Forensic Lead")
    collected_at: str = Field(..., description="Date/Time collected")


class AddEvidenceRequest(BaseModel):
    category: str = Field(..., description="Photos, Videos, Documents, Forensics, Fingerprints, DNA, Vehicle, Weapons, Witness")
    title: str = Field(..., description="Evidence description")
    file_url: str | None = Field(None, description="File URL")
    collected_by: str = Field("PSI Officer", description="Collected by officer name")


class UpdateEvidenceStatusRequest(BaseModel):
    status: str = Field(..., description="Collected, Pending, Verified, Rejected")


class InvestigationScore(BaseModel):
    risk_score: int = Field(..., description="Overall risk score out of 100")
    priority_score: int = Field(..., description="Priority score out of 100")
    confidence_pct: float = Field(..., description="AI confidence percentage")
    ai_completeness_pct: float = Field(..., description="AI data completeness percentage")
    investigation_progress_pct: float = Field(..., description="Investigation workflow progress percentage")


class SmartInvestigationResponse(BaseModel):
    case_id: int = Field(..., description="CaseMasterID")
    fir_number: str = Field(..., description="Crime No / FIR Number")
    crime_type: str = Field(..., description="Major crime head")
    registered_date: str = Field(..., description="FIR registration date")
    similar_cases: list[SimilarCaseMatch] = Field(default_factory=list, description="Similar cases detected")
    suspect_predictions: list[SuspectPrediction] = Field(default_factory=list, description="AI suspect predictions")
    pattern_analysis: CrimePatternAnalysis = Field(..., description="Crime pattern analysis")
    deployment_recommendation: DeploymentRecommendation = Field(..., description="Patrol & checkpoint deployment suggestions")
    timeline: list[TimelineStep] = Field(default_factory=list, description="Automated investigation timeline")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Tracked evidence items")
    scores: InvestigationScore = Field(..., description="Composite investigation scores")
