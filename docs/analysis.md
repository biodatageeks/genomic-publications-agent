# 🧬 Analysis Modules Guide

This document provides comprehensive documentation for all biomedical analysis modules in the Coordinates Literature Analysis project.

## 🔍 Overview

The analysis layer contains sophisticated modules for extracting, processing, and analyzing biomedical information from literature. These modules utilize Natural Language Processing (NLP), Named Entity Recognition (NER), and Large Language Models (LLMs) to understand relationships between genomic variants, genes, diseases, and other biomedical entities.

## 🏗️ Architecture

```
src/analysis/
├── base/
│   ├── base_analyzer.py        # Abstract base class for all analyzers
│   ├── analyzer_interface.py   # Common interface definitions
│   └── result_types.py         # Data structures for analysis results
├── bio_ner/
│   ├── variant_recognizer.py   # Genomic variant extraction
│   ├── gene_recognizer.py      # Gene name recognition
│   ├── disease_recognizer.py   # Disease entity extraction
│   └── coordinate_extractor.py # Genomic coordinate parsing
├── context/
│   ├── context_analyzer.py     # Context analysis around entities
│   ├── relationship_scorer.py  # Relationship strength scoring
│   └── proximity_analyzer.py   # Entity proximity analysis
└── llm/
    ├── llm_context_analyzer.py # LLM-based relationship analysis
    ├── prompt_templates.py     # Structured prompts for LLMs
    └── result_parser.py        # Parse and validate LLM responses
```

## 🧬 Bio NER Modules

### VariantRecognizer

**Purpose**: Extract genomic variants from biomedical text using pattern matching and NLP techniques.

**Key Features**:
- HGVS notation parsing (c., p., g., m., n.)
- SNP recognition (rs IDs)
- Coordinate-based variant extraction
- Validation against genomic standards

#### Basic Usage

```python
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer

# Initialize recognizer
recognizer = VariantRecognizer()

# Extract variants from text
text = "The BRCA1 c.123A>G mutation is associated with increased cancer risk."
variants = recognizer.extract_variants(text)

for variant in variants:
    print(f"Variant: {variant.notation}")
    print(f"Position: {variant.start}-{variant.end}")
    print(f"Confidence: {variant.confidence}")
```

#### Methods

##### `extract_variants(text: str) -> List[Variant]`
Extracts all genomic variants from given text.

**Parameters**:
- `text` (str): Input text containing potential variants

**Returns**: List of Variant objects with notation, position, and confidence

**Example**:
```python
variants = recognizer.extract_variants(
    "Found mutations c.123A>G and p.Arg456Gln in BRCA1"
)
# Returns: [Variant(notation="c.123A>G", ...), Variant(notation="p.Arg456Gln", ...)]
```

##### `validate_hgvs(notation: str) -> bool`
Validates HGVS notation format.

**Parameters**:
- `notation` (str): HGVS notation string

**Returns**: True if valid HGVS format

##### `extract_coordinates(text: str) -> List[GenomicCoordinate]`
Extracts genomic coordinates from text.

**Returns**: List of GenomicCoordinate objects

### GeneRecognizer

**Purpose**: Identify gene names and symbols in biomedical text.

**Key Features**:
- Standard gene symbol recognition
- Alternative gene name handling
- Gene synonym mapping
- Confidence scoring based on context

#### Basic Usage

```python
from src.analysis.bio_ner.gene_recognizer import GeneRecognizer

recognizer = GeneRecognizer()

# Extract genes from text
text = "BRCA1 and TP53 genes are tumor suppressors."
genes = recognizer.extract_genes(text)

for gene in genes:
    print(f"Gene: {gene.symbol}")
    print(f"Full name: {gene.full_name}")
    print(f"Confidence: {gene.confidence}")
```

#### Methods

##### `extract_genes(text: str) -> List[Gene]`
Extracts gene names and symbols from text.

##### `normalize_gene_symbol(symbol: str) -> str`
Normalizes gene symbols to standard format.

##### `get_gene_synonyms(symbol: str) -> List[str]`
Returns known synonyms for a gene symbol.

### DiseaseRecognizer

**Purpose**: Extract disease and phenotype entities from biomedical literature.

**Key Features**:
- Disease name recognition
- Phenotype extraction
- Medical ontology mapping
- Severity assessment

#### Basic Usage

```python
from src.analysis.bio_ner.disease_recognizer import DiseaseRecognizer

recognizer = DiseaseRecognizer()

text = "Patient diagnosed with breast cancer and diabetes mellitus."
diseases = recognizer.extract_diseases(text)

for disease in diseases:
    print(f"Disease: {disease.name}")
    print(f"Category: {disease.category}")
    print(f"Severity: {disease.severity}")
```

## 🎯 Context Analysis Modules

