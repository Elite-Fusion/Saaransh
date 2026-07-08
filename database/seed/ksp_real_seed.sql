-- ============================================================
--  KSP DATATHON — Seed Data (matching real KSP schema)
--  Run AFTER ksp_real_schema.sql
-- ============================================================

-- STATE
INSERT INTO State (StateID, StateName, Active) VALUES (1, 'Karnataka', true) ON CONFLICT DO NOTHING;

-- DISTRICTS
INSERT INTO District (DistrictID, DistrictName, StateID, Active) VALUES
  (1, 'Bengaluru Urban', 1, true),
  (2, 'Mysuru',          1, true),
  (3, 'Dharwad',         1, true),
  (4, 'Dakshina Kannada',1, true),
  (5, 'Belagavi',        1, true),
  (6, 'Shivamogga',      1, true),
  (7, 'Kalaburagi',      1, true),
  (8, 'Tumakuru',        1, true)
ON CONFLICT DO NOTHING;

-- UNIT TYPES
INSERT INTO UnitType (UnitTypeID, UnitTypeName, CityDistState, Hierarchy, Active) VALUES
  (1, 'Police Station', 'City',     3, true),
  (2, 'Circle Office',  'District', 2, true),
  (3, 'SP Office',      'District', 1, true)
ON CONFLICT DO NOTHING;

-- UNITS (Police Stations)
INSERT INTO Unit (UnitID, UnitName, TypeID, StateID, DistrictID, latitude, longitude, Active) VALUES
  (1, 'Mysuru City North PS',    1, 1, 2, 12.2958, 76.6394, true),
  (2, 'Bengaluru Whitefield PS', 1, 1, 1, 12.9698, 77.7500, true),
  (3, 'Hubballi East PS',        1, 1, 3, 15.3647, 75.1240, true),
  (4, 'Mangaluru Port PS',       1, 1, 4, 12.8714, 74.8431, true),
  (5, 'Belagavi Central PS',     1, 1, 5, 15.8497, 74.4977, true),
  (6, 'Shivamogga Town PS',      1, 1, 6, 13.9299, 75.5681, true),
  (7, 'Kalaburagi Rural PS',     1, 1, 7, 17.3297, 76.8200, true),
  (8, 'Tumakuru East PS',        1, 1, 8, 13.3379, 77.1173, true)
ON CONFLICT DO NOTHING;

-- RANKS
INSERT INTO Rank (RankID, RankName, Hierarchy, Active) VALUES
  (1, 'DGP',        1, true),
  (2, 'ADGP',       2, true),
  (3, 'IGP',        3, true),
  (4, 'DIG',        4, true),
  (5, 'SP',         5, true),
  (6, 'DSP',        6, true),
  (7, 'Inspector',  7, true),
  (8, 'PSI',        8, true),
  (9, 'SI',         9, true),
  (10,'HC',        10, true),
  (11,'Constable', 11, true)
ON CONFLICT DO NOTHING;

-- DESIGNATIONS
INSERT INTO Designation (DesignationID, DesignationName, SortOrder, Active) VALUES
  (1, 'Investigating Officer', 1, true),
  (2, 'Station House Officer', 2, true),
  (3, 'Circle Inspector',      3, true)
ON CONFLICT DO NOTHING;

-- EMPLOYEES (Officers)
INSERT INTO Employee (EmployeeID, DistrictID, UnitID, RankID, DesignationID, KGID, FirstName, GenderID) VALUES
  (1, 2, 1, 7, 2, 'KG-MYS-001', 'Rajesh Kumar M',   1),
  (2, 1, 2, 8, 1, 'KG-BLR-002', 'Priya Nair S',     2),
  (3, 3, 3, 9, 1, 'KG-HBL-003', 'Suresh Patil K',   1),
  (4, 4, 4, 7, 2, 'KG-MNG-004', 'Anitha Shetty R',  2),
  (5, 5, 5, 11,1, 'KG-BLG-005', 'Manoj Gowda T',    1),
  (6, 6, 6, 8, 1, 'KG-SMG-006', 'Kavitha Reddy N',  2),
  (7, 7, 7, 7, 2, 'KG-KLG-007', 'Ibrahim Khan S',   1),
  (8, 8, 8, 9, 1, 'KG-TMK-008', 'Deepa Murthy B',   2)
ON CONFLICT DO NOTHING;

