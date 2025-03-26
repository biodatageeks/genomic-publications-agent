#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import re
from collections import Counter

def clean_rs_id(variant_name):
    """Ekstrahuje ID rs z różnych formatów."""
    if pd.isna(variant_name):
        return None
    rs_match = re.search(r'rs\d+', str(variant_name))
    if rs_match:
        return rs_match.group(0)
    return variant_name

def extract_gene_symbol(gene_string):
    """Ekstrahuje symbole genów z różnych formatów."""
    if pd.isna(gene_string):
        return []
    # Wzorzec dla dopasowania symboli genów (litery, cyfry, myślniki)
    gene_patterns = re.findall(r'([A-Z0-9-]+)\s*(?:\(\d+\))?', str(gene_string))
    # Oczyszczenie i filtrowanie wyników
    genes = [g.strip() for g in gene_patterns if g and not g.isdigit() and len(g) >= 2]
    return genes

def extract_disease_names(disease_string):
    """Ekstrahuje nazwy chorób z różnych formatów."""
    if pd.isna(disease_string):
        return []
    # Rozdziel na podstawie średnika i nawiasu
    diseases = re.split(r';\s*', str(disease_string))
    # Usuń kody MESH i oczyść
    cleaned_diseases = []
    for d in diseases:
        # Usuń kod MESH jeśli istnieje
        d = re.sub(r'\s*\(MESH:[^)]+\)', '', d)
        # Usuń kod MESH w formacie MESH:DXXXXXX
        d = re.sub(r'\s*MESH:[^;]+', '', d)
        d = d.strip()
        if d:
            cleaned_diseases.append(d.lower())
    return cleaned_diseases

def test_data_processing():
    """Funkcja do testowania przetwarzania danych."""
    print("Wczytywanie danych testowych...")
    
    # Wczytanie danych
    pred_df = pd.read_csv('enhanced_output_final.csv')
    confirmed_df = pd.read_csv('data/Enhancer candidates - DiseaseEnhancer - to verify.csv')
    
    # Testowanie funkcji czyszczących na kilku przykładach
    print("\nTestowanie funkcji clean_rs_id:")
    test_variants = [
        'rs642961', 
        'tmVar:rs642961;VariantGroup:0;RS#:642961', 
        'chr1-209989270-209989270'
    ]
    for variant in test_variants:
        print(f"  Oryginał: '{variant}' -> Oczyszczone: '{clean_rs_id(variant)}'")
    
    print("\nTestowanie funkcji extract_gene_symbol:")
    test_genes = [
        'AP-2alpha (21418); IRF6 (54139); interferon regulatory factor 6 (54139)',
        'RET (5979)',
        'FOXE1'
    ]
    for gene in test_genes:
        print(f"  Oryginał: '{gene}' -> Oczyszczone: {extract_gene_symbol(gene)}")
    
    print("\nTestowanie funkcji extract_disease_names:")
    test_diseases = [
        'nonsyndromic cleft lip with or without (MESH:C566121); cleft palate (MESH:D002972); NSCL/P (MESH:D002972)',
        'Hirschsprung disease (MESH:D006627)',
        'Cleft lip'
    ]
    for disease in test_diseases:
        print(f"  Oryginał: '{disease}' -> Oczyszczone: {extract_disease_names(disease)}")
    
    # Pokrycie wspólnych identyfikatorów
    pred_df['rs_id'] = pred_df['variant_name'].apply(clean_rs_id)
    confirmed_df['rs_id'] = confirmed_df['variant name'].apply(clean_rs_id)
    
    # Tworzenie list genów i chorób
    pred_df['gene_list'] = pred_df['genes'].apply(extract_gene_symbol)
    pred_df['disease_list'] = pred_df['diseases'].apply(extract_disease_names)
    
    confirmed_df['gene_list'] = confirmed_df['gene'].apply(lambda x: [x] if not pd.isna(x) else [])
    confirmed_df['disease_list'] = confirmed_df['disease'].apply(lambda x: [x.lower()] if not pd.isna(x) else [])
    
    common_rs_ids = set(pred_df['rs_id'].dropna()) & set(confirmed_df['rs_id'].dropna())
    print(f"\nWspólne identyfikatory rs (top 10): {list(common_rs_ids)[:10]}")
    
    # Sprawdzenie wspólnych relacji
    print("\nSzczegóły wspólnych wariantów:")
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
        print(f"    - Przewidziane geny: {pred_genes}")
        print(f"    - Potwierdzone geny: {conf_genes}")
        print(f"    - Wspólne geny: {common_genes}")
        print(f"    - Przewidziane choroby: {pred_diseases}")
        print(f"    - Potwierdzone choroby: {conf_diseases}")
        print(f"    - Wspólne choroby: {common_diseases}")
    
    # Sprawdzenie PMID
    pred_pmids = set(pred_df['pmid'].dropna())
    confirmed_pmids = set(confirmed_df['PMID'].dropna())
    common_pmids = pred_pmids & confirmed_pmids
    
    print(f"\nLiczba unikalnych PMID w przewidzianych relacjach: {len(pred_pmids)}")
    print(f"Liczba unikalnych PMID w potwierdzonych relacjach: {len(confirmed_pmids)}")
    print(f"Liczba wspólnych PMID: {len(common_pmids)}")
    print(f"Wspólne PMID: {common_pmids}")

if __name__ == "__main__":
    test_data_processing() 