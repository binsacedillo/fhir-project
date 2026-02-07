from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()

# Get backend URL from environment for allowed origins
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL, 
        "http://localhost:3000",
        "https://fhir-project-five.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FHIR_BASE_URL = "https://server.fire.ly"

@app.get("/")
def root():
    return {"status": "ok", "message": "FHIR API Backend is running"}

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    try:
        url = f"{FHIR_BASE_URL}/Patient/{patient_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/allergies/{patient_id}")
def get_allergies(patient_id: str):
    try:
        url = f"{FHIR_BASE_URL}/AllergyIntolerance?patient={patient_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/medications/{patient_id}")
def get_medications(patient_id: str):
    try:
        url = f"{FHIR_BASE_URL}/MedicationStatement?patient={patient_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/check-prescription")
def check_prescription(patient_id: str = Query(...), medication: str = Query(...)):
    try:
        allergies_url = f"{FHIR_BASE_URL}/AllergyIntolerance?patient={patient_id}"
        allergies = requests.get(allergies_url, timeout=10).json()
        for entry in allergies.get("entry", []):
            substance = entry["resource"].get("code", {}).get("text", "").lower()
            if medication.lower() in substance:
                return {"safe": False, "reason": f"Allergy conflict: {substance}"}
        return {"safe": True}
    except Exception as e:
        return {"error": str(e)}, 500
