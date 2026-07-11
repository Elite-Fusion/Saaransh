"""
OpenAPI examples for the case API.

Every example here is a **literal** dict that FastAPI embeds into the
generated ``openapi.json`` under ``paths.<endpoint>.responses[code].content
["application/json"].examples``.  They show up in Swagger UI's "Examples"
dropdown and in ReDoc, so a consumer can see exactly what the API
returns without having to call it.

Keep this file in lockstep with the Pydantic response models — the
tests in :mod:`backend.tests.test_openapi_examples` assert that every
example here is reachable from the schema.
"""
from __future__ import annotations

# ---------------------------------------------------------------------
# Shared error envelope
# ---------------------------------------------------------------------

#: The shape used for every structured error response.
#: ``detail`` matches what ``HTTPException(detail=...)`` produces.
_ERROR_ENVELOPE = {
    "detail": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message.",
        "details": {"key": "value"},
    }
}

#: 400 — sort field rejected by the whitelist.
EXAMPLE_INVALID_SORT_FIELD = {
    "summary": "Invalid sort_by value",
    "description": (
        "Returned when the client passes a `sort_by` that is not in the "
        "service's whitelist."
    ),
    "value": {
        "detail": {
            "code": "INVALID_SORT_FIELD",
            "message": (
                "sort_by='drop_table' is not allowed. Allowed values: "
                "['case_id', 'case_status', 'crime_no', "
                "'crime_registered_date', 'created_at']"
            ),
            "details": {
                "allowed": [
                    "case_id",
                    "case_status",
                    "crime_no",
                    "crime_registered_date",
                    "created_at",
                ]
            },
        }
    },
}

#: 400 — sort order not asc/desc.
EXAMPLE_INVALID_SORT_ORDER = {
    "summary": "Invalid sort_order value",
    "description": "Returned when `sort_order` is neither 'asc' nor 'desc'.",
    "value": {
        "detail": {
            "code": "INVALID_SORT_ORDER",
            "message": "sort_order='sideways' must be 'asc' or 'desc'",
            "details": {"allowed": ["asc", "desc"]},
        }
    },
}

#: 422 — request body / query string failed Pydantic validation.
#: This is the envelope that FastAPI itself produces — the response model
#: is the framework default, NOT our ``ErrorResponse``. We document it
#: here so consumers can see the shape.
EXAMPLE_VALIDATION_ERROR = {
    "summary": "Validation error",
    "description": (
        "Returned when a query parameter or path parameter fails "
        "Pydantic validation (e.g. `page=0`, `page_size=500`, "
        "`date_from='not-a-date', `case_id=0`)."
    ),
    "value": {
        "detail": [
            {
                "type": "greater_than_equal",
                "loc": ["query", "page"],
                "msg": "Input should be greater than or equal to 1",
                "input": "0",
                "ctx": {"ge": 1},
                "url": "https://errors.pydantic.dev/2.10/v/greater_than_equal",
            }
        ]
    },
}

#: 404 — case id has no matching row.
EXAMPLE_CASE_NOT_FOUND = {
    "summary": "Case not found",
    "description": "Returned when no CaseMaster row matches the supplied id.",
    "value": {
        "detail": {
            "code": "CASE_NOT_FOUND",
            "message": "Case 99999 not found",
            "details": {"case_id": 99999},
        }
    },
}

#: 422 — invalid case_id (ge=1 violated).
EXAMPLE_INVALID_CASE_ID = {
    "summary": "Invalid case_id",
    "description": "`case_id` must be an integer >= 1.",
    "value": {
        "detail": [
            {
                "type": "greater_than_equal",
                "loc": ["path", "case_id"],
                "msg": "Input should be greater than or equal to 1",
                "input": "0",
                "ctx": {"ge": 1},
                "url": "https://errors.pydantic.dev/2.10/v/greater_than_equal",
            }
        ]
    },
}

# ---------------------------------------------------------------------
# Success examples — list endpoint
# ---------------------------------------------------------------------

