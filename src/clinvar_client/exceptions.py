"""
Wyjątki specyficzne dla klienta ClinVar.
"""


class ClinVarError(Exception):
    """Podstawowa klasa wyjątku dla wszystkich błędów związanych z ClinVar API."""
    pass


class APIRequestError(ClinVarError):
    """Wyjątek rzucany, gdy zapytanie API nie powiedzie się."""
    
    def __init__(self, message, status_code=None, response_text=None, **kwargs):
        """
        Inicjalizacja wyjątku APIRequestError.
        
        Args:
            message: Komunikat błędu
            status_code: Kod statusu odpowiedzi HTTP
            response_text: Treść odpowiedzi HTTP
            **kwargs: Dodatkowe parametry
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        
        for key, value in kwargs.items():
            setattr(self, key, value)


class InvalidFormatError(ClinVarError):
    """Wyjątek rzucany, gdy żądany format odpowiedzi nie jest obsługiwany."""
    pass


class ParseError(ClinVarError):
    """Wyjątek rzucany przy błędach parsowania odpowiedzi."""
    pass


class InvalidParameterError(ClinVarError):
    """Wyjątek rzucany, gdy podane parametry są nieprawidłowe."""
    pass


class RateLimitError(ClinVarError):
    """Wyjątek rzucany przy przekroczeniu limitu zapytań do API."""
    pass 