# Coordinates Literature Analysis

A tool for analyzing biomedical literature to extract relationships between genomic coordinates, variants, genes, and diseases.

## Overview

This project provides tools for analyzing PubMed articles to extract and understand relationships between genomic variants and other biomedical entities such as genes, diseases, and tissues. It uses Natural Language Processing (NLP) and Large Language Models (LLMs) to identify and score the strength of these relationships.

## Features

- Extract genomic coordinates and variants from biomedical literature
- Analyze relationships between variants and other biomedical entities
- Score relationship strength from 0-10
- Export results to CSV and JSON formats
- Cache API responses for faster processing
- Support for multiple LLM providers (OpenAI, TogetherAI)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/coordinates-lit.git
   cd coordinates-lit
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up configuration:
   ```
   cp config/development.example.yaml config/development.yaml
   ```
   Then edit `config/development.yaml` to add your API keys and other settings.

## Usage

### Analyzing PubMed Articles

You can analyze PubMed articles using the CLI tool:

```bash
python -m src.cli.analyze --pmids 32735606 32719766 --output results.csv
```

Or use a file containing PubMed IDs:

```bash
python -m src.cli.analyze --file pmids.txt --output results.csv --json results.json
```

### CLI Options

- `--pmids`: List of PubMed IDs to analyze
- `--file`: File containing PubMed IDs (one per line)
- `--output`: Path to output CSV file
- `--json`: Path to output JSON file (optional)
- `--model`: LLM model to use
- `--email`: Email for PubTator API
- `--debug`: Enable debug mode
- `--no-retry`: Disable automatic retries
- `--cache-type`: Cache type ('memory' or 'disk')
- `--log-level`: Logging level

## Project Structure

```
coordinates-lit/
├── config/                  # Configuration files
├── data/                    # Data storage
│   ├── cache/               # Cache storage
│   ├── raw/                 # Raw data
│   └── processed/           # Processed data
├── logs/                    # Log files
├── src/                     # Source code
│   ├── analysis/            # Analysis modules
│   │   ├── base/            # Base analyzer classes
│   │   └── llm/             # LLM-based analyzers
│   ├── cli/                 # Command-line interfaces
│   ├── core/                # Core functionality
│   │   ├── config/          # Configuration management
│   │   └── llm/             # LLM management
│   └── data/                # Data handling
│       ├── cache/           # Caching mechanisms
│       └── clients/         # API clients
├── scripts/                 # Utility scripts
└── tests/                   # Unit tests
```

## Running Tests

Run the tests using pytest:

```bash
pytest
```

For code coverage:

```bash
pytest --cov=src
```

## Licencje

### Kod źródłowy
Kod źródłowy projektu jest objęty licencją MIT. Oznacza to, że możesz używać, modyfikować i dystrybuować kod w ramach własnych projektów, również komercyjnych, pod warunkiem zachowania informacji o prawach autorskich. Szczegóły znajdują się w pliku [LICENSE](LICENSE).

### Dokumentacja
Dokumentacja projektu jest objęta licencją Creative Commons Attribution 4.0 International (CC BY 4.0). Możesz swobodnie udostępniać i adaptować dokumentację, także do celów komercyjnych, pod warunkiem zamieszczenia odpowiedniej informacji o autorach i licencji. Szczegóły znajdują się w pliku [LICENSE-DOCS](LICENSE-DOCS).

## Acknowledgments

- [PubTator](https://www.ncbi.nlm.nih.gov/research/pubtator/) for biomedical entity annotations
- [LangChain](https://www.langchain.com/) for LLM integration 