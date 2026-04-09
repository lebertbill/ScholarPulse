import asyncio
import argparse
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import os

from crossref_client import CrossrefClient
from journal_ranker import JournalRanker
from llm_verifier import LLMVerifier
from scopus_handler import ScopusHandler

async def main(keywords: str, search_field: str, max_results: int, mode: str, model: str, scopus_path: str = None):
    load_dotenv()
    
    # 1. Get Articles (from Scopus CSV or Crossref API)
    if scopus_path:
        print(f"\n--- ScholarPulse: Importing from Scopus {os.path.basename(scopus_path)} ---")
        handler = ScopusHandler()
        raw_articles = handler.parse_csv(scopus_path)
        if not keywords:
            keywords = os.path.basename(scopus_path).replace(".csv", "")
    else:
        print(f"\n--- ScholarPulse: Searching Crossref for '{keywords}' ---")
        client = CrossrefClient()
        raw_articles = await client.search_articles(keywords, max_results=max_results)
    
    print(f"Found {len(raw_articles)} candidate articles.")

    # 2. Filter by Journal Rank (Q1/Q2)
    ranker = JournalRanker()
    q_filtered = []
    for art in raw_articles:
        rank = ranker.get_rank(art.get('journal', ''), art.get('ISSNs', []))
        art['quartile'] = rank or "N/A"
        # Optional: check if internal rank check is needed or if Q1/Q2 is default
        if rank in ["Q1", "Q2"]:
            q_filtered.append(art)
    
    print(f"After Q1/Q2 filtering: {len(q_filtered)} articles remaining.")

    # 3. Verify with LLM
    verifier = LLMVerifier(mode=mode, model=model)
    final_results = []
    
    for art in tqdm(q_filtered, desc="Verifying Relevance"):
        verif = await verifier.verify_relevance(art['title'], art['abstract'], search_field)
        art['is_relevant'] = verif.get('is_relevant', False)
        art['llm_reason'] = verif.get('reason', '')
        
        if art['is_relevant']:
            final_results.append(art)

    print(f"Final relevant articles: {len(final_results)}")

    # 4. Save to Excel
    if final_results:
        df = pd.DataFrame(final_results)
        safe_keywords = keywords.replace(' ', '_').replace('/', '_')
        output_file = f"scholarpulse_{safe_keywords}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"Results saved to {output_file}")
    else:
        print("No relevant articles found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ScholarPulse: Filter literature by rank and relevance.")
    parser.add_argument("--keywords", type=str, help="Search keywords for Crossref (not required if using --scopus)")
    parser.add_argument("--scopus", type=str, help="Path to a Scopus export CSV file")
    parser.add_argument("--field", type=str, required=True, help="Detailed research field for LLM verification")
    parser.add_argument("--max", type=int, default=50, help="Max results to fetch from Crossref")
    parser.add_argument("--mode", type=str, default="local", choices=["local", "remote"], help="LLM mode")
    parser.add_argument("--model", type=str, default="gemma2:9b", help="LLM model name")
    
    args = parser.parse_args()
    
    if not args.scopus and not args.keywords:
        parser.error("Either --keywords (for Crossref) or --scopus (for CSV file) must be provided.")
        
    asyncio.run(main(args.keywords, args.field, args.max, args.mode, args.model, scopus_path=args.scopus))
