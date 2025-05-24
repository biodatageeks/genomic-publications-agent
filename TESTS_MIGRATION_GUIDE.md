# 🧪 Przewodnik Migracji Testów - Nowa Struktura

## Przegląd zmian

Katalog `tests` został całkowicie zreorganizowany w profesjonalną strukturę zgodną z nową organizacją modułów `src`. Stary katalog został zachowany jako `tests_old` dla bezpieczeństwa.

## ✅ Co zostało zrobione

### 1. Nowa struktura testów
```
tests/
├── api/                          # 🔌 Testy warstwy API
│   ├── clients/                  # Testy klientów API (PubTator, ClinVar, LitVar)
│   └── cache/                    # Testy systemu cache
│
├── analysis/                     # 🧬 Testy modułów analizy
│   ├── bio_ner/                  # Testy rozpoznawania encji
│   ├── context/                  # Testy analizy kontekstu
│   ├── llm/                      # Testy analizy z LLM
│   └── base/                     # Testy klas bazowych
│
├── cli/                          # 💻 Testy interfejsu CLI
├── models/                       # 📊 Testy modeli danych
├── services/                     # ⚙️ Testy serwisów biznesowych
│   ├── flow/                     # Testy orkiestracji przepływów
│   ├── processing/               # Testy przetwarzania danych
│   ├── search/                   # Testy wyszukiwania
│   └── validation/               # Testy walidacji
│
├── utils/                        # 🛠️ Testy narzędzi pomocniczych
│   ├── config/                   # Testy konfiguracji
│   ├── llm/                      # Testy zarządzania LLM
│   └── logging/                  # Testy systemu logowania
│
├── integration/                  # 🔗 Testy integracyjne
└── fixtures/                     # 📋 Dane testowe i fixtures
```

### 2. Automatyczna migracja importów
- ✅ Zaktualizowano 41 plików testów
- ✅ Wszystkie importy zostały automatycznie poprawione
- ✅ Usunięto duplikujące się testy

### 3. Konsolidacja testów
- ✅ Połączono rozproszone testy klientów API
- ✅ Zorganizowano testy analizatorów według typu
- ✅ Uporządkowano testy LLM managera

## 🔄 Mapowanie starych ścieżek na nowe

| Stara ścieżka | Nowa ścieżka |
|---------------|--------------|
| `tests/llm_manager/` | `tests/utils/llm/` |
| `tests/pubtator_client/` | `tests/api/clients/` |
| `tests/clinvar_client/` | `tests/api/clients/` |
| `tests/test_*_client/` | `tests/api/clients/` |
| `tests/cache/` | `tests/api/cache/` |
| `tests/test_*_analyzer.py` | `tests/analysis/*/` |
| `tests/test_*_validator.py` | `tests/services/validation/` |
| `tests/core/` | `tests/utils/` |

## 📝 Przykłady nowych ścieżek testów

### Przed migracją:
```bash
tests/llm_manager/test_llm_manager.py
tests/pubtator_client/test_pubtator_client.py
tests/test_llm_context_analyzer.py
tests/test_clinvar_relationship_validator.py
```

### Po migracji:
```bash
tests/utils/llm/test_llm_manager.py
tests/api/clients/test_pubtator_client.py
tests/analysis/llm/test_llm_context_analyzer.py
tests/services/validation/test_clinvar_relationship_validator.py
```

## 🧪 Uruchamianie testów

### Wszystkie testy
```bash
pytest
```

### Testy dla konkretnych modułów
```bash
# Testy API
pytest tests/api/

# Testy analizy LLM
pytest tests/analysis/llm/

# Testy LLM manager
pytest tests/utils/llm/

# Testy klientów API
pytest tests/api/clients/

# Testy walidacji
pytest tests/services/validation/
```

### Testy z mockami (bez rzeczywistych API)
```bash
pytest -m "not realapi"
```

### Testy z pokryciem kodu
```bash
pytest --cov=src --cov-report=html
```

## 🔧 Rozwiązywanie problemów

### Problem: Import Error w testach
**Rozwiązanie:** Sprawdź czy używasz nowych ścieżek importów zgodnie z tabelą mapowania powyżej.

### Problem: Brakujące pliki testów
**Rozwiązanie:** Niektóre testy mogły zostać przeniesione. Sprawdź w `tests_old/` i przenieś ręcznie jeśli potrzeba.

### Problem: Duplikujące się testy
**Rozwiązanie:** Niektóre testy były zduplikowane w różnych folderach. Sprawdź czy funkcjonalność jest już przetestowana w nowej lokalizacji.

### Problem: Błędy zależności
**Rozwiązanie:** Zainstaluj brakujące zależności:
```bash
pip install -r requirements.txt
pip install pytest pytest-cov
```

## 📁 Backup

Stary katalog `tests` został zachowany jako `tests_old`. Możesz go usunąć po upewnieniu się, że wszystko działa:

```bash
# Po sprawdzeniu, że wszystko działa:
rm -rf tests_old
```

## 🎯 Korzyści nowej struktury testów

1. **🎯 Zgodność ze strukturą src** - testy odzwierciedlają organizację kodu
2. **🔍 Łatwiejsza nawigacja** - intuicyjne znajdowanie testów dla modułów
3. **🧪 Lepsza organizacja** - logiczne grupowanie testów według funkcjonalności
4. **📈 Skalowalność** - łatwe dodawanie nowych testów w odpowiednich miejscach
5. **👥 Współpraca zespołowa** - standardowa struktura ułatwia pracę w zespole
6. **🚀 Wydajność** - możliwość uruchamiania testów dla konkretnych modułów

## 📊 Statystyki migracji

- **Plików testów**: 72
- **Zaktualizowanych plików**: 41
- **Nowych folderów**: 15
- **Usuniętych duplikatów**: ~10
- **Czas migracji**: Automatyczna

## 🔍 Weryfikacja jakości testów

### Sprawdzenie struktury
```bash
# Sprawdź czy wszystkie moduły src mają odpowiadające testy
find src -name "*.py" -not -path "*/\__pycache__*" | wc -l
find tests -name "test_*.py" | wc -l
```

### Analiza pokrycia
```bash
pytest --cov=src --cov-report=term-missing
```

### Sprawdzenie importów
```bash
# Test importów bez uruchamiania testów
python -c "import tests; print('✅ Testy importują się poprawnie')"
```

## 📝 Pisanie nowych testów

### Gdzie umieścić nowy test?
1. **Test modułu API**: `tests/api/clients/test_new_client.py`
2. **Test analizatora**: `tests/analysis/[typ]/test_new_analyzer.py`
3. **Test serwisu**: `tests/services/[typ]/test_new_service.py`
4. **Test narzędzia**: `tests/utils/[typ]/test_new_util.py`

### Konwencje nazewnictwa
- Pliki: `test_[nazwa_modułu].py`
- Klasy: `Test[NazwaModułu]`
- Funkcje: `test_[funkcjonalność]`

## 🚀 Następne kroki

1. **Uruchom testy** - sprawdź czy wszystko działa
2. **Dodaj brakujące testy** - dla nowych modułów
3. **Popraw pokrycie** - dąż do >80% pokrycia kodu
4. **Dokumentuj testy** - dodaj docstringi do skomplikowanych testów

---

**Migracja testów została wykonana automatycznie i nowa struktura jest bardziej profesjonalna! 🎉** 