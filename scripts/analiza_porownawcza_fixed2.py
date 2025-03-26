#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
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

def transform_ground_truth(confirmed_df):
    """
    Transformuje dane ground truth do formatu zgodnego z plikiem wyjściowym narzędzia.
    Dla każdego wariantu łączy wszystkie powiązane geny i choroby w osobne pola.
    """
    # Wykorzystamy variant_name jako klucz
    confirmed_df['rs_id'] = confirmed_df['variant name'].apply(clean_rs_id)
    
    # Zgrupujmy dane według rs_id
    result_data = {}
    
    for _, row in confirmed_df.iterrows():
        rs_id = row['rs_id']
        if pd.notna(rs_id):
            # Inicjalizacja słownika dla danego rs_id, jeśli nie istnieje
            if rs_id not in result_data:
                result_data[rs_id] = {
                    'genes': set(),
                    'diseases': set(),
                    'variant_names': set(),
                    'chr': None,
                    'start': None,
                    'end': None,
                    'pmids': set(),
                    'variant_modes': set(),
                    'variant_types': set()
                }
            
            # Dodaj dane do zgrupowanego słownika
            if pd.notna(row['gene']):
                result_data[rs_id]['genes'].add(row['gene'])
            
            if pd.notna(row['disease']):
                result_data[rs_id]['diseases'].add(row['disease'].lower())
            
            if pd.notna(row['variant name']):
                result_data[rs_id]['variant_names'].add(row['variant name'])
            
            # Wybierz pierwsze niepuste wartości dla chr, start, end
            if pd.notna(row['chr']) and result_data[rs_id]['chr'] is None:
                result_data[rs_id]['chr'] = row['chr']
            
            if pd.notna(row['start']) and result_data[rs_id]['start'] is None:
                result_data[rs_id]['start'] = row['start']
            
            if pd.notna(row['end']) and result_data[rs_id]['end'] is None:
                result_data[rs_id]['end'] = row['end']
            
            # Dodaj PMID
            if 'PMID' in row and pd.notna(row['PMID']):
                # Obsługa przypadku, gdy PMID zawiera wiele wartości oddzielonych przecinkami
                pmids = str(row['PMID']).split(',')
                for pmid in pmids:
                    pmid = pmid.strip()
                    if pmid:
                        result_data[rs_id]['pmids'].add(pmid)
            
            # Dodaj variant mode
            if pd.notna(row['variant mode']):
                result_data[rs_id]['variant_modes'].add(row['variant mode'])
            
            # Dodaj variant type
            if 'variant type (nie brać pod uwagę)' in row and pd.notna(row['variant type (nie brać pod uwagę)']):
                result_data[rs_id]['variant_types'].add(row['variant type (nie brać pod uwagę)'])
    
    # Konwersja do DataFrame
    transformed_data = []
    for rs_id, data in result_data.items():
        transformed_data.append({
            'rs_id': rs_id,
            'chr': data['chr'],
            'start': data['start'],
            'end': data['end'],
            'genes': '; '.join(sorted(data['genes'])) if data['genes'] else "",
            'diseases': '; '.join(sorted(data['diseases'])) if data['diseases'] else "",
            'variant_name': '; '.join(sorted(data['variant_names'])) if data['variant_names'] else "",
            'pmid': '; '.join(sorted(data['pmids'])) if data['pmids'] else "",
            'variant_mode': '; '.join(sorted(data['variant_modes'])) if data['variant_modes'] else "",
            'variant_type': '; '.join(sorted(data['variant_types'])) if data['variant_types'] else ""
        })
    
    return pd.DataFrame(transformed_data)

