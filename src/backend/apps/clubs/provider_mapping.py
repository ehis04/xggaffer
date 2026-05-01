from __future__ import annotations

from apps.clubs.models import Club, ProClubProviderLink


def get_provider_club(provider: str, provider_team_id: str) -> Club | None:
    link = ProClubProviderLink.objects.select_related('club').filter(
        provider=provider,
        provider_team_id=provider_team_id,
    ).first()
    return link.club if link else None


def get_clubs_for_provider_sync(provider: str):
    return Club.objects.filter(
        club_type=Club.ClubType.SYSTEM_PROFESSIONAL,
        provider_link__provider=provider,
    ).select_related('provider_link')


def assert_provider_managed(club: Club) -> None:
    assert club.club_type == Club.ClubType.SYSTEM_PROFESSIONAL, (
        f'Provider sync attempted on user-managed club: {club.id} ({club.name})'
    )