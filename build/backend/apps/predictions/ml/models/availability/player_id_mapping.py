from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

from apps.predictions.ml.models.availability.config import (
    DEFAULT_SEASONS,
    LEAGUES,
    MIN_FUZZY_MATCH_SCORE,
    MIN_TEAM_FUZZY_MATCH_SCORE,
    PLAYER_ID_MAPPING_PATH,
    TEAM_ID_MAPPING_PATH,
    UNDERSTAT_PLAYERS_PATH,
    UNDERSTAT_SOURCE_FILTER,
)
from services.providers.transfermarkt.client import TransfermarktClient, TransfermarktError

logger = logging.getLogger(__name__)

HTML_ENTITY_APOS = "&#039;"
UNICODE_APOS = "'"
MULTISPACE_PATTERN = re.compile(r"\s+")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")

FIRST_NAME_ALIASES = {
    "eddie": ("edward",),
}

TEAM_NAME_ALIASES = {
    "1 fc koln": "FC Cologne",
    "stade rennais fc": "Rennes",
}


def load_understat_players(understat_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(understat_csv)
    df = df[df["source"] == UNDERSTAT_SOURCE_FILTER].copy()
    df = df[["source_player_id", "name", "team", "league", "season"]].copy()
    df = df.rename(columns={"source_player_id": "player_id"})
    df["name_clean"] = df["name"].apply(_clean_name)
    df["name_match_key"] = df["name_clean"].apply(_to_match_key)
    return df


def _clean_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return name.replace(HTML_ENTITY_APOS, UNICODE_APOS).strip()


def _to_match_key(name: str) -> str:
    cleaned = _clean_name(name)
    normalized = unicodedata.normalize("NFKD", cleaned)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    normalized_punct = NON_ALNUM_PATTERN.sub(" ", lowered)
    return MULTISPACE_PATTERN.sub(" ", normalized_punct).strip()


def match_tm_team_to_understat(
    tm_team_name: str,
    understat_teams: list[str],
) -> Optional[tuple[str, float]]:
    if not tm_team_name or not understat_teams:
        return None

    tm_key = _to_match_key(tm_team_name)
    understat_team_by_key = {_to_match_key(team_name): team_name for team_name in understat_teams}

    alias_target = TEAM_NAME_ALIASES.get(tm_key)
    if alias_target is not None:
        matched_team = understat_team_by_key.get(_to_match_key(alias_target))
        if matched_team is not None:
            return matched_team, 100

    us_keys = [_to_match_key(t) for t in understat_teams]

    result = process.extractOne(
        tm_key,
        us_keys,
        scorer=fuzz.WRatio,
        score_cutoff=MIN_TEAM_FUZZY_MATCH_SCORE,
    )
    if result is None:
        return None

    _, score, idx = result
    return understat_teams[idx], score


def build_team_mapping_for_league_season(
    league: str,
    season: int,
    understat_players: pd.DataFrame,
    client: TransfermarktClient,
) -> list[dict]:
    us_teams_this = understat_players[
        (understat_players["league"] == league)
        & (understat_players["season"] == season)
    ]["team"].dropna().unique().tolist()

    if not us_teams_this:
        logger.warning("No Understat teams for league=%s season=%d", league, season)
        return []

    tm_teams = client.fetch_league_teams(league=league, season=season)
    if not tm_teams:
        logger.warning("No TM teams for league=%s season=%d", league, season)
        return []

    results: list[dict] = []
    for tm_team in tm_teams:
        match = match_tm_team_to_understat(tm_team["tm_team_name"], us_teams_this)
        results.append({
            "league": league,
            "season": season,
            "tm_team_id": tm_team["tm_team_id"],
            "tm_team_name": tm_team["tm_team_name"],
            "understat_team_name": match[0] if match else None,
            "team_match_score": int(match[1]) if match else 0,
        })

    return results


def build_mapping_for_team(
    tm_team_id: int,
    understat_team_name: str,
    season: int,
    understat_players: pd.DataFrame,
    client: TransfermarktClient,
    league: str = "EPL",
) -> list[dict]:
    candidates = understat_players[
        (understat_players["team"] == understat_team_name)
        & (understat_players["season"] == season)
        & (understat_players["league"] == league)
    ]

    if candidates.empty:
        logger.warning("No Understat players for team=%s season=%d", understat_team_name, season)
        return []

    soup = client.fetch_squad_page(tm_team_id=tm_team_id, season=season)
    tm_squad = client.parse_squad(soup)

    if not tm_squad:
        logger.warning("Empty TM squad for team_id=%d season=%d", tm_team_id, season)
        return []

    candidates = candidates.reset_index(drop=True).copy()
    if "name_match_key" not in candidates.columns:
        candidates["name_match_key"] = candidates["name_clean"].apply(_to_match_key)

    candidate_records = [
        {
            "index": row.Index,
            "player_id": int(row.player_id),
            "name_clean": row.name_clean,
            "name_match_key": row.name_match_key,
        }
        for row in candidates[["player_id", "name_clean", "name_match_key"]].itertuples(index=True)
    ]

    matched_candidate_indexes: set[int] = set()
    team_matches: list[Optional[tuple[dict, int]]] = [None] * len(tm_squad)

    for index, tm_player in enumerate(tm_squad):
        exact_match = _find_exact_match(tm_player, candidate_records, matched_candidate_indexes)
        if exact_match is None:
            continue
        team_matches[index] = exact_match
        matched_candidate_indexes.add(exact_match[0]["index"])

    for index, tm_player in enumerate(tm_squad):
        if team_matches[index] is not None:
            continue
        fuzzy_match = _find_best_available_match(tm_player, candidate_records, matched_candidate_indexes)
        if fuzzy_match is None:
            continue
        team_matches[index] = fuzzy_match
        matched_candidate_indexes.add(fuzzy_match[0]["index"])

    results: list[dict] = []
    for index, tm_player in enumerate(tm_squad):
        tm_name = _clean_name(tm_player["player_name"])
        match = team_matches[index]

        if match is None:
            results.append({
                "tm_player_id": tm_player["tm_player_id"],
                "understat_player_id": None,
                "tm_name": tm_name,
                "understat_name": None,
                "team": understat_team_name,
                "league": league,
                "season": season,
                "match_score": 0,
                "tm_team_id": tm_team_id,
            })
            continue

        matched_candidate, score = match
        results.append({
            "tm_player_id": tm_player["tm_player_id"],
            "understat_player_id": matched_candidate["player_id"],
            "tm_name": tm_name,
            "understat_name": matched_candidate["name_clean"],
            "team": understat_team_name,
            "league": league,
            "season": season,
            "match_score": int(score),
            "tm_team_id": tm_team_id,
        })

    return results


def _best_fuzzy_match(
    query: str,
    candidates: list[str],
) -> Optional[tuple[str, float, int]]:
    if not query or not candidates:
        return None

    result = process.extractOne(
        query,
        candidates,
        scorer=fuzz.WRatio,
        score_cutoff=MIN_FUZZY_MATCH_SCORE,
    )
    return result


def _find_exact_match(
    tm_player: dict,
    candidates: list[dict],
    matched_candidate_indexes: set[int],
) -> Optional[tuple[dict, int]]:
    for variant_key in _iter_tm_variant_keys(tm_player):
        exact_candidates = [
            candidate
            for candidate in candidates
            if candidate["index"] not in matched_candidate_indexes
            and candidate["name_match_key"] == variant_key
        ]
        if len(exact_candidates) == 1:
            return exact_candidates[0], 100
    return None


def _find_best_available_match(
    tm_player: dict,
    candidates: list[dict],
    matched_candidate_indexes: set[int],
) -> Optional[tuple[dict, int]]:
    remaining_candidates = [
        candidate for candidate in candidates if candidate["index"] not in matched_candidate_indexes
    ]
    if not remaining_candidates:
        return None

    remaining_keys = [candidate["name_match_key"] for candidate in remaining_candidates]
    best_candidate: Optional[dict] = None
    best_score = -1.0

    for variant_key in _iter_tm_variant_keys(tm_player):
        match = _best_fuzzy_match(variant_key, remaining_keys)
        if match is None:
            continue
        _, score, match_index = match
        if score > best_score:
            best_candidate = remaining_candidates[match_index]
            best_score = score

    if best_candidate is None:
        return None

    return best_candidate, int(best_score)


def _iter_tm_variant_keys(tm_player: dict) -> list[str]:
    variant_keys: list[str] = []
    seen: set[str] = set()

    raw_names = [tm_player.get("player_name"), _slug_to_name(tm_player.get("player_slug"))]
    for raw_name in raw_names:
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        for expanded_name in _expand_name_aliases(raw_name):
            match_key = _to_match_key(expanded_name)
            if not match_key or match_key in seen:
                continue
            seen.add(match_key)
            variant_keys.append(match_key)

    return variant_keys


def _slug_to_name(slug: Optional[str]) -> str:
    if not isinstance(slug, str):
        return ""
    return slug.replace("-", " ").strip()


def _expand_name_aliases(name: str) -> list[str]:
    match_key = _to_match_key(name)
    if not match_key:
        return []

    parts = match_key.split()
    variants = [match_key]
    aliases = FIRST_NAME_ALIASES.get(parts[0], ())
    for alias in aliases:
        variants.append(" ".join([alias, *parts[1:]]).strip())
    return variants


def build_full_mapping(
    leagues: list[str] | None = None,
    seasons: list[int] | None = None,
    output_path: Path = PLAYER_ID_MAPPING_PATH,
    team_mapping_path: Path = TEAM_ID_MAPPING_PATH,
) -> pd.DataFrame:
    leagues = leagues or LEAGUES
    seasons = seasons or DEFAULT_SEASONS

    understat_players = load_understat_players(UNDERSTAT_PLAYERS_PATH)

    all_team_mappings: list[dict] = []
    all_player_mappings: list[dict] = []
    team_fetch_failures: list[dict] = []

    with TransfermarktClient() as client:
        for league in leagues:
            for season in seasons:
                logger.info("=== %s %d ===", league, season)

                team_results = build_team_mapping_for_league_season(
                    league=league,
                    season=season,
                    understat_players=understat_players,
                    client=client,
                )
                all_team_mappings.extend(team_results)

                matched_teams = [
                    t for t in team_results if t["understat_team_name"] is not None
                ]
                logger.info(
                    "Matched %d/%d teams for %s %d",
                    len(matched_teams), len(team_results), league, season,
                )

                for team_map in matched_teams:
                    try:
                        player_results = build_mapping_for_team(
                            tm_team_id=team_map["tm_team_id"],
                            understat_team_name=team_map["understat_team_name"],
                            season=season,
                            understat_players=understat_players,
                            client=client,
                            league=league,
                        )
                        all_player_mappings.extend(player_results)
                    except TransfermarktError as exc:
                        team_fetch_failures.append(
                            {
                                "league": league,
                                "season": season,
                                "tm_team_id": team_map["tm_team_id"],
                                "tm_team_name": team_map["tm_team_name"],
                                "understat_team_name": team_map["understat_team_name"],
                                "error": str(exc),
                            }
                        )
                        logger.exception(
                            "Skipping team after Transfermarkt error: league=%s season=%d tm_team_id=%s tm_team_name=%s",
                            league,
                            season,
                            team_map["tm_team_id"],
                            team_map["tm_team_name"],
                        )

    team_df = pd.DataFrame(all_team_mappings)
    team_mapping_path.parent.mkdir(parents=True, exist_ok=True)
    team_df.to_csv(team_mapping_path, index=False)
    logger.info("Saved team mapping: %s (%d rows)", team_mapping_path, len(team_df))

    player_df = pd.DataFrame(all_player_mappings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    player_df.to_csv(output_path, index=False)
    logger.info("Saved player mapping: %s (%d rows)", output_path, len(player_df))

    if team_fetch_failures:
        logger.warning(
            "Completed with %d team fetch failures. First failure: %s",
            len(team_fetch_failures),
            team_fetch_failures[0],
        )

    return player_df


def print_mapping_summary(df: pd.DataFrame) -> None:
    total = len(df)
    matched = df["understat_player_id"].notna().sum()
    match_rate = matched / total if total > 0 else 0

    print(f"Total TM players: {total}")
    print(f"Matched: {matched} ({match_rate:.1%})")
    print(f"Unmatched: {total - matched}")
    print()

    print("Per-league match rates:")
    per_league = df.groupby("league").agg(
        total=("tm_player_id", "count"),
        matched=("understat_player_id", lambda s: s.notna().sum()),
    )
    per_league["rate"] = per_league["matched"] / per_league["total"]
    print(per_league.to_string())
    print()


def print_coverage_report(
    player_mapping_path: Path = PLAYER_ID_MAPPING_PATH,
    understat_csv: Path = UNDERSTAT_PLAYERS_PATH,
) -> None:
    mapping = pd.read_csv(player_mapping_path)
    understat = pd.read_csv(understat_csv)
    understat = understat[understat["source"] == UNDERSTAT_SOURCE_FILTER]

    matched_us_ids = set(
        mapping[mapping["understat_player_id"].notna()]["understat_player_id"].astype(int)
    )

    print(f"{'League':<15} {'US total':>9} {'Matched':>8} {'Coverage':>10}")
    print("-" * 45)
    overall_total = 0
    overall_matched = 0
    for league in sorted(understat["league"].unique()):
        league_us = understat[understat["league"] == league]
        us_ids = set(league_us["source_player_id"].astype(int))
        covered = len(us_ids & matched_us_ids)
        total = len(us_ids)
        overall_total += total
        overall_matched += covered
        pct = covered / total if total > 0 else 0
        print(f"{league:<15} {total:>9} {covered:>8} {pct:>9.1%}")

    print("-" * 45)
    pct = overall_matched / overall_total if overall_total > 0 else 0
    print(f"{'OVERALL':<15} {overall_total:>9} {overall_matched:>8} {pct:>9.1%}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    df = build_full_mapping()
    print_mapping_summary(df)
    print_coverage_report()