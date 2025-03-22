# Testy dla projektu Coordinates-Lit

Ten katalog zawiera testy dla różnych komponentów projektu, mające na celu weryfikację poprawnego działania kodu i wykrywanie regresji.

## Organizacja testów

Testy są podzielone na kategorie odpowiadające modułom projektu:

- **clinvar_client/** - Testy dla klienta ClinVar
- **pubtator_client/** - Testy dla klienta PubTator
- **llm_manager/** - Testy dla menedżera modeli językowych
- *[pozostałe pliki]* - Testy dla innych komponentów projektu

## Uruchamianie testów

Aby uruchomić wszystkie testy:

```bash
pytest
```

Aby uruchomić testy dla określonego modułu:

```bash
pytest tests/[nazwa_modułu]/
```

Na przykład, aby uruchomić testy dla LlmManager:

```bash
pytest tests/llm_manager/
```

### Testy z mockami vs. testy z rzeczywistymi API

Niektóre testy są zaprojektowane tak, aby działały z mockami zamiast wykonywać rzeczywiste zapytania API. Jest to przydatne do szybkich testów i CI/CD. Inne testy mogą używać rzeczywistych API, aby sprawdzić pełną integrację.

Aby uruchomić tylko testy z mockami dla LlmManager:

```bash
pytest tests/llm_manager/ -m "not realapi"
```

Aby uruchomić testy używające rzeczywistych API dla LlmManager:

```bash
pytest tests/llm_manager/ --run-realapi
```

## Testy LlmManager

Testy dla `LlmManager` są szczególnie ważne, ponieważ ta klasa jest używana w wielu kluczowych komponentach projektu, w tym:

- Inferencja współrzędnych genetycznych
- Analiza kontekstu z użyciem modeli językowych
- Eksperymentalne notatniki

Testy `LlmManager` sprawdzają:
- Poprawne tworzenie i konfigurację modeli LLM
- Obsługę kluczy API z różnych źródeł
- Integrację z innymi komponentami (BenchmarkTestService, LlmContextAnalyzer)
- Obsługę przypadków brzegowych i błędów

Więcej szczegółów na temat testów LlmManager znajduje się w [dokumentacji testów LlmManager](llm_manager/README.md).

## Wymagania dla testów

Testy wymagają zainstalowanego frameworka pytest. Możesz zainstalować wszystkie wymagane zależności za pomocą:

```bash
pip install -r requirements-dev.txt
```

Niektóre testy mogą wymagać dodatkowej konfiguracji, takiej jak klucze API, które powinny być dostarczone w pliku konfiguracyjnym lub jako zmienne środowiskowe. 