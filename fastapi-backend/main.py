from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI(title="FHIR API Backend", description="FastAPI backend for FHIR operations on Firely Server")

# Get backend URL from environment for allowed origins
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL, 
        "http://localhost:3000",
        "https://fhir-project-zeta.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firely Server - Public FHIR test instance (R4, STU3, R5 support)
FHIR_BASE_URL = "https://server.fire.ly"

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "message": "FHIR API Backend is running",
        "fhir_server": FHIR_BASE_URL
    }

@app.get("/search-patients")
def search_patients(
    name: str = Query(None, description="Search by patient name"),
    family: str = Query(None, description="Search by family name"),
    given: str = Query(None, description="Search by given name"),
    birthdate: str = Query(None, description="Search by birthdate (format: YYYY-MM-DD or ge1990-01-01)"),
    gender: str = Query(None, description="Search by gender (male, female, other, unknown)"),
    identifier: str = Query(None, description="Search by identifier (e.g., SSN, MRN)"),
    _id: str = Query(None, description="Search by patient ID (e.g., 4a704b3d-5f89-4951-8b83-53b580ff39da)"),
    _count: int = Query(10, description="Number of results per page"),
    _page: int = Query(1, description="Page number for pagination")
):
    """
    Search for patients on Firely Server using standard FHIR parameters.
    Examples:
    - ?name=John
    - ?family=Smith&given=John
    - ?birthdate=ge1990-01-01
    - ?gender=male
    - ?_id=4a704b3d-5f89-4951-8b83-53b580ff39da
    """
    try:
        params = {"_count": _count}
        if name:
            params["name"] = name
        if family:
            params["family"] = family
        if given:
            params["given"] = given
        if birthdate:
            params["birthdate"] = birthdate
        if gender:
            params["gender"] = gender
        if identifier:
            params["identifier"] = identifier
        if _id:
            params["_id"] = _id
        
        response = requests.get(f"{FHIR_BASE_URL}/Patient", params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout – Firely Server took too long to respond"}, 504
    except requests.exceptions.HTTPError as e:
        return {"error": f"FHIR Server error: {str(e)}"}, e.response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    """Retrieve a specific patient by ID"""
    try:
        response = requests.get(f"{FHIR_BASE_URL}/Patient/{patient_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Patient {patient_id} not found"}, 404
        return {"error": f"FHIR Server error: {str(e)}"}, e.response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/allergies/{patient_id}")
def get_allergies(patient_id: str):
    """Get all allergy intolerances for a patient"""
    try:
        response = requests.get(
            f"{FHIR_BASE_URL}/AllergyIntolerance",
            params={"patient": patient_id},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"No allergies found for patient {patient_id}"}, 404
        return {"error": f"FHIR Server error: {str(e)}"}, e.response.status_code
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/medications/{patient_id}")
def get_medications(patient_id: str):
    """
    Get medications for a patient (both MedicationRequest and MedicationStatement).
    MedicationRequest = Prescriptions, MedicationStatement = Current/Historical medications
    """
    try:
        # Fetch MedicationRequest (prescriptions)
        med_request = requests.get(
            f"{FHIR_BASE_URL}/MedicationRequest",
            params={"patient": patient_id, "status": "active"},
            timeout=10
        ).json()
        
        # Fetch MedicationStatement (current medications)
        med_statement = requests.get(
            f"{FHIR_BASE_URL}/MedicationStatement",
            params={"patient": patient_id},
            timeout=10
        ).json()
        
        return {
            "prescriptions": med_request,
            "medications": med_statement
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.post("/check-prescription")
def check_prescription(patient_id: str = Query(...), medication: str = Query(...)):
    """
    Prescription Safety Check: Verify if a medication conflicts with patient allergies.
    This is a custom feature (not standard FHIR) built on top of Firely Server data.
    """
    try:
        # Fetch patient allergies
        allergies_response = requests.get(
            f"{FHIR_BASE_URL}/AllergyIntolerance",
            params={"patient": patient_id},
            timeout=10
        ).json()
        
        allergies = allergies_response.get("entry", [])
        conflicts = []
        
        for entry in allergies:
            substance = entry["resource"].get("code", {}).get("text", "").lower()
            reaction = entry["resource"].get("reaction", [])
            
            if medication.lower() in substance:
                severity = reaction[0].get("severity", "unknown") if reaction else "unknown"
                conflicts.append({
                    "allergen": substance,
                    "severity": severity,
                    "description": entry["resource"].get("note", [{}])[0].get("text", "No details")
                })
        
        if conflicts:
            return {
                "safe": False,
                "conflicts": conflicts,
                "recommendation": "Do not prescribe – allergy conflict detected"
            }
        
        return {
            "safe": True,
            "recommendation": f"{medication} is safe for patient {patient_id} (no known allergies found)"
        }
    except Exception as e:
        return {"error": str(e)}, 500
