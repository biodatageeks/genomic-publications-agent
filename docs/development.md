# 🛠️ Development Guide

This document provides comprehensive guidance for developers working on the Coordinates Literature Analysis project, including architecture patterns, coding standards, testing procedures, and contribution guidelines.

## 🏗️ Project Architecture

### High-Level Architecture

The project follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│                CLI Layer                │  # User interface
├─────────────────────────────────────────┤
│              Services Layer             │  # Business logic orchestration
├─────────────────────────────────────────┤
│              Analysis Layer             │  # Core analysis algorithms
├─────────────────────────────────────────┤
│                API Layer                │  # External service integration
├─────────────────────────────────────────┤
│              Models Layer               │  # Data structures
├─────────────────────────────────────────┤
│               Utils Layer               │  # Cross-cutting concerns
└─────────────────────────────────────────┘
```

### Directory Structure

```
src/
├── api/                      # 🔌 External API integration
│   ├── clients/              # API client implementations
│   │   ├── base_client.py    # Abstract base client
│   │   ├── pubtator_client.py
│   │   ├── clinvar_client.py
│   │   └── litvar_client.py
│   └── cache/                # Caching layer
│       ├── cache_manager.py  # Cache orchestration
│       ├── memory_cache.py   # In-memory cache
│       └── disk_cache.py     # Persistent cache
│
├── analysis/                 # 🧬 Core analysis modules
│   ├── base/                 # Base classes and interfaces
│   │   ├── base_analyzer.py  # Abstract analyzer
│   │   └── result_types.py   # Common result types
│   ├── bio_ner/              # Named Entity Recognition
│   │   ├── variant_recognizer.py
│   │   ├── gene_recognizer.py
│   │   └── disease_recognizer.py
│   ├── context/              # Context analysis
│   │   ├── context_analyzer.py
│   │   └── relationship_scorer.py
│   └── llm/                  # LLM-based analysis
│       ├── llm_context_analyzer.py
│       ├── prompt_templates.py
│       └── result_parser.py
│
├── cli/                      # 💻 Command-line interface
│   ├── analyze.py            # Main analysis command
│   ├── commands/             # CLI command implementations
│   └── utils/                # CLI utilities
│
├── models/                   # 📊 Data models
│   ├── publication.py        # Publication data structures
│   ├── entities.py           # Biomedical entities
│   ├── relationships.py      # Relationship models
│   └── results.py            # Analysis result models
│
├── services/                 # ⚙️ Business logic services
│   ├── flow/                 # Workflow orchestration
│   │   ├── pubmed_flow.py    # PubMed analysis pipeline
│   │   └── batch_processor.py
│   ├── processing/           # Data processing
│   │   ├── entity_processor.py
│   │   └── result_aggregator.py
│   ├── search/               # Literature search
│   │   └── pubmed_search.py
│   └── validation/           # Data validation
│       ├── pmid_validator.py
│       └── result_validator.py
│
└── utils/                    # 🛠️ Utilities and helpers
    ├── config/               # Configuration management
    │   ├── config_manager.py
    │   └── settings.py
    ├── llm/                  # LLM utilities
    │   ├── llm_manager.py
    │   └── prompt_utils.py
    └── logging/              # Logging utilities
        ├── logger.py
        └── formatters.py
```

## 🎯 Design Patterns

### 1. Client-Server Pattern (API Layer)

All external API interactions follow a consistent client pattern:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class BaseClient(ABC):
    """Abstract base class for all API clients."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    @abstractmethod
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request to API endpoint."""
        pass
    
    @abstractmethod
    def post(self, endpoint: str, data: Dict = None) -> Dict:
        """Make POST request to API endpoint."""
        pass
    
    def _handle_response(self, response: requests.Response) -> Dict:
        """Common response handling logic."""
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        response.raise_for_status()
        return response.json()

class PubTatorClient(BaseClient):
    """PubTator3 API client implementation."""
    
    def __init__(self, email: str):
        super().__init__("https://www.ncbi.nlm.nih.gov/research/pubtator3-api")
        self.email = email
    
    def get_publication_by_pmid(self, pmid: str) -> Dict:
        """Get publication data for given PMID."""
        endpoint = f"/publications/{pmid}"
        params = {"email": self.email}
        return self.get(endpoint, params)
```

### 2. Strategy Pattern (Analysis Layer)

Different analysis strategies can be plugged in dynamically:

