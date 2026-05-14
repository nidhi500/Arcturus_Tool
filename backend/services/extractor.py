import re
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

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

def fetch_soup(url, p):
    # Optimized for Render's 512MB RAM
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ]
    )
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()
    try:
        # Increase timeout for slow Render CPUs
        page.goto(url, timeout=90000, wait_until="domcontentloaded")
        
        # Wait for the Oracle feature table to appear
        page.wait_for_selector("table", timeout=30000)
        
        html = page.content()
    except Exception as e:
        print(f"Extraction error at {url}: {e}")
        html = ""
    finally:
        browser.close()
        
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup

def extract_features(url: str):
    release = get_release(url)
    rel_date = get_release_date(release)
    slug = get_slug(url).upper()
    
    features = []
    
    with sync_playwright() as p:
        soup = fetch_soup(url, p)
        rows = soup.find_all("tr")
        
        if not rows:
            print("No rows found in the table.")
            return []

        count = 0
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2: 
                continue
            
            link = row.find("a", href=True)
            if not link: 
                continue
            
            title = clean_text(link.get_text())
            if "Title and Copyright" in title or len(title) < 5: 
                continue

            count += 1
            
            features.append({
                "release_version": release,
                "release_date": rel_date,
                "module": "Inventory Management", 
                "feature_id": f"{slug}-{count:03d}",
                "oracle_feature_id": f"F{count+10000}",
                "title": title,
                "delivery_status": "Enabled",
                "action_required": "No Action Required",
                "impact": "Small Scale",
                "bug_ids": "",
                "description": f"Upgrade details for {title}.",
                "steps_to_enable": "Automatically available.",
                "url": urljoin(url, link['href']),
                "priority": "Medium",
                "notes": "",
                "mandatory": "Yes"
            })
            
            # Limit features to keep memory usage low on Render
            if count >= 15: 
                break
            
    return features