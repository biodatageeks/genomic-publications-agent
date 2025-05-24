# 🧬 Coordinates Literature Analysis

Kompleksowe narzędzie do analizy literatury biomedycznej w celu ekstraktowania i rozumienia relacji między współrzędnymi genomowymi, wariantami, genami i chorobami z wykorzystaniem zaawansowanego NLP i dużych modeli językowych.

## 📋 Przegląd

Ten projekt zapewnia zaawansowane narzędzia do analizy artykułów PubMed w celu ekstraktowania i rozumienia relacji między wariantami genomowymi a innymi encjami biomedycznymi, takimi jak geny, choroby i tkanki. Wykorzystuje przetwarzanie języka naturalnego (NLP) i duże modele językowe (LLM) do identyfikacji, analizy i oceny siły tych relacji.

System został zaprojektowany dla naukowców, bioinformatyków i klinicystów, którzy potrzebują systematycznie analizować duże ilości literatury biomedycznej, aby zrozumieć asocjacje wariant-choroba i relacje genomowe.

## ✨ Kluczowe funkcje

- **🔍 Ekstraktowanie wariantów genomowych**: Wydobywanie współrzędnych genomowych i wariantów z literatury biomedycznej
- **🧬 Analiza relacji**: Analiza relacji między wariantami a encjami biomedycznymi (geny, choroby, tkanki)
- **📊 System oceniania**: Ocena siły relacji w skali 0-10 z wykorzystaniem zaawansowanej analizy LLM
- **📁 Wiele formatów eksportu**: Eksport wyników do formatów CSV i JSON
- **⚡ Inteligentne cache'owanie**: Cache'owanie odpowiedzi API dla szybszego przetwarzania i redukcji kosztów
- **🤖 Wsparcie dla wielu LLM**: Wsparcie dla wielu dostawców LLM (OpenAI, TogetherAI)
- **🔧 Architektura modularna**: Profesjonalna, skalowalna baza kodu z wyraźnym podziałem odpowiedzialności
- **🧪 Kompleksowe testowanie**: Rozbudowany zestaw testów z >80% pokryciem kodu
- **📚 Bogata dokumentacja**: Szczegółowa dokumentacja i przykłady

## 🚀 Szybki start

### Wymagania wstępne

- Python 3.9+
- Klucze API dla:
  - OpenAI (dla modeli GPT) lub TogetherAI (dla modeli open-source)
  - PubTator3 (opcjonalne, dla ulepszonego rozpoznawania encji)
  - ClinVar (opcjonalne, dla walidacji wariantów)

### Instalacja

1. **Sklonuj repozytorium:**
   ```bash
   git clone https://github.com/yourusername/coordinates-lit.git
   cd coordinates-lit
   ```

2. **Utwórz i aktywuj środowisko wirtualne:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Na Windows: venv\Scripts\activate
   ```

3. **Zainstaluj zależności:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Skonfiguruj ustawienia:**
   ```bash
   cp config/development.example.yaml config/development.yaml
   ```
   Następnie edytuj `config/development.yaml`, aby dodać swoje klucze API i ustawienia.

### Podstawowe użycie

**Analizuj artykuły PubMed:**
```bash
python -m src.cli.analyze --pmids 32735606 32719766 --output wyniki.csv
```

**Analizuj z pliku:**
```bash
python -m src.cli.analyze --file pmids.txt --output wyniki.csv --json wyniki.json
```

## 🏗️ Architektura projektu

Projekt stosuje profesjonalną architekturę modularną:

```
coordinates-lit/
├── 📁 src/                     # Kod źródłowy
│   ├── 🔌 api/                 # Warstwa API i komunikacja zewnętrzna
│   │   ├── clients/            # Klienty API (PubTator, ClinVar, LitVar)
│   │   └── cache/              # System cache'owania
│   ├── 🧬 analysis/            # Moduły analizy biomedycznej
│   │   ├── bio_ner/            # Rozpoznawanie encji nazw
│   │   ├── context/            # Analiza kontekstu
│   │   ├── llm/                # Analiza oparta na LLM
│   │   └── base/               # Klasy bazowe analizatorów
│   ├── 💻 cli/                 # Interfejs linii poleceń
│   ├── 📊 models/              # Modele i struktury danych
│   ├── ⚙️ services/            # Serwisy logiki biznesowej
│   │   ├── flow/               # Orkiestracja przepływu danych
│   │   ├── processing/         # Przetwarzanie danych
│   │   ├── search/             # Wyszukiwanie literatury
│   │   └── validation/         # Walidacja danych
│   └── 🛠️ utils/               # Narzędzia i pomocniki
│       ├── config/             # Zarządzanie konfiguracją
│       ├── llm/                # Zarządzanie LLM
│       └── logging/            # System logowania
├── 🧪 tests/                   # Zestaw testów (odzwierciedla strukturę src)
├── 📁 config/                  # Pliki konfiguracyjne
├── 📁 data/                    # Przechowywanie danych
├── 📁 scripts/                 # Skrypty narzędziowe
└── 📁 docs/                    # Dokumentacja
```

## 🔧 Użycie modułów

### Klienty API

**Klient PubTator** - Ekstraktowanie encji biomedycznych:
```python
from src.api.clients.pubtator_client import PubTatorClient

