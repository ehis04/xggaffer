class FootballDataError(Exception):
    pass


class FootballDataRequestError(FootballDataError):
    pass


class FootballDataAuthenticationError(FootballDataRequestError):
    pass


class FootballDataRateLimitError(FootballDataRequestError):
    pass


class FootballDataNotFoundError(FootballDataRequestError):
    pass


class FootballDataMalformedResponseError(FootballDataRequestError):
    pass