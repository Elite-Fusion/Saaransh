# Saaransh AI — Database Relationship Reference

> **Phase 2 deliverable.** Auto-generated alongside the ORM models.
> Source of truth: `backend/models/*.py`. Mermaid ERD: `backend/docs/erd.mmd`.

This document explains **every table** in the KSP schema, **every
foreign key**, and **every ORM relationship** in plain language.

---

## 1. The 30 Tables at a Glance

| Group             | Count | Tables |
|-------------------|-------|--------|
| Geography         |   2   | `State`, `District` |
| Organisation      |   6   | `UnitType`, `Unit`, `Rank`, `Designation`, `Employee`, `Court` |
| Crime Taxonomy    |  11   | `CaseCategory`, `GravityOffence`, `CaseStatusMaster`, `CrimeHead`, `CrimeSubHead`, `Act`, `Section`, `CrimeHeadActSection`, `OccupationMaster`, `ReligionMaster`, `CasteMaster` |
| Case Core         |   9   | `CaseMaster`, `ComplainantDetails`, `Victim`, `Accused`, `ArrestSurrender`, `ActSectionAssociation`, `ChargesheetDetails`, `Evidence`, `RecoveredItems` |
| AI / Security     |   2   | `AuditLog`, `Users` |
| **Total**         | **30**| |

---

## 2. Table-by-Table Notes

### 2.1 Geography

#### `State`
Root of the geo tree. Seed has 1 row (Karnataka).
- `StateID` PK
- `StateName` required
- `NationalityID` (unconstrained INT — not used in demo)
- `Active` soft-delete flag

#### `District`
A police district within a state. Seed has 8 Karnataka districts.
- `DistrictID` PK
- `StateID` → `State.StateID`
- `Active` soft-delete flag

---

### 2.2 Organisation

#### `UnitType`
Type of police unit. Seed: Police Station, Circle Office, SP Office.
- `UnitTypeID` PK
- `CityDistState` — "City" | "District" | "State"
- `Hierarchy` — ordering (1 = top-level)

#### `Unit`
A physical police unit (a station, circle, or SP office).
- `UnitID` PK
- `TypeID` → `UnitType.UnitTypeID`
- `ParentUnit` → `Unit.UnitID` (self-reference for hierarchy)
- `StateID` → `State.StateID`
- `DistrictID` → `District.DistrictID`
- `latitude`, `longitude` — for map display

#### `Rank`
Police rank from DGP down to Constable. Seed: 11 ranks.
- `RankID` PK
- `Hierarchy` — 1 = highest (DGP), 11 = lowest (Constable)

#### `Designation`
Job role: IO, SHO, CI, etc. Seed: 3 designations.
- `DesignationID` PK
- `SortOrder` — display order

#### `Employee`
A police officer. Seed: 8 officers.
- `EmployeeID` PK
- `DistrictID` → `District.DistrictID`
- `UnitID` → `Unit.UnitID`
- `RankID` → `Rank.RankID`
- `DesignationID` → `Designation.DesignationID`
- `KGID` — Karnataka Government ID, unique
- `FirstName` required
- `EmployeeDOB`, `GenderID`, `BloodGroupID`, `PhysicallyChallenged`, `AppointmentDate` — optional profile fields
- `Active` soft-delete flag

#### `Court`
A court where cases are heard. Seed: 5 courts.
- `CourtID` PK
- `DistrictID` → `District.DistrictID`
- `StateID` → `State.StateID`
- `Active` soft-delete flag

---

### 2.3 Crime Taxonomy

#### `CaseCategory`
Top-level case type: FIR, UDR, PAR, Zero FIR. Seed: 4.
- `CaseCategoryID` PK
- `LookupValue` required

#### `GravityOffence`
Severity: Heinous, Non-Heinous, Minor. Seed: 3.
- `GravityOffenceID` PK
- `LookupValue` required

#### `CaseStatusMaster`
Lifecycle: Open, Under Investigation, Charge Sheeted, Closed, Undetected. Seed: 5.
- `CaseStatusID` PK
- `CaseStatusName` required

