import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.extractor import extract_features
from services.excel_generator import generate_excel
from services.ppt_generator import generate_ppt


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


class GenerateRequest(BaseModel):
    url: str


def output_slug_from_url(url: str):
    parts = url.rstrip("/").split("/")
    if parts[-1] == "index.html":
        return parts[-2]
    return parts[-1]


@app.get("/")
def health_check():
    return {"message": "OQUAT backend is running"}


@app.post("/generate")
def generate_report(request: GenerateRequest):
    if not request.url.startswith("https://docs.oracle.com"):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid Oracle documentation URL."
        )

    # 1. Call extraction ONCE and store it in a variable
    features = extract_features(request.url)
    
    # 2. Check if the list is empty to prevent downstream crashes
    if not features:
        raise HTTPException(
            status_code=404,
            detail="Could not find any features at the provided URL. Please check if the URL is a standard Oracle Readiness index."
        )

    # 3. Proceed with generation using the stored 'features' variable
    slug = output_slug_from_url(request.url)

    # Excel Generation
    excel_path = generate_excel(features, f"outputs/oracle_{slug}.xlsx")

    # PPT Generation
    template_path = "templates/inventory_template.pptx"
    ppt_path = f"outputs/oracle_{slug}.pptx"
    generate_ppt(features, template_path, ppt_path)

    return {
        "message": "Reports generated successfully",
        "feature_count": len(features),
        "excel_url": f"/outputs/oracle_{slug}.xlsx",
        "ppt_url": f"/outputs/oracle_{slug}.pptx",
        "features": features
    }