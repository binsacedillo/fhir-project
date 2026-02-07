"use client";

import { useState } from "react";
import { fetchPatientData, fetchAllergies, fetchMedications, checkPrescriptionSafety } from "./services/fhirApi";
import styles from "./page.module.css";
import { Patient, AllergyIntolerance, MedicationStatement } from "./services/types";
import Image from "next/image";
import Spinner from "../components/Spinner";

export default function PatientDashboard() {
  // Patient search state/hooks must be inside the component
  const [searchName, setSearchName] = useState("");
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [searching, setSearching] = useState(false);

  // FHIR Patient search by name or ID (returns Bundle)
  async function searchPatients(query: string) {
    setSearching(true);
    setError("");
    setSearchResults([]);
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const params = new URLSearchParams();
      if (query) {
        // Simple UUID v4 regex: 8-4-4-4-12 hex digits
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(query.trim())) {
          params.append("_id", query.trim());
        } else {
          params.append("name", query);
        }
      }
      const res = await fetch(`${API_URL}/search-patients?${params.toString()}`);
      const data = await res.json();
      const patients: Patient[] = data.entry?.map((e: { resource: Patient }) => e.resource) || [];
      setSearchResults(patients);
    } catch {
      setError("Error searching patients");
    } finally {
      setSearching(false);
    }
  }
  const [patientId, setPatientId] = useState("");
  const [patientData, setPatientData] = useState<Patient | null>(null);
  const [allergies, setAllergies] = useState<AllergyIntolerance[]>([]);
  const [medications, setMedications] = useState<MedicationStatement[]>([]);
  const [medicationName, setMedicationName] = useState("");
  const [safetyResult, setSafetyResult] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [safetyLoading, setSafetyLoading] = useState(false);

  const fetchPatient = async () => {
    setLoading(true);
    setError("");
    setPatientData(null);
    setAllergies([]);
    setMedications([]);
    setMedicationName("");
    setSafetyResult("");
    try {
      const patient = await fetchPatientData(patientId);
      setPatientData(patient);
      const allergyData = await fetchAllergies(patientId);
      setAllergies(allergyData);
      const medicationData = await fetchMedications(patientId);
      setMedications(medicationData);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(String(err));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.gridContainer}>
        <main className={styles.main}>
          <header className={styles.dashboardHeader}>
            <Image src="/logo.png" alt="System Logo" width={72} height={72} style={{ objectFit: "contain", marginBottom: 16 }} priority />
            <div className={styles.dashboardHeaderTitleContainer}>
              <h1 style={{ fontSize: "2.2rem", letterSpacing: "-1px" }}>Patient Safety Guardrail Dashboard</h1>
            </div>
            <p style={{ color: "#64748b", fontSize: "1.1rem", marginTop: "0.5em" }}>
              A modern FHIR-based dashboard for safe prescription management.
            </p>
          </header>
          <div className={styles.dashboardContainer}>
            <section className={styles.dashboardSection}>
              <h2 className={styles.dashboardSectionHeader}>Patient Search</h2>
              <div className={styles.formRow}>
                <input
                  className={styles.formInput}
                  type="text"
                  placeholder="Search by patient name or ID (e.g. John Smith or 4a704b3d...)"
                  value={searchName}
                  onChange={e => setSearchName(e.target.value)}
                />
                <button
                  className={styles.formButton}
                  type="button"
                  onClick={() => searchPatients(searchName)}
                  disabled={searching || !searchName}
                >
                  {searching ? <Spinner size={20} /> : "Search"}
                </button>
                <button
                  className={styles.formButton}
                  type="button"
                  onClick={() => {
                    setSearchName("");
                    setSearchResults([]);
                    setPatientId("");
                    setPatientData(null);
                    setAllergies([]);
                    setMedications([]);
                    setMedicationName("");
                    setSafetyResult("");
                    setError("");
                  }}
                  disabled={searching && !searchName}
                >
                  Clear
                </button>
              </div>
              {searchResults.length > 0 && (
                <div style={{ margin: "8px 0 20px 0", display: "flex", alignItems: "center" }}>
                  <label htmlFor="patient-select"><strong>Select Patient:</strong></label>
                  <select
                    id="patient-select"
                    className={styles.formInput}
                    style={{ marginLeft: 8, minWidth: 220 }}
                    value={patientId}
                    onChange={e => setPatientId(e.target.value)}
                  >
                    <option value="">-- Choose --</option>
                    {searchResults.map((p: Patient) => (
                      <option key={p.id} value={p.id}>
                        {p.name?.[0]?.text || `${p.name?.[0]?.given?.join(" ") || ""} ${p.name?.[0]?.family || ""}`.trim() || "No Name"} (ID: {p.id})
                      </option>
                    ))}
                  </select>
                  <button
                    className={styles.formButton}
                    style={{ marginLeft: 8 }}
                    onClick={fetchPatient}
                    disabled={loading || !patientId}
                  >
                    {loading ? <Spinner size={20} /> : "Fetch Patient"}
                  </button>
                </div>
              )}
              {error && <div style={{ color: "red" }}>{error}</div>}
              {patientData && (
                <div style={{ background: "#f0f4ff", border: "1px solid #b3e0ff", color: "#222", padding: "1.2em", marginTop: "1em", borderRadius: "10px", maxWidth: "400px" }}>
                  <h3 style={{ marginBottom: "0.5em" }}>Patient Info</h3>
                  <div><strong>ID:</strong> {patientData.id}</div>
                  <div><strong>Identifier:</strong> {patientData.identifier?.[0]?.value || "N/A"}</div>
                  <div><strong>Name:</strong> {patientData.name?.[0]?.text || `${patientData.name?.[0]?.given?.join(" ") || ""} ${patientData.name?.[0]?.family || ""}`.trim() || "N/A"}</div>
                  <div><strong>Birthdate:</strong> {patientData.birthDate || "N/A"}</div>
                  <div><strong>Active:</strong> {patientData.active ? "Yes" : "No"}</div>
                </div>
              )}
            </section>
            <section className={styles.dashboardSection}>
              <h2 className={styles.dashboardSectionHeader}>Allergies</h2>
              {/* Allergy data is fetched using the main patient ID. */}
              {allergies.length === 0 && <div style={{ color: "#64748b" }}>No allergies found.</div>}
              {allergies.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "1.2em" }}>
                  {allergies.map((allergy, idx) => (
                    <div key={idx} style={{ background: "#fffbe6", boxShadow: "0 2px 8px rgba(255, 215, 0, 0.07)", border: "1px solid #ffe58f", color: "#222", padding: "1em", borderRadius: "10px", minWidth: "220px", display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                      <span style={{ fontSize: "1.5em", marginBottom: "0.3em" }} role="img" aria-label="allergy">⚠️</span>
                      <strong>Substance:</strong> <span style={{ background: "#ffe58f", borderRadius: "4px", padding: "2px 8px", marginLeft: "4px" }}>{allergy.code?.text || allergy.code?.coding?.[0]?.display || "Unknown"}</span><br />
                      <strong>Criticality:</strong> <span style={{ background: "#fef3c7", borderRadius: "4px", padding: "2px 8px", marginLeft: "4px" }}>{allergy.criticality || "N/A"}</span><br />
                      <strong>Type:</strong> <span style={{ background: "#f3e8ff", borderRadius: "4px", padding: "2px 8px", marginLeft: "4px" }}>{allergy.type || "N/A"}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
            <section className={styles.dashboardSection}>
              <h2 className={styles.dashboardSectionHeader}>Medications</h2>
              {/* Medication data is fetched using the main patient ID. */}
              {medications.length === 0 && <div style={{ color: "#64748b" }}>No medications found.</div>}
              {medications.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "1.2em" }}>
                  {medications.map((med, idx) => (
                    <div key={idx} style={{ background: "#e6ffe6", boxShadow: "0 2px 8px rgba(56, 161, 105, 0.07)", border: "1px solid #b7eb8f", color: "#222", padding: "1em", borderRadius: "10px", minWidth: "220px", display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                      <span style={{ fontSize: "1.5em", marginBottom: "0.3em" }} role="img" aria-label="medication">💊</span>
                      <strong>Medication:</strong> <span style={{ background: "#bbf7d0", borderRadius: "4px", padding: "2px 8px", marginLeft: "4px" }}>{med.medicationCodeableConcept?.text || med.medicationCodeableConcept?.coding?.[0]?.display || "Unknown"}</span><br />
                      <strong>Status:</strong> <span style={{ background: "#d1fae5", borderRadius: "4px", padding: "2px 8px", marginLeft: "4px" }}>{med.status || "N/A"}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>
            <section className={styles.dashboardSection}>
              <h2 className={styles.dashboardSectionHeader}>Prescription Safety Check</h2>
              <form
                onSubmit={async e => {
                  e.preventDefault();
                  setSafetyResult("");
                  setSafetyLoading(true);
                  try {
                    const result = await checkPrescriptionSafety(patientId, medicationName);
                    if (result.safe) {
                      setSafetyResult("Safe");
                    } else {
                      setSafetyResult(`Dangerous: ${result.reason || "Conflict detected"}`);
                    }
                  } catch {
                    setSafetyResult("Error checking prescription safety.");
                  } finally {
                    setSafetyLoading(false);
                  }
                }}
                style={{ marginTop: "1em" }}
              >
                <div className={styles.formRow}>
                  <label htmlFor="medication-name" style={{ fontWeight: 500 }}>Medication Name:</label>
                  <input
                    className={styles.formInput}
                    id="medication-name"
                    type="text"
                    placeholder="e.g. Amoxicillin"
                    value={medicationName}
                    onChange={e => setMedicationName(e.target.value)}
                    required
                    disabled={!patientId}
                  />
                  <button className={styles.formButton} type="submit" disabled={safetyLoading || !medicationName || !patientId}>
                    {safetyLoading ? <Spinner size={20} /> : "Check Safety"}
                  </button>
                </div>
              </form>
              {safetyResult && (
                <div style={{ marginTop: "1em", fontWeight: 600, color: safetyResult.startsWith("Safe") ? "#22c55e" : "#ef4444" }}>
                  {safetyResult}
                </div>
              )}
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
