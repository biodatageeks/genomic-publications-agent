#!/usr/bin/env python3
"""
Debug PubTator API calls to fix the 0 documents issue.
"""

import requests
import json
import time
from experiment_modules import SimplePubTatorClient

def test_pubtator_api_directly():
    """Test PubTator API directly."""
    print("=== Testing PubTator API Directly ===")
    
    # Test a known PMID
    test_pmid = "32735606"
    base_url = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
    
    # Try different endpoint formats
    endpoints = [
        f"{base_url}/publications/export/biocjson?pmids={test_pmid}",
        f"{base_url}/publications/export/biocjson?pmids={test_pmid}&concepts=gene,mutation",
        f"{base_url}/publications/{test_pmid}",
        f"{base_url}/publications?pmids={test_pmid}",
    ]
    
    for i, url in enumerate(endpoints):
        print(f"\nTesting endpoint {i+1}: {url}")
        try:
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"JSON data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    if isinstance(data, dict) and 'documents' in data:
                        docs = data['documents']
                        print(f"Documents found: {len(docs)}")
                        if docs:
                            doc = docs[0]
                            print(f"First doc keys: {list(doc.keys())}")
                            if 'passages' in doc:
                                print(f"Passages: {len(doc['passages'])}")
                    
                except json.JSONDecodeError:
                    print(f"Response text (first 200 chars): {response.text[:200]}")
            else:
                print(f"Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")
        
        time.sleep(1)

def test_simplified_client():
    """Test our simplified client."""
    print("\n=== Testing Simplified Client ===")
    
    client = SimplePubTatorClient()
    
    # Test with known PMIDs
    test_pmids = ["32735606", "33028563"]
    
    for pmid in test_pmids:
        print(f"\nTesting PMID: {pmid}")
        try:
            docs = client.get_publications_by_pmids([pmid])
            print(f"Retrieved {len(docs)} documents")
            
            if docs:
                doc = docs[0]
                print(f"Document ID: {doc.id}")
                print(f"Passages: {len(doc.passages)}")
                
                for i, passage in enumerate(doc.passages):
                    print(f"  Passage {i}: {len(passage.text)} chars, {len(passage.annotations)} annotations")
            
        except Exception as e:
            print(f"Error: {e}")

def test_fox_pmids():
    """Test with actual FOX PMIDs."""
    print("\n=== Testing with FOX PMIDs ===")
    
    import os
    import sys
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from services.search.fox_gene_pmid_finder import FoxGenePMIDFinder
    
    # Get some FOXB1 PMIDs (smaller number)
    finder = FoxGenePMIDFinder()
    finder.genes = ["FOXB1"]
    pmids = list(finder.find_pmids_for_genes())
    
    print(f"Found {len(pmids)} PMIDs for FOXB1")
    
    # Test first 3 PMIDs
    test_pmids = pmids[:3]
    print(f"Testing PMIDs: {test_pmids}")
    
    client = SimplePubTatorClient()
    docs = client.get_publications_by_pmids(test_pmids)
    
    print(f"Retrieved {len(docs)} documents")
    
    for doc in docs:
        print(f"Doc {doc.id}: {len(doc.passages)} passages")
        for passage in doc.passages:
            print(f"  Passage: {len(passage.text)} chars, {len(passage.annotations)} annotations")
            
            # Extract variant annotations
            variants = client.extract_variant_annotations(doc)
            print(f"  Variants found: {len(variants)}")
            for variant in variants[:3]:  # Show first 3
                print(f"    {variant}")

if __name__ == "__main__":
    test_pubtator_api_directly()
    test_simplified_client()
    test_fox_pmids() 