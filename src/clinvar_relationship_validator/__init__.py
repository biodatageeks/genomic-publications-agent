"""
ClinVar Relationship Validator - moduł do weryfikacji relacji genów, wariantów i chorób.

Ten moduł umożliwia weryfikację relacji wykrytych przez analizator współwystępowania
(CooccurrenceContextAnalyzer) przy użyciu danych klinicznych z bazy ClinVar.
"""

from .clinvar_relationship_validator import ClinvarRelationshipValidator
from .validation_report import ValidationReport
from .exceptions import ValidationError

__all__ = ['ClinvarRelationshipValidator', 'ValidationReport', 'ValidationError'] 