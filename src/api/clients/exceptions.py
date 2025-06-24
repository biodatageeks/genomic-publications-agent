"""
Exceptions specific to the ClinVar client.
"""


class ClinVarError(Exception):
    """Base exception class for all errors related to ClinVar API."""
    pass


class APIRequestError(ClinVarError):
    """Exception thrown when an API request fails."""
    
    def __init__(self, message, status_code=None, response_text=None, **kwargs):
        """
        Initialization of APIRequestError exception.
        
        Args:
            message: Error message
            status_code: HTTP response status code
            response_text: HTTP response text
            **kwargs: Additional parameters
        """
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        
        for key, value in kwargs.items():
            setattr(self, key, value)


class InvalidFormatError(ClinVarError):
    """Exception thrown when the requested response format is not supported."""
    pass


class ParseError(ClinVarError):
    """Exception thrown during response parsing errors."""
    pass


class InvalidParameterError(ClinVarError):
    """Exception thrown when the provided parameters are invalid."""
    pass


class RateLimitError(ClinVarError):
    """Exception thrown when the API request limit is exceeded."""
    pass


class FormatNotSupportedException(ClinVarError):
    """Exception thrown when the requested format is not supported."""
    pass


class PubTatorError(Exception):
    """Base exception class for all errors related to PubTator API."""
    pass 