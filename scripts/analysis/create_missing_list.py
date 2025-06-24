#!/usr/bin/env python3
"""
Skrypt do utworzenia listy brakujących PMID-ów.
"""

import sys
from scripts.utils import load_pmids_from_file, load_csv_pmids, save_pmids_to_file, ensure_dirs_exist

def main():
    # Upewnij się, że wymagane katalogi istnieją
    ensure_dirs_exist()
    
    if len(sys.argv) != 4:
        print(f"Użycie: {sys.argv[0]} <plik_wejściowy> <plik_wynikowy> <plik_wyjściowy>")
        print("Przykład: python create_missing_list.py data/pmids/input_pmids.txt data/csv/results.csv data/pmids/missing_pmids.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    result_file = sys.argv[2]
    output_file = sys.argv[3]
    
    try:
        # Wczytaj PMID-y z pliku wejściowego
        input_pmids = load_pmids_from_file(input_file)
        print(f"Wczytano {len(input_pmids)} PMIDów z pliku wejściowego")
        
        # Wczytaj PMID-y z pliku wynikowego (CSV)
        result_pmids = load_csv_pmids(result_file)
        print(f"Wczytano {len(result_pmids)} PMIDów z pliku wynikowego")
        
        # Znajdź brakujące PMID-y
        missing_pmids = input_pmids - result_pmids
        print(f"Znaleziono {len(missing_pmids)} brakujących PMIDów")
        
        # Zapisz brakujące PMID-y do pliku
        save_pmids_to_file(missing_pmids, output_file)
    
    except Exception as e:
        print(f"Błąd: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 