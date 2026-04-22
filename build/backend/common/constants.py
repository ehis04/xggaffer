from django.db import models

# Positions and preferred foot choices for players. Imported into Player model.
class Position(models.TextChoices):
    GK = 'GK', 'Goalkeeper'

    RB = 'RB', 'Right Back'
    RWB = 'RWB', 'Right Wing Back'
    CB = 'CB', 'Centre Back'
    RCB = 'RCB', 'Right Centre Back'
    CCB = 'CCB', 'Central Centre Back'
    LCB = 'LCB', 'Left Centre Back'
    LB = 'LB', 'Left Back'
    LWB = 'LWB', 'Left Wing Back'

    RDM = 'RDM', 'Right Defensive Midfielder'
    CDM = 'CDM', 'Central Defensive Midfielder'
    LDM = 'LDM', 'Left Defensive Midfielder'
    CM = 'CM', 'Central Midfielder'
    RM = 'RM', 'Right Midfielder'
    LM = 'LM', 'Left Midfielder'

    RAM = 'RAM', 'Right Attacking Midfielder'
    CAM = 'CAM', 'Central Attacking Midfielder'
    LAM = 'LAM', 'Left Attacking Midfielder'
    RW = 'RW', 'Right Winger'
    LW = 'LW', 'Left Winger'
    CF = 'CF', 'Centre Forward'
    ST = 'ST', 'Striker'


class PreferredFoot(models.TextChoices):
    RIGHT = 'r', 'Right'
    LEFT = 'l', 'Left'
    BOTH = 'b', 'Both'

class ProviderName(models.TextChoices):
    FOOTBALL_DATA  = 'football_data',  'football-data.org'
    UNDERSTAT      = 'understat',      'Understat'
    SOFASCORE      = 'sofascore',      'SofaScore'
    NATIVE_STATS   = 'native_stats',   'Native Stats'
    THE_ODDS_API   = 'the_odds_api',   'The Odds API'
    TRANSFERMARKT  = 'transfermarkt',  'Transfermarkt'
    WHOSCORED      = 'whoscored',      'WhoScored'


class DatasetName(models.TextChoices):
    FIXTURES              = 'fixtures',              'Fixtures'
    STANDINGS             = 'standings',             'Standings'
    SCORERS               = 'scorers',               'Scorers'
    SQUADS                = 'squads',                'Squads'
    LEAGUE_STATS          = 'league_stats',          'League Stats'
    PLAYER_STATS          = 'player_stats',          'Player Stats'
    CLUB_STATS            = 'club_stats',            'Club Stats'
    OVERVIEW              = 'overview',              'Overview'
    NATIVE_STATS_OVERVIEW = 'native_stats_overview', 'Native Stats Overview'
    ODDS                  = 'odds',                  'Odds'
    INFERENCE_FEATURES    = 'inference_features',    'Inference Features'
    MODEL_ARTEFACT        = 'model_artefact',        'Model Artefact'


class SyncStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    RUNNING = 'running', 'Running'
    SUCCESS = 'success', 'Success'
    FAILED  = 'failed',  'Failed'
    SKIPPED = 'skipped', 'Skipped'


class PublishStatus(models.TextChoices):
    CANDIDATE   = 'candidate',   'Candidate'
    ACTIVE      = 'active',      'Active'
    INVALIDATED = 'invalidated', 'Invalidated'
    FAILED      = 'failed',      'Failed'


class FreshnessStatus(models.TextChoices):
    FRESH    = 'fresh',    'Fresh'
    STALE    = 'stale',    'Stale'
    DEGRADED = 'degraded', 'Degraded'
    UNKNOWN  = 'unknown',  'Unknown'