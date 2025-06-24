import json
import os
from scripts.utils import load_json_file, save_pmids_to_file, ensure_dirs_exist

# Upewnij się, że wymagane katalogi istnieją
ensure_dirs_exist()

# Geny do wyodrębnienia
target_genes = ['FOXD1', 'FOXQ1', 'FOXK1', 'FOXI1', 'FOXD2', 'FOXA3']

# Wczytaj plik JSON z metadanymi
metadata = load_json_file('data/pmids/fox_pmids_metadata.json')

# Znajdź PMIDy dla wybranych genów
exp1_pmids = []
for pmid, data in metadata.items():
    if data.get('gene') in target_genes:
        exp1_pmids.append(pmid)

print(f'Znaleziono {len(exp1_pmids)} PMIDów dla genów: {", ".join(target_genes)}')

# Zapisz znalezione PMIDy do pliku
save_pmids_to_file(set(exp1_pmids), 'exp1_fox_pmids.txt')

# Pokaż liczbę PMIDów dla każdego genu
counts = {}
for pmid, data in metadata.items():
    if data.get('gene') in target_genes:
        gene = data.get('gene')
        counts[gene] = counts.get(gene, 0) + 1

for gene in target_genes:
    print(f'{gene}: {counts.get(gene, 0)} PMIDów') 