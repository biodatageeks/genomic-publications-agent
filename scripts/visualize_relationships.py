#!/usr/bin/env python3
"""
Skrypt wizualizujący relacje między wariantami, genami i chorobami.
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import networkx as nx
import argparse
from collections import Counter

# Dodanie ścieżki do katalogu głównego projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_relationship_graph(csv_file, output_image):
    """
    Tworzy graf relacji między wariantami, genami i chorobami.
    
    Args:
        csv_file: Ścieżka do pliku CSV z relacjami
        output_image: Ścieżka do zapisania obrazu grafu
    """
    try:
        # Wczytanie danych
        df = pd.read_csv(csv_file)
        
        # Utworzenie grafu
        G = nx.Graph()
        
        # Dodanie węzłów (warianty, geny, choroby)
        variants = set(df['variant_text'].dropna().unique())
        genes = set(df['gene_text'].dropna().unique())
        diseases = set(df['disease_text'].dropna().unique())
        
        # Usunięcie pustych stringów
        variants = {v for v in variants if v}
        genes = {g for g in genes if g}
        diseases = {d for d in diseases if d}
        
        # Dodanie wariantów jako węzłów
        for variant in variants:
            G.add_node(variant, type='variant')
            
        # Dodanie genów jako węzłów
        for gene in genes:
            G.add_node(gene, type='gene')
            
        # Dodanie chorób jako węzłów
        for disease in diseases:
            G.add_node(disease, type='disease')
            
        # Dodanie krawędzi między wariantami a genami
        for _, row in df.iterrows():
            variant = row['variant_text']
            gene = row['gene_text']
            disease = row['disease_text']
            
            if variant and gene and variant in variants and gene in genes:
                G.add_edge(variant, gene)
                
            if variant and disease and variant in variants and disease in diseases:
                G.add_edge(variant, disease)
                
            if gene and disease and gene in genes and disease in diseases:
                G.add_edge(gene, disease)
        
        # Określenie kolorów węzłów
        colors = []
        for node in G.nodes():
            if node in variants:
                colors.append('skyblue')
            elif node in genes:
                colors.append('lightgreen')
            elif node in diseases:
                colors.append('salmon')
        
        # Określenie pozycji węzłów
        pos = nx.spring_layout(G, seed=42)
        
        # Wizualizacja grafu
        plt.figure(figsize=(12, 10))
        nx.draw_networkx(G, pos, node_color=colors, with_labels=True, 
                         node_size=700, font_size=10, 
                         font_weight='bold', alpha=0.7)
        
        # Dodanie legendy
        variant_patch = mlines.Line2D([0], [0], marker='o', color='w', markerfacecolor='skyblue',
                                  markersize=15, label='Wariant')
        gene_patch = mlines.Line2D([0], [0], marker='o', color='w', markerfacecolor='lightgreen',
                               markersize=15, label='Gen')
        disease_patch = mlines.Line2D([0], [0], marker='o', color='w', markerfacecolor='salmon',
                                  markersize=15, label='Choroba')
        
        plt.legend(handles=[variant_patch, gene_patch, disease_patch], loc='upper right')
        
        plt.title('Graf relacji między wariantami, genami i chorobami')
        plt.tight_layout()
        plt.savefig(output_image, dpi=300)
        plt.close()
        
        print(f"Graf został zapisany do pliku: {output_image}")
        
        # Generowanie statystyk
        print(f"\nStatystyki grafu:")
        print(f" - Liczba węzłów: {G.number_of_nodes()}")
        print(f" - Liczba krawędzi: {G.number_of_edges()}")
        print(f" - Liczba wariantów: {len(variants)}")
        print(f" - Liczba genów: {len(genes)}")
        print(f" - Liczba chorób: {len(diseases)}")
        
    except ImportError as e:
        print(f"Błąd: Brak wymaganych bibliotek. {str(e)}")
        print("Zainstaluj wymagane biblioteki: pip install matplotlib networkx")
    except Exception as e:
        print(f"Błąd podczas tworzenia grafu: {str(e)}")

def main():
    """Główna funkcja skryptu."""
    parser = argparse.ArgumentParser(description="Wizualizacja relacji między wariantami, genami i chorobami.")
    parser.add_argument("--input", "-i", type=str, default="variant_relationships.csv",
                        help="Ścieżka do pliku CSV z relacjami (domyślnie: variant_relationships.csv)")
    parser.add_argument("--output", "-o", type=str, default="variant_relationships_graph.png",
                        help="Ścieżka do pliku wyjściowego z grafem (domyślnie: variant_relationships_graph.png)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Błąd: Plik {args.input} nie istnieje.")
        return
    
    # Tworzenie katalogu dla pliku wyjściowego, jeśli nie istnieje
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    create_relationship_graph(args.input, args.output)

if __name__ == "__main__":
    main() 