#### `CrimeHead`
Top-level crime group (6 in seed).
- `CrimeHeadID` PK
- `CrimeGroupName` required (e.g. "Crimes Against Property")
- `Active` soft-delete
- **ORM relationship:** `sub_heads → list[CrimeSubHead]`

#### `CrimeSubHead`
Specific crime type (17 in seed).
- `CrimeSubHeadID` PK
- `CrimeHeadID` → `CrimeHead.CrimeHeadID`
- `CrimeHeadName` required (e.g. "Chain Snatching")
- `SeqID` — display order within parent
- `Active` soft-delete
- **ORM relationship:** `crime_head → CrimeHead`

#### `Act`
A law: IPC, BNS, NDPS, IT, DV. Seed: 5.
- `ActCode` PK (e.g. "IPC")
- `ActDescription`, `ShortName` optional
- `Active` soft-delete
- **ORM relationship:** `sections → list[Section]`

#### `Section`
A section of an Act. Composite PK.
- `SectionCode` PK (e.g. "302")
- `ActCode` PK + FK → `Act.ActCode`
- `SectionDescription` optional (e.g. "Murder")
- **ORM relationship:** `act → Act`

#### `CrimeHeadActSection`
M:N bridge: which sections typically apply to which crime heads.
- `CrimeHeadID` PK + FK → `CrimeHead.CrimeHeadID`
- `ActCode` PK + FK → `Act.ActCode`
- `SectionCode` PK (no FK to `Section` — schema leaves it open for the act/section pair)

#### `OccupationMaster`, `ReligionMaster`, `CasteMaster`
Three small lookup tables for complainant demographics. Seed: 7 occupations, 6 religions, 4 castes.

---

### 2.4 Case Core

#### `CaseMaster` ⭐
The heart of the database. One row per FIR. Seed: 30 cases.
- `CaseMasterID` PK
- `CrimeNo` unique (the FIR number)
- `CrimeRegisteredDate` required
- `PolicePersonID` → `Employee.EmployeeID` (the IO)
- `PoliceStationID` → `Unit.UnitID`
- `CaseCategoryID` → `CaseCategory.CaseCategoryID`
- `GravityOffenceID` → `GravityOffence.GravityOffenceID`
- `CrimeMajorHeadID` → `CrimeHead.CrimeHeadID`
- `CrimeMinorHeadID` → `CrimeSubHead.CrimeSubHeadID`
- `CaseStatusID` → `CaseStatusMaster.CaseStatusID`
- `CourtID` → `Court.CourtID`
- `IncidentFromDate`, `IncidentToDate`, `InfoReceivedPSDate` — timestamps
- `latitude`, `longitude` — geo pin of the incident
- `BriefFacts` — free-text case description (used for embedding)
- `mo_embedding` — **pgvector Vector(384)** sentence-transformer embedding of `BriefFacts` (Phase 7)
- `is_series_crime`, `series_id` — cluster markers used for cross-case linking (Phase 3 demo)
- `created_at` — server timestamp

**ORM relationships (15):**
```
police_station            → Unit              (via PoliceStationID)
investigating_officer     → Employee          (via PolicePersonID)
court                     → Court             (via CourtID)
case_category             → CaseCategory      (via CaseCategoryID)
gravity                   → GravityOffence    (via GravityOffenceID)
crime_major_head          → CrimeHead         (via CrimeMajorHeadID)
crime_minor_head          → CrimeSubHead      (via CrimeMinorHeadID)
case_status               → CaseStatusMaster  (via CaseStatusID)
complainants              → list[ComplainantDetails]
victims                   → list[Victim]
accused                   → list[Accused]
arrests                   → list[ArrestSurrender]
act_sections              → list[ActSectionAssociation]
chargesheet               → ChargesheetDetails|None
evidence                  → list[Evidence]
recovered_items           → list[RecoveredItems]
```

