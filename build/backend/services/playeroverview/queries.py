from __future__ import annotations

from typing import Any

from apps.livefootball.models import CompetitionTopScorer, PlayerDirectoryEntry
from apps.players.models import Player
from services.livefootball.helpers import shape_competition_item, shape_team_lookup_item
from services.playerdata.comparisons import build_player_comparison
from services.playerdata.summaries import (
    build_player_provider_coverage_summary,
    build_player_season_summary,
)
from services.playeroverview.helpers import (
    apply_metric_source_preference,
    build_provider_coverage_block,
    build_source_detail_block,
    build_source_preference_block,
    clean_optional_str,
    first_non_empty_str,
    get_player_age,
    get_player_display_name,
    group_metric_dicts,
    latest_datetime,
    normalise_position,
)


def _build_comparison_metric_dict(metric: Any) -> dict[str, Any]:
    return {
        "key": metric.key,
        "label": metric.label,
        "player_a_value": metric.player_a_value,
        "player_a_formatted": metric.player_a_formatted,
        "player_b_value": metric.player_b_value,
        "player_b_formatted": metric.player_b_formatted,
        "delta": metric.delta,
        "formatted_delta": metric.formatted_delta,
        "unit": metric.unit or None,
        "winner": metric.winner,
        "is_tie": metric.is_tie,
        "is_comparable": metric.is_comparable,
        "sentence": metric.sentence,
    }


def _serialise_context_value(value: Any) -> Any:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _build_minimal_general_overview(*, player_name: str, livefootball_context: dict[str, Any] | None) -> dict[str, Any]:
    notes: list[str] = []
    summary = f"No stored playerdata season summary is available for {player_name}."

    if livefootball_context:
        competition = livefootball_context.get("competition") or {}
        team = livefootball_context.get("team") or {}
        competition_name = clean_optional_str(competition.get("name")) or clean_optional_str(competition.get("code"))
        team_name = clean_optional_str(team.get("name"))
        if team_name and competition_name:
            notes.append(f"Livefootball context places the player at {team_name} in {competition_name}.")
        elif team_name:
            notes.append(f"Livefootball context places the player at {team_name}.")

    return {
        "headline": "Merged player overview",
        "summary": summary,
        "strengths": [],
        "watchouts": ["Advanced season metrics are not available for the requested filters."],
        "notes": notes,
        "sentences": [summary, *notes],
    }


def _build_livefootball_source_detail(livefootball_context: dict[str, Any] | None) -> dict[str, Any]:
    if not livefootball_context:
        return build_source_detail_block(
            source="livefootball",
            has_data=False,
            coverage_notes=["No livefootball directory or top-scorer context matched the requested filters."],
        )

    coverage_notes: list[str] = []
    if livefootball_context.get("source") == "directory_entry":
        coverage_notes.append("Livefootball directory context is available for this player.")
    elif livefootball_context.get("source") == "top_scorer":
        coverage_notes.append("Livefootball top-scorer context is available for this player.")

    competition = livefootball_context.get("competition") or {}
    team = livefootball_context.get("team") or {}
    if team.get("name"):
        coverage_notes.append(f"Team context: {team['name']}.")
    if competition.get("name") or competition.get("code"):
        competition_label = clean_optional_str(competition.get("name")) or clean_optional_str(competition.get("code"))
        coverage_notes.append(f"Competition context: {competition_label}.")

    return build_source_detail_block(
        source="livefootball",
        has_data=True,
        provider=livefootball_context.get("provider"),
        last_synced_at=livefootball_context.get("last_synced_at"),
        coverage_notes=coverage_notes,
        extra_fields={
            "team": team,
            "competition": competition,
            "season_label": livefootball_context.get("season_label") or "",
        },
    )


