#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
import re
import argparse
import os
import json

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

def extract_pmids(pmid_string):
    """Ekstrahuje PMIDs z ciągu znaków."""
    if pd.isna(pmid_string):
        return []
    # Rozdziel PMIDs po średniku lub przecinku i usuń białe znaki
    pmids = re.split(r'[;,]\s*', str(pmid_string))
    return [pmid.strip() for pmid in pmids if pmid.strip()]

def transform_ground_truth(confirmed_df, common_pmids=None):
    """
    Transformuje dane ground truth do formatu zgodnego z plikiem wyjściowym narzędzia.
    Dla każdego wariantu łączy wszystkie powiązane geny i choroby w osobne pola.
    
    Args:
        confirmed_df: DataFrame z potwierdzonymi danymi
        common_pmids: Set lub lista PMIDs, które mają być uwzględnione (jeśli None, uwzględniane są wszystkie)
    """
    # Wykorzystamy variant_name jako klucz
    confirmed_df['rs_id'] = confirmed_df['variant name'].apply(clean_rs_id)
    
    # Zgrupujmy dane według rs_id
    result_data = {}
    
    for _, row in confirmed_df.iterrows():
        rs_id = row['rs_id']
        
        # Przetwórz PMIDs z bieżącego wiersza
        row_pmids = set()
        if 'PMID' in row and pd.notna(row['PMID']):
            row_pmids = set(extract_pmids(row['PMID']))
        
        # Jeśli określono wspólne PMIDs, pomiń wiersze bez wspólnych PMIDs
        if common_pmids is not None and not row_pmids.intersection(common_pmids):
            continue
            
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
            result_data[rs_id]['pmids'].update(row_pmids)
            
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

