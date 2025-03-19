"""
Exceptions for the PubTator client.

This module contains custom exceptions used by the PubTator client.
"""


class FormatNotSupportedException(Exception):
    """Exception raised when a requested format is not fully supported."""
    pass 