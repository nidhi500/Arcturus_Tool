import asyncio
import httpx
from bs4 import BeautifulSoup
import re

# Limit parallel requests to 10 to avoid being blocked by Oracle
semaphore = asyncio.Semaphore(10)

async def fetch_detail_page(client, feature):
    """Deep-scrapes sub-pages to fill Description, Steps, and Priority."""
    async with semaphore:
        try:
            url = feature.get('url', '')
            if not url or "javascript" in url: return feature

            response = await client.get(url, timeout=15.0)
            if response.status_code != 200: return feature

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. SMART DESCRIPTION SEARCH
            # Look for ANY section that smells like a description or overview
            desc_area = soup.find('section', id=re.compile(r'description|overview|feature', re.I)) or \
                        soup.find('div', class_=re.compile(r'section|content', re.I))
            
            if desc_area:
                paragraphs = desc_area.find_all('p')
                # Join first two paragraphs for a professional summary
                text = " ".join([p.get_text().strip() for p in paragraphs[:2]])
                feature['description'] = text[:600] + "..." if len(text) > 600 else text

            # 2. SMART ENABLEMENT SEARCH
            # Look for the setup instructions
            steps_area = soup.find('section', id=re.compile(r'steps-to-enable|setup|enable', re.I))
            if steps_area:
                steps_text = steps_area.get_text(separator=' ').strip()
                feature['steps_to_enable'] = steps_text
                
                # 3. DYNAMIC PRIORITY LOGIC
                # If the feature requires setup or opt-in, it's high priority
                check_text = steps_text.lower()
                if any(word in check_text for word in ["opt-in", "setup", "configure", "enable"]):
                    feature['action_required'] = "Setup Required"
                    feature['priority'] = "High"
                    feature['impact'] = "Significant"
                else:
                    feature['action_required'] = "No Action Required"
                    feature['priority'] = "Medium"
            else:
                feature['steps_to_enable'] = "Automatically enabled. No configuration required."
                feature['priority'] = "Low"

            # 4. BUG ID EXTRACTION
            bugs = re.findall(r'\b\d{8}\b', response.text)
            feature['bug_ids'] = ", ".join(set(bugs)) if bugs else "None"

        except Exception as e:
            print(f"Crawl Error [{feature.get('title')}]: {e}")
            
        return feature

async def enrich_all_features(injected_features):
    """Parallel crawler to fill the empty columns for all features."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [fetch_detail_page(client, f) for f in injected_features]
        enriched_features = await asyncio.gather(*tasks)
    return enriched_features

async def extract_features(url: str):
    """Fallback if no data is injected from extension."""
    # This remains as your basic scraper from previous steps
    return []