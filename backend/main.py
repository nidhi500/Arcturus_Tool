import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Internal services
from backend.services.extractor import enrich_all_features, extract_features, extract_feature_links
from backend.services.excel_generator import generate_excel
from backend.services.ppt_generator import generate_ppt

# Ensure output directory exists
os.makedirs("outputs", exist_ok=True)

# 1. DEFINE THE CLASS FIRST
class GenerateRequest(BaseModel):
    url: str
    limit: int = 0
    injected_features: list = None

# 2. THEN INITIALIZE THE APP
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
async def generate_report(request: GenerateRequest):
    # USE THE DATA FROM THE EXTENSION IF AVAILABLE
    if request.injected_features:
        print(f"Using {len(request.injected_features)} features from Extension")
        features_to_process = request.injected_features
    else:
        # Fallback: Scrape links from the URL (The part that was causing the NameError)
        print("No extension data found. Falling back to manual scrape...")
        features_to_process = extract_feature_links(request.url) 
    
    if not features_to_process:
        raise HTTPException(status_code=400, detail="No features found to process.")

    # RUN THE ENRICHMENT (This visits the 60 sub-pages)
    features = await enrich_all_features(features_to_process)
    
    slug = output_slug_from_url(request.url)
    excel_path = f"outputs/oracle_{slug}.xlsx"
    ppt_path = f"outputs/oracle_{slug}.pptx"
    
    # Generate Files
    generate_excel(features, excel_path)
    # Note: Ensure your PPT generator is updated to take only 2 args if that's what we changed
    # generate_ppt(features, ppt_path) 
    
    return {
        "status": "Ready",
        "feature_count": len(features),
        "excel_url": f"/outputs/oracle_{slug}.xlsx",
        "ppt_url": f"/outputs/oracle_{slug}.pptx"
    }