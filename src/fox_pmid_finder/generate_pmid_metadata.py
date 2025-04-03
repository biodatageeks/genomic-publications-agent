#!/usr/bin/env python3
"""
Skrypt generujący plik JSON z metadanymi dla PMIDów, 
przypisując każdemu PMID odpowiedni gen FOX na podstawie liczby wystąpień genów.
"""

import json
import os
import csv
import logging

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_pmid_metadata(
    pmids_file_path="data/pmids/fox_pmids.txt",
    counts_file_path="data/results/fox_gene_pmids_count.csv",
    output_json_path="data/pmids/fox_pmids_metadata.json"
):
    """
    Generuje plik JSON z metadanymi dla PMIDów, przypisując każdemu PMID odpowiedni gen FOX.
    
    Args:
        pmids_file_path: Ścieżka do pliku z PMIDami
        counts_file_path: Ścieżka do pliku CSV z liczbą PMIDów dla każdego genu
        output_json_path: Ścieżka do wyjściowego pliku JSON
    """
    # Wczytaj PMIDy
    logger.info(f"Wczytywanie PMIDów z pliku {pmids_file_path}")
    try:
        with open(pmids_file_path, 'r') as file:
            pmids = [line.strip() for line in file if line.strip()]
        logger.info(f"Wczytano {len(pmids)} PMIDów")
    except Exception as e:
        logger.error(f"Błąd podczas wczytywania pliku z PMIDami: {str(e)}")
        return
    
    # Wczytaj liczby PMIDów dla genów
    logger.info(f"Wczytywanie liczby PMIDów dla genów z pliku {counts_file_path}")
    genes_counts = []
    try:
        with open(counts_file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                genes_counts.append((row['Gen'], int(row['Liczba_PMIDs'])))
        logger.info(f"Wczytano dane dla {len(genes_counts)} genów")
    except Exception as e:
        logger.error(f"Błąd podczas wczytywania pliku z liczbą PMIDów: {str(e)}")
        return
    
    # Przypisz geny do PMIDów
    logger.info("Przypisywanie genów do PMIDów")
    pmid_metadata = {}
    index = 0
    
    # Upewnij się, że liczba PMIDów w CSV i w pliku tekstowym się zgadza
    total_pmids_csv = sum(count for _, count in genes_counts)
    if total_pmids_csv != len(pmids):
        logger.warning(f"Niezgodność liczby PMIDów: w pliku CSV: {total_pmids_csv}, w pliku z PMIDami: {len(pmids)}")
        logger.warning("Wartości w pliku CSV mogą wymagać korekty")
    
    # Przypisuj PMIDy do genów zgodnie z plikiem CSV
    for gene, count in genes_counts:
        logger.debug(f"Przypisywanie PMIDów dla genu {gene} (liczba: {count})")
        for i in range(count):
            if index < len(pmids):
                pmid = pmids[index]
                pmid_metadata[pmid] = {"gene": gene}
                index += 1
            else:
                logger.warning(f"Skończył się zakres PMIDów podczas przypisywania dla genu {gene} (indeks {i+1}/{count})")
                break
        
        if index >= len(pmids):
            logger.warning("Brak więcej PMIDów do przypisania")
            break
    
    # Sprawdź, czy wszystkie PMIDy zostały przypisane
    if index < len(pmids):
        logger.warning(f"Nie wszystkie PMIDy zostały przypisane do genów. Pozostało {len(pmids) - index} PMIDów.")
    
    # Zapisz metadane do pliku JSON
    logger.info(f"Zapisywanie metadanych do pliku {output_json_path}")
    try:
        with open(output_json_path, 'w') as file:
            json.dump(pmid_metadata, file, indent=2)
        logger.info(f"Zapisano metadane dla {len(pmid_metadata)} PMIDów")
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania pliku JSON: {str(e)}")

if __name__ == "__main__":
    generate_pmid_metadata() 