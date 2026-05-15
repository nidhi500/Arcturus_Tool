import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Internal services
from backend.services.extractor import extract_features
from backend.services.excel_generator import generate_excel
from backend.services.ppt_generator import generate_ppt

# Ensure output directory exists
os.makedirs("outputs", exist_ok=True)

app = FastAPI(title="OQUAT - Oracle Quarterly Upgrade Automation Tool")
CACHE_FILE = "outputs/cache_registry.json"

app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReportRequest(BaseModel):
    url: str
    limit: int = 0
    # This allows the Chrome Extension to "inject" real data
    injected_features: Optional[List[dict]] = None 

def output_slug_from_url(url: str):
    parts = url.rstrip("/").split("/")
    return parts[-2] if parts[-1] == "index.html" else parts[-1]

@app.get("/")
def health_check():
    return {"message": "OQUAT backend is running"}

@app.post("/generate")
async def generate_report(request: ReportRequest):
    # 1. Caching Check
    if os.path.exists(CACHE_FILE) and not request.injected_features:
        with open(CACHE_FILE, "r") as f:
            try:
                cache = json.load(f)
                if request.url in cache and cache[request.url].get("limit_applied") == request.limit:
                    return cache[request.url]
            except: pass

    try:
        # 2. Data Sourcing: Use Extension data if provided, else scrape
        if request.injected_features:
            features = request.injected_features
            # Ensure we apply enterprise fields to injected data
            slug_val = output_slug_from_url(request.url).upper()
            for i, feat in enumerate(features):
                feat.setdefault("release_version", "26B")
                feat.setdefault("release_date", "May 2026")
                feat.setdefault("feature_id", f"{slug_val}-{i+1:03d}")
                feat.setdefault("delivery_status", "Enabled")
                feat.setdefault("impact", "Small Scale")
        else:
            features = await extract_features(request.url)

        if not features:
            raise HTTPException(status_code=400, detail="No features found.")

        if request.limit > 0:
            features = features[:request.limit]

        slug = output_slug_from_url(request.url)
        excel_fn = f"oracle_{slug}_l{request.limit}.xlsx"
        ppt_fn = f"oracle_{slug}_l{request.limit}.pptx"
        
        # 3. Generate Reports
        generate_excel(features, f"outputs/{excel_fn}")
        template_path = os.path.join(os.path.dirname(__file__), "templates", "inventory_template.pptx")
        generate_ppt(features, template_path, f"outputs/{ppt_fn}")

        result = {
            "message": "Reports generated successfully",
            "feature_count": len(features),
            "excel_url": f"/outputs/{excel_fn}",
            "ppt_url": f"/outputs/{ppt_fn}",
            "features": features,
            "limit_applied": request.limit
        }

        # 4. Save to Cache
        cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                try: cache = json.load(f)
                except: pass
        cache[request.url] = result
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)

        return result

    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))