class UnderstatError(Exception):
    """Base exception for all Understat provider errors."""


class UnderstatRequestError(UnderstatError):
    """Raised when an Understat request fails or returns an unexpected HTTP-level error."""


class UnderstatAuthenticationError(UnderstatRequestError):
    """Raised when Understat access is rejected due to authentication or authorisation issues."""


class UnderstatRateLimitError(UnderstatRequestError):
    """Raised when Understat throttles or rate-limits requests."""


class UnderstatNotFoundError(UnderstatRequestError):
    """Raised when a requested Understat resource cannot be found."""


class UnderstatMalformedResponseError(UnderstatError):
    """Raised when Understat returns data that cannot be parsed into the expected shape."""