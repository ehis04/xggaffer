from __future__ import annotations

from rest_framework import serializers

from apps.predictions.ml.models.match_outcome.config import (
    DEFAULT_TOP_FACTORS,
    DEMO_LEAGUE,
    DEMO_SEASON,
)


class PredictionRequestSerializer(serializers.Serializer):
    home_team = serializers.CharField(max_length=100)
    away_team = serializers.CharField(max_length=100)
    league = serializers.CharField(max_length=50, default=DEMO_LEAGUE)
    season = serializers.CharField(max_length=10, default=DEMO_SEASON)
    top_factors = serializers.IntegerField(default=DEFAULT_TOP_FACTORS, min_value=1, max_value=15)

    def validate(self, attrs):
        if attrs['home_team'] == attrs['away_team']:
            raise serializers.ValidationError('Home and away teams must be different.')
        return attrs


class PredictionFactorSerializer(serializers.Serializer):
    feature = serializers.CharField()
    value = serializers.FloatField()
    contribution = serializers.FloatField()
    description = serializers.CharField()


class PredictionProbabilitiesSerializer(serializers.Serializer):
    home = serializers.FloatField()
    draw = serializers.FloatField()
    away = serializers.FloatField()


class PredictionMetricsSerializer(serializers.Serializer):
    accuracy = serializers.FloatField()
    brier_score = serializers.FloatField(allow_null=True)


class PredictionResponseSerializer(serializers.Serializer):
    home_team = serializers.CharField()
    away_team = serializers.CharField()
    league = serializers.CharField()
    season = serializers.CharField()
    prediction = serializers.ChoiceField(choices=['Home', 'Draw', 'Away'])
    probabilities = PredictionProbabilitiesSerializer()
    top_factors = PredictionFactorSerializer(many=True)
    metrics = PredictionMetricsSerializer()
    model_type = serializers.CharField()
    version = serializers.CharField()
    contract_version = serializers.CharField(required=False)


class AvailableTeamsRequestSerializer(serializers.Serializer):
    league = serializers.CharField(max_length=50, default=DEMO_LEAGUE)
    season = serializers.CharField(max_length=10, default=DEMO_SEASON)



class EloRatingSerializer(serializers.Serializer):
    team = serializers.CharField()
    league = serializers.CharField()
    season = serializers.CharField()
    date = serializers.DateField()
    match_id = serializers.CharField()
    elo_before = serializers.FloatField()
    elo_after = serializers.FloatField()


class CurrentEloSerializer(serializers.Serializer):
    team = serializers.CharField()
    league = serializers.CharField()
    elo = serializers.FloatField()
    last_match_date = serializers.DateField()

class ScorePredictionRequestSerializer(serializers.Serializer):
    home_team = serializers.CharField(max_length=100)
    away_team = serializers.CharField(max_length=100)
    league = serializers.CharField(max_length=50, default=DEMO_LEAGUE)
    season = serializers.CharField(max_length=10, default=DEMO_SEASON)
 
    def validate(self, attrs):
        if attrs['home_team'] == attrs['away_team']:
            raise serializers.ValidationError('Home and away teams must be different.')
        return attrs
 
 
class ScorelineProbabilitiesSerializer(serializers.Serializer):
    home_win = serializers.FloatField()
    draw = serializers.FloatField()
    away_win = serializers.FloatField()
 
 
class ScorePredictionResponseSerializer(serializers.Serializer):
    home_team = serializers.CharField()
    away_team = serializers.CharField()
    league = serializers.CharField()
    season = serializers.CharField()
    lambda_home = serializers.FloatField()
    lambda_away = serializers.FloatField()
    rho = serializers.FloatField()
    scoreline_matrix = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    probabilities = ScorelineProbabilitiesSerializer()
    over_2_5 = serializers.FloatField()
    btts_yes = serializers.FloatField()
    most_likely_score = serializers.CharField()
    most_likely_score_prob = serializers.FloatField()
 

class SimulationRequestSerializer(serializers.Serializer):
    league = serializers.CharField(max_length=50, default=DEMO_LEAGUE)
    season = serializers.CharField(max_length=10, default=DEMO_SEASON)


class ProjectedPointsSerializer(serializers.Serializer):
    mean = serializers.FloatField()
    median = serializers.FloatField()
    ci_low = serializers.FloatField()
    ci_high = serializers.FloatField()


