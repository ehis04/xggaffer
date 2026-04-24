from __future__ import annotations

import logging

from datetime import date

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.performance import RequestTimer

from .envelope import build_predictions_envelope
from .serializers import (
    AvailableTeamsRequestSerializer,
    ChatRequestSerializer,
    CurrentEloSerializer,
    EloRatingSerializer,
    PredictionRequestSerializer,
    PredictionResponseSerializer,
)
from django.db.models import Max
from django.utils import timezone
from .models import FixtureOddsSnapshot, HistoricalMarketBenchmark, ScrapedMatch
from apps.livefootball.models import Competition, CompetitionFixture

_LEAGUE_COMPETITION_CODE = {
    'EPL': 'PL',
    'La_Liga': 'PD',
    'Bundesliga': 'BL1',
    'Serie_A': 'SA',
    'Ligue_1': 'FL1',
}

# football-data.org (livefootball) uses abbreviated names; map to The Odds API names
_LF_TO_SNAPSHOT_NAME = {
    'Man City': 'Manchester City',
    'Man United': 'Manchester United',
    'Newcastle': 'Newcastle United',
    'Nottingham': 'Nottingham Forest',
    'Brighton Hove': 'Brighton',
    'Leeds United': 'Leeds',
    'Wolverhampton': 'Wolverhampton Wanderers',
    'Spurs': 'Tottenham',
    'Athletic': 'Athletic Club',
    'Bayern': 'Bayern Munich',
    'Angers SCO': 'Angers',
}


def _lf_to_snapshot(name: str) -> str:
    return _LF_TO_SNAPSHOT_NAME.get(name, name)
from .serializers import (
    AvailableTeamsRequestSerializer,
    ChatRequestSerializer,
    CurrentEloSerializer,
    EloRatingSerializer,
    OddsComparisonRequestSerializer,
    OddsComparisonResponseSerializer,
    PredictionRequestSerializer,
    PredictionResponseSerializer,
)
from .services.odds.exceptions import (
    OddsDataUnavailableError,
    OddsMatchingError,
    OddsSourceError,
)
from .services.odds.service import OddsComparisonService
from .services.odds.benchmark_builder import (
    DEFAULT_EVALUATION_SCOPE,
    DEFAULT_SOURCE_LABEL,
)
from .services.prediction_helper import build_match_prediction_payload

logger = logging.getLogger(__name__)




