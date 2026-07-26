"""
Deterministic synthetic dataset for the Phase-9 ML layer.

The KSP real seed has ~30 cases — too small to train any
meaningful model. This module generates a larger, **deterministic**
synthetic dataset (~1000 cases + ~600 accused records) with
realistic distributions so the demo is end-to-end useful.

The generator is deterministic: a fixed seed produces the same
output every time. Tests rely on this property; the training
script logs the seed at the top of its output for traceability.

Each generated row mirrors the shape of a real
:class:`backend.models.case.CaseMaster` /
:class:`backend.models.case.Accused` row, but only the columns
the ML layer actually consumes are populated. Anything else is
left as ``None``.

The generator does **not** insert rows into the database. The
training script reads the in-memory result and fits a
scikit-learn model. A future phase can persist the synthetic
rows to a table.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Sequence


#: Master list of Karnataka districts used in the synthetic
#: data. Mirrors the seed (``database/seed/ksp_real_seed.sql``).
DISTRICTS: tuple[str, ...] = (
    "Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Kalaburagi",
    "Hubballi", "Mangaluru", "Dharwad", "Belagavi", "Tumakuru",
    "Ballari", "Vijayapura", "Davangere", "Shivamogga", "Raichur",
    "Udupi", "Hassan", "Mandya", "Chitradurga", "Chikkamagaluru",
    "Kolar", "Chikkaballapur", "Ramanagara", "Chamarajanagar",
    "Yadgir", "Koppal", "Gadag", "Haveri", "Karwar", "Bagalkot",
    "Bidar",
)

#: Crime heads the synthetic data draws from. Mirrors the
#: ``crimehead`` lookup.
CRIME_HEADS: tuple[str, ...] = (
    "Crimes Against Property",
    "Crimes Against Persons",
    "Crimes Against Public Tranquillity",
    "Cyber Crime",
    "Economic Offences",
    "Special & Local Laws",
)

#: Crime sub-heads the synthetic data draws from. Mirrors the
#: ``crimesubhead`` lookup.
CRIME_SUB_HEADS: tuple[str, ...] = (
    "Theft", "Chain Snatching", "Robbery", "Burglary", "Dacoity",
    "Murder", "Attempt to Murder", "Rape", "Kidnapping", "Assault",
    "Cyber Fraud", "Hacking", "Phishing",
    "Cheating", "Forgery", "Extortion",
    "Rioting", "Arson", "Cruelty", "Molestation", "Stalking",
)

#: Gravity buckets the synthetic data draws from.
GRAVITIES: tuple[str, ...] = ("Heinous", "Non-Heinous")

#: Case-status names the synthetic data draws from.
STATUSES: tuple[str, ...] = (
    "Open", "Under Investigation", "Charge Sheeted", "Closed",
)

#: Synthetic FIR number prefix. Real KSP FIRs follow a station
#: code pattern; the prefix here is just a recognisable label.
_FIR_PREFIX = "1044"


# ---------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticCase:
    """One synthetic CaseMaster-shaped row.

    Only the columns consumed by the ML layer are populated.
    Field names mirror the ORM attribute names (the SQL column
    names are lowercase; we keep the camelCase Python names
    that the rest of the codebase uses).
    """

    CaseMasterID: int
    CrimeNo: str
    CrimeRegisteredDate: date
    CrimeMajorHeadName: str
    CrimeMinorHeadName: str
    GravityName: str
    CaseStatusName: str
    DistrictName: str
    # ML-friendly features that map to the real schema columns
    # but are produced directly by the generator (they would
    # otherwise require a JOIN during training).
    latitude: float
    longitude: float
    BriefFacts: str
    is_series_crime: bool
    series_id: int | None
    dow: int  # 0..6 (Mon..Sun)
    month: int  # 1..12
    # Latent features used as the regression/classification
    # targets by the trainers. The real database does not
    # have these columns — they exist only in the synthetic
    # dataset so the trainers have something to fit against.
    case_count_target: int = 0
    recidivism_target: int = 0
    risk_label: str = "medium"

    def as_feature_dict(self) -> dict:
        """Return a flat dict for the feature builder."""
        return {
            "case_id": self.CaseMasterID,
            "district": self.DistrictName,
            "crime_head": self.CrimeMajorHeadName,
            "crime_sub_head": self.CrimeMinorHeadName,
            "gravity": self.GravityName,
            "status": self.CaseStatusName,
            "month": self.month,
            "dow": self.dow,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_series_crime": self.is_series_crime,
            "series_id": self.series_id,
            "case_count_target": self.case_count_target,
            "recidivism_target": self.recidivism_target,
            "risk_label": self.risk_label,
        }


@dataclass(frozen=True)
class SyntheticAccused:
    """One synthetic Accused-shaped row.

    The fields below mirror the real ``accused`` table. Only
    the columns consumed by the repeat-offender predictor are
    populated.
    """

    AccusedMasterID: int
    AccusedName: str
    AgeYear: int
    GenderID: int
    is_known_criminal: bool
    criminal_history: str
    # Target for the repeat-offender classifier (1 = reoffended,
    # 0 = did not). Synthesised by the generator so the trainer
    # has a label.
    reoffended: int
    prior_count: int  # how many prior cases the accused was in
    primary_crime_head: str
    primary_gravity: str


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------


def _bounded(value: float, lo: float, hi: float) -> float:
    """Clamp a value into ``[lo, hi]``."""
    return max(lo, min(hi, value))


def _dow(d: date) -> int:
    """Day-of-week, Mon=0..Sun=6 (Python's convention)."""
    return d.weekday()


def _series_id_for(rng: random.Random) -> int | None:
    """Generate a series id 30% of the time, ``None`` otherwise.

    About a third of the synthetic cases are flagged as
    "series crimes" — they share a series_id with one or more
    other cases. This mirrors the seed (which pre-seeds 8
    series-crime rows).
    """
    if rng.random() < 0.30:
        return rng.randint(1, 200)
    return None


def _brief_facts(rng: random.Random, crime_sub_head: str) -> str:
    """Build a short, deterministic-ish "BriefFacts" string.

    The text is consumed by the TF-IDF part of the clustering
    and similarity predictors. Real brief facts are freeform
    police narratives; the synthetic version is short and
    keyword-rich so TF-IDF has signal to work with.
    """
    samples = {
        "Theft": (
            "gold chain stolen at knife-point near bus stand",
            "two-wheeler lifted from parking lot residential colony",
            "house break-in through rear window cash missing",
        ),
        "Chain Snatching": (
            "bike-borne accused snatched gold chain from woman",
            "two-wheeler chased victim and grabbed chain",
            "evening time chain snatching on busy road",
        ),
        "Robbery": (
            "armed robbery at ATM cash van",
            "group of four robbed jewellery shop",
            "knife-point robbery of mobile phone shop",
        ),
        "Murder": (
            "stabbing incident following altercation over money",
            "body found in abandoned building suspected murder",
            "domestic violence escalated to homicide",
        ),
        "Cyber Fraud": (
            "OTP phishing scam UPI account drained",
            "fake customer care number refund fraud",
            "investment app fraud lakhs siphoned",
        ),
        "Hacking": (
            "email account compromised malicious links sent",
            "social media account hacked private photos leaked",
        ),
        "Rape": (
            "sexual assault reported survivor statement recorded",
        ),
        "Kidnapping": (
            "child kidnapped from school van ransom demanded",
        ),
        "Burglary": (
            "midnight burglary of locked shop laptop stolen",
        ),
        "Dacoity": (
            "gang of six committed dacoity at farmhouse",
        ),
    }
    pool = samples.get(crime_sub_head, ("general crime reported",))
    return rng.choice(pool)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def generate_synthetic_cases(
    n: int = 1000,
    *,
    seed: int = 42,
    start: date | None = None,
    end: date | None = None,
) -> list[SyntheticCase]:
    """Generate ``n`` synthetic cases.

    Args:
        n: Number of cases to generate. Default 1000.
        seed: RNG seed. The same ``(n, seed)`` always produces
            the same list, so tests are reproducible.
        start: Inclusive lower bound on
            :attr:`SyntheticCase.CrimeRegisteredDate`. Defaults
            to 18 months before ``end`` (or today).
        end: Inclusive upper bound. Defaults to today.

    Returns:
        A list of :class:`SyntheticCase` objects, sorted by
        registration date (ascending) so the training script
        can split into train/test along the time axis.
    """
    rng = random.Random(seed)
    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=540)  # ~18 months

    total_days = (end - start).days
    if total_days <= 0:
        raise ValueError("`end` must be after `start`.")

    out: list[SyntheticCase] = []
    for case_id in range(1, n + 1):
        # Day-of-registration: uniform across the window so
        # trends have signal but no artificial seasonality.
        registered = start + timedelta(
            days=rng.randint(0, total_days)
        )
        crime_head = rng.choice(CRIME_HEADS)
        crime_sub_head = rng.choice(CRIME_SUB_HEADS)
        gravity = rng.choice(GRAVITIES)
        status = rng.choice(STATUSES)
        district = rng.choice(DISTRICTS)
        # Lat/long — a small jitter around each district's
        # centroid. Real KSP rows have per-case lat/long
        # (the schema has ``latitude`` and ``longitude`` on
        # both ``casemaster`` and ``unit``). For the
        # synthetic data we just use a generic Karnataka
        # bounding box.
        latitude = _bounded(12.5 + rng.uniform(-2.0, 2.0), 11.5, 18.0)
        longitude = _bounded(76.0 + rng.uniform(-2.0, 2.0), 74.0, 78.5)
        series_id = _series_id_for(rng)
        brief = _brief_facts(rng, crime_sub_head)
        # Latent targets. ``case_count_target`` is used by the
        # hotspot regression; the others by the repeat-offender
        # and risk-score classifiers. The trainer treats them
        # as the ground-truth label.
        # Crime heads that escalate quickly (murder, robbery)
        # carry a slightly higher target count.
        case_count_target = rng.randint(1, 4)
        if crime_sub_head in {"Murder", "Robbery", "Dacoity"}:
            case_count_target += rng.randint(1, 3)
        recidivism_target = 1 if (
            gravity == "Heinous" or crime_sub_head in {"Murder", "Robbery"}
        ) and rng.random() < 0.45 else 0
        risk_label = "high" if recidivism_target and crime_sub_head in {
            "Murder", "Robbery", "Dacoity",
        } else "medium" if recidivism_target else "low"
        out.append(
            SyntheticCase(
                CaseMasterID=case_id,
                CrimeNo=f"{_FIR_PREFIX}{case_id:012d}",
                CrimeRegisteredDate=registered,
                CrimeMajorHeadName=crime_head,
                CrimeMinorHeadName=crime_sub_head,
                GravityName=gravity,
                CaseStatusName=status,
                DistrictName=district,
                latitude=latitude,
                longitude=longitude,
                BriefFacts=brief,
                is_series_crime=series_id is not None,
                series_id=series_id,
                dow=_dow(registered),
                month=registered.month,
                case_count_target=case_count_target,
                recidivism_target=recidivism_target,
                risk_label=risk_label,
            )
        )

    out.sort(key=lambda c: c.CrimeRegisteredDate)
    return out


