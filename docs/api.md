# 📡 API Documentation

This document provides comprehensive documentation for all API clients and external service integrations in the Coordinates Literature Analysis project.

## 🔍 Overview

The API layer provides standardized access to external biomedical services including PubTator3, ClinVar, and LitVar. All clients implement consistent interfaces with built-in caching, error handling, and retry mechanisms.

## 🏗️ Architecture

```
src/api/
├── clients/
│   ├── pubtator_client.py      # PubTator3 API client
│   ├── clinvar_client.py       # ClinVar API client
│   ├── litvar_client.py        # LitVar API client
│   └── base_client.py          # Base client interface
└── cache/
    ├── cache_manager.py        # Unified cache management
    ├── memory_cache.py         # In-memory caching
    └── disk_cache.py          # Persistent disk caching
```

## 🔧 API Clients

### PubTatorClient

**Purpose**: Extract biomedical entities from PubMed articles using PubTator3 API.

**Key Features**:
- Retrieve publication data by PMID
- Extract entities (genes, diseases, chemicals, variants)
- Support for multiple annotation formats
- Automatic retry with exponential backoff

#### Basic Usage

```python
from src.api.clients.pubtator_client import PubTatorClient

# Initialize client
client = PubTatorClient(email="your.email@example.com")

# Get publication by PMID
publication = client.get_publication_by_pmid("32735606")

# Extract entities
entities = client.extract_entities(publication)
```

#### Methods

##### `get_publication_by_pmid(pmid: str) -> Dict`
Retrieves complete publication data for a given PMID.

**Parameters**:
- `pmid` (str): PubMed ID

**Returns**: Dictionary containing title, abstract, authors, and annotations

**Example**:
```python
pub = client.get_publication_by_pmid("32735606")
print(pub['title'])  # "Genomic variants in BRCA1..."
print(pub['abstract'])  # Full abstract text
```

##### `extract_entities(publication: Dict) -> List[Dict]`
Extracts biomedical entities from publication data.

**Parameters**:
- `publication` (Dict): Publication data from get_publication_by_pmid

**Returns**: List of entity dictionaries with type, text, and location

**Example**:
```python
entities = client.extract_entities(publication)
for entity in entities:
    print(f"{entity['type']}: {entity['text']}")
    # Output: Disease: breast cancer
    #         Gene: BRCA1
    #         Variant: c.123A>G
```

##### `batch_get_publications(pmids: List[str]) -> List[Dict]`
Retrieves multiple publications efficiently.

**Parameters**:
- `pmids` (List[str]): List of PubMed IDs

**Returns**: List of publication dictionaries

### ClinVarClient

**Purpose**: Validate and enrich genomic variant information using ClinVar database.

**Key Features**:
- Variant lookup by multiple identifiers
- Clinical significance assessment
- Allele frequency data
- Pathogenicity classifications

#### Basic Usage

```python
from src.api.clients.clinvar_client import ClinVarClient

# Initialize client
client = ClinVarClient()

# Get variant information
variant_info = client.get_variant_info("NM_000492.3:c.1521_1523delCTT")

# Search by coordinates
coords_info = client.search_by_coordinates("17", 43044295, 43044297)
```

#### Methods

##### `get_variant_info(variant_id: str) -> Dict`
Retrieves detailed information for a specific variant.

**Parameters**:
- `variant_id` (str): Variant identifier (HGVS, rsID, etc.)

**Returns**: Dictionary with clinical significance, frequency, and classifications

##### `search_by_coordinates(chromosome: str, start: int, end: int) -> List[Dict]`
Finds variants in genomic coordinate range.

**Parameters**:
- `chromosome` (str): Chromosome number or name
- `start` (int): Start position
- `end` (int): End position

**Returns**: List of variants in the specified region

##### `get_clinical_significance(variant_id: str) -> str`
Gets clinical significance classification for a variant.

**Returns**: One of: "Pathogenic", "Likely pathogenic", "VUS", "Likely benign", "Benign"

### LitVarClient

**Purpose**: Access literature-based variant information from LitVar database.

**Key Features**:
- Literature mining for variants
- PubMed citation retrieval
- Variant-publication associations
- Statistical analysis of variant mentions

#### Basic Usage

```python
from src.api.clients.litvar_client import LitVarClient

# Initialize client
client = LitVarClient()

# Search variant in literature
lit_results = client.search_variant_literature("rs7903146")

# Get PMIDs for variant
pmids = client.get_variant_pmids("rs7903146")
```

#### Methods

##### `search_variant_literature(variant_id: str) -> Dict`
Searches literature for variant mentions.

**Parameters**:
- `variant_id` (str): Variant identifier

**Returns**: Dictionary with literature statistics and top publications

##### `get_variant_pmids(variant_id: str) -> List[str]`
Gets PubMed IDs of articles mentioning the variant.

**Returns**: List of PMIDs

## 💾 Caching System

All API clients support intelligent caching to reduce API calls and improve performance.

### Cache Types

#### Memory Cache
- **Usage**: Fast, temporary caching during single runs
- **Lifetime**: Process lifetime
- **Best for**: Development and testing

```python
from src.api.cache.memory_cache import MemoryCache

cache = MemoryCache(max_size=1000, ttl=3600)  # 1 hour TTL
```

#### Disk Cache
- **Usage**: Persistent caching across runs
- **Lifetime**: Configurable (default: 24 hours)
- **Best for**: Production and repeated analyses

```python
from src.api.cache.disk_cache import DiskCache

cache = DiskCache(cache_dir="./cache", ttl=86400)  # 24 hour TTL
```

### Cache Configuration

