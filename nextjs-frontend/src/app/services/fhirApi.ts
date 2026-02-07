// FHIR API service functions
import { Patient, AllergyIntolerance, MedicationStatement } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchPatientData(patientId: string): Promise<Patient> {
    const res = await fetch(`${API_URL}/patient/${patientId}`);
    if (!res.ok) throw new Error("Patient not found");
    return await res.json();
}

export async function fetchAllergies(patientId: string): Promise<AllergyIntolerance[]> {
    const res = await fetch(`${API_URL}/allergies/${patientId}`);
    const data = await res.json();
    return data.entry?.map((entry: { resource: AllergyIntolerance }) => entry.resource) || [];
}

export async function fetchMedications(patientId: string): Promise<MedicationStatement[]> {
    const res = await fetch(`${API_URL}/medications/${patientId}`);
    const data = await res.json();
    return data.entry?.map((entry: { resource: MedicationStatement }) => entry.resource) || [];
}

export async function checkPrescriptionSafety(patientId: string, medication: string): Promise<{ safe: boolean; reason?: string }> {
    const res = await fetch(`${API_URL}/check-prescription?patient_id=${patientId}&medication=${encodeURIComponent(medication)}`, {
        method: "POST"
    });
    return await res.json();
}
