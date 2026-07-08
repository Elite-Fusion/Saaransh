-- ============================================================
--  KSP DATATHON — Real KSP Schema (matches official ER diagram)
--  Drop old tables first, then recreate
--  Run in Supabase SQL Editor
--  Database Manager: Dharaneesh J
-- ============================================================

-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- LOOKUP / MASTER TABLES (no dependencies)
-- ============================================================
CREATE TABLE IF NOT EXISTS State (
  StateID       SERIAL PRIMARY KEY,
  StateName     VARCHAR(100) NOT NULL,
  NationalityID INT,
  Active        BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS District (
  DistrictID    SERIAL PRIMARY KEY,
  DistrictName  VARCHAR(100) NOT NULL,
  StateID       INT REFERENCES State(StateID),
  Active        BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS UnitType (
  UnitTypeID    SERIAL PRIMARY KEY,
  UnitTypeName  VARCHAR(100) NOT NULL,
  CityDistState VARCHAR(20),   -- 'City','District','State'
  Hierarchy     INT,
  Active        BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Unit (
  UnitID        SERIAL PRIMARY KEY,
  UnitName      VARCHAR(200) NOT NULL,
  TypeID        INT REFERENCES UnitType(UnitTypeID),
  ParentUnit    INT REFERENCES Unit(UnitID),
  StateID       INT REFERENCES State(StateID),
  DistrictID    INT REFERENCES District(DistrictID),
  latitude      DECIMAL(9,6),
  longitude     DECIMAL(9,6),
  Active        BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Rank (
  RankID        SERIAL PRIMARY KEY,
  RankName      VARCHAR(100) NOT NULL,
  Hierarchy     INT,
  Active        BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Designation (
  DesignationID   SERIAL PRIMARY KEY,
  DesignationName VARCHAR(100) NOT NULL,
  SortOrder       INT,
  Active          BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Employee (
  EmployeeID          SERIAL PRIMARY KEY,
  DistrictID          INT REFERENCES District(DistrictID),
  UnitID              INT REFERENCES Unit(UnitID),
  RankID              INT REFERENCES Rank(RankID),
  DesignationID       INT REFERENCES Designation(DesignationID),
  KGID                VARCHAR(50) UNIQUE,
  FirstName           VARCHAR(100) NOT NULL,
  EmployeeDOB         DATE,
  GenderID            INT,
  BloodGroupID        INT,
  PhysicallyChallenged BOOLEAN DEFAULT false,
  AppointmentDate     DATE,
  Active              BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Court (
  CourtID    SERIAL PRIMARY KEY,
  CourtName  VARCHAR(200) NOT NULL,
  DistrictID INT REFERENCES District(DistrictID),
  StateID    INT REFERENCES State(StateID),
  Active     BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS CaseCategory (
  CaseCategoryID SERIAL PRIMARY KEY,
  LookupValue    VARCHAR(50) NOT NULL  -- 'FIR','UDR','PAR','Zero FIR'
);

CREATE TABLE IF NOT EXISTS GravityOffence (
  GravityOffenceID SERIAL PRIMARY KEY,
  LookupValue      VARCHAR(100) NOT NULL  -- 'Heinous','Non-Heinous'
);

CREATE TABLE IF NOT EXISTS CaseStatusMaster (
  CaseStatusID   SERIAL PRIMARY KEY,
  CaseStatusName VARCHAR(100) NOT NULL  -- 'Open','Under Investigation','Charge Sheeted','Closed'
);

CREATE TABLE IF NOT EXISTS CrimeHead (
  CrimeHeadID     SERIAL PRIMARY KEY,
  CrimeGroupName  VARCHAR(200) NOT NULL,
  Active          BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS CrimeSubHead (
  CrimeSubHeadID  SERIAL PRIMARY KEY,
  CrimeHeadID     INT REFERENCES CrimeHead(CrimeHeadID),
  CrimeHeadName   VARCHAR(200) NOT NULL,
  SeqID           INT,
  Active          BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Act (
  ActCode        VARCHAR(50) PRIMARY KEY,
  ActDescription VARCHAR(500),
  ShortName      VARCHAR(100),
  Active         BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS Section (
  SectionCode        VARCHAR(50),
  ActCode            VARCHAR(50) REFERENCES Act(ActCode),
  SectionDescription VARCHAR(500),
  Active             BOOLEAN DEFAULT true,
  PRIMARY KEY (SectionCode, ActCode)
);

CREATE TABLE IF NOT EXISTS CrimeHeadActSection (
  CrimeHeadID  INT REFERENCES CrimeHead(CrimeHeadID),
  ActCode      VARCHAR(50) REFERENCES Act(ActCode),
  SectionCode  VARCHAR(50),
  PRIMARY KEY (CrimeHeadID, ActCode, SectionCode)
);

CREATE TABLE IF NOT EXISTS OccupationMaster (
  OccupationID   SERIAL PRIMARY KEY,
  OccupationName VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS ReligionMaster (
  ReligionID   SERIAL PRIMARY KEY,
  ReligionName VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS CasteMaster (
  caste_master_id   SERIAL PRIMARY KEY,
  caste_master_name VARCHAR(100) NOT NULL
);

-- ============================================================
-- CORE — CASE MASTER (FIR)
-- ============================================================
CREATE TABLE IF NOT EXISTS CaseMaster (
  CaseMasterID          SERIAL PRIMARY KEY,
  CrimeNo               VARCHAR(50) UNIQUE NOT NULL,
  CaseNo                VARCHAR(20),
  CrimeRegisteredDate   DATE NOT NULL,
  PolicePersonID        INT REFERENCES Employee(EmployeeID),
  PoliceStationID       INT REFERENCES Unit(UnitID),
  CaseCategoryID        INT REFERENCES CaseCategory(CaseCategoryID),
  GravityOffenceID      INT REFERENCES GravityOffence(GravityOffenceID),
  CrimeMajorHeadID      INT REFERENCES CrimeHead(CrimeHeadID),
  CrimeMinorHeadID      INT REFERENCES CrimeSubHead(CrimeSubHeadID),
  CaseStatusID          INT REFERENCES CaseStatusMaster(CaseStatusID),
  CourtID               INT REFERENCES Court(CourtID),
  IncidentFromDate      TIMESTAMP,
  IncidentToDate        TIMESTAMP,
  InfoReceivedPSDate    TIMESTAMP,
  latitude              DECIMAL(9,6),
  longitude             DECIMAL(9,6),
  BriefFacts            TEXT,
  -- Extra fields for AI features
  mo_embedding          vector(384),  -- semantic MO vector
  is_series_crime       BOOLEAN DEFAULT false,
  series_id             INT,
  created_at            TIMESTAMP DEFAULT now()
);

-- ============================================================
-- COMPLAINANT
-- ============================================================
CREATE TABLE IF NOT EXISTS ComplainantDetails (
  ComplainantID   SERIAL PRIMARY KEY,
  CaseMasterID    INT REFERENCES CaseMaster(CaseMasterID),
  ComplainantName VARCHAR(200) NOT NULL,
  AgeYear         INT,
  OccupationID    INT REFERENCES OccupationMaster(OccupationID),
  ReligionID      INT REFERENCES ReligionMaster(ReligionID),
  CasteID         INT REFERENCES CasteMaster(caste_master_id),
  GenderID        INT
);

-- ============================================================
-- VICTIM
-- ============================================================
CREATE TABLE IF NOT EXISTS Victim (
  VictimMasterID  SERIAL PRIMARY KEY,
  CaseMasterID    INT REFERENCES CaseMaster(CaseMasterID),
  VictimName      VARCHAR(200) NOT NULL,
  AgeYear         INT,
  GenderID        INT,
  VictimPolice    VARCHAR(1) DEFAULT '0',  -- '1' if victim is police
  photo_url       TEXT,
  photo_hash      TEXT
);

-- ============================================================
-- ACCUSED
-- ============================================================
CREATE TABLE IF NOT EXISTS Accused (
  AccusedMasterID SERIAL PRIMARY KEY,
  CaseMasterID    INT REFERENCES CaseMaster(CaseMasterID),
  AccusedName     VARCHAR(200) NOT NULL,
  AgeYear         INT,
  GenderID        INT,
  PersonID        VARCHAR(10),   -- A1, A2, A3...
  photo_url       TEXT,
  photo_hash      TEXT,
  address         TEXT,
  is_known_criminal BOOLEAN DEFAULT false,
  criminal_history  TEXT
);

-- ============================================================
-- ARREST / SURRENDER
-- ============================================================
CREATE TABLE IF NOT EXISTS ArrestSurrender (
  ArrestSurrenderID       SERIAL PRIMARY KEY,
  CaseMasterID            INT REFERENCES CaseMaster(CaseMasterID),
  ArrestSurrenderTypeID   INT,
  ArrestSurrenderDate     DATE,
  ArrestSurrenderStateId  INT REFERENCES State(StateID),
  ArrestSurrenderDistrictId INT REFERENCES District(DistrictID),
  PoliceStationID         INT REFERENCES Unit(UnitID),
  IOID                    INT REFERENCES Employee(EmployeeID),
  CourtID                 INT REFERENCES Court(CourtID),
  AccusedMasterID         INT REFERENCES Accused(AccusedMasterID),
  IsAccused               BOOLEAN DEFAULT true,
  IsComplainantAccused    BOOLEAN DEFAULT false
);

-- ============================================================
-- ACT-SECTION ASSOCIATION (charges on a case)
-- ============================================================
CREATE TABLE IF NOT EXISTS ActSectionAssociation (
  CaseMasterID  INT REFERENCES CaseMaster(CaseMasterID),
  ActID         VARCHAR(50) REFERENCES Act(ActCode),
  SectionID     VARCHAR(50),
  ActOrderID    INT,
  SectionOrderID INT,
  PRIMARY KEY (CaseMasterID, ActID, SectionID)
);

-- ============================================================
-- CHARGESHEET
-- ============================================================
CREATE TABLE IF NOT EXISTS ChargesheetDetails (
  CSID           SERIAL PRIMARY KEY,
  CaseMasterID   INT REFERENCES CaseMaster(CaseMasterID),
  csdate         TIMESTAMP,
  cstype         CHAR(1),   -- A=Chargesheet, B=False Case, C=Undetected
  PolicePersonID INT REFERENCES Employee(EmployeeID)
);

-- ============================================================
-- EVIDENCE (our addition for photo evidence)
-- ============================================================
CREATE TABLE IF NOT EXISTS Evidence (
  EvidenceID    SERIAL PRIMARY KEY,
  CaseMasterID  INT REFERENCES CaseMaster(CaseMasterID),
  evidence_type VARCHAR(50),  -- 'CrimeScene','Weapon','Recovered','Document'
  file_url      TEXT,
  file_hash     TEXT,
  description   TEXT,
  gps_lat       DECIMAL(9,6),
  gps_lng       DECIMAL(9,6),
  collected_at  TIMESTAMP,
  uploaded_by   INT REFERENCES Employee(EmployeeID),
  created_at    TIMESTAMP DEFAULT now()
);

-- ============================================================
-- RECOVERED ITEMS (our addition)
-- ============================================================
CREATE TABLE IF NOT EXISTS RecoveredItems (
  RecoveryID        SERIAL PRIMARY KEY,
  CaseMasterID      INT REFERENCES CaseMaster(CaseMasterID),
  AccusedMasterID   INT REFERENCES Accused(AccusedMasterID),
  item_description  TEXT NOT NULL,
  quantity          VARCHAR(50),
  estimated_value   DECIMAL(12,2),
  photo_url         TEXT,
  photo_hash        TEXT,
  recovery_date     TIMESTAMP,
  recovery_location TEXT,
  recovered_by      INT REFERENCES Employee(EmployeeID),
  witness_name      TEXT,
  seizure_memo_ref  TEXT,
  created_at        TIMESTAMP DEFAULT now()
);

-- ============================================================
-- AUDIT LOG (our addition for AI query tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS AuditLog (
  LogID        SERIAL PRIMARY KEY,
  EmployeeID   INT REFERENCES Employee(EmployeeID),
  officer_name TEXT,
  officer_rank TEXT,
  action       VARCHAR(50),
  query_text   TEXT,
  result_count INT,
  ip_address   VARCHAR(50),
  created_at   TIMESTAMP DEFAULT now()
);

-- ============================================================
-- USERS (RBAC)
-- ============================================================
CREATE TABLE IF NOT EXISTS Users (
  UserID      SERIAL PRIMARY KEY,
  EmployeeID  INT REFERENCES Employee(EmployeeID),
  email       TEXT UNIQUE NOT NULL,
  role        VARCHAR(30) NOT NULL,
  is_active   BOOLEAN DEFAULT true,
  last_login  TIMESTAMP,
  created_at  TIMESTAMP DEFAULT now()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_case_district    ON CaseMaster(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_case_date        ON CaseMaster(CrimeRegisteredDate);
CREATE INDEX IF NOT EXISTS idx_case_status      ON CaseMaster(CaseStatusID);
CREATE INDEX IF NOT EXISTS idx_case_crimehead   ON CaseMaster(CrimeMajorHeadID);
CREATE INDEX IF NOT EXISTS idx_accused_case     ON Accused(CaseMasterID);
CREATE INDEX IF NOT EXISTS idx_victim_case      ON Victim(CaseMasterID);
CREATE INDEX IF NOT EXISTS idx_arrest_case      ON ArrestSurrender(CaseMasterID);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON AuditLog(created_at);

-- Vector index for MO similarity search
CREATE INDEX IF NOT EXISTS idx_mo_embedding
  ON CaseMaster USING ivfflat (mo_embedding vector_cosine_ops)
  WITH (lists = 10);

SELECT 'KSP Real Schema created successfully' AS status;
