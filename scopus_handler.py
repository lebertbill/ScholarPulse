import pandas as pd
from typing import List, Dict
import os

class ScopusHandler:
    def __init__(self):
        # Column mapping from Scopus to internal article schema
        self.column_map = {
            'Title': 'title',
            'Year': 'year',
            'Source title': 'journal',
            'DOI': 'DOI',
            'Abstract': 'abstract',
            'Author full names': 'authors'
        }

    def parse_csv(self, file_path_or_obj) -> List[Dict]:
        """Parses a Scopus export CSV (path or file-like object) and returns articles."""
        try:
            # pandas can handle both file paths and file-like objects (like UploadedFile)
            df = pd.read_csv(file_path_or_obj)
            # Filter and rename columns
            # Ensure all required columns exist
            existing_cols = [c for c in self.column_map.keys() if c in df.columns]
            df_slice = df[existing_cols].copy()
            df_slice = df_slice.rename(columns=self.column_map)
            
            # Additional processing: ensure ISSNs is present (even if empty) for ranker
            # Scopus doesn't always include ISSN in the basic export columns I saw,
            # but it uses 'Source title' which our ranker can use.
            if 'ISSNs' not in df_slice.columns:
                df_slice['ISSNs'] = [[] for _ in range(len(df_slice))]
            
            # Handle NaN in year and convert to int
            df_slice['year'] = pd.to_numeric(df_slice['year'], errors='coerce').fillna(0).astype(int)
            
            # Fill other NaNs
            df_slice = df_slice.fillna("")
            
            return df_slice.to_dict('records')
        except Exception as e:
            print(f"Error parsing Scopus CSV: {e}")
            return []

if __name__ == "__main__":
    # Test with the user's path
    handler = ScopusHandler()
    path = "/Users/lebertsambillgates/Downloads/scopus_export_Mar 25-2026_771ad8a6-37ab-49c3-8d5e-458b2c935949.csv"
    articles = handler.parse_csv(path)
    print(f"Parsed {len(articles)} articles.")
    if articles:
        print(f"First article: {articles[0].get('title')}")
