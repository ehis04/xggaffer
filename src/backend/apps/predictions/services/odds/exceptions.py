from __future__ import annotations


class OddsServiceError(Exception):
    pass


class OddsSourceError(OddsServiceError):
    pass


class OddsMatchingError(OddsServiceError):
    pass


class OddsDataUnavailableError(OddsServiceError):
    pass


class OddsConfigurationError(OddsServiceError):
    pass


class OddsPersistenceError(OddsServiceError):
    pass