### ContextAnalyzer

**Purpose**: Analyze the context around biomedical entities to understand relationships and associations.

**Key Features**:
- Sentence-level context extraction
- Entity co-occurrence analysis
- Relationship type classification
- Semantic similarity scoring

#### Basic Usage

```python
from src.analysis.context.context_analyzer import ContextAnalyzer

analyzer = ContextAnalyzer()

# Analyze context around entities
text = "The BRCA1 c.123A>G mutation increases breast cancer risk significantly."
entities = ["BRCA1", "c.123A>G", "breast cancer"]

context_result = analyzer.analyze_context(text, entities)

print(f"Relationship strength: {context_result.strength}")
print(f"Context type: {context_result.relationship_type}")
print(f"Supporting evidence: {context_result.evidence}")
```

#### Methods

##### `analyze_context(text: str, entities: List[str]) -> ContextResult`
Analyzes relationships between entities in given context.

**Parameters**:
- `text` (str): Text containing the entities
- `entities` (List[str]): List of entity names to analyze

**Returns**: ContextResult with relationship information

##### `extract_sentences_with_entities(text: str, entities: List[str]) -> List[str]`
Extracts sentences containing specified entities.

##### `calculate_entity_proximity(text: str, entity1: str, entity2: str) -> float`
Calculates proximity score between two entities in text.

### RelationshipScorer

**Purpose**: Score the strength of relationships between biomedical entities.

**Key Features**:
- Multiple scoring algorithms
- Confidence intervals
- Evidence weighting
- Relationship type classification

#### Basic Usage

```python
from src.analysis.context.relationship_scorer import RelationshipScorer

scorer = RelationshipScorer()

# Score relationship between variant and disease
variant = "c.123A>G"
disease = "breast cancer"
context = "The c.123A>G mutation is strongly associated with breast cancer."

score = scorer.score_relationship(variant, disease, context)

print(f"Relationship score: {score.strength}/10")
print(f"Confidence: {score.confidence}")
print(f"Evidence type: {score.evidence_type}")
```

#### Methods

##### `score_relationship(entity1: str, entity2: str, context: str) -> RelationshipScore`
Scores relationship strength between two entities.

**Returns**: RelationshipScore object with strength, confidence, and evidence

##### `classify_relationship_type(entity1: str, entity2: str, context: str) -> str`
Classifies the type of relationship (causal, associative, regulatory, etc.).

## 🤖 LLM Analysis Modules

### LlmContextAnalyzer

**Purpose**: Use Large Language Models to analyze complex relationships and extract insights from biomedical literature.

**Key Features**:
- GPT-based relationship analysis
- Structured prompt engineering
- Multi-model support (OpenAI, TogetherAI)
- Confidence scoring and validation

#### Basic Usage

```python
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer

# Initialize with specific model
analyzer = LlmContextAnalyzer(model="gpt-4", temperature=0.3)

# Analyze publications by PMIDs
pmids = ["32735606", "32719766"]
results = analyzer.analyze_publications_by_pmids(pmids)

for result in results:
    print(f"PMID: {result.pmid}")
    print(f"Relationships found: {len(result.relationships)}")
    
    for rel in result.relationships:
        print(f"  {rel.entity1} -> {rel.entity2}")
        print(f"  Strength: {rel.strength}/10")
        print(f"  Evidence: {rel.evidence}")
```

#### Methods

##### `analyze_publications_by_pmids(pmids: List[str]) -> List[PublicationAnalysis]`
Analyzes multiple publications for relationships.

**Parameters**:
- `pmids` (List[str]): List of PubMed IDs

**Returns**: List of PublicationAnalysis objects

##### `analyze_single_publication(publication: Dict) -> PublicationAnalysis`
Analyzes a single publication for entity relationships.

**Parameters**:
- `publication` (Dict): Publication data with title, abstract, and annotations

**Returns**: PublicationAnalysis with extracted relationships

##### `score_variant_disease_relationship(variant: str, disease: str, context: str) -> float`
Scores specific variant-disease relationship strength.

**Returns**: Relationship strength score (0-10)

#### Advanced Configuration

```python
# Configure LLM settings
analyzer = LlmContextAnalyzer(
    model="gpt-4",
    temperature=0.2,          # Lower temperature for more consistent results
    max_tokens=1000,          # Limit response length
    retry_attempts=3,         # Number of retries on failure
    timeout=60,               # Request timeout in seconds
    
    # Custom prompt configuration
    prompt_style="detailed",  # or "concise", "structured"
    include_context=True,     # Include full publication context
    extract_evidence=True     # Extract supporting evidence quotes
)

# Batch processing with progress tracking
results = analyzer.analyze_publications_by_pmids(
    pmids=["12345", "67890"],
    batch_size=5,             # Process 5 at a time
    delay=1.0,                # 1 second delay between batches
    progress_callback=lambda i, total: print(f"Progress: {i}/{total}")
)
```

