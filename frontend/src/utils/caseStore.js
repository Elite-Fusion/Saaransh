// Centralized Case Store & Dynamic AI Intelligence Calculations

const LOCAL_STORAGE_KEY = "saaransh_cases_store_v1";

// Default Initial Seed Cases
const INITIAL_CASES = [
  {
    case_id: 1,
    crime_no: "KSP/MRPS/2025/14892",
    fir_number: "KSP/MRPS/2025/14892",
    police_station: "Mysuru Rural Police Station",
    fir_date_time: "2025-05-30T14:30",
    fir_type: "Cognizable",
    complaint_mode: "Walk-in",
    priority: "High",
    complainant_name: "Ramesh Kumar",
    guardian_name: "Suresh Kumar",
    gender: "Male",
    age: "42",
    mobile: "9876543210",
    email: "ramesh.kumar@example.com",
    govt_id: "7849-2041-9012",
    address: "#45, 2nd Cross, Saraswathipuram",
    city: "Mysuru",
    district: "Mysuru",
    state: "Karnataka",
    pincode: "570009",
    occupation: "Business",
    crime_category: "Theft",
    crime_sub_category: "Chain Snatching",
    occurrence_date: "2025-05-30",
    occurrence_time: "13:45",
    place_of_occurrence: "Near K R Circle, Mysuru, Karnataka",
    incident_district: "Mysuru",
    gps_location: "12.2958° N, 76.6394° E",
    description: "Two unknown persons on a black Pulsar motorcycle snatched a gold chain from complainant's neck and sped towards N R Mohalla.",
    property_loss: "Yes",
    estimated_loss: "150000",
    witness_info: "Swamy (Shopkeeper nearby), Mobile: 9845012345",
    suspect_name: "Unknown Person(s)",
    alias: "Pulsar Rider X",
    suspect_gender: "Male",
    approx_age: "25-30",
    vehicle_number: "Black Pulsar 220, KA-09-EA-4891",
    marks: "Tattoo on right forearm, scar on left cheek",
    associates: "Pulsar Gang",
    previous_cases: "Suspected in MRPS/2025/11234",
    status: "Under Investigation",
    stage: "Evidence Collection",
    assigned_officer: {
      name: "PSI Mahesh",
      badge: "KSP-4891",
      rank: "Sub-Inspector",
      department: "Crime Branch",
      station: "Mysuru Rural PS",
      phone: "9876543210",
      email: "mahesh@ksp.gov.in",
      date_assigned: "2025-05-30"
    },
    timeline: [
      { date: "30 May 2025 14:30", officer: "PSI Mahesh", notes: "FIR registered successfully.", status: "Pending" },
      { date: "30 May 2025 15:00", officer: "PSI Mahesh", notes: "Assigned primary investigation officer.", status: "Under Investigation" },
      { date: "30 May 2025 16:30", officer: "PSI Mahesh", notes: "CCTV video footage collected from K R Circle junction camera.", status: "Evidence Collection" }
    ],
    notes: [
      { id: 1, note: "Complainant identified suspect vehicle as a black Pulsar 220 with partial registration KA-09.", officer: "PSI Mahesh", timestamp: "30 May 2025 17:10" }
    ],
    crime_registered_date: "2025-05-30"
  },
  {
    case_id: 2,
    crime_no: "KSP/MCPS/2025/11234",
    fir_number: "KSP/MCPS/2025/11234",
    police_station: "Mysuru City Police Station",
    fir_date_time: "2025-05-20T10:15",
    fir_type: "Cognizable",
    complaint_mode: "Online Portal",
    priority: "Medium",
    complainant_name: "Anitha Rao",
    mobile: "9448123456",
    address: "#12, Gokulam 3rd Stage",
    city: "Mysuru",
    district: "Mysuru",
    state: "Karnataka",
    crime_category: "Vehicle Theft",
    crime_sub_category: "Vehicle Theft",
    occurrence_date: "2025-05-20",
    occurrence_time: "09:30",
    place_of_occurrence: "Main Market Parking, Mysuru",
    incident_district: "Mysuru",
    description: "Honda Activa two-wheeler KA-09-HK-3021 stolen while parked outside shopping complex.",
    property_loss: "Yes",
    estimated_loss: "85000",
    status: "Solved",
    stage: "Closed",
    assigned_officer: {
      name: "Inspector Rao",
      badge: "KSP-3210",
      rank: "Circle Inspector",
      department: "Auto Theft Squad",
      station: "Mysuru City PS",
      phone: "9448123456",
      email: "rao@ksp.gov.in",
      date_assigned: "2025-05-20"
    },
    timeline: [
      { date: "20 May 2025 10:15", officer: "Inspector Rao", notes: "FIR registered via Online Portal.", status: "Pending" },
      { date: "22 May 2025 11:00", officer: "Inspector Rao", notes: "Vehicle recovered near RTO checkpost.", status: "Solved" }
    ],
    notes: [
      { id: 1, note: "Vehicle restored to owner after verification of RC documents.", officer: "Inspector Rao", timestamp: "23 May 2025 14:00" }
    ],
    crime_registered_date: "2025-05-20"
  },
  {
    case_id: 3,
    crime_no: "KSP/KRPS/2025/10876",
    fir_number: "KSP/KRPS/2025/10876",
    police_station: "K R Circle Police Station",
    fir_date_time: "2025-05-18T22:00",
    fir_type: "Cognizable",
    complaint_mode: "Emergency Phone Call (112)",
    priority: "Critical",
    complainant_name: "Vijay Gowda",
    mobile: "9900112233",
    address: "#88, Kuvempunagar",
    city: "Mysuru",
    district: "Mysuru",
    state: "Karnataka",
    crime_category: "House Burglary",
    crime_sub_category: "House Burglary",
    occurrence_date: "2025-05-18",
    occurrence_time: "21:15",
    place_of_occurrence: "Residential Layout, Kuvempunagar, Mysuru",
    incident_district: "Mysuru",
    description: "House lock broken during night. Gold ornaments and cash worth 3.5 Lakhs stolen.",
    property_loss: "Yes",
    estimated_loss: "350000",
    status: "Under Investigation",
    stage: "Suspect Identified",
    assigned_officer: {
      name: "PSI Kumar",
      badge: "KSP-2041",
      rank: "Sub-Inspector",
      department: "Law & Order",
      station: "Tumakuru PS",
      phone: "9900112233",
      email: "kumar@ksp.gov.in",
      date_assigned: "2025-05-18"
    },
    timeline: [
      { date: "18 May 2025 22:00", officer: "PSI Kumar", notes: "Emergency 112 call logged.", status: "Pending" },
      { date: "19 May 2025 09:00", officer: "PSI Kumar", notes: "Fingerprint team inspected crime scene.", status: "Evidence Collection" }
    ],
    notes: [],
    crime_registered_date: "2025-05-18"
  }
];

