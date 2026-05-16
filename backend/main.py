import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Internal services
from backend.services.extractor import enrich_all_features

# Ensure output directory exists
os.makedirs("outputs", exist_ok=True)

# 1. STRICT PAYLOAD SCHEMA (Fed directly by the Chrome Extension)
class GenerateRequest(BaseModel):
    url: str
    limit: int = 0
    injected_features: List[dict]  # Enforced as mandatory now

app = FastAPI(title="OQUAT - Extension-Only Core Engine")

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
    return parts[-2] if parts[-1] == "index.html" else parts[-1]

@app.get("/")
def health_check():
    return {"status": "Active", "engine": "Extension-Only Architecture Ready"}

@app.post("/generate")
async def generate_report(request: GenerateRequest):
    # Error checking: If the extension sent an empty payload, stop immediately
    if not request.injected_features:
        raise HTTPException(status_code=400, detail="Payload validation failed: No features received from extension.")

    features_to_process = request.injected_features
    print(f"Received {len(features_to_process)} raw features from Chrome Extension.")

    # Apply the UI Limit Choice (Top 5, Top 10, etc.)
    if request.limit > 0:
        features_to_process = features_to_process[:request.limit]
        print(f"Applying execution slice constraint: processing top {request.limit} records.")

    # Trigger our 15-column intelligence processing loop
    enriched_features = await enrich_all_features(features_to_process)
    
    # Generate clean output paths
    slug = output_slug_from_url(request.url)
    excel_path = f"outputs/oracle_{slug}.xlsx"
    
    # Import and execute local spreadsheet generation layout utilities
    from backend.services.excel_generator import generate_excel
    generate_excel(enriched_features, excel_path)
    
    # Return response directly back to the extension handler popup window
    return {
        "status": "Success",
        "feature_count": len(enriched_features),
        "excel_url": f"/outputs/oracle_{slug}.xlsx"
    }