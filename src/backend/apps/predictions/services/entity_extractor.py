from __future__ import annotations

import logging
import re

import pandas as pd
from rapidfuzz import fuzz, process

from apps.predictions.data_paths import PROCESSED_DATA_ROOT
from apps.predictions.services.intent_types import IntentClass
from apps.predictions.services.source_policy import season_group_key

logger = logging.getLogger(__name__)

FUZZY_THRESHOLD = 75
MAX_TEAMS_PER_QUERY = 2
MIN_SEASON = 2014
MAX_SEASON = 2026

TEAM_TOKEN_STOP_WORDS: frozenset[str] = frozenset({
    "fc", "cf", "sc", "ac", "as", "afc", "club", "football",
})

TEAM_ALIASES: dict[str, tuple[str, ...]] = {
    "barca": ("Barcelona", "FC Barcelona"),
    "man city": ("Manchester City",),
    "city": ("Manchester City",),
    "mci": ("Manchester City",),
    "man united": ("Manchester United",),
    "man utd": ("Manchester United",),
    "man u": ("Manchester United",),
    "mu": ("Manchester United",),
    "utd": ("Manchester United",),
    "liverpool": ("Liverpool",),
    "liv": ("Liverpool",),
    "spurs": ("Tottenham Hotspur", "Tottenham"),
    "tottenham": ("Tottenham Hotspur", "Tottenham"),
    "ars": ("Arsenal",),
    "che": ("Chelsea",),
    "cfc": ("Chelsea",),
    "psg": ("PSG", "Paris Saint Germain"),
    "dortmund": ("Borussia Dortmund",),
    "bayern": ("Bayern Munich",),
    "inter": ("Inter", "Inter Milan"),
    "milan": ("Milan", "AC Milan"),
    "ac milan": ("Milan", "AC Milan"),
    "juve": ("Juventus",),
    "real": ("Real Madrid",),
    "rm": ("Real Madrid",),
    "atleti": ("Atletico Madrid", "Atlético Madrid"),
}

TEAMS_CSV_PATH = (
    PROCESSED_DATA_ROOT
    / "teams"
    / "merged"
    / "all_leagues_all_seasons_teams_merged.csv"
)

PLAYERS_CSV_PATH = (
    PROCESSED_DATA_ROOT
    / "players"
    / "merged"
    / "all_leagues_all_seasons_players_merged.csv"
)

PLAYER_FUZZY_THRESHOLD = 80

LEAGUE_PATTERNS: dict[str, list[str]] = {
    "EPL": ["premier league", "epl", "english premier league", "prem", "premiership"],
    "La_Liga": ["la liga", "laliga", "spanish league", "primera division", "primera división"],
    "Bundesliga": ["bundesliga", "german league", "german bundesliga"],
    "Serie_A": ["serie a", "serie_a", "italian league", "calcio", "italian serie a"],
    "Ligue_1": ["ligue 1", "ligue_1", "ligue1", "french league", "ligue un"],
}

PLAYER_STOP_WORDS: frozenset[str] = frozenset({
    "a", "the", "vs", "versus", "in", "for", "of", "who", "what", "is",
    "are", "will", "how", "can", "does", "do", "this", "that", "and",
    "or", "at", "to", "from", "with", "by", "on", "be", "was", "were",
    "has", "have", "had", "their", "my", "your", "our", "its", "an",
    "if", "but", "not", "so", "up", "out", "about", "into", "than",
    "then", "when", "where", "which", "would", "could", "should",
    "me", "him", "her", "us", "them", "any", "all", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "only",
    "own", "same", "too", "very", "just", "because", "as", "until",
    "while", "although", "after", "before", "since", "during", "fit",
    "available", "injured", "injury", "risk", "fitness", "squad",
    "lineup", "starting", "predicted", "expected", "match", "game",
    "play", "plays", "played", "playing", "start", "starts", "win",
    "wins", "beat", "beats", "score", "scores", "result", "predict",
    "prediction", "analysis", "compare", "comparison", "stats", "rating",
    "strength", "elo", "chance", "chances", "full", "complete", "give",
    "everything", "analysis", "breakdown",
    "epl", "ucl", "efl", "mls", "var", "prem", "bundesliga", "calcio",
    "laliga", "ligue", "serie", "liga", "premier", "league", "champions",
    "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "weekend", "week", "today", "tomorrow", "tonight", "season", "this",
    "top", "bottom", "table", "standing", "standings", "position",
    "home", "away", "derby", "cup", "final", "semi", "quarter",
})

TWO_TEAM_INTENTS: frozenset[IntentClass] = frozenset({
    IntentClass.MATCH_PREDICTION,
    IntentClass.SCORE_PREDICTION,
    IntentClass.COMPOSITE_MATCH,
    IntentClass.STAT_COMPARISON,
    IntentClass.HEAD_TO_HEAD,
    IntentClass.ODDS_COMPARISON,
})


