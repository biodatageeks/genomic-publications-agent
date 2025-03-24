"""
ClinVar Relationship Validator - module for verifying relationships between genes, variants, and diseases.

This module allows verification of relationships detected by the CooccurrenceContextAnalyzer
using clinical data from the ClinVar database.
"""

from .clinvar_relationship_validator import ClinvarRelationshipValidator
from .validation_report import ValidationReport
from .exceptions import ValidationError

__all__ = ['ClinvarRelationshipValidator', 'ValidationReport', 'ValidationError'] 