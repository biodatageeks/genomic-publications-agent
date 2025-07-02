#!/usr/bin/env python3
"""
Example usage of the new generic model system.

This demonstrates how easy it is to use different types of models
with a unified interface across various tasks.
"""

import numpy as np
from src.utils.models.generic import (
    GenericEmbedder, 
    GenericTokenizer, 
    GenericChat, 
    GenericClassifier
)

def demo_embeddings():
    """Demonstrate text embedding with different models."""
    print("=== EMBEDDINGS DEMO ===")
    
    # HuggingFace embeddings
    print("\n1. HuggingFace Embeddings:")
    embedder = GenericEmbedder("sentence-transformers/all-MiniLM-L6-v2")
    
    text = "This is a sample text for embedding."
    embedding = embedder.embed(text)
    print(f"Text: '{text}'")
    print(f"Embedding shape: {embedding.shape}")
    print(f"First 5 values: {embedding[:5]}")
    
    # Batch embeddings
    texts = ["First text", "Second text", "Third text"]
    batch_embeddings = embedder.embed_batch(texts, batch_size=2)
    print(f"\nBatch embeddings for {len(texts)} texts:")
    for i, emb in enumerate(batch_embeddings):
        print(f"  Text {i+1} embedding shape: {emb.shape}")


def demo_tokenization():
    """Demonstrate text tokenization."""
    print("\n=== TOKENIZATION DEMO ===")
    
    tokenizer = GenericTokenizer("bert-base-uncased")
    
    text = "Hello world, this is a test!"
    tokens = tokenizer.tokenize(text)
    print(f"Text: '{text}'")
    print(f"Tokenization result: {tokens}")
    
    try:
        token_ids = tokenizer.encode(text)
        print(f"Token IDs: {token_ids[:10]}...")  # Show first 10
    except Exception as e:
        print(f"Token ID extraction failed: {e}")


def demo_chat():
    """Demonstrate chat/text generation."""
    print("\n=== CHAT DEMO ===")
    
    # Initialize chat with default LLM
    chat = GenericChat()
    print(f"Using model: {chat.model_name}")
    print(f"Provider: {chat.provider}")
    
    # Simple generation
    prompt = "Complete this sentence: The benefits of artificial intelligence include"
    print(f"\nPrompt: '{prompt}'")
    try:
        response = chat.generate(prompt)
        print(f"Response: {response[:100]}...")  # Show first 100 chars
    except Exception as e:
        print(f"Generation failed: {e}")
    
    # Chat with system prompt  
    print(f"\nChat example:")
    try:
        response = chat.chat(
            "What is machine learning?",
            system_prompt="You are a helpful AI assistant. Give concise answers."
        )
        print(f"Response: {response[:100]}...")
    except Exception as e:
        print(f"Chat failed: {e}")


def demo_classification():
    """Demonstrate text classification."""
    print("\n=== CLASSIFICATION DEMO ===")
    
    classifier = GenericClassifier()
    print(f"Using model: {classifier.model_name}")
    
    # Single text classification
    texts = [
        "I love this product! It's amazing!",
        "This is terrible, I hate it.",
        "It's okay, nothing special."
    ]
    
    print("\nClassifying sentiments:")
    for text in texts:
        try:
            result = classifier.classify(text)
            print(f"Text: '{text}'")
            print(f"  -> {result['label']} (confidence: {result['confidence']:.3f})")
        except Exception as e:
            print(f"Classification failed for '{text}': {e}")
    
    # Show available labels
    try:
        labels = classifier.get_labels()
        print(f"\nAvailable labels: {labels}")
    except Exception as e:
        print(f"Could not get labels: {e}")


def demo_multiple_providers():
    """Demonstrate using different providers for the same task."""
    print("\n=== MULTIPLE PROVIDERS DEMO ===")
    
    # Different embedding models
    embedding_models = [
        ("sentence-transformers/all-MiniLM-L6-v2", None),
        ("text-embedding-3-small", "openai"),  # This would need OpenAI API key
    ]
    
    text = "Sample text for comparison"
    
    for model_name, provider in embedding_models:
        try:
            print(f"\nTrying {model_name} with provider {provider}")
            embedder = GenericEmbedder(model_name, provider=provider)
            embedding = embedder.embed(text)
            print(f"  Success! Embedding shape: {embedding.shape}")
        except Exception as e:
            print(f"  Failed: {e}")


def demo_easy_switching():
    """Demonstrate how easy it is to switch between models."""
    print("\n=== EASY MODEL SWITCHING DEMO ===")
    
    text = "Analyze this text"
    
    # Try different embedding models
    embedding_models = [
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ]
    
    for model in embedding_models:
        try:
            print(f"\nUsing embedding model: {model}")
            embedder = GenericEmbedder(model)
            embedding = embedder.embed(text)
            print(f"  Embedding shape: {embedding.shape}")
            print(f"  Model type: {embedder.model_wrapper.get_model_type()}")
        except Exception as e:
            print(f"  Failed: {e}")


if __name__ == "__main__":
    print("🚀 Generic Model System Demo")
    print("=" * 50)
    
    try:
        demo_embeddings()
        demo_tokenization() 
        demo_classification()
        demo_chat()
        demo_multiple_providers()
        demo_easy_switching()
        
        print("\n" + "=" * 50)
        print("✅ Demo completed successfully!")
        print("\nKey Benefits of the Generic System:")
        print("- 🔄 Easy switching between model types")
        print("- 🏗️  Unified interface for all tasks") 
        print("- 🔌 Multiple provider support")
        print("- 🧠 Automatic model type detection")
        print("- 📦 Clean, intuitive API")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc() 