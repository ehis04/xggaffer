from django.db import models
from django.utils import timezone

class ScrapedMatch(models.Model):
    external_id = models.CharField(max_length=50, unique=True)
    source = models.CharField(max_length=50, default='understat')

    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    match_date = models.DateField()
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)

    home_xg = models.FloatField()
    away_xg = models.FloatField()
    home_goals = models.IntegerField()
    away_goals = models.IntegerField()
    raw_data = models.JSONField(default=dict)
    
    scraped_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-match_date']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['match_date']),
            models.Index(fields=['home_team', 'away_team']),
        ]
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.match_date})"


class ScrapeLog(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]

    scraper_name = models.CharField(max_length=100)
    target = models.CharField(max_length=100)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    matches_found = models.IntegerField(default=0)
    matches_created = models.IntegerField(default=0)
    matches_updated = models.IntegerField(default=0)
    matches_failed = models.IntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.scraper_name} - {self.target} ({self.status})"


class TeamStats(models.Model):
    team_name = models.CharField(max_length=100)
    season = models.CharField(max_length=10)
    league = models.CharField(max_length=50)

    matches_played = models.IntegerField(default=0)
    total_xg_for = models.FloatField(default=0)
    total_xg_against = models.FloatField(default=0)
    avg_xg_for = models.FloatField(default=0)
    avg_xg_against = models.FloatField(default=0)

    last_5_xg_for = models.FloatField(default=0)
    last_5_xg_against = models.FloatField(default=0)

    home_avg_xg = models.FloatField(default=0)
    away_avg_xg = models.FloatField(default=0)

    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['team_name', 'season', 'league']
    
    def __str__(self):
        return f"{self.team_name} - {self.league} {self.season}"


class PredictionModel(models.Model):
    name = models.CharField(max_length=100)
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    model_type = models.CharField(max_length=50, default='decision_tree')
    model_file = models.CharField(max_length=200)
    
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    
    training_samples = models.IntegerField(default=0)
    test_samples = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['league', 'season', 'model_type']
    
    def __str__(self):
        return f"{self.name} ({self.league} {self.season})"


class Prediction(models.Model):
    model_used = models.ForeignKey(PredictionModel, on_delete=models.CASCADE)
    
    team = models.CharField(max_length=100)
    opponent = models.CharField(max_length=100)
    is_home = models.BooleanField()
    
    team_xg = models.FloatField()
    opponent_xg = models.FloatField()
    
    predicted_result = models.CharField(max_length=1)
    win_probability = models.FloatField()
    confidence = models.FloatField()
    
    actual_result = models.CharField(max_length=1, blank=True, null=True)
    was_correct = models.BooleanField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.team} vs {self.opponent} - Predicted: {self.predicted_result}"


class ModelRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('complete', 'Complete'),
    ]
    
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    votes = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-votes', '-requested_at']
        unique_together = ['league', 'season']
    
    def __str__(self):
        return f"{self.league} {self.season} ({self.votes} votes)"



class EloRating(models.Model):
    team = models.CharField(max_length=100)
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    date = models.DateField()
    match_id = models.CharField(max_length=50)
    elo_before = models.FloatField()
    elo_after = models.FloatField()

    class Meta:
        indexes = [
            models.Index(fields=['team', 'date']),
            models.Index(fields=['league', 'season']),
            models.Index(fields=['team', '-date']),
        ]
        ordering = ['date']

    def __str__(self):
        return f"{self.team} {self.date}: {self.elo_before:.0f} → {self.elo_after:.0f}"


class CurrentEloRating(models.Model):
    team = models.CharField(max_length=100, unique=True)
    league = models.CharField(max_length=50)
    elo = models.FloatField()
    last_match_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-elo']

    def __str__(self):
        return f"{self.team} ({self.league}): {self.elo:.0f}"


def populate_elo_from_csv(csv_path: str | None = None) -> dict[str, int]:
    import pandas as pd
    from apps.predictions.ml.models.match_outcome.config import PROCESSED_DIR

    if csv_path is None:
        csv_path = str(PROCESSED_DIR / "elo_ratings.csv")

    df = pd.read_csv(csv_path, parse_dates=["date"])

    EloRating.objects.all().delete()
    CurrentEloRating.objects.all().delete()

    home_rows = df.rename(columns={
        "home_team": "team",
        "home_elo_before": "elo_before",
        "home_elo_after": "elo_after",
    })[["team", "league", "season", "date", "match_id", "elo_before", "elo_after"]]

    away_rows = df.rename(columns={
        "away_team": "team",
        "away_elo_before": "elo_before",
        "away_elo_after": "elo_after",
    })[["team", "league", "season", "date", "match_id", "elo_before", "elo_after"]]

    all_rows = pd.concat([home_rows, away_rows], ignore_index=True)

    BATCH_SIZE = 5000
    elo_objects = [
        EloRating(
            team=row.team,
            league=row.league,
            season=str(row.season),
            date=row.date,
            match_id=str(row.match_id),
            elo_before=row.elo_before,
            elo_after=row.elo_after,
        )
        for row in all_rows.itertuples(index=False)
    ]
    EloRating.objects.bulk_create(elo_objects, batch_size=BATCH_SIZE)

    latest = all_rows.sort_values("date").groupby("team").last().reset_index()

    current_objects = [
        CurrentEloRating(
            team=row.team,
            league=row.league,
            elo=row.elo_after,
            last_match_date=row.date,
        )
        for row in latest.itertuples(index=False)
    ]
    CurrentEloRating.objects.bulk_create(current_objects)

    return {
        "history_rows": len(elo_objects),
        "current_ratings": len(current_objects),
    }

