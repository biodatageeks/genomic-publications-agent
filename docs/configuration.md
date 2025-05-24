# ⚙️ Configuration Guide

This document provides comprehensive information about configuring the Coordinates Literature Analysis project for different environments and use cases.

## 📋 Overview

The project uses a hierarchical configuration system that supports multiple environments, environment variables, and flexible overrides. Configuration is managed through YAML files with support for development, testing, and production environments.

## 🏗️ Configuration Structure

```
config/
├── development.yaml           # Development environment (default)
├── testing.yaml              # Testing environment
├── production.yaml           # Production environment
├── development.example.yaml  # Template for development config
└── local.yaml                # Local overrides (git-ignored)
```

## 🔧 Basic Configuration

### Default Configuration File

The system looks for configuration files in this order:
1. `config/local.yaml` (highest priority, git-ignored)
2. `config/{environment}.yaml` (based on `ENVIRONMENT` variable)
3. `config/development.yaml` (default fallback)

### Environment Selection

Set the environment using the `ENVIRONMENT` variable:

```bash
export ENVIRONMENT=production
# or
export ENVIRONMENT=testing
```

## 📄 Configuration Sections

### LLM Configuration

```yaml
llm:
  # Primary LLM provider
  provider: "openai"  # Options: "openai", "together"
  
  # Model selection
  model: "gpt-3.5-turbo"  # OpenAI: gpt-3.5-turbo, gpt-4, gpt-4-turbo
                          # Together: llama-2-70b, mixtral-8x7b, etc.
  
  # Generation parameters
  temperature: 0.7        # 0.0 (deterministic) to 2.0 (creative)
  max_tokens: 2000        # Maximum response length
  top_p: 0.9             # Nucleus sampling parameter
  frequency_penalty: 0.0  # Reduce repetition (-2.0 to 2.0)
  presence_penalty: 0.0   # Encourage new topics (-2.0 to 2.0)
  
  # Request settings
  timeout: 60            # Request timeout in seconds
  retry_attempts: 3      # Number of retry attempts
  retry_delay: 1.0       # Initial delay between retries (exponential backoff)
  
  # Advanced settings
  stream: false          # Enable streaming responses
  seed: null            # Seed for reproducible outputs
  response_format: "text"  # Options: "text", "json"
```

### API Configuration

```yaml
api:
  # API Keys (can be overridden by environment variables)
  openai_key: "your-openai-api-key"
  together_key: "your-together-api-key"
  pubtator_email: "your-email@example.com"
  clinvar_key: "optional-clinvar-key"
  litvar_key: "optional-litvar-key"
  
  # Rate limiting
  rate_limits:
    openai: 3500        # Requests per minute
    together: 1000      # Requests per minute
    pubtator: 180       # Requests per minute (3 per second)
    clinvar: 600        # Requests per minute (10 per second)
    litvar: 300         # Requests per minute (5 per second)
  
  # Timeouts
  timeouts:
    openai: 60
    together: 60
    pubtator: 30
    clinvar: 15
    litvar: 20
  
  # Base URLs (usually don't need to change)
  base_urls:
    pubtator: "https://www.ncbi.nlm.nih.gov/research/pubtator3-api"
    clinvar: "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    litvar: "https://www.ncbi.nlm.nih.gov/research/litvar2-api"
```

### Cache Configuration

```yaml
cache:
  # Cache type
  type: "disk"           # Options: "memory", "disk", "redis"
  
  # Cache settings
  ttl: 86400            # Time to live in seconds (24 hours)
  max_size: 10000       # Maximum number of cached items
  
  # Disk cache specific
  cache_dir: "./cache"   # Directory for disk cache
  compression: true      # Compress cached data
  
  # Memory cache specific
  cleanup_interval: 3600 # Cleanup interval in seconds
  
  # Redis cache specific (if using Redis)
  redis:
    host: "localhost"
    port: 6379
    db: 0
    password: null
    ssl: false
```

### Logging Configuration

