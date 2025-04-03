import json
import os

# Geny do wyodrębnienia
target_genes = ['FOXD1', 'FOXQ1', 'FOXK1', 'FOXI1', 'FOXD2', 'FOXA3']

# Wczytaj plik JSON z metadanymi
with open('data/pmids/fox_pmids_metadata.json', 'r') as f:
    metadata = json.load(f)

# Znajdź PMIDy dla wybranych genów
exp1_pmids = []
for pmid, data in metadata.items():
    if data.get('gene') in target_genes:
        exp1_pmids.append(pmid)

print(f'Znaleziono {len(exp1_pmids)} PMIDów dla genów: {", ".join(target_genes)}')

# Zapisz znalezione PMIDy do pliku
with open('exp1_fox_pmids.txt', 'w') as f:
    for pmid in exp1_pmids:
        f.write(f'{pmid}\n')

print(f'Zapisano PMIDy do pliku exp1_fox_pmids.txt')

# Pokaż liczbę PMIDów dla każdego genu
counts = {}
for pmid, data in metadata.items():
    if data.get('gene') in target_genes:
        gene = data.get('gene')
        counts[gene] = counts.get(gene, 0) + 1

for gene in target_genes:
    print(f'{gene}: {counts.get(gene, 0)} PMIDów') 