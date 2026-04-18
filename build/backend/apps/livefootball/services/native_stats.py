from __future__ import annotations

import re
import time
import unicodedata
from typing import Any

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - dependency may be optional in some envs
    sync_playwright = None


NATIVE_STATS_BASE_URL = "https://native-stats.org"
REQUEST_TIMEOUT_SECONDS = 10
PLAYWRIGHT_WAIT_MILLISECONDS = 7000
HOMEPAGE_CACHE_SECONDS = 300


SQUAD_ROW_RE = re.compile(
    r"^(?P<number>\d+)\s+"
    r"(?P<name>.+?)\s+"
    r"(?P<position>Goalkeeper|Defence|Midfield|Offence)\s+"
    r"(?P<contract_start>\d{4}-\d{2}|-)\s+"
    r"(?P<contract_end>\d{4}-\d{2}|-)\s+"
    r"(?P<minutes>\d+)\s+min$"
)

STREAK_PERIOD_RE = re.compile(
    r"^(?P<start>\d{4}-\d{2}-\d{2})\s*-\s*(?P<end>\d{4}-\d{2}-\d{2})$"
)

STREAK_BUSTER_DATE_RE = re.compile(
    r"^(?P<date>\d{4}/\d{2}/\d{2})\b"
)


class NativeStatsError(Exception):
    pass


def get_team_squad_minutes(team_external_id: int) -> list[dict[str, Any]]:
    if not team_external_id:
        return []

    text = _fetch_page_text(f"{NATIVE_STATS_BASE_URL}/team/{team_external_id}")
    lines = _normalise_lines(text)

    squad_start_index = next(
        (i for i, line in enumerate(lines) if line.startswith("Squad:")),
        None,
    )

    if squad_start_index is None:
        return []

    _SQUAD_HEADER_LINES = frozenset({"No.", "Name", "Position", "Contract Start/End", "on Pitch"})
    _POSITIONS = frozenset({"Goalkeeper", "Defence", "Midfield", "Offence"})
    _CONTRACT_RE = re.compile(r"^\d{4}-\d{2}$|^-$")
    _MINUTES_RE = re.compile(r"^(?P<minutes>\d+)\s+min$")

    squad_rows: list[dict[str, Any]] = []

    # --- single-line format (original) ---
    for line in lines[squad_start_index + 1 :]:
        if line.startswith("Category") or line.startswith("Showing records"):
            break
        match = SQUAD_ROW_RE.match(line)
        if match:
            squad_rows.append(
                {
                    "shirt_number": _safe_int(match.group("number")),
                    "name": match.group("name").strip(),
                    "normalised_name": _normalise_name(match.group("name")),
                    "position_group": match.group("position").strip(),
                    "minutes_played": _safe_int(match.group("minutes")) or 0,
                }
            )

    if squad_rows:
        return squad_rows

    # --- multi-line format: 6 lines per player ---
    # (shirt_number, name, position, contract_start, contract_end, "NNN min")
    data_lines: list[str] = []
    for line in lines[squad_start_index + 1 :]:
        if line.startswith("Category") or line.startswith("Showing records"):
            break
        if line in _SQUAD_HEADER_LINES:
            continue
        data_lines.append(line)

    i = 0
    while i + 5 < len(data_lines):
        number_str   = data_lines[i]
        name_str     = data_lines[i + 1]
        position_str = data_lines[i + 2]
        c_start_str  = data_lines[i + 3]
        c_end_str    = data_lines[i + 4]
        minutes_str  = data_lines[i + 5]

        minutes_match = _MINUTES_RE.match(minutes_str)
        if (
            number_str.isdigit()
            and position_str in _POSITIONS
            and _CONTRACT_RE.match(c_start_str)
            and _CONTRACT_RE.match(c_end_str)
            and minutes_match
        ):
            squad_rows.append(
                {
                    "shirt_number": _safe_int(number_str),
                    "name": name_str.strip(),
                    "normalised_name": _normalise_name(name_str),
                    "position_group": position_str.strip(),
                    "minutes_played": _safe_int(minutes_match.group("minutes")) or 0,
                }
            )
            i += 6
        else:
            i += 1

    return squad_rows


