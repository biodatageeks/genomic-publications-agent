"""
Exceptions for the PubTator client.

This module contains custom exceptions used by the PubTator client.
"""


class PubTatorError(Exception):
    """Base exception for all PubTator client errors."""
    pass


class FormatNotSupportedException(PubTatorError):
    """Exception raised when a requested format is not fully supported."""
    pass 