```python
from abc import ABC, abstractmethod

class AnalysisStrategy(ABC):
    """Abstract base class for analysis strategies."""
    
    @abstractmethod
    def analyze(self, text: str, entities: List[str]) -> AnalysisResult:
        """Perform analysis on given text and entities."""
        pass

class NERAnalysisStrategy(AnalysisStrategy):
    """Named Entity Recognition strategy."""
    
    def analyze(self, text: str, entities: List[str]) -> AnalysisResult:
        # Implement NER-based analysis
        pass

class LLMAnalysisStrategy(AnalysisStrategy):
    """LLM-based analysis strategy."""
    
    def analyze(self, text: str, entities: List[str]) -> AnalysisResult:
        # Implement LLM-based analysis
        pass

class ContextAnalyzer:
    """Context analyzer using strategy pattern."""
    
    def __init__(self, strategy: AnalysisStrategy):
        self.strategy = strategy
    
    def set_strategy(self, strategy: AnalysisStrategy):
        """Change analysis strategy at runtime."""
        self.strategy = strategy
    
    def analyze(self, text: str, entities: List[str]) -> AnalysisResult:
        return self.strategy.analyze(text, entities)
```

### 3. Observer Pattern (Progress Tracking)

For long-running operations with progress updates:

```python
from abc import ABC, abstractmethod
from typing import List

class ProgressObserver(ABC):
    """Abstract observer for progress updates."""
    
    @abstractmethod
    def on_progress(self, current: int, total: int, message: str = ""):
        """Handle progress update."""
        pass

class ConsoleProgressObserver(ProgressObserver):
    """Console-based progress observer."""
    
    def on_progress(self, current: int, total: int, message: str = ""):
        percentage = (current / total) * 100
        print(f"Progress: {current}/{total} ({percentage:.1f}%) - {message}")

class BatchProcessor:
    """Batch processor with observer pattern."""
    
    def __init__(self):
        self.observers: List[ProgressObserver] = []
    
    def add_observer(self, observer: ProgressObserver):
        self.observers.append(observer)
    
    def _notify_progress(self, current: int, total: int, message: str = ""):
        for observer in self.observers:
            observer.on_progress(current, total, message)
    
    def process_batch(self, items: List[str]):
        total = len(items)
        for i, item in enumerate(items):
            # Process item
            self.process_item(item)
            self._notify_progress(i + 1, total, f"Processed {item}")
```

### 4. Factory Pattern (Model Creation)

For creating different types of entities and results:

```python
from enum import Enum
from typing import Dict, Type

class EntityType(Enum):
    GENE = "gene"
    DISEASE = "disease"
    VARIANT = "variant"
    CHEMICAL = "chemical"

class EntityFactory:
    """Factory for creating biomedical entities."""
    
    _entity_classes: Dict[EntityType, Type] = {
        EntityType.GENE: Gene,
        EntityType.DISEASE: Disease,
        EntityType.VARIANT: Variant,
        EntityType.CHEMICAL: Chemical,
    }
    
    @classmethod
    def create_entity(cls, entity_type: EntityType, **kwargs) -> Entity:
        """Create entity of specified type."""
        entity_class = cls._entity_classes.get(entity_type)
        if not entity_class:
            raise ValueError(f"Unknown entity type: {entity_type}")
        return entity_class(**kwargs)
    
    @classmethod
    def register_entity_type(cls, entity_type: EntityType, entity_class: Type):
        """Register new entity type."""
        cls._entity_classes[entity_type] = entity_class
```

## 📝 Coding Standards

### Python Style Guide

We follow PEP 8 with some project-specific additions:

#### 1. Import Organization

```python
# Standard library imports
import os
import sys
from typing import Dict, List, Optional

# Third-party imports
import requests
import pandas as pd
from pydantic import BaseModel

# Local imports
from src.models.entities import Gene, Disease
from src.utils.config import ConfigManager
```

#### 2. Type Hints

Use type hints for all function signatures:

```python
from typing import Dict, List, Optional, Union

def analyze_publication(
    pmid: str, 
    entities: List[str], 
    config: Optional[Dict] = None
) -> Dict[str, Union[str, float]]:
    """Analyze publication for entity relationships.
    
    Args:
        pmid: PubMed ID of the publication
        entities: List of entities to analyze
        config: Optional configuration overrides
        
    Returns:
        Dictionary containing analysis results
        
    Raises:
        ValueError: If PMID is invalid
        APIError: If API request fails
    """
    pass
```