EXAMPLE_LIST_SUCCESS = {
    "summary": "200 — paginated list of cases",
    "description": (
        "Default sort is `crime_registered_date desc`. The first case "
        "shown is the most recently registered FIR."
    ),
    "value": {
        "items": [
            {
                "case_id": 30,
                "crime_no": "104430001202400134",
                "case_no": "202400134",
                "crime_registered_date": "2024-07-25",
                "case_status": {
                    "case_status_id": 2,
                    "case_status_name": "Under Investigation",
                },
                "case_category": {"case_category_id": 1, "lookup_value": "FIR"},
                "gravity": {"gravity_offence_id": 2, "lookup_value": "Non-Heinous"},
                "crime_major_head": {
                    "crime_head_id": 4,
                    "crime_group_name": "Economic Offences",
                },
                "crime_minor_head": {
                    "crime_sub_head_id": 14,
                    "crime_head_name": "Cyber Fraud",
                },
                "police_station": {
                    "unit_id": 1,
                    "unit_name": "Mysuru City North PS",
                    "district": {
                        "district_id": 2,
                        "district_name": "Mysuru",
                    },
                },
                "brief_facts": (
                    "Victim paid Rs 45,000 for laptop on fake e-commerce site."
                ),
                "is_series_crime": False,
                "series_id": None,
            }
        ],
        "pagination": {
            "total": 30,
            "page": 1,
            "page_size": 20,
            "total_pages": 2,
            "has_next": True,
            "has_prev": False,
        },
    },
}

EXAMPLE_LIST_FILTERED = {
    "summary": "200 — filtered list (district by name)",
    "description": (
        "Example response for `GET /api/v1/cases?district=Bengaluru%20Urban`."
    ),
    "value": {
        "items": [
            {
                "case_id": 4,
                "crime_no": "104430002202400112",
                "case_no": "202400112",
                "crime_registered_date": "2024-02-03",
                "case_status": {"case_status_id": 4, "case_status_name": "Closed"},
                "case_category": {"case_category_id": 1, "lookup_value": "FIR"},
                "gravity": {"gravity_offence_id": 2, "lookup_value": "Non-Heinous"},
                "crime_major_head": {
                    "crime_head_id": 4,
                    "crime_group_name": "Economic Offences",
                },
                "crime_minor_head": {
                    "crime_sub_head_id": 13,
                    "crime_head_name": "ATM Skimming",
                },
                "police_station": {
                    "unit_id": 2,
                    "unit_name": "Bengaluru Whitefield PS",
                    "district": {
                        "district_id": 1,
                        "district_name": "Bengaluru Urban",
                    },
                },
                "brief_facts": (
                    "Skimming device found on ATM. Multiple accounts compromised."
                ),
                "is_series_crime": True,
                "series_id": 2,
            }
        ],
        "pagination": {
            "total": 6,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        },
    },
}

EXAMPLE_LIST_EMPTY = {
    "summary": "200 — empty results",
    "description": (
        "Returned when filters match no rows. Always 200, never 404 — an "
        "empty result is a valid response."
    ),
    "value": {
        "items": [],
        "pagination": {
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        },
    },
}

# ---------------------------------------------------------------------
# Success examples — detail endpoint
# ---------------------------------------------------------------------

EXAMPLE_DETAIL_SUCCESS = {
    "summary": "200 — full case detail",
    "description": (
        "Includes complainant, victims, accused, evidence, recovered "
        "items, act & sections, chargesheet, and assigned officers."
    ),
    "value": {
        "case_id": 12,
        "crime_no": "104430007202400033",
        "case_no": "202400033",
        "crime_registered_date": "2024-01-20",
        "incident_from_date": "2024-01-19T23:00:00",
        "incident_to_date": None,
        "info_received_ps_date": None,
        "latitude": 17.335,
        "longitude": 76.825,
        "brief_facts": (
            "Body found near Sedam Road with stab wounds. "
            "Money lending dispute suspected."
        ),
        "is_series_crime": False,
        "series_id": None,
        "created_at": "2024-01-20T00:00:00",
        "case_status": {"case_status_id": 2, "case_status_name": "Under Investigation"},
        "case_category": {"case_category_id": 1, "lookup_value": "FIR"},
        "gravity": {"gravity_offence_id": 1, "lookup_value": "Heinous"},
        "crime_major_head": {
            "crime_head_id": 1,
            "crime_group_name": "Crimes Against Body",
        },
        "crime_minor_head": {
            "crime_sub_head_id": 1,
            "crime_head_name": "Murder",
        },
        "court": {
            "court_id": 5,
            "court_name": "District Court Belagavi",
        },
        "police_station": {
            "unit_id": 7,
            "unit_name": "Kalaburagi Rural PS",
            "district": {
                "district_id": 7,
                "district_name": "Kalaburagi",
            },
        },
        "complainants": [],
        "victims": [
            {
                "victim_master_id": 3,
                "case_master_id": 12,
                "victim_name": "Shiva Kumar R",
                "age_year": 45,
                "gender_id": 1,
                "victim_police": "0",
                "photo_url": None,
            }
        ],
        "accused": [
            {
                "accused_master_id": 7,
                "case_master_id": 12,
                "accused_name": "Naveen Gowda S",
                "age_year": 31,
                "gender_id": 1,
                "person_id": "A1",
                "address": None,
                "is_known_criminal": True,
                "criminal_history": "Robbery 2020",
                "photo_url": None,
            }
        ],
        "evidence": [],
        "recovered_items": [],
        "act_sections": [
            {
                "act_code": "IPC",
                "section_code": "302",
                "act_order_id": 1,
                "section_order_id": 1,
                "act_short_name": "IPC",
                "act_description": "Indian Penal Code 1860",
                "section_description": "Murder",
            }
        ],
        "chargesheet": None,
        "assigned_officers": [
            {
                "employee_id": 7,
                "kgid": "KG-KLG-007",
                "first_name": "Ibrahim Khan S",
                "role": "investigating_officer",
            }
        ],
    },
}

