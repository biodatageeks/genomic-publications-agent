#!/usr/bin/env python3
"""
Narzędzie do sprawdzenia anotacji wariantów w PubTator dla listy PMID-ów.
Sprawdza, które PMID-y zawierają anotacje typu Variant/Mutation/DNAMutation.
"""

import json
import sys
import argparse
import logging
import requests
from typing import List, Dict, Any, Set
from scripts.utils import load_pmids_from_file, save_json_file, ensure_dirs_exist

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_variant_annotations(pmids: Set[str]) -> Dict[str, Dict[str, Any]]:
    """
    Sprawdza anotacje wariantów dla każdego PMID w PubTator.
    
    Args:
        pmids: Zbiór PMID-ów do sprawdzenia
        
    Returns:
        Słownik {pmid: {has_variants: bool, annotation_count: int, variants: List[str]}}
    """
    results = {}
    
    total = len(pmids)
    current = 0
    
    # Sprawdzamy każdy PMID indywidualnie
    for pmid in pmids:
        current += 1
        logger.info(f"Sprawdzanie anotacji wariantów dla PMID: {pmid} ({current}/{total})")
        
        try:
            response = requests.get(
                f"https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson",
                params={"pmids": pmid},
                headers={"Accept": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "PubTator3" in data and data["PubTator3"]:
                        doc = data["PubTator3"][0]
                        
                        variant_annotations = []
                        
                        # Przeszukaj wszystkie anotacje we wszystkich sekcjach
                        for passage in doc.get("passages", []):
                            for anno in passage.get("annotations", []):
                                anno_type = anno.get("infons", {}).get("type", "unknown")
                                
                                # Sprawdź, czy anotacja jest typu Variant, Mutation lub DNAMutation
                                if anno_type in ["Variant", "Mutation", "DNAMutation"]:
                                    variant_text = anno.get("text", "")
                                    if variant_text:
                                        variant_annotations.append(variant_text)
                        
                        has_variants = len(variant_annotations) > 0
                        
                        results[pmid] = {
                            "has_variants": has_variants,
                            "annotation_count": len(variant_annotations),
                            "variants": variant_annotations
                        }
                    else:
                        results[pmid] = {
                            "has_variants": False,
                            "annotation_count": 0,
                            "variants": [],
                            "error": "Brak danych PubTator3"
                        }
                except json.JSONDecodeError as e:
                    results[pmid] = {
                        "has_variants": False,
                        "annotation_count": 0,
                        "variants": [],
                        "error": f"Błąd parsowania JSON: {str(e)}"
                    }
            else:
                results[pmid] = {
                    "has_variants": False,
                    "annotation_count": 0,
                    "variants": [],
                    "error": f"Błąd HTTP: {response.status_code}"
                }
                    
        except requests.exceptions.RequestException as e:
            results[pmid] = {
                "has_variants": False,
                "annotation_count": 0,
                "variants": [],
                "error": f"Błąd połączenia: {str(e)}"
            }
    
    return results

def main():
    # Upewnij się, że wymagane katalogi istnieją
    ensure_dirs_exist()
    
    parser = argparse.ArgumentParser(description="Sprawdza anotacje wariantów w PubTator dla listy PMID-ów")
    parser.add_argument("input_file", help="Ścieżka do pliku z listą PMID-ów")
    parser.add_argument("--output-file", help="Ścieżka do pliku wyjściowego JSON z wynikami")
    args = parser.parse_args()
    
    # Wczytaj PMID-y
    logger.info(f"Wczytywanie PMID-ów z {args.input_file}")
    pmids = load_pmids_from_file(args.input_file)
    logger.info(f"Znaleziono {len(pmids)} unikalnych PMID-ów")
    
    # Sprawdź anotacje wariantów
    logger.info("Sprawdzanie anotacji wariantów w PubTator")
    results = check_variant_annotations(pmids)
    
    # Zlicz PMID-y z wariantami
    pmids_with_variants = sum(1 for info in results.values() if info.get("has_variants", False))
    
    # Podsumowanie
    print(f"\nPodsumowanie:")
    print(f"Sprawdzono {len(pmids)} PMID-ów")
    print(f"PMID-y z anotacjami wariantów: {pmids_with_variants} ({pmids_with_variants/len(pmids)*100:.2f}%)")
    print(f"PMID-y bez anotacji wariantów: {len(pmids) - pmids_with_variants} ({(len(pmids) - pmids_with_variants)/len(pmids)*100:.2f}%)")
    
    # Szczegóły
    pmids_with_variants_list = sorted(
        [(pmid, info["annotation_count"]) for pmid, info in results.items() if info.get("has_variants", False)],
        key=lambda x: x[1],
        reverse=True
    )
    
    if pmids_with_variants_list:
        print(f"\nPMID-y z anotacjami wariantów:")
        for pmid, count in pmids_with_variants_list:
            variants = results[pmid]["variants"]
            variants_str = ", ".join(variants[:3])
            if len(variants) > 3:
                variants_str += f" i {len(variants) - 3} więcej"
            print(f"- {pmid}: {count} wariantów ({variants_str})")
    
    pmids_without_variants = sorted([pmid for pmid, info in results.items() if not info.get("has_variants", False)])
    
    if pmids_without_variants:
        print(f"\nPMID-y bez anotacji wariantów:")
        for pmid in pmids_without_variants:
            if "error" in results[pmid]:
                print(f"- {pmid}: BŁĄD - {results[pmid]['error']}")
            else:
                print(f"- {pmid}: brak anotacji wariantów")
    
    # Zapisz wyniki do pliku JSON
    if args.output_file:
        logger.info(f"Zapisywanie wyników do {args.output_file}")
        save_json_file(results, args.output_file)
        print(f"\nWyniki zapisano do pliku {args.output_file}")

if __name__ == "__main__":
    main() 