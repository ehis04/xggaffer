from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from apps.predictions.ml.models.availability.config import (
    INJURY_CATEGORIES,
    INJURY_CATEGORY_OTHER,
    INJURY_SPELLS_PATH,
    INJURY_TYPE_KEYWORDS,
    PLAYER_ID_MAPPING_PATH,
    RAW_INJURIES_DIR,
    SUSPENSION_KEYWORDS,
)
from services.providers.transfermarkt.client import (
    TransfermarktClient,
    TransfermarktError,
)

logger = logging.getLogger(__name__)

INJURY_SPELL_COLUMNS = [
    "tm_player_id",
    "understat_player_id",
    "player_name",
    "injury_type_raw",
    "injury_type_category",
    "start_date",
    "end_date",
    "days_out",
    "games_missed",
    "season_raw",
    "is_open_spell",
]


def normalise_injury_type(raw: str) -> str:
    if not isinstance(raw, str):
        return INJURY_CATEGORY_OTHER

    lowered = raw.lower()

    for category, keywords in INJURY_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                return category

    return INJURY_CATEGORY_OTHER


def is_suspension(raw: str) -> bool:
    if not isinstance(raw, str):
        return False

    lowered = raw.lower()
    return any(keyword in lowered for keyword in SUSPENSION_KEYWORDS)


def collect_player_injuries(
    tm_player_id: int,
    understat_player_id: int,
    player_name: str,
    client: TransfermarktClient,
    output_dir: Path = RAW_INJURIES_DIR,
    skip_if_exists: bool = True,
) -> Optional[pd.DataFrame]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{tm_player_id}_injuries.csv"

    if skip_if_exists and output_path.exists():
        return pd.read_csv(output_path)

    try:
        soup = client.fetch_injury_page(tm_player_id=tm_player_id)
    except TransfermarktError as exc:
        logger.warning("Fetch failed for tm_player_id=%d: %s", tm_player_id, exc)
        return None

    raw_spells = client.parse_injury_spells(soup)

    rows: list[dict] = []
    for spell in raw_spells:
        injury_type_raw = spell.get("injury_type_raw", "")

        if is_suspension(injury_type_raw):
            continue

        rows.append({
            "tm_player_id": tm_player_id,
            "understat_player_id": understat_player_id,
            "player_name": player_name,
            "injury_type_raw": injury_type_raw,
            "injury_type_category": normalise_injury_type(injury_type_raw),
            "start_date": spell.get("start_date"),
            "end_date": spell.get("end_date"),
            "days_out": spell.get("days_out"),
            "games_missed": spell.get("games_missed"),
            "season_raw": spell.get("season"),
            "is_open_spell": spell.get("end_date") is None,
        })

    df = pd.DataFrame(rows, columns=INJURY_SPELL_COLUMNS)
    df.to_csv(output_path, index=False)
    return df


def collect_all_injuries(
    mapping_path: Path = PLAYER_ID_MAPPING_PATH,
    output_dir: Path = RAW_INJURIES_DIR,
    limit: Optional[int] = None,
) -> None:
    mapping = pd.read_csv(mapping_path)
    matched = mapping[mapping["understat_player_id"].notna()].copy()
    matched["understat_player_id"] = matched["understat_player_id"].astype(int)

    unique_players = (
        matched.sort_values("season", ascending=False)
        .drop_duplicates(subset=["tm_player_id"], keep="first")
        [["tm_player_id", "understat_player_id", "tm_name"]]
        .rename(columns={"tm_name": "player_name"})
    )

    if limit is not None:
        unique_players = unique_players.head(limit)

    total = len(unique_players)
    logger.info("Starting injury collection for %d unique players", total)

    collected = 0
    skipped = 0
    failed = 0
    start_time = time.monotonic()

    with TransfermarktClient() as client:
        for index, row in enumerate(unique_players.itertuples(index=False), start=1):
            tm_player_id = int(row.tm_player_id)
            understat_player_id = int(row.understat_player_id)
            player_name = row.player_name

            output_path = output_dir / f"{tm_player_id}_injuries.csv"
            if output_path.exists():
                skipped += 1
                continue

            result = collect_player_injuries(
                tm_player_id=tm_player_id,
                understat_player_id=understat_player_id,
                player_name=player_name,
                client=client,
                output_dir=output_dir,
                skip_if_exists=True,
            )

            if result is None:
                failed += 1
            else:
                collected += 1

            if index % 50 == 0:
                elapsed = time.monotonic() - start_time
                rate = (collected + failed) / elapsed if elapsed > 0 else 0
                remaining = (total - index) / rate if rate > 0 else 0
                logger.info(
                    "Progress: %d/%d (collected=%d skipped=%d failed=%d) | "
                    "rate=%.2f/s | eta=%.1f min",
                    index, total, collected, skipped, failed, rate, remaining / 60,
                )

    logger.info(
        "Collection complete: collected=%d skipped=%d failed=%d",
        collected, skipped, failed,
    )


def merge_injury_spells(
    raw_dir: Path = RAW_INJURIES_DIR,
    output_path: Path = INJURY_SPELLS_PATH,
) -> pd.DataFrame:
    csv_files = sorted(raw_dir.glob("*_injuries.csv"))
    logger.info("Merging %d per-player CSVs", len(csv_files))

    frames: list[pd.DataFrame] = []
    for path in csv_files:
        try:
            df = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if df.empty:
            continue
        frames.append(df)

    if not frames:
        logger.warning("No injury CSVs to merge")
        return pd.DataFrame(columns=INJURY_SPELL_COLUMNS)

    merged = pd.concat(frames, ignore_index=True)
    merged = merged[~merged["injury_type_raw"].apply(is_suspension)].copy()
    merged["injury_type_category"] = merged["injury_type_raw"].apply(normalise_injury_type)
    merged = merged[INJURY_SPELL_COLUMNS]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    logger.info("Saved merged spells: %s (%d rows)", output_path, len(merged))

    return merged


def print_injury_summary(df: pd.DataFrame) -> None:
    if df.empty:
        print("No injury spells.")
        return

    total = len(df)
    unique_players = df["tm_player_id"].nunique()
    open_spells = df["is_open_spell"].sum()

    print(f"Total injury spells: {total}")
    print(f"Unique players with spells: {unique_players}")
    print(f"Open spells (right-censored): {open_spells}")
    print()

    print("Spells by injury type category:")
    print(df["injury_type_category"].value_counts().to_string())
    print()

    print("Mean days_out by category:")
    stats = df[df["days_out"].notna()].groupby("injury_type_category")["days_out"].agg(
        ["count", "mean", "median"]
    )
    print(stats.round(1).to_string())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of players (for testing)")
    parser.add_argument("--merge-only", action="store_true", help="Skip collection, just merge existing CSVs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if not args.merge_only:
        collect_all_injuries(limit=args.limit)

    merged = merge_injury_spells()
    print_injury_summary(merged)


if __name__ == "__main__":
    main()