def analyze_data(pred_file, confirmed_file, output_prefix="analysis"):
    """Główna funkcja analizy danych."""
    print("Wczytywanie danych...")
    
    # Wczytanie danych
    pred_df = pd.read_csv(pred_file)
    original_confirmed_df = pd.read_csv(confirmed_file)
    
    print("\nTransformacja danych ground truth do formatu zgodnego z przewidzianymi...")
    confirmed_df = transform_ground_truth(original_confirmed_df)
    
    # Podstawowe informacje o danych
    print("\nInformacje o danych:")
    print(f"Przewidziane relacje (oryginał): {len(pred_df)} wierszy")
    print(f"Potwierdzone relacje (oryginał): {len(original_confirmed_df)} wierszy")
    print(f"Potwierdzone relacje (po transformacji): {len(confirmed_df)} wierszy")
    
    # Przygotowanie danych
    print("\nPrzygotowanie danych do analizy...")
    
    # Przetwarzanie przewidzianych relacji
    pred_df['rs_id'] = pred_df['variant_name'].apply(clean_rs_id)
    pred_df['gene_list'] = pred_df['genes'].apply(extract_gene_symbol)
    pred_df['disease_list'] = pred_df['diseases'].apply(extract_disease_names)
    
    # Przetwarzanie potwierdzonych relacji
    confirmed_df['gene_list'] = confirmed_df['genes'].apply(lambda x: x.split('; ') if pd.notna(x) and x else [])
    confirmed_df['disease_list'] = confirmed_df['diseases'].apply(lambda x: [d.lower() for d in x.split('; ')] if pd.notna(x) and x else [])
    
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
    print(f"Pokrycie wariantów: {len(common_variants)/len(confirmed_variants)*100:.2f}% jeśli są potwierdzone")
    
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
    print(f"Pokrycie genów: {len(common_genes)/len(confirmed_genes)*100:.2f}% jeśli są potwierdzone")
    
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
    print(f"Pokrycie chorób: {len(common_diseases)/len(confirmed_diseases)*100:.2f}% jeśli są potwierdzone")
    
    # 4. Analiza wariant-gen-choroba dla wspólnych wariantów
    print("\n4. Analiza dokładności powiązań wariant-gen-choroba dla wspólnych wariantów:")
    
    # Dla każdego wspólnego wariantu porównaj geny i choroby
    correct_gene_mappings = 0
    correct_disease_mappings = 0
    total_common_variants = len(common_variants)
    
    for variant in common_variants:
        # Znajdź rekordy dla tego wariantu
        pred_rows = pred_df[pred_df['rs_id'] == variant]
        conf_rows = confirmed_df[confirmed_df['rs_id'] == variant]
        
        # Zbierz wszystkie geny i choroby dla tego wariantu
        pred_variant_genes = set([gene for genes in pred_rows['gene_list'] for gene in genes])
        conf_variant_genes = set([gene for genes in conf_rows['gene_list'] for gene in genes])
        
        pred_variant_diseases = set([disease for diseases in pred_rows['disease_list'] for disease in diseases])
        conf_variant_diseases = set([disease for diseases in conf_rows['disease_list'] for disease in diseases])
        
        # Sprawdź, czy istnieje co najmniej jedno dopasowanie genu i choroby
        if pred_variant_genes.intersection(conf_variant_genes):
            correct_gene_mappings += 1
        
        if pred_variant_diseases.intersection(conf_variant_diseases):
            correct_disease_mappings += 1
    
    # Oblicz dokładność
    gene_accuracy = correct_gene_mappings / total_common_variants * 100 if total_common_variants > 0 else 0
    disease_accuracy = correct_disease_mappings / total_common_variants * 100 if total_common_variants > 0 else 0
    
    print(f"Dla {total_common_variants} wspólnych wariantów:")
    print(f"Dokładność przypisania genów: {gene_accuracy:.2f}%")
    print(f"Dokładność przypisania chorób: {disease_accuracy:.2f}%")
    
    # 5. Analiza chromosomów
    print("\n5. Rozkład chromosomów:")
    
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
    
    # 6. Analiza par wariant-gen i wariant-choroba dla wspólnych wariantów
    print("\n6. Analiza dopasowań wariant-gen i wariant-choroba:")
    
    # Dla każdego wspólnego wariantu analizuj dopasowania genów i chorób
    variant_gene_matches = []
    variant_disease_matches = []
    
    for variant in common_variants:
        # Znajdź rekordy dla tego wariantu
        pred_rows = pred_df[pred_df['rs_id'] == variant]
        conf_rows = confirmed_df[confirmed_df['rs_id'] == variant]
        
        # Zbierz wszystkie geny i choroby dla tego wariantu
        pred_variant_genes = set([gene for genes in pred_rows['gene_list'] for gene in genes])
        conf_variant_genes = set([gene for genes in conf_rows['gene_list'] for gene in genes])
        
        pred_variant_diseases = set([disease for diseases in pred_rows['disease_list'] for disease in diseases])
        conf_variant_diseases = set([disease for diseases in conf_rows['disease_list'] for disease in diseases])
        
        # Oblicz wartości TP, FP, FN dla genów
        tp_genes = len(pred_variant_genes.intersection(conf_variant_genes))
        fp_genes = len(pred_variant_genes - conf_variant_genes)
        fn_genes = len(conf_variant_genes - pred_variant_genes)
        
        # Oblicz wartości TP, FP, FN dla chorób
        tp_diseases = len(pred_variant_diseases.intersection(conf_variant_diseases))
        fp_diseases = len(pred_variant_diseases - conf_variant_diseases)
        fn_diseases = len(conf_variant_diseases - pred_variant_diseases)
        
        variant_gene_matches.append({
            'variant': variant,
            'TP': tp_genes,
            'FP': fp_genes,
            'FN': fn_genes
        })
        
        variant_disease_matches.append({
            'variant': variant,
            'TP': tp_diseases,
            'FP': fp_diseases,
            'FN': fn_diseases
        })
    
    # Oblicz łączne metryki dla genów
    total_tp_genes = sum(match['TP'] for match in variant_gene_matches)
    total_fp_genes = sum(match['FP'] for match in variant_gene_matches)
    total_fn_genes = sum(match['FN'] for match in variant_gene_matches)
    
    precision_genes = total_tp_genes / (total_tp_genes + total_fp_genes) if (total_tp_genes + total_fp_genes) > 0 else 0
    recall_genes = total_tp_genes / (total_tp_genes + total_fn_genes) if (total_tp_genes + total_fn_genes) > 0 else 0
    f1_genes = 2 * precision_genes * recall_genes / (precision_genes + recall_genes) if (precision_genes + recall_genes) > 0 else 0
    
    # Oblicz łączne metryki dla chorób
    total_tp_diseases = sum(match['TP'] for match in variant_disease_matches)
    total_fp_diseases = sum(match['FP'] for match in variant_disease_matches)
    total_fn_diseases = sum(match['FN'] for match in variant_disease_matches)
    
    precision_diseases = total_tp_diseases / (total_tp_diseases + total_fp_diseases) if (total_tp_diseases + total_fp_diseases) > 0 else 0
    recall_diseases = total_tp_diseases / (total_tp_diseases + total_fn_diseases) if (total_tp_diseases + total_fn_diseases) > 0 else 0
    f1_diseases = 2 * precision_diseases * recall_diseases / (precision_diseases + recall_diseases) if (precision_diseases + recall_diseases) > 0 else 0
    
    print("\nMetryki dla przypisań genów:")
    print(f"Precision: {precision_genes:.4f}")
    print(f"Recall: {recall_genes:.4f}")
    print(f"F1 Score: {f1_genes:.4f}")
    
    print("\nMetryki dla przypisań chorób:")
    print(f"Precision: {precision_diseases:.4f}")
    print(f"Recall: {recall_diseases:.4f}")
    print(f"F1 Score: {f1_diseases:.4f}")
    
    # Wykres 5: Metryki genów i chorób
    metrics_data = pd.DataFrame({
        'Geny': [precision_genes, recall_genes, f1_genes],
        'Choroby': [precision_diseases, recall_diseases, f1_diseases]
    }, index=['Precision', 'Recall', 'F1 Score'])
    
    plt.figure(figsize=(10, 6))
    metrics_data.plot(kind='bar', figsize=(10, 6))
    plt.title('Metryki dla przypisań genów i chorób')
    plt.xlabel('Metryka')
    plt.ylabel('Wartość')
    plt.ylim(0, 1)
    plt.legend(['Geny', 'Choroby'])
    plt.tight_layout()
    plt.savefig(f'{output_prefix}_metrics.png', dpi=300)
    
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
        
        "gene_precision": precision_genes,
        "gene_recall": recall_genes,
        "gene_f1": f1_genes,
        
        "disease_precision": precision_diseases,
        "disease_recall": recall_diseases,
        "disease_f1": f1_diseases
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analiza porównawcza danych z przewidywań i potwierdzonych relacji.")
    parser.add_argument("--pred", required=True, help="Ścieżka do pliku CSV z przewidzianymi relacjami")
    parser.add_argument("--confirmed", required=True, help="Ścieżka do pliku CSV z potwierdzonymi relacjami")
    parser.add_argument("--prefix", default="analysis", help="Prefiks dla plików wyjściowych")
    
    args = parser.parse_args()
    
    analyze_data(args.pred, args.confirmed, args.prefix) 