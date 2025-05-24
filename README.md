# 🧬 Coordinates Literature Analysis

A comprehensive tool for analyzing biomedical literature to extract and understand relationships between genomic coordinates, variants, genes, and diseases using advanced NLP and Large Language Models.

## 📋 Overview

This project provides sophisticated tools for analyzing PubMed articles to extract and understand relationships between genomic variants and other biomedical entities such as genes, diseases, and tissues. It leverages Natural Language Processing (NLP) and Large Language Models (LLMs) to identify, analyze, and score the strength of these relationships.

The system is designed for researchers, bioinformaticians, and clinicians who need to systematically analyze large volumes of biomedical literature to understand variant-disease associations and genomic relationships.

## ✨ Key Features

- **🔍 Genomic Variant Extraction**: Extract genomic coordinates and variants from biomedical literature
- **🧬 Relationship Analysis**: Analyze relationships between variants and biomedical entities (genes, diseases, tissues)
- **📊 Scoring System**: Score relationship strength from 0-10 using advanced LLM analysis
- **📁 Multiple Export Formats**: Export results to CSV and JSON formats
- **⚡ Intelligent Caching**: Cache API responses for faster processing and reduced costs
- **🤖 Multi-LLM Support**: Support for multiple LLM providers (OpenAI, TogetherAI)
- **🔧 Modular Architecture**: Professional, scalable codebase with clear separation of concerns
- **🧪 Comprehensive Testing**: Extensive test suite with >80% code coverage
- **📚 Rich Documentation**: Detailed documentation and examples

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- API keys for:
  - OpenAI (for GPT models) or TogetherAI (for open-source models)
  - PubTator3 (optional, for enhanced entity recognition)
  - ClinVar (optional, for variant validation)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/coordinates-lit.git
   cd coordinates-lit
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up configuration:**
   ```bash
   cp config/development.example.yaml config/development.yaml
   ```
   Then edit `config/development.yaml` to add your API keys and settings.

### Basic Usage

**Analyze PubMed articles:**
```bash
python -m src.cli.analyze --pmids 32735606 32719766 --output results.csv
```

**Analyze from file:**
```bash
python -m src.cli.analyze --file pmids.txt --output results.csv --json results.json
```

## 🏗️ Project Architecture

The project follows a professional modular architecture:

```
coordinates-lit/
├── 📁 src/                     # Source code
│   ├── 🔌 api/                 # API layer & external communication
│   │   ├── clients/            # API clients (PubTator, ClinVar, LitVar)
│   │   └── cache/              # Caching system
│   ├── 🧬 analysis/            # Biomedical analysis modules
│   │   ├── bio_ner/            # Named Entity Recognition
│   │   ├── context/            # Context analysis
│   │   ├── llm/                # LLM-based analysis
│   │   └── base/               # Base analyzer classes
│   ├── 💻 cli/                 # Command-line interface
│   ├── 📊 models/              # Data models & structures
│   ├── ⚙️ services/            # Business logic services
│   │   ├── flow/               # Data flow orchestration
│   │   ├── processing/         # Data processing
│   │   ├── search/             # Literature search
│   │   └── validation/         # Data validation
│   └── 🛠️ utils/               # Utilities & helpers
│       ├── config/             # Configuration management
│       ├── llm/                # LLM management
│       └── logging/            # Logging system
├── 🧪 tests/                   # Test suite (mirrors src structure)
├── 📁 config/                  # Configuration files
├── 📁 data/                    # Data storage
├── 📁 scripts/                 # Utility scripts
└── 📁 docs/                    # Documentation
```

## 🔧 Module Usage

### API Clients

**PubTator Client** - Extract biomedical entities:
```python
from src.api.clients.pubtator_client import PubTatorClient

client = PubTatorClient()
publication = client.get_publication_by_pmid("32735606")
entities = client.extract_entities(publication)
```

**ClinVar Client** - Validate variants:
```python
from src.api.clients.clinvar_client import ClinVarClient

client = ClinVarClient()
variant_info = client.get_variant_info("NM_000492.3:c.1521_1523delCTT")
```

### Analysis Modules

**LLM Context Analyzer** - Analyze relationships using LLM:
```python
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer

analyzer = LlmContextAnalyzer()
results = analyzer.analyze_publications_by_pmids(["32735606", "32719766"])
```

**Bio NER** - Extract genomic variants:
```python
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer

recognizer = VariantRecognizer()
variants = recognizer.extract_variants("Found mutation c.123A>G in BRCA1")
```