#### `ComplainantDetails`
The person who reported the FIR. Seed: empty (no rows in seed).
- `ComplainantID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `ComplainantName` required
- `AgeYear`, `GenderID` optional
- `OccupationID` → `OccupationMaster.OccupationID`
- `ReligionID` → `ReligionMaster.ReligionID`
- `CasteID` → `CasteMaster.caste_master_id` *(note: column name is `caste_master_id`, snake-case)*

#### `Victim`
A victim of the case. Seed: 7 rows.
- `VictimMasterID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `VictimName` required
- `VictimPolice` — `'1'` if victim is a police officer
- `photo_url`, `photo_hash` — SHA-256 hash for integrity

#### `Accused`
A person accused. Seed: 10 rows.
- `AccusedMasterID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `AccusedName` required
- `PersonID` — `A1`, `A2`, `A3`… role-within-case identifier
- `is_known_criminal`, `criminal_history` — for repeat-offender tracking
- `photo_url`, `photo_hash`, `address`

**ORM relationships:**
```
case    → CaseMaster
arrests → list[ArrestSurrender]
recovered_items → list[RecoveredItems]
```

#### `ArrestSurrender`
An arrest or surrender event. Seed: 6 rows.
- `ArrestSurrenderID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `ArrestSurrenderTypeID` *(INT — no lookup table; convention TBD)*
- `ArrestSurrenderStateId` → `State.StateID`
- `ArrestSurrenderDistrictId` → `District.DistrictID`
- `PoliceStationID` → `Unit.UnitID`
- `IOID` → `Employee.EmployeeID` (the IO who made the arrest)
- `CourtID` → `Court.CourtID`
- `AccusedMasterID` → `Accused.AccusedMasterID`
- `IsAccused`, `IsComplainantAccused` — booleans

#### `ActSectionAssociation`
Which Act+Section(s) are charged on a case. Seed: 13 rows.
- `CaseMasterID` PK + FK
- `ActID` PK + FK → `Act.ActCode`
- `SectionID` PK
- `ActOrderID`, `SectionOrderID` — display order

#### `ChargesheetDetails`
Zero-or-one chargesheet per case. Seed: 6 rows.
- `CSID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `csdate` — date filed
- `cstype` — `'A'`=Chargesheet, `'B'`=False Case, `'C'`=Undetected
- `PolicePersonID` → `Employee.EmployeeID`

#### `Evidence`
Photo / file evidence with chain-of-custody hash. Seed: empty.
- `EvidenceID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `evidence_type` — `'CrimeScene'` | `'Weapon'` | `'Recovered'` | `'Document'`
- `file_url`, `file_hash` — SHA-256
- `gps_lat`, `gps_lng` — where collected
- `uploaded_by` → `Employee.EmployeeID`

#### `RecoveredItems`
Items recovered from an accused. Seed: empty.
- `RecoveryID` PK
- `CaseMasterID` → `CaseMaster.CaseMasterID`
- `AccusedMasterID` → `Accused.AccusedMasterID`
- `item_description` required
- `quantity`, `estimated_value`
- `photo_url`, `photo_hash`
- `recovery_date`, `recovery_location`
- `recovered_by` → `Employee.EmployeeID`
- `witness_name`, `seizure_memo_ref`

---

### 2.5 AI / Security

#### `AuditLog`
One row per AI query — the trust layer. Seed: empty.
- `LogID` PK
- `EmployeeID` → `Employee.EmployeeID`
- `officer_name`, `officer_rank` — denormalised for quick display
- `action` — e.g. `'nl_query'`, `'similarity_search'`
- `query_text` — the user's question
- `result_count` — how many rows came back
- `ip_address`

#### `Users`
A login identity bound to an `Employee`. Seed: 6 users.
- `UserID` PK
- `EmployeeID` → `Employee.EmployeeID`
- `email` unique
- `role` — `'inspector'` | `'si'` | (admin added later)
- `is_active`, `last_login`, `created_at`

---

## 3. Key Relationship Map