# Indian male/female first names for the synthetic accused.
# A small but recognisable pool. We do not need to be exhaustive.
_ACCUSED_FIRST_NAMES: tuple[str, ...] = (
    "Rajesh", "Suresh", "Anil", "Vinod", "Manoj", "Prakash",
    "Ravi", "Sunil", "Faisal", "Imran", "Arjun", "Karthik",
    "Sandeep", "Mohan", "Ramesh", "Mahesh", "Rakesh", "Dinesh",
    "Sanjay", "Ajay", "Vijay", "Naveen", "Kiran", "Pavan",
    "Pooja", "Priya", "Anita", "Sunita", "Lakshmi", "Kavita",
    "Rekha", "Meena", "Geeta", "Anjali", "Divya", "Sneha",
)


def _accused_name(rng: random.Random, used: set[str]) -> str:
    """Pick a unique synthetic name. Reuses a known set with
    a trailing initial to mimic "Sunil Kumar B" patterns in
    the real seed."""
    while True:
        first = rng.choice(_ACCUSED_FIRST_NAMES)
        last = rng.choice(("Kumar", "Reddy", "Sharma", "Patel",
                           "Naik", "Ahmed", "Khan", "Das", "Rao"))
        initial = rng.choice("ABCDEFGHIJKLM")
        name = f"{first} {last} {initial}"
        if name not in used:
            used.add(name)
            return name


