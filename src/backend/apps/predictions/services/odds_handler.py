from __future__ import annotations

import logging

from apps.predictions.models import HistoricalMarketBenchmark
from apps.predictions.services.base_handler import EngineHandler, QueryPayload
from apps.predictions.services.intent_types import IntentClass, ParsedQuery
from apps.predictions.services.odds.benchmark_builder import (
    DEFAULT_EVALUATION_SCOPE,
    DEFAULT_SOURCE_LABEL,
)
from apps.predictions.services.odds.exceptions import (
    OddsDataUnavailableError,
    OddsMatchingError,
    OddsSourceError,
)
from apps.predictions.services.odds.service import OddsComparisonService
from apps.predictions.services.prediction_helper import build_match_prediction_payload
from apps.predictions.services.source_policy import source_coverage_metadata
from common.utils import current_football_season

_logger = logging.getLogger(__name__)


class OddsHandler(EngineHandler):
    ODDS_SPORT_KEY_BY_LEAGUE = {
        "epl": "soccer_epl",
        "premier league": "soccer_epl",
        "la_liga": "soccer_spain_la_liga",
        "la liga": "soccer_spain_la_liga",
        "bundesliga": "soccer_germany_bundesliga",
        "serie_a": "soccer_italy_serie_a",
        "serie a": "soccer_italy_serie_a",
        "ligue_1": "soccer_france_ligue_one",
        "ligue 1": "soccer_france_ligue_one",
        "rpl": "soccer_russia_premier_league",
        "russian premier league": "soccer_russia_premier_league",
    }

    PREDICTION_LEAGUE_ALIASES = {
        "premier league": "EPL",
        "epl": "EPL",
        "la liga": "La_Liga",
        "la_liga": "La_Liga",
        "serie a": "Serie_A",
        "serie_a": "Serie_A",
        "ligue 1": "Ligue_1",
        "ligue_1": "Ligue_1",
    }

    def handle(self, parsed_query: ParsedQuery) -> QueryPayload:
        league = parsed_query.league or "EPL"
        season = parsed_query.season or current_football_season()
        service = OddsComparisonService()

        try:
            prediction_league = self._resolve_prediction_league(league)
            fixture, is_historical = self._resolve_fixture(
                parsed_query=parsed_query,
                service=service,
                league=league,
                prediction_league=prediction_league,
                season=season,
            )
            return self._build_query_payload(
                parsed_query=parsed_query,
                fixture=fixture,
                league=league,
                prediction_league=prediction_league,
                season=season,
                is_historical=is_historical,
            )

        except OddsMatchingError as exc:
            _logger.warning("OddsHandler: team name matching failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={"support": self._build_support_payload()},
                partial=True,
                error=str(exc),
            )
        except OddsDataUnavailableError as exc:
            _logger.warning("OddsHandler: odds data unavailable: %s", exc)
            return QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={"support": self._build_support_payload()},
                partial=True,
                error=str(exc),
            )
        except OddsSourceError:
            return QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={"support": self._build_support_payload()},
                partial=True,
                error="Live odds data is temporarily unavailable.",
            )
        except FileNotFoundError:
            return QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={"support": self._build_support_payload()},
                partial=True,
                error="Prediction model is not available.",
            )
        except ValueError as exc:
            return QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={"support": self._build_support_payload()},
                partial=True,
                error=str(exc),
            )
        except Exception as exc:
            _logger.exception("OddsHandler failed: %s", exc)
            return QueryPayload(
                intent=IntentClass.ODDS_COMPARISON,
                engine_data={"support": self._build_support_payload()},
                partial=True,
                error=str(exc),
            )

    def _resolve_fixture(
        self,
        *,
        parsed_query: ParsedQuery,
        service: OddsComparisonService,
        league: str,
        prediction_league: str,
        season: str,
    ) -> tuple[dict, bool]:
        """Return (fixture_dict, is_historical).

        Tries live odds first. If the specific fixture is not in the API's
        upcoming window, falls back to the most recent stored snapshot from
        the database so that historical matches can still be answered.
        """
        live_error = None
        try:
            sport_key = self._resolve_odds_sport_key(league)
            odds_payload = service.get_fixture_odds_comparison(
                sport_key=sport_key,
                league=prediction_league,
                season=season,
            )

            available = [
                f"{f['home_team']} vs {f['away_team']}"
                for f in odds_payload.get("fixtures", [])
            ]
            _logger.warning(
                "Odds API returned %d fixture(s) for sport_key=%r: %s",
                len(available),
                sport_key,
                available,
            )

            fixture = self._select_fixture(
                fixtures=odds_payload["fixtures"],
                home_team=parsed_query.home_team,
                away_team=parsed_query.away_team,
            )
            fixture["source"] = odds_payload["source"]
            return fixture, False

        except OddsDataUnavailableError as live_exc:
            live_error = live_exc
            _logger.warning(
                "Live odds unavailable (%s) — falling back to stored snapshot.",
                live_exc,
            )

        try:
            stored_fixture = service.get_stored_fixture_odds(
                home_team=parsed_query.home_team or "",
                away_team=parsed_query.away_team or "",
                league=prediction_league,
                season=season,
            )
        except RuntimeError as exc:
            if "Database access not allowed" not in str(exc):
                raise
            if live_error is not None:
                raise live_error from exc
            raise
        stored_fixture["source"] = stored_fixture["bookmaker_source"]
        return stored_fixture, True

    def _build_query_payload(
        self,
        *,
        parsed_query: ParsedQuery,
        fixture: dict,
        league: str,
        prediction_league: str,
        season: str,
        is_historical: bool,
    ) -> QueryPayload:
        model_payload = build_match_prediction_payload(
            home_team=parsed_query.home_team,
            away_team=parsed_query.away_team,
            league=prediction_league,
            season=season,
        )
        market_payload = self._build_market_payload(
            fixture=fixture,
            source=fixture["source"],
        )
        comparison_payload = self._build_comparison_payload(
            home_team=parsed_query.home_team,
            away_team=parsed_query.away_team,
            model_payload=model_payload,
            market_payload=market_payload,
        )
        benchmark_payload = self._get_benchmark_payload(
            league_candidates=[prediction_league, league],
            season=season,
        )

        engine_data = {
            "home_team": parsed_query.home_team,
            "away_team": parsed_query.away_team,
            "league": league,
            "season": season,
            "kickoff": fixture["commence_time"],
            "source": fixture["source"],
            "is_historical": is_historical,
            "odds_fetched_at": fixture.get("fetched_at"),
            "model": {
                "probabilities": model_payload["probabilities"],
                "prediction": model_payload["prediction"],
                "version": model_payload["version"],
                "model_type": model_payload["model_type"],
            },
            "market": market_payload,
            "bookmakers": [
                {
                    "bookmaker": quote["bookmaker_name"],
                    "home_odds": quote["home_odds"],
                    "draw_odds": quote["draw_odds"],
                    "away_odds": quote["away_odds"],
                    "devig_home": quote["devig_home"],
                    "devig_draw": quote["devig_draw"],
                    "devig_away": quote["devig_away"],
                    "last_seen_at": quote["last_seen_at"],
                }
                for quote in fixture["bookmaker_quotes"]
            ],
            "comparison": comparison_payload,
            "benchmark": benchmark_payload,
            "support": self._build_support_payload(),
            "source_coverage": source_coverage_metadata(
                intent=IntentClass.ODDS_COMPARISON.value,
                used_sources=[fixture["source"], "native_stats_api"],
                required_sources=[fixture["source"], "native_stats_api"],
            ),
        }

        return QueryPayload(
            intent=IntentClass.ODDS_COMPARISON,
            engine_data=engine_data,
            partial=False,
            error=None,
        )

    def _resolve_odds_sport_key(self, league: str) -> str:
        league_key = league.strip().casefold()
        sport_key = self.ODDS_SPORT_KEY_BY_LEAGUE.get(league_key)
        if sport_key is None:
            raise ValueError(f"Unsupported league for odds comparison: {league}")
        return sport_key

    def _resolve_prediction_league(self, league: str) -> str:
        league_key = league.strip().casefold()
        return self.PREDICTION_LEAGUE_ALIASES.get(league_key, league)

    def _select_fixture(
        self,
        *,
        fixtures: list[dict],
        home_team: str | None,
        away_team: str | None,
    ) -> dict:
        for fixture in fixtures:
            if (
                fixture["home_team"].casefold() == (home_team or "").casefold()
                and fixture["away_team"].casefold() == (away_team or "").casefold()
            ):
                return fixture

        raise OddsDataUnavailableError(
            f"No live odds are available for {home_team} vs {away_team}."
        )

    def _build_market_payload(self, *, fixture: dict, source: str) -> dict:
        quotes = fixture["bookmaker_quotes"]
        quote_count = len(quotes)

        if quote_count == 0:
            raise OddsDataUnavailableError("No bookmaker quotes are available for this fixture.")

        implied_home = sum(quote["implied_home"] for quote in quotes) / quote_count
        implied_draw = sum(quote["implied_draw"] for quote in quotes) / quote_count
        implied_away = sum(quote["implied_away"] for quote in quotes) / quote_count
        devig_home = sum(quote["devig_home"] for quote in quotes) / quote_count
        devig_draw = sum(quote["devig_draw"] for quote in quotes) / quote_count
        devig_away = sum(quote["devig_away"] for quote in quotes) / quote_count
        overround = sum(quote["overround"] for quote in quotes) / quote_count

        return {
            "implied_home": implied_home,
            "implied_draw": implied_draw,
            "implied_away": implied_away,
            "devig_home": devig_home,
            "devig_draw": devig_draw,
            "devig_away": devig_away,
            "consensus_method": "mean_devigged_probabilities_across_bookmakers",
            "favourite": fixture["consensus"]["market_favourite"],
            "overround": overround,
            "source_label": source,
        }

    def _build_comparison_payload(
        self,
        *,
        home_team: str | None,
        away_team: str | None,
        model_payload: dict,
        market_payload: dict,
    ) -> dict:
        model_probabilities = model_payload["probabilities"]
        outcome_labels = {
            "home": home_team or "the home team",
            "draw": "the draw",
            "away": away_team or "the away team",
        }

        model_favourite = max(
            ("home", "draw", "away"),
            key=lambda side: model_probabilities[side],
        )
        market_favourite = market_payload["favourite"]

        edges = {
            "home": model_probabilities["home"] - market_payload["devig_home"],
            "draw": model_probabilities["draw"] - market_payload["devig_draw"],
            "away": model_probabilities["away"] - market_payload["devig_away"],
        }
        biggest_edge_side = max(edges, key=lambda side: abs(edges[side]))
        biggest_edge_points = abs(edges[biggest_edge_side]) * 100

        return {
            "model_favourite": model_favourite,
            "market_favourite": market_favourite,
            "biggest_edge_side": biggest_edge_side,
            "biggest_edge_points": round(biggest_edge_points, 1),
            "agreement": model_favourite == market_favourite,
            "summary": (
                f"xgGaffer is {round(biggest_edge_points, 1)} percentage points "
                f"{'higher' if edges[biggest_edge_side] >= 0 else 'lower'} on "
                f"{outcome_labels[biggest_edge_side]} than the market."
            ),
        }

    def _get_benchmark_payload(
        self,
        *,
        league_candidates: list[str],
        season: str,
    ) -> dict | None:
        for league in league_candidates:
            benchmark = (
                HistoricalMarketBenchmark.objects.filter(
                    league=league,
                    season=season,
                    source_label=DEFAULT_SOURCE_LABEL,
                    evaluation_scope=DEFAULT_EVALUATION_SCOPE,
                )
                .order_by("-generated_at")
                .first()
            )
            if benchmark is not None:
                return {
                    "sample_size": benchmark.sample_size,
                    "model_accuracy": benchmark.model_accuracy,
                    "market_favourite_accuracy": benchmark.market_favourite_accuracy,
                    "model_brier_score": benchmark.model_brier_score,
                    "market_brier_score": benchmark.market_brier_score,
                    "evaluation_scope": benchmark.evaluation_scope,
                    "source_label": benchmark.source_label,
                }

        return None

    def _build_support_payload(self) -> dict:
        return {
            "warning": (
                "Bookmaker prices reflect probabilities with margin, not certainty. "
                "Use market comparisons responsibly and avoid treating any outcome as guaranteed."
            ),
            "resources": [
                {
                    "label": "Ireland safer gambling support",
                    "region": "Ireland",
                    "support_type": "support",
                },
                {
                    "label": "UK safer gambling support",
                    "region": "UK",
                    "support_type": "support",
                },
            ],
        }
