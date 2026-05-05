from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


class TestDevig:

    def test_devig_single_sums_to_one(self):
        from apps.predictions.ml.data.odds.devig import devig_single
        h, d, a = devig_single(2.10, 3.40, 3.50)
        assert abs(h + d + a - 1.0) < 1e-9

    def test_devig_single_preserves_ordering(self):
        from apps.predictions.ml.data.odds.devig import devig_single
        h, d, a = devig_single(1.50, 4.00, 6.00)
        assert h > d > a

    def test_devig_single_home_favourite(self):
        from apps.predictions.ml.data.odds.devig import devig_single
        h, d, a = devig_single(1.20, 6.00, 12.00)
        assert h > 0.7

    def test_devig_single_away_favourite(self):
        from apps.predictions.ml.data.odds.devig import devig_single
        h, d, a = devig_single(6.00, 4.00, 1.50)
        assert a > h

    def test_devig_single_equal_odds(self):
        from apps.predictions.ml.data.odds.devig import devig_single
        h, d, a = devig_single(3.00, 3.00, 3.00)
        assert abs(h - d) < 1e-9
        assert abs(d - a) < 1e-9
        assert abs(h - 1.0 / 3.0) < 1e-9

    def test_devig_columns_all_sum_to_one(self):
        from apps.predictions.ml.data.odds.devig import devig_columns
        df = pd.DataFrame({
            "H": [2.10, 1.50, 3.00],
            "D": [3.40, 4.00, 3.20],
            "A": [3.50, 6.00, 2.30],
        })
        result = devig_columns(df, "H", "D", "A")
        sums = result["market_home_prob"] + result["market_draw_prob"] + result["market_away_prob"]
        assert (sums - 1.0).abs().max() < 1e-9

    def test_devig_columns_overround_above_one(self):
        from apps.predictions.ml.data.odds.devig import devig_columns
        df = pd.DataFrame({
            "H": [2.10],
            "D": [3.40],
            "A": [3.50],
        })
        result = devig_columns(df, "H", "D", "A")
        assert result["overround"].iloc[0] > 1.0

    def test_devig_columns_overround_reasonable_range(self):
        from apps.predictions.ml.data.odds.devig import devig_columns
        df = pd.DataFrame({
            "H": [2.10],
            "D": [3.40],
            "A": [3.50],
        })
        result = devig_columns(df, "H", "D", "A")
        assert 1.01 < result["overround"].iloc[0] < 1.15

    def test_validate_odds_rejects_below_minimum(self):
        from apps.predictions.ml.data.odds.devig import validate_odds
        assert validate_odds(0.50, 3.00, 3.00) is False

    def test_validate_odds_rejects_above_maximum(self):
        from apps.predictions.ml.data.odds.devig import validate_odds
        assert validate_odds(2.00, 3.00, 600.0) is False

    def test_validate_odds_rejects_nan(self):
        from apps.predictions.ml.data.odds.devig import validate_odds
        assert validate_odds(float("nan"), 3.00, 3.00) is False

    def test_validate_odds_rejects_inf(self):
        from apps.predictions.ml.data.odds.devig import validate_odds
        assert validate_odds(float("inf"), 3.00, 3.00) is False

    def test_validate_odds_accepts_normal(self):
        from apps.predictions.ml.data.odds.devig import validate_odds
        assert validate_odds(2.10, 3.40, 3.50) is True

    def test_validate_odds_accepts_extreme_favourite(self):
        from apps.predictions.ml.data.odds.devig import validate_odds
        assert validate_odds(1.02, 15.0, 25.0) is True


class TestDownloadConstants:

    def test_season_mapping_covers_all_seasons(self):
        from apps.predictions.ml.data.odds.download import UNDERSTAT_TO_FDCOUK_SEASON
        for year in range(2014, 2025):
            assert str(year) in UNDERSTAT_TO_FDCOUK_SEASON

    def test_league_mapping_covers_five_leagues(self):
        from apps.predictions.ml.data.odds.download import LEAGUE_TO_FDCOUK_CODE
        expected = {"EPL", "La_Liga", "Bundesliga", "Serie_A", "Ligue_1"}
        assert set(LEAGUE_TO_FDCOUK_CODE.keys()) == expected

    def test_build_url_format(self):
        from apps.predictions.ml.data.odds.download import build_url
        url = build_url("EPL", "2024")
        assert url == "https://www.football-data.co.uk/mmz4281/2425/E0.csv"

    def test_build_url_la_liga(self):
        from apps.predictions.ml.data.odds.download import build_url
        url = build_url("La_Liga", "2014")
        assert "SP1" in url
        assert "1415" in url


