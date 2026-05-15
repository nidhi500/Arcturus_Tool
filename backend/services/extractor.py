import asyncio
import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Limit parallel requests to 10 to prevent Oracle from blocking the Render IP
semaphore = asyncio.Semaphore(10)

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

async def fetch_detail_page(client, feature):
    """Visits the sub-link for a single feature to extract deep details."""
    async with semaphore:
        try:
            url = feature.get('url', '')
            if not url or "javascript" in url: return feature

            response = await client.get(url, timeout=15.0)
            if response.status_code != 200: return feature

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. SMART DESCRIPTION SEARCH
            desc_area = soup.find('section', id=re.compile(r'description|overview|feature', re.I)) or \
                        soup.find('div', class_=re.compile(r'section|content', re.I))
            
            if desc_area:
                paragraphs = desc_area.find_all('p')
                text = " ".join([p.get_text().strip() for p in paragraphs[:2] if len(p.get_text()) > 20])
                feature['description'] = text[:600] + "..." if len(text) > 600 else text

            # 2. SMART ENABLEMENT SEARCH
            steps_area = soup.find('section', id=re.compile(r'steps-to-enable|setup|enable', re.I)) or \
                         soup.find(lambda tag: tag.name in ['h2', 'h3'] and "Steps" in tag.text)
            
            if steps_area:
                # If we found a header, get the next siblings
                if steps_area.name in ['h2', 'h3']:
                    steps_content = []
                    for sib in steps_area.find_next_siblings():
                        if sib.name in ['h2', 'h3']: break
                        steps_content.append(sib.get_text().strip())
                    feature['steps_to_enable'] = " ".join(steps_content)[:800]
                else:
                    feature['steps_to_enable'] = steps_area.get_text(separator=' ').strip()[:800]
                
                # DYNAMIC PRIORITY
                check_text = feature['steps_to_enable'].lower()
                if any(word in check_text for word in ["opt-in", "setup", "configure", "enable"]):
                    feature['action_required'] = "Setup Required"
                    feature['priority'] = "High"
                else:
                    feature['action_required'] = "No Action Required"
                    feature['priority'] = "Medium"
            else:
                feature['steps_to_enable'] = "Automatically enabled. No configuration required."
                feature['priority'] = "Low"

            # 3. ORACLE ID & BUGS
            id_match = re.search(r"\b[FT]\d{5,6}\b", response.text)
            if id_match: feature['oracle_feature_id'] = id_match.group().upper()
            
            bugs = re.findall(r"\b\d{8}\b", response.text)
            feature['bug_ids'] = ", ".join(set(bugs)) if bugs else "None"

        except Exception as e:
            print(f"Error crawling {feature['title']}: {e}")
        return feature

async def enrich_all_features(injected_features):
    """The engine that powers the 60-feature crawl."""
    headers = {"User-Agent": "OQUAT-Consultant-Bot/1.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [fetch_detail_page(client, f) for f in injected_features]
        return await asyncio.gather(*tasks)

# Keep your existing extract_feature_links function but make sure it returns the list of URLs

# ... (all your existing fetch_detail_page and enrich_all_features code)

async def extract_features(url: str):
    """
    Dummy/Fallback function to satisfy the import in main.py.
    Since we are now using 'enrich_all_features' from the extension,
    this just needs to exist to prevent the ImportError.
    """
    return []

# Ensure these names exactly match what you are importing in main.py

def extract_feature_links(index_url):
    """Fallback link extractor using httpx to avoid 'requests' dependency issues."""
    if index_url.endswith("/"):
        index_url += "index.html"

    try:
        import httpx  # Use httpx since it's already in your project
        headers = {"User-Agent": "Mozilla/5.0"}
        # Use a synchronous call here since this specific function isn't async
        with httpx.Client(headers=headers, follow_redirects=True, timeout=10) as client:
            response = client.get(index_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            feature_links = []
            for link in soup.find_all("a", href=True):
                title = link.get_text().strip()
                href = link.get("href")
                if len(title) > 10 and any(x in href for x in ["-wn-f", "-wn-t"]):
                    feature_links.append({
                        "title": title,
                        "url": urljoin(index_url, href)
                    })
            return feature_links
    except Exception as e:
        print(f"Link extraction failed: {e}")
        return []