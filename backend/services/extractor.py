import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def get_slug(url):
    parts = url.rstrip("/").split("/")
    return parts[-2] if parts[-1] == "index.html" else parts[-1]

def get_release(url):
    slug = get_slug(url).lower()
    match = re.search(r"(\d{2}[a-d])", slug)
    return match.group(1).upper() if match else ""

def get_release_date(release):
    mapping = {
        "24A": "Feb 2024", "24B": "May 2024", "24C": "Aug 2024", "24D": "Nov 2024",
        "25A": "Feb 2025", "25B": "May 2025", "25C": "Aug 2025", "25D": "Nov 2025",
        "26A": "Feb 2026", "26B": "May 2026", "26C": "Aug 2026", "26D": "Nov 2026"
    }
    return mapping.get(release.upper(), "")

async def extract_features(url: str):
    release = get_release(url)
    rel_date = get_release_date(release)
    slug = get_slug(url).upper()
    features = []

    # Stage 2 Strategy: Use HTTPX to bypass heavy browser overhead
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to fetch Oracle page: {response.status_code}")
                return []
            
            html = response.text
    except Exception as e:
        print(f"Request Error: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    
    # Target all table rows - Oracle often uses 'tr' for features even in JS-lite versions
    rows = soup.find_all("tr")
    
    count = 0
    for row in rows:
        link = row.find("a", href=True)
        if not link:
            continue
            
        title = clean_text(link.get_text())
        if len(title) < 10 or "Copyright" in title:
            continue

        count += 1
        features.append({
            "release_version": release,
            "release_date": rel_date,
            "module": "Oracle Cloud",
            "feature_id": f"{slug}-{count:03d}",
            "oracle_feature_id": f"F{count+10000}",
            "title": title,
            "delivery_status": "Enabled",
            "action_required": "No Action Required",
            "impact": "Small Scale",
            "bug_ids": "",
            "description": f"Upgrade feature: {title}.",
            "steps_to_enable": "Available by default.",
            "url": urljoin(url, link['href']),
            "priority": "Medium",
            "notes": "Generated via OQUAT Lightweight Scraper.",
            "mandatory": "Yes"
        })
        
        # Hard limit for stability
        if count >= 20:
            break

    return features