class TestTeamNameMappings:

    def test_to_canonical_epl_teams(self):
        from data_collection.config.team_name_mappings import to_canonical
        assert to_canonical("Man City", "football_data_co_uk") == "Manchester City"
        assert to_canonical("Man United", "football_data_co_uk") == "Manchester United"
        assert to_canonical("Nott'm Forest", "football_data_co_uk") == "Nottingham Forest"
        assert to_canonical("Wolves", "football_data_co_uk") == "Wolverhampton Wanderers"
        assert to_canonical("QPR", "football_data_co_uk") == "Queens Park Rangers"
        assert to_canonical("West Brom", "football_data_co_uk") == "West Bromwich Albion"

    def test_to_canonical_la_liga_teams(self):
        from data_collection.config.team_name_mappings import to_canonical
        assert to_canonical("Ath Bilbao", "football_data_co_uk") == "Athletic Club"
        assert to_canonical("Ath Madrid", "football_data_co_uk") == "Atletico Madrid"
        assert to_canonical("Betis", "football_data_co_uk") == "Real Betis"
        assert to_canonical("Celta", "football_data_co_uk") == "Celta Vigo"
        assert to_canonical("Sociedad", "football_data_co_uk") == "Real Sociedad"
        assert to_canonical("Vallecano", "football_data_co_uk") == "Rayo Vallecano"

    def test_to_canonical_bundesliga_teams(self):
        from data_collection.config.team_name_mappings import to_canonical
        assert to_canonical("Dortmund", "football_data_co_uk") == "Borussia Dortmund"
        assert to_canonical("Leverkusen", "football_data_co_uk") == "Bayer Leverkusen"
        assert to_canonical("M'gladbach", "football_data_co_uk") == "Borussia M.Gladbach"
        assert to_canonical("Ein Frankfurt", "football_data_co_uk") == "Eintracht Frankfurt"
        assert to_canonical("Stuttgart", "football_data_co_uk") == "VfB Stuttgart"
        assert to_canonical("RB Leipzig", "football_data_co_uk") == "RasenBallsport Leipzig"

    def test_to_canonical_serie_a_teams(self):
        from data_collection.config.team_name_mappings import to_canonical
        assert to_canonical("Milan", "football_data_co_uk") == "AC Milan"
        assert to_canonical("Spal", "football_data_co_uk") == "SPAL 2013"
        assert to_canonical("Parma", "football_data_co_uk") == "Parma Calcio 1913"

    def test_to_canonical_ligue_1_teams(self):
        from data_collection.config.team_name_mappings import to_canonical
        assert to_canonical("Paris SG", "football_data_co_uk") == "Paris Saint Germain"
        assert to_canonical("St Etienne", "football_data_co_uk") == "Saint-Etienne"
        assert to_canonical("Bastia", "football_data_co_uk") == "SC Bastia"
        assert to_canonical("Clermont", "football_data_co_uk") == "Clermont Foot"

    def test_to_canonical_unknown_team_raises(self):
        from data_collection.config.team_name_mappings import to_canonical
        with pytest.raises(KeyError):
            to_canonical("Nonexistent FC", "football_data_co_uk")

    def test_to_canonical_identical_names(self):
        from data_collection.config.team_name_mappings import to_canonical
        assert to_canonical("Arsenal", "football_data_co_uk") == "Arsenal"
        assert to_canonical("Liverpool", "football_data_co_uk") == "Liverpool"
        assert to_canonical("Barcelona", "football_data_co_uk") == "Barcelona"


class TestFeatureColumns:

    def test_base_feature_count(self):
        from apps.predictions.ml.models.match_outcome.prepare_data import BASE_FEATURE_COLUMNS
        assert len(BASE_FEATURE_COLUMNS) == 84

    def test_odds_feature_count(self):
        from apps.predictions.ml.models.match_outcome.prepare_data import ODDS_FEATURES
        assert len(ODDS_FEATURES) == 3

    def test_with_odds_feature_count(self):
        from apps.predictions.ml.models.match_outcome.prepare_data import FEATURE_COLUMNS_WITH_ODDS
        assert len(FEATURE_COLUMNS_WITH_ODDS) == 87

    def test_base_equals_feature_columns(self):
        from apps.predictions.ml.models.match_outcome.prepare_data import BASE_FEATURE_COLUMNS, FEATURE_COLUMNS
        assert FEATURE_COLUMNS == BASE_FEATURE_COLUMNS

    def test_no_duplicate_features(self):
        from apps.predictions.ml.models.match_outcome.prepare_data import FEATURE_COLUMNS_WITH_ODDS
        assert len(FEATURE_COLUMNS_WITH_ODDS) == len(set(FEATURE_COLUMNS_WITH_ODDS))

    def test_odds_features_at_end(self):
        from apps.predictions.ml.models.match_outcome.prepare_data import FEATURE_COLUMNS_WITH_ODDS, ODDS_FEATURES
        assert FEATURE_COLUMNS_WITH_ODDS[-3:] == ODDS_FEATURES