client = PubTatorClient()
publikacja = client.get_publication_by_pmid("32735606")
encje = client.extract_entities(publikacja)
```

**Klient ClinVar** - Walidacja wariantów:
```python
from src.api.clients.clinvar_client import ClinVarClient

client = ClinVarClient()
info_wariantu = client.get_variant_info("NM_000492.3:c.1521_1523delCTT")
```

### Moduły analizy

**Analizator kontekstu LLM** - Analiza relacji z wykorzystaniem LLM:
```python
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer

analizator = LlmContextAnalyzer()
wyniki = analizator.analyze_publications_by_pmids(["32735606", "32719766"])
```

**Bio NER** - Ekstraktowanie wariantów genomowych:
```python
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer

rozpoznawacz = VariantRecognizer()
warianty = rozpoznawacz.extract_variants("Znaleziono mutację c.123A>G w genie BRCA1")
```

### Serwisy

**Orkiestracja przepływów** - Uruchamianie kompletnych pipeline'ów analizy:
```python
from src.services.flow.pubmed_flow import PubMedAnalysisFlow

przepływ = PubMedAnalysisFlow()
wyniki = przepływ.analyze_pmids(["32735606"], output_format="csv")
```

## 🧪 Testowanie

Projekt zawiera kompleksowe testowanie z >80% pokryciem kodu.

### Uruchom wszystkie testy
```bash
pytest
```

### Uruchom konkretne kategorie testów
```bash
# Testy API
pytest tests/api/

# Testy analizy
pytest tests/analysis/

# Testy LLM manager
pytest tests/utils/llm/

# Testy integracyjne
pytest tests/integration/
```

### Testy z pokryciem
```bash
pytest --cov=src --cov-report=html
```

### Markery testów
```bash
# Testy bez rzeczywistych wywołań API (szybkie)
pytest -m "not realapi"

# Tylko testy integracyjne
pytest -m integration

