# 🧪 Testy dla projektu Coordinates-Lit

Ten katalog zawiera testy dla różnych komponentów projektu, mające na celu weryfikację poprawnego działania kodu i wykrywanie regresji.

## 📁 Nowa struktura testów

Struktura testów została zorganizowana zgodnie z nową strukturą modułów `src`:

```
tests/
├── conftest.py                    # Globalna konfiguracja pytest i fixtures
├── test_main.py                   # Testy głównego modułu aplikacji
├── test_main_module.py           # Dodatkowe testy modułu głównego
├── __init__.py                   # Inicjalizacja pakietu testów
├── README.md                     # Ta dokumentacja
│
├── api/                          # 🔌 Testy warstwy API
│   ├── clients/                  # Testy klientów API
│   │   ├── test_pubtator_client.py
│   │   ├── test_clinvar_client.py
│   │   └── test_litvar_client.py
│   └── cache/                    # Testy systemu cache
│       ├── test_api_cache.py
│       ├── test_memory_cache.py
│       └── test_disk_cache.py
│
├── analysis/                     # 🧬 Testy modułów analizy
│   ├── bio_ner/                  # Testy rozpoznawania encji
│   │   └── test_variant_recognizer.py
│   ├── context/                  # Testy analizy kontekstu
│   │   └── test_cooccurrence_context_analyzer.py
│   ├── llm/                      # Testy analizy z LLM
│   │   ├── test_llm_context_analyzer.py
│   │   ├── test_enhanced_llm_context_analyzer.py
│   │   └── test_unified_llm_context_analyzer.py
│   └── base/                     # Testy klas bazowych
│
├── cli/                          # 💻 Testy interfejsu CLI
│
├── models/                       # 📊 Testy modeli danych
│
├── services/                     # ⚙️ Testy serwisów biznesowych
│   ├── flow/                     # Testy orkiestracji przepływów
│   ├── processing/               # Testy przetwarzania danych
│   ├── search/                   # Testy wyszukiwania
│   │   └── test_fox_gene_pmid_finder.py
│   └── validation/               # Testy walidacji
│       ├── test_clinvar_relationship_validator.py
│       └── test_clinvar_validator_utils.py
│
├── utils/                        # 🛠️ Testy narzędzi pomocniczych
│   ├── config/                   # Testy konfiguracji
│   │   ├── test_config.py
│   │   ├── test_settings.py
│   │   └── test_validation.py
│   ├── llm/                      # Testy zarządzania LLM
│   │   ├── test_llm_manager.py
│   │   ├── test_benchmark_integration.py
│   │   └── test_llm_context_analyzer_integration.py
│   └── logging/                  # Testy systemu logowania
│
├── integration/                  # 🔗 Testy integracyjne
└── fixtures/                     # 📋 Dane testowe i fixtures
```

## 🎯 Typy testów

### 1. Testy jednostkowe (Unit Tests)
- Testują pojedyncze funkcje i klasy w izolacji
- Używają mocków do zastąpienia zależności
- Szybkie wykonanie, brak wywołań zewnętrznych API

### 2. Testy integracyjne (Integration Tests)
- Testują współpracę między modułami
- Mogą używać rzeczywistych API (z odpowiednimi kluczami)
- Wolniejsze wykonanie, ale bardziej realistyczne

### 3. Testy funkcjonalne (Functional Tests)
- Testują kompletne scenariusze użycia
- End-to-end testy głównych funkcjonalności

## 🚀 Uruchamianie testów

### Wszystkie testy
```bash
pytest
```

### Testy dla konkretnego modułu
```bash
# Testy API
pytest tests/api/

# Testy analizy
pytest tests/analysis/

# Testy LLM manager
pytest tests/utils/llm/

# Testy klientów API
pytest tests/api/clients/
```

### Testy z mockami (bez rzeczywistych API)
```bash
pytest -m "not realapi"
```

### Testy z rzeczywistymi API
```bash
pytest -m "realapi"
```

### Testy z pokryciem kodu
```bash
pytest --cov=src --cov-report=html
```

### Testy w trybie verbose
```bash
pytest -v
```

## 📊 Markery testów

- `realapi` - testy wymagające rzeczywistych kluczy API
- `integration` - testy integracyjne
- `slow` - testy długotrwałe
- `advanced_mocking` - testy z zaawansowanymi mockami

## 🔧 Konfiguracja

### pytest.ini
Główna konfiguracja pytest znajduje się w pliku `pytest.ini` w katalogu głównym projektu.

### conftest.py
Globalne fixtures i konfiguracja dla wszystkich testów:
- `sample_text` - przykładowy tekst naukowy
- `sample_variants` - lista wariantów genomowych
- `mock_llm` - mock modelu LLM
- `temp_files` - tymczasowe pliki do testów

## 📝 Pisanie nowych testów

### Konwencje nazewnictwa
- Pliki testów: `test_*.py`
- Klasy testów: `Test*`
- Funkcje testów: `test_*`

### Przykład testu jednostkowego
```python
import pytest
from unittest.mock import Mock, patch
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer

def test_variant_recognition():
    """Test rozpoznawania wariantów genomowych."""
    recognizer = VariantRecognizer()
    text = "Found mutation c.123A>G in BRCA1 gene"
    
    variants = recognizer.extract_variants(text)
    
    assert len(variants) == 1
    assert variants[0] == "c.123A>G"
```

### Przykład testu z mockami
```python
@patch('src.api.clients.pubtator_client.requests.get')
def test_pubtator_client_get_publication(mock_get):
    """Test klienta PubTator z mockiem."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"pmid": "12345"}
    mock_get.return_value = mock_response
    
    client = PubTatorClient()
    result = client.get_publication("12345")
    
    assert result["pmid"] == "12345"
    mock_get.assert_called_once()
```

## 🔍 Weryfikacja jakości testów

### Pokrycie kodu
Sprawdź pokrycie kodu testami:
```bash
pytest --cov=src --cov-report=term-missing
```

### Analiza testów
- Każdy test powinien mieć jasny cel
- Testy powinny być niezależne od siebie
- Używaj opisowych nazw testów
- Dodawaj docstringi do skomplikowanych testów

## 🐛 Debugowanie testów

### Uruchomienie pojedynczego testu
```bash
pytest tests/api/clients/test_pubtator_client.py::test_get_publication
```

### Tryb debugowania
```bash
pytest --pdb
```

### Wyświetlanie print statements
```bash
pytest -s
```

## 📈 Metryki testów

Projekt dąży do:
- **Pokrycie kodu**: > 80%
- **Czas wykonania**: < 30 sekund dla testów jednostkowych
- **Stabilność**: 0% flaky tests

## 🔄 Migracja z poprzedniej struktury

Główne zmiany w strukturze testów:
- `tests/llm_manager/` → `tests/utils/llm/`
- `tests/pubtator_client/` → `tests/api/clients/`
- `tests/test_*_analyzer.py` → `tests/analysis/*/`
- Konsolidacja duplikujących się testów
- Aktualizacja importów zgodnie z nową strukturą `src`

---

**Nowa struktura testów jest bardziej zorganizowana i ułatwia utrzymanie oraz rozwój testów! 🎉** 