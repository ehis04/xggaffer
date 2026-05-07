import numpy as np
import pandas as pd
import pytest

from apps.predictions.ml.features import rolling
from apps.predictions.ml.features.rolling import (
    ROLLING_STATS,
    ROLLING_WINDOWS,
    build_all_features,
    build_features,
    compute_team_rolling_features,
    load_match_history,
    to_team_match_rows,
)


SAMPLE_LEAGUES = ["EPL"]
SAMPLE_SEASONS = ["2020", "2021", "2022", "2023", "2024"]


@pytest.fixture(scope="module")
def match_data():
    try:
        matches = load_match_history(SAMPLE_LEAGUES, SAMPLE_SEASONS)
    except FileNotFoundError:
        pytest.skip("Match data files not available")
    return matches


@pytest.fixture(scope="module")
def team_match_rows(match_data):
    return to_team_match_rows(match_data)


@pytest.fixture(scope="module")
def full_features():
    try:
        df = build_all_features(SAMPLE_LEAGUES, SAMPLE_SEASONS)
    except FileNotFoundError:
        pytest.skip("Match data files not available")
    return df


def _write_match_csv(path, rows):
    frame = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_load_match_history_keeps_secondary_source_future_fixtures(tmp_path, monkeypatch):
    processed_dir = tmp_path / "processed" / "matches"
    legacy_dir = tmp_path / "raw" / "understat" / "matches"
    merged_file = tmp_path / "processed" / "matches" / "merged" / "all.csv"
    legacy_merged_file = tmp_path / "raw" / "understat" / "merged" / "all.csv"

    monkeypatch.setattr(rolling, "PROCESSED_MATCHES_DIR", processed_dir)
    monkeypatch.setattr(rolling, "LEGACY_MATCHES_DIR", legacy_dir)
    monkeypatch.setattr(rolling, "MERGED_MATCHES_FILE", merged_file)
    monkeypatch.setattr(rolling, "LEGACY_MERGED_MATCHES_FILE", legacy_merged_file)

    common = {
        "league": "EPL",
        "season": "2025",
        "home_xa": 0.5,
        "away_xa": 0.4,
        "home_shots": 10,
        "away_shots": 8,
        "home_key_passes": 7,
        "away_key_passes": 5,
        "home_xpts": 2.0,
        "away_xpts": 0.8,
    }
    played_understat = {
        **common,
        "match_id": "u-1",
        "date": "2025-08-15",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_goals": 2,
        "away_goals": 1,
        "home_xg": 1.8,
        "away_xg": 0.9,
    }
    played_sofascore_duplicate = {
        **played_understat,
        "match_id": "s-1",
        "home_goals": 9,
        "away_goals": 9,
    }
    future_sofascore_only = {
        **common,
        "match_id": "s-2",
        "date": "2026-05-24",
        "home_team": "Brighton & Hove Albion",
        "away_team": "Tottenham Hotspur",
        "home_goals": np.nan,
        "away_goals": np.nan,
        "home_xg": np.nan,
        "away_xg": np.nan,
    }

    _write_match_csv(
        processed_dir / "2025" / "matches_understat_EPL_2025_canonical.csv",
        [played_understat],
    )
    _write_match_csv(
        processed_dir / "2025" / "matches_sofascore_EPL_2025_canonical.csv",
        [played_sofascore_duplicate, future_sofascore_only],
    )

    matches = load_match_history(["EPL"], ["2025"])

    assert len(matches) == 2
    played = matches[
        (matches["home_team"] == "Arsenal")
        & (matches["away_team"] == "Chelsea")
    ].iloc[0]
    assert played["match_id"] == "u-1"
    assert played["home_goals"] == 2

    future = matches[
        (matches["home_team"] == "Brighton")
        & (matches["away_team"] == "Tottenham")
    ].iloc[0]
    assert future["match_id"] == "s-2"
    assert pd.isna(future["home_goals"])