#### 3. Docstring Format

Use Google-style docstrings:

```python
def extract_variants(self, text: str, confidence_threshold: float = 0.7) -> List[Variant]:
    """Extract genomic variants from biomedical text.
    
    This method uses pattern matching and NLP techniques to identify
    genomic variants in HGVS notation and other formats.
    
    Args:
        text: Input text containing potential variants
        confidence_threshold: Minimum confidence score for extraction
        
    Returns:
        List of Variant objects with notation, position, and confidence
        
    Raises:
        ValueError: If confidence_threshold is not between 0 and 1
        
    Example:
        >>> recognizer = VariantRecognizer()
        >>> variants = recognizer.extract_variants("Found c.123A>G mutation")
        >>> print(variants[0].notation)  # "c.123A>G"
    """
    pass
```

#### 4. Error Handling

Use specific exception types and proper error handling:

```python
class CoordinatesLitError(Exception):
    """Base exception for Coordinates Literature Analysis."""
    pass

class APIError(CoordinatesLitError):
    """Exception raised for API-related errors."""
    pass

class AnalysisError(CoordinatesLitError):
    """Exception raised for analysis-related errors."""
    pass

def get_publication(pmid: str) -> Dict:
    """Get publication data with proper error handling."""
    try:
        response = requests.get(f"/api/publications/{pmid}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise APIError(f"Publication {pmid} not found")
        raise APIError(f"HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        raise APIError(f"Request failed: {e}")
```

#### 5. Configuration Handling

Use dependency injection for configuration:

```python
class AnalysisService:
    """Service for performing biomedical analysis."""
    
    def __init__(self, config: ConfigManager, llm_manager: LLMManager):
        self.config = config
        self.llm_manager = llm_manager
        self.cache_enabled = config.get("cache.enabled", default=True)
    
    def analyze(self, pmid: str) -> AnalysisResult:
        """Perform analysis with injected dependencies."""
        # Use injected config and LLM manager
        model = self.config.get("llm.model")
        result = self.llm_manager.analyze(pmid, model=model)
        return result
```

### Code Quality Tools

#### 1. Linting and Formatting

```bash
# Install development tools
pip install black isort flake8 mypy pre-commit

# Format code
black src/ tests/
isort src/ tests/

# Check code style
flake8 src/ tests/

# Type checking
mypy src/
```

#### 2. Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203,W503"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## 🧪 Testing Strategy

### Testing Pyramid

```
        ┌─────────────────┐
        │   E2E Tests     │  # Few, high-value integration tests
        │    (Slow)       │
        ├─────────────────┤
        │Integration Tests│  # API and service integration
        │   (Medium)      │
        ├─────────────────┤
        │   Unit Tests    │  # Fast, isolated component tests
        │    (Fast)       │
        └─────────────────┘
```

### Unit Testing

#### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer

class TestVariantRecognizer:
    """Test suite for VariantRecognizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.recognizer = VariantRecognizer()
        self.sample_text = "The BRCA1 c.123A>G mutation causes cancer."
    
    def test_extract_variants_success(self):
        """Test successful variant extraction."""
        variants = self.recognizer.extract_variants(self.sample_text)
        
        assert len(variants) == 1
        assert variants[0].notation == "c.123A>G"
        assert variants[0].confidence > 0.8
    
    def test_extract_variants_empty_text(self):
        """Test variant extraction with empty text."""
        variants = self.recognizer.extract_variants("")
        assert len(variants) == 0
    
    def test_extract_variants_no_variants(self):
        """Test text with no variants."""
        text = "This text contains no genomic variants."
        variants = self.recognizer.extract_variants(text)
        assert len(variants) == 0
    
    @pytest.mark.parametrize("notation,expected", [
        ("c.123A>G", True),
        ("p.Arg456Gln", True),
        ("invalid_notation", False),
    ])
    def test_validate_hgvs(self, notation, expected):
        """Test HGVS notation validation."""
        result = self.recognizer.validate_hgvs(notation)
        assert result == expected
```

#### Mocking External Dependencies

```python
@patch('src.api.clients.pubtator_client.requests.get')
def test_get_publication_success(self, mock_get):
    """Test successful publication retrieval."""
    # Arrange
    mock_response = Mock()
    mock_response.json.return_value = {
        'title': 'Test Publication',
        'abstract': 'Test abstract'
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    client = PubTatorClient(email="test@example.com")
    
    # Act
    result = client.get_publication_by_pmid("12345")
    
    # Assert
    assert result['title'] == 'Test Publication'
    mock_get.assert_called_once()
```

### Integration Testing

```python
@pytest.mark.integration
class TestPubMedAnalysisFlow:
    """Integration tests for PubMed analysis workflow."""
    
    def setup_method(self):
        """Set up integration test environment."""
        self.config = ConfigManager(environment="testing")
        self.flow = PubMedAnalysisFlow(config=self.config)
    
    @pytest.mark.slow
    def test_analyze_known_publication(self):
        """Test analysis of a known publication."""
        # Use a known PMID with predictable content
        pmid = "32735606"
        
        result = self.flow.analyze_pmids([pmid])
        
        assert len(result) == 1
        assert result[0]['pmid'] == pmid
        assert 'relationships' in result[0]
        assert len(result[0]['relationships']) > 0
    
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), 
        reason="OpenAI API key required"
    )
    def test_llm_analysis_integration(self):
        """Test LLM analysis integration."""
        analyzer = LlmContextAnalyzer()
        result = analyzer.analyze_publications_by_pmids(["32735606"])
        
        assert len(result) > 0
        assert result[0].confidence > 0
```

### Test Markers

```python
# pytest.ini
[tool:pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, with external dependencies)
    slow: Slow tests (may take several minutes)
    realapi: Tests that make real API calls
    llm_dependent: Tests that require LLM API access
    expensive: Tests that consume significant API credits
```

#### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m "unit"

# Run tests excluding real API calls
pytest -m "not realapi"

# Run with coverage
pytest --cov=src --cov-report=html

# Run tests in parallel
pytest -n auto

# Run specific test file
pytest tests/analysis/test_variant_recognizer.py

# Run with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x
```

## 🔄 Development Workflow

### Git Workflow

We use GitFlow with the following branches:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Individual feature development
- `release/*`: Release preparation
- `hotfix/*`: Critical bug fixes

#### Feature Development

```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/analysis-improvements

# Make changes and commit
git add .
git commit -m "feat: improve variant recognition accuracy"

# Push feature branch
git push origin feature/analysis-improvements

# Create pull request to develop branch
```

#### Commit Message Format

Use conventional commits:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(analysis): add support for structural variants
fix(api): handle rate limiting in PubTator client
docs(readme): update installation instructions
test(ner): add tests for gene recognition
```

### Code Review Process

#### Pull Request Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
```

#### Review Guidelines

**For Authors:**
1. Keep PRs small and focused
2. Write clear commit messages
3. Add tests for new functionality
4. Update documentation
5. Self-review before requesting review

**For Reviewers:**
1. Check code quality and style
2. Verify test coverage
3. Review for security issues
4. Ensure backward compatibility
5. Test manually if needed

### Continuous Integration

#### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake8 src/ tests/
    
    - name: Type check with mypy
      run: |
        mypy src/
    
    - name: Test with pytest
      run: |
        pytest -m "not realapi" --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## 📊 Performance Optimization

### Profiling

```python
import cProfile
import pstats
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer

def profile_analysis():
    """Profile analysis performance."""
    analyzer = LlmContextAnalyzer()
    pmids = ["32735606", "32719766"]
    
    # Profile the analysis
    profiler = cProfile.Profile()
    profiler.enable()
    
    results = analyzer.analyze_publications_by_pmids(pmids)
    
    profiler.disable()
    
    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)

if __name__ == "__main__":
    profile_analysis()
```

### Memory Optimization

```python
import tracemalloc
from memory_profiler import profile

@profile
def memory_intensive_analysis(pmids):
    """Analysis function with memory profiling."""
    # Start memory tracing
    tracemalloc.start()
    
    results = []
    for pmid in pmids:
        # Process each PMID
        result = analyze_publication(pmid)
        results.append(result)
        
        # Check memory usage
        current, peak = tracemalloc.get_traced_memory()
        print(f"Current memory: {current / 1024 / 1024:.1f} MB")
        print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")
    
    tracemalloc.stop()
    return results
```

### Async Processing

```python
import asyncio
import aiohttp
from typing import List

class AsyncPubTatorClient:
    """Async version of PubTator client."""
    
    async def get_publication_by_pmid(self, pmid: str) -> Dict:
        """Get publication asynchronously."""
        async with aiohttp.ClientSession() as session:
            url = f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/{pmid}"
            async with session.get(url) as response:
                return await response.json()
    
    async def batch_get_publications(self, pmids: List[str]) -> List[Dict]:
        """Get multiple publications concurrently."""
        tasks = [self.get_publication_by_pmid(pmid) for pmid in pmids]
        return await asyncio.gather(*tasks, return_exceptions=True)

# Usage
async def main():
    client = AsyncPubTatorClient()
    pmids = ["32735606", "32719766", "31234567"]
    results = await client.batch_get_publications(pmids)
    return results

# Run async code
results = asyncio.run(main())
```

## 🐛 Debugging

### Logging for Development

```python
import logging
from src.utils.logging.logger import setup_logger

# Set up debug logging
logger = setup_logger(
    name="coordinates_lit",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
)

def debug_analysis(pmid: str):
    """Analysis with detailed logging."""
    logger.debug(f"Starting analysis for PMID: {pmid}")
    
    try:
        # Get publication
        logger.debug("Fetching publication data...")
        publication = get_publication(pmid)
        logger.debug(f"Retrieved publication: {publication['title']}")
        
        # Extract entities
        logger.debug("Extracting entities...")
        entities = extract_entities(publication)
        logger.debug(f"Found {len(entities)} entities")
        
        # Analyze relationships
        logger.debug("Analyzing relationships...")
        relationships = analyze_relationships(entities)
        logger.debug(f"Found {len(relationships)} relationships")
        
        return relationships
        
    except Exception as e:
        logger.error(f"Analysis failed for {pmid}: {e}", exc_info=True)
        raise
```

### Debugging Tools

```python
# Using pdb for interactive debugging
import pdb

def debug_variant_extraction(text: str):
    """Debug variant extraction step by step."""
    pdb.set_trace()  # Debugger will stop here
    
    # Step through the code
    patterns = get_variant_patterns()
    matches = find_pattern_matches(text, patterns)
    variants = create_variant_objects(matches)
    
    return variants

# Using breakpoint() (Python 3.7+)
def extract_variants(text: str):
    """Extract variants with debugging."""
    if not text.strip():
        breakpoint()  # Modern debugging
        return []
    
    # Continue with extraction logic
    pass
```

## 📦 Deployment

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Expose port (if needed)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "from src.utils.health import health_check; health_check()" || exit 1

# Default command
CMD ["python", "-m", "src.cli.analyze", "--help"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  coordinates-lit:
    build: .
    environment:
      - ENVIRONMENT=production
      - COORDINATES_CACHE_TYPE=redis
      - COORDINATES_CACHE_REDIS_HOST=redis
    depends_on:
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - coordinates-net

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - coordinates-net

volumes:
  redis_data:

networks:
  coordinates-net:
    driver: bridge
```

### Environment Configuration

```bash
# Production environment variables
export ENVIRONMENT=production
export COORDINATES_OPENAI_KEY="your-production-key"
export COORDINATES_CACHE_TYPE=redis
export COORDINATES_CACHE_REDIS_HOST=redis.production.com
export COORDINATES_LOGGING_LEVEL=INFO
export COORDINATES_PROCESSING_MAX_WORKERS=8
```

## 🤝 Contributing

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/coordinates-lit.git
cd coordinates-lit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Set up configuration
cp config/development.example.yaml config/development.yaml
# Edit config/development.yaml with your API keys

# Run tests to verify setup
pytest -m "not realapi"
```

### Development Dependencies

```txt
# requirements-dev.txt
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
pytest-xdist>=3.0.0
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.3.0
pre-commit>=3.0.0
memory-profiler>=0.60.0
line-profiler>=4.0.0
sphinx>=5.0.0
sphinx-rtd-theme>=1.2.0
```

### Documentation

```bash
# Build documentation
cd docs/
make html

# Serve documentation locally
python -m http.server 8000 -d _build/html/
```

### Release Process

1. **Prepare Release**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/1.2.0
   ```

2. **Update Version**
   - Update version in `setup.py`
   - Update `CHANGELOG.md`
   - Update documentation

3. **Test Release**
   ```bash
   pytest
   python setup.py check
   ```

4. **Merge and Tag**
   ```bash
   git checkout main
   git merge release/1.2.0
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin main --tags
   ```

5. **Deploy**
   - Automated deployment via CI/CD
   - Manual deployment if needed

This development guide provides the foundation for maintaining high code quality, implementing robust testing, and ensuring smooth collaboration across the team. 