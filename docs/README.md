# Coordinates Literature Analysis Tool

Narzędzie do analizy literatury biomedycznej z wykorzystaniem współrzędnych kontekstowych.

## Opis

Narzędzie służy do:
- Ekstrakcji informacji z publikacji biomedycznych
- Analizy kontekstu występowania genów, chorób i innych encji
- Wykrywania relacji między encjami
- Wizualizacji wyników analizy

## Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/yourusername/coordinates-lit.git
cd coordinates-lit

# Instalacja zależności
pip install -e .
```

## Użycie

### Analiza pojedynczej publikacji

```python
from src.clients.pubtator.client import PubTatorClient
from src.analysis.context.analyzer import ContextAnalyzer

# Inicjalizacja klienta
client = PubTatorClient()

# Pobranie danych publikacji
publication = client.get_publication("12345678")

# Analiza kontekstu
analyzer = ContextAnalyzer()
results = analyzer.analyze_publication("12345678")
```

### Analiza zbioru publikacji

```python
from src.data.processors.base import BaseProcessor

# Implementacja własnego procesora
class CustomProcessor(BaseProcessor):
    def process(self):
        data = self.load_input()
        # Przetwarzanie danych
        self.save_output(processed_data)

# Użycie procesora
processor = CustomProcessor("input.json", "output.json")
processor.process()
```

## Struktura projektu

```
coordinates-lit/
├── src/                    # Kod źródłowy
├── tests/                  # Testy
├── docs/                   # Dokumentacja
├── data/                   # Dane
└── config/                 # Konfiguracja
```

## Dokumentacja API

Szczegółowa dokumentacja API znajduje się w katalogu `docs/api/`.

## Licencja

MIT License 