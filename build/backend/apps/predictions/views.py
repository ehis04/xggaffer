from __future__ import annotations

import logging

from datetime import date

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AvailableTeamsRequestSerializer,
    CurrentEloSerializer,
    EloRatingSerializer,
    PredictionRequestSerializer,
    PredictionResponseSerializer,
)

logger = logging.getLogger(__name__)


class PredictMatchView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from .ml.models.match_outcome.interpret import explain_match

            result = explain_match(
                home_team=data['home_team'],
                away_team=data['away_team'],
                league=data['league'],
                season=data['season'],
                top_n=data['top_factors'],
            )

            response_payload = {
                'home_team': data['home_team'],
                'away_team': data['away_team'],
                'league': data['league'],
                'season': data['season'],
                'prediction': result['prediction'],
                'probabilities': result['probabilities'],
                'top_factors': result['top_factors'],
                'metrics': result['metrics'],
                'model_type': result['model_type'],
                'version': result['version'],
                'contract_version': result.get('contract_version'),
            }
            response_serializer = PredictionResponseSerializer(data=response_payload)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as exc:
            logger.error('Model not found: %s', exc)
            return Response(
                {'error': 'Prediction model is not available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Prediction failed: %s', exc)
            return Response(
                {'error': 'An unexpected error occurred during prediction.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AvailableTeamsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = AvailableTeamsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from .ml.models.match_outcome.feature_service import get_feature_service

            service = get_feature_service(leagues=[data['league']], seasons=[data['season']])
            teams = service.get_available_teams(league=data['league'], season=data['season'])

            return Response({
                'league': data['league'],
                'season': data['season'],
                'teams': teams,
                'count': len(teams),
            })
        except Exception as exc:
            logger.exception('Failed to load teams: %s', exc)
            return Response(
                {'error': 'Could not load available teams.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ModelInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .ml.models.match_outcome.predict import get_predictor

            predictor = get_predictor()
            return Response(predictor.get_model_info())
        except FileNotFoundError:
            return Response(
                {'error': 'No trained model available.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )



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
            return Response(response_serializer.data, status=status.HTTP_200_OK)
 
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
            return Response(response_serializer.data, status=status.HTTP_200_OK)

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
            return Response(response_serializer.data, status=status.HTTP_200_OK)

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
            return Response(response_serializer.data, status=status.HTTP_200_OK)

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
            return Response(response_serializer.data, status=status.HTTP_200_OK)

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
            return Response(response_serializer.data, status=status.HTTP_200_OK)

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