class EntityExtractor:
    def __init__(self) -> None:
        self._canonical_teams: list[str] = []
        self._canonical_teams_lower: set[str] = set()
        self._resolved_aliases: dict[str, str] = {}
        self._canonical_players: list[str] = []
        self._latest_season = "2025"
        try:
            df = pd.read_csv(TEAMS_CSV_PATH)
            self._canonical_teams = sorted(df["team"].dropna().unique().tolist())
            self._canonical_teams_lower = {team.lower() for team in self._canonical_teams}
            self._resolved_aliases = self._build_alias_map()
            season_keys = pd.to_numeric(df["season"].map(season_group_key), errors="coerce").dropna()
            if not season_keys.empty:
                self._latest_season = str(int(season_keys.max()))
        except Exception as exc:
            logger.warning("EntityExtractor could not load teams CSV: %s", exc)
        try:
            pdf = pd.read_csv(PLAYERS_CSV_PATH, usecols=["name"])
            self._canonical_players = sorted(pdf["name"].dropna().unique().tolist())
        except Exception as exc:
            logger.warning("EntityExtractor could not load players CSV: %s", exc)

    def _build_alias_map(self) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for alias, candidates in TEAM_ALIASES.items():
            for candidate in candidates:
                if candidate.lower() in self._canonical_teams_lower:
                    resolved[alias] = candidate
                    break
        return resolved

    def _extract_alias_teams(self, query_lower: str) -> list[tuple[str, int]]:
        alias_hits: list[tuple[str, int]] = []
        seen: set[str] = set()
        for alias, canonical in self._resolved_aliases.items():
            match = re.search(rf"\b{re.escape(alias)}\b", query_lower)
            if not match:
                continue
            if canonical in seen:
                continue
            seen.add(canonical)
            alias_hits.append((canonical, match.start()))
        return alias_hits

    def extract_teams(self, query: str) -> list[str]:
        query_lower = query.lower()
        candidates: list[tuple[str, int]] = self._extract_alias_teams(query_lower)
        seen: set[str] = {team for team, _ in candidates}

        matches = process.extract(
            query_lower,
            self._canonical_teams,
            scorer=fuzz.partial_ratio,
            limit=10,
            score_cutoff=FUZZY_THRESHOLD,
        )
        for team_name, _score, _idx in matches:
            if team_name in seen:
                continue
            if not self._has_query_token_overlap(query_lower, team_name):
                continue
            seen.add(team_name)
            words = team_name.lower().split()
            pos = len(query_lower)
            for word in words:
                found = query_lower.find(word)
                if found != -1:
                    pos = min(pos, found)
            candidates.append((team_name, pos))
        candidates.sort(key=lambda x: x[1])
        return [t for t, _ in candidates[:MAX_TEAMS_PER_QUERY]]

    def _has_query_token_overlap(self, query_lower: str, team_name: str) -> bool:
        team_lower = team_name.lower()
        if re.search(rf"\b{re.escape(team_lower)}\b", query_lower):
            return True

        for token in re.split(r"[^a-z0-9]+", team_lower):
            if len(token) < 3:
                continue
            if token in TEAM_TOKEN_STOP_WORDS:
                continue
            if re.search(rf"\b{re.escape(token)}\b", query_lower):
                return True
        return False

    def extract_league(self, query: str) -> str | None:
        query_lower = query.lower()
        for league, patterns in LEAGUE_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return league
        return None

    def extract_season(self, query: str) -> str | None:
        current_season_pattern = re.compile(r"\b(this season|current season)\b", re.IGNORECASE)
        if current_season_pattern.search(query):
            return self._latest_season

        split_season_pattern = re.compile(r"\b(\d{2}|\d{4})\s*[/\-]\s*(\d{2}|\d{4})\b")
        split_match = split_season_pattern.search(query)
        if split_match:
            start_raw = split_match.group(1)
            start_year = int(start_raw) + 2000 if len(start_raw) == 2 else int(start_raw)
            if MIN_SEASON <= start_year <= MAX_SEASON:
                return str(start_year)

        year_pattern = re.compile(r"\b(\d{4})\b")
        for match in year_pattern.finditer(query):
            year = int(match.group(1))
            if MIN_SEASON <= year <= MAX_SEASON and str(year) in {self._latest_season, *[str(y) for y in range(MIN_SEASON, int(self._latest_season) + 1)]}:
                return str(year)
        return None

    def extract_player(self, query: str, known_teams: list[str]) -> str | None:
        known_team_words: set[str] = set()
        for team in known_teams:
            known_team_words.update(team.lower().split())

        if self._canonical_players:
            matches = process.extract(
                query,
                self._canonical_players,
                scorer=fuzz.partial_ratio,
                limit=3,
                score_cutoff=PLAYER_FUZZY_THRESHOLD,
            )
            for player_name, _score, _idx in matches:
                name_lower = player_name.lower()
                if any(word in name_lower for word in known_team_words):
                    continue
                for part in name_lower.split():
                    if len(part) >= 3 and re.search(rf"\b{re.escape(part)}\b", query.lower()):
                        return player_name
                        break

        tokens = query.split()
        candidate_tokens: list[str] = []
        for token in tokens:
            clean = re.sub(r"[^a-zA-Z]", "", token)
            if not clean:
                continue
            if not clean[0].isupper():
                continue
            if clean.lower() in PLAYER_STOP_WORDS:
                continue
            if clean.lower() in known_team_words:
                continue
            candidate_tokens.append(clean)
        if not candidate_tokens:
            return None
        return " ".join(candidate_tokens[:2])

    def extract(self, query: str, intent: IntentClass) -> dict:
        teams = self.extract_teams(query)
        league = self.extract_league(query)
        season = self.extract_season(query)
        player_name = (
            self.extract_player(query, teams)
            if intent in {IntentClass.PLAYER_STATS, IntentClass.AVAILABILITY_QUERY}
            else None
        )

        home_team: str | None = None
        away_team: str | None = None
        team: str | None = None

        if intent in TWO_TEAM_INTENTS:
            if len(teams) >= 2:
                home_team = teams[0]
                away_team = teams[1]
            elif len(teams) == 1:
                home_team = teams[0]
        elif intent == IntentClass.TACTICAL_QUERY:
            if len(teams) >= 2:
                home_team = teams[0]
                away_team = teams[1]
            elif len(teams) == 1:
                team = teams[0]
        else:
            if teams:
                team = teams[0]

        return {
            "home_team": home_team,
            "away_team": away_team,
            "team": team,
            "player_name": player_name,
            "league": league,
            "season": season,
        }
