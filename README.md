# FOX Genes Variant Extraction Experiment - 01.07.2025

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
