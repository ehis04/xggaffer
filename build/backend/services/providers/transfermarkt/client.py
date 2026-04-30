"""
Transfermarkt client for squad, player profile, and injury data scraping

Handles polite Transfermarkt requests, retry behaviour, HTML parsing, and conversion of scraped page sections into internal dictionaries
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from common.provider_policy import exponential_backoff_seconds

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transfermarkt request configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.transfermarkt.com"
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 5
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}

DATE_FORMAT_TM = "%d/%m/%Y"
INJURY_SPELLS_CONTAINER_INDEX = 0
EXPECTED_INJURY_HEADERS = ["Season", "Injury", "from", "until", "Days", "Games missed"]

SQUAD_CONTAINER_INDEX = 0
PLAYER_PROFILE_URL_FRAGMENT = "/profil/spieler/"
TEAM_STARTSEITE_FRAGMENT = "/startseite/verein/"

TM_LEAGUE_COMPETITION_CODES = {
    "EPL": "GB1",
    "La_Liga": "ES1",
    "Bundesliga": "L1",
    "Serie_A": "IT1",
    "Ligue_1": "FR1",
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

# Base error raised by Transfermarkt provider helpers
class TransfermarktError(Exception):
    pass


# ---------------------------------------------------------------------------
# Transfermarkt client
# ---------------------------------------------------------------------------

# Client for fetching and parsing Transfermarkt pages
class TransfermarktClient:

    # Set up the Transfermarkt session and request delay
    def __init__(self, delay_seconds: float = REQUEST_DELAY_SECONDS):
        self._delay_seconds = delay_seconds
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        self._last_request_time: Optional[float] = None

    # Fetch the squad page for a team and season
    def fetch_squad_page(self, tm_team_id: int, season: int) -> BeautifulSoup:
        url = f"{BASE_URL}/team/startseite/verein/{tm_team_id}/saison_id/{season}"
        return self._get(url)

    # Fetch the injury history page for a player
    def fetch_injury_page(self, tm_player_id: int) -> BeautifulSoup:
        url = f"{BASE_URL}/player/verletzungen/spieler/{tm_player_id}"
        return self._get(url)

    # Fetch the profile page for a player
    def fetch_player_profile(self, tm_player_id: int, player_slug: str = "player") -> BeautifulSoup:
        url = f"{BASE_URL}/{player_slug}/profil/spieler/{tm_player_id}"
        return self._get(url)

    # Parse a player's date of birth from a profile page
    def parse_player_dob(self, soup: BeautifulSoup) -> Optional[str]:
        bold_spans = soup.find_all("span", class_="info-table__content--bold")
        for span in bold_spans:
            text = span.get_text(strip=True)
            parsed = self._extract_dob_from_text(text)
            if parsed is not None:
                return parsed

        header_spans = soup.find_all("span", attrs={"data-header__content": True})
        for span in header_spans:
            text = span.get_text(strip=True)
            parsed = self._extract_dob_from_text(text)
            if parsed is not None:
                return parsed

        return None

    # Extract a date of birth from Transfermarkt profile text
    @staticmethod
    def _extract_dob_from_text(text: str) -> Optional[str]:
        if not text or "/" not in text:
            return None
        candidate = text.split("(")[0].strip()
        try:
            parsed = datetime.strptime(candidate, DATE_FORMAT_TM)
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d")

    # Fetch and parse league team IDs for a supported league season
    def fetch_league_teams(self, league: str, season: int) -> list[dict]:
        competition_code = TM_LEAGUE_COMPETITION_CODES.get(league)
        if competition_code is None:
            raise TransfermarktError(f"Unknown league: {league}")

        url = f"{BASE_URL}/league/startseite/wettbewerb/{competition_code}/plus/?saison_id={season}"
        soup = self._get(url)

        teams: list[dict] = []
        seen_ids: set[int] = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if TEAM_STARTSEITE_FRAGMENT not in href or "/saison_id/" not in href:
                continue

            parts = href.split(TEAM_STARTSEITE_FRAGMENT)[1].split("/")
            try:
                tm_team_id = int(parts[0])
            except (ValueError, IndexError):
                continue

            if tm_team_id in seen_ids:
                continue

            name = link.get_text(strip=True)
            if not name:
                continue

            seen_ids.add(tm_team_id)
            teams.append({"tm_team_id": tm_team_id, "tm_team_name": name})

        return teams

    # Parse injury spell rows from a Transfermarkt injury page
    def parse_injury_spells(self, soup: BeautifulSoup) -> list[dict]:
        containers = soup.find_all("div", class_="responsive-table")
        if len(containers) <= INJURY_SPELLS_CONTAINER_INDEX:
            return []

        table = containers[INJURY_SPELLS_CONTAINER_INDEX].find("table")
        if table is None:
            return []

        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        if headers != EXPECTED_INJURY_HEADERS:
            logger.warning("Unexpected injury table headers: %s", headers)
            return []

        tbody = table.find("tbody")
        if tbody is None:
            return []

        spells: list[dict] = []
        for row in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) != len(EXPECTED_INJURY_HEADERS):
                continue

            spell = self._parse_spell_row(cells)
            if spell is not None:
                spells.append(spell)

        return spells

    # Parse squad rows from a Transfermarkt squad page
    def parse_squad(self, soup: BeautifulSoup) -> list[dict]:
        containers = soup.find_all("div", class_="responsive-table")
        if len(containers) <= SQUAD_CONTAINER_INDEX:
            return []

        table = containers[SQUAD_CONTAINER_INDEX].find("table")
        if table is None:
            return []

        tbody = table.find("tbody")
        if tbody is None:
            return []

        players: list[dict] = []
        for row in tbody.find_all("tr", recursive=False):
            player = self._parse_squad_row(row)
            if player is not None:
                players.append(player)

        return players

    # Close the underlying requests session
    def close(self) -> None:
        self._session.close()

    # Enter the client context manager
    def __enter__(self) -> "TransfermarktClient":
        return self

    # Exit the client context manager and close the session
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # Parse one squad table row into a player dictionary
    @staticmethod
    def _parse_squad_row(row) -> Optional[dict]:
        profile_link = None
        for link in row.find_all("a", href=True):
            if PLAYER_PROFILE_URL_FRAGMENT in link["href"]:
                profile_link = link
                break

        if profile_link is None:
            return None

        tm_player_id = TransfermarktClient._extract_tm_player_id(profile_link["href"])
        if tm_player_id is None:
            return None

        player_name = profile_link.get_text(strip=True)
        if not player_name:
            return None

        position = None
        position_td = row.find("td", class_="posrela")
        if position_td is not None:
            inline_table = position_td.find("table")
            if inline_table is not None:
                rows_inside = inline_table.find_all("tr")
                if len(rows_inside) >= 2:
                    position = rows_inside[1].get_text(strip=True) or None

        return {
            "tm_player_id": tm_player_id,
            "player_name": player_name,
            "player_slug": TransfermarktClient._extract_player_slug(profile_link["href"]),
            "position": position,
        }

    # Extract the Transfermarkt player ID from a profile URL
    @staticmethod
    def _extract_tm_player_id(href: str) -> Optional[int]:
        parts = href.split(PLAYER_PROFILE_URL_FRAGMENT)
        if len(parts) != 2:
            return None
        tail = parts[1].split("/")[0].split("?")[0]
        try:
            return int(tail)
        except ValueError:
            return None

    # Extract the player slug from a profile URL
    @staticmethod
    def _extract_player_slug(href: str) -> Optional[str]:
        parts = href.split(PLAYER_PROFILE_URL_FRAGMENT)
        if len(parts) != 2:
            return None
        slug = parts[0].strip("/").split("/")[-1]
        return slug or None

    # Parse one injury table row into an injury spell dictionary
    @staticmethod
    def _parse_spell_row(cells: list[str]) -> Optional[dict]:
        season, injury_type, from_str, until_str, days_str, games_str = cells

        start_date = TransfermarktClient._parse_date(from_str)
        if start_date is None:
            return None

        end_date = TransfermarktClient._parse_date(until_str)
        days_out = TransfermarktClient._parse_days(days_str)
        games_missed = TransfermarktClient._parse_int(games_str)

        return {
            "season": season,
            "injury_type_raw": injury_type,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
            "days_out": days_out,
            "games_missed": games_missed,
        }

    # Parse a Transfermarkt date string
    @staticmethod
    def _parse_date(value: str) -> Optional[datetime]:
        value = value.strip()
        if not value or value == "-" or value == "?":
            return None
        try:
            return datetime.strptime(value, DATE_FORMAT_TM)
        except ValueError:
            return None

    # Parse a days-out value into an integer
    @staticmethod
    def _parse_days(value: str) -> Optional[int]:
        value = value.replace("days", "").replace("day", "").strip()
        return TransfermarktClient._parse_int(value)

    # Parse an integer from a scraped string
    @staticmethod
    def _parse_int(value: str) -> Optional[int]:
        value = value.strip().replace(",", "")
        if not value or value == "-" or value == "?":
            return None
        try:
            return int(value)
        except ValueError:
            return None

    # Send a throttled GET request with retry handling
    def _get(self, url: str) -> BeautifulSoup:
        self._throttle()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                if attempt == MAX_RETRIES:
                    raise TransfermarktError(f"Network error after {MAX_RETRIES} attempts: {url}") from exc
                self._backoff(attempt)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == MAX_RETRIES:
                    raise TransfermarktError(
                        f"HTTP {response.status_code} after {MAX_RETRIES} attempts: {url}"
                    )
                logger.warning("HTTP %d on attempt %d for %s, backing off", response.status_code, attempt, url)
                self._backoff(attempt)
                continue

            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")

        raise TransfermarktError(f"Exhausted retries: {url}")

    # Enforce the configured delay between requests
    def _throttle(self) -> None:
        if self._last_request_time is None:
            self._last_request_time = time.monotonic()
            return

        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._delay_seconds:
            time.sleep(self._delay_seconds - elapsed)
        self._last_request_time = time.monotonic()

    # Sleep before retrying after a retryable failure
    def _backoff(self, attempt: int) -> None:
        delay = BACKOFF_BASE_SECONDS * exponential_backoff_seconds(
            attempt=attempt - 1,
            base=2.0,
            jitter=False,
            cap=2.0 ** (MAX_RETRIES - 1),
        )
        logger.info("Backing off %.1fs before retry %d", delay, attempt + 1)
        time.sleep(delay)