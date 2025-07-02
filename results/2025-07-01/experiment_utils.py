#!/usr/bin/env python3
"""
Experiment Utilities - 01.07.2025

Helper functions for debugging and testing the FOX variant experiment.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Set
import sys
import os

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)


def test_small_subset_experiment():
    """
    Test the experiment with a small subset of genes.
    """
    from main_fox_experiment import FoxVariantExperiment
    
    # Create test experiment with limited genes
    experiment = FoxVariantExperiment()
    
    # Test with first 3 FOX genes only
    test_genes = ["FOXA1", "FOXB1", "FOXC1"]
    
    # Create temporary gene file
    test_genes_file = experiment.data_dir / "test_fox_genes.txt"
    with open(test_genes_file, 'w') as f:
        for gene in test_genes:
            f.write(f"{gene}\n")
    
    print(f"Testing experiment with genes: {test_genes}")
    
    try:
        # Test step 1-3: PMID counts
        print("\n=== Testing PMID collection ===")
        gene_pmid_counts = experiment.step1_load_genes_and_get_pmids(str(test_genes_file))
        print(f"PMID counts: {gene_pmid_counts}")
        
        # Test step 4: LitVar variants
        print("\n=== Testing LitVar variant extraction ===")
        litvar_variants = experiment.step4_extract_reference_variants_litvar(test_genes)
        for gene, variants in litvar_variants.items():
            print(f"{gene}: {len(variants)} variants")
        
        print("\n=== Small subset test completed successfully ===")
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


def validate_experiment_data(data_dir: str = "results/2025-07-01/data"):
    """
    Validate that all required experiment data files exist and are valid.
    
    Args:
        data_dir: Directory containing experiment data
    """
    data_path = Path(data_dir)
    
    required_files = [
        "fox_genes.txt",
        "gene_pmids_counts.csv", 
        "reference_variants.json",
        "predicted_variants.json",
        "pubtator_variants.json"
    ]
    
    print("=== Validating experiment data ===")
    
    for filename in required_files:
        filepath = data_path / filename
        if filepath.exists():
            print(f"✓ {filename} exists")
            
            # Validate content based on file type
            if filename.endswith('.json'):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    print(f"  - Valid JSON with {len(data)} top-level entries")
                except json.JSONDecodeError as e:
                    print(f"  - ❌ Invalid JSON: {e}")
            
            elif filename.endswith('.csv'):
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                    print(f"  - CSV with {len(lines)} lines")
                except Exception as e:
                    print(f"  - ❌ Error reading CSV: {e}")
            
            elif filename.endswith('.txt'):
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                    print(f"  - Text file with {len(lines)} lines")
                except Exception as e:
                    print(f"  - ❌ Error reading text file: {e}")
        else:
            print(f"❌ {filename} missing")


def analyze_gene_variant_distribution(data_dir: str = "results/2025-07-01/data"):
    """
    Analyze the distribution of variants across genes.
    
    Args:
        data_dir: Directory containing experiment data
    """
    data_path = Path(data_dir)
    
    print("=== Analyzing variant distribution ===")
    
    # Load all variant files
    variant_files = {
        "LitVar": "reference_variants.json",
        "LLM Predicted": "predicted_variants.json", 
        "PubTator": "pubtator_variants.json"
    }
    
    for source, filename in variant_files.items():
        filepath = data_path / filename
        
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                print(f"\n{source} variants:")
                total_variants = 0
                
                for gene, variants in data.items():
                    variant_count = len(variants) if variants else 0
                    total_variants += variant_count
                    print(f"  {gene}: {variant_count} variants")
                
                print(f"  Total: {total_variants} variants across {len(data)} genes")
                
            except Exception as e:
                print(f"Error analyzing {source}: {e}")
        else:
            print(f"{source} data not found")


def debug_variant_normalization():
    """
    Test variant normalization function with example variants.
    """
    from variant_metrics_evaluator import VariantMetricsEvaluator
    
    evaluator = VariantMetricsEvaluator()
    
    test_variants = [
        "c.123A>G",
        "c.123a>g",
        "p.Val600Glu",
        "p.val600glu",
        "p.V600E",
        "rs123456",
        "Variant: c.456T>C",
        "mutation: p.Arg789His"
    ]
    
    print("=== Testing variant normalization ===")
    
    for variant in test_variants:
        normalized = evaluator.normalize_variant(variant)
        print(f"'{variant}' → '{normalized}'")


def check_api_connections():
    """
    Check if all API connections are working.
    """
    print("=== Checking API connections ===")
    
    try:
        # Test PubTator
        from api.clients.pubtator_client import PubTatorClient
        pubtator = PubTatorClient()
        test_pub = pubtator.get_publication_by_pmid("32735606")
        print("✓ PubTator API working")
    except Exception as e:
        print(f"❌ PubTator API error: {e}")
    
    try:
        # Test LitVar
        from api.clients.litvar_endpoint import LitVarEndpoint
        litvar = LitVarEndpoint()
        test_variants = litvar.search_by_genes(["BRCA1"])
        print("✓ LitVar API working")
    except Exception as e:
        print(f"❌ LitVar API error: {e}")
    
    try:
        # Test FOX PMID finder
        from services.search.fox_gene_pmid_finder import FoxGenePMIDFinder
        finder = FoxGenePMIDFinder()
        finder.genes = ["BRCA1"]
        pmids = finder.find_pmids_for_genes()
        print("✓ FOX PMID finder working")
    except Exception as e:
        print(f"❌ FOX PMID finder error: {e}")
    
    try:
        # Test Variant Recognizer
        from analysis.bio_ner.variant_recognizer import VariantRecognizer
        recognizer = VariantRecognizer()
        test_text = "The BRCA1 c.123A>G mutation is pathogenic."
        variants = recognizer.recognize_variants_text(test_text)
        print("✓ Variant Recognizer working")
    except Exception as e:
        print(f"❌ Variant Recognizer error: {e}")


def create_experiment_readme():
    """
    Create a README file for the experiment.
    """
    readme_content = """# FOX Genes Variant Extraction Experiment - 01.07.2025

