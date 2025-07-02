"""
Generic model utilities for different use cases.

This module provides unified interfaces for common NLP tasks regardless of 
the underlying model type (HuggingFace, OpenAI, etc.).
"""

from .embedder import GenericEmbedder
from .tokenizer import GenericTokenizer
from .chat import GenericChat
from .classifier import GenericClassifier

__all__ = [
    'GenericEmbedder',
    'GenericTokenizer', 
    'GenericChat',
    'GenericClassifier'
] 