-- COURTS
INSERT INTO Court (CourtID, CourtName, DistrictID, StateID, Active) VALUES
  (1, 'City Civil Court Mysuru',     2, 1, true),
  (2, 'City Civil Court Bengaluru',  1, 1, true),
  (3, 'District Court Dharwad',      3, 1, true),
  (4, 'District Court DK',           4, 1, true),
  (5, 'District Court Belagavi',     5, 1, true)
ON CONFLICT DO NOTHING;

-- CASE CATEGORIES
INSERT INTO CaseCategory (CaseCategoryID, LookupValue) VALUES
  (1, 'FIR'), (2, 'UDR'), (3, 'PAR'), (4, 'Zero FIR')
ON CONFLICT DO NOTHING;

-- GRAVITY
INSERT INTO GravityOffence (GravityOffenceID, LookupValue) VALUES
  (1, 'Heinous'), (2, 'Non-Heinous'), (3, 'Minor')
ON CONFLICT DO NOTHING;

-- CASE STATUS
INSERT INTO CaseStatusMaster (CaseStatusID, CaseStatusName) VALUES
  (1, 'Open'),
  (2, 'Under Investigation'),
  (3, 'Charge Sheeted'),
  (4, 'Closed'),
  (5, 'Undetected')
ON CONFLICT DO NOTHING;

-- CRIME HEADS
INSERT INTO CrimeHead (CrimeHeadID, CrimeGroupName, Active) VALUES
  (1, 'Crimes Against Body',     true),
  (2, 'Crimes Against Property', true),
  (3, 'Crimes Against Women',    true),
  (4, 'Economic Offences',       true),
  (5, 'Drug Offences',           true),
  (6, 'Crimes Against Children', true)
ON CONFLICT DO NOTHING;

-- CRIME SUB HEADS
INSERT INTO CrimeSubHead (CrimeSubHeadID, CrimeHeadID, CrimeHeadName, SeqID) VALUES
  (1,  1, 'Murder',             1),
  (2,  1, 'Attempt to Murder',  2),
  (3,  1, 'Assault',            3),
  (4,  1, 'Robbery',            4),
  (5,  2, 'Theft',              1),
  (6,  2, 'Chain Snatching',    2),
  (7,  2, 'House Breaking',     3),
  (8,  2, 'Vehicle Theft',      4),
  (9,  2, 'Dacoity',            5),
  (10, 3, 'Domestic Violence',  1),
  (11, 3, 'Kidnapping',         2),
  (12, 4, 'Fraud',              1),
  (13, 4, 'ATM Skimming',       2),
  (14, 4, 'Cyber Fraud',        3),
  (15, 4, 'UPI Fraud',          4),
  (16, 5, 'Drug Possession',    1),
  (17, 5, 'Drug Trafficking',   2)
ON CONFLICT DO NOTHING;

-- ACTS
INSERT INTO Act (ActCode, ActDescription, ShortName, Active) VALUES
  ('IPC',   'Indian Penal Code 1860',                   'IPC',  true),
  ('BNS',   'Bharatiya Nyaya Sanhita 2023',             'BNS',  true),
  ('NDPS',  'Narcotic Drugs and Psychotropic Substances Act 1985', 'NDPS', true),
  ('IT',    'Information Technology Act 2000',           'IT',   true),
  ('DV',    'Protection of Women from Domestic Violence Act 2005', 'DV Act', true)
ON CONFLICT DO NOTHING;

-- SECTIONS
INSERT INTO Section (SectionCode, ActCode, SectionDescription, Active) VALUES
  ('302',   'IPC', 'Murder',                              true),
  ('307',   'IPC', 'Attempt to Murder',                   true),
  ('376',   'IPC', 'Rape',                                true),
  ('379',   'IPC', 'Theft',                               true),
  ('380',   'IPC', 'Theft in dwelling house',             true),
  ('392',   'IPC', 'Robbery',                             true),
  ('395',   'IPC', 'Dacoity',                             true),
  ('420',   'IPC', 'Cheating',                            true),
  ('498A',  'IPC', 'Cruelty by husband or relatives',     true),
  ('20',    'NDPS','Punishment for contravention of cannabis', true),
  ('21',    'NDPS','Punishment for contravention of manufactured drugs', true),
  ('66C',   'IT', 'Identity theft',                       true),
  ('66D',   'IT', 'Cheating by impersonation using computer resource', true)
ON CONFLICT DO NOTHING;

