# Testy dla klasy LlmManager

Ten katalog zawiera kompleksowe testy dla klasy `LlmManager`, odpowiedzialnej za tworzenie i zarządzanie instancjami modeli językowych (LLM) w projekcie. Klasa `LlmManager` obsługuje różne dostawców API, takich jak OpenAI i TogetherAI.

## Struktura testów

Testy są podzielone na trzy główne grupy:

1. **test_llm_manager.py** - Podstawowe testy jednostkowe dla klasy `LlmManager`
   - Testy inicjalizacji
   - Testy zarządzania kluczami API
   - Testy parametrów konstruktora
   - Testy funkcjonalne
   - Testy z rzeczywistym API (opcjonalne)
   - Testy przypadków brzegowych i obsługi błędów
   - Dodatkowe testy

2. **test_benchmark_integration.py** - Testy integracji z `BenchmarkTestService`
   - Testy inicjalizacji serwisu z `LlmManager`
   - Testy przygotowania tekstów z PubMed IDs
   - Testy wykonywania testów porównawczych
   - Testy wyszukiwania współrzędnych

3. **test_llm_context_analyzer_integration.py** - Testy integracji z `LlmContextAnalyzer`
   - Testy inicjalizacji analizatora
   - Testy analizy publikacji
   - Testy grupowania adnotacji
   - Testy czyszczenia odpowiedzi JSON
   - Testy funkcjonalności cache

## Uruchamianie testów

### Testy z mockami (bez rzeczywistych zapytań API)

Aby uruchomić testy, które używają mocków zamiast rzeczywistych zapytań API:

```bash
pytest tests/llm_manager/ -m "not realapi"
```

### Testy z rzeczywistymi zapytaniami API

Aby uruchomić wszystkie testy, w tym te, które wykonują rzeczywiste zapytania API:

```bash
pytest tests/llm_manager/
```

**Uwaga:** Testy z rzeczywistymi zapytaniami API wymagają skonfigurowania kluczy API w pliku konfiguracyjnym lub zmiennych środowiskowych.

## Struktura kodu

Klasa `LlmManager` jest używana w następujących modułach:

1. **BenchmarkTestService** (`src/inference/BenchmarkTestService.py`)
   - Zarządza testami porównawczymi wnioskowania współrzędnych
   - Używa `LlmManager` do tworzenia instancji modeli LLM dla `CoordinatesInference`

2. **LlmContextAnalyzer** (`src/llm_context_analyzer/llm_context_analyzer.py`)
   - Analizuje kontekst biomedyczny i relacje w publikacjach naukowych
   - Używa `LlmManager` do tworzenia instancji modeli LLM dla analizy

3. **Notatniki Jupyter** (`notebooks/Flow.ipynb`)
   - Różne eksperymenty z wykorzystaniem modeli LLM
   - Bezpośrednie wykorzystanie `LlmManager` do interakcji z API

## Obsługiwane funkcje

Klasa `LlmManager` obsługuje:

1. Automatyczne pobieranie kluczy API z:
   - Pliku konfiguracyjnego
   - Zmiennych środowiskowych
   - Wprowadzania przez użytkownika w trybie interaktywnym

2. Przełączanie między różnymi dostawcami API:
   - 'gpt' - dla modeli OpenAI (np. GPT-4, GPT-3.5)
   - 'together' - dla modeli hostowanych przez TogetherAI (np. Llama, Claude)

3. Konfigurację parametrów dla modeli, takich jak:
   - Temperatura
   - Maksymalna liczba tokenów
   - Limity czasu i ponowne próby 