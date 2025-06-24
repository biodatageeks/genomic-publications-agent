import os
import subprocess
import time
from scripts.utils import load_pmids_from_file, ensure_dirs_exist, DIRS, get_path

# Upewnij się, że wymagane katalogi istnieją
ensure_dirs_exist()

# Wczytaj wszystkie PMIDy
all_pmids = load_pmids_from_file('exp1_fox_pmids.txt')

print(f"Łącznie wczytano {len(all_pmids)} PMIDów.")

# Rozmiar partii
BATCH_SIZE = 100
batches = [list(all_pmids)[i:i + BATCH_SIZE] for i in range(0, len(all_pmids), BATCH_SIZE)]
print(f"Podzielono na {len(batches)} partii po maksymalnie {BATCH_SIZE} PMIDów.")

# Przetwórz każdą partię
for i, batch in enumerate(batches):
    batch_filename = get_path(f"batch_{i+1}_pmids.txt", DIRS['batch_results'])
    output_filename = get_path(f"batch_{i+1}_results.csv", DIRS['batch_results'])
    
    # Zapisz bieżącą partię do pliku
    with open(batch_filename, 'w') as f:
        for pmid in batch:
            f.write(f"{pmid}\n")
    
    print(f"\nPrzetwarzanie partii {i+1}/{len(batches)} ({len(batch)} PMIDów)...")
    
    # Uruchom skrypt dla tej partii z domyślnym modelem (Llama)
    # Nie specyfikujemy modelu, aby użyć domyślnego z konfiguracji
    cmd = f"python scripts/enhanced_generate_coordinate_csv.py --file {batch_filename} --output {output_filename}"
    print(f"Wykonuję: {cmd}")
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"Partia {i+1} zakończona pomyślnie.")
    except subprocess.CalledProcessError as e:
        print(f"Błąd podczas przetwarzania partii {i+1}: {e}")
    
    # Krótka przerwa między zapytaniami do API
    if i < len(batches) - 1:
        print("Czekam 5 sekund przed przetworzeniem następnej partii...")
        time.sleep(5)

print("\nZakończono przetwarzanie wszystkich partii.") 