class SimulationResult(models.Model):
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    freeze_date = models.DateField()
    results = models.JSONField()
    n_simulations = models.IntegerField()
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["league", "season", "freeze_date"]
        ordering = ["-computed_at"]

    def __str__(self):
        return f"Simulation {self.league} {self.season} @ {self.freeze_date}"

class Bookmaker(models.Model):
    class Source(models.TextChoices):
        THE_ODDS_API = 'the_odds_api', 'The Odds API'
        FDCOUK = 'fdcouk', 'Football-Data.co.uk'
        MANUAL = 'manual', 'Manual'

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.THE_ODDS_API,
    )
    region = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['source']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class FixtureOddsSnapshot(models.Model):
    class MarketType(models.TextChoices):
        MATCH_RESULT = '1x2', '1X2'

    bookmaker_source = models.CharField(max_length=50)
    external_fixture_id = models.CharField(max_length=100)
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    commence_time = models.DateTimeField()
    fetched_at = models.DateTimeField(default=timezone.now)
    market_type = models.CharField(
        max_length=20,
        choices=MarketType.choices,
        default=MarketType.MATCH_RESULT,
    )
    is_consensus_snapshot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['external_fixture_id']),
            models.Index(fields=['league', 'season']),
            models.Index(fields=['fetched_at']),
            models.Index(fields=['bookmaker_source', 'market_type']),
        ]

    def fixture_label(self):
        return f"{self.home_team} vs {self.away_team} ({self.league} {self.season})"

    def __str__(self):
        return self.fixture_label()


class BookmakerQuote(models.Model):
    snapshot = models.ForeignKey(
        FixtureOddsSnapshot,
        on_delete=models.CASCADE,
        related_name='quotes',
    )
    bookmaker = models.ForeignKey(
        Bookmaker,
        on_delete=models.CASCADE,
        related_name='quotes',
        db_index=False,
    )
    home_odds = models.FloatField()
    draw_odds = models.FloatField()
    away_odds = models.FloatField()
    implied_home = models.FloatField()
    implied_draw = models.FloatField()
    implied_away = models.FloatField()
    devig_home = models.FloatField()
    devig_draw = models.FloatField()
    devig_away = models.FloatField()
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['bookmaker__name']
        constraints = [
            models.UniqueConstraint(
                fields=['snapshot', 'bookmaker'],
                name='unique_bookmaker_quote_per_snapshot',
            ),
        ]
        indexes = [
            models.Index(fields=['bookmaker']),
            models.Index(fields=['last_seen_at']),
        ]

    def __str__(self):
        return f"{self.bookmaker.name} - {self.snapshot.fixture_label()}"


class HistoricalMarketBenchmark(models.Model):
    league = models.CharField(max_length=50)
    season = models.CharField(max_length=10)
    sample_size = models.PositiveIntegerField()
    model_accuracy = models.FloatField()
    market_favourite_accuracy = models.FloatField(null=True, blank=True)
    model_brier_score = models.FloatField(null=True, blank=True)
    market_brier_score = models.FloatField(null=True, blank=True)
    evaluation_scope = models.CharField(max_length=50)
    source_label = models.CharField(max_length=100)
    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['league', 'season']
        constraints = [
            models.UniqueConstraint(
                fields=['league', 'season', 'evaluation_scope', 'source_label'],
                name='unique_historical_market_benchmark_scope',
            ),
        ]
        indexes = [
            models.Index(fields=['league']),
            models.Index(fields=['season']),
        ]

    def __str__(self):
        return f"{self.league} {self.season} {self.source_label}"

class ModelArtefactRecord(models.Model):
    algorithm = models.CharField(max_length=64)
    path = models.CharField(max_length=512)
    trained_at = models.DateTimeField()
    promoted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['algorithm', 'is_active']),
        ]

    def __str__(self):
        active = 'ACTIVE' if self.is_active else 'inactive'
        return f'ModelArtefactRecord({self.algorithm}, {active}, {self.path})'


class InferenceSnapshotRecord(models.Model):
    algorithm = models.CharField(max_length=64)
    feature_set_version = models.CharField(max_length=64)
    snapshot_published_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['algorithm', 'is_active']),
        ]

    def __str__(self):
        active = 'ACTIVE' if self.is_active else 'inactive'
        return f'InferenceSnapshotRecord({self.algorithm}, {active}, {self.snapshot_published_at})'