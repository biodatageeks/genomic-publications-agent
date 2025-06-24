#!/usr/bin/env python3
"""
Skrypt do analizy danych przekazywanych do LLM podczas analizy relacji.
"""

import sys
import os
import json
from typing import Dict, Any, List
from collections import defaultdict
import types

# Dodaj ścieżkę do głównego katalogu projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.pubtator_client.pubtator_client import PubTatorClient
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer

# PMID do analizy
test_pmids = ["18836445", "19306335"]

def analyze_llm_inputs():
    """Analizuje dane przekazywane do LLM"""
    print("Analiza danych przekazywanych do LLM podczas przetwarzania:", test_pmids)
    
    # Inicjalizuj analizator LLM
    analyzer = LlmContextAnalyzer()
    
    # Przed rozpoczęciem analizy tworzy katalog na prompty
    prompt_dir = "llm_prompts"
    os.makedirs(prompt_dir, exist_ok=True)
    
    prompt_counter = 0
    all_entities_in_prompts = defaultdict(int)
    
    # Podmieniam metodę _analyze_relationships_with_llm na własną
    original_method = analyzer._analyze_relationships_with_llm
    
    def mock_analyze_relationships(self_instance, variant_text, entities, passage_text):
        """Przechwytuje wywołanie analizy LLM i zapisuje prompt"""
        nonlocal prompt_counter
        
        # Przygotuj prompt tak samo jak robi to oryginalna metoda
        entities_list = "\n".join([f"- {e['entity_type']}: {e['text']} (ID: {e['id']})" for e in entities])
        
        # Zbierz statystyki typów encji
        entity_types_list = []
        for e in entities:
            entity_type = e['entity_type']
            all_entities_in_prompts[entity_type] += 1
            if entity_type not in entity_types_list:
                entity_types_list.append(entity_type)
        
        prompt_template = analyzer.USER_PROMPT_TEMPLATE
        user_message_content = prompt_template.format(
            variant_text=variant_text,
            entities_list=entities_list,
            passage_text=passage_text
        )
        
        # Zapisz prompt do pliku
        prompt_counter += 1
        prompt_file = os.path.join(prompt_dir, f"llm_prompt_{prompt_counter}.json")
        
        prompt_data = {
            "variant_text": variant_text,
            "entities": entities,
            "passage_text": passage_text,
            "formatted_prompt": user_message_content,
            "entity_types": entity_types_list  # Używam listy zamiast setu
        }
        
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f, indent=2)
        
        print(f"Zapisano prompt do {prompt_file}")
        
        # Przekazuje do oryginalnej metody
        return original_method(self_instance, variant_text, entities, passage_text)
    
    # Monkey patching metody
    analyzer._analyze_relationships_with_llm = types.MethodType(mock_analyze_relationships, analyzer)
    
    try:
        # Analizuj publikacje
        relationships = analyzer.analyze_publications(test_pmids)
        
        print(f"Liczba znalezionych relacji: {len(relationships)}")
        
        # Przeanalizuj, jakie typy encji były w relacjach
        entity_types = defaultdict(int)
        
        for rel in relationships:
            for entity_type in ["genes", "diseases", "tissues", "species", "chemicals"]:
                entity_types[entity_type] += len(rel[entity_type])
        
        print("\nLiczba encji w relacjach:")
        for entity_type, count in entity_types.items():
            print(f"  - {entity_type}: {count}")
        
        print("\nLiczba typów encji przekazanych w promptach do LLM:")
        for entity_type, count in all_entities_in_prompts.items():
            print(f"  - {entity_type}: {count}")
            
    finally:
        # Przywróć oryginalną metodę
        analyzer._analyze_relationships_with_llm = original_method
    
    # Analiza zapisanych promptów
    print("\nAnaliza pierwszych 5 promptów:")
    for i in range(1, min(6, prompt_counter + 1)):
        prompt_file = os.path.join(prompt_dir, f"llm_prompt_{i}.json")
        if os.path.exists(prompt_file):
            with open(prompt_file, "r") as f:
                data = json.load(f)
                entity_types = data.get("entity_types", [])
                print(f"\nPrompt {i}:")
                print(f"  Variant: {data.get('variant_text')}")
                print(f"  Typy encji: {entity_types}")
                print(f"  Liczba encji: {len(data.get('entities', []))}")
                
                # Zapisz prompt w bardziej czytelnej formie
                readable_file = os.path.join(prompt_dir, f"prompt_readable_{i}.txt")
                with open(readable_file, "w") as rf:
                    rf.write(f"Variant: {data.get('variant_text')}\n\n")
                    rf.write(f"Entities:\n")
                    for e in data.get('entities', []):
                        rf.write(f"  - {e['entity_type']}: {e['text']} (ID: {e['id']})\n")
                    rf.write(f"\nPassage:\n{data.get('passage_text')}\n")
    
    print(f"\nWszystkie prompty zapisano w katalogu {prompt_dir}/")
    print("Czytelne wersje pierwszych 5 promptów zapisano jako prompt_readable_X.txt")

if __name__ == "__main__":
    analyze_llm_inputs() 