#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demonstration of the PubTator client for retrieving and analyzing biomedical publications.
This script demonstrates the basic functions of the PubTator client, such as retrieving publications,
searching, and extracting annotations.
"""

import logging
import json
from src.pubtator_client.pubtator_client import PubTatorClient

def main():
    """Main demonstration function."""
    # Logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize the PubTator client
    client = PubTatorClient()
    
    # Example 1: Retrieving publications by PMID identifiers
    print("=" * 80)
    print("Example 1: Retrieving publications by PMID identifiers")
    print("=" * 80)
    
    pmids = ["34197738", "33429114"]  # Selected publications about COVID-19
    print(f"Retrieving publications for PMIDs: {', '.join(pmids)}")
    
    try:
        publications = client.get_publications_by_pmids(pmids)
        
        for i, pub in enumerate(publications, 1):
            print(f"\nPublication {i}:")
            print(f"ID: {pub.id}")
            
            # Display title (the first text passage is usually the title)
            title = pub.passages[0].text if pub.passages else "No title"
            print(f"Title: {title}")
            
            # Extract gene annotations
            genes = client.extract_gene_annotations(pub)
            if genes:
                print(f"Found {len(genes)} gene annotations (first 3):")
                for gene in genes[:3]:
                    print(f"  - {gene['text']} (ID: {gene['normalized_id']})")
            else:
                print("No gene annotations found.")
            
            # Extract disease annotations
            diseases = client.extract_disease_annotations(pub)
            if diseases:
                print(f"Found {len(diseases)} disease annotations (first 3):")
                for disease in diseases[:3]:
                    print(f"  - {disease['text']} (ID: {disease['normalized_id']})")
            else:
                print("No disease annotations found.")
            
            # Extract genetic variant annotations
            variants = client.extract_variant_annotations(pub)
            if variants:
                print(f"Found {len(variants)} variant annotations (first 3):")
                for variant in variants[:3]:
                    print(f"  - {variant['text']} (ID: {variant['normalized_id']})")
            else:
                print("No genetic variant annotations found.")
            
            # Extract tissue specificity annotations
            tissues = client.extract_tissue_specificity(pub)
            if tissues:
                print(f"Found {len(tissues)} tissue annotations (first 3):")
                for tissue in tissues[:3]:
                    print(f"  - {tissue['text']} (ID: {tissue['normalized_id']})")
            else:
                print("No tissue specificity annotations found.")
            
    except Exception as e:
        print(f"An error occurred while retrieving publications: {e}")
    
    # Example 2: Searching for publications
    print("\n" + "=" * 80)
    print("Example 2: Searching for publications")
    print("=" * 80)
    
    query = "BRCA1 AND cancer AND breast"
    print(f"Searching for publications with query: '{query}'")
    
    try:
        results = client.search_publications(query, concepts=["Gene", "Disease", "Mutation"])
        print(f"Found {len(results)} publications")
        
        # Display details of the first 2 publications
        for i, pub in enumerate(results[:2], 1):
            print(f"\nResult {i}:")
            title = pub.passages[0].text if pub.passages else "No title"
            print(f"Title: {title}")
            
            # Get all annotations and group by type
            annotations = client.extract_all_annotations(pub)
            
            print("Annotation types and their count:")
            for anno_type, items in annotations.items():
                print(f"  - {anno_type}: {len(items)} annotations")
        
    except Exception as e:
        print(f"An error occurred while searching for publications: {e}")
    
    # Example 3: Saving results to a JSON file
    print("\n" + "=" * 80)
    print("Example 3: Saving results to a JSON file")
    print("=" * 80)
    
    try:
        # Retrieve one publication about COVID-19
        pub = client.get_publication_by_pmid("33429114")
        
        if pub:
            # Extract all annotations
            annotations = client.extract_all_annotations(pub)
            
            # Prepare data for saving
            output_data = {
                "pmid": pub.id,
                "title": pub.passages[0].text if pub.passages else "No title",
                "annotations": annotations
            }
            
            # Save to JSON file
            output_file = "publication_annotations.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"Saved annotations to file: {output_file}")
            print(f"Saved annotation types: {', '.join(annotations.keys())}")
        else:
            print("No publication found.")
            
    except Exception as e:
        print(f"An error occurred while saving results: {e}")


if __name__ == "__main__":
    main() 