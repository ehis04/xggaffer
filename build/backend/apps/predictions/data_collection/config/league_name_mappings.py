CANONICAL_LEAGUE_NAMES = {
    "EPL": {
        "understat": "EPL",
        "sofascore": "ENG-Premier League",
        "football_data_co_uk": "E0",
        "football_data_org": "PL",
    },
    "La_Liga": {
        "understat": "La_Liga",
        "sofascore": "ESP-La Liga",
        "football_data_co_uk": "SP1",
        "football_data_org": "PD",
    },
    "Bundesliga": {
        "understat": "Bundesliga",
        "sofascore": "GER-Bundesliga",
        "football_data_co_uk": "D1",
        "football_data_org": "BL1",
    },
    "Serie_A": {
        "understat": "Serie_A",
        "sofascore": "ITA-Serie A",
        "football_data_co_uk": "I1",
        "football_data_org": "SA",
    },
    "Ligue_1": {
        "understat": "Ligue_1",
        "sofascore": "FRA-Ligue 1",
        "football_data_co_uk": "F1",
        "football_data_org": "FL1",
    },
}

SUPPORTED_SOURCES = ["understat", "sofascore", "football_data_co_uk", "football_data_org"]


def _build_reverse_index(source):
    return {
        names[source]: canonical
        for canonical, names in CANONICAL_LEAGUE_NAMES.items()
        if source in names
    }


_reverse_cache = {}


def to_canonical(source_name, source):
    if source not in _reverse_cache:
        _reverse_cache[source] = _build_reverse_index(source)

    index = _reverse_cache[source]
    if source_name not in index:
        raise KeyError(
            f"Unknown league '{source_name}' for source '{source}'. "
            f"Known: {list(index.keys())}"
        )
    return index[source_name]


def from_canonical(canonical_name, source):
    if canonical_name not in CANONICAL_LEAGUE_NAMES:
        raise KeyError(
            f"Unknown canonical league '{canonical_name}'. "
            f"Known: {list(CANONICAL_LEAGUE_NAMES.keys())}"
        )

    names = CANONICAL_LEAGUE_NAMES[canonical_name]
    if source not in names:
        raise KeyError(
            f"Source '{source}' not mapped for league '{canonical_name}'. "
            f"Mapped sources: {list(names.keys())}"
        )
    return names[source]