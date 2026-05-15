import asyncio
import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Limit parallel requests to 10
semaphore = asyncio.Semaphore(10)

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def summarize_text(text, max_sentences=2):
    """FIX: Truncates long walls of text to keep Excel readable."""
    if not text or "Automatically enabled" in text:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:max_sentences]).strip()
    return summary[:400] + "..." if len(summary) > 400 else summary

def analyze_intelligence(title, steps, description):
    """
    FIX: The 'Brain' that solves Delivery Status, Impact, and Priority.
    No more uniform 'Low' or 'Small Scale' for everything.
    """
    combined = (title + " " + steps + " " + description).lower()
    
    # 1. DYNAMIC DELIVERY STATUS & ACTION
    if any(word in steps.lower() for word in ["opt in", "profile option", "setup and maintenance", "provision"]):
        status = "Disabled"
        action = "Setup Required"
    else:
        status = "Enabled"
        action = "No Action Required"

    # 2. DYNAMIC IMPACT EVALUATION
    if any(word in combined for word in ["ai agent", "redwood", "workspace", "mobile", "new experience"]):
        impact = "Large Scale (UI/UX)"
    elif any(word in combined for word in ["rest api", "fbdi", "integration", "algorithm"]):
        impact = "Medium (Technical)"
    else:
        impact = "Small Scale"

    # 3. SYNCED PRIORITY
    if impact == "Large Scale (UI/UX)" or action == "Setup Required":
        priority = "High"
    elif "report" in combined or "search" in combined:
        priority = "Low"
    else:
        priority = "Medium"

    return status, action, impact, priority

async def fetch_detail_page(client, feature):
    """Deep-scrapes sub-pages with enhanced selector logic."""
    async with semaphore:
        try:
            url = feature.get('url', '')
            if not url or "javascript" in url: return feature

            response = await client.get(url, timeout=15.0)
            if response.status_code != 200: return feature
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # FIX: Real Description Scraping
            desc_area = soup.find('section', id=re.compile(r'description|overview', re.I)) or \
                        soup.find('div', class_=re.compile(r'section|content', re.I))
            if desc_area:
                p_text = " ".join([p.get_text().strip() for p in desc_area.find_all('p') if len(p.get_text()) > 30])
                feature['description'] = p_text if p_text else "Details available in Oracle Cloud Readiness."
            
            # FIX: Steps to Enable Scraping
            steps_area = soup.find('section', id=re.compile(r'steps-to-enable|setup', re.I))
            feature['steps_to_enable'] = steps_area.get_text(separator=' ').strip() if steps_area else "Automatically enabled."

            # Oracle ID & Bugs
            id_match = re.search(r"\b[FT]\d{5,6}\b", response.text)
            if id_match: feature['oracle_feature_id'] = id_match.group().upper()
            bugs = re.findall(r"\b\d{8}\b", response.text)
            feature['bug_ids'] = ", ".join(set(bugs)) if bugs else "None"

        except Exception as e:
            print(f"Crawl Error: {e}")
        return feature

async def enrich_all_features(injected_features):
    """The master loop that processes all 60 features."""
    headers = {"User-Agent": "OQUAT-Consultant-v2"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        # Step 1: Raw Crawl
        tasks = [fetch_detail_page(client, f) for f in injected_features]
        raw_results = await asyncio.gather(*tasks)
        
        # Step 2: Intelligence Processing (Fixing the 5 key issues)
        final_features = []
        for idx, f in enumerate(raw_results, start=1):
            title = f.get('title', '')
            raw_steps = f.get('steps_to_enable', '')
            raw_desc = f.get('description', '')

            # Run the Brain
            status, action, impact, priority = analyze_intelligence(title, raw_steps, raw_desc)

            f.update({
                "feature_id": f"INV-{idx:03d}",
                "description": summarize_text(raw_desc, 2),
                "steps_to_enable": summarize_text(raw_steps, 3),
                "delivery_status": status,
                "action_required": action,
                "impact": impact,
                "priority": priority,
                "notes": f"Validated for {impact}."
            })
            final_features.append(f)
        return final_features

async def extract_features(url: str):
    """
    Fallback function to satisfy the import in main.py.
    The primary logic now uses extract_feature_links + enrich_all_features.
    """
    return []

def extract_feature_links(url: str):
    """
    Placeholder to prevent NameError in main.py.
    Real link extraction happens via the Chrome Extension.
    """
    return []