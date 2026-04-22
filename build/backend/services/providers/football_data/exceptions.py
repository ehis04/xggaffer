"""
Custom exception classes for the football-data provider service layer.

Defines provider-specific request and response errors raised by the football-data client and related service helpers.
"""

# Base exception for all football-data client errors
class FootballDataError(Exception):
    pass


# Raised when a football-data request fails
class FootballDataRequestError(FootballDataError):
    pass


# Raised when authentication with football-data fails
class FootballDataAuthenticationError(FootballDataRequestError):
    pass


# Raised when the football-data rate limit is exceeded
class FootballDataRateLimitError(FootballDataRequestError):
    pass


# Raised when a football-data resource cannot be found
class FootballDataNotFoundError(FootballDataRequestError):
    pass


# Raised when football-data returns an invalid response format
class FootballDataMalformedResponseError(FootballDataRequestError):
    pass