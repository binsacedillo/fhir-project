# FHIR Project

A full-stack healthcare application using FHIR standards.

## Project Structure

- **fastapi-backend/** - Python FastAPI server for FHIR API integration
- **nextjs-frontend/** - Next.js React frontend

## Setup Instructions

### Backend Setup
```bash
cd fastapi-backend
python -m venv venv
venv\Scripts\activate
pip install -r [requirements.txt](http://_vscodecontentref_/0)
python -m uvicorn main:app --reload