class PredictMatchView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        with RequestTimer(endpoint="predictions.predict", method=request.method, params=None) as timer:
            serializer = PredictionRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            try:
                from .services.prediction_helper import build_match_prediction_payload

                response_payload = build_match_prediction_payload(
                    home_team=data['home_team'],
                    away_team=data['away_team'],
                    league=data['league'],
                    season=data['season'],
                    top_n=data['top_factors'],
                )
                response_serializer = PredictionResponseSerializer(data=response_payload)
                response_serializer.is_valid(raise_exception=True)
                response = Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)
            except ValueError as exc:
                response = Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except FileNotFoundError as exc:
                logger.error('Model not found: %s', exc)
                response = Response({'error': 'Prediction model is not available.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as exc:
                logger.exception('Prediction failed: %s', exc)
                response = Response({'error': 'An unexpected error occurred during prediction.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            timer.status_code = response.status_code
            return response


class ModelInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        with RequestTimer(endpoint="predictions.model_info", method=request.method, params=dict(request.query_params)) as timer:
            try:
                from .ml.models.match_outcome.predict import get_predictor

                predictor = get_predictor()
                response = Response(predictor.get_model_info())
            except FileNotFoundError:
                response = Response({'error': 'No trained model available.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            timer.status_code = response.status_code
            return response


class AvailableTeamsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        with RequestTimer(endpoint="predictions.teams", method=request.method, params=dict(request.query_params)) as timer:
            serializer = AvailableTeamsRequestSerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            try:
                from .ml.models.match_outcome.feature_service import get_feature_service

                service = get_feature_service(leagues=[data['league']], seasons=[data['season']])
                teams = service.get_available_teams(league=data['league'], season=data['season'])
                response = Response({'league': data['league'], 'season': data['season'], 'teams': teams, 'count': len(teams)})
            except Exception as exc:
                logger.exception('Failed to load teams: %s', exc)
                response = Response({'error': 'Could not load available teams.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            timer.status_code = response.status_code
            return response


class ChatQueryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        with RequestTimer(endpoint="predictions.chat", method=request.method, params=None, snapshot_version="none") as timer:
            serializer = ChatRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            query = serializer.validated_data["query"]
            try:
                from .services.chat_service import handle_chat_query

                result = handle_chat_query(query)
                response = Response(build_predictions_envelope(result), status=status.HTTP_200_OK)
            except Exception as exc:
                logger.exception("Chat query failed: %s", exc)
                response = Response({"error": "Query processing failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            timer.status_code = response.status_code
            return response

class EloRankingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, league):
        from .models import CurrentEloRating

        ratings = CurrentEloRating.objects.filter(league=league)

        if not ratings.exists():
            return Response(
                {'error': f'No Elo ratings found for league: {league}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CurrentEloSerializer(ratings, many=True)
        return Response({
            'league': league,
            'count': ratings.count(),
            'rankings': serializer.data,
        })


class EloHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, team):
        from .models import EloRating

        history = EloRating.objects.filter(team=team)

        season = request.query_params.get('season')
        if season:
            history = history.filter(season=season)

        league = request.query_params.get('league')
        if league:
            history = history.filter(league=league)

        if not history.exists():
            return Response(
                {'error': f'No Elo history found for team: {team}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EloRatingSerializer(history, many=True)
        return Response({
            'team': team,
            'count': history.count(),
            'history': serializer.data,
        })

class ScorePredictionView(APIView):
    permission_classes = [AllowAny]
 
    def post(self, request):
        from .serializers import (
            ScorePredictionRequestSerializer,
            ScorePredictionResponseSerializer,
        )
 
        serializer = ScorePredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
 
        try:
            from .ml.models.scoreline.predict import ScorePredictor
            from .ml.models.scoreline.score_feature_service import get_score_feature_service
 
            service = get_score_feature_service(
                leagues=[data['league']],
                seasons=[data['season']],
            )
            features = service.build_prediction_features(
                home_team=data['home_team'],
                away_team=data['away_team'],
                league=data['league'],
                season=data['season'],
            )
 
            predictor = ScorePredictor()
            result = predictor.predict(features)
 
            response_payload = {
                'home_team': data['home_team'],
                'away_team': data['away_team'],
                'league': data['league'],
                'season': data['season'],
                'lambda_home': result['lambda_home'],
                'lambda_away': result['lambda_away'],
                'rho': result['rho'],
                'scoreline_matrix': result['scoreline_matrix'],
                'probabilities': {
                    'home_win': result['home_win'],
                    'draw': result['draw'],
                    'away_win': result['away_win'],
                },
                'over_2_5': result['over_2.5'],
                'btts_yes': result['btts_yes'],
                'most_likely_score': result['most_likely_score'],
                'most_likely_score_prob': result['most_likely_score_prob'],
            }
 
            response_serializer = ScorePredictionResponseSerializer(data=response_payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)
 
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as exc:
            logger.error('Score model not found: %s', exc)
            return Response(
                {'error': 'Score prediction model is not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Score prediction failed: %s', exc)
            return Response(
                {'error': 'An unexpected error occurred during score prediction.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
 
class SimulationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, league, season):
        try:
            from .ml.features.rolling import load_match_history
            from .ml.models.scoreline.predict import ScorePredictor
            from .ml.models.simulation.prepare_fixtures import prepare_remaining_fixtures
            from .ml.models.simulation.simulate import aggregate_results, simulate_season

            all_seasons = [str(y) for y in range(2014, 2025)]
            matches = load_match_history([league], all_seasons)

            actual, remaining, features = prepare_remaining_fixtures(
                matches, season, league, freeze_matchweek=38,
            )

            if not remaining:
                agg_dicts = self._build_final_table_response(actual)
            else:
                predictor = ScorePredictor()
                lambda_h, lambda_a = predictor.predict_lambdas_batch(features)
                sim = simulate_season(actual, remaining, lambda_h, lambda_a)
                agg = aggregate_results(sim)
                agg_dicts = self._build_response_rows(agg, sim["n_simulations"])

            from .serializers import SimulationResponseSerializer

            payload = {
                "league": league,
                "season": season,
                "n_simulations": 10000,
                "teams": agg_dicts,
            }
            response_serializer = SimulationResponseSerializer(data=payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as exc:
            logger.error("Simulation model not found: %s", exc)
            return Response(
                {"error": "Required models are not available."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Simulation failed: %s", exc)
            return Response(
                {"error": "An unexpected error occurred during simulation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _build_response_rows(agg_df, n_sims):
        rows = []
        for _, row in agg_df.iterrows():
            rows.append({
                "team": row["team"],
                "p_title": round(row["p_title"], 4),
                "p_top_4": round(row["p_top_4"], 4),
                "p_top_6": round(row["p_top_6"], 4),
                "p_relegation": round(row["p_relegation"], 4),
                "projected_points": {
                    "mean": round(row["projected_points_mean"], 1),
                    "median": round(row["projected_points_median"], 1),
                    "ci_low": round(row["projected_points_5th"], 1),
                    "ci_high": round(row["projected_points_95th"], 1),
                },
                "modal_position": row["modal_position"],
                "position_probs": {
                    str(k): round(v, 4) for k, v in row["position_probs"].items()
                },
            })
        return rows

    @staticmethod
    def _build_final_table_response(actual_results):
        from .ml.models.simulation.simulate import compute_league_table

        table = compute_league_table(actual_results)
        rows = []
        n_teams = len(table)
        for _, row in table.iterrows():
            pos = row["position"]
            rows.append({
                "team": row["team"],
                "p_title": 1.0 if pos == 1 else 0.0,
                "p_top_4": 1.0 if pos <= 4 else 0.0,
                "p_top_6": 1.0 if pos <= 6 else 0.0,
                "p_relegation": 1.0 if pos >= n_teams - 2 else 0.0,
                "projected_points": {
                    "mean": float(row["points"]),
                    "median": float(row["points"]),
                    "ci_low": float(row["points"]),
                    "ci_high": float(row["points"]),
                },
                "modal_position": int(pos),
                "position_probs": {str(int(pos)): 1.0},
            })
        return rows


class WhatIfSimulationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, league, season):
        from .serializers import WhatIfRequestSerializer, SimulationResponseSerializer

        serializer = WhatIfRequestSerializer(data={**request.data, "league": league, "season": season})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from .ml.features.rolling import load_match_history
            from .ml.models.scoreline.predict import ScorePredictor
            from .ml.models.simulation.prepare_fixtures import prepare_remaining_fixtures
            from .ml.models.simulation.simulate import (
                aggregate_results,
                simulate_with_locked_results,
            )

            all_seasons = [str(y) for y in range(2014, 2025)]
            matches = load_match_history([league], all_seasons)

            actual, remaining, features = prepare_remaining_fixtures(
                matches, season, league, freeze_matchweek=38,
            )

            if not remaining:
                return Response(
                    {"error": "Season is complete, no fixtures to simulate."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            predictor = ScorePredictor()
            lambda_h, lambda_a = predictor.predict_lambdas_batch(features)

            sim = simulate_with_locked_results(
                actual, remaining, lambda_h, lambda_a,
                locked_results=data["locked_results"],
            )
            agg = aggregate_results(sim)

            payload = {
                "league": league,
                "season": season,
                "n_simulations": sim["n_simulations"],
                "teams": SimulationView._build_response_rows(agg, sim["n_simulations"]),
            }
            response_serializer = SimulationResponseSerializer(data=payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as exc:
            logger.error("Simulation model not found: %s", exc)
            return Response(
                {"error": "Required models are not available."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("What-if simulation failed: %s", exc)
            return Response(
                {"error": "An unexpected error occurred during simulation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class PredictLineupView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from .serializers import LineupRequestSerializer, LineupResponseSerializer

        serializer = LineupRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from .ml.models.lineup.feature_service import get_latest_team_features
            from .ml.models.lineup.predict import LineupPredictor
            from .ml.models.lineup.predict import assemble_xi, infer_formation

            team_features = get_latest_team_features(
                team_name=data['team'],
                league=data['league'],
                season=data['season'],
            )

            predictor = LineupPredictor()
            probs_df = predictor.predict_start_probabilities(team_features)

            formation = infer_formation(team_features)
            xi_df = assemble_xi(probs_df, formation)

            xi_player_ids = set(xi_df['player_id'].astype(str))
            rotation_risks_df = (
                probs_df[~probs_df['player_id'].astype(str).isin(xi_player_ids)]
                .sort_values('p_start', ascending=False)
                .head(5)
            )

            predicted_xi_payload = [
                {
                    'player_id': str(row['player_id']),
                    'player_name': row['player_name'],
                    'position': row['position'],
                    'p_start': float(row['p_start']),
                }
                for _, row in xi_df.iterrows()
            ]

            rotation_risks_payload = [
                {
                    'player_id': str(row['player_id']),
                    'player_name': row['player_name'],
                    'position': row['position'],
                    'p_start': float(row['p_start']),
                }
                for _, row in rotation_risks_df.iterrows()
            ]

            response_payload = {
                'team': data['team'],
                'league': data['league'],
                'season': data['season'],
                'formation': formation,
                'predicted_xi': predicted_xi_payload,
                'rotation_risks': rotation_risks_payload,
                'model_version': 'v1',
                'metrics': {
                    'per_player_accuracy': predictor.metrics.get('accuracy'),
                    'accuracy_gain': predictor.metrics.get('accuracy_gain'),
                },
            }

            response_serializer = LineupResponseSerializer(data=response_payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as exc:
            logger.error('Lineup resource not found: %s', exc)
            return Response(
                {'error': 'Lineup model or feature cache not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Lineup prediction failed: %s', exc)
            return Response(
                {'error': 'An unexpected error occurred during lineup prediction.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AvailableLineupTeamsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        league = request.query_params.get('league')
        season = request.query_params.get('season')

        if not league or not season:
            return Response(
                {'error': 'league and season query parameters are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from .ml.models.lineup.feature_service import get_available_teams

            teams = get_available_teams(league=league, season=season)
            return Response({
                'league': league,
                'season': season,
                'teams': teams,
                'count': len(teams),
            })
        except FileNotFoundError:
            return Response(
                {'error': 'Lineup feature cache not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Failed to load lineup teams: %s', exc)
            return Response(
                {'error': 'Could not load available teams.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class PredictAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from .serializers import (
            AvailabilityRequestSerializer,
            AvailabilityResponseSerializer,
        )

        serializer = AvailabilityRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_date = data.get("target_date") or date.today()

        try:
            from .ml.models.availability.feature_service import (
                get_team_availability_features,
            )
            from .ml.models.availability.predict import AvailabilityPredictor

            features_df = get_team_availability_features(
                team_name=data["team"],
                league=data["league"],
                season=data["season"],
                target_date=target_date,
            )

            if features_df.empty:
                return Response(
                    {"detail": f"No active players found for {data['team']} in {data['league']} {data['season']}"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            predictor = AvailabilityPredictor()
            predictions = predictor.predict_for_players(features_df, target_date=target_date)

            summary = self._build_summary(predictions)

            payload = {
                "team": data["team"],
                "league": data["league"],
                "season": data["season"],
                "target_date": target_date,
                "players": predictions,
                "summary": summary,
                "model_version": "5A_cox_v1+5B_xgb_v1",
            }

            response_serializer = AvailabilityResponseSerializer(payload)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)

        except FileNotFoundError as exc:
            logger.error("Availability model artifact missing: %s", exc)
            return Response(
                {"detail": "Availability models not yet trained"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Availability prediction failed")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _build_summary(predictions: list[dict]) -> dict:
        total = len(predictions)
        injured = sum(1 for p in predictions if p["status"] == "injured")
        risk_flagged = sum(1 for p in predictions if p["status"] == "risk_flagged")
        available = total - injured - risk_flagged

        return {
            "total_players": total,
            "available": available,
            "injured": injured,
            "risk_flagged": risk_flagged,
        }

class TacticalAnalysisView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from .serializers import (
            TacticalRequestSerializer,
            TacticalResponseSerializer,
        )

        serializer = TacticalRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        season_name = data.get('season') or None
        opponent = data.get('opponent') or None

        try:
            from .ml.models.tactical.predict import TacticalAnalyser

            analyser = TacticalAnalyser()

            if opponent:
                comparison = analyser.compare_teams(
                    team_a=data['team'],
                    team_b=opponent,
                    season_name=season_name,
                )
                if comparison is None:
                    return Response(
                        {'detail': f'No tactical profile found for {data["team"]} or {opponent}'},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                payload = {
                    'team': self._serialise_profile(comparison['team_a']),
                    'opponent': self._serialise_profile(comparison['team_b']),
                    'style_similarity': comparison['style_similarity'],
                    'matchup_type': comparison['matchup_type'],
                    'model_version': '6A_xgb_v1+6B_kmeans_v1',
                }
            else:
                analysis = analyser.analyse_team(
                    team_name=data['team'],
                    season_name=season_name,
                )
                if analysis is None:
                    return Response(
                        {'detail': f'No tactical profile found for {data["team"]}'},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                payload = {
                    'team': self._serialise_profile(analysis),
                    'opponent': None,
                    'style_similarity': None,
                    'matchup_type': None,
                    'model_version': '6A_xgb_v1+6B_kmeans_v1',
                }

            response_serializer = TacticalResponseSerializer(data=payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as exc:
            logger.error('Tactical model or data missing: %s', exc)
            return Response(
                {'detail': 'Tactical models or data not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Tactical analysis failed: %s', exc)
            return Response(
                {'detail': 'An unexpected error occurred during tactical analysis.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _serialise_profile(analysis: dict) -> dict:
        zone_rates = [
            {'zone_id': zone_id, 'success_rate': rate}
            for zone_id, rate in sorted(analysis['zone_success_rates'].items())
        ]
        return {
            'team': analysis['team'],
            'season_name': analysis['season_name'],
            'competition_name': analysis['competition_name'],
            'n_matches_in_profile': analysis['n_matches_in_profile'],
            'style_cluster': analysis['style_cluster'],
            'style_label': analysis['style_label'],
            'overall_completion_rate': analysis['overall_completion_rate'],
            'overall_forward_ratio': analysis['overall_forward_ratio'],
            'overall_pass_length': analysis['overall_pass_length'],
            'zone_success_rates': zone_rates,
            'dominant_zones': analysis['dominant_zones'],
        }


class AvailableTacticalTeamsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .ml.models.tactical.feature_service import (
                list_available_seasons_for_team,
                list_available_teams,
            )

            team = request.query_params.get('team')
            if team:
                seasons = list_available_seasons_for_team(team)
                return Response({
                    'team': team,
                    'seasons': seasons,
                    'count': len(seasons),
                })

            teams = list_available_teams()
            return Response({
                'teams': teams,
                'count': len(teams),
            })
        except FileNotFoundError:
            return Response(
                {'detail': 'Tactical feature cache not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Failed to load tactical teams: %s', exc)
            return Response(
                {'detail': 'Could not load tactical teams.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OddsComparisonView(APIView):
    permission_classes = [AllowAny]

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

    def post(self, request):
        serializer = OddsComparisonRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        home_team = data["home_team"]
        away_team = data["away_team"]
        requested_league = data["league"]
        season = data["season"]
        bookmakers = data.get("bookmakers")

        try:
            sport_key = self._resolve_odds_sport_key(requested_league)
            prediction_league = self._resolve_prediction_league(requested_league)

            odds_service = OddsComparisonService()
            fixture, odds_source = self._get_fixture_with_odds(
                odds_service=odds_service,
                sport_key=sport_key,
                prediction_league=prediction_league,
                season=season,
                home_team=home_team,
                away_team=away_team,
                bookmakers=bookmakers,
            )

            model_payload = build_match_prediction_payload(
                home_team=home_team,
                away_team=away_team,
                league=prediction_league,
                season=season,
            )

            market_payload = self._build_market_payload(
                fixture=fixture,
                source=odds_source,
            )
            comparison_payload = self._build_comparison_payload(
                home_team=home_team,
                away_team=away_team,
                model_payload=model_payload,
                market_payload=market_payload,
            )
            benchmark_payload = self._get_benchmark_payload(
                league_candidates=[prediction_league, requested_league],
                season=season,
            )
            support_payload = self._build_support_payload()

            response_payload = {
                "home_team": home_team,
                "away_team": away_team,
                "league": requested_league,
                "season": season,
                "kickoff": fixture["commence_time"],
                "source": odds_source,
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
                "support": support_payload,
            }

            response_serializer = OddsComparisonResponseSerializer(data=response_payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(build_predictions_envelope(response_serializer.data), status=status.HTTP_200_OK)

        except OddsMatchingError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except OddsDataUnavailableError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except OddsSourceError:
            return Response(
                {"error": "Live odds data is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except FileNotFoundError as exc:
            logger.error("Prediction model not found for odds comparison: %s", exc)
            return Response(
                {"error": "Prediction model is not available."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Odds comparison failed: %s", exc)
            return Response(
                {"error": "An unexpected error occurred during odds comparison."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_fixture_with_odds(
        self,
        *,
        odds_service,
        sport_key: str,
        prediction_league: str,
        season: str,
        home_team: str,
        away_team: str,
        bookmakers,
    ) -> tuple[dict, str]:
        try:
            fixture = odds_service.get_stored_fixture_odds(
                home_team=home_team,
                away_team=away_team,
                league=prediction_league,
                season=season,
            )
            return fixture, fixture["bookmaker_source"]
        except OddsDataUnavailableError:
            pass

        odds_payload = odds_service.get_fixture_odds_comparison(
            sport_key=sport_key,
            league=prediction_league,
            season=season,
            bookmakers=bookmakers,
        )
        fixture = self._select_fixture(
            fixtures=odds_payload["fixtures"],
            home_team=home_team,
            away_team=away_team,
        )
        return fixture, odds_payload["source"]

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
        home_team: str,
        away_team: str,
    ) -> dict:
        for fixture in fixtures:
            if (
                fixture["home_team"].casefold() == home_team.casefold()
                and fixture["away_team"].casefold() == away_team.casefold()
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
        home_team: str,
        away_team: str,
        model_payload: dict,
        market_payload: dict,
    ) -> dict:
        model_probabilities = model_payload["probabilities"]
        outcome_labels = {
            "home": home_team,
            "draw": "the draw",
            "away": away_team,
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


class OddsTeamsView(APIView):
    """Return all team names for the league, sourced from CompetitionFixture (full season)."""
    permission_classes = [AllowAny]

    def get(self, request):
        league = request.query_params.get("league", "EPL")
        comp_code = _LEAGUE_COMPETITION_CODE.get(league)
        names: set[str] = set()

        if comp_code:
            try:
                comp = Competition.objects.get(code=comp_code)
                for name in CompetitionFixture.objects.filter(
                    competition=comp, season_label="2025"
                ).values_list("home_team_name", flat=True).distinct():
                    names.add(_lf_to_snapshot(name))
                for name in CompetitionFixture.objects.filter(
                    competition=comp, season_label="2025"
                ).values_list("away_team_name", flat=True).distinct():
                    names.add(_lf_to_snapshot(name))
            except Competition.DoesNotExist:
                pass

        # Fallback: odds snapshots (covers leagues not in CompetitionFixture)
        if not names:
            for field in ("home_team", "away_team"):
                names.update(
                    FixtureOddsSnapshot.objects
                    .filter(league=league, season="2025")
                    .values_list(field, flat=True)
                    .distinct()
                )

        return Response({"league": league, "teams": sorted(names)})


class OddsFixtureListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Q as DQ

        league = request.query_params.get("league", "EPL")
        season = "2025"
        view = request.query_params.get("view", "future")
        team_a = request.query_params.get("team_a", "").strip()
        team_b = request.query_params.get("team_b", "").strip()
        matchup_mode = bool(team_a and team_b)

        now = timezone.now()
        comp_code = _LEAGUE_COMPETITION_CODE.get(league)

        # Reverse of _LF_TO_SNAPSHOT_NAME: snapshot name → football-data name
        _snapshot_to_lf = {v: k for k, v in _LF_TO_SNAPSHOT_NAME.items()}

        # Build result lookup keyed by (snapshot_home, snapshot_away)
        result_map: dict[tuple[str, str], dict] = {}
        comp: Competition | None = None
        if comp_code:
            try:
                comp = Competition.objects.get(code=comp_code)
                for f in CompetitionFixture.objects.filter(
                    competition=comp,
                    season_label=season,
                    home_score__isnull=False,
                    away_score__isnull=False,
                ):
                    h = _lf_to_snapshot(f.home_team_name)
                    a = _lf_to_snapshot(f.away_team_name)
                    hg, ag = f.home_score, f.away_score
                    result_map[(h, a)] = {
                        "home_goals": hg,
                        "away_goals": ag,
                        "outcome": "H" if hg > ag else "A" if ag > hg else "D",
                        "score": f"{hg}–{ag}",
                    }
            except Competition.DoesNotExist:
                pass

        # ------------------------------------------------------------------
        # MATCHUP + PAST: use CompetitionFixture as the primary source so
        # that games played before we started storing odds still appear.
        # Attach odds from FixtureOddsSnapshot where available.
        # ------------------------------------------------------------------
        odds_service = OddsComparisonService()

        def _build_consensus(snapshot: FixtureOddsSnapshot) -> dict | None:
            quotes = list(snapshot.quotes.all())
            if not quotes:
                return None
            quote_rows = [
                {
                    "bookmaker": q.bookmaker.name,
                    "home_odds": q.home_odds,
                    "draw_odds": q.draw_odds,
                    "away_odds": q.away_odds,
                    "devig_home": q.devig_home,
                    "devig_draw": q.devig_draw,
                    "devig_away": q.devig_away,
                    "last_seen_at": q.last_seen_at.isoformat() if q.last_seen_at else None,
                }
                for q in quotes
            ]
            raw = odds_service.get_consensus_market_view(quote_rows)
            return {
                "devig_home": raw["consensus_home_probability"],
                "devig_draw": raw["consensus_draw_probability"],
                "devig_away": raw["consensus_away_probability"],
                "overround": 0.0,
                "favourite": raw["market_favourite"],
                "source_label": f"{raw['quote_count']} bookmakers",
            }

        if matchup_mode and view == "past" and comp:
            lf_a = _snapshot_to_lf.get(team_a, team_a)
            lf_b = _snapshot_to_lf.get(team_b, team_b)

            cf_games = CompetitionFixture.objects.filter(
                DQ(home_team_name=lf_a, away_team_name=lf_b) |
                DQ(home_team_name=lf_b, away_team_name=lf_a),
                competition=comp,
                season_label=season,
                kickoff_at__lt=now,
                home_score__isnull=False,
                away_score__isnull=False,
            ).order_by("-kickoff_at")

            fixtures = []
            for cf in cf_games:
                h_snap = _lf_to_snapshot(cf.home_team_name)
                a_snap = _lf_to_snapshot(cf.away_team_name)
                hg, ag = cf.home_score, cf.away_score
                result = {
                    "home_goals": hg,
                    "away_goals": ag,
                    "outcome": "H" if hg > ag else "A" if ag > hg else "D",
                    "score": f"{hg}–{ag}",
                }

                # Try to find a matching odds snapshot by date
                snap = (
                    FixtureOddsSnapshot.objects
                    .filter(
                        home_team=h_snap,
                        away_team=a_snap,
                        league=league,
                        season=season,
                        commence_time__date=cf.kickoff_at.date() if cf.kickoff_at else None,
                    )
                    .prefetch_related("quotes__bookmaker")
                    .order_by("-fetched_at")
                    .first()
                )
                consensus = _build_consensus(snap) if snap else None

                fixtures.append({
                    "home_team": h_snap,
                    "away_team": a_snap,
                    "league": league,
                    "season": season,
                    "commence_time": cf.kickoff_at.isoformat() if cf.kickoff_at else "",
                    "fetched_at": snap.fetched_at.isoformat() if snap else "",
                    "bookmakers": [],
                    "consensus": consensus,
                    "result": result,
                })

            return Response({
                "league": league, "season": season, "view": view,
                "count": len(fixtures), "fixtures": fixtures,
            })

        # ------------------------------------------------------------------
        # Standard path: FixtureOddsSnapshot as primary source
        # ------------------------------------------------------------------
        latest_ids = (
            FixtureOddsSnapshot.objects
            .filter(league=league, season=season)
            .values("external_fixture_id")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )

        snapshots_qs = (
            FixtureOddsSnapshot.objects
            .filter(id__in=latest_ids)
            .prefetch_related("quotes__bookmaker")
        )

        if matchup_mode:
            team_set = {team_a, team_b}
            all_snapshots = list(snapshots_qs.order_by("commence_time"))
            snapshots_qs = [
                s for s in all_snapshots
                if {s.home_team, s.away_team} == team_set
            ]

        if view == "past":
            snapshots = [s for s in snapshots_qs if s.commence_time < now]
            snapshots.sort(key=lambda s: s.commence_time, reverse=True)
        else:
            snapshots = [s for s in snapshots_qs if s.commence_time >= now]
            snapshots.sort(key=lambda s: s.commence_time)

        fixtures = []
        for snapshot in snapshots:
            consensus = _build_consensus(snapshot)
            if consensus is None:
                continue

            result = result_map.get((snapshot.home_team, snapshot.away_team))

            fixtures.append({
                "home_team": snapshot.home_team,
                "away_team": snapshot.away_team,
                "league": snapshot.league,
                "season": snapshot.season,
                "commence_time": snapshot.commence_time.isoformat(),
                "fetched_at": snapshot.fetched_at.isoformat(),
                "bookmakers": [],
                "consensus": consensus,
                "result": result,
            })

        return Response({
            "league": league,
            "season": season,
            "view": view,
            "count": len(fixtures),
            "fixtures": fixtures,
        })