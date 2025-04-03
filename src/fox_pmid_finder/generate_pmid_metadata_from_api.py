#!/usr/bin/env python3
"""
Skrypt pobierający publikacje dla genów FOX z API NCBI E-utilities
i tworzący plik JSON z metadanymi (PMID -> gen)
"""

import json
import os
import logging
import time
import requests
from typing import Dict, List, Set, Any

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FoxPmidMetadataGenerator:
    """
    Klasa odpowiedzialna za pobieranie informacji o publikacjach związanych z genami FOX
    i generowanie metadanych przypisujących PMIDy do odpowiednich genów.
    """
    
    def __init__(self):
        """Inicjalizacja generatora metadanych."""
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.pmid_metadata = {}  # słownik PMID -> {gen}
        self.genes = []
        
    def load_genes_from_file(self, file_path: str = "data/input/fox_unique_genes.txt") -> List[str]:
        """
        Wczytuje listę genów z pliku tekstowego.
        
        Args:
            file_path: Ścieżka do pliku z listą genów (jeden na linię)
            
        Returns:
            Lista wczytanych genów
        """
        logger.info(f"Wczytywanie genów z pliku {file_path}")
        try:
            with open(file_path, 'r') as file:
                self.genes = [line.strip() for line in file if line.strip()]
            logger.info(f"Wczytano {len(self.genes)} genów")
            return self.genes
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania genów: {str(e)}")
            raise
    
    def fetch_pmids_for_gene(self, gene: str, retmax: int = 1000) -> List[str]:
        """
        Pobiera identyfikatory PMID publikacji związanych z danym genem.
        
        Args:
            gene: Symbol genu
            retmax: Maksymalna liczba zwracanych wyników
            
        Returns:
            Lista identyfikatorów PMID
        """
        logger.info(f"Pobieranie publikacji dla genu {gene}")
        
        # Construct query for human studies related to the gene
        search_term = f"{gene}[Gene Name] AND human[Organism]"
        
        # Use ESearch to find IDs
        esearch_url = f"{self.base_url}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": search_term,
            "retmax": retmax,
            "retmode": "json"
        }
        
        try:
            response = requests.get(esearch_url, params=params, timeout=30)
            
            if response.status_code == 200:
                results = response.json()
                id_list = results.get('esearchresult', {}).get('idlist', [])
                
                logger.info(f"Znaleziono {len(id_list)} publikacji dla genu {gene}")
                return id_list
            else:
                logger.warning(f"Nieudane zapytanie dla genu {gene}: status {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Błąd podczas pobierania publikacji dla genu {gene}: {str(e)}")
            return []
    
    def generate_metadata(self, output_pmids_path: str = "data/pmids/fox_pmids.txt", 
                          output_json_path: str = "data/pmids/fox_pmids_metadata.json") -> Dict[str, Any]:
        """
        Generuje metadane dla PMIDów i zapisuje je do pliku JSON.
        Zapisuje również wszystkie unikalne PMIDy do pliku tekstowego.
        
        Args:
            output_pmids_path: Ścieżka do pliku wyjściowego z PMIDami
            output_json_path: Ścieżka do pliku wyjściowego JSON
            
        Returns:
            Słownik z metadanymi
        """
        if not self.genes:
            logger.error("Brak wczytanych genów. Najpierw wczytaj geny za pomocą load_genes_from_file()")
            raise ValueError("Brak wczytanych genów")
        
        all_pmids = set()  # zbiór wszystkich unikalnych PMIDów
        
        # Pobierz publikacje dla każdego genu i zapisz metadane
        for gene in self.genes:
            try:
                # Pobierz PMIDy dla genu
                pmids = self.fetch_pmids_for_gene(gene)
                
                # Zapisz metadane
                for pmid in pmids:
                    # Dodaj PMID do metadanych tylko jeśli jeszcze nie był przypisany do innego genu
                    if pmid not in self.pmid_metadata:
                        self.pmid_metadata[pmid] = {"gene": gene}
                        all_pmids.add(pmid)
                    
                # Dodaj opóźnienie, aby nie przekroczyć limitów API
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania genu {gene}: {str(e)}")
        
        # Zapisz wszystkie unikalne PMIDy do pliku tekstowego
        logger.info(f"Zapisywanie {len(all_pmids)} unikalnych PMIDów do pliku {output_pmids_path}")
        try:
            # Upewnij się, że katalog istnieje
            os.makedirs(os.path.dirname(output_pmids_path), exist_ok=True)
            
            with open(output_pmids_path, 'w') as file:
                for pmid in sorted(all_pmids):
                    file.write(f"{pmid}\n")
                    
            logger.info(f"Zapisano {len(all_pmids)} PMIDów do pliku {output_pmids_path}")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania PMIDów do pliku: {str(e)}")
        
        # Zapisz metadane do pliku JSON
        logger.info(f"Zapisywanie metadanych do pliku {output_json_path}")
        try:
            # Upewnij się, że katalog istnieje
            os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
            
            with open(output_json_path, 'w') as file:
                json.dump(self.pmid_metadata, file, indent=2)
                
            logger.info(f"Zapisano metadane dla {len(self.pmid_metadata)} PMIDów do pliku {output_json_path}")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania metadanych do pliku JSON: {str(e)}")
        
        return self.pmid_metadata
    
    def generate_csv_report(self, output_csv_path: str = "data/results/fox_gene_pmids_count.csv") -> None:
        """
        Generuje plik CSV z informacją o liczbie publikacji dla każdego genu.
        
        Args:
            output_csv_path: Ścieżka do pliku wyjściowego CSV
        """
        if not self.pmid_metadata:
            logger.error("Brak metadanych. Najpierw wygeneruj metadane za pomocą generate_metadata()")
            return
        
        # Oblicz liczbę PMIDów dla każdego genu
        gene_counts = {}
        for pmid, metadata in self.pmid_metadata.items():
            gene = metadata["gene"]
            if gene in gene_counts:
                gene_counts[gene] += 1
            else:
                gene_counts[gene] = 1
        
        # Zapisz dane do pliku CSV
        logger.info(f"Zapisywanie raportu do pliku {output_csv_path}")
        try:
            # Upewnij się, że katalog istnieje
            os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
            
            with open(output_csv_path, 'w') as file:
                file.write("Gen,Liczba_PMIDs\n")
                
                # Zapisz dane dla wszystkich genów, nawet tych bez publikacji
                for gene in self.genes:
                    count = gene_counts.get(gene, 0)
                    file.write(f"{gene},{count}\n")
                    
            logger.info(f"Zapisano raport dla {len(self.genes)} genów")
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania raportu: {str(e)}")

def main():
    """Główna funkcja skryptu."""
    generator = FoxPmidMetadataGenerator()
    
    try:
        # Wczytaj geny
        generator.load_genes_from_file()
        
        # Wygeneruj metadane
        generator.generate_metadata()
        
        # Wygeneruj raport CSV
        generator.generate_csv_report()
        
        logger.info("Przetwarzanie zakończone pomyślnie")
        
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania skryptu: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    main() 