from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pandas as pd

try:
    import soccerdata as sd
except ImportError:
    sd = None


WHOSCORED_LEAGUE_MAP = {
    "EPL": "ENG-Premier League",
    "La_Liga": "ESP-La Liga",
    "Bundesliga": "GER-Bundesliga",
    "Serie_A": "ITA-Serie A",
    "Ligue_1": "FRA-Ligue 1",
    "RFPL": "RUS-Premier League",
}


def _resolve_whoscored_league(league: str) -> str:
    value = str(league).strip()
    return WHOSCORED_LEAGUE_MAP.get(value, value)


def _resolve_whoscored_season(season: str | int) -> str | int:
    value = str(season).strip()

    if value.isdigit() and len(value) == 4:
        return int(value)

    if "-" in value and value[:4].isdigit():
        return int(value[:4])

    if "/" in value and value[:4].isdigit():
        return int(value[:4])

    return value


def _materialize_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.MultiIndex):
        return df.reset_index()

    if any(name is not None for name in df.index.names):
        return df.reset_index()

    return df.copy()


def get_whoscored_client(
    league: str,
    season: str | int,
    *,
    no_cache: bool = False,
    no_store: bool = False,
    data_dir: str | Path | None = None,
):
    if sd is None:
        raise ImportError(
            "soccerdata is not installed. Install it with `pip install soccerdata`."
        )

    kwargs: dict[str, object] = {
        "leagues": [_resolve_whoscored_league(league)],
        "seasons": [_resolve_whoscored_season(season)],
        "no_cache": no_cache,
        "no_store": no_store,
    }

    if data_dir is not None:
        kwargs["data_dir"] = Path(data_dir)

    return _make_whoscored_client(**kwargs)


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as fh:
            return "microsoft" in fh.read().lower()
    except OSError:
        return False


def _start_xvfb(display: int = 99) -> subprocess.Popen | None:
    try:
        proc = subprocess.Popen(
            ["Xvfb", f":{display}", "-screen", "0", "1280x720x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
        return proc
    except FileNotFoundError:
        return None


def _make_whoscored_client(**kwargs):
    if not _is_wsl():
        return sd.WhoScored(**kwargs)

    try:
        import seleniumbase as sb
    except ImportError:
        return sd.WhoScored(**kwargs)

    xvfb_proc = None
    display = os.environ.get("DISPLAY", "")
    if not display:
        xvfb_proc = _start_xvfb(display=99)
        if xvfb_proc is not None:
            os.environ["DISPLAY"] = ":99"

    import io as _io
    import json as _json

    class _WSLWhoScored(sd.WhoScored):
        _xvfb_proc = xvfb_proc

        @classmethod
        def _all_leagues(cls):
            return sd.WhoScored._all_leagues()

        def _init_webdriver(self):
            if hasattr(self, "_driver"):
                self._driver.quit()
            proxy_str = self.proxy() if callable(getattr(self, "proxy", None)) else None
            use_headless = self._xvfb_proc is None and not os.environ.get("DISPLAY")
            return sb.Driver(
                uc=True,
                headless2=use_headless,
                binary_location=self.path_to_browser,
                host_resolver_rules="MAP * ~NOTFOUND , EXCLUDE 127.0.0.1" if proxy_str else None,
                proxy=proxy_str,
            )

        def _download_and_save(self, url, filepath=None, var=None):
            if "/data/?d=" not in url:
                return super()._download_and_save(url, filepath, var)

            for attempt in range(5):
                try:
                    current = self._driver.current_url or ""
                    if "whoscored.com" not in current:
                        self._driver.get("https://www.whoscored.com/")
                        time.sleep(3)

                    raw = self._driver.execute_async_script(
                        """
                        var cb = arguments[arguments.length - 1];
                        fetch(arguments[0], {credentials: 'include'})
                            .then(function(r){ return r.text(); })
                            .then(function(t){ cb(t); })
                            .catch(function(){ cb(''); });
                        """,
                        url,
                    )
                    if not raw:
                        raise ValueError("Empty fetch response")
                    _json.loads(raw)
                    data = raw.encode("utf-8")
                    if filepath is not None and not self.no_store:
                        filepath.parent.mkdir(parents=True, exist_ok=True)
                        filepath.write_bytes(data)
                    return _io.BytesIO(data)
                except Exception:
                    time.sleep(attempt * 10)
                    self._driver = self._init_webdriver()
            raise ConnectionError(f"Could not download {url}")

    return _WSLWhoScored(**kwargs)


def fetch_whoscored_matches(
    league: str,
    season: str | int,
    *,
    force_cache: bool = False,
    no_cache: bool = False,
    no_store: bool = False,
    data_dir: str | Path | None = None,
) -> pd.DataFrame:
    client = get_whoscored_client(
        league,
        season,
        no_cache=no_cache,
        no_store=no_store,
        data_dir=data_dir,
    )

    raw_df = client.read_schedule(force_cache=force_cache)

    if not isinstance(raw_df, pd.DataFrame):
        raise TypeError(
            f"WhoScored read_schedule() returned unsupported type: {type(raw_df)!r}"
        )

    return _materialize_index(raw_df)


__all__ = [
    "WHOSCORED_LEAGUE_MAP",
    "fetch_whoscored_matches",
    "get_whoscored_client",
]