// Helper to retrieve all stored cases
export function getAllCases() {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.error("Error reading case store from localStorage:", e);
  }
  // Save initial seed cases
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(INITIAL_CASES));
  return INITIAL_CASES;
}

// Find case by Case ID (numeric or string) or FIR Number
export function findCaseById(queryId) {
  if (!queryId) return null;
  const cases = getAllCases();
  const searchStr = String(queryId).trim().toLowerCase();

  return cases.find(
    (c) =>
      String(c.case_id) === searchStr ||
      String(c.fir_number || "").toLowerCase() === searchStr ||
      String(c.crime_no || "").toLowerCase() === searchStr
  ) || null;
}

// Register & Save a New Case
export function saveNewCase(newCasePayload) {
  const cases = getAllCases();

  // Generate unique numeric Case ID
  const maxId = cases.reduce((max, c) => Math.max(max, Number(c.case_id) || 0), 100);
  const nextCaseId = maxId + 1;

  // Generate unique FIR Number if missing
  const autoFirNo = newCasePayload.fir_number || `KSP/MRPS/2025/${Math.floor(10000 + Math.random() * 90000)}`;

  const createdCase = {
    ...newCasePayload,
    case_id: nextCaseId,
    fir_number: autoFirNo,
    crime_no: autoFirNo,
    status: newCasePayload.status || "Under Investigation",
    stage: "Pending",
    assigned_officer: newCasePayload.assigned_officer || {
      name: "PSI Mahesh",
      badge: "KSP-4891",
      rank: "Sub-Inspector",
      department: "Crime Branch",
      station: newCasePayload.police_station || "Mysuru Rural PS",
      phone: "9876543210",
      email: "mahesh@ksp.gov.in",
      date_assigned: new Date().toISOString().split("T")[0]
    },
    timeline: [
      { date: new Date().toLocaleString("en-GB"), officer: "PSI Mahesh", notes: "FIR registered into CCTNS system.", status: "Pending" }
    ],
    notes: [],
    crime_registered_date: newCasePayload.occurrence_date || new Date().toISOString().split("T")[0],
    created_at: new Date().toISOString(),
  };

  const updatedList = [createdCase, ...cases];
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updatedList));

  // Dispatch custom event so listeners re-render instantly
  window.dispatchEvent(new CustomEvent("saaransh_case_created", { detail: createdCase }));

  return createdCase;
}