def get_best_available_player_context(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    active_only: bool = True,
) -> dict[str, Any] | None:
    resolved_season_label = clean_optional_str(season_label or season) or None

    directory_queryset = PlayerDirectoryEntry.objects.select_related(
        "team",
        "team__competition",
        "canonical_player",
    ).filter(canonical_player_id=player_id)

    if resolved_season_label:
        directory_queryset = directory_queryset.filter(team__season_label=resolved_season_label)
    if competition_code:
        directory_queryset = directory_queryset.filter(team__competition__code=competition_code)
    if competition_name:
        directory_queryset = directory_queryset.filter(team__competition__name=competition_name)
    if active_only:
        directory_queryset = directory_queryset.filter(is_active=True)

    directory_entry = directory_queryset.order_by(
        "-team__season_label",
        "-last_synced_at",
        "-updated_at",
        "-id",
    ).first()

    if directory_entry is not None:
        team = directory_entry.team
        competition = team.competition if team else None
        return {
            "source": "directory_entry",
            "provider": directory_entry.provider,
            "entry_id": directory_entry.id,
            "player_name": directory_entry.player_name,
            "primary_position": directory_entry.primary_position or directory_entry.raw_position or "",
            "raw_position": directory_entry.raw_position or "",
            "nationality": directory_entry.nationality or "",
            "date_of_birth": directory_entry.date_of_birth,
            "squad_number": directory_entry.squad_number,
            "season_label": team.season_label if team else (resolved_season_label or ""),
            "last_synced_at": directory_entry.last_synced_at,
            "team": shape_team_lookup_item(team) if team else None,
            "competition": shape_competition_item(competition) if competition else None,
        }

    scorer_queryset = CompetitionTopScorer.objects.select_related(
        "competition",
        "team",
        "canonical_player",
    ).filter(canonical_player_id=player_id)

    if resolved_season_label:
        scorer_queryset = scorer_queryset.filter(season_label=resolved_season_label)
    if competition_code:
        scorer_queryset = scorer_queryset.filter(competition__code=competition_code)
    if competition_name:
        scorer_queryset = scorer_queryset.filter(competition__name=competition_name)

    scorer_entry = scorer_queryset.order_by(
        "-season_label",
        "-synced_at",
        "rank",
        "id",
    ).first()

    if scorer_entry is None:
        return None

    return {
        "source": "top_scorer",
        "provider": getattr(scorer_entry.competition, "provider", None),
        "entry_id": scorer_entry.id,
        "player_name": scorer_entry.player_name,
        "primary_position": "",
        "raw_position": "",
        "nationality": "",
        "date_of_birth": None,
        "squad_number": None,
        "season_label": scorer_entry.season_label or (resolved_season_label or ""),
        "last_synced_at": scorer_entry.synced_at,
        "team": shape_team_lookup_item(scorer_entry.team) if scorer_entry.team else None,
        "competition": shape_competition_item(scorer_entry.competition) if scorer_entry.competition else None,
        "rank": scorer_entry.rank,
        "goals": scorer_entry.goals,
    }