```yaml
logging:
  # Log level
  level: "INFO"         # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
  
  # Log format
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Log destinations
  handlers:
    console:
      enabled: true
      level: "INFO"
      format: "%(levelname)s: %(message)s"
    
    file:
      enabled: true
      level: "DEBUG"
      filename: "logs/coordinates-lit.log"
      max_bytes: 10485760  # 10MB
      backup_count: 5
      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    rotating_file:
      enabled: false
      level: "INFO"
      filename: "logs/coordinates-lit-daily.log"
      when: "midnight"
      interval: 1
      backup_count: 30
  
  # Logger-specific settings
  loggers:
    "src.api.clients": "DEBUG"
    "src.analysis.llm": "INFO"
    "httpx": "WARNING"
    "urllib3": "WARNING"
```

### Analysis Configuration

```yaml
analysis:
  # Bio NER settings
  bio_ner:
    variant_recognizer:
      confidence_threshold: 0.7
      validate_hgvs: true
      include_coordinates: true
    
    gene_recognizer:
      use_gene_db: true
      normalize_symbols: true
      confidence_threshold: 0.8
    
    disease_recognizer:
      use_ontology_mapping: true
      include_phenotypes: true
      confidence_threshold: 0.7
  
  # Context analysis settings
  context:
    window_size: 200      # Context window around entities (characters)
    sentence_boundary: true
    proximity_threshold: 50
    relationship_threshold: 0.6
  
  # LLM analysis settings
  llm_analysis:
    batch_size: 10
    concurrent_requests: 3
    enable_caching: true
    validate_responses: true
    extract_evidence: true
    score_threshold: 3.0
```

### Processing Configuration

```yaml
processing:
  # Batch processing
  batch_size: 50
  max_workers: 4
  timeout_per_item: 300
  
  # Data validation
  validate_pmids: true
  skip_invalid_entries: true
  max_retry_attempts: 3
  
  # Output settings
  output_formats: ["csv", "json"]
  include_metadata: true
  compress_output: false
  
  # Quality control
  min_confidence_score: 0.5
  require_relationships: false
  filter_weak_relationships: true
```

## 🌍 Environment-Specific Configurations

### Development Configuration

```yaml
# config/development.yaml
llm:
  provider: "openai"
  model: "gpt-3.5-turbo"
  temperature: 0.7

cache:
  type: "memory"
  ttl: 3600

logging:
  level: "DEBUG"
  handlers:
    console:
      enabled: true
      level: "DEBUG"

analysis:
  llm_analysis:
    batch_size: 5
    concurrent_requests: 2
```

### Testing Configuration

```yaml
# config/testing.yaml
llm:
  provider: "mock"      # Use mock LLM for testing
  model: "mock-model"

cache:
  type: "memory"
  ttl: 60

logging:
  level: "WARNING"
  handlers:
    console:
      enabled: true

analysis:
  llm_analysis:
    batch_size: 2
    concurrent_requests: 1
    enable_caching: false
```

### Production Configuration

```yaml
# config/production.yaml
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.3

cache:
  type: "redis"
  ttl: 86400
  redis:
    host: "redis.example.com"
    port: 6379
    ssl: true

logging:
  level: "INFO"
  handlers:
    console:
      enabled: false
    file:
      enabled: true
      level: "INFO"
    rotating_file:
      enabled: true

analysis:
  llm_analysis:
    batch_size: 20
    concurrent_requests: 5
```

## 🔐 Environment Variables

All configuration values can be overridden using environment variables with the prefix `COORDINATES_`:

### API Keys
```bash
export COORDINATES_OPENAI_KEY="your-openai-key"
export COORDINATES_TOGETHER_KEY="your-together-key"
export COORDINATES_PUBTATOR_EMAIL="your-email@example.com"
```

### LLM Settings
```bash
export COORDINATES_LLM_PROVIDER="openai"
export COORDINATES_LLM_MODEL="gpt-4"
export COORDINATES_LLM_TEMPERATURE="0.3"
export COORDINATES_LLM_MAX_TOKENS="2000"
```

### Cache Settings
```bash
export COORDINATES_CACHE_TYPE="disk"
export COORDINATES_CACHE_TTL="86400"
export COORDINATES_CACHE_DIR="./cache"
```

