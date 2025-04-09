#!/usr/bin/env python3
"""
Narzędzie do porównania PMID-ów z pliku wejściowego z PMID-ami w wynikach eksperymentu.
Identyfikuje PMID-y, które nie zostały przetworzone.
"""

import json
import sys
import argparse
import logging
import requests
from typing import List, Dict, Any, Set, Tuple

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_input_pmids(input_file: str) -> Set[str]:
    """
    Wczytuje PMID-y z pliku wejściowego.
    
    Args:
        input_file: Ścieżka do pliku z listą PMID-ów
        
    Returns:
        Zbiór unikalnych PMID-ów
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            pmids = {line.strip() for line in f if line.strip()}
        return pmids
    except Exception as e:
        logger.error(f"Błąd odczytu pliku {input_file}: {str(e)}")
        sys.exit(1)

def load_results_pmids(results_file: str) -> Set[str]:
    """
    Wczytuje PMID-y z pliku wynikowego JSON.
    
    Args:
        results_file: Ścieżka do pliku wynikowego JSON
        
    Returns:
        Zbiór unikalnych PMID-ów
    """
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Pobierz unikalne PMID-y z danych
        pmids = {item.get('pmid', '') for item in data if 'pmid' in item}
        return pmids
    except json.JSONDecodeError as e:
        logger.error(f"Błąd parsowania JSON: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd odczytu pliku {results_file}: {str(e)}")
        sys.exit(1)

def check_pmid_availability(pmids: Set[str]) -> Dict[str, bool]:
    """
    Sprawdza dostępność PMID-ów w PubTator poprzez API.
    
    Args:
        pmids: Zbiór PMID-ów do sprawdzenia
        
    Returns:
        Słownik {pmid: dostępność}
    """
    availability = {}
    
    # Sprawdzamy po 10 PMID-ów na raz, aby nie obciążać API
    batch_size = 10
    pmids_list = list(pmids)
    
    for i in range(0, len(pmids_list), batch_size):
        batch = pmids_list[i:i+batch_size]
        pmids_str = ",".join(batch)
        
        try:
            logger.info(f"Sprawdzanie dostępności dla PMID-ów: {pmids_str}")
            response = requests.get(
                f"https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/biocjson",
                params={"pmids": pmids_str},
                headers={"Accept": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "PubTator3" in data:
                        # Sprawdź, które PMID-y są w odpowiedzi
                        returned_pmids = set(doc.get("id", "") for doc in data["PubTator3"])
                        
                        for pmid in batch:
                            availability[pmid] = pmid in returned_pmids
                    else:
                        # Jeśli brak klucza PubTator3, to dane są niedostępne
                        for pmid in batch:
                            availability[pmid] = False
                except json.JSONDecodeError:
                    # Błąd parsowania JSON oznacza, że dane są niedostępne
                    for pmid in batch:
                        availability[pmid] = False
            else:
                # Błąd HTTP oznacza, że dane są niedostępne
                for pmid in batch:
                    availability[pmid] = False
                    
        except requests.exceptions.RequestException:
            # Błąd połączenia oznacza, że nie można sprawdzić dostępności
            for pmid in batch:
                availability[pmid] = False
    
    return availability

def check_pmid_content(pmids: Set[str]) -> Dict[str, Dict[str, Any]]:
    """
    Sprawdza zawartość PMID-ów w PubTator poprzez API.
    
    Args:
        pmids: Zbiór PMID-ów do sprawdzenia
        
    Returns:
        Słownik {pmid: {sections: int, annotations: {type: count}}}
    """
    content_info = {}
    
    # Sprawdzamy każdy PMID indywidualnie
    for pmid in pmids:
        try:
            logger.info(f"Sprawdzanie zawartości dla PMID: {pmid}")
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
                        passages = doc.get("passages", [])
                        
                        # Zlicz anotacje według typu
                        annotations_count = {}
                        for passage in passages:
                            for anno in passage.get("annotations", []):
                                anno_type = anno.get("infons", {}).get("type", "unknown")
                                annotations_count[anno_type] = annotations_count.get(anno_type, 0) + 1
                        
                        content_info[pmid] = {
                            "sections": len(passages),
                            "annotations": annotations_count
                        }
                    else:
                        content_info[pmid] = {
                            "sections": 0,
                            "annotations": {},
                            "error": "Brak danych PubTator3"
                        }
                except json.JSONDecodeError as e:
                    content_info[pmid] = {
                        "sections": 0,
                        "annotations": {},
                        "error": f"Błąd parsowania JSON: {str(e)}"
                    }
            else:
                content_info[pmid] = {
                    "sections": 0,
                    "annotations": {},
                    "error": f"Błąd HTTP: {response.status_code}"
                }
                    
        except requests.exceptions.RequestException as e:
            content_info[pmid] = {
                "sections": 0,
                "annotations": {},
                "error": f"Błąd połączenia: {str(e)}"
            }
    
    return content_info

def main():
    parser = argparse.ArgumentParser(description="Porównuje PMID-y z pliku wejściowego z wynikami eksperymentu")
    parser.add_argument("input_file", help="Ścieżka do pliku z wejściowymi PMID-ami")
    parser.add_argument("results_file", help="Ścieżka do pliku JSON z wynikami eksperymentu")
    parser.add_argument("--check-api", action="store_true", help="Sprawdź dostępność brakujących PMID-ów w API PubTator")
    parser.add_argument("--check-content", action="store_true", help="Sprawdź zawartość brakujących PMID-ów w API PubTator")
    args = parser.parse_args()
    
    # Wczytaj PMID-y z pliku wejściowego
    logger.info(f"Wczytywanie PMID-ów z {args.input_file}")
    input_pmids = load_input_pmids(args.input_file)
    logger.info(f"Znaleziono {len(input_pmids)} unikalnych PMID-ów w pliku wejściowym")
    
    # Wczytaj PMID-y z pliku wynikowego
    logger.info(f"Wczytywanie PMID-ów z {args.results_file}")
    results_pmids = load_results_pmids(args.results_file)
    logger.info(f"Znaleziono {len(results_pmids)} unikalnych PMID-ów w wynikach")
    
    # Znajdź PMID-y, które są w pliku wejściowym, ale nie ma ich w wynikach
    missing_pmids = input_pmids - results_pmids
    
    # Znajdź PMID-y, które są w wynikach, ale nie ma ich w pliku wejściowym
    extra_pmids = results_pmids - input_pmids
    
    # Wyświetl statystyki
    print(f"\nPodsumowanie:")
    print(f"PMID-y w pliku wejściowym: {len(input_pmids)}")
    print(f"PMID-y w wynikach: {len(results_pmids)}")
    print(f"Brakujące PMID-y: {len(missing_pmids)}")
    print(f"Dodatkowe PMID-y: {len(extra_pmids)}")
    print(f"Kompletność danych: {len(results_pmids)/len(input_pmids)*100:.2f}%")
    
    if missing_pmids:
        print(f"\nBrakujące PMID-y ({len(missing_pmids)}):")
        for pmid in sorted(missing_pmids):
            print(f"- {pmid}")
    
    if extra_pmids:
        print(f"\nDodatkowe PMID-y ({len(extra_pmids)}):")
        for pmid in sorted(extra_pmids):
            print(f"- {pmid}")
    
    if args.check_api and missing_pmids:
        # Sprawdź dostępność brakujących PMID-ów w API
        logger.info("Sprawdzanie dostępności brakujących PMID-ów w API PubTator")
        availability = check_pmid_availability(missing_pmids)
        
        available_count = sum(1 for available in availability.values() if available)
        
        print(f"\nDostępność brakujących PMID-ów w API PubTator:")
        print(f"Dostępne: {available_count} z {len(missing_pmids)} ({available_count/len(missing_pmids)*100:.2f}%)")
        
        print("\nSzczegóły dostępności:")
        for pmid, available in sorted(availability.items()):
            status = "dostępny" if available else "niedostępny"
            print(f"- {pmid}: {status}")
    
    if args.check_content and missing_pmids:
        # Pobierz próbkę brakujących PMID-ów (maksymalnie 5)
        sample_pmids = set(sorted(missing_pmids)[:5])
        
        # Sprawdź zawartość wybranych PMID-ów w API
        logger.info(f"Sprawdzanie zawartości {len(sample_pmids)} wybranych brakujących PMID-ów w API PubTator")
        content_info = check_pmid_content(sample_pmids)
        
        print(f"\nZawartość wybranych brakujących PMID-ów w API PubTator:")
        for pmid, info in sorted(content_info.items()):
            if "error" in info:
                print(f"{pmid}: BŁĄD - {info['error']}")
            else:
                print(f"{pmid}: {info['sections']} sekcji, anotacje: ", end="")
                annotations = info["annotations"]
                if annotations:
                    print(", ".join([f"{type}: {count}" for type, count in sorted(annotations.items())]))
                else:
                    print("brak")
        
        # Sprawdź, czy są anotacje typu Mutation/Variant/DNAMutation
        mutation_annotations = {
            pmid: info["annotations"].get("Mutation", 0) + 
                 info["annotations"].get("Variant", 0) + 
                 info["annotations"].get("DNAMutation", 0)
            for pmid, info in content_info.items() if "annotations" in info
        }
        
        print("\nLiczba anotacji wariantów w PubTator dla wybranych brakujących PMID-ów:")
        for pmid, count in sorted(mutation_annotations.items()):
            status = "OK" if count > 0 else "BRAK WARIANTÓW"
            print(f"{pmid}: {count} anotacji wariantów - {status}")

if __name__ == "__main__":
    main() 