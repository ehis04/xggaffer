from rest_framework import serializers


class CompetitionListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    provider = serializers.CharField()
    external_id = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_blank=True)
    area_name = serializers.CharField(allow_blank=True)
    emblem_url = serializers.CharField(allow_blank=True)
    current_season_label = serializers.CharField(allow_blank=True)
    current_season_start_date = serializers.DateField(allow_null=True)
    current_season_end_date = serializers.DateField(allow_null=True)
    current_matchday = serializers.IntegerField(allow_null=True)
    last_synced_at = serializers.DateTimeField(allow_null=True)


class TeamReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    external_id = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_blank=True)
    short_name = serializers.CharField(allow_blank=True)
    tla = serializers.CharField(allow_blank=True)
    emblem_url = serializers.CharField(allow_blank=True)


class CanonicalPlayerReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    display_name = serializers.CharField(allow_blank=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)


class TableRowSerializer(serializers.Serializer):
    position = serializers.IntegerField()
    team = TeamReferenceSerializer()
    played = serializers.IntegerField()
    won = serializers.IntegerField()
    drawn = serializers.IntegerField()
    lost = serializers.IntegerField()
    goals_for = serializers.IntegerField()
    goals_against = serializers.IntegerField()
    goal_difference = serializers.IntegerField()
    points = serializers.IntegerField()
    form = serializers.CharField(allow_blank=True)


class CompetitionTableResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    snapshot_label = serializers.CharField(allow_blank=True)
    matchday = serializers.IntegerField(allow_null=True)
    fetched_at = serializers.DateTimeField(allow_null=True)
    synced_at = serializers.DateTimeField(allow_null=True)
    rows = TableRowSerializer(many=True)


class FixtureItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    external_match_id = serializers.CharField(allow_blank=True)
    season_label = serializers.CharField(allow_blank=True)
    status = serializers.CharField(allow_blank=True)
    kickoff_at = serializers.DateTimeField(allow_null=True)
    matchday = serializers.IntegerField(allow_null=True)
    home_team = TeamReferenceSerializer()
    away_team = TeamReferenceSerializer()
    home_score = serializers.IntegerField(allow_null=True)
    away_score = serializers.IntegerField(allow_null=True)


class CompetitionFixturesResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField()
    items = FixtureItemSerializer(many=True)


class CompetitionPreviousNextFixturesResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    previous = FixtureItemSerializer(many=True)
    next = FixtureItemSerializer(many=True)


class ScorerItemSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    external_player_id = serializers.CharField(allow_blank=True)
    player_name = serializers.CharField(allow_blank=True)
    goals = serializers.IntegerField()
    penalties = serializers.IntegerField(allow_null=True)
    team = TeamReferenceSerializer()
    canonical_player = CanonicalPlayerReferenceSerializer()


class CompetitionScorersResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField()
    items = ScorerItemSerializer(many=True)


class TeamLookupItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    competition_id = serializers.IntegerField()
    provider = serializers.CharField()
    external_id = serializers.CharField(allow_blank=True)
    season_label = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_blank=True)
    short_name = serializers.CharField(allow_blank=True)
    tla = serializers.CharField(allow_blank=True)
    area_name = serializers.CharField(allow_blank=True)
    emblem_url = serializers.CharField(allow_blank=True)
    venue = serializers.CharField(allow_blank=True)
    website = serializers.CharField(allow_blank=True)
    founded_year = serializers.IntegerField(allow_null=True)
    last_synced_at = serializers.DateTimeField(allow_null=True)


class CompetitionTeamsResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField()
    items = TeamLookupItemSerializer(many=True)


class PlayerLookupItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    provider = serializers.CharField()
    external_player_id = serializers.CharField(allow_blank=True)
    player_name = serializers.CharField(allow_blank=True)
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)
    date_of_birth = serializers.DateField(allow_null=True)
    nationality = serializers.CharField(allow_blank=True)
    primary_position = serializers.CharField(allow_blank=True)
    raw_position = serializers.CharField(allow_blank=True)
    squad_number = serializers.IntegerField(allow_null=True)
    is_active = serializers.BooleanField()
    team = serializers.SerializerMethodField()
    canonical_player = CanonicalPlayerReferenceSerializer()

    def get_team(self, obj):
        team_data = obj.get("team") or {}
        return TeamLookupItemSerializer(team_data).data


class TeamPlayersResponseSerializer(serializers.Serializer):
    team = TeamLookupItemSerializer()
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField()
    items = PlayerLookupItemSerializer(many=True)


class CompetitionPlayersResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField()
    items = PlayerLookupItemSerializer(many=True)


class PlayerSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField(allow_blank=True)
    count = serializers.IntegerField()
    items = PlayerLookupItemSerializer(many=True)

from rest_framework import serializers


class OverviewCtaSerializer(serializers.Serializer):
    label = serializers.CharField()
    path = serializers.CharField()
    query = serializers.DictField(required=False, default=dict)


class OverviewCompetitionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField(allow_blank=True, allow_null=True)
    name = serializers.CharField()
    country = serializers.CharField(allow_blank=True, allow_null=True)
    emblem_url = serializers.CharField(allow_blank=True, allow_null=True)


class OverviewTeamReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    short_name = serializers.CharField(allow_blank=True, allow_null=True)
    crest_url = serializers.CharField(allow_blank=True, allow_null=True)


class OverviewPlayerReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    short_name = serializers.CharField(allow_blank=True, allow_null=True)
    position = serializers.CharField(allow_blank=True, allow_null=True)
    shirt_number = serializers.IntegerField(allow_null=True, required=False)
    photo_url = serializers.CharField(allow_blank=True, allow_null=True, required=False)


class LeagueSnapshotRowSerializer(serializers.Serializer):
    position = serializers.IntegerField(allow_null=True)
    team = OverviewTeamReferenceSerializer()
    played = serializers.IntegerField(allow_null=True)
    won = serializers.IntegerField(allow_null=True)
    drawn = serializers.IntegerField(allow_null=True)
    lost = serializers.IntegerField(allow_null=True)
    goals_for = serializers.IntegerField(allow_null=True, required=False)
    goals_against = serializers.IntegerField(allow_null=True, required=False)
    goal_difference = serializers.IntegerField(allow_null=True)
    points = serializers.IntegerField(allow_null=True)
    form_label = serializers.CharField(allow_blank=True, allow_null=True, required=False)


class LeagueSnapshotCardSerializer(serializers.Serializer):
    competition = OverviewCompetitionSerializer()
    synced_at = serializers.DateTimeField(allow_null=True)
    top_rows = LeagueSnapshotRowSerializer(many=True)
    bottom_rows = LeagueSnapshotRowSerializer(many=True)
    cta = OverviewCtaSerializer()


class TrendTeamCardSerializer(serializers.Serializer):
    rank = serializers.IntegerField(allow_null=True)
    team = OverviewTeamReferenceSerializer()
    competition = OverviewCompetitionSerializer()
    summary = serializers.CharField()
    metric_label = serializers.CharField()
    metric_value = serializers.CharField()
    form_label = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    cta = OverviewCtaSerializer()


class TrendPlayerCardSerializer(serializers.Serializer):
    rank = serializers.IntegerField(allow_null=True, required=False)
    player = OverviewPlayerReferenceSerializer()
    team = OverviewTeamReferenceSerializer()
    competition = OverviewCompetitionSerializer()
    summary = serializers.CharField()
    metric_label = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    metric_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cta = OverviewCtaSerializer()


class MatchReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    utc_date = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField(allow_blank=True, allow_null=True)
    home_team = OverviewTeamReferenceSerializer()
    away_team = OverviewTeamReferenceSerializer()
    home_score = serializers.IntegerField(allow_null=True)
    away_score = serializers.IntegerField(allow_null=True)
    score_line = serializers.CharField(allow_blank=True, allow_null=True)
    venue_label = serializers.CharField(allow_blank=True, allow_null=True)


class LeagueMatchPreviewSerializer(serializers.Serializer):
    competition = OverviewCompetitionSerializer()
    synced_at = serializers.DateTimeField(allow_null=True)
    items = MatchReferenceSerializer(many=True)
    cta = OverviewCtaSerializer()


class ClubSpotlightPlayerSerializer(serializers.Serializer):
    team_id = serializers.IntegerField(allow_null=True)
    team_name = serializers.CharField()
    player = OverviewPlayerReferenceSerializer()
    minutes_played = serializers.IntegerField(allow_null=True)
    reason_label = serializers.CharField()


class FirstVsLastLeagueCardSerializer(serializers.Serializer):
    competition = OverviewCompetitionSerializer()
    synced_at = serializers.DateTimeField(allow_null=True)
    leader = LeagueSnapshotRowSerializer(allow_null=True)
    bottom = LeagueSnapshotRowSerializer(allow_null=True)
    spotlight_players = ClubSpotlightPlayerSerializer(many=True)
    cta = OverviewCtaSerializer()


