import pandas as pd
import os
from typing import List, Dict, Optional

class JournalRanker:
    def __init__(self, rank_file: str = "journal_rankings.csv"):
        self.rank_file = rank_file
        self.rank_data = None
        self._load_rankings()

    def _load_rankings(self):
        """Loads journal rankings from a CSV file (SJR format)."""
        if not os.path.exists(self.rank_file):
            print(f"[Ranker] Warning: Ranking file '{self.rank_file}' not found.")
            return

        try:
            # SJR files usually use ';' as separator
            self.rank_data = pd.read_csv(self.rank_file, sep=';', low_memory=False)
            # Normalize column names
            self.rank_data.columns = [c.lower() for c in self.rank_data.columns]
            print(f"[Ranker] Loaded {len(self.rank_data)} journals.")
        except Exception as e:
            print(f"[Ranker] Error loading ranking file: {e}")

    def _parse_best_from_categories(self, categories: str) -> Optional[str]:
        """Parses the best quartile (e.g., Q1) from a semicolon-separated categories string."""
        if not isinstance(categories, str) or not categories:
            return None
        
        # Scimagojr format: "Category1 (Q1); Category2 (Q2)"
        import re
        quartiles = re.findall(r'\(Q([1-4])\)', categories)
        if not quartiles:
            return None
        
        # Return the minimum (best) quartile found
        return f"Q{min(quartiles)}"

    def get_rank(self, journal_name: str, issns: List[str]) -> Optional[str]:
        """Returns the best SJR Best Quartile (e.g., Q1, Q2) for a journal."""
        if self.rank_data is None:
            return None

        # Try matching by ISSN first (more reliable)
        match = pd.DataFrame()
        if issns:
            for issn in issns:
                clean_issn = issn.replace("-", "")
                m = self.rank_data[self.rank_data['issn'].str.contains(clean_issn, na=False)]
                if not m.empty:
                    match = m
                    break

        # Fallback to journal name match if no ISSN match
        if match.empty:
            match = self.rank_data[self.rank_data['title'].str.lower() == journal_name.lower()]

        if not match.empty:
            row = match.iloc[0]
            rank = row.get('sjr best quartile', None)
            
            # If no direct rank, try parsing from categories
            if not isinstance(rank, str) or rank in ["", "-", "None", "nan"]:
                categories = row.get('categories', "")
                rank = self._parse_best_from_categories(categories)
            
            return rank if isinstance(rank, str) and rank.startswith("Q") else None

        return None

    def is_in_quartiles(self, journal_name: str, issns: List[str], target_quartiles: List[str]) -> bool:
        """Checks if a journal is in at least one of the target quartiles (e.g., ['Q1', 'Q2'])."""
        rank = self.get_rank(journal_name, issns)
        return rank in target_quartiles
