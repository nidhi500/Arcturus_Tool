import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

# In backend/services/extractor.py

async def extract_features(url):
    async with async_playwright() as p:
        # These specific args are CRITICAL for Render's 512MB RAM limit
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage", # Uses /tmp instead of memory for shared heap
                "--disable-gpu",            # Saves a massive amount of RAM
                "--single-process"         # Reduces overhead (use with caution but good for low RAM)
            ]
        )
        # ... rest of your code

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def get_slug(url):
    parts = url.rstrip("/").split("/")
    if parts[-1] == "index.html":
        return parts[-2]
    return parts[-1]

def get_module_name(url):
    slug = get_slug(url).lower()
    if "inv" in slug: return "Inventory Management"
    if "om" in slug: return "Order Management"
    if "proc" in slug: return "Procurement"
    return "Inventory Management"

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

def fetch_soup(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(1000)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup

def extract_bug_ids(text):
    bug_ids = re.findall(r"\b\d{7,10}\b", text or "")
    return ", ".join(sorted(set(bug_ids)))

def find_feature_summary_url(index_url):
    if index_url.endswith("/"):
        index_url += "index.html"
    soup = fetch_soup(index_url)
    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" "))
        href = link.get("href", "")
        if "Feature Summary" in text:
            return urljoin(index_url, href)

    slug = get_slug(index_url).lower()
    release = get_release(index_url)

    # Robust Fallback Logic
    module_map = {
        "inv": "inventory",
        "om": "order-management",
        "proc": "procurement",
        "fin": "financials"
    }
    
    target_module = "inventory"
    for key, name in module_map.items():
        if key in slug:
            target_module = name
            break

    if target_module == "inventory":
        return index_url.replace("index.html", f"{release}-inventory-wn-t73741.htm")
    
    probable_filename = f"{release}-{target_module}-wn.htm"
    return index_url.replace("index.html", probable_filename)

def extract_feature_links(index_url):
    feature_summary_url = find_feature_summary_url(index_url)
    if not feature_summary_url:
        print("Feature Summary page not found.")
        return []
    
    print("Feature Summary URL:", feature_summary_url)
    soup = fetch_soup(feature_summary_url)
    feature_links = []
    seen = set()

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 3: continue
        cell_texts = [clean_text(cell.get_text(" ")) for cell in cells]
        row_text = " ".join(cell_texts)
        if "Feature" in row_text and "Module" in row_text: continue
        link = row.find("a", href=True)
        if not link: continue
        title = clean_text(link.get_text(" "))
        href = link.get("href", "")
        if not title or len(title) < 10: continue
        if "Title and Copyright" in title: continue
        feature_url = urljoin(feature_summary_url, href)
        if title in seen: continue
        seen.add(title)
        feature_links.append({
            "title": title, "url": feature_url,
            "summary_url": feature_summary_url, "raw_cells": cell_texts
        })
    return feature_links

def extract_section_text(soup, section_names):
    section_names_lower = [name.lower() for name in section_names]
    headings = soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"])
    for heading in headings:
        heading_text = clean_text(heading.get_text(" ")).lower()
        if any(name in heading_text for name in section_names_lower):
            collected = []
            for sibling in heading.find_all_next():
                if sibling.name in ["h1", "h2", "h3", "h4"]: break
                text = clean_text(sibling.get_text(" "))
                if text and text not in collected: collected.append(text)
                if len(" ".join(collected)) > 1200: break
            return clean_text(" ".join(collected))
    return ""

def extract_oracle_feature_id(feature_url, soup):
    url_match = re.search(r"-wn-([ft]\d{5,6})", feature_url, re.IGNORECASE)
    if url_match: return url_match.group(1).upper()
    text = clean_text(soup.get_text(" "))
    match = re.search(r"\b[FT]\d{5,6}\b", text, re.IGNORECASE)
    return match.group().upper() if match else ""