# ---------------------------------------------------------------------
# Parameter examples — for the route's `openapi_extra`
# ---------------------------------------------------------------------

EXAMPLE_LIST_PARAMS = {
    "summary": "List cases with district and pagination",
    "description": (
        "Example query string: "
        "`/api/v1/cases?district=Bengaluru%20Urban&page=1&page_size=5`"
    ),
    "value": {
        "district": "Bengaluru Urban",
        "page": 1,
        "page_size": 5,
        "sort_by": "crime_registered_date",
        "sort_order": "desc",
    },
}

EXAMPLE_DETAIL_PARAMS = {
    "summary": "Get one case by id",
    "description": "Example: `/api/v1/cases/12`",
    "value": {"case_id": 12},
}


# ---------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------


#: 200 — service is up and the database is reachable.
EXAMPLE_HEALTH_SUCCESS = {
    "summary": "200 — service healthy",
    "description": (
        "Returned when the API and the database are both reachable. "
        "HTTP status is always 200; the database state is reported "
        "in the `database` field so liveness probes can read it "
        "without retrying on transient DB blips."
    ),
    "value": {
        "status": "ok",
        "service": "Saaransh AI",
        "version": "0.1.0",
        "environment": "development",
        "database": "up",
        "timestamp": "2026-07-09T10:15:30.123456+00:00",
    },
}

#: 200 — service is up but the database is currently unreachable.
#: Still HTTP 200 — see the description on ``EXAMPLE_HEALTH_SUCCESS``.
EXAMPLE_HEALTH_DEGRADED = {
    "summary": "200 — service up, database down",
    "description": (
        "Returned when the API process is healthy but a `SELECT 1` "
        "against the database fails. The HTTP status remains 200 so "
        "probes do not flap during transient DB outages; the "
        "`database: down` field is the source of truth for the "
        "monitoring system."
    ),
    "value": {
        "status": "ok",
        "service": "Saaransh AI",
        "version": "0.1.0",
        "environment": "development",
        "database": "down",
        "timestamp": "2026-07-09T10:15:30.123456+00:00",
    },
}


# ---------------------------------------------------------------------
# Dashboard — summary
# ---------------------------------------------------------------------


#: 200 — six headline numbers, including a normal mix of statuses.
#: Convictions/acquittals are 0 in the current schema.
EXAMPLE_SUMMARY_NORMAL = {
    "summary": "200 — summary with realistic counts",
    "description": (
        "Example for `GET /api/v1/dashboard/summary` over a 30-case "
        "seed dataset. `convictions` and `acquittals` are always 0 "
        "in the current schema — verdict data is not yet tracked; "
        "the fields exist in the contract for the React UI and the "
        "Gemini AI provider."
    ),
    "value": {
        "total_cases": 30,
        "open_cases": 9,
        "closed_cases": 8,
        "charge_sheet_filed": 6,
        "convictions": 0,
        "acquittals": 0,
    },
}

#: 200 — all zeros (no cases registered or all filters miss).
EXAMPLE_SUMMARY_ZEROS = {
    "summary": "200 — summary with all zeros",
    "description": (
        "Returned when the result set is empty (no cases, or the "
        "district filter matches no rows). 200, never 404 — an "
        "empty result is a valid response."
    ),
    "value": {
        "total_cases": 0,
        "open_cases": 0,
        "closed_cases": 0,
        "charge_sheet_filed": 0,
        "convictions": 0,
        "acquittals": 0,
    },
}


# ---------------------------------------------------------------------
# Dashboard — monthly trends
# ---------------------------------------------------------------------


