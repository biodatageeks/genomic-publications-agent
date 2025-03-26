#!/usr/bin/env python3
"""
Narzędzie do sprawdzenia kompletności danych pobieranych dla PMID-ów.
Identyfikuje PMID-y, które nie zostały poprawnie przetworzone lub mają błędy parsowania.
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

def load_data(input_file: str) -> List[Dict[str, Any]]:
    """
    Wczytuje dane z pliku JSON.
    
    Args:
        input_file: Ścieżka do pliku wejściowego JSON
        
    Returns:
        Lista słowników z danymi
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Błąd parsowania JSON: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Błąd odczytu pliku {input_file}: {str(e)}")
        sys.exit(1)

def get_pmids_from_data(data: List[Dict[str, Any]]) -> Set[str]:
    """
    Pobiera unikalne PMID-y z danych.
    
    Args:
        data: Lista słowników z danymi
        
    Returns:
        Zbiór unikalnych PMID-ów
    """
    return set(item['pmid'] for item in data if 'pmid' in item)

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

def count_variants_per_pmid(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Zlicza liczbę wariantów dla każdego PMID.
    
    Args:
        data: Lista słowników z danymi
        
    Returns:
        Słownik {pmid: liczba_wariantów}
    """
    pmid_counts = {}
    
    for item in data:
        pmid = item.get('pmid', '')
        if pmid:
            pmid_counts[pmid] = pmid_counts.get(pmid, 0) + 1
    
    return pmid_counts

def check_entity_relationships(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """
    Sprawdza liczbę relacji dla każdego PMID.
    
    Args:
        data: Lista słowników z danymi
        
    Returns:
        Słownik {pmid: {typ_encji: liczba_relacji}}
    """
    pmid_relationships = {}
    
    for item in data:
        pmid = item.get('pmid', '')
        if not pmid:
            continue
            
        if pmid not in pmid_relationships:
            pmid_relationships[pmid] = {
                'genes': 0,
                'diseases': 0,
                'tissues': 0,
                'species': 0,
                'chemicals': 0
            }
        
        for entity_type in ['genes', 'diseases', 'tissues', 'species', 'chemicals']:
            entities = item.get(entity_type, [])
            pmid_relationships[pmid][entity_type] += len(entities)
    
    return pmid_relationships

def main():
    parser = argparse.ArgumentParser(description="Sprawdza kompletność danych PMID w plikach JSON")
    parser.add_argument("input_file", help="Ścieżka do pliku JSON z danymi")
    parser.add_argument("--check-api", action="store_true", help="Sprawdź dostępność PMID-ów w API PubTator")
    parser.add_argument("--check-content", action="store_true", help="Sprawdź zawartość PMID-ów w API PubTator")
    args = parser.parse_args()
    
    # Wczytaj dane
    logger.info(f"Wczytywanie danych z {args.input_file}")
    data = load_data(args.input_file)
    
    # Pobierz unikalne PMID-y
    pmids = get_pmids_from_data(data)
    logger.info(f"Znaleziono {len(pmids)} unikalnych PMID-ów")
    
    # Zlicz warianty dla każdego PMID-a
    pmid_counts = count_variants_per_pmid(data)
    
    print("\nPMID-y z liczbą wariantów:")
    for pmid, count in sorted(pmid_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{pmid}: {count} wariantów")
    
    # Sprawdź relacje dla każdego PMID-a
    relationships = check_entity_relationships(data)
    
    print("\nLiczba relacji dla każdego PMID-a:")
    for pmid in sorted(relationships.keys()):
        rel = relationships[pmid]
        print(f"{pmid}: Geny: {rel['genes']}, Choroby: {rel['diseases']}, Tkanki: {rel['tissues']}, Gatunki: {rel['species']}, Chemikalia: {rel['chemicals']}")
    
    if args.check_api:
        # Sprawdź dostępność PMID-ów w API
        logger.info("Sprawdzanie dostępności PMID-ów w API PubTator")
        availability = check_pmid_availability(pmids)
        
        print("\nDostępność PMID-ów w API PubTator:")
        for pmid, available in availability.items():
            status = "dostępny" if available else "niedostępny"
            print(f"{pmid}: {status}")
        
        # Podsumowanie
        available_count = sum(1 for available in availability.values() if available)
        print(f"\nPodsumowanie: {available_count} z {len(pmids)} PMID-ów dostępnych w API")
    
    if args.check_content:
        # Sprawdź zawartość PMID-ów w API
        logger.info("Sprawdzanie zawartości PMID-ów w API PubTator")
        content_info = check_pmid_content(pmids)
        
        print("\nZawartość PMID-ów w API PubTator:")
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
        
        print("\nLiczba anotacji wariantów w PubTator dla każdego PMID:")
        for pmid, count in sorted(mutation_annotations.items()):
            variants_in_data = pmid_counts.get(pmid, 0)
            status = "OK" if count >= variants_in_data else "BRAK ANOTACJI"
            print(f"{pmid}: {count} anotacji w PubTator, {variants_in_data} wariantów w danych - {status}")

if __name__ == "__main__":
    main() 