## Overview

This experiment compares LLM-based variant extraction against reference sources for FOX family genes.

## Experiment Steps

1. **Load FOX genes** from `external_data/enhancer_tables_from_uw/fox_unique_genes.txt`
2. **Get PMID counts** for each gene using NCBI E-utilities
3. **Extract reference variants** from LitVar based on gene names
4. **Extract predicted variants** from publication texts using LLM (max 100 pubs/gene)
5. **Extract reference variants** from PubTator annotations
6. **Calculate metrics** comparing predicted vs reference variants

## File Structure

```
results/2025-07-01/
├── data/
│   ├── fox_genes.txt                    # FOX family genes (50 genes)
│   ├── gene_pmids_counts.csv           # PMID counts per gene
│   ├── reference_variants.json         # LitVar variants by gene
│   ├── predicted_variants.json         # LLM-predicted variants
│   └── pubtator_variants.json          # PubTator reference variants
├── reports/
│   ├── llm_vs_pubtator_metrics.json    # Detailed metrics vs PubTator
│   ├── llm_vs_litvar_metrics.json      # Detailed metrics vs LitVar
│   ├── metrics_summary.csv             # Summary metrics
│   └── experiment_summary.md           # Human-readable report
├── logs/
│   └── experiment.log                  # Experiment execution log
├── main_fox_experiment.py              # Main experiment orchestrator
├── variant_metrics_evaluator.py       # Metrics calculation
├── experiment_utils.py                 # Helper functions
└── README.md                           # This file
```

## Usage

### Run Full Experiment
```bash
cd results/2025-07-01
python main_fox_experiment.py
```

### Calculate Metrics (after data collection)
```bash
python variant_metrics_evaluator.py
```

### Test with Small Subset
```bash
python -c "from experiment_utils import test_small_subset_experiment; test_small_subset_experiment()"
```

### Validate Data
```bash
python -c "from experiment_utils import validate_experiment_data; validate_experiment_data()"
```

### Check API Connections
```bash
python -c "from experiment_utils import check_api_connections; check_api_connections()"
```

## Metrics Calculated

- **Precision**: TP / (TP + FP) - How many predicted variants are correct
- **Recall**: TP / (TP + FN) - How many actual variants were found
- **F1-Score**: 2 * (Precision * Recall) / (Precision + Recall) - Harmonic mean

## Data Sources

- **FOX Genes**: 50 genes from enhancer tables
- **Publications**: Retrieved via NCBI E-utilities based on gene names
- **LLM**: Meta-Llama-3.1-8B-Instruct for variant extraction
- **PubTator**: Manual annotations for reference variants
- **LitVar**: Literature-derived variant database

## Expected Runtime

- Full experiment: ~2-4 hours (depends on API rate limits)
- Small subset test: ~5-10 minutes
- Metrics calculation: ~1-2 minutes

## Notes

- Rate limiting is implemented for all API calls
- LLM calls are limited to 100 publications per gene
- Variant normalization handles HGVS and protein notation
- All intermediate results are saved for debugging
"""
    
    readme_file = Path("README.md")
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    print(f"README created at {readme_file}")


def main():
    """
    Main function - run utility tests and checks.
    """
    print("=== FOX Variant Experiment Utilities ===\n")
    
    # Check API connections
    check_api_connections()
    
    # Test variant normalization
    debug_variant_normalization()
    
    # Create README
    create_experiment_readme()
    
    print("\n=== Utilities completed ===")
    print("To run a small test: python -c 'from experiment_utils import test_small_subset_experiment; test_small_subset_experiment()'")


if __name__ == "__main__":
    main() 