def get_default_all_time_streaks(limit: int = 12) -> list[dict[str, Any]]:
    text = _fetch_page_text(f"{NATIVE_STATS_BASE_URL}/alltime-streaks")
    lines = _normalise_lines(text)

    # Look for the header - either single line or multi-line format
    start_index = None
    
    # First try multi-line header (new format): Team, Days, Matches, Period, Buster on separate lines
    for i in range(len(lines) - 4):
        if (lines[i] == "Team" and 
            lines[i + 1] == "Days" and 
            lines[i + 2] == "Matches" and 
            lines[i + 3] == "Period" and 
            lines[i + 4] == "Buster"):
            start_index = i + 4  # Start after "Buster"
            break
    
    # Fall back to single-line header (old format)
    if start_index is None:
        for i, line in enumerate(lines):
            if line == "Team Days Matches Period Buster":
                start_index = i
                break
    
    if start_index is None:
        return []

    entries: list[dict[str, Any]] = []
    i = start_index + 1

    while i < len(lines) and len(entries) < limit:
        if not lines[i].startswith("#"):
            i += 1
            continue

        rank = _safe_int(lines[i].replace("#", ""))
        i += 1

        team_name = None
        matches = None
        days = None
        period_start = None
        period_end = None
        buster_date = None

        while i < len(lines):
            line = lines[i]

            if line.startswith("#"):
                break

            if line == "Days:":
                if i + 1 < len(lines):
                    days = _safe_int(lines[i + 1])
                    i += 2
                else:
                    i += 1
                continue

            if line == "Matches:":
                if i + 1 < len(lines):
                    matches = _safe_int(lines[i + 1])
                    i += 2
                else:
                    i += 1
                continue

            if line == "Period:":
                if i + 1 < len(lines):
                    match = STREAK_PERIOD_RE.match(lines[i + 1])
                    if match:
                        period_start = match.group("start")
                        period_end = match.group("end")
                    i += 2
                else:
                    i += 1
                continue

            if team_name is None and _is_valid_team_name(line):
                team_name = line
                i += 1
                continue

            match = STREAK_BUSTER_DATE_RE.match(line)
            if match:
                buster_date = match.group("date").replace("/", "-")

            i += 1

        if team_name and matches is not None:
            entries.append(
                {
                    "rank": rank,
                    "team_name": team_name,
                    "normalised_team_name": _normalise_name(team_name),
                    "days": days,
                    "matches": matches,
                    "period_start": period_start,
                    "period_end": period_end,
                    "buster_date": buster_date,
                    "label": "Longest all-time unbeaten run",
                    "summary": f"{matches} matches without defeat",
                }
            )

    return entries


def build_minutes_lookup(team_external_id: int) -> dict[str, dict[str, Any]]:
    squad = get_team_squad_minutes(team_external_id)
    return {
        item["normalised_name"]: item
        for item in squad
        if item.get("normalised_name")
    }


def _fetch_page_text(url: str) -> str:
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": "xgGaffer/1.0",
                "Accept-Language": "en-GB,en;q=0.9",
            },
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise NativeStatsError(str(exc)) from exc

    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text("\n")


def _normalise_lines(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]


def _normalise_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_valid_team_name(value: str) -> bool:
    if not value:
        return False

    invalid = {"Show", "Close", "Days:", "Matches:", "Period:"}
    if value in invalid:
        return False

    if STREAK_PERIOD_RE.match(value):
        return False

    if STREAK_BUSTER_DATE_RE.match(value):
        return False

    return True

HOME_TOP_PERFORMING_TEAMS_HEADING = "Top performing teams"
HOME_STRIKERS_WITH_A_LULL_HEADING = "Strikers w/ a lull."
HOME_LATEST_HAT_TRICKS_HEADING = "Latest hat-tricks"

