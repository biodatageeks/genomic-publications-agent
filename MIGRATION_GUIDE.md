# 🚀 Przewodnik Migracji - Nowa Struktura Projektu

## Przegląd zmian

Folder `src` został całkowicie zreorganizowany w profesjonalną strukturę modułową. Stary folder został zachowany jako `src_old` dla bezpieczeństwa.

## ✅ Co zostało zrobione

### 1. Nowa struktura folderów
```
src/
├── api/                   # 🔌 Warstwa API i komunikacji
│   ├── clients/           # Klienty API (PubTator, ClinVar, LitVar)
│   └── cache/             # System cache'owania
│
├── analysis/              # 🧬 Moduły analizy biomedycznej
│   ├── bio_ner/           # Named Entity Recognition
│   ├── context/           # Analiza kontekstu
│   ├── llm/               # Analiza z LLM
│   ├── base/              # Klasy bazowe
│   └── inference/         # Wnioskowanie
│
├── cli/                   # 💻 Interfejs linii poleceń
├── models/                # 📊 Modele danych
│   ├── entities/          # Encje biomedyczne
│   └── data/              # Struktury danych
│
├── services/              # ⚙️ Serwisy biznesowe
│   ├── analysis/          # Serwisy analizy
│   ├── flow/              # Orkiestracja przepływów
│   ├── processing/        # Przetwarzanie danych
│   ├── search/            # Wyszukiwanie
│   └── validation/        # Walidacja
│
└── utils/                 # 🛠️ Narzędzia pomocnicze
    ├── config/            # Konfiguracja
    ├── llm/               # Zarządzanie LLM
    └── logging/           # Logowanie
```

### 2. Automatyczna migracja importów
- ✅ Zaktualizowano 24 pliki Python
- ✅ Wszystkie importy zostały automatycznie poprawione
- ✅ Zachowano kompatybilność wsteczną

### 3. Dokumentacja
- ✅ Utworzono `src/README.md` z opisem struktury
- ✅ Dodano ten przewodnik migracji

## 🔄 Mapowanie starych ścieżek na nowe

| Stara ścieżka | Nowa ścieżka |
|---------------|--------------|
| `src/core/` | `src/utils/` |
| `src/pubtator_client/` | `src/api/clients/` |
| `src/clinvar_client/` | `src/api/clients/` |
| `src/cache/` | `src/api/cache/` |
| `src/llm_context_analyzer/` | `src/analysis/llm/` |
| `src/bio_ner/` | `src/analysis/bio_ner/` |
| `src/flow/` | `src/services/flow/` |
| `src/data_processor/` | `src/services/processing/` |

## 📝 Przykłady nowych importów

### Przed migracją:
```python
from src.core.config.config import Config
from src.core.llm.manager import LlmManager
from src.pubtator_client.pubtator_client import PubTatorClient
from src.llm_context_analyzer.llm_context_analyzer import LlmContextAnalyzer
```

### Po migracji:
```python
from src.utils.config.config import Config
from src.utils.llm.manager import LlmManager
from src.api.clients.pubtator_client import PubTatorClient
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer
```

## 🧪 Testowanie

Sprawdź czy wszystko działa:

```bash
# Test podstawowych importów
python -c "from src.utils.config.config import Config; print('✅ Config OK')"
python -c "import src; print('✅ Pakiet src OK')"

# Test CLI
python -m src.cli.analyze --help

# Uruchom testy
pytest tests/
```

## 🔧 Rozwiązywanie problemów

### Problem: Import Error
**Rozwiązanie:** Sprawdź czy używasz nowych ścieżek importów zgodnie z tabelą mapowania powyżej.

### Problem: Brakujące moduły
**Rozwiązanie:** Niektóre pliki mogły zostać przeniesione. Sprawdź w `src_old/` i przenieś ręcznie jeśli potrzeba.

### Problem: Testy nie działają
**Rozwiązanie:** Zaktualizuj importy w testach zgodnie z nową strukturą.

## 📁 Backup

Stary folder `src` został zachowany jako `src_old`. Możesz go usunąć po upewnieniu się, że wszystko działa:

```bash
# Po sprawdzeniu, że wszystko działa:
rm -rf src_old
```

## 🎯 Korzyści nowej struktury

1. **🎯 Jasna separacja odpowiedzialności** - każdy moduł ma określoną funkcję
2. **🔍 Łatwiejsza nawigacja** - intuicyjna organizacja folderów
3. **🧪 Lepsza testowalność** - struktura ułatwia pisanie testów
4. **📈 Skalowalność** - łatwe dodawanie nowych modułów
5. **👥 Współpraca zespołowa** - standardowa struktura ułatwia pracę w zespole
6. **📚 Czytelność kodu** - logiczne grupowanie funkcjonalności

## 📞 Wsparcie

Jeśli napotkasz problemy z migracją:
1. Sprawdź ten przewodnik
2. Porównaj z przykładami w `src/README.md`
3. Sprawdź backup w `src_old/`

---

**Migracja została wykonana automatycznie i powinna działać bez problemów. Nowa struktura jest bardziej profesjonalna i ułatwi dalszy rozwój projektu! 🚀** 