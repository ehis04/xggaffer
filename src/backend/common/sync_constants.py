# SLA thresholds in seconds — override in settings.py via SLA_* keys
# Fallback defaults

FOOTBALL_DATA_FIXTURE_SLA_SECONDS: int = 900       # 15 min
FOOTBALL_DATA_STANDINGS_SLA_SECONDS: int = 900
FOOTBALL_DATA_SCORERS_SLA_SECONDS: int = 21_600    # 6 hr
FOOTBALL_DATA_SQUADS_SLA_SECONDS: int = 21_600
UNDERSTAT_SLA_SECONDS: int = 21_600
SOFASCORE_SLA_SECONDS: int = 10_800                # 3 hr
NATIVE_STATS_SLA_SECONDS: int = 7_200              # 2 hr
INFERENCE_FEATURES_SLA_SECONDS: int = 86_400       # 24 hr

# Retry policy
DEFAULT_MAX_RETRIES: int = 3
HIGH_RISK_MAX_RETRIES: int = 1   # SofaScore — no retry without valid session

# Degraded threshold
DEFAULT_DEGRADED_THRESHOLD: int = 3   # consecutive failures before DEGRADED

# Budget safety margin
BUDGET_SAFETY_MARGIN: float = 0.10   # abort at 90% of daily limit used