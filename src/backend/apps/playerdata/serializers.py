"""
Serializers for player data summary, overview, and comparison responses

Defines nested response shapes for player identities, club context, provider coverage, metrics, explanations, and comparison output
"""

from rest_framework import serializers


# Serializer for shared season and competition context
class SeasonContextSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    season = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for provider coverage and freshness details
class ProviderCoverageSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    has_data = serializers.BooleanField(required=False, allow_null=True)
    coverage_status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    freshness_label = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_updated_at = serializers.DateTimeField(required=False, allow_null=True)
    last_synced_at = serializers.DateTimeField(required=False, allow_null=True)
    matches_sampled = serializers.IntegerField(required=False, allow_null=True)
    minutes_sampled = serializers.IntegerField(required=False, allow_null=True)
    coverage_notes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for generated summary explanations
class SummaryExplanationSerializer(serializers.Serializer):
    headline = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    strengths = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    watchouts = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    notes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for one summary metric
class SummaryMetricSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.FloatField(required=False, allow_null=True)
    formatted_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rank = serializers.IntegerField(required=False, allow_null=True)
    percentile = serializers.FloatField(required=False, allow_null=True)
    sample_size = serializers.IntegerField(required=False, allow_null=True)
    is_available = serializers.BooleanField(required=False, allow_null=True)


# Serializer for player identity data
class PlayerIdentitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    display_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    short_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nationality = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    age = serializers.IntegerField(required=False, allow_null=True)
    photo_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for club identity data
class ClubIdentitySerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    short_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    crest_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for one player season enrichment summary
class PlayerSeasonEnrichmentSummarySerializer(serializers.Serializer):
    player = PlayerIdentitySerializer()
    club = ClubIdentitySerializer(required=False, allow_null=True)
    context = SeasonContextSerializer(required=False, allow_null=True)
    metrics = SummaryMetricSerializer(many=True, required=False, allow_null=True)
    explanation = SummaryExplanationSerializer(required=False, allow_null=True)
    provider_coverage = ProviderCoverageSerializer(required=False, allow_null=True)
    has_summary_data = serializers.BooleanField(required=False, allow_null=True)
    missing_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for one club season enrichment summary
class ClubSeasonEnrichmentSummarySerializer(serializers.Serializer):
    club = ClubIdentitySerializer()
    context = SeasonContextSerializer(required=False, allow_null=True)
    metrics = SummaryMetricSerializer(many=True, required=False, allow_null=True)
    explanation = SummaryExplanationSerializer(required=False, allow_null=True)
    provider_coverage = ProviderCoverageSerializer(required=False, allow_null=True)
    has_summary_data = serializers.BooleanField(required=False, allow_null=True)
    missing_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for one side of a player comparison
class ComparisonSideSerializer(serializers.Serializer):
    player = PlayerIdentitySerializer()
    club = ClubIdentitySerializer(required=False, allow_null=True)


# Serializer for one player comparison metric
class ComparisonMetricSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    player_a_value = serializers.FloatField(required=False, allow_null=True)
    player_a_formatted = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    player_b_value = serializers.FloatField(required=False, allow_null=True)
    player_b_formatted = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    delta = serializers.FloatField(required=False, allow_null=True)
    formatted_delta = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    winner = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_tie = serializers.BooleanField(required=False, allow_null=True)


# Serializer for the overall comparison winner
class ComparisonWinnerSerializer(serializers.Serializer):
    winner = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    winner_player_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for the legacy player comparison response
class PlayerComparisonSerializer(serializers.Serializer):
    player_a = ComparisonSideSerializer()
    player_b = ComparisonSideSerializer()
    context = SeasonContextSerializer(required=False, allow_null=True)
    metrics = ComparisonMetricSerializer(many=True, required=False, allow_null=True)
    overall_winner = ComparisonWinnerSerializer(required=False, allow_null=True)
    explanation = SummaryExplanationSerializer(required=False, allow_null=True)
    provider_coverage = ProviderCoverageSerializer(required=False, allow_null=True)
    has_comparison_data = serializers.BooleanField(required=False, allow_null=True)
    missing_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for one enriched player list item
class EnrichedPlayerListItemSerializer(serializers.Serializer):
    player = PlayerIdentitySerializer()
    club = ClubIdentitySerializer(required=False, allow_null=True)
    context = SeasonContextSerializer(required=False, allow_null=True)
    key_metrics = SummaryMetricSerializer(many=True, required=False, allow_null=True)
    explanation_snippet = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    provider_coverage = ProviderCoverageSerializer(required=False, allow_null=True)
    has_enrichment_data = serializers.BooleanField(required=False, allow_null=True)


# Serializer for player identity in overview responses
class PlayerOverviewIdentitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    display_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    short_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    primary_position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    secondary_positions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    nationality = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    age = serializers.IntegerField(required=False, allow_null=True)
    photo_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for club identity in player overview responses
class PlayerOverviewClubSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    short_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    crest_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for season, team, and source context in player overview responses
class PlayerOverviewContextSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    season = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_id = serializers.IntegerField(required=False, allow_null=True)
    team_id = serializers.IntegerField(required=False, allow_null=True)
    team_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    livefootball_source = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for deterministic player overview explanation text
class PlayerOverviewExplanationSerializer(serializers.Serializer):
    headline = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    strengths = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    watchouts = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    notes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    sentences = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for metric source preference details
class MetricSourcePreferenceSerializer(serializers.Serializer):
    concept = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    primary_source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferred_provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for one metric in a player overview
class PlayerOverviewMetricSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    value = serializers.FloatField(required=False, allow_null=True)
    formatted_value = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rank = serializers.IntegerField(required=False, allow_null=True)
    percentile = serializers.FloatField(required=False, allow_null=True)
    sample_size = serializers.IntegerField(required=False, allow_null=True)
    is_available = serializers.BooleanField(required=False, allow_null=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferred_provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_preference = MetricSourcePreferenceSerializer(required=False, allow_null=True)


# Serializer for a grouped set of player overview metrics
class PlayerOverviewMetricGroupSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    metrics = PlayerOverviewMetricSerializer(many=True, required=False, allow_null=True)


# Serializer for one source detail block
class SourceDetailSerializer(serializers.Serializer):
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    providers = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    has_data = serializers.BooleanField(required=False, allow_null=True)
    coverage_status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    freshness_label = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_updated_at = serializers.DateTimeField(required=False, allow_null=True)
    last_synced_at = serializers.DateTimeField(required=False, allow_null=True)
    matches_sampled = serializers.IntegerField(required=False, allow_null=True)
    minutes_sampled = serializers.IntegerField(required=False, allow_null=True)
    coverage_notes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    team = serializers.JSONField(required=False, allow_null=True)
    competition = serializers.JSONField(required=False, allow_null=True)
    season_label = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    record_count = serializers.IntegerField(required=False, allow_null=True)
    seasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    competitions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    items = serializers.ListField(
        child=serializers.JSONField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for merged provider coverage across multiple sources
class MergedProviderCoverageSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    has_data = serializers.BooleanField(required=False, allow_null=True)
    coverage_status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    freshness_label = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_updated_at = serializers.DateTimeField(required=False, allow_null=True)
    last_synced_at = serializers.DateTimeField(required=False, allow_null=True)
    matches_sampled = serializers.IntegerField(required=False, allow_null=True)
    minutes_sampled = serializers.IntegerField(required=False, allow_null=True)
    coverage_notes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    available_sources = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    missing_sources = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    source_count = serializers.IntegerField(required=False, allow_null=True)
    available_source_count = serializers.IntegerField(required=False, allow_null=True)
    missing_source_count = serializers.IntegerField(required=False, allow_null=True)
    source_details = serializers.DictField(
        child=serializers.JSONField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    player_a = serializers.JSONField(required=False, allow_null=True)
    player_b = serializers.JSONField(required=False, allow_null=True)


# Serializer for one source preference rule
class SourcePreferenceRuleSerializer(serializers.Serializer):
    key = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    primary_source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferred_provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for available source preferences and metric rules
class SourcePreferenceBlockSerializer(serializers.Serializer):
    available_sources = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    rules = SourcePreferenceRuleSerializer(many=True, required=False, allow_null=True)
    metric_rules = SourcePreferenceRuleSerializer(many=True, required=False, allow_null=True)


# Serializer for a full player overview response
class PlayerOverviewSerializer(serializers.Serializer):
    player = PlayerOverviewIdentitySerializer()
    club = PlayerOverviewClubSerializer(required=False, allow_null=True)
    context = PlayerOverviewContextSerializer(required=False, allow_null=True)
    general_overview = PlayerOverviewExplanationSerializer(required=False, allow_null=True)
    metric_groups = PlayerOverviewMetricGroupSerializer(many=True, required=False, allow_null=True)
    provider_coverage = MergedProviderCoverageSerializer(required=False, allow_null=True)
    source_preferences = SourcePreferenceBlockSerializer(required=False, allow_null=True)
    livefootball_context = serializers.JSONField(required=False, allow_null=True)
    playerdata_context = serializers.JSONField(required=False, allow_null=True)
    has_overview_data = serializers.BooleanField(required=False, allow_null=True)
    missing_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )


# Serializer for context shared by two-player overview comparisons
class ComparisonOverviewContextSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    season = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    competition_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    same_provider = serializers.BooleanField(required=False, allow_null=True)
    same_season = serializers.BooleanField(required=False, allow_null=True)
    same_competition = serializers.BooleanField(required=False, allow_null=True)
    left_last_synced_at = serializers.DateTimeField(required=False, allow_null=True)
    right_last_synced_at = serializers.DateTimeField(required=False, allow_null=True)
    sentence = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Serializer for one metric in a two-player overview comparison
class PlayerOverviewComparisonMetricSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    player_a_value = serializers.FloatField(required=False, allow_null=True)
    player_a_formatted = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    player_b_value = serializers.FloatField(required=False, allow_null=True)
    player_b_formatted = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    delta = serializers.FloatField(required=False, allow_null=True)
    formatted_delta = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    winner = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_tie = serializers.BooleanField(required=False, allow_null=True)
    is_comparable = serializers.BooleanField(required=False, allow_null=True)
    sentence = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    preferred_provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_preference = MetricSourcePreferenceSerializer(required=False, allow_null=True)


# Serializer for a grouped set of comparison metrics
class PlayerOverviewComparisonMetricGroupSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    metrics = PlayerOverviewComparisonMetricSerializer(many=True, required=False, allow_null=True)


# Serializer for a full two-player overview comparison response
class PlayerOverviewComparisonSerializer(serializers.Serializer):
    player_a = PlayerOverviewSerializer()
    player_b = PlayerOverviewSerializer()
    context = ComparisonOverviewContextSerializer(required=False, allow_null=True)
    general_overview = PlayerOverviewExplanationSerializer(required=False, allow_null=True)
    metric_groups = PlayerOverviewComparisonMetricGroupSerializer(many=True, required=False, allow_null=True)
    summary_lines = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )
    overall_winner = ComparisonWinnerSerializer(required=False, allow_null=True)
    provider_coverage = MergedProviderCoverageSerializer(required=False, allow_null=True)
    source_preferences = SourcePreferenceBlockSerializer(required=False, allow_null=True)
    has_comparison_data = serializers.BooleanField(required=False, allow_null=True)
    missing_reasons = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        allow_null=True,
    )