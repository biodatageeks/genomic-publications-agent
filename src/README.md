# Struktura projektu Coordinates Literature Analysis

## Przegląd architektury

Projekt został zorganizowany w profesjonalną strukturę modułową, która ułatwia rozwój, testowanie i utrzymanie kodu.

## Struktura folderów

```
src/
├── main.py                 # Główny punkt wejścia aplikacji
├── __init__.py            # Inicjalizacja pakietu
│
├── api/                   # Warstwa API i komunikacji zewnętrznej
│   ├── clients/           # Klienty API (PubTator, ClinVar, LitVar)
│   └── cache/             # System cache'owania zapytań API
│
├── analysis/              # Moduły analizy danych biomedycznych
│   ├── bio_ner/           # Named Entity Recognition dla biologii
│   ├── context/           # Analiza kontekstu i współwystępowania
│   ├── llm/               # Analiza z użyciem modeli językowych
│   ├── base/              # Klasy bazowe dla analizatorów
│   ├── cooccurrence/      # Analiza współwystępowania encji
│   └── inference/         # Wnioskowanie i predykcja
│
├── cli/                   # Interfejs linii poleceń
│   └── analyze.py         # Główny skrypt CLI do analizy
│
├── models/                # Modele danych i struktury
│   ├── entities/          # Modele encji biomedycznych
│   └── data/              # Struktury danych i schemy
│
├── services/              # Serwisy biznesowe
│   ├── analysis/          # Serwisy analizy wysokiego poziomu
│   ├── flow/              # Orkiestracja przepływów danych
│   ├── processing/        # Przetwarzanie danych
│   ├── search/            # Wyszukiwanie i indeksowanie
│   └── validation/        # Walidacja danych i relacji
│
└── utils/                 # Narzędzia pomocnicze
    ├── config/            # Zarządzanie konfiguracją
    ├── llm/               # Zarządzanie modelami LLM
    └── logging/           # System logowania
```

## Opis modułów

### 🔌 API (`api/`)
- **clients/**: Klienty do zewnętrznych API (PubTator3, ClinVar, LitVar)
- **cache/**: System cache'owania odpowiedzi API dla optymalizacji wydajności

### 🧬 Analysis (`analysis/`)
- **bio_ner/**: Rozpoznawanie encji biomedycznych (geny, warianty, choroby)
- **context/**: Analiza kontekstu i relacji między encjami
- **llm/**: Analiza z wykorzystaniem dużych modeli językowych
- **base/**: Abstrakcyjne klasy bazowe dla wszystkich analizatorów
- **inference/**: Wnioskowanie i predykcja na podstawie danych

### 💻 CLI (`cli/`)
- Interfejs linii poleceń do uruchamiania analiz
- Skrypty do przetwarzania wsadowego

### 📊 Models (`models/`)
- **entities/**: Modele danych dla encji biomedycznych
- **data/**: Struktury danych, schemy i typy

### ⚙️ Services (`services/`)
- **analysis/**: Wysokopoziomowe serwisy analizy
- **flow/**: Orkiestracja złożonych przepływów danych
- **processing/**: Przetwarzanie i transformacja danych
- **search/**: Wyszukiwanie publikacji i metadanych
- **validation/**: Walidacja danych i relacji

### 🛠️ Utils (`utils/`)
- **config/**: Zarządzanie konfiguracją aplikacji
- **llm/**: Zarządzanie modelami LLM i providerami
- **logging/**: System logowania i monitorowania

## Zasady organizacji

1. **Separacja odpowiedzialności**: Każdy moduł ma jasno określoną funkcję
2. **Hierarchia zależności**: Moduły wyższego poziomu używają niższych, nie odwrotnie
3. **Testowalność**: Struktura ułatwia pisanie testów jednostkowych i integracyjnych
4. **Rozszerzalność**: Łatwe dodawanie nowych analizatorów i klientów API
5. **Czytelność**: Intuicyjna organizacja ułatwiająca nawigację w kodzie

## Migracja z poprzedniej struktury

Główne zmiany:
- `src/core/` → `src/utils/`
- Rozproszeni klienci API → `src/api/clients/`
- Różne analizatory → `src/analysis/`
- Serwisy biznesowe → `src/services/`
- Modele danych → `src/models/`

## Importy

Przykłady nowych importów:
```python
# Konfiguracja
from src.utils.config.config import Config

# Manager LLM
from src.utils.llm.manager import LlmManager

# Klienty API
from src.api.clients.pubtator_client import PubTatorClient
from src.api.clients.clinvar_client import ClinVarClient

# Analizatory
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer

# Serwisy
from src.services.analysis.benchmark_service import BenchmarkTestService
``` 