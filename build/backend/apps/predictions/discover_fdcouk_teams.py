#temp file
from ml.data.odds.parse import parse_all

df = parse_all()

for league in sorted(df["league"].unique()):
    league_df = df[df["league"] == league]
    all_teams = sorted(
        set(league_df["fdcouk_home_team"].unique()) | set(league_df["fdcouk_away_team"].unique())
    )
    print(f"\n{'=' * 60}")
    print(f"{league} ({len(all_teams)} teams)")
    print(f"{'=' * 60}")
    for team in all_teams:
        print(f"  {repr(team)}")