```
                          ┌────────┐
                          │ State  │
                          └───┬────┘
                              │ 1
                       ┌──────┴──────┐
                       ▼ N           ▼ N
                  ┌─────────┐    ┌─────────┐
                  │District │    │  Court  │
                  └────┬────┘    └────┬────┘
                       │ N            │
            ┌──────────┤              │
            ▼ 1        ▼ 1            ▼ 1
       ┌────────┐  ┌────────┐         │
       │  Unit  │  │Employee├─────────┘
       │ (PS)   │  │(Officer)│
       └───┬────┘  └───┬────┘
           │ 1          │ 1
           │ N          │ N (as IO, IOID, recovered_by, etc.)
           ▼            ▼
      ┌────────────────────────┐
      │       CaseMaster       │  ◄── the FIR
      └─┬─┬─┬─┬─┬─┬─┬─┬───────┘
        │ │ │ │ │ │ │ │
   Complainant Victim Accused Arrest Act-Section Chargesheet
                            │
                            ▼
                       Accused ──► RecoveredItems
                            │
                            ▼
                       ArrestSurrender (IO, PS, Court…)

       CrimeHead ─┐
                  ├─► CrimeSubHead
       Act ───────┴─► Section ─┐
                              │
            CrimeHeadActSection (M:N, schema)
            ActSectionAssociation (per case)

       Employee ──► AuditLog
       Employee ──► Users
```

---

## 4. Cardinality Cheat-Sheet

| Parent | Child | Cardinality | Why |
|---|---|---|---|
| `State` | `District` | 1 : N | Karnataka has many districts |
| `State` | `Unit` | 1 : N | Units belong to a state |
| `District` | `Unit` | 1 : N | PS is in a district |
| `UnitType` | `Unit` | 1 : N | Many units share a type |
| `Unit` | `Unit` | 1 : N (self) | A circle has many stations |
| `Rank` | `Employee` | 1 : N | One rank, many officers |
| `District` | `Employee` | 1 : N | Officers posted to a district |
| `CrimeHead` | `CrimeSubHead` | 1 : N | Group → sub-types |
| `Act` | `Section` | 1 : N | An act has many sections |
| `CaseMaster` | `Complainant/Victim/Accused` | 1 : N | Case can have many |
| `CaseMaster` | `Chargesheet` | 1 : 0..1 | At most one chargesheet |
| `CaseMaster` | `ActSectionAssociation` | 1 : N | Many acts/sections per case |
| `Accused` | `ArrestSurrender` | 1 : N | Can be arrested multiple times |
| `Accused` | `RecoveredItems` | 1 : N | Can have many items |
| `CaseMaster` | `Evidence` | 1 : N | Many pieces of evidence |
| `Employee` | `AuditLog` | 1 : N | Officer runs many queries |
| `Employee` | `Users` | 1 : 0..1 | Each officer may have a login |

---

## 5. Notes & Gotchas

1. **Composite PKs:** `Section`, `ActSectionAssociation`, `CrimeHeadActSection` use multi-column primary keys. The ORM models declare each component column individually with `primary_key=True`.
2. **`CasteMaster` column name:** The schema uses snake_case `caste_master_id` rather than the `CasteID` style used elsewhere. The ORM mirrors this exactly to keep autogenerate quiet.
3. **Vectors:** `CaseMaster.mo_embedding` is a pgvector `Vector(384)` column. It can only be created/queried in Postgres (the `pgvector` Python extension handles the binding). It will not work in SQLite.
4. **Nullable foreign keys everywhere:** Every FK in the schema is declared `nullable=True` in the ORM. This mirrors the real KSP data, where many old FIRs have missing/cleared officer assignments.
5. **`is_series_crime` + `series_id`:** Two non-standard columns added to `CaseMaster` to support the "cross-case linking" demo. Three series exist in the seed (chain-snatching in Mysuru, ATM skimming in Whitefield, drug trafficking in Mangaluru).
6. **`Evidence` and `RecoveredItems` are empty in the seed** — the demo in Phase 3 will either back-fill them or generate them at runtime from `BriefFacts`.
7. **`mo_embedding` is NULL in the seed** — populated in Phase 7 by `scripts/embed_existing_cases.py`.