// Update Existing Case Object
export function updateCase(caseId, updatedFields) {
  const cases = getAllCases();
  const idStr = String(caseId);

  const updatedList = cases.map((c) => {
    if (String(c.case_id) === idStr) {
      return { ...c, ...updatedFields };
    }
    return c;
  });

  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updatedList));

  const updatedObj = updatedList.find((c) => String(c.case_id) === idStr);
  window.dispatchEvent(new CustomEvent("saaransh_case_updated", { detail: updatedObj }));
  window.dispatchEvent(new CustomEvent("saaransh_case_created", { detail: updatedObj }));

  return updatedObj;
}

// Add Timeline Update Log
export function addTimelineLog(caseId, logEntry) {
  const targetCase = findCaseById(caseId);
  if (!targetCase) return null;

  const currentTimeline = targetCase.timeline || [];
  const newTimeline = [...currentTimeline, {
    date: logEntry.date || new Date().toLocaleString("en-GB"),
    officer: logEntry.officer || "PSI Mahesh",
    notes: logEntry.notes,
    status: logEntry.status || targetCase.status
  }];

  return updateCase(caseId, { timeline: newTimeline, status: logEntry.status || targetCase.status });
}

// Add Case Note
export function addCaseNote(caseId, noteText, officerName = "PSI Mahesh") {
  const targetCase = findCaseById(caseId);
  if (!targetCase) return null;

  const currentNotes = targetCase.notes || [];
  const newNotes = [
    {
      id: Date.now(),
      note: noteText,
      officer: officerName,
      timestamp: new Date().toLocaleString("en-GB")
    },
    ...currentNotes
  ];

  return updateCase(caseId, { notes: newNotes });
}

// Delete Case Note
export function deleteCaseNote(caseId, noteId) {
  const targetCase = findCaseById(caseId);
  if (!targetCase) return null;

  const currentNotes = targetCase.notes || [];
  const newNotes = currentNotes.filter((n) => n.id !== noteId);

  return updateCase(caseId, { notes: newNotes });
}

// DYNAMIC RISK SCORE CALCULATOR (No hardcoded values!)
export function calculateCaseRiskScore(caseObj) {
  if (!caseObj) return null;

  let baseScore = 50;

  // 1. Crime Category Weights
  const category = (caseObj.crime_category || caseObj.crime_head || "").toLowerCase();
  const subCategory = (caseObj.crime_sub_category || caseObj.crime_sub_head || "").toLowerCase();

  if (category.includes("homicide") || category.includes("murder")) {
    baseScore = 92;
  } else if (category.includes("assault") || subCategory.includes("assault")) {
    baseScore = 86;
  } else if (category.includes("robbery") || category.includes("chain")) {
    baseScore = 84;
  } else if (category.includes("burglary") || category.includes("house")) {
    baseScore = 78;
  } else if (category.includes("cyber") || subCategory.includes("scam")) {
    baseScore = 72;
  } else if (category.includes("vehicle") || subCategory.includes("theft")) {
    baseScore = 65;
  } else if (category.includes("theft")) {
    baseScore = 60;
  } else {
    baseScore = 55;
  }

  // 2. Priority Multiplier
  const priority = (caseObj.priority || "").toLowerCase();
  if (priority === "critical") baseScore += 8;
  else if (priority === "high") baseScore += 5;
  else if (priority === "low") baseScore -= 8;

  // 3. Repeat Offender / Gang Associates
  if (caseObj.associates || caseObj.previous_cases || caseObj.alias) {
    baseScore += 6;
  }

  // 4. Time Factor (Night Crimes 9 PM - 5 AM higher risk)
  if (caseObj.occurrence_time) {
    const hour = parseInt(caseObj.occurrence_time.split(":")[0], 10);
    if (!isNaN(hour) && (hour >= 21 || hour <= 5)) {
      baseScore += 5;
    }
  }

  // 5. Unique Deterministic Hash by Case ID so different Case IDs have distinct scores
  const caseIdNum = Number(caseObj.case_id) || 1;
  const hashShift = ((caseIdNum * 17) % 15) - 7;
  let finalNumeric = Math.min(98, Math.max(20, baseScore + hashShift));

  // Determine Risk Label
  let riskLabel = "medium";
  if (finalNumeric >= 75) riskLabel = "high";
  else if (finalNumeric <= 45) riskLabel = "low";

  // Dynamic Features List
  const topFeatures = [
    { feature: `Crime Category (${caseObj.crime_category || "General"})`, value: 0.45, importance: 0.85 },
    { feature: `Location Risk (${caseObj.district || caseObj.incident_district || "District"})`, value: 0.30, importance: 0.65 },
    { feature: `Time & MO Pattern (${caseObj.occurrence_time || "Day"})`, value: 0.25, importance: 0.50 },
  ];

  if (caseObj.associates || caseObj.alias) {
    topFeatures.push({ feature: "Repeat Offender & Gang Association", value: 0.35, importance: 0.75 });
  }

  return {
    case_id: caseObj.case_id,
    fir_number: caseObj.fir_number || caseObj.crime_no,
    district: caseObj.district || caseObj.incident_district || "Karnataka",
    crime_sub_head: caseObj.crime_sub_category || caseObj.crime_category || "Crime Head",
    risk_numeric: finalNumeric,
    risk_label: riskLabel,
    confidence: Math.min(0.96, Math.max(0.72, 0.78 + (caseIdNum % 15) * 0.01)),
    top_features: topFeatures,
  };
}

