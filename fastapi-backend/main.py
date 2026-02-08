from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import logging
import re
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FHIR API Backend", description="FastAPI backend for FHIR operations on Firely Server")

# Get backend URL from environment for allowed origins
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL, 
        "http://localhost:3000",
        "https://fhir-project-zeta.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Firely Server - Public FHIR test instance (R4, STU3, R5 support)
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://server.fire.ly")

def validate_fhir_id(resource_id: str):
    """Validate that resource ID contains only safe characters."""
    if not re.match(r"^[A-Za-z0-9\-\.]+$", resource_id):
        raise HTTPException(status_code=400, detail="Invalid ID format provided.")

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "message": "FHIR API Backend is running"
    }

@app.get("/search-patients")
def search_patients(
    name: str = Query(None, description="Search by patient name", max_length=50),
    family: str = Query(None, description="Search by family name", max_length=50),
    given: str = Query(None, description="Search by given name", max_length=50),
    birthdate: str = Query(None, description="Search by birthdate (format: YYYY-MM-DD or ge1990-01-01)", max_length=20),
    gender: str = Query(None, description="Search by gender (male, female, other, unknown)", max_length=10),
    identifier: str = Query(None, description="Search by identifier (e.g., SSN, MRN)", max_length=50),
    _id: str = Query(None, description="Search by patient ID (e.g., 4a704b3d-5f89-4951-8b83-53b580ff39da)", max_length=64),
    _count: int = Query(10, description="Number of results per page", ge=1, le=100),
    _page: int = Query(1, description="Page number for pagination", ge=1)
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
        logger.error(f"Unexpected error in search_patients: {str(e)}")
        return {"error": "Internal Server Error"}, 500

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    """Retrieve a specific patient by ID"""
    try:
        validate_fhir_id(patient_id)
        response = requests.get(f"{FHIR_BASE_URL}/Patient/{patient_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": f"Patient {patient_id} not found"}, 404
        return {"error": f"FHIR Server error: {str(e)}"}, e.response.status_code
    except Exception as e:
        logger.error(f"Unexpected error in get_patient: {str(e)}")
        return {"error": "Internal Server Error"}, 500

@app.get("/allergies/{patient_id}")
def get_allergies(patient_id: str):
    """Get all allergy intolerances for a patient"""
    try:
        validate_fhir_id(patient_id)
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
        logger.error(f"Unexpected error in get_allergies: {str(e)}")
        return {"error": "Internal Server Error"}, 500

@app.get("/medications/{patient_id}")
def get_medications(patient_id: str):
    """
    Get medications for a patient (both MedicationRequest and MedicationStatement).
    MedicationRequest = Prescriptions, MedicationStatement = Current/Historical medications
    """
    try:
        validate_fhir_id(patient_id)
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
        logger.error(f"Unexpected error in get_medications: {str(e)}")
        return {"error": "Internal Server Error"}, 500

@app.post("/check-prescription")
def check_prescription(patient_id: str = Query(..., max_length=64), medication: str = Query(..., max_length=100)):
    """
    Prescription Safety Check: Verify if a medication conflicts with patient allergies.
    This is a custom feature (not standard FHIR) built on top of Firely Server data.
    """
    try:
        validate_fhir_id(patient_id)
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
        logger.error(f"Unexpected error in check_prescription: {str(e)}")
        return {"error": "Internal Server Error"}, 500