-- OCCUPATION MASTER
INSERT INTO OccupationMaster (OccupationID, OccupationName) VALUES
  (1,'Farmer'),(2,'Government Employee'),(3,'Private Employee'),
  (4,'Business'),(5,'Student'),(6,'Unemployed'),(7,'Daily Wage Worker')
ON CONFLICT DO NOTHING;

-- RELIGION MASTER
INSERT INTO ReligionMaster (ReligionID, ReligionName) VALUES
  (1,'Hindu'),(2,'Muslim'),(3,'Christian'),(4,'Jain'),(5,'Buddhist'),(6,'Other')
ON CONFLICT DO NOTHING;

-- CASTE MASTER
INSERT INTO CasteMaster (caste_master_id, caste_master_name) VALUES
  (1,'SC'),(2,'ST'),(3,'OBC'),(4,'General')
ON CONFLICT DO NOTHING;

-- CASE MASTER (30 cases)
INSERT INTO CaseMaster (CaseMasterID, CrimeNo, CaseNo, CrimeRegisteredDate, PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID, CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, IncidentFromDate, latitude, longitude, BriefFacts, is_series_crime, series_id) VALUES
  (1,  '104430001202400001','202400001','2024-01-15',1,1,1,2,2,6, 4,'2024-01-15 09:00:00',12.3052,76.6551,'Gold chain snatched from elderly woman near market. Suspect on motorcycle approached from behind.',true,1),
  (2,  '104430001202400019','202400019','2024-03-22',1,1,1,2,2,6, 2,'2024-03-22 09:45:00',12.3011,76.6489,'Gold chain snatched near temple. Two suspects on motorcycle.',true,1),
  (3,  '104430001202400047','202400047','2024-06-10',1,1,1,2,2,6, 1,'2024-06-10 08:20:00',12.2978,76.6423,'Chain snatching near palace road. Motorcycle-borne suspects escaped towards Bannimantap.',true,1),
  (4,  '104430002202400112','202400112','2024-02-03',2,2,1,2,4,13,4,'2024-02-01 23:00:00',12.9698,77.7499,'Skimming device found on ATM. Multiple accounts compromised.',true,2),
  (5,  '104430002202400198','202400198','2024-04-18',2,2,1,2,4,13,2,'2024-04-17 22:00:00',12.9762,77.7218,'Card skimmer installed on ATM near tech park with pinhole camera.',true,2),
  (6,  '104430002202400267','202400267','2024-07-29',2,2,1,2,4,13,1,'2024-07-28 21:30:00',12.9590,77.6974,'Multiple victims reported unauthorized ATM withdrawals.',true,2),
  (7,  '104430004202400034','202400034','2024-01-28',4,4,1,1,5,17,3,'2024-01-28 02:00:00',12.8658,74.8432,'10kg ganja seized from auto-rickshaw near port. Contraband hidden under false floor.',true,3),
  (8,  '104430004202400089','202400089','2024-03-15',4,4,1,1,5,17,2,'2024-03-15 03:00:00',12.8714,74.8400,'5kg brown sugar seized from hotel room. Interstate supply network suspected.',true,3),
  (9,  '104430003202400021','202400021','2024-02-14',3,3,1,1,2,9, 3,'2024-02-14 22:00:00',15.3700,75.1350,'Armed robbery of truck on NH48. 4 armed men looted cash at gunpoint.',false,NULL),
  (10, '104430005202400056','202400056','2024-03-01',5,5,1,2,1,3, 4,'2024-03-01 19:00:00',15.8520,74.4990,'Group assault over land dispute. 3 persons injured.',false,NULL),
  (11, '104430006202400078','202400078','2024-04-05',6,6,1,2,2,8, 1,'2024-04-04 23:00:00',13.9320,75.5700,'Two-wheeler stolen from residential area overnight.',false,NULL),
  (12, '104430007202400033','202400033','2024-01-20',7,7,1,1,1,1, 2,'2024-01-19 23:00:00',17.3350,76.8250,'Body found near Sedam Road with stab wounds. Money lending dispute suspected.',false,NULL),
  (13, '104430008202400044','202400044','2024-05-12',8,8,1,2,4,14,1,'2024-05-11 15:00:00',13.3400,77.1200,'Victim lost Rs 2.5 lakh in fake investment scheme via WhatsApp.',false,NULL),
  (14, '104430001202400088','202400088','2024-07-03',1,1,1,2,2,7, 2,'2024-07-03 02:00:00',12.3200,76.6550,'House burglary during night. Suspects broke window latch, stole gold jewellery.',false,NULL),
  (15, '104430002202400334','202400334','2024-06-22',2,2,1,3,5,16,3,'2024-06-22 13:30:00',12.9116,77.6400,'Ganja seized from suspect near park. 500g cannabis found.',false,NULL),
  (16, '104430003202400067','202400067','2024-05-30',3,3,1,2,2,4, 1,'2024-05-30 19:45:00',15.3600,75.1150,'Mobile phone snatched near bus stand.',false,NULL),
  (17, '104430004202400145','202400145','2024-04-25',4,4,1,2,3,10,4,'2024-04-25 20:30:00',12.8800,74.8500,'Domestic violence complaint. Victim reported repeated assault by husband.',false,NULL),
  (18, '104430005202400102','202400102','2024-06-08',5,5,1,2,4,12,2,'2024-06-01 00:00:00',15.8600,74.5050,'Fake land documents used to sell property to multiple buyers.',false,NULL),
  (19, '104430006202400091','202400091','2024-03-18',6,6,1,1,6,11,4,'2024-03-17 18:00:00',13.9400,75.5800,'Child abducted near school. Ransom of Rs 5 lakh demanded. Child recovered safely.',false,NULL),
  (20, '104430007202400071','202400071','2024-05-05',7,7,1,1,5,17,2,'2024-05-05 03:30:00',17.3400,76.8300,'2kg brown sugar in vegetable truck. Interstate nexus suspected.',false,NULL),
  (21, '104430008202400059','202400059','2024-02-28',8,8,1,2,2,5, 4,'2024-02-28 12:00:00',13.3360,77.1020,'10 bicycles stolen from cycle shop. Truck used for transportation.',false,NULL),
  (22, '104430001202400101','202400101','2024-04-12',1,1,1,1,2,9, 3,'2024-04-12 11:00:00',12.3100,76.6480,'Armed robbery at bank branch. Rs 8 lakh looted at gunpoint.',false,NULL),
  (23, '104430002202400421','202400421','2024-08-01',2,2,1,2,4,15,1,'2024-07-31 20:00:00',12.9352,77.6245,'Victim defrauded through fake UPI payment link. Rs 80,000 lost.',false,NULL),
  (24, '104430003202400098','202400098','2024-06-15',3,3,1,1,1,1, 3,'2024-06-14 22:30:00',15.3750,75.1400,'Murder over property dispute between brothers. Axe recovered.',false,NULL),
  (25, '104430004202400178','202400178','2024-05-19',4,4,1,2,2,5, 4,'2024-05-19 15:00:00',12.8750,74.8420,'3-member shoplifting gang caught at mall. Rs 50,000 goods recovered.',false,NULL),
  (26, '104430005202400134','202400134','2024-07-08',5,5,1,2,1,3, 4,'2024-07-08 16:45:00',15.8550,74.5100,'Road rage assault with iron rod on NH48.',false,NULL),
  (27, '104430006202400112','202400112','2024-07-20',6,6,1,2,4,12,1,'2024-07-15 00:00:00',13.9350,75.5750,'Fake job placement agency collected Rs 25,000 each from 12 victims.',false,NULL),
  (28, '104430007202400094','202400094','2024-06-28',7,7,1,2,2,5, 1,'2024-06-28 01:00:00',17.4620,77.4170,'5 cattle stolen from farm during night. Truck used.',false,NULL),
  (29, '104430008202400077','202400077','2024-07-14',8,8,1,1,5,17,3,'2024-07-14 15:30:00',13.3500,77.1400,'8kg ganja seized from house. 2 arrested. Andhra Pradesh supply route.',false,NULL),
  (30, '104430001202400134','202400134','2024-07-25',1,1,1,2,4,14,2,'2024-07-24 18:00:00',12.3150,76.6380,'Victim paid Rs 45,000 for laptop on fake e-commerce site.',false,NULL)
