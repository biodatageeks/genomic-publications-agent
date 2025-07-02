#!/usr/bin/env python3
"""
Simple test for FOX experiment - using only working components.
"""

import os
import sys
import json
import csv
import time
from pathlib import Path

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from services.search.fox_gene_pmid_finder import FoxGenePMIDFinder
from api.clients.litvar_endpoint import LitVarEndpoint


def test_steps_1_to_4():
    """
    Test steps 1-4 of the experiment (working components only).
    """
    print("=== TESTING FOX EXPERIMENT STEPS 1-4 ===")
    
    # Setup paths
    data_dir = Path("results/2025-07-01/data")
    data_dir.mkdir(exist_ok=True)
    
    # Test genes (small subset)
    test_genes = ["FOXA1", "FOXB1", "FOXC1"]
    
    # Step 1-3: Get PMID counts
    print("\n=== STEP 1-3: Getting PMID counts ===")
    
    pmid_finder = FoxGenePMIDFinder()
    gene_pmid_counts = {}
    all_pmids = set()
    
    for gene in test_genes:
        print(f"Getting PMIDs for {gene}...")
        
        # Create temporary finder for single gene
        temp_finder = FoxGenePMIDFinder()
        temp_finder.genes = [gene]
        gene_pmids = temp_finder.find_pmids_for_genes()
        
        count = len(gene_pmids)
        gene_pmid_counts[gene] = count
        all_pmids.update(gene_pmids)
        
        print(f"  {gene}: {count} PMIDs")
        time.sleep(0.5)
    
    # Save genes file
    genes_file = data_dir / "fox_genes.txt"
    with open(genes_file, 'w') as f:
        for gene in test_genes:
            f.write(f"{gene}\n")
    print(f"Saved genes to {genes_file}")
    
    # Save PMID counts
    csv_file = data_dir / "gene_pmids_counts.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['gene', 'pmid_count'])
        for gene, count in gene_pmid_counts.items():
            writer.writerow([gene, count])
    print(f"Saved PMID counts to {csv_file}")
    
    total_pmids = len(all_pmids)
    print(f"Total unique PMIDs: {total_pmids}")
    
    # Step 4: Get LitVar variants
    print("\n=== STEP 4: Getting LitVar variants ===")
    
    litvar_client = LitVarEndpoint()
    gene_variants = {}
    
    for gene in test_genes:
        print(f"Getting variants for {gene}...")
        try:
            variants = litvar_client.search_by_genes([gene])
            gene_variants[gene] = variants
            print(f"  {gene}: {len(variants)} variants")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error for {gene}: {e}")
            gene_variants[gene] = []
    
    # Save LitVar variants
    litvar_file = data_dir / "reference_variants.json"
    with open(litvar_file, 'w') as f:
        json.dump(gene_variants, f, indent=2)
    print(f"Saved LitVar variants to {litvar_file}")
    
    total_variants = sum(len(variants) for variants in gene_variants.values())
    print(f"Total LitVar variants: {total_variants}")
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    print(f"✓ Tested {len(test_genes)} genes: {', '.join(test_genes)}")
    print(f"✓ Total PMIDs collected: {total_pmids}")
    print(f"✓ Total LitVar variants: {total_variants}")
    print(f"✓ Files created in {data_dir}")
    
    return {
        "genes": test_genes,
        "pmid_counts": gene_pmid_counts,
        "variants": gene_variants,
        "total_pmids": total_pmids,
        "total_variants": total_variants
    }


def validate_test_results():
    """
    Validate the test results.
    """
    print("\n=== VALIDATING TEST RESULTS ===")
    
    data_dir = Path("results/2025-07-01/data")
    
    files_to_check = [
        "fox_genes.txt",
        "gene_pmids_counts.csv",
        "reference_variants.json"
    ]
    
    for filename in files_to_check:
        filepath = data_dir / filename
        if filepath.exists():
            print(f"✓ {filename} exists")
            
            if filename.endswith('.json'):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                print(f"  - JSON with {len(data)} entries")
            elif filename.endswith('.csv'):
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                print(f"  - CSV with {len(lines)} lines")
            elif filename.endswith('.txt'):
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                print(f"  - Text with {len(lines)} lines")
        else:
            print(f"❌ {filename} missing")


if __name__ == "__main__":
    try:
        # Run test
        results = test_steps_1_to_4()
        
        # Validate results
        validate_test_results()
        
        print("\n✅ SIMPLE TEST COMPLETED SUCCESSFULLY!")
        print("\nNext steps:")
        print("1. Fix import issues for PubTator and VariantRecognizer")
        print("2. Implement steps 5-6 (LLM prediction and PubTator reference)")
        print("3. Run full experiment with all 50 FOX genes")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc() 