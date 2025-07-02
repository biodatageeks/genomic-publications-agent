# Universal Model Wrapper System 🚀

A unified model wrapper system providing a consistent interface for different types of AI models and various use cases.

## 🎯 Goal

Elimination of code duplication and providing a consistent API for:
- **Embeddings** (HuggingFace, OpenAI, etc.)
- **Tokenization** (BERT, GPT, etc.)
- **Chat/Generation** (LLM, OpenAI, Together AI, etc.)
- **Classification** (sentiment, NER, etc.)

## 🏗️ Architecture

```
BaseModelWrapper (abstract base class)
├── HuggingFaceModelWrapper (HuggingFace models)
├── LLMModelWrapper (LLM models via API)
└── [Other implementations...]

ModelFactory (automatic detection and creation of wrappers)

Generic Classes (easy-to-use interfaces):
├── GenericEmbedder
├── GenericTokenizer  
├── GenericChat
└── GenericClassifier
```

## 🚀 Quick Start

### 1. Embeddings
```python
from src.utils.models.generic import GenericEmbedder

# HuggingFace embeddings
embedder = GenericEmbedder("sentence-transformers/all-MiniLM-L6-v2")
embedding = embedder.embed("Your text here")

# Batch processing
embeddings = embedder.embed_batch(["Text 1", "Text 2", "Text 3"])
```

### 2. Chat/Generation
```python
from src.utils.models.generic import GenericChat

# Together AI
chat = GenericChat("meta-llama/Llama-3-8b-chat-hf", provider="together")
response = chat.chat("Hello!", system_prompt="You are helpful")

# OpenAI (requires API key)
chat = GenericChat("gpt-3.5-turbo", provider="openai")
response = chat.generate("Complete this: AI is...")
```

### 3. Classification
```python
from src.utils.models.generic import GenericClassifier

# Sentiment analysis
classifier = GenericClassifier("cardiffnlp/twitter-roberta-base-sentiment-latest")
result = classifier.classify("I love this!")
print(result['label'])  # 'positive'
```

### 4. Tokenization
```python
from src.utils.models.generic import GenericTokenizer

tokenizer = GenericTokenizer("bert-base-uncased")
tokens = tokenizer.tokenize("Hello world!")
token_ids = tokenizer.encode("Hello world!")
```

## 🔄 Easy Model Switching

```python
# Changing models is just one line!
embedder = GenericEmbedder("model-v1")
# embedder = GenericEmbedder("model-v2")  # <- switch!

# All methods work the same way
embedding = embedder.embed("test")
```

## 🏭 Factory Pattern

```python
from src.utils.models.factory import ModelFactory

# Automatic model type detection
wrapper = ModelFactory.create("bert-base-uncased")
wrapper = ModelFactory.create("gpt-3.5-turbo", provider="openai")

# Specific creation
hf_wrapper = ModelFactory.create_embedder("sentence-transformers/all-MiniLM-L6-v2")
llm_wrapper = ModelFactory.create_llm("llama-2-7b", provider="together")
```

## 🎛️ Configuration

### Supported Providers:
- **HuggingFace**: Local models (BERT, RoBERTa, sentence-transformers, etc.)
- **OpenAI**: gpt-3.5-turbo, gpt-4, text-embedding-ada-002, etc.
- **Together AI**: Llama, Mistral, Code Llama, etc.

### Environment Variables:
```bash
export OPENAI_API_KEY="your-openai-key"
export TOGETHER_API_KEY="your-together-key"
```

## 🔧 Advanced Usage

### Context Manager
```python
with GenericEmbedder("large-model") as embedder:
    embeddings = embedder.embed_batch(large_text_list)
# Model automatically freed from memory
```

### Batch Processing
```python
embedder = GenericEmbedder()
# Efficient batch processing with automatic chunking
embeddings = embedder.embed_batch(texts, batch_size=16)
```

### Error Handling
```python
try:
    chat = GenericChat("non-existent-model")
    response = chat.generate("test")
except Exception as e:
    print(f"Model failed: {e}")
```

## 📊 Use Case Examples

### 1. RAG System
```python
# Embedding documents
embedder = GenericEmbedder("sentence-transformers/all-MiniLM-L6-v2")
doc_embeddings = embedder.embed_batch(documents)

# Generating responses
chat = GenericChat("llama-2-7b-chat", provider="together")
response = chat.chat(query, system_prompt="Answer based on context")
```

### 2. Text Classification Pipeline
```python
# Sentiment + Topic classification
sentiment = GenericClassifier("cardiffnlp/twitter-roberta-base-sentiment")
topic = GenericClassifier("facebook/bart-large-mnli")

for text in texts:
    sent_result = sentiment.classify(text)
    topic_result = topic.classify(text)
```

### 3. Multilingual Processing
```python
# Easy language switching
embedder_en = GenericEmbedder("sentence-transformers/all-MiniLM-L6-v2")
embedder_multilingual = GenericEmbedder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Same API, different languages
en_embedding = embedder_en.embed("Hello world")
ml_embedding = embedder_multilingual.embed("Hola mundo")
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/utils/models/ -v

# Run specific test category
python -m pytest tests/utils/models/test_generic.py -v
```

## 🔗 Backward Compatibility

Existing classes like `Embedder` and `VariantRecognizer` have been updated to use the new system while maintaining full backward compatibility.

```python
# Old code still works
from src.analysis.Embedder import Embedder
embedder = Embedder("model-name")
embedding = embedder.embed("text")

# But now uses the new system under the hood!
```

## 📈 Benefits

- ✅ **Zero code duplication** - unified code for all models
- ✅ **Easy model switching** - change models in one line
- ✅ **Provider flexibility** - support for multiple providers
- ✅ **Memory management** - automatic memory management
- ✅ **Error handling** - consistent error handling
- ✅ **Batch processing** - efficient batch processing
- ✅ **Type safety** - full Python typing
- ✅ **Testing coverage** - comprehensive test suite

## 🛠️ Development

To add support for a new model type:

1. Create a new class inheriting from `BaseModelWrapper`
2. Implement required abstract methods
3. Add detection to `ModelFactory`
4. Add tests in `tests/utils/models/`

## 📚 Demo

Run the full system demo:
```bash
PYTHONPATH=/path/to/project python examples/generic_models_usage.py
``` 