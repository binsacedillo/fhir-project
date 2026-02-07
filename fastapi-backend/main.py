from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Allow CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
    response = requests.get(url)
    return response.json()

@app.get("/allergies/{patient_id}")
def get_allergies(patient_id: str):
    url = f"{FHIR_BASE_URL}/AllergyIntolerance?patient={patient_id}"
    response = requests.get(url)
    return response.json()

@app.get("/medications/{patient_id}")
def get_medications(patient_id: str):
    url = f"{FHIR_BASE_URL}/MedicationStatement?patient={patient_id}"
    response = requests.get(url)
    return response.json()

@app.post("/check-prescription")
def check_prescription(patient_id: str = Query(...), medication: str = Query(...)):
    # Fetch allergies
    allergies_url = f"{FHIR_BASE_URL}/AllergyIntolerance?patient={patient_id}"
    allergies = requests.get(allergies_url).json()
    # Simple check: if medication name matches any allergy substance
    for entry in allergies.get("entry", []):
        substance = entry["resource"].get("code", {}).get("text", "").lower()
        if medication.lower() in substance:
            return {"safe": False, "reason": f"Allergy conflict: {substance}"}
    return {"safe": True}
