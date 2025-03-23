# Scripts for Analyzing Genetic Variant Co-occurrence

This directory contains scripts for analyzing and visualizing the co-occurrence of genetic variants with other biological entities in scientific publications.

## Available Scripts

1. **analyze_variant_relationships.py** - Script analyzing the co-occurrence of genetic variants with genes, diseases, and tissues.
   - Analyzes scientific publications using PubTator API
   - Detects mutual relationships between variants and other entities
   - Saves results in CSV format and optionally Excel

2. **visualize_relationships.py** - Script visualizing relationships between variants, genes, and diseases as a graph.
   - Creates a network graph of relationships
   - Colors different node types (variants, genes, diseases)
   - Saves visualization as PNG file

## How to Use

### Analyzing Variant Relationships

```bash
python scripts/analyze_variant_relationships.py --email your@email.com --output results.csv
```

### Visualizing Relationships

```bash
python scripts/visualize_relationships.py --input results.csv --output relationship_graph.png
```

## Requirements

- Python 3.6+
- pandas
- networkx
- matplotlib
- openpyxl (optional, for Excel file output)

## Example PMIDs for Analysis

The scripts by default analyze the following publications:
- 33417880 - Publication about COVID-19 and SARS-CoV-2 variants
- 33705364 - Publication about BRAF variants in melanoma
- 34268513 - Publication about germline variants in pancreatic cancer
- 34002096 - Publication about variants in prostate cancer
- 33208827 - Publication about variants in BRCA1/2 gene

## Analysis Results

The following relationships were detected in the analysis:

- 1 variant identified: D614G (SARS-CoV-2 variant)
- 2 genes identified: toll-like receptor 9 (TLR9)
- 3 diseases identified: COVID-19, MERS-CoV, COVID-19 disease

The D614G variant is associated with the TLR9 gene and various aspects of COVID-19, suggesting a potential pathogenesis mechanism. The relationship graph shows connections between these elements, indicating complex biological dependencies. 