# Wolne testy
pytest -m slow
```

## 📊 Referencja CLI

### Główna komenda analizy
```bash
python -m src.cli.analyze [OPCJE]
```

**Opcje:**
- `--pmids TEXT`: Lista ID PubMed do analizy
- `--file PATH`: Plik zawierający ID PubMed (jeden na linię)
- `--output PATH`: Ścieżka do pliku wyjściowego CSV
- `--json PATH`: Ścieżka do pliku wyjściowego JSON (opcjonalne)
- `--model TEXT`: Model LLM do użycia (domyślny z konfiguracji)
- `--email TEXT`: Email dla zapytań API PubTator
- `--debug`: Włącz tryb debugowania
- `--no-retry`: Wyłącz automatyczne ponowne próby
- `--cache-type [memory|disk]`: Typ cache
- `--log-level [DEBUG|INFO|WARNING|ERROR]`: Poziom logowania

### Przykłady

**Podstawowa analiza:**
```bash
python -m src.cli.analyze --pmids 32735606 32719766 --output wyniki.csv
```

**Analiza wsadowa z wyjściem JSON:**
```bash
python -m src.cli.analyze --file pmids.txt --output wyniki.csv --json wyniki.json
```

**Tryb debugowania z konkretnym modelem:**
```bash
python -m src.cli.analyze --pmids 32735606 --model gpt-4 --debug --log-level DEBUG
```

## 🎯 Przypadki użycia

### 1. **Badania kliniczne**
- Identyfikacja asocjacji wariant-choroba w literaturze
- Walidacja odkryć genomowych przeciwko publikowanym badaniom
- Systematyczne przeglądy literatury dla konkretnych wariantów

### 2. **Analiza bioinformatyczna**
- Ekstraktowanie współrzędnych genomowych z publikacji
- Budowanie grafów wiedzy o relacjach wariantów
- Automatyczna kuratorstwo literatury

### 3. **Odkrywanie leków**
- Znajdowanie wariantów związanych z odpowiedziami na leki
- Identyfikacja celów terapeutycznych
- Repozycjonowanie leków oparte na literaturze

### 4. **Wsparcie diagnostyczne**
- Walidacja patogenności wariantów z literatury
- Znajdowanie podobnych przypadków w publikowanych badaniach
- Interpretacja wariantów oparta na dowodach

## ⚙️ Konfiguracja

### Struktura pliku konfiguracyjnego
```yaml
# config/development.yaml
llm:
  provider: "openai"  # lub "together"
  model: "gpt-3.5-turbo"
  temperature: 0.7

api:
  openai_key: "twój-klucz-openai"
  together_key: "twój-klucz-together"
  pubtator_email: "twój-email@example.com"

cache:
  type: "disk"  # lub "memory"
  ttl: 3600
  max_size: 1000

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Zmienne środowiskowe
```bash
export OPENAI_API_KEY="twój-klucz-openai"
export TOGETHER_API_KEY="twój-klucz-together"
export PUBTATOR_EMAIL="twój-email@example.com"
```

## 🔄 Migracja ze starej struktury

Jeśli aktualizujesz ze starszej wersji, zobacz:
- [Przewodnik migracji](MIGRATION_GUIDE.md) - Dla reorganizacji src
- [Przewodnik migracji testów](TESTS_MIGRATION_GUIDE.md) - Dla reorganizacji testów

## 🤝 Współpraca

1. Forkuj repozytorium
2. Utwórz branch funkcji (`git checkout -b feature/niesamowita-funkcja`)
3. Wprowadź zmiany zgodnie ze strukturą projektu
4. Dodaj testy dla nowej funkcjonalności
5. Upewnij się, że wszystkie testy przechodzą (`pytest`)
6. Zatwierdź zmiany (`git commit -m 'Dodaj niesamowitą funkcję'`)
7. Wypchnij do brancha (`git push origin feature/niesamowita-funkcja`)
8. Otwórz Pull Request

## 📚 Dokumentacja

- [Dokumentacja API](docs/api.md)
- [Przewodnik modułów analizy](docs/analysis.md)
- [Przewodnik konfiguracji](docs/configuration.md)
- [Przewodnik rozwoju](docs/development.md)

## 📄 Licencja

### Kod źródłowy
Ten projekt jest licencjonowany na licencji MIT - szczegóły w pliku [LICENSE](LICENSE).

### Dokumentacja
Dokumentacja jest licencjonowana na Creative Commons Attribution 4.0 International (CC BY 4.0) - szczegóły w pliku [LICENSE-DOCS](LICENSE-DOCS).

## 🙏 Podziękowania

- [PubTator3](https://www.ncbi.nlm.nih.gov/research/pubtator3/) za adnotacje encji biomedycznych
- [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) za bazy danych wariantów
- [LangChain](https://www.langchain.com/) za integrację LLM
- [OpenAI](https://openai.com/) i [Together AI](https://www.together.ai/) za usługi LLM

## 📞 Wsparcie

- **Problemy**: [GitHub Issues](https://github.com/yourusername/coordinates-lit/issues)
- **Dyskusje**: [GitHub Discussions](https://github.com/yourusername/coordinates-lit/discussions)
- **Email**: wojciech.sitek@pw.edu.pl

---

**🌟 Jeśli ten projekt pomaga w Twoich badaniach, rozważ dodanie gwiazdki!** 