class TestParseIntegration:

    @pytest.fixture(autouse=True)
    def _check_data_available(self):
        from apps.predictions.ml.data.odds.download import build_output_path
        path = build_output_path("EPL", "2024")
        if not path.exists():
            pytest.skip("Odds data not downloaded — run download first")

    def test_parse_single_csv_returns_dataframe(self):
        from apps.predictions.ml.data.odds.download import build_output_path
        from apps.predictions.ml.data.odds.parse import parse_single_csv
        path = build_output_path("EPL", "2024")
        df = parse_single_csv(path, "EPL", "2024")
        assert df is not None
        assert len(df) > 300

    def test_parse_single_csv_has_required_columns(self):
        from apps.predictions.ml.data.odds.download import build_output_path
        from apps.predictions.ml.data.odds.parse import parse_single_csv
        path = build_output_path("EPL", "2024")
        df = parse_single_csv(path, "EPL", "2024")
        for col in ["market_home_prob", "market_draw_prob", "market_away_prob", "date"]:
            assert col in df.columns

    def test_parse_probs_sum_to_one(self):
        from apps.predictions.ml.data.odds.download import build_output_path
        from apps.predictions.ml.data.odds.parse import parse_single_csv
        path = build_output_path("EPL", "2024")
        df = parse_single_csv(path, "EPL", "2024")
        sums = df["market_home_prob"] + df["market_draw_prob"] + df["market_away_prob"]
        assert (sums - 1.0).abs().max() < 1e-6

    def test_parse_probs_in_valid_range(self):
        from apps.predictions.ml.data.odds.download import build_output_path
        from apps.predictions.ml.data.odds.parse import parse_single_csv
        path = build_output_path("EPL", "2024")
        df = parse_single_csv(path, "EPL", "2024")
        for col in ["market_home_prob", "market_draw_prob", "market_away_prob"]:
            assert (df[col] > 0).all()
            assert (df[col] < 1).all()


class TestMergeIntegration:

    @pytest.fixture(autouse=True)
    def _check_data_available(self):
        from apps.predictions.ml.data.odds.download import build_output_path
        from apps.predictions.ml.features.rolling import MERGED_MATCHES_FILE
        odds_path = build_output_path("EPL", "2024")
        if not odds_path.exists():
            pytest.skip("Odds data not downloaded")
        if not MERGED_MATCHES_FILE.exists():
            pytest.skip("Match data not available")

    def test_merge_match_rate_above_threshold(self):
        from apps.predictions.ml.features.rolling import load_match_history
        from apps.predictions.ml.data.odds.merge import merge_odds_to_matches
        matches = load_match_history(leagues=["EPL"], seasons=["2024"])
        merged = merge_odds_to_matches(matches, leagues=["EPL"], seasons=["2024"])
        matched = merged["market_home_prob"].notna().sum()
        rate = matched / len(merged)
        assert rate > 0.95

    def test_merge_preserves_match_count(self):
        from apps.predictions.ml.features.rolling import load_match_history
        from apps.predictions.ml.data.odds.merge import merge_odds_to_matches
        matches = load_match_history(leagues=["EPL"], seasons=["2024"])
        original_count = len(matches)
        merged = merge_odds_to_matches(matches, leagues=["EPL"], seasons=["2024"])
        assert len(merged) == original_count

    def test_merge_odds_in_valid_range(self):
        from apps.predictions.ml.features.rolling import load_match_history
        from apps.predictions.ml.data.odds.merge import merge_odds_to_matches
        matches = load_match_history(leagues=["EPL"], seasons=["2024"])
        merged = merge_odds_to_matches(matches, leagues=["EPL"], seasons=["2024"])
        has_odds = merged[merged["market_home_prob"].notna()]
        for col in ["market_home_prob", "market_draw_prob", "market_away_prob"]:
            assert (has_odds[col] > 0).all()
            assert (has_odds[col] < 1).all()