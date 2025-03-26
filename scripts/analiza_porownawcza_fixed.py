#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
import argparse

# Ustawienia dla wykresów
plt.style.use('ggplot')
sns.set(font_scale=1.2)
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.family'] = 'DejaVu Sans'

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

def analyze_data(pred_file, confirmed_file, output_prefix="analysis"):
    """Główna funkcja analizy danych."""
    print("Wczytywanie danych...")
    
    # Wczytanie danych
    pred_df = pd.read_csv(pred_file)
    confirmed_df = pd.read_csv(confirmed_file)
    
    # Podstawowe informacje o danych
    print("\nInformacje o danych:")
    print(f"Przewidziane relacje: {len(pred_df)} wierszy")
    print(f"Potwierdzone relacje: {len(confirmed_df)} wierszy")
    
    # Przygotowanie danych
    print("\nPrzygotowanie danych do analizy...")
    
    # Przetwarzanie przewidzianych relacji
    pred_df['rs_id'] = pred_df['variant_name'].apply(clean_rs_id)
    pred_df['gene_list'] = pred_df['genes'].apply(extract_gene_symbol)
    pred_df['disease_list'] = pred_df['diseases'].apply(extract_disease_names)
    
    # Przetwarzanie potwierdzonych relacji
    confirmed_df['rs_id'] = confirmed_df['variant name'].apply(clean_rs_id)
    confirmed_df['gene_list'] = confirmed_df['gene'].apply(lambda x: [x] if not pd.isna(x) else [])
    confirmed_df['disease_list'] = confirmed_df['disease'].apply(lambda x: [x.lower()] if not pd.isna(x) else [])
    
    # 1. Analiza pokrycia wariantów
    pred_variants = set(pred_df['rs_id'].dropna())
    confirmed_variants = set(confirmed_df['rs_id'].dropna())
    
    common_variants = pred_variants.intersection(confirmed_variants)
    unique_pred_variants = pred_variants - confirmed_variants
    unique_confirmed_variants = confirmed_variants - pred_variants
    
    print("\n1. Analiza pokrycia wariantów (rs IDs):")
    print(f"Liczba unikalnych wariantów w przewidzianych relacjach: {len(pred_variants)}")
    print(f"Liczba unikalnych wariantów w potwierdzonych relacjach: {len(confirmed_variants)}")
    print(f"Liczba wspólnych wariantów: {len(common_variants)}")
    print(f"Pokrycie wariantów: {len(common_variants)/len(confirmed_variants)*100:.2f}%")
    
    # 2. Analiza genów
    pred_genes = set([gene for genes in pred_df['gene_list'] for gene in genes])
    confirmed_genes = set([gene for genes in confirmed_df['gene_list'] for gene in genes])
    
    common_genes = pred_genes.intersection(confirmed_genes)
    unique_pred_genes = pred_genes - confirmed_genes
    unique_confirmed_genes = confirmed_genes - pred_genes
    
    print("\n2. Analiza pokrycia genów:")
    print(f"Liczba unikalnych genów w przewidzianych relacjach: {len(pred_genes)}")
    print(f"Liczba unikalnych genów w potwierdzonych relacjach: {len(confirmed_genes)}")
    print(f"Liczba wspólnych genów: {len(common_genes)}")
    print(f"Pokrycie genów: {len(common_genes)/len(confirmed_genes)*100:.2f}%")
    
    # 3. Analiza chorób
    pred_diseases = set([disease for diseases in pred_df['disease_list'] for disease in diseases])
    confirmed_diseases = set([disease for diseases in confirmed_df['disease_list'] for disease in diseases])
    
    common_diseases = pred_diseases.intersection(confirmed_diseases)
    unique_pred_diseases = pred_diseases - confirmed_diseases
    unique_confirmed_diseases = confirmed_diseases - pred_diseases
    
    print("\n3. Analiza pokrycia chorób:")
    print(f"Liczba unikalnych chorób w przewidzianych relacjach: {len(pred_diseases)}")
    print(f"Liczba unikalnych chorób w potwierdzonych relacjach: {len(confirmed_diseases)}")
    print(f"Liczba wspólnych chorób: {len(common_diseases)}")
    print(f"Pokrycie chorób: {len(common_diseases)/len(confirmed_diseases)*100:.2f}%")
    
    # 4. Analiza chromosomów
    print("\n4. Rozkład chromosomów:")
    
    # Zliczanie chromosomów
    pred_chr_count = Counter(pred_df['chr'].dropna())
    confirmed_chr_count = Counter(confirmed_df['chr'].dropna())
    
    # Połącz wszystkie chromosomy
    all_chrs = sorted(list(set(pred_chr_count.keys()) | set(confirmed_chr_count.keys())))
    
    # Przygotowanie danych do wykresu
    chr_data = pd.DataFrame({
        'Przewidziane': [pred_chr_count.get(chr_name, 0) for chr_name in all_chrs],
        'Potwierdzone': [confirmed_chr_count.get(chr_name, 0) for chr_name in all_chrs]
    }, index=all_chrs)
    
    # Wizualizacja
    print("\nTworzenie wizualizacji...")
    
    # Wykres 1: Porównanie pokrycia wariantów, genów i chorób
    plt.figure(figsize=(14, 8))
    
    categories = ['Warianty', 'Geny', 'Choroby']
    pred_only = [len(unique_pred_variants), len(unique_pred_genes), len(unique_pred_diseases)]
    common = [len(common_variants), len(common_genes), len(common_diseases)]
    confirmed_only = [len(unique_confirmed_variants), len(unique_confirmed_genes), len(unique_confirmed_diseases)]
    
    width = 0.5
    fig, ax = plt.subplots(figsize=(12, 8))
    
    ax.bar(categories, pred_only, width, label='Tylko przewidziane', color='skyblue')
    ax.bar(categories, common, width, bottom=pred_only, label='Wspólne', color='green')
    ax.bar(categories, confirmed_only, width, bottom=[p+c for p,c in zip(pred_only, common)], 
           label='Tylko potwierdzone', color='tomato')
    
    ax.set_ylabel('Liczba elementów')
    ax.set_title('Porównanie pokrycia danych między przewidzianymi a potwierdzonymi relacjami')
    ax.legend()
    
    # Dodanie etykiet liczbowych
    for i, category in enumerate(categories):
        total_pred = pred_only[i] + common[i]
        total_confirmed = confirmed_only[i] + common[i]
        ax.text(i, pred_only[i]/2, str(pred_only[i]), ha='center', va='center', color='black')
        ax.text(i, pred_only[i] + common[i]/2, str(common[i]), ha='center', va='center', color='white')
        ax.text(i, pred_only[i] + common[i] + confirmed_only[i]/2, str(confirmed_only[i]), 
                ha='center', va='center', color='black')
        
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_comparison_coverage.png', dpi=300)
    
    # Wykres 2: Rozkład chromosomów
    plt.figure(figsize=(14, 10))
    chr_data.plot(kind='bar', figsize=(14, 8))
    plt.title('Porównanie liczby relacji na chromosom')
    plt.xlabel('Chromosom')
    plt.ylabel('Liczba relacji')
    plt.legend(['Przewidziane', 'Potwierdzone'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_chromosome_distribution.png', dpi=300)
    
    # Wykres 3: Top 10 genów
    plt.figure(figsize=(14, 8))
    
    # Zliczanie genów
    pred_gene_counter = Counter([gene for genes in pred_df['gene_list'] for gene in genes])
    confirmed_gene_counter = Counter([gene for genes in confirmed_df['gene_list'] for gene in genes])
    
    # Top 10 genów z obu zbiorów
    top_pred_genes = [gene for gene, _ in pred_gene_counter.most_common(10)]
    top_confirmed_genes = [gene for gene, _ in confirmed_gene_counter.most_common(10)]
    all_top_genes = sorted(list(set(top_pred_genes) | set(top_confirmed_genes)))
    
    gene_data = pd.DataFrame({
        'Przewidziane': [pred_gene_counter.get(gene, 0) for gene in all_top_genes],
        'Potwierdzone': [confirmed_gene_counter.get(gene, 0) for gene in all_top_genes]
    }, index=all_top_genes)
    
    gene_data.sort_values(by=['Przewidziane', 'Potwierdzone'], ascending=False, inplace=True)
    gene_data.head(15).plot(kind='bar', figsize=(14, 8))
    plt.title('Top geny w obu zbiorach danych')
    plt.xlabel('Gen')
    plt.ylabel('Liczba wystąpień')
    plt.legend(['Przewidziane', 'Potwierdzone'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_top_genes.png', dpi=300)
    
    # Wykres 4: Top 10 chorób
    plt.figure(figsize=(14, 8))
    
    # Zliczanie chorób
    pred_disease_counter = Counter([disease for diseases in pred_df['disease_list'] for disease in diseases])
    confirmed_disease_counter = Counter([disease for diseases in confirmed_df['disease_list'] for disease in diseases])
    
    # Top 10 chorób z obu zbiorów
    top_pred_diseases = [disease for disease, _ in pred_disease_counter.most_common(10)]
    top_confirmed_diseases = [disease for disease, _ in confirmed_disease_counter.most_common(10)]
    all_top_diseases = sorted(list(set(top_pred_diseases) | set(top_confirmed_diseases)))
    
    disease_data = pd.DataFrame({
        'Przewidziane': [pred_disease_counter.get(disease, 0) for disease in all_top_diseases],
        'Potwierdzone': [confirmed_disease_counter.get(disease, 0) for disease in all_top_diseases]
    }, index=all_top_diseases)
    
    disease_data.sort_values(by=['Przewidziane', 'Potwierdzone'], ascending=False, inplace=True)
    
    # Skrócenie długich nazw chorób - naprawiona wersja
    disease_data = disease_data.copy()
    disease_data.index = pd.Index([d[:40] + '...' if len(d) > 40 else d for d in disease_data.index])
    
    disease_data.head(15).plot(kind='bar', figsize=(14, 8))
    plt.title('Top choroby w obu zbiorach danych')
    plt.xlabel('Choroba')
    plt.ylabel('Liczba wystąpień')
    plt.legend(['Przewidziane', 'Potwierdzone'])
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_top_diseases.png', dpi=300)
    
    # 5. Analiza par gen-choroba
    print("\n5. Analiza par gen-choroba:")
    
    # Tworzenie par gen-choroba
    pred_gene_disease = set()
    for _, row in pred_df.iterrows():
        for gene in row['gene_list']:
            for disease in row['disease_list']:
                pred_gene_disease.add((gene, disease))
    
    confirmed_gene_disease = set()
    for _, row in confirmed_df.iterrows():
        for gene in row['gene_list']:
            for disease in row['disease_list']:
                confirmed_gene_disease.add((gene, disease))
    
    common_pairs = pred_gene_disease.intersection(confirmed_gene_disease)
    unique_pred_pairs = pred_gene_disease - confirmed_gene_disease
    unique_confirmed_pairs = confirmed_gene_disease - pred_gene_disease
    
    print(f"Liczba unikalnych par gen-choroba w przewidzianych relacjach: {len(pred_gene_disease)}")
    print(f"Liczba unikalnych par gen-choroba w potwierdzonych relacjach: {len(confirmed_gene_disease)}")
    print(f"Liczba wspólnych par gen-choroba: {len(common_pairs)}")
    print(f"Pokrycie par gen-choroba: {len(common_pairs)/len(confirmed_gene_disease)*100:.2f}%")
    
    # Wykres 5: Pokrycie par gen-choroba
    plt.figure(figsize=(10, 6))
    venn_data = [
        len(unique_pred_pairs),
        len(unique_confirmed_pairs),
        len(common_pairs)
    ]
    labels = [
        f'Tylko przewidziane\n({venn_data[0]})',
        f'Tylko potwierdzone\n({venn_data[1]})',
        f'Wspólne\n({venn_data[2]})'
    ]
    plt.pie(venn_data, labels=labels, autopct='%1.1f%%', colors=['skyblue', 'tomato', 'lightgreen'])
    plt.title('Pokrycie par gen-choroba')
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_gene_disease_pairs.png', dpi=300)
    
    print("\nAnalizę zakończono pomyślnie. Wykresy zostały zapisane z prefiksem:", output_prefix)
    
    return {
        "pred_variants": len(pred_variants),
        "confirmed_variants": len(confirmed_variants),
        "common_variants": len(common_variants),
        "variant_coverage": len(common_variants)/len(confirmed_variants)*100 if confirmed_variants else 0,
        
        "pred_genes": len(pred_genes),
        "confirmed_genes": len(confirmed_genes),
        "common_genes": len(common_genes),
        "gene_coverage": len(common_genes)/len(confirmed_genes)*100 if confirmed_genes else 0,
        
        "pred_diseases": len(pred_diseases),
        "confirmed_diseases": len(confirmed_diseases),
        "common_diseases": len(common_diseases),
        "disease_coverage": len(common_diseases)/len(confirmed_diseases)*100 if confirmed_diseases else 0,
        
        "pred_gene_disease": len(pred_gene_disease),
        "confirmed_gene_disease": len(confirmed_gene_disease),
        "common_gene_disease": len(common_pairs),
        "gene_disease_coverage": len(common_pairs)/len(confirmed_gene_disease)*100 if confirmed_gene_disease else 0
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analiza porównawcza danych z przewidywań i potwierdzonych relacji.")
    parser.add_argument("--pred", required=True, help="Ścieżka do pliku CSV z przewidzianymi relacjami")
    parser.add_argument("--confirmed", required=True, help="Ścieżka do pliku CSV z potwierdzonymi relacjami")
    parser.add_argument("--prefix", default="analysis", help="Prefiks dla plików wyjściowych")
    
    args = parser.parse_args()
    
    analyze_data(args.pred, args.confirmed, args.prefix) 