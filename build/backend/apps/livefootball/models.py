from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.players.models import ExternalProvider, Player


class Competition(models.Model):
    """
    App-owned readable competition / league record.

    This is a synced read model for live football features.
    It does not replace canonical club or player identity models.
    """

    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    external_id = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=255)
    area_name = models.CharField(max_length=255, blank=True)
    emblem_url = models.URLField(blank=True)

    current_season_label = models.CharField(max_length=20, blank=True)
    current_season_start_date = models.DateField(null=True, blank=True)
    current_season_end_date = models.DateField(null=True, blank=True)
    current_matchday = models.PositiveSmallIntegerField(null=True, blank=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "provider", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                name="lf_comp_provider_ext_uq",
            ),
            models.UniqueConstraint(
                fields=["provider", "code"],
                condition=~Q(code=""),
                name="lf_comp_provider_code_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "name"],
                name="lf_comp_provider_name_idx",
            ),
            models.Index(
                fields=["provider", "code"],
                name="lf_comp_provider_code_idx",
            ),
            models.Index(
                fields=["provider", "current_season_label"],
                name="lf_comp_provider_season_idx",
            ),
        ]

    def __str__(self) -> str:
        code = f" ({self.code})" if self.code else ""
        return f"{self.name}{code}"


class TeamDirectoryEntry(models.Model):
    """
    Competition-scoped team directory row used for lookup and selection flows.

    This is not the club operational model.
    Club linkage should still resolve through provider identity mappings when needed.
    """

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )
    season_label = models.CharField(max_length=20)

    external_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255, blank=True)
    tla = models.CharField(max_length=10, blank=True)
    area_name = models.CharField(max_length=255, blank=True)

    emblem_url = models.URLField(blank=True)
    venue = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["competition", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "season_label", "provider", "external_id"],
                name="lf_team_comp_season_ext_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["competition", "season_label", "name"],
                name="lf_team_comp_name_idx",
            ),
            models.Index(
                fields=["provider", "external_id"],
                name="lf_team_provider_ext_idx",
            ),
            models.Index(
                fields=["competition", "season_label"],
                name="lf_team_comp_season_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} | {self.season_label}"


class PlayerDirectoryEntry(models.Model):
    """
    Team-scoped player directory row used for team/league lookup and search.

    This remains a synced read model.
    canonical_player is optional and soft-linked where identity resolution exists.
    """

    team = models.ForeignKey(
        TeamDirectoryEntry,
        on_delete=models.CASCADE,
        related_name="players",
    )
    canonical_player = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="livefootball_directory_entries",
    )
    provider = models.CharField(
        max_length=50,
        choices=ExternalProvider.choices,
    )

    external_player_id = models.CharField(max_length=100)
    player_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    primary_position = models.CharField(max_length=50, blank=True)
    raw_position = models.CharField(max_length=100, blank=True)
    squad_number = models.PositiveSmallIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["team", "player_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "provider", "external_player_id"],
                name="lf_player_team_provider_ext_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["team", "player_name"],
                name="lf_player_team_name_idx",
            ),
            models.Index(
                fields=["provider", "external_player_id"],
                name="lf_player_provider_ext_idx",
            ),
            models.Index(
                fields=["canonical_player"],
                name="lf_player_canonical_idx",
            ),
            models.Index(
                fields=["last_name", "first_name"],
                name="lf_player_name_parts_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.player_name


class CompetitionTableSnapshot(models.Model):
    """
    A stored table snapshot for a competition/season.

    snapshot_label can be values such as:
    - latest
    - matchday-28
    - final
    """

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="table_snapshots",
    )
    season_label = models.CharField(max_length=20)
    snapshot_label = models.CharField(max_length=100, default="latest", blank=True)
    matchday = models.PositiveSmallIntegerField(null=True, blank=True)

    fetched_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["competition", "-season_label", "-synced_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "season_label", "snapshot_label"],
                name="lf_table_snapshot_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["competition", "season_label"],
                name="lf_table_comp_season_idx",
            ),
            models.Index(
                fields=["competition", "season_label", "matchday"],
                name="lf_table_comp_matchday_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.competition} | {self.season_label} | {self.snapshot_label}"


class CompetitionTableRow(models.Model):
    """
    Stored row within a competition table snapshot.
    """

    snapshot = models.ForeignKey(
        CompetitionTableSnapshot,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    team = models.ForeignKey(
        TeamDirectoryEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="table_rows",
    )

    position = models.PositiveSmallIntegerField()
    external_team_id = models.CharField(max_length=100, blank=True)
    team_name = models.CharField(max_length=255)

    played = models.PositiveSmallIntegerField(default=0)
    won = models.PositiveSmallIntegerField(default=0)
    drawn = models.PositiveSmallIntegerField(default=0)
    lost = models.PositiveSmallIntegerField(default=0)

    goals_for = models.PositiveSmallIntegerField(default=0)
    goals_against = models.PositiveSmallIntegerField(default=0)
    goal_difference = models.SmallIntegerField(default=0)
    points = models.PositiveSmallIntegerField(default=0)

    form = models.CharField(max_length=50, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["snapshot", "position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "position"],
                name="lf_table_row_snapshot_pos_uq",
            ),
            models.UniqueConstraint(
                fields=["snapshot", "external_team_id"],
                condition=~Q(external_team_id=""),
                name="lf_table_row_snapshot_team_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["snapshot", "position"],
                name="lf_table_row_snapshot_pos_idx",
            ),
            models.Index(
                fields=["external_team_id"],
                name="lf_table_row_ext_team_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.snapshot} | {self.position}. {self.team_name}"


class CompetitionFixture(models.Model):
    """
    Stored competition fixture / match record.
    """

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="fixtures",
    )
    season_label = models.CharField(max_length=20)

    external_match_id = models.CharField(max_length=100)
    status = models.CharField(max_length=50, blank=True)
    kickoff_at = models.DateTimeField(null=True, blank=True)
    matchday = models.PositiveSmallIntegerField(null=True, blank=True)

    home_team = models.ForeignKey(
        TeamDirectoryEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="home_fixtures",
    )
    away_team = models.ForeignKey(
        TeamDirectoryEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="away_fixtures",
    )

    home_external_team_id = models.CharField(max_length=100, blank=True)
    home_team_name = models.CharField(max_length=255)
    away_external_team_id = models.CharField(max_length=100, blank=True)
    away_team_name = models.CharField(max_length=255)

    home_score = models.SmallIntegerField(null=True, blank=True)
    away_score = models.SmallIntegerField(null=True, blank=True)

    synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["competition", "kickoff_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "season_label", "external_match_id"],
                name="lf_fixture_comp_season_ext_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["competition", "season_label", "kickoff_at"],
                name="lf_fix_comp_kickoff_idx",
            ),
            models.Index(
                fields=["competition", "season_label", "status"],
                name="lf_fix_comp_status_idx",
            ),
            models.Index(
                fields=["home_external_team_id"],
                name="lf_fix_home_team_idx",
            ),
            models.Index(
                fields=["away_external_team_id"],
                name="lf_fix_away_team_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.home_team_name} vs {self.away_team_name}"


class CompetitionTopScorer(models.Model):
    """
    Stored top-scorer row for a competition/season snapshot.
    """

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="top_scorers",
    )
    season_label = models.CharField(max_length=20)

    canonical_player = models.ForeignKey(
        Player,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="livefootball_top_scorer_entries",
    )
    team = models.ForeignKey(
        TeamDirectoryEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="top_scorer_entries",
    )

    rank = models.PositiveSmallIntegerField(default=0)

    external_player_id = models.CharField(max_length=100, blank=True)
    player_name = models.CharField(max_length=255)
    team_name = models.CharField(max_length=255, blank=True)
    external_team_id = models.CharField(max_length=100, blank=True)

    goals = models.PositiveSmallIntegerField(default=0)
    penalties = models.PositiveSmallIntegerField(null=True, blank=True)

    synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["competition", "season_label", "rank", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "season_label", "rank"],
                name="lf_scorer_comp_season_rank_uq",
            ),
            models.UniqueConstraint(
                fields=["competition", "season_label", "external_player_id"],
                condition=~Q(external_player_id=""),
                name="lf_scorer_comp_player_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["competition", "season_label", "rank"],
                name="lf_scorer_comp_rank_idx",
            ),
            models.Index(
                fields=["player_name"],
                name="lf_scorer_player_name_idx",
            ),
            models.Index(
                fields=["external_team_id"],
                name="lf_scorer_ext_team_idx",
            ),
            models.Index(
                fields=["canonical_player"],
                name="lf_scorer_canonical_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.player_name} | {self.goals}"

class SavedLeagueScenario(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="livefootball_saved_scenarios",
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="saved_scenarios",
    )

    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    season_label = models.CharField(max_length=20)
    mode = models.CharField(max_length=50)
    based_on_matchweek = models.PositiveSmallIntegerField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "updated_at"],
                name="lf_saved_user_updated_idx",
            ),
            models.Index(
                fields=["user", "competition"],
                name="lf_saved_user_comp_idx",
            ),
            models.Index(
                fields=["user", "season_label", "mode"],
                name="lf_saved_user_mode_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} | {self.competition} | {self.season_label}"


class SavedLeagueScenarioLockedFixture(models.Model):
    scenario = models.ForeignKey(
        SavedLeagueScenario,
        on_delete=models.CASCADE,
        related_name="locked_fixtures",
    )

    fixture_key = models.CharField(max_length=255)
    home_team_name = models.CharField(max_length=255)
    away_team_name = models.CharField(max_length=255)
    home_goals = models.PositiveSmallIntegerField()
    away_goals = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scenario", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["scenario", "fixture_key"],
                name="lf_saved_fix_scenario_key_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["scenario"],
                name="lf_saved_fix_scenario_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.scenario.title} | {self.fixture_key}"