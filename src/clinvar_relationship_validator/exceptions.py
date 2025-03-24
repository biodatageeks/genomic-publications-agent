"""
Exceptions for the ClinVar Relationship Validator module.

This module defines custom exceptions used in the clinvar_relationship_validator
module to handle various error situations.
"""


class ValidationError(Exception):
    """
    Base exception for relationship validation errors.
    
    Raised when an error occurs during the process of validating genetic
    relationships using the ClinVar API.
    """
    pass 