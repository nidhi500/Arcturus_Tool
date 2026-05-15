import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Internal services
from backend.services.extractor import extract_features, enrich_all_features
from backend.services.excel_generator import generate_excel
from backend.services.ppt_generator import generate_ppt

# Ensure output directory exists
os.makedirs("outputs", exist_ok=True)

app = FastAPI(title="OQUAT - Oracle Quarterly Upgrade Automation Tool")

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
    # Handle index.html or folder-based URLs
    return parts[-2] if parts[-1] == "index.html" else parts[-1]

@app.get("/")
def health_check():
    return {"message": "OQUAT backend is running", "status": "Ready"}

@app.post("/generate")
async def generate_report(request: Request):
    data = await request.json()
    url = data.get("url", "")
    injected_features = data.get("injected_features", [])
    
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    slug = output_slug_from_url(url)
    
    # STEP 1: Data Gathering & Enrichment
    if injected_features:
        # We use the new parallel crawler to visit all 60+ pages
        print(f"Enriching {len(injected_features)} features for {slug}...")
        features = await enrich_all_features(injected_features)
    else:
        # Standard fallback if extension data isn't provided
        features = await extract_features(url)

    if not features:
        raise HTTPException(status_code=404, detail="No features extracted")

    # STEP 2: File Generation
    excel_filename = f"{slug}_report.xlsx"
    ppt_filename = f"{slug}_deck.pptx"
    
    excel_path = f"outputs/{excel_filename}"
    ppt_path = f"outputs/{ppt_filename}"

    # Generate the actual files
    try:
        generate_excel(features, excel_path)
        generate_ppt(features, ppt_path)
    except Exception as e:
        print(f"Generation Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating files: {str(e)}")

    # STEP 3: Return links (Render serves /outputs/ via StaticFiles)
    return {
        "status": "Ready",
        "total": len(features),
        "release": slug.upper(),
        "excel_link": f"/outputs/{excel_filename}",
        "ppt_link": f"/outputs/{ppt_filename}"
    }