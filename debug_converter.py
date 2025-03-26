#!/usr/bin/env python3
import json
import csv

# Wczytaj dane z pliku JSON
data = json.load(open('results_llm_debug.csv_llm_temp.json'))

# Przygotuj nagłówki dla pliku CSV
headers = [
    'pmid', 'variant_text', 'variant_id', 'entity_type', 'entity_text', 
    'entity_id', 'has_relationship', 'explanation', 'passage_text'
]

# Otwórz plik CSV do zapisu
with open('manual_debug.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    
    # Dla każdej relacji w pliku JSON
    for rel in data:
        pmid = rel.get('pmid', '')
        variant_text = rel.get('variant_text', '')
        variant_id = rel.get('variant_id', '')
        passage_text = rel.get('passage_text', '')
        
        # Sprawdź każdy typ encji
        for entity_type in ['genes', 'diseases', 'tissues', 'species', 'chemicals']:
            entities = rel.get(entity_type, [])
            
            # Dla każdej encji danego typu
            for entity in entities:
                # Przygotuj wiersz CSV
                row = {
                    'pmid': pmid,
                    'variant_text': variant_text,
                    'variant_id': variant_id,
                    'entity_type': entity_type[:-1] if entity_type != 'species' else 'species',
                    'entity_text': entity.get('text', ''),
                    'entity_id': entity.get('id', ''),
                    'has_relationship': 'True',
                    'explanation': entity.get('explanation', ''),
                    'passage_text': passage_text
                }
                
                # Zapisz wiersz do pliku CSV
                writer.writerow(row)

print("Konwersja zakończona. Wyniki zapisano w pliku manual_debug.csv") 