def get_player_provider_coverage(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
    livefootball_context: dict[str, Any] | None = None,
    summary: Any | None = None,
) -> dict[str, Any]:
    playerdata_summary = build_player_provider_coverage_summary(player_id)

    playerdata_detail = build_source_detail_block(
        source="playerdata",
        has_data=False,
        coverage_notes=["No stored enrichment coverage exists for this player."],
    )

    if playerdata_summary is not None:
        playerdata_dict = playerdata_summary.to_dict()
        relevant_items = playerdata_dict.get("items", [])
        resolved_season_label = clean_optional_str(season_label or season)

        if resolved_season_label:
            relevant_items = [item for item in relevant_items if item.get("season_label") == resolved_season_label]
        if competition_code:
            relevant_items = [item for item in relevant_items if item.get("competition_code") == competition_code]
        if competition_name:
            relevant_items = [item for item in relevant_items if item.get("competition_name") == competition_name]
        if club_id is not None:
            relevant_items = [item for item in relevant_items if item.get("club_id") == club_id]

        if relevant_items:
            latest_synced_at = latest_datetime(*(item.get("last_synced_at") for item in relevant_items))
            latest_updated_at = latest_datetime(*(item.get("updated_at") for item in relevant_items))
            providers = sorted({item.get("provider") for item in relevant_items if item.get("provider")})
            seasons = sorted(
                {item.get("season_label") for item in relevant_items if item.get("season_label")},
                reverse=True,
            )
            competitions = sorted(
                {
                    clean_optional_str(item.get("competition_name")) or clean_optional_str(item.get("competition_code"))
                    for item in relevant_items
                    if clean_optional_str(item.get("competition_name")) or clean_optional_str(item.get("competition_code"))
                }
            )

            playerdata_detail = build_source_detail_block(
                source="playerdata",
                has_data=True,
                provider=providers[0] if len(providers) == 1 else "mixed",
                providers=providers,
                source_updated_at=latest_updated_at,
                last_synced_at=latest_synced_at,
                matches_sampled=getattr(summary, "matches_played", None),
                minutes_sampled=getattr(summary, "minutes_played", None),
                coverage_notes=playerdata_dict.get("sentences", []),
                extra_fields={
                    "record_count": len(relevant_items),
                    "seasons": seasons,
                    "competitions": competitions,
                    "items": relevant_items,
                },
            )

    livefootball_detail = _build_livefootball_source_detail(livefootball_context)

    return build_provider_coverage_block(
        {
            "playerdata": playerdata_detail,
            "livefootball": livefootball_detail,
        },
        matches_sampled=getattr(summary, "matches_played", None),
        minutes_sampled=getattr(summary, "minutes_played", None),
    )


def _build_player_identity(player: Player, *, summary: Any | None, livefootball_context: dict[str, Any] | None) -> dict[str, Any]:
    livefootball_date_of_birth = livefootball_context.get("date_of_birth") if livefootball_context else None
    display_name = get_player_display_name(player)
    first_name = clean_optional_str(getattr(player, "first_name", ""))
    last_name = clean_optional_str(getattr(player, "last_name", ""))
    full_name = first_non_empty_str(getattr(player, "full_name", ""), display_name) or display_name
    primary_position = first_non_empty_str(
        getattr(summary, "primary_position", ""),
        getattr(player, "primary_position", ""),
        livefootball_context.get("primary_position") if livefootball_context else "",
    )

    secondary_positions = list(getattr(summary, "secondary_positions", None) or getattr(player, "secondary_positions", None) or [])

    nationality = first_non_empty_str(
        livefootball_context.get("nationality") if livefootball_context else "",
        getattr(player, "nationality", ""),
    )

    return {
        "id": player.id,
        "full_name": full_name,
        "display_name": display_name,
        "short_name": display_name,
        "position": primary_position or None,
        "primary_position": primary_position or None,
        "secondary_positions": secondary_positions,
        "nationality": nationality,
        "age": get_player_age(player, fallback_date_of_birth=livefootball_date_of_birth),
        "photo_url": first_non_empty_str(getattr(player, "photo_url", "")),
        "first_name": first_name or None,
        "last_name": last_name or None,
    }