### Prompt Templates

**Purpose**: Standardized prompts for consistent LLM analysis across different tasks.

#### Available Templates

```python
from src.analysis.llm.prompt_templates import PromptTemplates

templates = PromptTemplates()

# Relationship analysis prompt
rel_prompt = templates.get_relationship_analysis_prompt(
    title="BRCA1 mutations in breast cancer",
    abstract="Study abstract...",
    entities=["BRCA1", "c.123A>G", "breast cancer"]
)

# Variant-disease scoring prompt
score_prompt = templates.get_variant_disease_scoring_prompt(
    variant="c.123A>G",
    disease="breast cancer",
    context="Full publication context..."
)

# Evidence extraction prompt
evidence_prompt = templates.get_evidence_extraction_prompt(
    text="Publication text...",
    target_relationship="BRCA1 mutation causes breast cancer"
)
```

## 🔄 Analysis Workflows

### Complete Analysis Pipeline

```python
from src.analysis.bio_ner.variant_recognizer import VariantRecognizer
from src.analysis.bio_ner.disease_recognizer import DiseaseRecognizer
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer
from src.api.clients.pubtator_client import PubTatorClient

# Initialize components
variant_recognizer = VariantRecognizer()
disease_recognizer = DiseaseRecognizer()
llm_analyzer = LlmContextAnalyzer()
pubtator_client = PubTatorClient()

# Complete analysis workflow
def analyze_publication_complete(pmid: str):
    # 1. Get publication data
    publication = pubtator_client.get_publication_by_pmid(pmid)
    
    # 2. Extract entities using NER
    text = f"{publication['title']} {publication['abstract']}"
    variants = variant_recognizer.extract_variants(text)
    diseases = disease_recognizer.extract_diseases(text)
    
    # 3. Analyze relationships using LLM
    llm_results = llm_analyzer.analyze_single_publication(publication)
    
    # 4. Combine results
    return {
        'pmid': pmid,
        'publication': publication,
        'variants': variants,
        'diseases': diseases,
        'relationships': llm_results.relationships,
        'overall_score': llm_results.confidence
    }

# Use the pipeline
result = analyze_publication_complete("32735606")
```

### Batch Processing

```python
# Process multiple publications efficiently
def batch_analyze_publications(pmids: List[str], batch_size: int = 10):
    results = []
    
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i + batch_size]
        
        # Process batch
        batch_results = []
        for pmid in batch:
            try:
                result = analyze_publication_complete(pmid)
                batch_results.append(result)
            except Exception as e:
                print(f"Error processing {pmid}: {e}")
        
        results.extend(batch_results)
        
        # Progress update
        print(f"Processed {min(i + batch_size, len(pmids))}/{len(pmids)} publications")
    
    return results

# Usage
pmids = ["32735606", "32719766", "31234567"]
all_results = batch_analyze_publications(pmids)
```

## 📊 Result Interpretation

### Understanding Scores

The analysis modules provide various scoring mechanisms:

#### Relationship Strength Scores (0-10)
- **0-2**: No significant relationship
- **3-4**: Weak/possible relationship
- **5-6**: Moderate relationship
- **7-8**: Strong relationship
- **9-10**: Very strong/definitive relationship

#### Confidence Scores (0-1)
- **0.0-0.3**: Low confidence
- **0.4-0.6**: Moderate confidence
- **0.7-0.8**: High confidence
- **0.9-1.0**: Very high confidence

### Result Validation

```python
# Validate analysis results
def validate_analysis_result(result):
    validation = {
        'has_variants': len(result['variants']) > 0,
        'has_diseases': len(result['diseases']) > 0,
        'has_relationships': len(result['relationships']) > 0,
        'score_valid': 0 <= result['overall_score'] <= 10,
        'quality_score': 0
    }
    
    # Calculate quality score
    quality_factors = [
        validation['has_variants'],
        validation['has_diseases'], 
        validation['has_relationships'],
        validation['score_valid']
    ]
    validation['quality_score'] = sum(quality_factors) / len(quality_factors)
    
    return validation

# Usage
result = analyze_publication_complete("32735606")
validation = validate_analysis_result(result)
print(f"Analysis quality: {validation['quality_score']:.2%}")
```

## 🧪 Testing Analysis Modules

### Unit Testing

```bash
# Test all analysis modules
pytest tests/analysis/

# Test specific modules
pytest tests/analysis/bio_ner/
pytest tests/analysis/llm/
pytest tests/analysis/context/

# Test with specific markers
pytest tests/analysis/ -m "not llm_dependent"  # Skip LLM tests
pytest tests/analysis/ -m slow                  # Only slow tests
```