class TestNoFutureData:

    def test_rolling_excludes_current_match_batch(self, match_data, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date")

        test_positions = [1, 5, 10, 20, 30]

        for pos in test_positions:
            if pos >= len(arsenal):
                continue

            test_row = arsenal.iloc[pos]
            test_date = test_row["date"]
            test_xg = test_row["xg"]

            prior = arsenal.iloc[:pos]
            assert (prior["date"] < test_date).all() or (prior["date"] == test_date).sum() == 0, (
                f"Position {pos}: found match at or after {test_date} in history"
            )

    def test_rolling_excludes_current_match_single(self, match_data, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date")

        mid_idx = len(arsenal) // 2
        test_row = arsenal.iloc[mid_idx]
        kickoff = test_row["date"]

        features = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=kickoff,
        )

        prior = arsenal[arsenal["date"] < kickoff]
        expected_xg_5 = prior.tail(5)["xg"].mean()

        assert abs(features["rolling_xg_5"] - expected_xg_5) < 0.0001, (
            f"Single-match rolling_xg_5 mismatch: "
            f"{features['rolling_xg_5']} != {expected_xg_5}"
        )

    def test_batch_and_single_match_agree(self, match_data, team_match_rows, full_features):
        arsenal_matches = match_data[
            (match_data["home_team"] == "Arsenal") |
            (match_data["away_team"] == "Arsenal")
        ].sort_values("date")

        test_match = arsenal_matches.iloc[len(arsenal_matches) // 2]
        match_id = test_match["match_id"]
        kickoff = test_match["date"]

        single_features = build_features(
            match_id=match_id,
            home_team=test_match["home_team"],
            away_team=test_match["away_team"],
            kickoff=kickoff,
            all_matches=match_data,
            all_team_matches=team_match_rows,
        )

        batch_row = full_features[full_features["match_id"] == match_id]
        assert len(batch_row) == 1, f"Match {match_id} not found in batch output"
        batch_row = batch_row.iloc[0]

        for col in ["home_rolling_xg_5", "away_rolling_xg_5",
                     "home_rolling_xga_10", "away_rolling_xga_10"]:
            if col in single_features and col in batch_row.index:
                single_val = single_features[col]
                batch_val = batch_row[col]
                if pd.notna(single_val) and pd.notna(batch_val):
                    assert abs(single_val - batch_val) < 0.0001, (
                        f"{col}: single={single_val}, batch={batch_val}"
                    )

    def test_no_future_data_sampled_matches(self, match_data, team_match_rows, full_features):
        rng = np.random.RandomState(42)
        sample_size = min(20, len(full_features))
        sample_indices = rng.choice(len(full_features), size=sample_size, replace=False)

        for idx in sample_indices:
            row = full_features.iloc[idx]
            match_date = row["date"]
            home_team = row["home_team"]

            home_history = team_match_rows[
                (team_match_rows["team"] == home_team) &
                (team_match_rows["date"] < match_date)
            ]

            if home_history.empty:
                assert pd.isna(row.get("home_rolling_xg_5", np.nan)), (
                    f"Match {row['match_id']}: no history but features are not NaN"
                )
                continue

            latest_history_date = home_history["date"].max()
            assert latest_history_date < match_date, (
                f"Match {row['match_id']}: history includes date {latest_history_date} "
                f"which is not before match date {match_date}"
            )



class TestRollingWindowCorrectness:

    def test_rolling_xg_5_manual_calculation(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date").reset_index(drop=True)

        for test_pos in [5, 10, 15, 25]:
            if test_pos >= len(arsenal):
                continue

            expected = arsenal.iloc[test_pos - 5 : test_pos]["xg"].mean()

            features = compute_team_rolling_features(
                team_matches=arsenal,
                as_of=arsenal.iloc[test_pos]["date"],
            )

            assert abs(features["rolling_xg_5"] - expected) < 0.0001, (
                f"Position {test_pos}: expected {expected}, got {features['rolling_xg_5']}"
            )

    def test_rolling_window_20_uses_correct_count(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date").reset_index(drop=True)

        test_pos = min(30, len(arsenal) - 1)
        as_of = arsenal.iloc[test_pos]["date"]

        features = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=as_of,
        )

        expected = arsenal.iloc[test_pos - 20 : test_pos]["xg"].mean()
        assert abs(features["rolling_xg_20"] - expected) < 0.0001



class TestChronologicalOrder:

    def test_team_match_rows_sorted_per_team(self, team_match_rows):
        for team in ["Arsenal", "Liverpool", "Bayern Munich", "Barcelona"]:
            team_df = team_match_rows[team_match_rows["team"] == team]
            if team_df.empty:
                continue
            dates = team_df["date"].values
            assert (dates[:-1] <= dates[1:]).all(), (
                f"{team}: team-match rows are not chronologically sorted"
            )

    def test_match_history_sorted_globally(self, match_data):
        dates = match_data["date"].values
        assert (dates[:-1] <= dates[1:]).all(), (
            "Match history is not sorted by date"
        )



class TestFeatureCompleteness:

    def test_mid_season_no_nan(self, full_features):
        mid_season = full_features[
            (full_features["season"].astype(str) == "2022") &
            (full_features["league"] == "EPL")
        ].sort_values("date")

        if mid_season.empty:
            pytest.skip("No 2022 EPL data available")

        late_season = mid_season.iloc[len(mid_season) // 2 :]

        rolling_cols = [
            c for c in late_season.columns
            if c.startswith("home_rolling_xg_") or c.startswith("away_rolling_xg_")
        ]

        for col in rolling_cols:
            nan_count = late_season[col].isna().sum()
            assert nan_count == 0, (
                f"Mid-season 2022 EPL has {nan_count} NaN values in {col}"
            )

    def test_all_expected_columns_present(self, full_features):
        expected_prefixes = [
            "home_rolling_xg_5", "away_rolling_xg_5",
            "home_rolling_xga_5", "away_rolling_xga_5",
            "home_rolling_points_5", "away_rolling_points_5",
            "home_ewm_xg_5", "away_ewm_xg_5",
            "home_days_rest", "away_days_rest",
            "xg_diff_5", "xga_diff_5",
            "is_home",
        ]
        for col in expected_prefixes:
            assert col in full_features.columns, f"Missing column: {col}"

    def test_correct_row_count(self, match_data, full_features):
        assert len(full_features) == len(match_data), (
            f"Feature output has {len(full_features)} rows, "
            f"expected {len(match_data)} (one per match)"
        )



class TestEarlySeasonGracefulDegradation:

    def test_first_match_has_nan_rolling(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date")

        first_date = arsenal.iloc[0]["date"]

        features = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=first_date,
        )

        assert features == {}, (
            f"First match should have empty features, got {features}"
        )

    def test_second_match_uses_one_prior(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date").reset_index(drop=True)

        second_date = arsenal.iloc[1]["date"]
        first_xg = arsenal.iloc[0]["xg"]

        features = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=second_date,
        )

        assert abs(features["rolling_xg_5"] - first_xg) < 0.0001, (
            f"Second match rolling_xg_5 should be first match xg ({first_xg}), "
            f"got {features['rolling_xg_5']}"
        )

    def test_third_match_uses_two_prior(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date").reset_index(drop=True)

        third_date = arsenal.iloc[2]["date"]
        expected = arsenal.iloc[0:2]["xg"].mean()

        features = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=third_date,
        )

        assert abs(features["rolling_xg_5"] - expected) < 0.0001

    def test_no_crash_on_empty_history(self, team_match_rows):
        fake_date = pd.Timestamp("2000-01-01")
        arsenal = team_match_rows[team_match_rows["team"] == "Arsenal"]

        features = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=fake_date,
        )

        assert features == {}



class TestFeatureValuesChangeOverTime:

    def test_same_team_different_matchweeks(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date").reset_index(drop=True)

        early_pos = 5
        late_pos = min(25, len(arsenal) - 1)

        if late_pos <= early_pos:
            pytest.skip("Not enough matches for comparison")

        early_feats = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=arsenal.iloc[early_pos]["date"],
        )
        late_feats = compute_team_rolling_features(
            team_matches=arsenal,
            as_of=arsenal.iloc[late_pos]["date"],
        )

        differences_found = False
        for key in early_feats:
            if key in late_feats and key.startswith("rolling_"):
                if abs(early_feats[key] - late_feats[key]) > 0.001:
                    differences_found = True
                    break

        assert differences_found, (
            "Rolling features at matchweek 5 and matchweek 25 should differ"
        )

    def test_schedule_features_vary(self, team_match_rows):
        arsenal = team_match_rows[
            team_match_rows["team"] == "Arsenal"
        ].sort_values("date").reset_index(drop=True)

        days_rest_values = set()
        for pos in [5, 10, 15, 20]:
            if pos >= len(arsenal):
                continue
            feats = compute_team_rolling_features(
                team_matches=arsenal,
                as_of=arsenal.iloc[pos]["date"],
            )
            if "days_rest" in feats:
                days_rest_values.add(round(feats["days_rest"], 1))

        assert len(days_rest_values) > 1, (
            "days_rest should vary between matches"
        )



class TestDiffFeatures:

    def test_diff_equals_home_minus_away(self, full_features):
        mid_season = full_features[
            full_features["home_rolling_xg_5"].notna() &
            full_features["away_rolling_xg_5"].notna()
        ]

        if mid_season.empty:
            pytest.skip("No complete rows available")

        sample = mid_season.iloc[len(mid_season) // 2]

        expected_diff = sample["home_rolling_xg_5"] - sample["away_rolling_xg_5"]
        actual_diff = sample["xg_diff_5"]

        assert abs(actual_diff - expected_diff) < 0.0001, (
            f"xg_diff_5 should be home - away: "
            f"expected {expected_diff}, got {actual_diff}"
        )