ON CONFLICT DO NOTHING;

-- ACCUSED
INSERT INTO Accused (AccusedMasterID, CaseMasterID, AccusedName, AgeYear, GenderID, PersonID, is_known_criminal, criminal_history) VALUES
  (1,  1,  'Sunil Kumar B',    28, 1, 'A1', true,  'Chain snatching 2020, 2022'),
  (2,  2,  'Sunil Kumar B',    28, 1, 'A1', true,  'Chain snatching 2020, 2022'),
  (3,  3,  'Ravi Shankar D',   34, 1, 'A1', true,  'Theft cases 2019, 2021'),
  (4,  7,  'Faisal Ahmed K',   36, 1, 'A1', true,  'Drug trafficking 2021'),
  (5,  8,  'Faisal Ahmed K',   36, 1, 'A1', true,  'Drug trafficking 2021'),
  (6,  9,  'Mahesh Naik T',    41, 1, 'A1', false, NULL),
  (7,  12, 'Naveen Gowda S',   31, 1, 'A1', true,  'Robbery 2020'),
  (8,  14, 'Ravi Shankar D',   34, 1, 'A1', true,  'Theft cases 2019, 2021'),
  (9,  22, 'Abdul Rehman S',   38, 1, 'A1', true,  'Assault 2019, Drug 2022'),
  (10, 24, 'Girish Hegde N',   29, 1, 'A1', false, NULL)