### Logging Settings
```bash
export COORDINATES_LOGGING_LEVEL="INFO"
export COORDINATES_LOGGING_FILE_ENABLED="true"
```

### Processing Settings
```bash
export COORDINATES_PROCESSING_BATCH_SIZE="50"
export COORDINATES_PROCESSING_MAX_WORKERS="4"
```

## 🔧 Configuration Loading

### Programmatic Access

```python
from src.utils.config.config_manager import ConfigManager

# Load configuration
config = ConfigManager()

# Access configuration values
llm_model = config.get("llm.model")
cache_type = config.get("cache.type")
log_level = config.get("logging.level")

# Access with defaults
timeout = config.get("api.timeouts.openai", default=60)

# Check if value exists
if config.has("llm.openai_key"):
    api_key = config.get("llm.openai_key")
```

### Environment-Specific Loading

```python
# Load specific environment
config = ConfigManager(environment="production")

# Override environment via environment variable
import os
os.environ["ENVIRONMENT"] = "testing"
config = ConfigManager()  # Loads testing configuration
```

### Configuration Validation

```python
# Validate configuration
validation_result = config.validate()

if not validation_result.is_valid:
    print("Configuration errors:")
    for error in validation_result.errors:
        print(f"  - {error}")
```

## 🎛️ Advanced Configuration

### Custom Configuration Providers

```python
# Custom configuration provider
class CustomConfigProvider:
    def get_config(self) -> dict:
        return {
            "llm": {
                "provider": "custom_provider",
                "model": "custom_model"
            }
        }

# Register custom provider
config_manager = ConfigManager()
config_manager.add_provider(CustomConfigProvider())
```

### Configuration Overrides

```python
# Runtime configuration overrides
config = ConfigManager()

# Override specific values
config.set("llm.temperature", 0.5)
config.set("cache.ttl", 7200)

# Bulk override
overrides = {
    "llm": {
        "model": "gpt-4",
        "temperature": 0.2
    },
    "cache": {
        "type": "memory"
    }
}
config.update(overrides)
```

### Configuration Profiles

```yaml
# config/profiles.yaml
profiles:
  fast_analysis:
    llm:
      model: "gpt-3.5-turbo"
      temperature: 0.8
    cache:
      type: "memory"
    analysis:
      batch_size: 20
  
  accurate_analysis:
    llm:
      model: "gpt-4"
      temperature: 0.2
    cache:
      type: "disk"
    analysis:
      batch_size: 5
      validate_responses: true

  cost_optimized:
    llm:
      provider: "together"
      model: "llama-2-70b"
    cache:
      type: "disk"
      ttl: 604800  # 1 week
```

```python
# Load configuration profile
config = ConfigManager(profile="accurate_analysis")
```

## 🔍 Configuration Examples

### Research Environment

```yaml
# Optimized for research with high accuracy
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 3000

cache:
  type: "disk"
  ttl: 604800  # 1 week
  cache_dir: "./research_cache"

analysis:
  context:
    window_size: 300
  llm_analysis:
    batch_size: 5
    extract_evidence: true
    validate_responses: true
    score_threshold: 2.0

processing:
  batch_size: 10
  validate_pmids: true
  require_relationships: true
```

### High-Throughput Environment

```yaml
# Optimized for processing large datasets
llm:
  provider: "together"
  model: "mixtral-8x7b"
  temperature: 0.5

cache:
  type: "redis"
  ttl: 86400

analysis:
  llm_analysis:
    batch_size: 50
    concurrent_requests: 10

processing:
  batch_size: 100
  max_workers: 8
  skip_invalid_entries: true
```

### Cost-Optimized Environment

```yaml
# Minimize API costs while maintaining quality
llm:
  provider: "together"
  model: "llama-2-70b"
  temperature: 0.7
  max_tokens: 1500

cache:
  type: "disk"
  ttl: 2592000  # 30 days
  compression: true

analysis:
  llm_analysis:
    enable_caching: true
    score_threshold: 4.0

processing:
  filter_weak_relationships: true
  min_confidence_score: 0.7
```

## 🧪 Testing Configuration

### Unit Test Configuration

