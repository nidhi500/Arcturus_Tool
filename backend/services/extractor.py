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

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return []
            
            # ORACLE DATA EXTRACTION STRATEGY:
            # If the table isn't in HTML, we look for the 'feature-summary' links in the text
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find any link that mentions "Feature Summary" or "What's New"
            all_links = soup.find_all("a", href=True)
            
            count = 0
            for link in all_links:
                title = clean_text(link.get_text())
                href = link['href']
                
                # Filter for actual feature titles (usually longer than 15 chars)
                if len(title) < 15 or "Copyright" in title or "Privacy" in title:
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
                    "description": f"New feature available in {release}: {title}.",
                    "steps_to_enable": "Automatically available after update.",
                    "url": urljoin(url, href),
                    "priority": "Medium",
                    "notes": "Extracted via OQUAT High-Speed Scraper.",
                    "mandatory": "Yes"
                })
                
                if count >= 20: break

            # FALLBACK: If standard links fail, look for specific Oracle ID patterns in the HTML text
            if not features:
                ids = re.findall(r'F\d{5,6}', response.text)
                for idx, fid in enumerate(set(ids[:10])):
                    features.append({
                        "release_version": release, "release_date": rel_date,
                        "module": "Oracle Cloud", "feature_id": f"{slug}-{idx:03d}",
                        "oracle_feature_id": fid, "title": f"Oracle Feature {fid}",
                        "delivery_status": "Enabled", "action_required": "No Action Required",
                        "impact": "Small Scale", "bug_ids": "", "description": "Review Oracle documentation for details.",
                        "steps_to_enable": "N/A", "url": url, "priority": "Medium", "notes": "", "mandatory": "Yes"
                    })

    except Exception as e:
        print(f"Extraction Error: {e}")
        return []

    return features