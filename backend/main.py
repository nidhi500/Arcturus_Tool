import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Internal Core Intelligence Services
from backend.services.extractor import enrich_all_features
from backend.services.excel_generator import generate_excel
from backend.services.ppt_generator import generate_ppt  # IMPORT THE POWERPOINT CONTEXT GENERATOR

# Ensure transient and permanent file compilation volumes exist
os.makedirs("outputs", exist_ok=True)

# 1. STRICT PAYLOAD SCHEMA (Fed directly by the Chrome Extension)
class GenerateRequest(BaseModel):
    url: str
    limit: int = 1000
    injected_features: List[dict]

app = FastAPI(title="OQUAT - Extension-Only Core Engine")

# Mount output storage endpoints under standard proxy directory tokens
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def output_slug_from_url(url: str):
    parts = url.rstrip("/").split("/")
    target = parts[-2] if parts[-1] == "index.html" else parts[-1]
    # Clean up trailing file formats to maintain pristine alphanumeric system paths
    return target.replace(".html", "").replace(".htm", "")

@app.get("/")
def health_check():
    return {"status": "Active", "engine": "Extension-Only Architecture Ready"}

@app.post("/generate")
async def generate_report(request: GenerateRequest):
    if not request.injected_features:
        raise HTTPException(status_code=400, detail="Payload validation failed: No features received from extension.")

    features_to_process = request.injected_features
    print(f"Received {len(features_to_process)} raw features from Chrome Extension.")

    # Apply the User Interface Limit Constraint
    if request.limit > 0:
        features_to_process = features_to_process[:request.limit]
        print(f"Applying execution slice constraint: processing top {request.limit} records.")

    # Trigger our 15-column intelligence processing logic loops
    enriched_features = await enrich_all_features(features_to_process)
    
    # Generate unified, clean asset storage names
    slug = output_slug_from_url(request.url)
    excel_path = f"outputs/oracle_{slug}.xlsx"
    ppt_path = f"outputs/oracle_{slug}.pptx"
    
    try:
        # Task A: Compile the client data audit tracking sheets
        generate_excel(enriched_features, excel_path)
        print(f"Prism spreadsheet matrix written successfully to: {excel_path}")
        
        # Task B: Compile the synchronized executive presentation deck slides
        generate_ppt(enriched_features, ppt_path)
        print(f"Executive boardroom presentation deck written successfully to: {ppt_path}")
        
    except Exception as generation_error:
        print(f"Compilation Exception in Document Factory Loop: {generation_error}")
        raise HTTPException(status_code=500, detail=f"Internal Document Factory Failure: {str(generation_error)}")
    
    # Return explicit artifact routing references back to popup.js elements
    return {
        "status": "Success",
        "feature_count": len(enriched_features),
        "excel_url": f"/outputs/oracle_{slug}.xlsx",
        "ppt_url": f"/outputs/oracle_{slug}.pptx"
    }