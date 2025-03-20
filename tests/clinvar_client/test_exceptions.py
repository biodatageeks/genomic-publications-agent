"""
Testy dla wyjątków klienta ClinVar.
"""

import pytest

from src.clinvar_client.exceptions import (
    ClinVarError,
    APIRequestError,
    InvalidFormatError,
    ParseError,
    InvalidParameterError,
    RateLimitError
)


class TestExceptions:
    """
    Testy dla klas wyjątków zdefiniowanych dla klienta ClinVar.
    """

    def test_clinvar_error_base_class(self):
        """
        Test weryfikujący, że ClinVarError jest podstawową klasą wyjątku.
        """
        error = ClinVarError("Ogólny błąd ClinVar")
        assert isinstance(error, Exception)
        assert str(error) == "Ogólny błąd ClinVar"

    def test_api_request_error(self):
        """
        Test weryfikujący klasę wyjątku APIRequestError.
        """
        error = APIRequestError("Błąd zapytania API")
        assert isinstance(error, ClinVarError)
        assert str(error) == "Błąd zapytania API"

    def test_invalid_format_error(self):
        """
        Test weryfikujący klasę wyjątku InvalidFormatError.
        """
        error = InvalidFormatError("Niewspierany format")
        assert isinstance(error, ClinVarError)
        assert str(error) == "Niewspierany format"

    def test_parse_error(self):
        """
        Test weryfikujący klasę wyjątku ParseError.
        """
        error = ParseError("Błąd parsowania danych")
        assert isinstance(error, ClinVarError)
        assert str(error) == "Błąd parsowania danych"

    def test_invalid_parameter_error(self):
        """
        Test weryfikujący klasę wyjątku InvalidParameterError.
        """
        error = InvalidParameterError("Nieprawidłowy parametr")
        assert isinstance(error, ClinVarError)
        assert str(error) == "Nieprawidłowy parametr"

    def test_rate_limit_error(self):
        """
        Test weryfikujący klasę wyjątku RateLimitError.
        """
        error = RateLimitError("Przekroczono limit zapytań")
        assert isinstance(error, ClinVarError)
        assert str(error) == "Przekroczono limit zapytań"

    def test_exception_hierarchy(self):
        """
        Test weryfikujący hierarchię wyjątków.
        """
        exceptions = [
            APIRequestError("Test"),
            InvalidFormatError("Test"),
            ParseError("Test"),
            InvalidParameterError("Test"),
            RateLimitError("Test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, ClinVarError)
            assert isinstance(exc, Exception)

    def test_catching_specific_exceptions(self):
        """
        Test weryfikujący możliwość łapania konkretnych wyjątków.
        """
        try:
            raise APIRequestError("Test API error")
        except APIRequestError as e:
            assert str(e) == "Test API error"
        except ClinVarError:
            pytest.fail("Nie powinno trafić tutaj")
            
        try:
            raise InvalidFormatError("Test format error")
        except InvalidFormatError as e:
            assert str(e) == "Test format error"
        except ClinVarError:
            pytest.fail("Nie powinno trafić tutaj")

    def test_catching_base_exception(self):
        """
        Test weryfikujący możliwość łapania wszystkich wyjątków ClinVar
        przy użyciu bazowej klasy ClinVarError.
        """
        exceptions = [
            APIRequestError("API error"),
            InvalidFormatError("Format error"),
            ParseError("Parse error"),
            InvalidParameterError("Parameter error"),
            RateLimitError("Rate limit error")
        ]
        
        for expected_exc in exceptions:
            try:
                raise expected_exc
            except ClinVarError as e:
                assert str(e) == str(expected_exc)
                assert type(e) == type(expected_exc)

    def test_custom_exception_attributes(self):
        """
        Test weryfikujący, że wyjątki mogą mieć dodatkowe atrybuty.
        """
        response_status = 404
        response_text = "Not found"
        
        error = APIRequestError(
            "API request failed",
            status_code=response_status,
            response_text=response_text
        )
        
        assert hasattr(error, "status_code")
        assert hasattr(error, "response_text")
        assert error.status_code == response_status
        assert error.response_text == response_text 