### Services

**Flow Orchestration** - Run complete analysis pipelines:
```python
from src.services.flow.pubmed_flow import PubMedAnalysisFlow

flow = PubMedAnalysisFlow()
results = flow.analyze_pmids(["32735606"], output_format="csv")
```

## 🧪 Testing

The project includes comprehensive testing with >80% code coverage.

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# API tests
pytest tests/api/

# Analysis tests
pytest tests/analysis/

# LLM manager tests
pytest tests/utils/llm/

# Integration tests
pytest tests/integration/
```

### Test with Coverage
```bash
pytest --cov=src --cov-report=html
```

### Test Markers
```bash
# Tests without real API calls (fast)
pytest -m "not realapi"

# Integration tests only
pytest -m integration

# Slow tests
pytest -m slow
```

## 📊 CLI Reference

### Main Analysis Command
```bash
python -m src.cli.analyze [OPTIONS]
```

**Options:**
- `--pmids TEXT`: List of PubMed IDs to analyze
- `--file PATH`: File containing PubMed IDs (one per line)
- `--output PATH`: Output CSV file path
- `--json PATH`: Output JSON file path (optional)
- `--model TEXT`: LLM model to use (default from config)
- `--email TEXT`: Email for PubTator API requests
- `--debug`: Enable debug mode
- `--no-retry`: Disable automatic retries
- `--cache-type [memory|disk]`: Cache type
- `--log-level [DEBUG|INFO|WARNING|ERROR]`: Logging level

### Examples

**Basic analysis:**
```bash
python -m src.cli.analyze --pmids 32735606 32719766 --output results.csv
```

**Batch analysis with JSON output:**
```bash
python -m src.cli.analyze --file pmids.txt --output results.csv --json results.json
```

**Debug mode with specific model:**
```bash
python -m src.cli.analyze --pmids 32735606 --model gpt-4 --debug --log-level DEBUG
```

## 🎯 Use Cases

### 1. **Clinical Research**
- Identify variant-disease associations in literature
- Validate genomic findings against published research
- Systematic literature reviews for specific variants

### 2. **Bioinformatics Analysis**
- Extract genomic coordinates from publications
- Build knowledge graphs of variant relationships
- Automated literature curation

### 3. **Drug Discovery**
- Find variants associated with drug responses
- Identify therapeutic targets
- Literature-based drug repurposing

### 4. **Diagnostic Support**
- Validate variant pathogenicity from literature
- Find similar cases in published research
- Evidence-based variant interpretation

## ⚙️ Configuration

### Config File Structure
```yaml
# config/development.yaml
llm:
  provider: "openai"  # or "together"
  model: "gpt-3.5-turbo"
  temperature: 0.7

api:
  openai_key: "your-openai-key"
  together_key: "your-together-key"
  pubtator_email: "your-email@example.com"

cache:
  type: "disk"  # or "memory"
  ttl: 3600
  max_size: 1000

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Environment Variables
```bash
export OPENAI_API_KEY="your-openai-key"
export TOGETHER_API_KEY="your-together-key"
export PUBTATOR_EMAIL="your-email@example.com"
```

## 🔄 Migration from Old Structure

If you're upgrading from an older version, see:
- [Migration Guide](MIGRATION_GUIDE.md) - For src reorganization
- [Tests Migration Guide](TESTS_MIGRATION_GUIDE.md) - For tests reorganization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the project structure
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Analysis Modules Guide](docs/analysis.md)
- [Configuration Guide](docs/configuration.md)
- [Development Guide](docs/development.md)

## 📄 License

### Source Code
This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0) - see the [LICENSE](LICENSE) file for details.

### Documentation
Documentation is licensed under Creative Commons Attribution 4.0 International (CC BY 4.0) - see the [LICENSE-DOCS](LICENSE-DOCS) file for details.

## 🙏 Acknowledgments

- [PubTator3](https://www.ncbi.nlm.nih.gov/research/pubtator3/) for biomedical entity annotations
- [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/) for variant databases
- [LangChain](https://www.langchain.com/) for LLM integration
- [OpenAI](https://openai.com/) and [Together AI](https://www.together.ai/) for LLM services

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/coordinates-lit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/coordinates-lit/discussions)
- **Email**: wojciech.sitek@pw.edu.pl

---

**🌟 If this project helps your research, please consider giving it a star!** 