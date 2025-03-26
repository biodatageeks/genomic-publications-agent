import json
import csv

# Wczytaj dane JSON
with open('threshold_analysis_results.json', 'r') as f:
    data = json.load(f)

# Sortuj dane według wartości threshold (None na końcu)
sorted_data = sorted([item for item in data if item['score_threshold'] is not None], 
                    key=lambda x: x['score_threshold'])
none_data = [item for item in data if item['score_threshold'] is None]
sorted_data.extend(none_data)

# Zapisz dane do CSV
with open('threshold_metrics.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    # Nagłówki
    writer.writerow(['threshold', 'gene_precision', 'gene_recall', 'gene_f1', 
                     'disease_precision', 'disease_recall', 'disease_f1'])
    
    # Dane
    for item in sorted_data:
        threshold = item['score_threshold'] if item['score_threshold'] is not None else 'None'
        writer.writerow([
            threshold,
            item['gene_precision'],
            item['gene_recall'],
            item['gene_f1'],
            item['disease_precision'],
            item['disease_recall'],
            item['disease_f1']
        ])

print('Zapisano dane do pliku threshold_metrics.csv') 