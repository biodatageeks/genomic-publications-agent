#!/usr/bin/env python3
"""
Skrypt do analizy anotacji w publikacjach naukowych.
"""

import sys
import os
import json
from collections import defaultdict

# Dodaj ścieżkę do głównego katalogu projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.pubtator_client.pubtator_client import PubTatorClient
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer

# PMID do analizy
test_pmids = ["18836445", "19306335"]

def analyze_entities():
    """Analizuje encje w publikacjach"""
    print("Analiza encji w publikacjach:", test_pmids)
    
    client = PubTatorClient()
    
    # Pobierz publikacje
    publications = client.get_publications_by_pmids(test_pmids)
    
    # Inicjalizuj liczniki
    entity_types_counter = defaultdict(int)
    passage_entity_counts = []
    
    for pub in publications:
        print(f"\nPublikacja PMID: {pub.id}")
        print(f"Liczba pasaży: {len(pub.passages)}")
        
        for i, passage in enumerate(pub.passages):
            print(f"\n  Pasaż {i+1}, liczba anotacji: {len(passage.annotations)}")
            
            # Grupuj anotacje według typu
            types_in_passage = defaultdict(list)
            
            for annotation in passage.annotations:
                annotation_type = annotation.infons.get("type", "")
                if annotation_type:
                    types_in_passage[annotation_type].append(annotation.text)
                    entity_types_counter[annotation_type] += 1
            
            # Wypisz typy anotacji w pasażu
            print("  Typy anotacji i liczba wystąpień:")
            for typ, annotations in types_in_passage.items():
                print(f"    - {typ}: {len(annotations)}")
                if len(annotations) > 0:
                    print(f"      Przykład: {annotations[0]}")
            
            # Zapisz liczby encji dla tego pasażu
            passage_data = {
                "pmid": pub.id,
                "passage_index": i,
                "entity_counts": {k: len(v) for k, v in types_in_passage.items()}
            }
            passage_entity_counts.append(passage_data)
    
    print("\nPodsumowanie wszystkich typów encji:")
    for typ, count in sorted(entity_types_counter.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {typ}: {count}")
    
    # Mapowanie typów encji używane w LlmContextAnalyzer
    analyzer = LlmContextAnalyzer()
    print("\nMapowanie typów encji z LlmContextAnalyzer:")
    for category, types in analyzer.ENTITY_TYPES.items():
        print(f"  - {category}: {types}")
    
    # Zapisz dane do pliku JSON
    with open("entity_analysis.json", "w") as f:
        json.dump({
            "entity_type_counts": dict(entity_types_counter),
            "passage_entity_counts": passage_entity_counts
        }, f, indent=2)
    
    print("\nDane zapisane do entity_analysis.json")

if __name__ == "__main__":
    analyze_entities() 