class TeamSimulationSerializer(serializers.Serializer):
    team = serializers.CharField()
    p_title = serializers.FloatField()
    p_top_4 = serializers.FloatField()
    p_top_6 = serializers.FloatField()
    p_relegation = serializers.FloatField()
    projected_points = ProjectedPointsSerializer()
    modal_position = serializers.IntegerField()
    position_probs = serializers.DictField(child=serializers.FloatField())


class SimulationResponseSerializer(serializers.Serializer):
    league = serializers.CharField()
    season = serializers.CharField()
    n_simulations = serializers.IntegerField()
    teams = TeamSimulationSerializer(many=True)


class WhatIfMatchSerializer(serializers.Serializer):
    home_team = serializers.CharField(max_length=100)
    away_team = serializers.CharField(max_length=100)
    home_goals = serializers.IntegerField(min_value=0, max_value=20)
    away_goals = serializers.IntegerField(min_value=0, max_value=20)


class WhatIfRequestSerializer(serializers.Serializer):
    league = serializers.CharField(max_length=50, default=DEMO_LEAGUE)
    season = serializers.CharField(max_length=10, default=DEMO_SEASON)
    locked_results = WhatIfMatchSerializer(many=True)

    def validate_locked_results(self, value):
        if not value:
            raise serializers.ValidationError("At least one locked result is required.")
        return value

from rest_framework import serializers


class LineupRequestSerializer(serializers.Serializer):
    team = serializers.CharField(max_length=100)
    league = serializers.CharField(max_length=50)
    season = serializers.CharField(max_length=10)


class PredictedPlayerSerializer(serializers.Serializer):
    player_id = serializers.CharField()
    player_name = serializers.CharField()
    position = serializers.CharField()
    p_start = serializers.FloatField(min_value=0.0, max_value=1.0)


class LineupResponseSerializer(serializers.Serializer):
    team = serializers.CharField()
    league = serializers.CharField()
    season = serializers.CharField()
    formation = serializers.CharField()
    predicted_xi = PredictedPlayerSerializer(many=True)
    rotation_risks = PredictedPlayerSerializer(many=True)
    model_version = serializers.CharField()
    metrics = serializers.DictField()

class AvailabilityRequestSerializer(serializers.Serializer):
    team = serializers.CharField(max_length=100)
    league = serializers.CharField(max_length=50)
    season = serializers.IntegerField()
    target_date = serializers.DateField(required=False)


class PlayerAvailabilitySerializer(serializers.Serializer):
    player_id = serializers.CharField()
    player_name = serializers.CharField()
    p_available = serializers.FloatField(min_value=0.0, max_value=1.0)
    status = serializers.ChoiceField(choices=["available", "injured", "risk_flagged"])
    expected_return_date = serializers.DateField(allow_null=True, required=False)
    median_matchdays_out = serializers.IntegerField(allow_null=True, required=False)


class AvailabilityResponseSerializer(serializers.Serializer):
    team = serializers.CharField()
    league = serializers.CharField()
    season = serializers.IntegerField()
    target_date = serializers.DateField()
    players = PlayerAvailabilitySerializer(many=True)
    summary = serializers.DictField()
    model_version = serializers.CharField()

class TacticalRequestSerializer(serializers.Serializer):
    team = serializers.CharField(max_length=100)
    season = serializers.CharField(max_length=20, required=False, allow_blank=True)
    opponent = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate(self, attrs):
        opponent = attrs.get('opponent') or ''
        if opponent and opponent == attrs['team']:
            raise serializers.ValidationError('Team and opponent must be different.')
        return attrs


class ZoneSuccessRateSerializer(serializers.Serializer):
    zone_id = serializers.IntegerField(min_value=0, max_value=23)
    success_rate = serializers.FloatField(min_value=0.0, max_value=1.0)


class TeamTacticalProfileSerializer(serializers.Serializer):
    team = serializers.CharField()
    season_name = serializers.CharField()
    competition_name = serializers.CharField()
    n_matches_in_profile = serializers.IntegerField()
    style_cluster = serializers.IntegerField()
    style_label = serializers.CharField()
    overall_completion_rate = serializers.FloatField()
    overall_forward_ratio = serializers.FloatField()
    overall_pass_length = serializers.FloatField()
    zone_success_rates = ZoneSuccessRateSerializer(many=True)
    dominant_zones = serializers.ListField(child=serializers.IntegerField())