def _build_club_block(*, summary: Any | None, livefootball_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if summary is not None and getattr(summary, "club", None):
        club = summary.club
        return {
            "id": club.get("id"),
            "name": club.get("name"),
            "short_name": club.get("short_name") or club.get("name"),
            "crest_url": club.get("crest_url"),
            "source": "playerdata",
        }

    team = (livefootball_context or {}).get("team") or None
    if team is None:
        return None

    return {
        "id": None,
        "name": team.get("name") or None,
        "short_name": team.get("short_name") or team.get("name") or None,
        "crest_url": team.get("emblem_url") or None,
        "source": "livefootball",
    }


def _build_context_block(*, summary: Any | None, livefootball_context: dict[str, Any] | None) -> dict[str, Any]:
    livefootball_competition = (livefootball_context or {}).get("competition") or {}
    livefootball_team = (livefootball_context or {}).get("team") or {}

    return {
        "provider": getattr(summary, "provider", None) or (livefootball_context.get("provider") if livefootball_context else None),
        "season": getattr(summary, "season_label", None) or (livefootball_context.get("season_label") if livefootball_context else None),
        "competition_code": getattr(summary, "competition_code", None) or livefootball_competition.get("code"),
        "competition_name": getattr(summary, "competition_name", None) or livefootball_competition.get("name"),
        "competition_id": livefootball_competition.get("id"),
        "team_id": livefootball_team.get("id"),
        "team_name": livefootball_team.get("name"),
        "livefootball_source": livefootball_context.get("source") if livefootball_context else None,
    }


def _build_general_overview(*, player_name: str, summary: Any | None, livefootball_context: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return _build_minimal_general_overview(
            player_name=player_name,
            livefootball_context=livefootball_context,
        )

    explanation = summary.explanation
    return {
        "headline": explanation.get("headline"),
        "summary": explanation.get("summary"),
        "strengths": explanation.get("strengths", []),
        "watchouts": explanation.get("watchouts", []),
        "notes": explanation.get("notes", []),
        "sentences": list(getattr(summary, "sentences", []) or []),
    }


def _build_overview_metrics(summary: Any | None, *, position: str | None) -> list[dict[str, Any]]:
    if summary is None:
        return []

    metrics = []
    for metric in summary.metrics:
        preferred_metric = apply_metric_source_preference(
            dict(metric),
            available_provider=getattr(summary, "provider", None),
        )
        metrics.append(preferred_metric)
    return group_metric_dicts(metrics, position=position)


def get_player_overview(
    player_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_id: int | None = None,
    active_only: bool = True,
) -> dict[str, Any] | None:
    player = Player.objects.filter(id=player_id).first()
    if player is None:
        return None

    summary = build_player_season_summary(
        player_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_id,
    )

    livefootball_context = get_best_available_player_context(
        player_id,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
        active_only=active_only,
    )

    player_block = _build_player_identity(
        player,
        summary=summary,
        livefootball_context=livefootball_context,
    )
    club_block = _build_club_block(summary=summary, livefootball_context=livefootball_context)
    context_block = _build_context_block(summary=summary, livefootball_context=livefootball_context)
    provider_coverage = get_player_provider_coverage(
        player_id,
        season_label=season_label,
        season=season,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_id,
        livefootball_context=livefootball_context,
        summary=summary,
    )
    general_overview = _build_general_overview(
        player_name=player_block["display_name"],
        summary=summary,
        livefootball_context=livefootball_context,
    )
    metric_groups = _build_overview_metrics(summary, position=player_block.get("position"))

    missing_reasons: list[str] = []
    if summary is None:
        missing_reasons.append("No stored playerdata season summary matched the requested filters.")
    if livefootball_context is None:
        missing_reasons.append("No livefootball context matched the requested filters.")

    return {
        "player": player_block,
        "club": club_block,
        "context": context_block,
        "general_overview": general_overview,
        "metric_groups": metric_groups,
        "provider_coverage": provider_coverage,
        "source_preferences": build_source_preference_block(
            available_sources=provider_coverage.get("available_sources", []),
        ),
        "livefootball_context": livefootball_context,
        "playerdata_context": _serialise_context_value(summary.context) if summary is not None else None,
        "has_overview_data": bool(summary is not None or livefootball_context is not None),
        "missing_reasons": missing_reasons,
    }


build_player_overview = get_player_overview


def _build_comparison_context(
    *,
    player_a_overview: dict[str, Any],
    player_b_overview: dict[str, Any],
    raw_comparison: Any | None,
) -> dict[str, Any]:
    if raw_comparison is not None:
        return raw_comparison.context.to_dict()

    context_a = player_a_overview.get("context", {})
    context_b = player_b_overview.get("context", {})

    season_a = context_a.get("season")
    season_b = context_b.get("season")
    competition_code_a = context_a.get("competition_code")
    competition_code_b = context_b.get("competition_code")
    competition_name_a = context_a.get("competition_name")
    competition_name_b = context_b.get("competition_name")

    same_season = season_a and season_b and season_a == season_b
    same_competition = (
        (competition_code_a and competition_code_b and competition_code_a == competition_code_b)
        or (competition_name_a and competition_name_b and competition_name_a == competition_name_b)
    )

    return {
        "provider": None,
        "season": season_a if same_season else None,
        "competition_code": competition_code_a if same_competition else None,
        "competition_name": competition_name_a if same_competition else None,
        "same_provider": False,
        "same_season": bool(same_season),
        "same_competition": bool(same_competition),
        "left_last_synced_at": player_a_overview.get("provider_coverage", {}).get("last_synced_at"),
        "right_last_synced_at": player_b_overview.get("provider_coverage", {}).get("last_synced_at"),
        "sentence": "The players do not share a comparable stored playerdata season context for deterministic metric comparison.",
    }


def _build_grouped_comparison_metrics(
    raw_comparison: Any | None,
    *,
    player_a_position: str | None,
    player_b_position: str | None,
) -> list[dict[str, Any]]:
    if raw_comparison is None:
        return []

    if normalise_position(player_a_position) == normalise_position(player_b_position):
        position_for_grouping = player_a_position
    else:
        position_for_grouping = None

    metrics = []
    for metric in raw_comparison.metrics:
        metric_dict = _build_comparison_metric_dict(metric)
        preferred_metric = apply_metric_source_preference(
            metric_dict,
            available_provider=raw_comparison.context.provider,
        )
        metrics.append(preferred_metric)

    return group_metric_dicts(metrics, position=position_for_grouping)


def _build_comparison_general_overview(raw_comparison: Any | None) -> dict[str, Any]:
    if raw_comparison is None:
        return {
            "headline": "Merged player comparison",
            "summary": "No honest deterministic playerdata comparison is available for the requested players and filters.",
            "strengths": [],
            "watchouts": ["Comparison metrics require stored playerdata records for both players."],
            "notes": [],
            "sentences": ["No honest deterministic playerdata comparison is available for the requested players and filters."],
        }

    explanation = raw_comparison.explanation
    return {
        "headline": explanation.get("headline"),
        "summary": explanation.get("summary"),
        "strengths": explanation.get("strengths", []),
        "watchouts": explanation.get("watchouts", []),
        "notes": explanation.get("notes", []),
        "sentences": list(getattr(raw_comparison, "summary_lines", []) or []),
    }


def _build_comparison_provider_coverage(
    *,
    player_a_overview: dict[str, Any],
    player_b_overview: dict[str, Any],
    raw_comparison: Any | None,
) -> dict[str, Any]:
    player_a_coverage = player_a_overview.get("provider_coverage", {})
    player_b_coverage = player_b_overview.get("provider_coverage", {})
    latest_synced_at = latest_datetime(
        player_a_coverage.get("last_synced_at"),
        player_b_coverage.get("last_synced_at"),
    )
    latest_updated_at = latest_datetime(
        player_a_coverage.get("source_updated_at"),
        player_b_coverage.get("source_updated_at"),
    )

    available_sources = sorted(
        {
            *player_a_coverage.get("available_sources", []),
            *player_b_coverage.get("available_sources", []),
        }
    )
    missing_sources = sorted(
        {
            *player_a_coverage.get("missing_sources", []),
            *player_b_coverage.get("missing_sources", []),
        }
    )

    if raw_comparison is not None:
        comparison_coverage = dict(raw_comparison.provider_coverage)
    else:
        comparison_coverage = {
            "provider": "merged",
            "has_data": False,
            "coverage_status": "missing",
            "freshness_label": "unknown",
            "source_updated_at": latest_updated_at,
            "last_synced_at": latest_synced_at,
            "matches_sampled": None,
            "minutes_sampled": None,
            "coverage_notes": [
                "No deterministic playerdata comparison exists for the requested players and filters."
            ],
        }

    comparison_coverage["available_sources"] = available_sources
    comparison_coverage["missing_sources"] = missing_sources
    comparison_coverage["player_a"] = player_a_coverage
    comparison_coverage["player_b"] = player_b_coverage
    comparison_coverage["source_updated_at"] = comparison_coverage.get("source_updated_at") or latest_updated_at
    comparison_coverage["last_synced_at"] = comparison_coverage.get("last_synced_at") or latest_synced_at
    comparison_coverage["source_count"] = len(available_sources) + len(missing_sources)
    comparison_coverage["available_source_count"] = len(available_sources)
    comparison_coverage["missing_source_count"] = len(missing_sources)
    return comparison_coverage


def compare_players_overview(
    player_a_id: int,
    player_b_id: int,
    *,
    season_label: str | None = None,
    season: str | None = None,
    provider: str | None = None,
    competition_code: str | None = None,
    competition_name: str | None = None,
    club_a_id: int | None = None,
    club_b_id: int | None = None,
    active_only: bool = True,
) -> dict[str, Any] | None:
    player_a_overview = get_player_overview(
        player_a_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_a_id,
        active_only=active_only,
    )
    player_b_overview = get_player_overview(
        player_b_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_id=club_b_id,
        active_only=active_only,
    )

    if player_a_overview is None or player_b_overview is None:
        return None

    raw_comparison = build_player_comparison(
        player_a_id,
        player_b_id,
        season_label=season_label,
        season=season,
        provider=provider,
        competition_code=competition_code,
        competition_name=competition_name,
        club_a_id=club_a_id,
        club_b_id=club_b_id,
    )

    metric_groups = _build_grouped_comparison_metrics(
        raw_comparison,
        player_a_position=player_a_overview.get("player", {}).get("position"),
        player_b_position=player_b_overview.get("player", {}).get("position"),
    )

    missing_reasons: list[str] = []
    if raw_comparison is None:
        missing_reasons.append("No deterministic playerdata comparison matched the requested players and filters.")
    if not player_a_overview.get("has_overview_data"):
        missing_reasons.append(f"{player_a_overview['player']['display_name']} has no stored overview data.")
    if not player_b_overview.get("has_overview_data"):
        missing_reasons.append(f"{player_b_overview['player']['display_name']} has no stored overview data.")

    provider_coverage = _build_comparison_provider_coverage(
        player_a_overview=player_a_overview,
        player_b_overview=player_b_overview,
        raw_comparison=raw_comparison,
    )

    return {
        "player_a": player_a_overview,
        "player_b": player_b_overview,
        "context": _build_comparison_context(
            player_a_overview=player_a_overview,
            player_b_overview=player_b_overview,
            raw_comparison=raw_comparison,
        ),
        "general_overview": _build_comparison_general_overview(raw_comparison),
        "metric_groups": metric_groups,
        "summary_lines": list(getattr(raw_comparison, "summary_lines", []) or []),
        "overall_winner": (
            raw_comparison.overall_winner
            if raw_comparison is not None
            else {
                "winner": None,
                "winner_player_id": None,
                "reason": "No metrics could be compared honestly.",
            }
        ),
        "provider_coverage": provider_coverage,
        "source_preferences": build_source_preference_block(
            available_sources=provider_coverage.get("available_sources", []),
        ),
        "has_comparison_data": raw_comparison is not None,
        "missing_reasons": missing_reasons,
    }


build_players_overview_comparison = compare_players_overview
get_player_overview_comparison = compare_players_overview