### Integration Testing

```python
# Example integration test
import pytest
from src.analysis.llm.llm_context_analyzer import LlmContextAnalyzer

@pytest.mark.integration
@pytest.mark.llm_dependent
def test_full_analysis_pipeline():
    """Test complete analysis pipeline with real data."""
    analyzer = LlmContextAnalyzer()
    
    # Use known publication with variants
    results = analyzer.analyze_publications_by_pmids(["32735606"])
    
    assert len(results) == 1
    assert results[0].pmid == "32735606"
    assert len(results[0].relationships) > 0
    
    # Check relationship quality
    for rel in results[0].relationships:
        assert 0 <= rel.strength <= 10
        assert rel.entity1 is not None
        assert rel.entity2 is not None
```

## 🔧 Performance Optimization

### Caching Analysis Results

```python
from src.api.cache.cache_manager import CacheManager

# Cache analysis results
cache_manager = CacheManager(cache_type="disk", ttl=86400)  # 24 hours

def cached_analyze_publication(pmid: str):
    cache_key = f"analysis_{pmid}"
    
    # Check cache first
    cached_result = cache_manager.get(cache_key)
    if cached_result:
        return cached_result
    
    # Perform analysis
    result = analyze_publication_complete(pmid)
    
    # Cache result
    cache_manager.set(cache_key, result)
    
    return result
```

### Parallel Processing

```python
import concurrent.futures
from typing import List, Dict

def parallel_analyze_publications(pmids: List[str], max_workers: int = 4) -> List[Dict]:
    """Analyze publications in parallel."""
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_pmid = {
            executor.submit(analyze_publication_complete, pmid): pmid 
            for pmid in pmids
        }
        
        results = []
        for future in concurrent.futures.as_completed(future_to_pmid):
            pmid = future_to_pmid[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {pmid}: {e}")
        
        return results

# Usage
pmids = ["32735606", "32719766", "31234567"]
results = parallel_analyze_publications(pmids, max_workers=3)
```

## 🔍 Advanced Features

### Custom Entity Recognition

```python
# Extend variant recognizer with custom patterns
class CustomVariantRecognizer(VariantRecognizer):
    def __init__(self):
        super().__init__()
        self.custom_patterns = [
            r'chr\d+:g\.\d+[ATCG]>[ATCG]',  # Custom genomic pattern
            r'exon\s+\d+\s+mutation',       # Exon mutation pattern
        ]
    
    def extract_variants(self, text: str):
        # Use parent method
        variants = super().extract_variants(text)
        
        # Add custom pattern matches
        for pattern in self.custom_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                custom_variant = Variant(
                    notation=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=0.8,
                    source="custom_pattern"
                )
                variants.append(custom_variant)
        
        return variants
```

### Custom LLM Prompts

```python
# Create custom prompt templates
class CustomPromptTemplates(PromptTemplates):
    def get_clinical_significance_prompt(self, variant: str, phenotype: str) -> str:
        return f"""
        Analyze the clinical significance of the following genomic variant 
        in relation to the specified phenotype:
        
        Variant: {variant}
        Phenotype: {phenotype}
        
        Please provide:
        1. Clinical significance (Pathogenic/Benign/VUS)
        2. Confidence level (0-10)
        3. Supporting evidence
        4. Mechanism of action (if known)
        
        Format your response as structured JSON.
        """
```

## 📚 Best Practices

### 1. **Error Handling**
Always implement robust error handling for API calls and LLM requests:

```python
try:
    result = analyzer.analyze_publications_by_pmids(pmids)
except APIError as e:
    logger.error(f"API error: {e}")
    # Implement fallback strategy
except LLMError as e:
    logger.error(f"LLM error: {e}")
    # Use cached results or simpler analysis
```

### 2. **Input Validation**
Validate inputs before processing:

```python
def validate_pmid(pmid: str) -> bool:
    return pmid.isdigit() and len(pmid) >= 8

def validate_hgvs_notation(notation: str) -> bool:
    return re.match(r'^[cgnpm]\.[0-9]+', notation) is not None
```

### 3. **Result Quality Control**
Implement quality checks for analysis results:

```python
def quality_check_result(result):
    warnings = []
    
    if result.confidence < 0.5:
        warnings.append("Low confidence score")
    
    if len(result.relationships) == 0:
        warnings.append("No relationships found")
    
    return warnings
```

### 4. **Resource Management**
Monitor and manage computational resources:

```python
# Monitor LLM token usage
total_tokens = sum(result.token_usage for result in results)
estimated_cost = total_tokens * 0.002 / 1000  # Example pricing

print(f"Total tokens used: {total_tokens}")
print(f"Estimated cost: ${estimated_cost:.2f}")
``` 