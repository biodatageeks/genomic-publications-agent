#!/usr/bin/env python3
"""
Prosty test klienta PubTator dla analizy FOXF1
"""

import requests
import json

def test_pubtator_api():
    """Test bezpośredniego API PubTator"""
    pmid = "32735606"
    url = f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/{pmid}"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully retrieved PMID {pmid}")
            print(f"Title: {data.get('title', 'No title')}")
            return data
        else:
            print(f"HTTP Error {response.status_code}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_multiple_pmids():
    """Test kilku PMIDów z listy FOXF1"""
    pmids = ["32735606", "32719766", "10092306", "11278651"]
    
    results = []
    for pmid in pmids:
        print(f"\nTesting PMID: {pmid}")
        result = test_pubtator_api()
        if result:
            results.append(result)
    
    return results

if __name__ == "__main__":
    print("=== Test PubTator API ===")
    results = test_multiple_pmids()
    print(f"\nSuccessfully retrieved {len(results)} publications") 