```yaml
# config/unittest.yaml
llm:
  provider: "mock"
  model: "mock-gpt"

cache:
  type: "memory"
  ttl: 60

logging:
  level: "ERROR"
  handlers:
    console:
      enabled: false

api:
  timeouts:
    openai: 5
    pubtator: 5
```

### Integration Test Configuration

```yaml
# config/integration.yaml
llm:
  provider: "openai"
  model: "gpt-3.5-turbo"
  temperature: 0.0  # Deterministic for testing

cache:
  type: "memory"
  ttl: 300

analysis:
  llm_analysis:
    batch_size: 2
    concurrent_requests: 1
```

## 🚨 Security Considerations

### API Key Management

```yaml
# NEVER commit API keys to version control
# Use environment variables or secure vault systems

# Bad ❌
api:
  openai_key: "sk-abcd1234..."

# Good ✅
api:
  openai_key: "${OPENAI_API_KEY}"
```

### Environment Variable Security

```bash
# Use secure methods to set environment variables

# For development (in .env file, git-ignored)
COORDINATES_OPENAI_KEY="your-key-here"

# For production (set in deployment environment)
kubectl create secret generic api-keys \
  --from-literal=openai-key="your-key-here"
```

### Configuration Encryption

```python
# Encrypt sensitive configuration sections
from src.utils.config.encryption import ConfigEncryption

# Encrypt configuration
encryptor = ConfigEncryption()
encrypted_config = encryptor.encrypt_section(config, "api")

# Decrypt at runtime
decrypted_config = encryptor.decrypt_section(encrypted_config, "api")
```

## 🔧 Troubleshooting

### Common Configuration Issues

**1. Missing API Keys**
```
Error: OpenAI API key not found
Solution: Set COORDINATES_OPENAI_KEY environment variable
```

**2. Invalid Configuration Format**
```
Error: Invalid YAML syntax
Solution: Check YAML indentation and special characters
```

**3. Cache Directory Permissions**
```
Error: Permission denied writing to cache directory
Solution: Ensure cache directory is writable
```

**4. Model Not Available**
```
Error: Model 'gpt-5' not found
Solution: Check model name and provider availability
```

### Configuration Validation

```python
# Validate configuration before use
def validate_config(config):
    errors = []
    
    # Check required fields
    required_fields = [
        "llm.provider",
        "llm.model",
        "cache.type"
    ]
    
    for field in required_fields:
        if not config.has(field):
            errors.append(f"Missing required field: {field}")
    
    # Check API keys
    provider = config.get("llm.provider")
    if provider == "openai" and not config.has("api.openai_key"):
        errors.append("OpenAI API key required for OpenAI provider")
    
    return errors

# Usage
config = ConfigManager()
errors = validate_config(config)
if errors:
    for error in errors:
        print(f"Config error: {error}")
```

### Debug Configuration

```python
# Debug configuration loading
config = ConfigManager(debug=True)

# Print loaded configuration
print("Loaded configuration:")
config.print_config(mask_sensitive=True)

# Print configuration sources
print("Configuration sources:")
for source in config.get_sources():
    print(f"  {source.name}: {source.path}")
```

## 📈 Performance Tuning

### Cache Optimization

```yaml
cache:
  type: "redis"
  redis:
    # Connection pooling
    max_connections: 50
    connection_pool_class: "redis.BlockingConnectionPool"
    
    # Performance settings
    socket_keepalive: true
    socket_keepalive_options: {}
    health_check_interval: 30
```

### LLM Optimization

```yaml
llm:
  # Batch requests for better throughput
  batch_size: 20
  
  # Optimize for speed vs quality
  temperature: 0.7
  max_tokens: 1500
  
  # Connection settings
  timeout: 30
  max_retries: 2
  
  # Rate limiting
  requests_per_minute: 3000
  tokens_per_minute: 150000
```

### Processing Optimization

```yaml
processing:
  # Parallel processing
  max_workers: 8
  batch_size: 100
  
  # Memory management
  memory_limit: "8GB"
  gc_threshold: 1000
  
  # I/O optimization
  async_io: true
  buffer_size: 65536
``` 