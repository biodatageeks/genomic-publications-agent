#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import re
from collections import Counter

def clean_rs_id(variant_name):
    """Extracts rs ID from various formats."""
    if pd.isna(variant_name):
        return None
    rs_match = re.search(r'rs\d+', str(variant_name))
    if rs_match:
        return rs_match.group(0)
    return variant_name

def extract_gene_symbol(gene_string):
    """Extracts gene symbols from various formats."""
    if pd.isna(gene_string):
        return []
    # Pattern for matching gene symbols (letters, numbers, hyphens)
    gene_patterns = re.findall(r'([A-Z0-9-]+)\s*(?:\(\d+\))?', str(gene_string))
    # Clean and filter results
    genes = [g.strip() for g in gene_patterns if g and not g.isdigit() and len(g) >= 2]
    return genes

def extract_disease_names(disease_string):
    """Extracts disease names from various formats."""
    if pd.isna(disease_string):
        return []
    # Split based on semicolon and parentheses
    diseases = re.split(r';\s*', str(disease_string))
    # Remove MESH codes and clean
    cleaned_diseases = []
    for d in diseases:
        # Remove MESH code if exists
        d = re.sub(r'\s*\(MESH:[^)]+\)', '', d)
        # Remove MESH code in MESH:DXXXXXX format
        d = re.sub(r'\s*MESH:[^;]+', '', d)
        d = d.strip()
        if d:
            cleaned_diseases.append(d.lower())
    return cleaned_diseases

def test_data_processing():
    """Function for testing data processing."""
    print("Loading test data...")
    
    # Load data
    pred_df = pd.read_csv('enhanced_output_final.csv')
    confirmed_df = pd.read_csv('data/Enhancer candidates - DiseaseEnhancer - to verify.csv')
    
    # Test cleaning functions on several examples
    print("\nTesting clean_rs_id function:")
    test_variants = [
        'rs642961', 
        'tmVar:rs642961;VariantGroup:0;RS#:642961', 
        'chr1-209989270-209989270'
    ]
    for variant in test_variants:
        print(f"  Original: '{variant}' -> Cleaned: '{clean_rs_id(variant)}'")
    
    print("\nTesting extract_gene_symbol function:")
    test_genes = [
        'AP-2alpha (21418); IRF6 (54139); interferon regulatory factor 6 (54139)',
        'RET (5979)',
        'FOXE1'
    ]
    for gene in test_genes:
        print(f"  Original: '{gene}' -> Cleaned: {extract_gene_symbol(gene)}")
    
    print("\nTesting extract_disease_names function:")
    test_diseases = [
        'nonsyndromic cleft lip with or without (MESH:C566121); cleft palate (MESH:D002972); NSCL/P (MESH:D002972)',
        'Hirschsprung disease (MESH:D006627)',
        'Cleft lip'
    ]
    for disease in test_diseases:
        print(f"  Original: '{disease}' -> Cleaned: {extract_disease_names(disease)}")
    
    # Coverage of common identifiers
    pred_df['rs_id'] = pred_df['variant_name'].apply(clean_rs_id)
    confirmed_df['rs_id'] = confirmed_df['variant name'].apply(clean_rs_id)
    
    # Create gene and disease lists
    pred_df['gene_list'] = pred_df['genes'].apply(extract_gene_symbol)
    pred_df['disease_list'] = pred_df['diseases'].apply(extract_disease_names)
    
    confirmed_df['gene_list'] = confirmed_df['gene'].apply(lambda x: [x] if not pd.isna(x) else [])
    confirmed_df['disease_list'] = confirmed_df['disease'].apply(lambda x: [x.lower()] if not pd.isna(x) else [])
    
    common_rs_ids = set(pred_df['rs_id'].dropna()) & set(confirmed_df['rs_id'].dropna())
    print(f"\nCommon rs identifiers (top 10): {list(common_rs_ids)[:10]}")
    
    # Check common relationships
    print("\nDetails of common variants:")
    for rs_id in common_rs_ids:
        pred_rows = pred_df[pred_df['rs_id'] == rs_id]
        conf_rows = confirmed_df[confirmed_df['rs_id'] == rs_id]
        
        pred_genes = set()
        for genes in pred_rows['gene_list']:
            for gene in genes:
                pred_genes.add(gene)
                
        conf_genes = set()
        for genes in conf_rows['gene_list']:
            for gene in genes:
                conf_genes.add(gene)
        
        pred_diseases = set()
        for diseases in pred_rows['disease_list']:
            for disease in diseases:
                pred_diseases.add(disease)
                
        conf_diseases = set()
        for diseases in conf_rows['disease_list']:
            for disease in diseases:
                conf_diseases.add(disease)
        
        common_genes = pred_genes & conf_genes
        common_diseases = pred_diseases & conf_diseases
        
        print(f"  * {rs_id}:")
        print(f"    - Predicted genes: {pred_genes}")
        print(f"    - Confirmed genes: {conf_genes}")
        print(f"    - Common genes: {common_genes}")
        print(f"    - Predicted diseases: {pred_diseases}")
        print(f"    - Confirmed diseases: {conf_diseases}")
        print(f"    - Common diseases: {common_diseases}")
    
    # Check PMIDs
    pred_pmids = set(pred_df['pmid'].dropna())
    confirmed_pmids = set(confirmed_df['PMID'].dropna())
    common_pmids = pred_pmids & confirmed_pmids
    
    print(f"\nNumber of unique PMIDs in predicted relationships: {len(pred_pmids)}")
    print(f"Number of unique PMIDs in confirmed relationships: {len(confirmed_pmids)}")
    print(f"Number of common PMIDs: {len(common_pmids)}")
    print(f"Common PMIDs: {common_pmids}")

if __name__ == "__main__":
    test_data_processing()