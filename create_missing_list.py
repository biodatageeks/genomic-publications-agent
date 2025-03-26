#!/usr/bin/env python3
"""
Skrypt do utworzenia listy brakujących PMID-ów.
"""

import json
import sys

def load_input_pmids(file_path):
    with open(file_path, 'r') as f:
        return {line.strip() for line in f if line.strip()}

def load_result_pmids(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        return {item.get('pmid', '') for item in data if 'pmid' in item}

def main():
    if len(sys.argv) != 4:
        print(f"Użycie: {sys.argv[0]} <plik_wejściowy> <plik_wynikowy> <plik_wyjściowy>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    result_file = sys.argv[2]
    output_file = sys.argv[3]
    
    try:
        input_pmids = load_input_pmids(input_file)
        result_pmids = load_result_pmids(result_file)
        
        missing_pmids = input_pmids - result_pmids
        
        with open(output_file, 'w') as f:
            for pmid in sorted(missing_pmids):
                f.write(f"{pmid}\n")
        
        print(f"Zapisano {len(missing_pmids)} brakujących PMID-ów do pliku {output_file}")
    
    except Exception as e:
        print(f"Błąd: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 