# Saaransh AI — Natural Language → SQL Prompt

> **Phase 5 — Foundation.** The schema reference and the
> `{{SCHEMA_SUMMARY}}` placeholder are filled in by
> `PromptService.render(...)` at call time in Phase 6.

---

## Task

Convert the officer's natural-language question into a single
**parameterised SQL `SELECT`** statement against the KSP FIR
schema. Return the SQL plus the bound parameters as a JSON object.

---

## Schema reference

The full schema is appended to this prompt at call time as
`{{SCHEMA_SUMMARY}}`. Treat that block as authoritative — do not
invent table or column names that are not in it.

Key entities:

- `CaseMaster` — the FIR. PK `CaseMasterID`. Unique `CrimeNo`.
- `Unit` — police stations. Belongs to a `District` and a `State`.
- `CrimeHead` / `CrimeSubHead` — the crime taxonomy (group → type).
- `CaseStatusMaster` — lifecycle: `Open`, `Under Investigation`,
  `Charge Sheeted`, `Closed`, `Undetected`.
- `Accused`, `Victim`, `ComplainantDetails`, `Evidence`,
  `RecoveredItems`, `ChargesheetDetails`, `ActSectionAssociation` —
  children of a case.

---

## Allowlist of SQL verbs

| Allowed | Forbidden |
|---|---|
| `SELECT` | `DELETE`, `UPDATE`, `INSERT`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE` |

Any forbidden verb causes the entire response to be rejected.

---

## Output format

Return a single JSON object (no prose, no Markdown) shaped exactly
like this:

```json
{
  "sql": "SELECT ... FROM ... WHERE ...",
  "params": { ":param_name": value },
  "tables": ["CaseMaster", "Unit"],
  "estimated_rows": "low | medium | high | unknown",
  "notes": "Free-text caveats, if any. Empty string when none."
}
```

Rules:

- `sql` is a single statement, no semicolons at the end.
- `params` uses named bind parameters (`:district_id`, never `?`).
  Every user-supplied value must be a parameter — never concatenated
  into the SQL string.
- `tables` lists every table the query references, in the order
  they appear. Used by the audit logger.
- `estimated_rows` is a hint, not a guarantee. Use the cardinalities
  you can read off the schema (PKs, FKs, indexes).
- `notes` is for things the caller should know — e.g. "This query
  joins through `Unit`, so cases with no `PoliceStationID` are
  excluded."

---

## Filters you should honour

When the user mentions any of these, translate to a `WHERE` clause:

| Natural language | SQL fragment |
|---|---|
| "in <District>" | `JOIN Unit AS u ON cm.PoliceStationID = u.UnitID JOIN District AS d ON u.DistrictID = d.DistrictID WHERE ILIKE(d.DistrictName, :district_name)` |
| "at <Police Station>" | `JOIN Unit AS u ON cm.PoliceStationID = u.UnitID WHERE ILIKE(u.UnitName, :unit_name)` |
| "of type <Crime Head>" | `JOIN CrimeHead AS ch ON cm.CrimeMajorHeadID = ch.CrimeHeadID WHERE ILIKE(ch.CrimeGroupName, :crime_group_name)` (Note: `CrimeMajorHeadID` is an integer FK; do NOT compare `CrimeMajorHeadID` directly to a string name) |
| "sub-type <Crime Sub Head>" | `JOIN CrimeSubHead AS csh ON cm.CrimeMinorHeadID = csh.CrimeSubHeadID WHERE ILIKE(csh.CrimeHeadName, :subhead_name)` |
| "status <Open / Closed / ...>" | `JOIN CaseStatusMaster AS csm ON cm.CaseStatusID = csm.CaseStatusID WHERE ILIKE(csm.CaseStatusName, :status_name)` (Note: `CaseStatusID` is an integer FK; do NOT compare `CaseStatusID` directly to string `'Open'`) |
| "registered between X and Y" | `WHERE cm.CrimeRegisteredDate BETWEEN :date_from AND :date_to` |
| "FIR number <CrimeNo>" | `WHERE cm.CrimeNo = :fir_number` (exact match) |

IMPORTANT: Foreign key columns like `CrimeMajorHeadID`, `CaseStatusID`, `PoliceStationID`, `DistrictID` are INTEGERS. Never pass a string like `'chain snatching'` or `'Open'` as a value for an integer column. Always `JOIN` the corresponding lookup table (`CrimeHead`, `CaseStatusMaster`, `District`, `Unit`) when filtering by text names.


---

## Hard rules

- Never use `SELECT *`. Always project the columns the response
  needs.
- Always include `ORDER BY CrimeRegisteredDate DESC, CaseMasterID DESC`
  unless the user explicitly asks for a different order.
- Always apply a `LIMIT` (default `100`) unless the user asks for
  the full set.
- Never trust user input. Every value is a bind parameter.
- If the request cannot be expressed in `SELECT`, return
  `{"sql": "", "params": {}, "tables": [], "estimated_rows": "unknown", "notes": "request is not a read query"}`.

---

## Examples (Phase 6 will populate)

The Phase 5 prompt is structural. Phase 6 will add five-to-ten
worked examples (one per common filter combination) and an explicit
few-shot section.