ON CONFLICT DO NOTHING;

-- VICTIMS
INSERT INTO Victim (VictimMasterID, CaseMasterID, VictimName, AgeYear, GenderID) VALUES
  (1,  1,  'Lakshmi Devi R',  52, 2),
  (2,  9,  'Truck Driver - Ramanna', 35, 1),
  (3,  12, 'Shiva Kumar R',   45, 1),
  (4,  17, 'Sumitra Nayak K', 33, 2),
  (5,  19, 'Child - Akash',    8, 1),
  (6,  22, 'Bank Manager - Prakash', 42, 1),
  (7,  24, 'Nagaraj Hegde',   55, 1)
ON CONFLICT DO NOTHING;

-- ACT-SECTION ASSOCIATIONS
INSERT INTO ActSectionAssociation (CaseMasterID, ActID, SectionID, ActOrderID, SectionOrderID) VALUES
  (1,  'IPC', '379',  1, 1),
  (2,  'IPC', '379',  1, 1),
  (3,  'IPC', '379',  1, 1),
  (7,  'NDPS','20',   1, 1),
  (8,  'NDPS','21',   1, 1),
  (9,  'IPC', '395',  1, 1),
  (12, 'IPC', '302',  1, 1),
  (13, 'IT',  '66D',  1, 1),
  (15, 'NDPS','20',   1, 1),
  (17, 'IPC', '498A', 1, 1),
  (22, 'IPC', '392',  1, 1),
  (23, 'IT',  '66C',  1, 1),
  (24, 'IPC', '302',  1, 1)
ON CONFLICT DO NOTHING;

-- ARREST / SURRENDER
INSERT INTO ArrestSurrender (CaseMasterID, ArrestSurrenderTypeID, ArrestSurrenderDate, PoliceStationID, IOID, AccusedMasterID, IsAccused) VALUES
  (1,  1, '2024-01-20', 1, 1, 1, true),
  (7,  1, '2024-01-28', 4, 4, 4, true),
  (8,  1, '2024-03-15', 4, 4, 5, true),
  (9,  1, '2024-02-16', 3, 3, 6, true),
  (22, 1, '2024-04-13', 1, 1, 9, true),
  (24, 1, '2024-06-15', 3, 3, 10,true)
ON CONFLICT DO NOTHING;

-- CHARGESHEETED CASES
INSERT INTO ChargesheetDetails (CaseMasterID, csdate, cstype, PolicePersonID) VALUES
  (7,  '2024-03-01', 'A', 4),
  (9,  '2024-04-10', 'A', 3),
  (15, '2024-08-01', 'A', 2),
  (22, '2024-06-01', 'A', 1),
  (24, '2024-08-10', 'A', 3),
  (29, '2024-09-01', 'A', 8)
ON CONFLICT DO NOTHING;

-- USERS
INSERT INTO Users (EmployeeID, email, role) VALUES
  (1, 'rajesh.inspector@ksp.gov.in',  'inspector'),
  (2, 'priya.psi@ksp.gov.in',         'si'),
  (3, 'suresh.si@ksp.gov.in',         'si'),
  (4, 'anitha.inspector@ksp.gov.in',  'inspector'),
  (7, 'ibrahim.inspector@ksp.gov.in', 'inspector'),
  (8, 'deepa.si@ksp.gov.in',          'si')
ON CONFLICT DO NOTHING;

SELECT
  'Seed complete' AS status,
  (SELECT COUNT(*) FROM CaseMaster)  AS total_cases,
  (SELECT COUNT(*) FROM Accused)     AS total_accused,
  (SELECT COUNT(*) FROM Victim)      AS total_victims,
  (SELECT COUNT(*) FROM Employee)    AS total_officers;
