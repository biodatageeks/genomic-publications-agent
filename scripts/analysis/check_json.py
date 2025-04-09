import json
import csv

# Wczytaj dane z CSV
csv_gene_counts = {}
with open('data/results/fox_gene_pmids_count.csv', 'r') as csv_file:
    reader = csv.DictReader(csv_file)
    for row in reader:
        csv_gene_counts[row['Gen']] = int(row['Liczba_PMIDs'])

# Wczytaj dane z JSON
with open('data/pmids/fox_pmids_metadata.json', 'r') as json_file:
    data = json.load(json_file)
    print(f'Liczba PMIDów w pliku JSON: {len(data)}')
    
    # Przykładowe dane
    print('Przykładowe geny dla pierwszych 5 PMIDów:')
    for i, (pmid, metadata) in enumerate(list(data.items())[:5]):
        print(f'{pmid}: {metadata["gene"]}')

    # Oblicz liczbę PMIDów dla każdego genu
    json_gene_counts = {}
    for pmid, metadata in data.items():
        gene = metadata["gene"]
        if gene in json_gene_counts:
            json_gene_counts[gene] += 1
        else:
            json_gene_counts[gene] = 1
    
    # Porównaj liczby z CSV i JSON
    print("\nPorównanie liczby PMIDów z CSV i z JSON:")
    print("Gen\tCSV\tJSON\tRóżnica")
    for gene in sorted(csv_gene_counts.keys()):
        csv_count = csv_gene_counts.get(gene, 0)
        json_count = json_gene_counts.get(gene, 0)
        diff = json_count - csv_count
        print(f"{gene}\t{csv_count}\t{json_count}\t{diff}") 