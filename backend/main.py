import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Internal services
from backend.services.extractor import extract_features
from backend.services.excel_generator import generate_excel
from backend.services.ppt_generator import generate_ppt

# Ensure output directory exists
os.makedirs("outputs", exist_ok=True)

app = FastAPI(title="OQUAT - Oracle Quarterly Upgrade Automation Tool")
CACHE_FILE = "outputs/cache_registry.json"

# Middleware and Static Files
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
    limit: int = 0  # 0 means no limit

def output_slug_from_url(url: str):
    parts = url.rstrip("/").split("/")
    if parts[-1] == "index.html":
        return parts[-2]
    return parts[-1]

@app.get("/")
def health_check():
    return {"message": "OQUAT backend is running"}

@app.post("/generate")
async def generate_report(request: ReportRequest):
    # 1. Persistence Check (Stage 2: Caching)
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                cache = json.load(f)
                if request.url in cache and cache[request.url].get("limit_applied") == request.limit:
                    return cache[request.url]
            except json.JSONDecodeError:
                pass

    try:
        # 1. Await the scraper result (Fixes 'coroutine' error)
        features = await extract_features(request.url)
        
        if not features:
            raise HTTPException(status_code=400, detail="No features found at the provided URL.")

        # 2. Apply the Limit Parameter
        if request.limit > 0:
            features = features[:request.limit]

        slug = output_slug_from_url(request.url)

        # 3. Generate filenames and files
        excel_filename = f"oracle_{slug}_l{request.limit}.xlsx"
        ppt_filename = f"oracle_{slug}_l{request.limit}.pptx"
        
        # Call synchronous generators
        generate_excel(features, f"outputs/{excel_filename}")
        
        # Ensure pathing for template is correct based on your folder structure
        template_path = os.path.join(os.path.dirname(__file__), "templates", "inventory_template.pptx")
        generate_ppt(features, template_path, f"outputs/{ppt_filename}")

        # 4. Construct Result
        result = {
            "message": "Reports generated successfully",
            "feature_count": len(features),
            "excel_url": f"/outputs/{excel_filename}",
            "ppt_url": f"/outputs/{ppt_filename}",
            "features": features,
            "limit_applied": request.limit
        }

        # 5. Save to Cache Registry (Stage 2 Completion)
        cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                try:
                    cache = json.load(f)
                except json.JSONDecodeError:
                    pass
        
        cache[request.url] = result
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)

        return result

    except Exception as e:
        # Log the specific error for Render debugging
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))