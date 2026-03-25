import httpx
import asyncio
from bs4 import BeautifulSoup
import os
from typing import List, Dict, Optional

class CrossrefClient:
    def __init__(self, email: str = None):
        self.email = email or os.getenv("CROSSREF_EMAIL", "scholarpulse@example.com")
        self.base_url = "https://api.crossref.org/works"
        self.headers = {"User-Agent": f"ScholarPulse/1.0 (mailto:{self.email})"}

    async def search_articles(self, keywords: str, max_results: int = 20, fetch_all: bool = False, year_range: Optional[tuple] = None) -> List[Dict]:
        """Searches Crossref for articles matching the keywords. Supports cursor marking and year filtering."""
        all_items = []
        cursor = "*"
        

        limit = max_results if not fetch_all else 3000000 
        
        base_filter = "type:journal-article"
        if year_range:
            base_filter += f",from-pub-date:{year_range[0]},until-pub-date:{year_range[1]}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                while len(all_items) < limit:
                    params = {
                        "query": keywords,
                        "rows": 1000 if fetch_all else max_results,
                        "filter": base_filter,
                        "cursor": cursor
                    }
                    
                    print(f"[Crossref] Searching (count: {len(all_items)})...")
                    response = await client.get(self.base_url, params=params, headers=self.headers)
                    response.raise_for_status()
                    data = response.json().get("message", {})
                    items = data.get("items", [])
                    next_cursor = data.get("next-cursor")
                    
                    if not items:
                        break
                        
                    all_items.extend([self._parse_item(item) for item in items])
                    
                    if not fetch_all or next_cursor == cursor:
    
                        if not fetch_all or len(items) < 1000:
                            break
                        
                    cursor = next_cursor
                        
                return all_items
            except Exception as e:
                print(f"[Crossref] Error during search: {e}")
                return all_items

    def _parse_item(self, item: Dict) -> Dict:
        """Parses a Crossref single item into a simpler dictionary."""
        title = item.get("title", ["No Title"])[0]
        doi = item.get("DOI", "")
        journal = item.get("container-title", ["Unknown Journal"])[0]
        issns = item.get("ISSN", [])
        
        abstract_html = item.get("abstract", "")
        abstract = ""
        if abstract_html:
            soup = BeautifulSoup(abstract_html, 'html.parser')
            abstract = soup.get_text(separator=' ', strip=True)

        return {
            "title": title,
            "DOI": doi,
            "journal": journal,
            "ISSNs": issns,
            "abstract": abstract,
            "year": item.get("published", {}).get("date-parts", [[None]])[0][0]
        }

if __name__ == "__main__":
    async def test():
        client = CrossrefClient()
        results = await client.search_articles("2D magnets", max_results=5)
        for r in results:
            print(f"- {r['title']} ({r['journal']})")

    asyncio.run(test())
