import asyncio
import httpx
from bs4 import BeautifulSoup
import re

# Limit parallel requests to 10 to avoid being blocked by Oracle
semaphore = asyncio.Semaphore(10)

async def fetch_detail_page(client, feature):
    try:
        response = await client.get(feature['url'], timeout=15.0)
        if response.status_code != 200: return feature

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. FIND DESCRIPTION: Look for the main content div or sections
        # Oracle uses different IDs like 'description', 'feature-overview', etc.
        desc_area = soup.find('section', id=re.compile('description|overview', re.I)) or \
                    soup.find('div', class_='section')
        
        if desc_area:
            # Grab all paragraphs in that section
            p_text = " ".join([p.get_text().strip() for p in desc_area.find_all('p')])
            feature['description'] = p_text[:600] + "..." if len(p_text) > 600 else p_text

        # 2. FIND STEPS TO ENABLE: Look for the 'setup' or 'enablement' section
        steps_area = soup.find('section', id=re.compile('steps-to-enable|how-to-enable|setup', re.I))
        if steps_area:
            feature['steps_to_enable'] = steps_area.get_text(separator=' ').strip()
            
            # 3. DYNAMIC PRIORITY: If it's not automatic, it's High Priority
            setup_text = feature['steps_to_enable'].lower()
            if any(word in setup_text for word in ["opt-in", "setup", "enable", "config"]):
                feature['action_required'] = "Setup Required"
                feature['priority'] = "High"
                feature['impact'] = "Significant"
            else:
                feature['action_required'] = "No Action Required"
                feature['priority'] = "Medium"
        else:
            feature['steps_to_enable'] = "Automatically enabled. Review for business impact."
            feature['priority'] = "Low"

    except Exception as e:
        print(f"Detail Fetch Error for {feature['title']}: {e}")
    
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