from __future__ import annotations

import urllib.request
import urllib.error
from pathlib import Path

from apps.predictions.ml.models.match_outcome.config import DATA_DIR


RAW_ODDS_DIR = DATA_DIR / "raw" / "football_data_co_uk"

BASE_URL = "https://www.football-data.co.uk/mmz4281"

UNDERSTAT_TO_FDCOUK_SEASON = {
    "2014": "1415",
    "2015": "1516",
    "2016": "1617",
    "2017": "1718",
    "2018": "1819",
    "2019": "1920",
    "2020": "2021",
    "2021": "2122",
    "2022": "2223",
    "2023": "2324",
    "2024": "2425",
    "2025": "2526",
}

LEAGUE_TO_FDCOUK_CODE = {
    "EPL": "E0",
    "La_Liga": "SP1",
    "Bundesliga": "D1",
    "Serie_A": "I1",
    "Ligue_1": "F1",
}

ALL_LEAGUES = list(LEAGUE_TO_FDCOUK_CODE.keys())
ALL_SEASONS = list(UNDERSTAT_TO_FDCOUK_SEASON.keys())


def build_url(league: str, season: str) -> str:
    fdcouk_season = UNDERSTAT_TO_FDCOUK_SEASON[season]
    league_code = LEAGUE_TO_FDCOUK_CODE[league]
    return f"{BASE_URL}/{fdcouk_season}/{league_code}.csv"


def build_output_path(league: str, season: str) -> Path:
    return RAW_ODDS_DIR / f"{league}_{season}_odds.csv"


def download_one(league: str, season: str, overwrite: bool = False) -> Path:
    url = build_url(league, season)
    output_path = build_output_path(league, season)

    if output_path.exists() and not overwrite:
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "xgGaffer-academic-project/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()

    output_path.write_bytes(content)
    return output_path


def download_all(
    leagues: list[str] | None = None,
    seasons: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, list]:
    leagues = leagues or ALL_LEAGUES
    seasons = seasons or ALL_SEASONS

    results: dict[str, list] = {"downloaded": [], "skipped": [], "failed": []}

    for league in leagues:
        if league not in LEAGUE_TO_FDCOUK_CODE:
            print(f"  SKIP: Unknown league '{league}'")
            results["skipped"].append((league, None, "unknown league"))
            continue

        for season in seasons:
            if season not in UNDERSTAT_TO_FDCOUK_SEASON:
                print(f"  SKIP: Unknown season '{season}'")
                results["skipped"].append((league, season, "unknown season"))
                continue

            output_path = build_output_path(league, season)
            if output_path.exists() and not overwrite:
                results["skipped"].append((league, season, "already exists"))
                continue

            try:
                path = download_one(league, season, overwrite=overwrite)
                size_kb = path.stat().st_size / 1024
                print(f"  OK: {league} {season} ({size_kb:.1f} KB)")
                results["downloaded"].append((league, season, str(path)))
            except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
                print(f"  FAIL: {league} {season} — {exc}")
                results["failed"].append((league, season, str(exc)))

    total = len(results["downloaded"])
    skipped = len(results["skipped"])
    failed = len(results["failed"])
    print(f"\nSummary: {total} downloaded, {skipped} skipped, {failed} failed")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download football-data.co.uk odds CSVs")
    parser.add_argument("--leagues", nargs="+", default=ALL_LEAGUES)
    parser.add_argument("--seasons", nargs="+", default=ALL_SEASONS)
    parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()

    print(f"Downloading odds data to {RAW_ODDS_DIR}")
    print(f"Leagues: {args.leagues}")
    print(f"Seasons: {args.seasons}")
    print()

    download_all(
        leagues=args.leagues,
        seasons=args.seasons,
        overwrite=args.overwrite,
    )