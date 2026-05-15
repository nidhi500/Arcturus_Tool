import asyncio
import httpx
from bs4 import BeautifulSoup
import re

# Limit parallel requests to 10 to avoid being blocked by Oracle
semaphore = asyncio.Semaphore(10)

async def fetch_detail_page(client, feature):
    """Visits the sub-link for a single feature to extract deep details."""
    async with semaphore:
        try:
            # Oracle URLs are often relative; ensure we have a full URL
            url = feature.get('url', '')
            if not url or url.startswith('javascript'):
                return feature

            response = await client.get(url, timeout=15.0)
            if response.status_code != 200:
                return feature

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Extract Description
            # Oracle uses <section id="description"> or generic <div> classes
            desc_sect = soup.find('section', {'id': 'description'}) or soup.find('div', {'class': 'section'})
            if desc_sect:
                # Get the first two paragraphs for a clean summary
                paragraphs = desc_sect.find_all('p')
                text = " ".join([p.get_text() for p in paragraphs[:2]])
                feature['description'] = text[:1000] if text else "Review full documentation for details."
            
            # 2. Extract Steps to Enable (The "Consulting Gold")
            steps_sect = soup.find('section', {'id': 'steps-to-enable'}) or soup.find('div', {'id': 'setup'})
            if steps_sect:
                feature['steps_to_enable'] = steps_sect.get_text(separator=' ').strip()
                # Determine Action Required based on Enablement text
                if "opt-in" in feature['steps_to_enable'].lower() or "setup" in feature['steps_to_enable'].lower():
                    feature['action_required'] = "Setup Required"
                    feature['priority'] = "High"
                else:
                    feature['action_required'] = "No Action Required"
                    feature['priority'] = "Medium"
            else:
                feature['steps_to_enable'] = "Automatically enabled."
                feature['action_required'] = "No Action Required"
                feature['priority'] = "Low"

            # 3. Extract Bug IDs (8-digit numbers)
            bug_match = re.findall(r'\b\d{8}\b', response.text)
            feature['bug_ids'] = ", ".join(set(bug_match)) if bug_match else "None"
            
            # 4. Set default Impact if missing
            if not feature.get('impact'):
                feature['impact'] = "Significant" if feature['priority'] == "High" else "Small Scale"

        except Exception as e:
            print(f"Error crawling {feature.get('title')}: {e}")
            feature['description'] = "Details available in Oracle Cloud Readiness."
            feature['steps_to_enable'] = "Refer to source URL."
        
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