class TacticalResponseSerializer(serializers.Serializer):
    team = TeamTacticalProfileSerializer()
    opponent = TeamTacticalProfileSerializer(allow_null=True, required=False)
    style_similarity = serializers.FloatField(allow_null=True, required=False)
    matchup_type = serializers.CharField(allow_null=True, required=False)
    model_version = serializers.CharField()

class ChatRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, min_length=1)
    image_b64 = serializers.CharField(required=False, allow_blank=False)
    image_media_type = serializers.CharField(required=False, allow_blank=False)

class OddsComparisonRequestSerializer(serializers.Serializer):
    home_team = serializers.CharField(max_length=100)
    away_team = serializers.CharField(max_length=100)
    league = serializers.CharField(max_length=50, default=DEMO_LEAGUE)
    season = serializers.CharField(max_length=10, default=DEMO_SEASON)
    bookmakers = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        allow_empty=True,
    )
    use_cached = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        home_team = attrs["home_team"].strip()
        away_team = attrs["away_team"].strip()

        if home_team.casefold() == away_team.casefold():
            raise serializers.ValidationError("Home and away teams must be different.")

        attrs["home_team"] = home_team
        attrs["away_team"] = away_team
        return attrs


class BookmakerQuoteSerializer(serializers.Serializer):
    bookmaker = serializers.CharField()
    home_odds = serializers.FloatField()
    draw_odds = serializers.FloatField()
    away_odds = serializers.FloatField()
    devig_home = serializers.FloatField()
    devig_draw = serializers.FloatField()
    devig_away = serializers.FloatField()
    last_seen_at = serializers.DateTimeField(allow_null=True)


class MarketProbabilitiesSerializer(serializers.Serializer):
    implied_home = serializers.FloatField()
    implied_draw = serializers.FloatField()
    implied_away = serializers.FloatField()
    devig_home = serializers.FloatField()
    devig_draw = serializers.FloatField()
    devig_away = serializers.FloatField()
    consensus_method = serializers.CharField()
    favourite = serializers.ChoiceField(choices=["home", "draw", "away"])
    overround = serializers.FloatField()
    source_label = serializers.CharField()


class OddsComparisonModelProbabilitiesSerializer(serializers.Serializer):
    home = serializers.FloatField()
    draw = serializers.FloatField()
    away = serializers.FloatField()


class OddsComparisonModelBlockSerializer(serializers.Serializer):
    probabilities = OddsComparisonModelProbabilitiesSerializer()
    prediction = serializers.ChoiceField(choices=["Home", "Draw", "Away"])
    version = serializers.CharField()
    model_type = serializers.CharField()


class BenchmarkSummarySerializer(serializers.Serializer):
    sample_size = serializers.IntegerField()
    model_accuracy = serializers.FloatField()
    market_favourite_accuracy = serializers.FloatField(allow_null=True)
    model_brier_score = serializers.FloatField(allow_null=True)
    market_brier_score = serializers.FloatField(allow_null=True)
    evaluation_scope = serializers.CharField()
    source_label = serializers.CharField()


class SupportResourceSerializer(serializers.Serializer):
    label = serializers.CharField()
    region = serializers.CharField()
    support_type = serializers.CharField()


class SupportBlockSerializer(serializers.Serializer):
    warning = serializers.CharField()
    resources = SupportResourceSerializer(many=True)


class OddsComparisonComparisonSerializer(serializers.Serializer):
    model_favourite = serializers.ChoiceField(choices=["home", "draw", "away"])
    market_favourite = serializers.ChoiceField(choices=["home", "draw", "away"])
    biggest_edge_side = serializers.ChoiceField(choices=["home", "draw", "away"])
    biggest_edge_points = serializers.FloatField()
    agreement = serializers.BooleanField()
    summary = serializers.CharField()


class OddsComparisonResponseSerializer(serializers.Serializer):
    home_team = serializers.CharField()
    away_team = serializers.CharField()
    league = serializers.CharField()
    season = serializers.CharField()
    kickoff = serializers.DateTimeField()
    source = serializers.CharField()
    model = OddsComparisonModelBlockSerializer()
    market = MarketProbabilitiesSerializer()
    bookmakers = BookmakerQuoteSerializer(many=True)
    comparison = OddsComparisonComparisonSerializer()
    benchmark = BenchmarkSummarySerializer(allow_null=True, required=False)
    support = SupportBlockSerializer()