from __future__ import annotations


class TeamMappingNotFoundError(LookupError):
    def __init__(
        self,
        *,
        team_name: str,
        short_name: str | None = None,
        tla: str | None = None,
        competition_name: str | None = None,
        season_label: str | None = None,
    ) -> None:
        details: list[str] = [f"name='{team_name}'"]

        if short_name:
            details.append(f"short_name='{short_name}'")
        if tla:
            details.append(f"tla='{tla}'")
        if competition_name:
            details.append(f"competition='{competition_name}'")
        if season_label:
            details.append(f"season='{season_label}'")

        message = (
            "Could not map livefootball team to an Understat canonical team name. "
            f"Tried: {', '.join(details)}."
        )
        super().__init__(message)

        self.team_name = team_name
        self.short_name = short_name
        self.tla = tla
        self.competition_name = competition_name
        self.season_label = season_label