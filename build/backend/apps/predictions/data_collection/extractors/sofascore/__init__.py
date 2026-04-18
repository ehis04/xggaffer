# Sofascore (via soccerdata) returns some historic La_Liga seasons with a leading
# space (e.g. ' 72/73'). The upstream SeasonCode.parse() has no strip(), so the
# pattern match fails with "Unrecognized season code". Patch it once at import time.
try:
    from soccerdata._common import SeasonCode

    _orig_season_parse = SeasonCode.parse

    def _patched_season_parse(self, season):  # type: ignore[override]
        if isinstance(season, str):
            season = season.strip()
        return _orig_season_parse(self, season)

    SeasonCode.parse = _patched_season_parse  # type: ignore[method-assign]
except Exception:
    pass
