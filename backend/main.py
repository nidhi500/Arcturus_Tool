import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Internal services
from backend.services.extractor import enrich_all_features  # Removed extract_features if you aren't using it
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
    # 1. Get the 60 links from the summary page
    # (Using your existing extract_feature_links logic)
    raw_features = extract_feature_links(request.url) 
    
    # 2. RUN THE ENRICHMENT (This fills the empty columns)
    features = await enrich_all_features(raw_features)
    
    slug = output_slug_from_url(request.url)
    excel_path = f"outputs/oracle_{slug}.xlsx"
    
    # 3. Generate the Excel with the now-populated data
    generate_excel(features, excel_path)
    
    return {
        "status": "Ready",
        "feature_count": len(features),
        "excel_url": f"/outputs/oracle_{slug}.xlsx"
    }