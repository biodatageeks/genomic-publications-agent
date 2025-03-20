"""
Wyjątki dla modułu ClinVar Relationship Validator.

Ten moduł definiuje niestandardowe wyjątki używane w module
clinvar_relationship_validator do obsługi różnych sytuacji błędów.
"""


class ValidationError(Exception):
    """
    Podstawowy wyjątek dla błędów walidacji relacji.
    
    Zgłaszany, gdy wystąpi błąd podczas procesu walidacji relacji
    genetycznych przy użyciu API ClinVar.
    """
    pass 