#!/usr/bin/env python3
"""
Debug annotations from PubTator to see what types we get.
"""

import os
import sys
from collections import Counter

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from services.search.fox_gene_pmid_finder import FoxGenePMIDFinder
from experiment_modules import SimplePubTatorClient

def analyze_pubtator_annotations():
    """Analyze what types of annotations we get from PubTator."""
    print("=== Analyzing PubTator Annotations ===")
    
    # Get some FOXB1 PMIDs
    finder = FoxGenePMIDFinder()
    finder.genes = ["FOXB1"]
    pmids = list(finder.find_pmids_for_genes())[:5]  # Get 5 PMIDs
    
    print(f"Testing PMIDs: {pmids}")
    
    client = SimplePubTatorClient()
    docs = client.get_publications_by_pmids(pmids)
    
    print(f"Retrieved {len(docs)} documents\n")
    
    all_annotation_types = []
    all_annotation_texts = []
    
    for doc in docs:
        print(f"Document {doc.id}:")
        
        for i, passage in enumerate(doc.passages):
            print(f"  Passage {i}: {len(passage.annotations)} annotations")
            
            for annotation in passage.annotations:
                annotation_type = annotation.infons.get('type', 'unknown').lower()
                all_annotation_types.append(annotation_type)
                all_annotation_texts.append(annotation.text)
                
                print(f"    Type: {annotation_type}, Text: '{annotation.text}', "
                      f"Infons: {annotation.infons}")
        
        print()
    
    print("=== SUMMARY ===")
    print(f"Total annotations: {len(all_annotation_types)}")
    
    print("\nAnnotation types count:")
    type_counter = Counter(all_annotation_types)
    for annotation_type, count in type_counter.most_common():
        print(f"  {annotation_type}: {count}")
    
    print("\nSample annotation texts:")
    for text in set(all_annotation_texts)[:10]:
        print(f"  '{text}'")
    
    print("\nCurrent filter in extract_variant_annotations:")
    print("  ['mutation', 'variant', 'sequence_variant', 'dnamutation']")
    
    # Check if any match our filters
    variant_types = ['mutation', 'variant', 'sequence_variant', 'dnamutation']
    matching_types = [t for t in type_counter.keys() if t in variant_types]
    
    if matching_types:
        print(f"\nMATCHING TYPES FOUND: {matching_types}")
    else:
        print(f"\nNO MATCHING TYPES! Consider adding these to filter:")
        for annotation_type, count in type_counter.most_common(5):
            print(f"  '{annotation_type}' ({count} annotations)")

if __name__ == "__main__":
    analyze_pubtator_annotations() 