def analyze_data(pred_file, confirmed_file, output_prefix="analysis", score_threshold=None):
    """
    Główna funkcja analizy danych.
    
    Args:
        pred_file: Ścieżka do pliku CSV z przewidzianymi relacjami
        confirmed_file: Ścieżka do pliku CSV z potwierdzonymi relacjami
        output_prefix: Prefiks dla plików wyjściowych
        score_threshold: Minimalny próg dla scoringu relacji (jeśli None, bierze wszystkie relacje)
    
    Returns:
        Słownik z wynikami analizy
    """
    print("Wczytywanie danych...")
    
    # Wczytanie danych
    pred_df = pd.read_csv(pred_file)
    original_confirmed_df = pd.read_csv(confirmed_file)
    
    # Sprawdź czy mamy kolumny ze scoringiem
    has_gene_score = 'gene_score' in pred_df.columns
    has_disease_score = 'disease_score' in pred_df.columns
    
    # Zastosuj filtrowanie według progu
    if score_threshold is not None:
        print(f"Filtrowanie relacji z progiem scoringu >= {score_threshold}...")
        filtered_pred_df = pred_df.copy()
        
        # Początkowa liczba wierszy
        initial_rows = len(filtered_pred_df)
        
        # Filtrowanie w przypadku danych zagregowanych
        rows_to_keep = []
        
        for idx, row in filtered_pred_df.iterrows():
            keep_row = True
            
            # Sprawdź czy wiersz ma geny i czy spełniają próg
            if has_gene_score and pd.notna(row['genes']) and pd.notna(row['gene_score']):
                # Podziel łańcuchy na listy
                gene_scores = [float(score) for score in row['gene_score'].split('; ') if score]
                
                # Sprawdź, czy którykolwiek ze scorów spełnia warunek
                if not any(score >= score_threshold for score in gene_scores if not pd.isna(score)):
                    keep_row = False
            
            # Sprawdź czy wiersz ma choroby i czy spełniają próg
            if has_disease_score and pd.notna(row['diseases']) and pd.notna(row['disease_score']):
                # Podziel łańcuchy na listy
                disease_scores = [float(score) for score in row['disease_score'].split('; ') if score]
                
                # Sprawdź, czy którykolwiek ze scorów spełnia warunek
                if not any(score >= score_threshold for score in disease_scores if not pd.isna(score)):
                    keep_row = False
            
            if keep_row:
                rows_to_keep.append(idx)
        
        # Filtruj DataFrame
        filtered_pred_df = filtered_pred_df.loc[rows_to_keep]
        
        # Liczba wierszy po filtrowaniu
        filtered_rows = len(filtered_pred_df)
        print(f"Usunięto {initial_rows - filtered_rows} wierszy, które nie spełniają kryterium progu scoringu.")
        
        # Kontynuuj z przefiltrowanymi danymi
        pred_df = filtered_pred_df
    
    # Wyodrębnij PMIDs z przewidywanych danych
    pred_pmids = set()
    for pmid_str in pred_df['pmid'].dropna():
        pred_pmids.update(extract_pmids(pmid_str))
    
    print(f"Liczba unikalnych PMIDs w przewidzianych danych: {len(pred_pmids)}")
    
    print("\nTransformacja danych ground truth do formatu zgodnego z przewidzianymi...")
    print("Filtrowanie ground truth tylko do wspólnych PMIDs...")
    
    # Transformuj dane ground truth, uwzględniając tylko wspólne PMIDs
    confirmed_df = transform_ground_truth(original_confirmed_df, common_pmids=pred_pmids)
    
    # Podstawowe informacje o danych
    print("\nInformacje o danych:")
    print(f"Przewidziane relacje (oryginał): {len(pred_df)} wierszy")
    print(f"Potwierdzone relacje (oryginał): {len(original_confirmed_df)} wierszy")
    print(f"Potwierdzone relacje (po transformacji i filtracji wg PMIDs): {len(confirmed_df)} wierszy")
    
    # Jeśli po filtracji nie ma danych, zakończ
    if len(confirmed_df) == 0:
        print("UWAGA: Po filtracji wg PMIDs nie znaleziono pasujących danych w zbiorze ground truth!")
        return
    
    # Przygotowanie danych
    print("\nPrzygotowanie danych do analizy...")
    
    # Przetwarzanie przewidzianych relacji
    pred_df['rs_id'] = pred_df['variant_name'].apply(clean_rs_id)
    pred_df['gene_list'] = pred_df['genes'].apply(extract_gene_symbol)
    pred_df['disease_list'] = pred_df['diseases'].apply(extract_disease_names)
    
    # Przetwarzanie potwierdzonych relacji
    confirmed_df['gene_list'] = confirmed_df['genes'].apply(lambda x: x.split('; ') if pd.notna(x) and x else [])
    confirmed_df['disease_list'] = confirmed_df['diseases'].apply(lambda x: [d.lower() for d in x.split('; ')] if pd.notna(x) and x else [])
    
    # Uzyskaj zbiór unikalnych rs_id z przewidzianych danych
    pred_variants = set(pred_df['rs_id'].dropna())
    
    # 1. Analiza pokrycia wariantów
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
    
    # Tworzenie słownika variant -> [genes] dla obu zbiorów
    pred_variant_to_genes = defaultdict(set)
    for _, row in pred_df.iterrows():
        if pd.notna(row['rs_id']):
            pred_variant_to_genes[row['rs_id']].update(row['gene_list'])
    
    confirmed_variant_to_genes = defaultdict(set)
    for _, row in confirmed_df.iterrows():
        if pd.notna(row['rs_id']):
            confirmed_variant_to_genes[row['rs_id']].update(row['gene_list'])
    
    # Tworzenie słownika variant -> [diseases] dla obu zbiorów
    pred_variant_to_diseases = defaultdict(set)
    for _, row in pred_df.iterrows():
        if pd.notna(row['rs_id']):
            pred_variant_to_diseases[row['rs_id']].update(row['disease_list'])
    
    confirmed_variant_to_diseases = defaultdict(set)
    for _, row in confirmed_df.iterrows():
        if pd.notna(row['rs_id']):
            confirmed_variant_to_diseases[row['rs_id']].update(row['disease_list'])
    
    # Zliczanie trafnych przypisań genów i chorób dla wspólnych wariantów
    correct_gene_assignments = 0
    correct_disease_assignments = 0
    
    print(f"Dla {len(common_variants)} wspólnych wariantów:")
    
    for variant in common_variants:
        pred_genes = pred_variant_to_genes[variant]
        confirmed_genes = confirmed_variant_to_genes[variant]
        
        # Wariant ma przypisany przynajmniej jeden gen w obu zbiorach
        if pred_genes and confirmed_genes:
            # Sprawdzamy czy jest co najmniej jeden wspólny gen
            if pred_genes.intersection(confirmed_genes):
                correct_gene_assignments += 1
        
        pred_diseases = pred_variant_to_diseases[variant]
        confirmed_diseases = confirmed_variant_to_diseases[variant]
        
        # Wariant ma przypisaną przynajmniej jedną chorobę w obu zbiorach
        if pred_diseases and confirmed_diseases:
            # Sprawdzamy czy jest co najmniej jedna wspólna choroba
            if pred_diseases.intersection(confirmed_diseases):
                correct_disease_assignments += 1
    
    # Obliczanie dokładności
    gene_accuracy = correct_gene_assignments / len(common_variants) * 100 if common_variants else 0
    disease_accuracy = correct_disease_assignments / len(common_variants) * 100 if common_variants else 0
    
    print(f"Dokładność przypisania genów: {gene_accuracy:.2f}%")
    print(f"Dokładność przypisania chorób: {disease_accuracy:.2f}%")
    
    # 5. Analiza chromosomów
    print("\n5. Rozkład chromosomów:")
    
    # Wizualizacje
    print("\nTworzenie wizualizacji...")
    
    # 1. Wykres porównania pokrycia wariantów, genów i chorób
    plt.figure(figsize=(14, 8))
    
    categories = ['Warianty', 'Geny', 'Choroby']
    coverage_values = [
        len(common_variants)/len(confirmed_variants)*100,
        len(common_genes)/len(confirmed_genes)*100,
        len(common_diseases)/len(confirmed_diseases)*100
    ]
    
    bars = plt.bar(categories, coverage_values, color='skyblue')
    
    # Dodanie etykiet z wartościami
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                 f'{height:.2f}%', ha='center', va='bottom')
    
    plt.title('Pokrycie wariantów, genów i chorób przez przewidziane relacje', fontsize=16)
    plt.ylabel('Procent pokrycia [%]', fontsize=14)
    plt.ylim(0, 100)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_comparison_coverage.png", dpi=300, bbox_inches='tight')
    
    # 2. Wykres Top 10 genów
    plt.figure(figsize=(16, 10))
    
    # Zliczanie występowania genów
    gene_counts = Counter([gene for genes in confirmed_df['gene_list'] for gene in genes])
    top_genes = dict(gene_counts.most_common(10))
    
    # Oznaczenie genów, które są również w przewidzianych relacjach
    gene_keys = list(top_genes.keys())
    gene_values = list(top_genes.values())
    is_in_pred = [gene in pred_genes for gene in gene_keys]
    colors = ['#2ecc71' if in_pred else '#e74c3c' for in_pred in is_in_pred]
    
    plt.bar(gene_keys, gene_values, color=colors)
    plt.title('Top 10 najczęściej występujących genów w potwierdzonych relacjach', fontsize=16)
    plt.xlabel('Gen', fontsize=14)
    plt.ylabel('Liczba wystąpień', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    
    # Dodanie legendy
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', label='Występuje w przewidzianych'),
        Patch(facecolor='#e74c3c', label='Nie występuje w przewidzianych')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_top_genes.png", dpi=300, bbox_inches='tight')
    
    # 3. Wykres Top 10 chorób
    plt.figure(figsize=(16, 10))
    
    # Zliczanie występowania chorób
    disease_counts = Counter([disease for diseases in confirmed_df['disease_list'] for disease in diseases])
    top_diseases = dict(disease_counts.most_common(10))
    
    # Oznaczenie chorób, które są również w przewidzianych relacjach
    disease_keys = list(top_diseases.keys())
    disease_values = list(top_diseases.values())
    is_in_pred = [disease in pred_diseases for disease in disease_keys]
    colors = ['#2ecc71' if in_pred else '#e74c3c' for in_pred in is_in_pred]
    
    plt.bar(disease_keys, disease_values, color=colors)
    plt.title('Top 10 najczęściej występujących chorób w potwierdzonych relacjach', fontsize=16)
    plt.xlabel('Choroba', fontsize=14)
    plt.ylabel('Liczba wystąpień', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    
    # Dodanie legendy
    legend_elements = [
        Patch(facecolor='#2ecc71', label='Występuje w przewidzianych'),
        Patch(facecolor='#e74c3c', label='Nie występuje w przewidzianych')
    ]
    plt.legend(handles=legend_elements, loc='upper right')
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_top_diseases.png", dpi=300, bbox_inches='tight')
    
    # 6. Analiza par wariant-gen i wariant-choroba dla wspólnych wariantów
    print("\n6. Analiza dopasowań wariant-gen i wariant-choroba:")
    
    # Przygotowanie danych do analizy przypisań genów i chorób
    true_gene_pairs = set()
    pred_gene_pairs = set()
    true_disease_pairs = set()
    pred_disease_pairs = set()
    
    # Tworzenie par (wariant, gen) i (wariant, choroba)
    for _, row in confirmed_df.iterrows():
        variant = row['rs_id']
        for gene in row['gene_list']:
            true_gene_pairs.add((variant, gene))
        for disease in row['disease_list']:
            true_disease_pairs.add((variant, disease))
    
    for _, row in pred_df.iterrows():
        variant = row['rs_id']
        for gene in row['gene_list']:
            pred_gene_pairs.add((variant, gene))
        for disease in row['disease_list']:
            pred_disease_pairs.add((variant, disease))
    
    # Zliczanie TP, FP, FN dla genów
    tp_genes = len(true_gene_pairs.intersection(pred_gene_pairs))
    fp_genes = len(pred_gene_pairs - true_gene_pairs)
    fn_genes = len(true_gene_pairs - pred_gene_pairs)
    
    # Zliczanie TP, FP, FN dla chorób
    tp_diseases = len(true_disease_pairs.intersection(pred_disease_pairs))
    fp_diseases = len(pred_disease_pairs - true_disease_pairs)
    fn_diseases = len(true_disease_pairs - pred_disease_pairs)
    
    # Obliczanie precision, recall, F1 dla genów
    precision_genes = tp_genes / (tp_genes + fp_genes) if (tp_genes + fp_genes) > 0 else 0
    recall_genes = tp_genes / (tp_genes + fn_genes) if (tp_genes + fn_genes) > 0 else 0
    f1_genes = 2 * (precision_genes * recall_genes) / (precision_genes + recall_genes) if (precision_genes + recall_genes) > 0 else 0
    
    # Obliczanie precision, recall, F1 dla chorób
    precision_diseases = tp_diseases / (tp_diseases + fp_diseases) if (tp_diseases + fp_diseases) > 0 else 0
    recall_diseases = tp_diseases / (tp_diseases + fn_diseases) if (tp_diseases + fn_diseases) > 0 else 0
    f1_diseases = 2 * (precision_diseases * recall_diseases) / (precision_diseases + recall_diseases) if (precision_diseases + recall_diseases) > 0 else 0
    
    print("\nMetryki dla przypisań genów:")
    print(f"Precision: {precision_genes:.4f}")
    print(f"Recall: {recall_genes:.4f}")
    print(f"F1 Score: {f1_genes:.4f}")
    
    print("\nMetryki dla przypisań chorób:")
    print(f"Precision: {precision_diseases:.4f}")
    print(f"Recall: {recall_diseases:.4f}")
    print(f"F1 Score: {f1_diseases:.4f}")
    
    # Wykres metryk dla genów i chorób
    plt.figure(figsize=(12, 8))
    
    categories = ['Geny', 'Choroby']
    precision_values = [precision_genes, precision_diseases]
    recall_values = [recall_genes, recall_diseases]
    f1_values = [f1_genes, f1_diseases]
    
    x = np.arange(len(categories))
    width = 0.25
    
    plt.bar(x - width, precision_values, width, label='Precision', color='#3498db')
    plt.bar(x, recall_values, width, label='Recall', color='#2ecc71')
    plt.bar(x + width, f1_values, width, label='F1 Score', color='#e74c3c')
    
    plt.title('Metryki dla przypisań genów i chorób', fontsize=16)
    plt.xticks(x, categories)
    plt.ylim(0, 1)
    plt.ylabel('Wartość', fontsize=14)
    plt.legend()
    
    # Dodanie etykiet z wartościami
    for i, v in enumerate(precision_values):
        plt.text(i - width, v + 0.02, f'{v:.2f}', ha='center')
    for i, v in enumerate(recall_values):
        plt.text(i, v + 0.02, f'{v:.2f}', ha='center')
    for i, v in enumerate(f1_values):
        plt.text(i + width, v + 0.02, f'{v:.2f}', ha='center')
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_metrics.png", dpi=300, bbox_inches='tight')
    
    print(f"\nAnalizę zakończono pomyślnie. Wykresy zostały zapisane z prefiksem: {output_prefix}")
    
    # Zwróć wyniki jako słownik do potencjalnego dalszego użycia
    return {
        "score_threshold": score_threshold,
        "variant_coverage": len(common_variants)/len(confirmed_variants)*100,
        "gene_coverage": len(common_genes)/len(confirmed_genes)*100,
        "disease_coverage": len(common_diseases)/len(confirmed_diseases)*100,
        "gene_assignment_accuracy": gene_accuracy,
        "disease_assignment_accuracy": disease_accuracy,
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
    parser.add_argument("--threshold", type=float, help="Próg scoringu relacji (0-10)")
    parser.add_argument("--output-json", help="Ścieżka do pliku JSON dla zapisania wyników")
    
    args = parser.parse_args()
    
    results = analyze_data(args.pred, args.confirmed, args.prefix, args.threshold)
    
    # Jeśli podano plik JSON do zapisu wyników
    if args.output_json and results:
        try:
            # Sprawdź, czy plik już istnieje i zawiera dane
            existing_results = []
            if os.path.exists(args.output_json):
                with open(args.output_json, 'r') as f:
                    try:
                        existing_results = json.load(f)
                    except json.JSONDecodeError:
                        existing_results = []
            
            # Dodaj aktualny wynik do listy
            existing_results.append(results)
            
            # Zapisz zaktualizowaną listę
            with open(args.output_json, 'w') as f:
                json.dump(existing_results, f, indent=2)
            
            print(f"Wyniki zapisano do pliku JSON: {args.output_json}")
        except Exception as e:
            print(f"Błąd podczas zapisywania wyników do pliku JSON: {str(e)}") 