class StreakCardSerializer(serializers.Serializer):
    competition_code = serializers.CharField(allow_blank=True, allow_null=True)
    competition_name = serializers.CharField(allow_blank=True, allow_null=True)
    team_name = serializers.CharField()
    team_id = serializers.IntegerField(allow_null=True)
    crest_url = serializers.CharField(allow_blank=True, allow_null=True)
    streak_value = serializers.IntegerField(allow_null=True)
    label = serializers.CharField()
    summary = serializers.CharField()


class AllTimeStreaksSerializer(serializers.Serializer):
    updated_at = serializers.DateTimeField(allow_null=True)
    all_time = StreakCardSerializer(many=True)
    current = StreakCardSerializer(many=True)
    cta = OverviewCtaSerializer()


class TrendStripSerializer(serializers.Serializer):
    updated_at = serializers.DateTimeField(allow_null=True)
    items = serializers.ListField()


class TopPerformingTeamsSerializer(serializers.Serializer):
    updated_at = serializers.DateTimeField(allow_null=True)
    items = TrendTeamCardSerializer(many=True)


class TopPerformingScorersSerializer(serializers.Serializer):
    updated_at = serializers.DateTimeField(allow_null=True)
    items = TrendPlayerCardSerializer(many=True)


class LatestHatTricksSerializer(serializers.Serializer):
    updated_at = serializers.DateTimeField(allow_null=True)
    items = TrendPlayerCardSerializer(many=True)


class StrikersWithALullSerializer(serializers.Serializer):
    updated_at = serializers.DateTimeField(allow_null=True)
    items = TrendPlayerCardSerializer(many=True)


class LiveFootballOverviewSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    league_order = serializers.ListField(
        child=serializers.CharField(),
    )
    league_snapshot = LeagueSnapshotCardSerializer(many=True)
    top_performing_teams = TopPerformingTeamsSerializer()
    top_performing_scorers = TopPerformingScorersSerializer()
    latest_hat_tricks = LatestHatTricksSerializer()
    strikers_with_a_lull = StrikersWithALullSerializer()
    recent_matches_by_league = LeagueMatchPreviewSerializer(many=True)
    upcoming_matches_by_league = LeagueMatchPreviewSerializer(many=True)
    first_vs_last_by_league = FirstVsLastLeagueCardSerializer(many=True)
    all_time_streaks = AllTimeStreaksSerializer()

class UnsupportedModeSerializer(serializers.Serializer):
    mode = serializers.CharField()
    reason = serializers.CharField()


class CommentaryBlockSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["headline", "observation", "comparison", "caveat"])
    text = serializers.CharField()
    confidence = serializers.ChoiceField(choices=["high", "medium", "low"])
    related_teams = serializers.ListField(child=serializers.CharField(), default=list)


class LeagueMetaItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField(allow_blank=True)
    name = serializers.CharField(allow_blank=True)
    emblem_url = serializers.CharField(allow_blank=True)
    current_season_label = serializers.CharField(allow_blank=True, required=False)
    available_seasons = serializers.ListField(child=serializers.CharField(), default=list)
    supported_modes = serializers.ListField(child=serializers.CharField(), default=list)
    unavailable_modes = UnsupportedModeSerializer(many=True, default=list)


class LeaguesMetaResponseSerializer(serializers.Serializer):
    leagues = LeagueMetaItemSerializer(many=True)


class ExpectedTableRowSerializer(serializers.Serializer):
    team = TeamReferenceSerializer()
    canonical_team_name = serializers.CharField()
    predicted_points = serializers.FloatField()
    predicted_position = serializers.IntegerField()
    position_probabilities = serializers.DictField(child=serializers.FloatField())
    title_probability = serializers.FloatField()
    top_4_probability = serializers.FloatField()
    relegation_probability = serializers.FloatField()
    simulated_wins = serializers.FloatField()
    simulated_draws = serializers.FloatField()
    simulated_losses = serializers.FloatField()
    simulated_goals_for = serializers.FloatField()
    simulated_goals_against = serializers.FloatField()


class LeagueExpectedTableMetadataSerializer(serializers.Serializer):
    supported_modes = serializers.ListField(child=serializers.CharField(), default=list)
    unavailable_modes = UnsupportedModeSerializer(many=True, default=list)
    based_on_matchweek = serializers.IntegerField(allow_null=True)
    data_cutoff_date = serializers.CharField(allow_null=True)
    simulation_count = serializers.IntegerField(allow_null=True)
    engine_versions = serializers.DictField(child=serializers.CharField(), default=dict)
    remaining_fixtures = serializers.IntegerField(allow_null=True)
    total_fixtures_simulated = serializers.IntegerField(allow_null=True)
    total_matchweeks = serializers.IntegerField(allow_null=True, required=False)
    actual_table_source = serializers.CharField()
    expected_table_source = serializers.CharField()


class LeagueExpectedTableResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField()
    mode = serializers.CharField()
    expected_table = ExpectedTableRowSerializer(many=True)
    commentary = CommentaryBlockSerializer(many=True)
    metadata = LeagueExpectedTableMetadataSerializer()


class LeagueComparisonDeltaSerializer(serializers.Serializer):
    team = TeamReferenceSerializer()
    canonical_team_name = serializers.CharField()
    actual_position = serializers.IntegerField()
    expected_position = serializers.IntegerField()
    position_delta = serializers.IntegerField()
    actual_points = serializers.FloatField()
    expected_points = serializers.FloatField()
    points_delta = serializers.FloatField()


class LeagueComparisonMetricsSerializer(serializers.Serializer):
    matched_team_count = serializers.IntegerField()
    average_absolute_position_delta = serializers.FloatField(allow_null=True)
    average_absolute_points_delta = serializers.FloatField(allow_null=True)
    points_correlation = serializers.FloatField(allow_null=True)


class LeagueCompareMetadataSerializer(LeagueExpectedTableMetadataSerializer):
    actual_snapshot_label = serializers.CharField(allow_blank=True, allow_null=True)
    actual_matchday = serializers.IntegerField(allow_null=True)
    actual_synced_at = serializers.DateTimeField(allow_null=True)


class LeagueCompareResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField()
    mode = serializers.CharField()
    actual_table = TableRowSerializer(many=True)
    expected_table = ExpectedTableRowSerializer(many=True)
    deltas = LeagueComparisonDeltaSerializer(many=True)
    comparison_metrics = LeagueComparisonMetricsSerializer()
    commentary = CommentaryBlockSerializer(many=True)
    metadata = LeagueCompareMetadataSerializer()

class LeagueScenarioFixtureSerializer(serializers.Serializer):
    fixture_key = serializers.CharField()
    home_team = TeamReferenceSerializer()
    away_team = TeamReferenceSerializer()


class LeagueScenarioLockedResultInputSerializer(serializers.Serializer):
    fixture_key = serializers.CharField()
    home_goals = serializers.IntegerField(min_value=0)
    away_goals = serializers.IntegerField(min_value=0)


class LeagueScenarioRequestSerializer(serializers.Serializer):
    locked_results = LeagueScenarioLockedResultInputSerializer(many=True, required=False, default=list)


class LeagueScenarioLockedResultSerializer(serializers.Serializer):
    fixture_key = serializers.CharField()
    home_team = TeamReferenceSerializer()
    away_team = TeamReferenceSerializer()
    home_goals = serializers.IntegerField()
    away_goals = serializers.IntegerField()


class LeagueScenarioMetadataSerializer(LeagueExpectedTableMetadataSerializer):
    remaining_fixtures_before_lock = serializers.IntegerField(allow_null=True, required=False)
    remaining_fixtures_after_lock = serializers.IntegerField(allow_null=True, required=False)


class LeagueScenarioResponseSerializer(serializers.Serializer):
    competition = CompetitionListItemSerializer()
    season_label = serializers.CharField()
    mode = serializers.CharField()
    remaining_fixtures = LeagueScenarioFixtureSerializer(many=True)
    locked_results = LeagueScenarioLockedResultSerializer(many=True)
    expected_table = ExpectedTableRowSerializer(many=True)
    commentary = CommentaryBlockSerializer(many=True)
    metadata = LeagueScenarioMetadataSerializer()

class SavedLeagueScenarioLockedFixtureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    fixture_key = serializers.CharField()
    home_team_name = serializers.CharField()
    away_team_name = serializers.CharField()
    home_goals = serializers.IntegerField()
    away_goals = serializers.IntegerField()


class SavedLeagueScenarioListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    competition_id = serializers.IntegerField()
    competition_name = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    season_label = serializers.CharField()
    mode = serializers.CharField()
    based_on_matchweek = serializers.IntegerField(allow_null=True)
    locked_result_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField()


class SavedLeagueScenarioListResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    items = SavedLeagueScenarioListItemSerializer(many=True)


class SavedLeagueScenarioDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    competition = CompetitionListItemSerializer()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    season_label = serializers.CharField()
    mode = serializers.CharField()
    based_on_matchweek = serializers.IntegerField(allow_null=True)
    locked_results = SavedLeagueScenarioLockedFixtureSerializer(many=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class SavedLeagueScenarioCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    locked_results = LeagueScenarioLockedResultInputSerializer(many=True, required=False, default=list)