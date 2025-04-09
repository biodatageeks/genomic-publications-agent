# Struktura katalogów projektu

Projekt jest zorganizowany w następujący sposób, aby ułatwić zarządzanie plikami i zapewnić spójność:

## Główne katalogi

- `src/` - Kod źródłowy aplikacji
  - `core/` - Podstawowe komponenty
  - `fox_pmid_finder/` - Moduł do znajdowania identyfikatorów PMID
  - `...` - Inne moduły

- `scripts/` - Skrypty pomocnicze
  - `analysis/` - Skrypty do analizy danych i eksperymentów

- `config/` - Pliki konfiguracyjne
  - `config.yaml` - Główny plik konfiguracyjny
  - `development.yaml` - Konfiguracja środowiska deweloperskiego

- `data/` - Katalogi z danymi
  - `pmids/` - Pliki z identyfikatorami PMID
  - `csv/` - Pliki CSV z wynikami
  - `batch_results/` - Wyniki przetwarzania wsadowego
  - `results/` - Katalog z wynikami
    - `experiments/` - Pliki JSON z wynikami eksperymentów
    - `images/` - Obrazy i wykresy generowane podczas analizy

- `tests/` - Testy jednostkowe i integracyjne
  - `core/` - Testy dla podstawowych komponentów
  - `...` - Testy dla innych modułów

- `docs/` - Dokumentacja projektu

## Konwencje nazewnictwa plików

1. **Pliki z danymi PMID**: Powinny być zapisywane w katalogu `data/pmids/`
   - Przykład: `data/pmids/exp1_fox_pmids.txt`

2. **Pliki CSV z wynikami**: Powinny być zapisywane w katalogu `data/csv/`
   - Przykład: `data/csv/threshold_metrics.csv`

3. **Wyniki eksperymentów**: Pliki JSON powinny być zapisywane w katalogu `data/results/experiments/`
   - Przykład: `data/results/experiments/threshold_analysis_results.json`

4. **Obrazy i wykresy**: Powinny być zapisywane w katalogu `data/results/images/`
   - Przykład: `data/results/images/analysis_unified_llama_threshold_8_metrics.png`

5. **Pliki tymczasowe**: Powinny być zapisywane w katalogu `data/temp/`
   - Przykład: `data/temp/temp_data.json`

## Skrypty

Skrypty analizy zostały przeniesione do katalogu `scripts/analysis/`. Przy uruchamianiu skryptów, należy używać odpowiednich ścieżek do plików:

```bash
# Przykład uruchomienia skryptu z odpowiednimi ścieżkami
python scripts/analysis/check_variant_annotations.py data/pmids/input_pmids.txt --output-file data/results/experiments/variant_annotations.json
```

## Automatyczne tworzenie katalogów

Większość skryptów automatycznie tworzy wymagane katalogi, jeśli te nie istnieją. Jednak dla pewności, można ręcznie utworzyć strukturę katalogów:

```bash
mkdir -p data/pmids data/csv data/batch_results data/results/experiments data/results/images data/temp
``` 