from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Optional

import pandas as pd

from apps.predictions.ml.models.availability.config import (
    PLAYER_ID_MAPPING_PATH,
    PROCESSED_DIR,
)
from services.providers.transfermarkt.client import (
    TransfermarktClient,
    TransfermarktError,
)

logger = logging.getLogger(__name__)

RAW_DOBS_DIR = PROCESSED_DIR.parent / "raw" / "player_dobs"
PLAYER_DOBS_PATH = PROCESSED_DIR / "player_dobs.csv"

DOB_COLUMNS = ["tm_player_id", "understat_player_id", "player_name", "dob"]


def collect_player_dob(
    tm_player_id: int,
    understat_player_id: int,
    player_name: str,
    client: TransfermarktClient,
    output_dir: Path = RAW_DOBS_DIR,
    skip_if_exists: bool = True,
) -> Optional[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{tm_player_id}_dob.csv"

    if skip_if_exists and output_path.exists():
        existing = pd.read_csv(output_path)
        if len(existing) > 0:
            return existing.iloc[0].to_dict()

    try:
        soup = client.fetch_player_profile(tm_player_id=tm_player_id)
    except TransfermarktError as exc:
        logger.warning("Fetch failed for tm_player_id=%d: %s", tm_player_id, exc)
        return None

    dob = client.parse_player_dob(soup)

    row = {
        "tm_player_id": tm_player_id,
        "understat_player_id": understat_player_id,
        "player_name": player_name,
        "dob": dob,
    }

    pd.DataFrame([row], columns=DOB_COLUMNS).to_csv(output_path, index=False)
    return row


def collect_all_dobs(
    mapping_path: Path = PLAYER_ID_MAPPING_PATH,
    output_dir: Path = RAW_DOBS_DIR,
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
    logger.info("Starting DOB collection for %d unique players", total)

    collected = 0
    skipped = 0
    failed = 0
    start_time = time.monotonic()

    with TransfermarktClient() as client:
        for index, row in enumerate(unique_players.itertuples(index=False), start=1):
            tm_player_id = int(row.tm_player_id)
            understat_player_id = int(row.understat_player_id)
            player_name = row.player_name

            output_path = output_dir / f"{tm_player_id}_dob.csv"
            if output_path.exists():
                skipped += 1
                continue

            result = collect_player_dob(
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


def merge_dobs(
    raw_dir: Path = RAW_DOBS_DIR,
    output_path: Path = PLAYER_DOBS_PATH,
) -> pd.DataFrame:
    csv_files = sorted(raw_dir.glob("*_dob.csv"))
    logger.info("Merging %d per-player DOB CSVs", len(csv_files))

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
        logger.warning("No DOB CSVs to merge")
        return pd.DataFrame(columns=DOB_COLUMNS)

    merged = pd.concat(frames, ignore_index=True)
    merged = merged[DOB_COLUMNS]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    total = len(merged)
    with_dob = merged["dob"].notna().sum()
    logger.info(
        "Saved merged DOBs: %s (%d rows, %d with DOB, %d missing)",
        output_path, total, with_dob, total - with_dob,
    )

    return merged


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--merge-only", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if not args.merge_only:
        collect_all_dobs(limit=args.limit)

    merge_dobs()


if __name__ == "__main__":
    main()