ISO_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLASH_DATE_ONLY_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
DECIMAL_VALUE_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
FORM_TEXT_RE = re.compile(r"^[WDL\s]+$", re.IGNORECASE)
SCORE_RE = re.compile(r"\b\d{1,2}:\d{1,2}\b")
MATCH_ID_RE = re.compile(r"/match/(\d+)")
PERSON_ID_RE = re.compile(r"/person/(\d+)")
COMP_CODE_RE = re.compile(r"^[A-Z0-9]{2,5}$")
INVALID_COMP_CODES = {
    "MENU",
    "BLOG",
    "LOGIN",
    "SETTINGS",
    "SEARCH",
    "SHOW",
    "CLOSE",
}

_homepage_cache_payload: dict[str, Any] | None = None
_homepage_cache_timestamp = 0.0


def get_homepage_top_performing_teams(limit: int = 10) -> list[dict[str, Any]]:
    text = _fetch_page_text(f"{NATIVE_STATS_BASE_URL}/")
    lines = _normalise_lines(text)

    section_lines = _extract_section_lines(
        lines,
        heading=HOME_TOP_PERFORMING_TEAMS_HEADING,
    )
    cleaned_lines = _clean_section_lines(
        section_lines,
        skip_values={
            "Best performing teams across Europe's top flights",
            "Team Form ⌀ points ⌀ scored goals",
        },
    )

    rows: list[dict[str, Any]] = []
    index = 0

    while index + 3 < len(cleaned_lines) and len(rows) < limit:
        team_name = cleaned_lines[index]
        form_label = cleaned_lines[index + 1]
        average_points = cleaned_lines[index + 2]
        average_goals = cleaned_lines[index + 3]

        if (
            _is_valid_team_name(team_name)
            and _looks_like_form_text(form_label)
            and _looks_like_numeric_value(average_points)
            and _looks_like_numeric_value(average_goals)
        ):
            rows.append(
                {
                    "team_name": team_name,
                    "normalised_team_name": _normalise_name(team_name),
                    "form_label": re.sub(r"\s+", "", form_label).upper(),
                    "average_points": _safe_float_value(average_points),
                    "average_goals": _safe_float_value(average_goals),
                }
            )
            index += 4
            continue

        index += 1

    return rows


def get_homepage_latest_hat_tricks(limit: int = 8) -> list[dict[str, Any]]:
    homepage_tables = _fetch_homepage_rendered_tables()
    hat_rows = homepage_tables.get("latest_hat_tricks") or []

    rows: list[dict[str, Any]] = []
    for row in hat_rows:
        if len(rows) >= limit:
            break

        scorer_name = str(row.get("scorer_name") or "").strip()
        date_value = _normalise_date_value(str(row.get("date") or ""))
        match_label = str(row.get("match_label") or "").strip()
        match_id = _safe_int(row.get("match_id"))

        if not scorer_name or not date_value or not match_label:
            continue

        person_id = _safe_int(row.get("person_id"))
        person_profile = _fetch_person_profile(person_id) if person_id else None

        rows.append(
            {
                "date": date_value,
                "match_label": match_label,
                "match_id": match_id,
                "result": _fetch_match_result(match_id) if match_id else None,
                "competition_code": _fetch_match_competition_code(match_id) if match_id else None,
                "scorer_name": scorer_name,
                "normalised_scorer_name": _normalise_name(scorer_name),
                "person_id": person_id,
                "team_name": person_profile.get("current_team") if person_profile else None,
            }
        )

    return rows


def get_homepage_strikers_with_a_lull(limit: int = 8) -> list[dict[str, Any]]:
    homepage_tables = _fetch_homepage_rendered_tables()
    lull_rows = homepage_tables.get("strikers_with_a_lull") or []

    rows: list[dict[str, Any]] = []
    for row in lull_rows:
        if len(rows) >= limit:
            break

        scorer_name = str(row.get("scorer_name") or "").strip()
        normalised_last_scored = _normalise_date_value(str(row.get("last_scored") or ""))
        match_label = str(row.get("match_label") or "").strip()
        person_id = _safe_int(row.get("person_id"))
        match_id = _safe_int(row.get("match_id"))

        if not _is_valid_person_name(scorer_name) or not normalised_last_scored or not match_label:
            continue

        person_profile = _fetch_person_profile(person_id) if person_id else None
        lull_stats = person_profile if person_profile else None
        no_goal_matches = lull_stats.get("no_goal_matches") if lull_stats else None

        # Native-stats lull logic is effectively no-goal run form; enforce 10+ explicitly.
        if no_goal_matches is not None and no_goal_matches < 10:
            continue

        rows.append(
            {
                "scorer_name": scorer_name,
                "normalised_scorer_name": _normalise_name(scorer_name),
                "last_scored": normalised_last_scored,
                "match_label": match_label,
                "match_id": match_id,
                "result": _fetch_match_result(match_id) if match_id else None,
                "person_id": person_id,
                "no_goal_matches": no_goal_matches,
                "goals_per_game": lull_stats.get("goals_per_game") if lull_stats else None,
                "team_name": person_profile.get("current_team") if person_profile else None,
            }
        )

    return rows