def generate_synthetic_accused(
    cases: Sequence[SyntheticCase],
    *,
    seed: int = 43,
) -> list[SyntheticAccused]:
    """Generate one synthetic :class:`SyntheticAccused` per
    real case, plus a handful of repeat offenders (so the
    classifier has signal).

    The returned list has length ``len(cases) + extra``. About
    25% of the generated accused carry ``prior_count > 1`` so
    the repeat-offender classifier has both classes to learn.

    Args:
        cases: The synthetic cases. Used to look up the
            primary crime head and gravity that the accused
            was charged with.
        seed: RNG seed. Same ``(cases, seed)`` always produces
            the same list.

    Returns:
        A list of :class:`SyntheticAccused` objects.
    """
    rng = random.Random(seed)
    used_names: set[str] = set()
    out: list[SyntheticAccused] = []

    for case in cases:
        prior_count = rng.choices(
            [0, 1, 2, 3, 4, 5], weights=[55, 20, 12, 7, 4, 2]
        )[0]
        # Repeat offenders are the labelled positives.
        reoffended = 1 if prior_count >= 2 and rng.random() < 0.55 else (
            1 if prior_count >= 1 and rng.random() < 0.20 else 0
        )
        # Criminal history is a short freeform string. The
        # clustering predictor consumes it via TF-IDF.
        history_parts: list[str] = []
        if prior_count > 0:
            history_parts.append(
                f"{prior_count} prior case(s) in the last 5 years"
            )
        if case.GravityName == "Heinous":
            history_parts.append("heinous offence history")
        if reoffended:
            history_parts.append("reoffended within 12 months")
        history = "; ".join(history_parts) or "no prior history"
        out.append(
            SyntheticAccused(
                AccusedMasterID=case.CaseMasterID * 10,
                AccusedName=_accused_name(rng, used_names),
                AgeYear=rng.randint(18, 65),
                GenderID=rng.choice((1, 2)),
                is_known_criminal=prior_count > 0,
                criminal_history=history,
                reoffended=reoffended,
                prior_count=prior_count,
                primary_crime_head=case.CrimeMajorHeadName,
                primary_gravity=case.GravityName,
            )
        )

    return out