```yaml
# config/development.yaml
cache:
  type: "disk"  # or "memory"
  ttl: 3600     # Time to live in seconds
  max_size: 1000
  cache_dir: "./cache"
```

### Cache Management

```python
from src.api.cache.cache_manager import CacheManager

# Initialize cache
cache_manager = CacheManager(cache_type="disk", ttl=3600)

# Cache client responses
client = PubTatorClient(cache_manager=cache_manager)

# Clear cache
cache_manager.clear()

# Get cache statistics
stats = cache_manager.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

## 🔧 Configuration

### API Keys Setup

Set up your API keys in the configuration file:

```yaml
# config/development.yaml
api:
  pubtator_email: "your.email@example.com"
  clinvar_key: "your-clinvar-key"  # Optional
  litvar_key: "your-litvar-key"    # Optional
```

Or use environment variables:

```bash
export PUBTATOR_EMAIL="your.email@example.com"
export CLINVAR_API_KEY="your-clinvar-key"
export LITVAR_API_KEY="your-litvar-key"
```

### Client Configuration

```yaml
api_clients:
  pubtator:
    base_url: "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
    timeout: 30
    retry_attempts: 3
    retry_delay: 1.0
  
  clinvar:
    base_url: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    timeout: 15
    retry_attempts: 2
  
  litvar:
    base_url: "https://www.ncbi.nlm.nih.gov/research/litvar2-api"
    timeout: 20
```

## 🚨 Error Handling

All clients implement robust error handling:

### HTTP Errors
```python
from src.api.clients.exceptions import APIError, RateLimitError

try:
    publication = client.get_publication_by_pmid("12345")
except RateLimitError as e:
    print(f"Rate limit hit: {e}")
    # Automatic retry with backoff
except APIError as e:
    print(f"API error: {e}")
```

### Network Errors
```python
from requests.exceptions import Timeout, ConnectionError

try:
    result = client.get_variant_info("rs123")
except Timeout:
    print("Request timed out")
except ConnectionError:
    print("Network connection failed")
```

## 📊 Monitoring and Metrics

### API Usage Statistics

```python
# Get client statistics
stats = client.get_usage_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
print(f"Average response time: {stats['avg_response_time']:.2f}s")
```

### Rate Limiting

All clients respect API rate limits:

- **PubTator3**: 3 requests/second
- **ClinVar**: 10 requests/second  
- **LitVar**: 5 requests/second

```python
# Rate limiting is handled automatically
# But you can configure it:

client = PubTatorClient(
    rate_limit=2.0,  # 2 seconds between requests
    burst_limit=5    # Allow up to 5 rapid requests
)
```

## 🔍 Advanced Usage

### Batch Processing

```python
# Process multiple PMIDs efficiently
pmids = ["32735606", "32719766", "31234567"]

# Batch request with automatic chunking
publications = client.batch_get_publications(
    pmids, 
    chunk_size=10,  # Process 10 at a time
    delay=1.0       # 1 second delay between chunks
)
```

### Custom Annotations

```python
# Get specific annotation types
entities = client.extract_entities(
    publication,
    entity_types=["Gene", "Disease", "Variant"]
)

# Filter by confidence
high_conf_entities = client.extract_entities(
    publication,
    min_confidence=0.8
)
```

### Parallel Processing

```python
import asyncio
from src.api.clients.async_pubtator_client import AsyncPubTatorClient

async def process_pmids_parallel(pmids):
    client = AsyncPubTatorClient()
    
    # Process up to 10 PMIDs simultaneously
    tasks = [client.get_publication_by_pmid(pmid) for pmid in pmids]
    publications = await asyncio.gather(*tasks, return_exceptions=True)
    
    return publications

# Usage
pmids = ["32735606", "32719766", "31234567"]
publications = asyncio.run(process_pmids_parallel(pmids))
```

## 🧪 Testing

### Unit Tests

```bash
# Test all API clients
pytest tests/api/clients/

# Test specific client
pytest tests/api/clients/test_pubtator_client.py

# Test with real API calls (requires API keys)
pytest tests/api/clients/ -m realapi
```

### Mock Testing

```python
# Example test with mocking
from unittest.mock import Mock, patch
from src.api.clients.pubtator_client import PubTatorClient

def test_get_publication_success():
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'title': 'Test publication',
            'abstract': 'Test abstract'
        }
        
        client = PubTatorClient()
        result = client.get_publication_by_pmid("12345")
        
        assert result['title'] == 'Test publication'
```

## 🔧 Troubleshooting

### Common Issues

**1. Rate Limiting**
```
Solution: Increase delay between requests or implement exponential backoff
```

**2. Cache Misses**
```
Solution: Check cache configuration and ensure disk cache directory is writable
```

**3. Network Timeouts**
```
Solution: Increase timeout values in client configuration
```

**4. Invalid Responses**
```
Solution: Check API endpoint URLs and authentication credentials
```

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = PubTatorClient(debug=True)
```

## 📈 Performance Optimization

### Best Practices

1. **Use caching**: Enable disk cache for repeated analyses
2. **Batch requests**: Process multiple items together when possible
3. **Async processing**: Use async clients for high-throughput scenarios
4. **Rate limiting**: Respect API limits to avoid blocking
5. **Error handling**: Implement proper retry logic

### Benchmarking

```python
import time
from src.api.clients.pubtator_client import PubTatorClient

# Benchmark client performance
client = PubTatorClient()
pmids = ["32735606", "32719766", "31234567"]

start_time = time.time()
publications = client.batch_get_publications(pmids)
elapsed = time.time() - start_time

print(f"Processed {len(pmids)} PMIDs in {elapsed:.2f} seconds")
print(f"Rate: {len(pmids)/elapsed:.2f} PMIDs/second")
``` 