def extract_feature_detail(feature_url):
    data = {"description": "", "steps_to_enable": "", "impact": "", "bug_ids": "", "oracle_feature_id": ""}
    try:
        soup = fetch_soup(feature_url)
    except Exception as e:
        print("Detail extraction failed:", feature_url, e)
        return data

    page_text = clean_text(soup.get_text(" "))
    data["oracle_feature_id"] = extract_oracle_feature_id(feature_url, soup)
    data["bug_ids"] = extract_bug_ids(page_text)
    data["steps_to_enable"] = extract_section_text(soup, ["Steps to Enable", "How to Enable", "Enablement", "Setup"])
    data["impact"] = extract_section_text(soup, ["Impact to Existing Processes", "Impact", "Business Benefit"])
    data["description"] = extract_section_text(soup, ["Overview", "Description", "Feature Summary"])

    if not data["description"]:
        paragraphs = [clean_text(p.get_text(" ")) for p in soup.find_all("p") if len(clean_text(p.get_text(" "))) > 50]
        if paragraphs: data["description"] = " ".join(paragraphs[:2])

    return data

def infer_delivery_status(action_required):
    action = clean_text(action_required).lower()
    if action in ["", "none", "no action required", "automatically available"]: return "Enabled"
    return "Disabled"

def infer_priority(title, action_required):
    t_low, a_low = title.lower(), action_required.lower()
    if "ai agent" in t_low or "setup required" in a_low or "opt in" in a_low: return "High"
    if "view" in t_low or "search" in t_low: return "Low"
    return "Medium"

def normalize_action_required(raw_action):
    action = clean_text(raw_action)
    if not action: return "No Action Required"
    a_low = action.lower()
    if "opt in" in a_low: return "Opt In"
    if "setup" in a_low: return "Setup Required"
    if "rest" in a_low or "api" in a_low: return "REST APIs"
    return "No Action Required" if "no" in a_low and "required" in a_low else action

def get_value_from_summary_cells(cell_texts, title):
    module, impact, action_required = "", "", ""
    filtered = [text for text in cell_texts if text and text != title]
    if len(filtered) >= 1: module = filtered[0]
    for text in filtered:
        lower = text.lower()
        if any(x in lower for x in ["opt in", "setup required", "rest api"]): action_required = normalize_action_required(text)
        if lower in ["report", "small scale", "larger scale"]: impact = text
    return module, impact, action_required

def summarize_text(text, max_sentences=2):
    if not text: return ""
    sentences = re.split(r"(?<=[.!?])\s+", clean_text(text))
    return " ".join(sentences[:max_sentences]).strip()

def extract_features(url: str):
    release, rel_date, slug = get_release(url), get_release_date(get_release(url)), get_slug(url).upper()
    try:
        feature_links = extract_feature_links(url)
    except:
        feature_links = []

    features = []
    # Using first 10 for speed, change to feature_links for full report
    for idx, item in enumerate(feature_links, start=1):
        title, feature_url, raw_cells = item.get("title", ""), item.get("url", url), item.get("raw_cells", [])
        s_mod, s_impact, s_action = get_value_from_summary_cells(raw_cells, title)
        
        module = s_mod or get_module_name(url)
        action_req = normalize_action_required(s_action)
        delivery_stat = infer_delivery_status(action_req)
        
        detail = extract_feature_detail(feature_url.split("#")[0]) if ".htm" in feature_url else {}
        
        # Inside your extract_features function
        async with page:
            await page.goto(url, wait_until="networkidle")
    
    # CRITICAL: Wait specifically for the Oracle feature table to appear
    try:
        await page.wait_for_selector(".oj-table-body", timeout=15000) 
    except:
        print("Timeout: Oracle table did not load in time.")
        return [] # Returns empty if table never shows

        # MANDATORY LOGIC: Enabled = Yes, else No
        mandatory_val = "Yes" if delivery_stat == "Enabled" else "No"

        features.append({
            "release_version": release,
            "release_date": rel_date,
            "module": module,
            "feature_id": f"{slug}-{idx:03d}",
            "oracle_feature_id": detail.get("oracle_feature_id", ""),
            "title": title,
            "delivery_status": delivery_stat,
            "action_required": action_req,
            "impact": detail.get("impact", "") or s_impact,
            "bug_ids": detail.get("bug_ids", ""),
            "description": summarize_text(detail.get("description", ""), 2),
            "steps_to_enable": summarize_text(detail.get("steps_to_enable", ""), 1),
            "url": feature_url,
            "priority": infer_priority(title, action_req),
            "notes": summarize_text(detail.get("description", ""), 1),
            "mandatory": mandatory_val
        })
    return features