#: 200 — full year of monthly counts.
EXAMPLE_MONTHLY_NORMAL = {
    "summary": "200 — monthly trends for 2024 (unfiltered)",
    "description": (
        "Always 12 entries (Jan..Dec). Months with no cases appear "
        "with `case_count: 0` so the chart never has gaps."
    ),
    "value": {
        "year": 2024,
        "district": None,
        "items": [
            {"year": 2024, "month": 1, "month_label": "Jan", "case_count": 3},
            {"year": 2024, "month": 2, "month_label": "Feb", "case_count": 4},
            {"year": 2024, "month": 3, "month_label": "Mar", "case_count": 4},
            {"year": 2024, "month": 4, "month_label": "Apr", "case_count": 4},
            {"year": 2024, "month": 5, "month_label": "May", "case_count": 4},
            {"year": 2024, "month": 6, "month_label": "Jun", "case_count": 5},
            {"year": 2024, "month": 7, "month_label": "Jul", "case_count": 5},
            {"year": 2024, "month": 8, "month_label": "Aug", "case_count": 1},
            {"year": 2024, "month": 9, "month_label": "Sep", "case_count": 0},
            {"year": 2024, "month": 10, "month_label": "Oct", "case_count": 0},
            {"year": 2024, "month": 11, "month_label": "Nov", "case_count": 0},
            {"year": 2024, "month": 12, "month_label": "Dec", "case_count": 0},
        ],
    },
}

#: 200 — monthly trends narrowed to a single district.
EXAMPLE_MONTHLY_FILTERED = {
    "summary": "200 — monthly trends filtered by district",
    "description": (
        "Example for `GET /api/v1/dashboard/monthly-trends?year=2024"
        "&district=Mysuru`. The `district` field echoes the applied "
        "filter so the UI can render the chart title."
    ),
    "value": {
        "year": 2024,
        "district": {"district_id": 2, "district_name": "Mysuru"},
        "items": [
            {"year": 2024, "month": 1, "month_label": "Jan", "case_count": 1},
            {"year": 2024, "month": 2, "month_label": "Feb", "case_count": 0},
            {"year": 2024, "month": 3, "month_label": "Mar", "case_count": 1},
            {"year": 2024, "month": 4, "month_label": "Apr", "case_count": 0},
            {"year": 2024, "month": 5, "month_label": "May", "case_count": 0},
            {"year": 2024, "month": 6, "month_label": "Jun", "case_count": 1},
            {"year": 2024, "month": 7, "month_label": "Jul", "case_count": 2},
            {"year": 2024, "month": 8, "month_label": "Aug", "case_count": 0},
            {"year": 2024, "month": 9, "month_label": "Sep", "case_count": 0},
            {"year": 2024, "month": 10, "month_label": "Oct", "case_count": 0},
            {"year": 2024, "month": 11, "month_label": "Nov", "case_count": 0},
            {"year": 2024, "month": 12, "month_label": "Dec", "case_count": 0},
        ],
    },
}

#: 200 — monthly trends for a year that has no data.
EXAMPLE_MONTHLY_EMPTY = {
    "summary": "200 — empty year (zero-fills every month)",
    "description": (
        "Returned when no cases were registered in the requested "
        "year for the given district. The 12-month structure is "
        "preserved so the chart always has 12 data points."
    ),
    "value": {
        "year": 2023,
        "district": None,
        "items": [
            {"year": 2023, "month": m, "month_label": mo, "case_count": 0}
            for m, mo in enumerate(
                ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                start=1,
            )
        ],
    },
}


# ---------------------------------------------------------------------
# Dashboard — crime head distribution
# ---------------------------------------------------------------------


EXAMPLE_CRIME_HEAD_NORMAL = {
    "summary": "200 — crime head distribution (unfiltered)",
    "description": (
        "Example for `GET /api/v1/dashboard/crime-head-distribution` "
        "over the 30-case seed. `Crimes Against Property` leads the "
        "distribution, matching the seed."
    ),
    "value": {
        "items": [
            {"key": 2, "label": "Crimes Against Property", "case_count": 12},
            {"key": 4, "label": "Economic Offences", "case_count": 6},
            {"key": 5, "label": "Drug Offences", "case_count": 5},
            {"key": 1, "label": "Crimes Against Body", "case_count": 3},
            {"key": 3, "label": "Crimes Against Women", "case_count": 2},
            {"key": 6, "label": "Crimes Against Children", "case_count": 2},
        ],
        "total": 30,
    },
}

EXAMPLE_CRIME_HEAD_FILTERED = {
    "summary": "200 — crime head distribution filtered by district",
    "description": (
        "Example for `GET /api/v1/dashboard/crime-head-distribution"
        "?district=Bengaluru%20Urban`. The 3 Bengaluru Urban cases "
        "fall under Economic Offences (ATM skimming, cyber fraud)."
    ),
    "value": {
        "items": [
            {"key": 4, "label": "Economic Offences", "case_count": 3},
        ],
        "total": 3,
    },
}