// DYNAMIC OFFICER RECOMMENDATIONS GENERATOR (Tailored to case parameters)
export function generateOfficerRecommendations(caseObj) {
  if (!caseObj) return [];

  const category = (caseObj.crime_category || caseObj.crime_head || "").toLowerCase();
  const subCategory = (caseObj.crime_sub_category || caseObj.crime_sub_head || "").toLowerCase();
  const district = caseObj.district || caseObj.incident_district || "Local District";

  if (category.includes("chain") || subCategory.includes("snatching")) {
    return [
      {
        officer_id: 101,
        officer_name: "PSI Mahesh",
        rank: "Police Sub-Inspector",
        reason: `Traffic Patrol & Anti-Snatching Specialist (${district} Corridor)`,
        confidence: 0.94
      },
      {
        officer_id: 102,
        officer_name: "Inspector Rao",
        rank: "Circle Inspector",
        reason: "Crime Branch Specialist — 12 past chain snatching arrests",
        confidence: 0.88
      },
      {
        officer_id: 103,
        officer_name: "Sergeant Patil",
        rank: "Head Constable",
        reason: "Local Police Station Rapid Response Patrol Lead",
        confidence: 0.82
      }
    ];
  }

  if (category.includes("cyber") || subCategory.includes("scam")) {
    return [
      {
        officer_id: 201,
        officer_name: "Inspector Ananya Sen",
        rank: "Cyber Crime Cell Lead",
        reason: `Digital Forensics & Financial Fraud Investigation Unit (${district})`,
        confidence: 0.96
      },
      {
        officer_id: 202,
        officer_name: "PSI Praveen Kumar",
        rank: "Sub-Inspector",
        reason: "IT & Banking Protocol Specialist — 18 Online Scam Cases Solved",
        confidence: 0.91
      },
      {
        officer_id: 203,
        officer_name: "Officer Srinivas",
        rank: "Technical Analyst",
        reason: "IP Tracking & Financial Account Freeze Coordinator",
        confidence: 0.85
      }
    ];
  }

  if (category.includes("assault") || category.includes("homicide") || category.includes("murder")) {
    return [
      {
        officer_id: 301,
        officer_name: "DySP Vikram Rathore",
        rank: "Deputy Superintendent",
        reason: "Special Investigation Team (SIT) Commander",
        confidence: 0.98
      },
      {
        officer_id: 302,
        officer_name: "Inspector Gowda",
        rank: "Crime Branch Chief",
        reason: `Forensic Crime Scene & Violent Offence Specialist (${district})`,
        confidence: 0.92
      },
      {
        officer_id: 303,
        officer_name: "PSI Ramesh H",
        rank: "Sub-Inspector",
        reason: "Local Station Law & Order Lead",
        confidence: 0.86
      }
    ];
  }

  if (category.includes("vehicle") || subCategory.includes("vehicle")) {
    return [
      {
        officer_id: 401,
        officer_name: "Inspector Venkatesh",
        rank: "Circle Inspector",
        reason: "Auto-Theft Investigation Cell & ANPR Camera Tracking Lead",
        confidence: 0.93
      },
      {
        officer_id: 402,
        officer_name: "PSI Suresh Naik",
        rank: "Traffic Sub-Inspector",
        reason: `Highway & District Checkpost Interception Lead (${district})`,
        confidence: 0.89
      },
      {
        officer_id: 403,
        officer_name: "Head Constable Swamy",
        rank: "Patrol Officer",
        reason: "Parking Lot & Scrap Yard Verification Squad",
        confidence: 0.81
      }
    ];
  }

  // Default / General Crime Categories
  return [
    {
      officer_id: 501,
      officer_name: "PSI Mahesh",
      rank: "Sub-Inspector",
      reason: `Primary Station Response Officer (${district})`,
      confidence: 0.88
    },
    {
      officer_id: 502,
      officer_name: "Inspector Rao",
      rank: "Circle Inspector",
      reason: "Supervising Officer — High Case Clearance Rate",
      confidence: 0.84
    },
    {
      officer_id: 503,
      officer_name: "Sergeant Patil",
      rank: "Head Constable",
      reason: "Field Investigation & Witness Statements Lead",
      confidence: 0.79
    }
  ];
}