def cases_to_feature_matrix(
    cases: Sequence[SyntheticCase],
) -> tuple[list[list[float]], list[str]]:
    """Convert synthetic cases into a 2-D feature matrix.

    The matrix is the one the hotspot regressor and the
    risk-score classifier consume. The output is a
    ``(rows, features)`` pair. The second element is the
    column order (so callers can re-build a feature row
    at inference time).

    Columns (in order):
        0. month (1..12)
        1. dow (0..6)
        2. district_id (categorical -> int code; see below)
        3. crime_head_id (categorical -> int code)
        4. crime_sub_head_id (categorical -> int code)
        5. gravity_id (categorical -> int code)
        6. is_series_crime (0/1)
        7. latitude (normalised)
        8. longitude (normalised)
    """
    districts = sorted({c.DistrictName for c in cases})
    heads = sorted({c.CrimeMajorHeadName for c in cases})
    sub_heads = sorted({c.CrimeMinorHeadName for c in cases})
    gravities = sorted({c.GravityName for c in cases})

    district_id = {d: i for i, d in enumerate(districts)}
    head_id = {h: i for i, h in enumerate(heads)}
    sub_id = {h: i for i, h in enumerate(sub_heads)}
    grav_id = {g: i for i, g in enumerate(gravities)}

    rows: list[list[float]] = []
    for c in cases:
        rows.append([
            c.month,
            c.dow,
            district_id[c.DistrictName],
            head_id[c.CrimeMajorHeadName],
            sub_id[c.CrimeMinorHeadName],
            grav_id[c.GravityName],
            1.0 if c.is_series_crime else 0.0,
            (c.latitude - 11.5) / (18.0 - 11.5),
            (c.longitude - 74.0) / (78.5 - 74.0),
        ])
    columns = [
        "month", "dow", "district_id", "crime_head_id",
        "crime_sub_head_id", "gravity_id", "is_series_crime",
        "latitude_norm", "longitude_norm",
    ]
    return rows, columns


def dataset_summary(cases: Sequence[SyntheticCase]) -> dict:
    """Return a small summary dict the training script prints
    before training. Useful as a sanity check in the logs."""
    if not cases:
        return {"count": 0}
    by_status: dict[str, int] = {}
    by_gravity: dict[str, int] = {}
    by_head: dict[str, int] = {}
    for c in cases:
        by_status[c.CaseStatusName] = by_status.get(c.CaseStatusName, 0) + 1
        by_gravity[c.GravityName] = by_gravity.get(c.GravityName, 0) + 1
        by_head[c.CrimeMajorHeadName] = by_head.get(c.CrimeMajorHeadName, 0) + 1
    return {
        "count": len(cases),
        "first_date": cases[0].CrimeRegisteredDate.isoformat(),
        "last_date": cases[-1].CrimeRegisteredDate.isoformat(),
        "districts": len({c.DistrictName for c in cases}),
        "by_status": by_status,
        "by_gravity": by_gravity,
        "by_head": by_head,
        "series_count": sum(1 for c in cases if c.is_series_crime),
    }


__all__ = [
    "CRIME_HEADS",
    "CRIME_SUB_HEADS",
    "DISTRICTS",
    "GRAVITIES",
    "STATUSES",
    "SyntheticAccused",
    "SyntheticCase",
    "cases_to_feature_matrix",
    "dataset_summary",
    "generate_synthetic_accused",
    "generate_synthetic_cases",
]