EXAMPLE_CRIME_HEAD_EMPTY = {
    "summary": "200 — empty distribution",
    "description": (
        "Returned when the filter (or the entire database) has no "
        "cases. Always 200 — an empty distribution is a valid "
        "response."
    ),
    "value": {"items": [], "total": 0},
}


# ---------------------------------------------------------------------
# Dashboard — status distribution
# ---------------------------------------------------------------------


EXAMPLE_STATUS_NORMAL = {
    "summary": "200 — case status distribution",
    "description": (
        "Example for `GET /api/v1/dashboard/status-distribution` "
        "over the 30-case seed. Mirrors the summary headline numbers."
    ),
    "value": {
        "items": [
            {"key": 1, "label": "Open", "case_count": 9},
            {"key": 2, "label": "Under Investigation", "case_count": 7},
            {"key": 3, "label": "Charge Sheeted", "case_count": 6},
            {"key": 4, "label": "Closed", "case_count": 8},
            {"key": 5, "label": "Undetected", "case_count": 0},
        ],
        "total": 30,
    },
}

EXAMPLE_STATUS_EMPTY = {
    "summary": "200 — empty status distribution",
    "description": "Returned when no cases exist.",
    "value": {"items": [], "total": 0},
}


# ---------------------------------------------------------------------
# Dashboard — district distribution
# ---------------------------------------------------------------------


EXAMPLE_DISTRICT_NORMAL = {
    "summary": "200 — case count by district",
    "description": (
        "Example for `GET /api/v1/dashboard/district-distribution`. "
        "Each row counts cases whose police station belongs to the "
        "district."
    ),
    "value": {
        "items": [
            {"key": 1, "label": "Bengaluru Urban", "case_count": 7},
            {"key": 2, "label": "Mysuru", "case_count": 6},
            {"key": 3, "label": "Dharwad", "case_count": 3},
            {"key": 4, "label": "Dakshina Kannada", "case_count": 4},
            {"key": 5, "label": "Belagavi", "case_count": 3},
            {"key": 6, "label": "Shivamogga", "case_count": 3},
            {"key": 7, "label": "Kalaburagi", "case_count": 3},
            {"key": 8, "label": "Tumakuru", "case_count": 1},
        ],
        "total": 30,
    },
}

EXAMPLE_DISTRICT_EMPTY = {
    "summary": "200 — empty district distribution",
    "description": "Returned when no cases exist.",
    "value": {"items": [], "total": 0},
}


# ---------------------------------------------------------------------
# Dashboard — recent cases
# ---------------------------------------------------------------------


EXAMPLE_RECENT_NORMAL = {
    "summary": "200 — most recent cases (default limit 10)",
    "description": (
        "Example for `GET /api/v1/dashboard/recent-cases`. The "
        "items list is the same shape as the case-list endpoint, "
        "ordered by `CrimeRegisteredDate` descending."
    ),
    "value": {
        "items": [
            {
                "case_id": 30,
                "crime_no": "104430001202400134",
                "case_no": "202400134",
                "crime_registered_date": "2024-07-25",
                "case_status": {
                    "case_status_id": 2,
                    "case_status_name": "Under Investigation",
                },
                "case_category": {"case_category_id": 1, "lookup_value": "FIR"},
                "gravity": {"gravity_offence_id": 2, "lookup_value": "Non-Heinous"},
                "crime_major_head": {
                    "crime_head_id": 4,
                    "crime_group_name": "Economic Offences",
                },
                "crime_minor_head": {
                    "crime_sub_head_id": 14,
                    "crime_head_name": "Cyber Fraud",
                },
                "police_station": {
                    "unit_id": 1,
                    "unit_name": "Mysuru City North PS",
                    "district": {
                        "district_id": 2,
                        "district_name": "Mysuru",
                    },
                },
                "brief_facts": "Victim paid Rs 45,000 for laptop on fake e-commerce site.",
                "is_series_crime": False,
                "series_id": None,
            }
        ],
        "pagination": {
            "total": 30,
            "page": 1,
            "page_size": 10,
            "total_pages": 3,
            "has_next": True,
            "has_prev": False,
        },
    },
}

EXAMPLE_RECENT_EMPTY = {
    "summary": "200 — no recent cases",
    "description": (
        "Returned when the database is empty. Always 200, never 404."
    ),
    "value": {
        "items": [],
        "pagination": {
            "total": 0,
            "page": 1,
            "page_size": 10,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
        },
    },
}
