from __future__ import annotations

import json
import logging

from django.conf import settings

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the xgGaffer AI assistant. xgGaffer is a football analytics platform.
You receive structured analytics data and write a concise natural language summary for a user who asked a football question.

Rules you must follow without exception:
1. Only state facts that appear in the engine_data field of the JSON you receive.
2. Never invent probabilities, statistics, player names, team names, or outcomes.
3. Never say "I think", "I believe", or express personal opinions on results.
4. Keep responses under 120 words. Write in 2-3 short paragraphs. No bullet points.
5. If partial is true in the payload, acknowledge the limitation in one sentence.
6. If intent is UNKNOWN, explain what xgGaffer can do using the capabilities list.
7. Always refer to probabilities as percentages rounded to the nearest whole number.
8. Do not repeat the user's question back to them.

Intent-specific guidance:
- FORM_ANALYSIS: Summarise the team's record, recent form string, home/away split, and avg xG/xGA trend.
- HEAD_TO_HEAD: State total meetings, each team's wins, draws, and note the most recent encounter.
- PLAYER_STATS: Lead with goals and assists, then mention xG/npxG per 90 and any standout per-90 metric.
- TEAM_RANKINGS: State the league leader, top 4, and relegation zone teams. Mention one standout stat.
- REST_DAYS: State avg days between matches, matches in last 28 days, and whether the schedule is congested."""

MAX_TOKENS = 400
MODEL = "claude-haiku-4-5-20251001"
SUPPORTED_IMAGE_MEDIA_TYPES = {"image/jpeg", "image/png"}


class LLMNarrator:
    def __init__(self) -> None:
        self._api_key: str | None = None

    def _get_api_key(self) -> str:
        if self._api_key is None:
            try:
                self._api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
            except Exception:
                self._api_key = ""
            if not self._api_key:
                _logger.warning(
                    "ANTHROPIC_API_KEY not configured — narrator will use "
                    "deterministic fallback for all queries."
                )
        return self._api_key

    def narrate(
        self,
        payload: dict,
        raw_query: str,
        image_b64: str | None = None,
        image_media_type: str | None = None,
    ) -> tuple[str, bool]:
        api_key = self._get_api_key()
        if not api_key:
            return self._fallback_response(payload), True
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            user_message = (
                f"User asked: {raw_query}\n\n"
                f"Analytics data:\n{json.dumps(payload, indent=2)}"
            )

            if image_b64 and image_media_type:
                if image_media_type not in SUPPORTED_IMAGE_MEDIA_TYPES:
                    _logger.warning(
                        "Unsupported image media type %s — treating as text-only.",
                        image_media_type,
                    )
                    content = user_message
                else:
                    content = [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": user_message},
                    ]
            else:
                content = user_message

            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            prose = message.content[0].text.strip()
            return prose, False
        except Exception as exc:
            _logger.exception("Narrator API call failed: %s", exc)
            return self._fallback_response(payload), True

    def _fallback_response(self, payload: dict) -> str:
        intent = payload.get("intent", "UNKNOWN")
        entities = payload.get("entities", {})
        data = payload.get("engine_data", {})

        if payload.get("partial") and payload.get("error"):
            return (
                f"xgGaffer was unable to retrieve full data for this query. "
                f"{payload.get('error', '')}"
            )

        if intent == "MATCH_PREDICTION":
            prediction = data.get("prediction", "unknown")
            probs = data.get("probabilities", {})
            home_pct = round(probs.get("home", 0) * 100)
            draw_pct = round(probs.get("draw", 0) * 100)
            away_pct = round(probs.get("away", 0) * 100)
            home = entities.get("home_team", "Home")
            away = entities.get("away_team", "Away")
            return (
                f"Prediction: {prediction}. {home} {home_pct}% | "
                f"Draw {draw_pct}% | {away} {away_pct}%."
            )

        if intent == "SCORE_PREDICTION":
            return (
                "The scoreline predictor is currently being recalibrated. "
                "Match outcome and Elo predictions remain available."
            )

        if intent == "ELO_QUERY":
            team = entities.get("team") or entities.get("home_team", "The team")
            rating = data.get("elo_rating")
            if rating:
                return f"{team} currently has an Elo rating of {rating:.0f}."
            return f"Elo rating data for {team} is not available."

        if intent == "SEASON_SIMULATION":
            league = entities.get("league", "the league")
            title_probs = data.get("title_probabilities", {})
            if title_probs:
                leader = max(title_probs, key=title_probs.get)
                pct = round(title_probs[leader] * 100)
                return f"{leader} are the title favourites in {league} with a {pct}% chance."
            return f"Season simulation data for {league} is not available."

        if intent == "GLOSSARY":
            term = data.get("term", "").upper()
            definition = data.get("definition", "No definition available.")
            return f"{term}: {definition}"

        if intent == "LINEUP_PREDICTION":
            team = entities.get("team") or entities.get("home_team", "The team")
            return f"Lineup prediction for {team} is shown in the data panel."

        if intent == "TACTICAL_QUERY":
            team = entities.get("team") or entities.get("home_team", "The team")
            label = data.get("cluster_label", "")
            if label:
                return f"{team} play a {label} style based on their tactical profile."
            return f"Tactical profile for {team} is not available."

        if intent == "AVAILABILITY_QUERY":
            players = data.get("players", [])
            if players:
                return f"Availability data retrieved for {len(players)} player(s)."
            return "Player availability data is not available for this query."

        if intent == "COMPOSITE_MATCH":
            home = entities.get("home_team", "Home")
            away = entities.get("away_team", "Away")
            return (
                f"Full analysis for {home} vs {away} is shown in the data panel. "
                "This includes match prediction, Elo ratings, availability, and lineup."
            )

        if intent == "STAT_COMPARISON":
            home = entities.get("home_team", "Home")
            away = entities.get("away_team", "Away")
            return f"Statistical comparison between {home} and {away} is shown below."

        if intent == "UNKNOWN":
            return (
                "xgGaffer can predict match outcomes, scorelines, season simulations, "
                "team strength (Elo), player availability, lineups, and tactical styles "
                "across the top 5 European leagues. Ask a specific question to get started."
            )

        if intent == "FORM_ANALYSIS":
            team = entities.get("team") or entities.get("home_team", "The team")
            form = data.get("recent_form", "")
            wins = data.get("wins", "—")
            draws = data.get("draws", "—")
            losses = data.get("losses", "—")
            avg_xg = data.get("avg_xg", "—")
            if form:
                return (
                    f"{team} recent form: {form}. "
                    f"Season record: {wins}W {draws}D {losses}L. "
                    f"Avg xG per game: {avg_xg}."
                )
            return f"Form data for {team} is not available."

        if intent == "HEAD_TO_HEAD":
            team_a = data.get("team_a", entities.get("home_team", "Team A"))
            team_b = data.get("team_b", entities.get("away_team", "Team B"))
            total = data.get("total_meetings", 0)
            a_wins = data.get(f"{team_a}_wins", "—")
            b_wins = data.get(f"{team_b}_wins", "—")
            draws = data.get("draws", "—")
            if total:
                return (
                    f"In {total} meetings: {team_a} {a_wins} wins, "
                    f"{team_b} {b_wins} wins, {draws} draws."
                )
            return f"No head-to-head history found between {team_a} and {team_b}."

        if intent == "PLAYER_STATS":
            name = data.get("name", entities.get("player_name", "The player"))
            team = data.get("team", "")
            goals = data.get("goals", "—")
            assists = data.get("assists", "—")
            xg = data.get("xg", "—")
            npxg90 = data.get("npxg90", "—")
            if goals != "—":
                return (
                    f"{name} ({team}): {goals} goals, {assists} assists. "
                    f"xG: {xg}, npxG/90: {npxg90}."
                )
            return f"Player stats for {name} are not available."

        if intent == "TEAM_RANKINGS":
            league = data.get("league", entities.get("league", "the league"))
            season = data.get("season", "")
            leader = data.get("leader", "—")
            top_4 = data.get("top_4", [])
            relegation = data.get("relegation_zone", [])
            top_4_str = ", ".join(top_4) if top_4 else "—"
            rel_str = ", ".join(relegation) if relegation else "—"
            return (
                f"{league} {season} standings. Leader: {leader}. "
                f"Top 4: {top_4_str}. "
                f"Relegation zone: {rel_str}."
            )

        if intent == "REST_DAYS":
            team = entities.get("team") or entities.get("home_team", "The team")
            avg = data.get("avg_days_between_matches", "—")
            recent = data.get("matches_in_last_28_days", "—")
            last = data.get("last_match_date", "—")
            return (
                f"{team} rest analysis: avg {avg} days between matches. "
                f"{recent} games in the last 28 days. Last match: {last}."
            )

        return "xgGaffer retrieved the data for your query. Results are shown below."