def _fetch_homepage_rendered_tables() -> dict[str, list[dict[str, Any]]]:
    global _homepage_cache_payload, _homepage_cache_timestamp

    now = time.time()
    if _homepage_cache_payload and (now - _homepage_cache_timestamp) <= HOMEPAGE_CACHE_SECONDS:
        return _homepage_cache_payload

    if sync_playwright is None:
        if _homepage_cache_payload:
            return _homepage_cache_payload
        raise NativeStatsError("playwright is required to read rendered native-stats homepage data")

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0 xgGaffer/1.0")
            page.goto(
                f"{NATIVE_STATS_BASE_URL}/",
                wait_until="domcontentloaded",
                timeout=REQUEST_TIMEOUT_SECONDS * 1000 * 6,
            )
            page.wait_for_timeout(PLAYWRIGHT_WAIT_MILLISECONDS)
            payload = page.evaluate(
                """
                () => {
                    function parseIdFromNode(node, pattern) {
                        if (!node) return null;
                        const html = node.outerHTML || "";
                        const attr = node.getAttribute("phx-click") || "";
                        const source = `${html}\n${attr}`;
                        const match = source.match(pattern);
                        return match ? Number(match[1]) : null;
                    }

                    function findCard(h3) {
                        let current = h3;
                        for (let i = 0; i < 8 && current; i += 1) {
                            if (current.querySelector && current.querySelector("table")) return current;
                            current = current.parentElement;
                        }
                        return null;
                    }

                    function extractRows(heading) {
                        const h3 = [...document.querySelectorAll("h3")].find(
                            (el) => el.textContent.trim() === heading,
                        );
                        if (!h3) return [];
                        const card = findCard(h3);
                        if (!card) return [];
                        const table = card.querySelector("table");
                        if (!table) return [];
                        return [...table.querySelectorAll("tbody tr")].map((tr) => {
                            const tds = [...tr.querySelectorAll("td")];
                            return {
                                cells: tds.map((td) => td.textContent.replace(/\s+/g, " ").trim()),
                                match_id: parseIdFromNode(tr, /\\/match\\/(\\d+)/),
                                person_id: parseIdFromNode(tr, /\\/person\\/(\\d+)/),
                            };
                        });
                    }

                    return {
                        latest_hat_tricks: extractRows("Latest hat-tricks").map((row) => ({
                            date: row.cells[0] || "",
                            match_label: row.cells[1] || "",
                            scorer_name: row.cells[2] || "",
                            match_id: row.match_id,
                            person_id: row.person_id,
                        })),
                        strikers_with_a_lull: extractRows("Strikers w/ a lull.").map((row) => ({
                            scorer_name: row.cells[0] || "",
                            last_scored: row.cells[1] || "",
                            match_label: row.cells[2] || "",
                            match_id: row.match_id,
                            person_id: row.person_id,
                        })),
                    };
                }
                """
            )
            browser.close()
    except Exception as exc:  # pragma: no cover - network / browser variance
        if _homepage_cache_payload:
            return _homepage_cache_payload
        raise NativeStatsError(str(exc)) from exc

    _homepage_cache_payload = payload
    _homepage_cache_timestamp = now
    return payload


