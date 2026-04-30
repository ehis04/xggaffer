"""
Custom exception classes for the Understat provider service layer

Defines provider-specific request, access, rate limit, missing resource, and malformed response errors
"""


# Base exception for all Understat provider errors
class UnderstatError(Exception):
    pass


# Raised when an Understat request fails or returns an unexpected HTTP error
class UnderstatRequestError(UnderstatError):
    pass


# Raised when Understat rejects access to a resource
class UnderstatAuthenticationError(UnderstatRequestError):
    pass


# Raised when Understat throttles or rate-limits requests
class UnderstatRateLimitError(UnderstatRequestError):
    pass


# Raised when a requested Understat resource cannot be found
class UnderstatNotFoundError(UnderstatRequestError):
    pass


# Raised when Understat returns data that cannot be parsed into the expected shape
class UnderstatMalformedResponseError(UnderstatError):
    pass


__all__ = [
    "UnderstatError",
    "UnderstatRequestError",
    "UnderstatAuthenticationError",
    "UnderstatRateLimitError",
    "UnderstatNotFoundError",
    "UnderstatMalformedResponseError",
]