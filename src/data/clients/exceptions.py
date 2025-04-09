"""
Exceptions for API clients.

This module contains custom exceptions that can be raised by API clients
when interacting with external services.
"""


class APIClientError(Exception):
    """Base exception for all API client errors."""
    pass


class PubTatorError(APIClientError):
    """
    Exception raised for errors related to the PubTator API.
    
    This can include connection errors, authentication errors,
    parsing errors, or any other issues when interacting with
    the PubTator service.
    """
    pass


class CacheError(Exception):
    """
    Exception raised for errors related to caching operations.
    
    This can include issues with reading from or writing to
    the cache, invalid cache data, or cache configuration errors.
    """
    pass


class LLMError(APIClientError):
    """
    Exception raised for errors related to Language Model APIs.
    
    This can include connection errors, authentication errors,
    quota exceeded errors, or issues with parsing responses from
    LLM services like OpenAI or TogetherAI.
    """
    pass 