def _fetch_match_result(match_id: int) -> str | None:
    if not match_id:
        return None

    try:
        text = _fetch_page_text(f"{NATIVE_STATS_BASE_URL}/match/{match_id}")
    except NativeStatsError:
        return None

    lines = _normalise_lines(text)
    for line in lines:
        score_match = SCORE_RE.search(line)
        if score_match:
            return score_match.group(0)

    return None


def _fetch_match_competition_code(match_id: int) -> str | None:
    if not match_id:
        return None

    try:
        text = _fetch_page_text(f"{NATIVE_STATS_BASE_URL}/match/{match_id}")
    except NativeStatsError:
        return None

    for line in _normalise_lines(text):
        value = line.strip().upper()
        if COMP_CODE_RE.match(value) and value not in INVALID_COMP_CODES:
            return value

    return None


def _fetch_person_profile(person_id: int) -> dict[str, Any] | None:
    if not person_id:
        return None

    try:
        response = requests.get(
            f"{NATIVE_STATS_BASE_URL}/person/{person_id}",
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": "xgGaffer/1.0",
                "Accept-Language": "en-GB,en;q=0.9",
            },
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    candidate_table = None
    for table in soup.find_all("table"):
        header_cells = [th.get_text(strip=True) for th in table.select("thead th")]
        if header_cells and "Date" in header_cells and "Score" in header_cells:
            candidate_table = table
            break

    if candidate_table is None:
        return None

    lines = _normalise_lines(soup.get_text("\n"))
    current_team = None
    for index, line in enumerate(lines):
        if line == "Current Team":
            for candidate in lines[index + 1 : index + 8]:
                clean = candidate.strip()
                if not clean:
                    continue
                if clean in {"-", "--", ":"}:
                    continue
                if len(clean) < 3:
                    continue
                if clean.lower().startswith("n/a"):
                    continue
                if clean in {"Contract", "Est. market value", "Preferred foot"}:
                    continue
                if COMP_CODE_RE.match(clean.upper()):
                    continue
                current_team = clean
                break
            break

    rows = list(candidate_table.select("tbody tr"))
    if not rows:
        return {
            "no_goal_matches": None,
            "goals_per_game": None,
            "current_team": current_team,
        }

    streak = 0
    goals = 0

    for row in rows:
        text = row.get_text(" ", strip=True)
        has_goal = "⚽" in text
        if has_goal:
            goals += 1
        elif goals == 0:
            streak += 1

    matches = len(rows)
    goals_per_game = round(goals / matches, 2) if matches > 0 else None

    return {
        "no_goal_matches": streak,
        "goals_per_game": goals_per_game,
        "current_team": current_team,
    }


def _extract_section_lines(lines: list[str], heading: str) -> list[str]:
    start_index = next((i for i, line in enumerate(lines) if line == heading), None)
    if start_index is None:
        return []

    extracted: list[str] = []

    for line in lines[start_index + 1:]:
        if line.startswith("### "):
            break
        if line.startswith("For the "):
            break
        extracted.append(line)

    return extracted


def _clean_section_lines(
    lines: list[str],
    skip_values: set[str] | None = None,
) -> list[str]:
    skip_values = skip_values or set()

    cleaned: list[str] = []
    for line in lines:
        if not line:
            continue
        if line in skip_values:
            continue
        cleaned.append(line)

    return cleaned


def _looks_like_numeric_value(value: str) -> bool:
    return bool(DECIMAL_VALUE_RE.match(value.strip()))


def _looks_like_form_text(value: str) -> bool:
    compact = re.sub(r"\s+", "", value).upper()
    if len(compact) < 3:
        return False
    return bool(FORM_TEXT_RE.match(compact))


def _normalise_date_value(value: str) -> str | None:
    cleaned = value.strip()

    if ISO_DATE_ONLY_RE.match(cleaned):
        return cleaned

    if SLASH_DATE_ONLY_RE.match(cleaned):
        return cleaned.replace("/", "-")

    return None


def _safe_float_value(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _is_valid_person_name(value: str) -> bool:
    cleaned = value.strip()
    if not cleaned:
        return False
    if _normalise_date_value(cleaned):
        return False
    if cleaned.startswith("### "):
        return False
    return True