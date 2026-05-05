from datetime import timedelta
import unicodedata

from django.db import transaction
from django.db.models import Q, Case, When, Value, IntegerField, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.livefootball.models import CompetitionFixture, CompetitionTableRow, TeamDirectoryEntry
from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player, PlayerExternalIdentity
from apps.teamsheets.models import Teamsheet
from apps.tactics.models import TacticsBoard
from services.providers.football_data.exceptions import FootballDataError
from services.providers.football_data.sync import sync_club_team_squad
from services.providers.understat.exceptions import UnderstatError
from services.providers.understat.sync import sync_understat_club_season

from ..envelope import build_clubs_envelope
from ..models import (
    Club,
    ClubFan,
    ClubMembership,
    ClubPlayer,
    ClubPlayerInjury,
    ClubSeasonResult,
    Fixture,
)
from ..permissions import (
    CanCreateClub,
    CanManageOwnClubTrash,
    IsAuthenticatedOrBypass,
    IsClubMemberOrPublicRead,
    should_bypass_permissions,
)
from ..serializers import (
    AvailablePlayerSerializer,
    ClubCalendarFeedItemSerializer,
    ClubDuplicateSerializer,
    ClubListSerializer,
    ClubSerializer,
    ClubTrashActionSerializer,
    ClubWriteSerializer,
    TrashListItemSerializer,
)


def apply_club_player_position_filter(queryset, position):
    if not position:
        return queryset

    return queryset.filter(
        Q(player__primary_position=position) |
        Q(player__secondary_positions__contains=[position]) |
        Q(primary_position=position) |
        Q(secondary_position=position)
    ).distinct()


def apply_club_player_search_filter(queryset, search):
    if not search:
        return queryset

    return queryset.filter(
        Q(player__first_name__icontains=search) |
        Q(player__last_name__icontains=search) |
        Q(player__display_name__icontains=search) |
        Q(first_name__icontains=search) |
        Q(last_name__icontains=search) |
        Q(display_name__icontains=search)
    ).distinct()


def get_listed_directory_filter():
    return (
        Q(directory_visibility=Club.DirectoryVisibility.LISTED) |
        Q(directory_visibility__isnull=True, visibility=Club.Visibility.PUBLIC) |
        Q(directory_visibility='', visibility=Club.Visibility.PUBLIC)
    )


def apply_club_search_filter(queryset, search):
    if not search:
        return queryset

    search = search.strip()
    if not search:
        return queryset

    return queryset.filter(
        Q(name__icontains=search) |
        Q(description__icontains=search) |
        Q(city__icontains=search) |
        Q(country__icontains=search) |
        Q(stadium__icontains=search) |
        Q(division__icontains=search) |
        Q(source_real_club_name__icontains=search)
    ).distinct()


def _normalise_club_name(value: str) -> str:
    if not value:
        return ''

    normalised = unicodedata.normalize('NFKD', value)
    ascii_only = normalised.encode('ascii', 'ignore').decode('ascii')
    tokens = ''.join(ch if ch.isalnum() else ' ' for ch in ascii_only.lower()).split()
    return ' '.join(tokens)


FEATURED_FAN_CLUB_KEYS = {
    'manchester united',
    'manchester united fc',
    'real madrid',
    'real madrid cf',
    'bayern munich',
    'fc bayern munchen',
    'paris saint germain',
    'paris saint germain fc',
    'psg',
    'juventus',
    'juventus fc',
}

FEATURED_FAN_CLUB_CANONICAL_KEYS = {
    'manchester united': 'manchester united',
    'manchester united fc': 'manchester united',
    'real madrid': 'real madrid',
    'real madrid cf': 'real madrid',
    'bayern munich': 'bayern munich',
    'fc bayern munchen': 'bayern munich',
    'paris saint germain': 'psg',
    'paris saint germain fc': 'psg',
    'psg': 'psg',
    'juventus': 'juventus',
    'juventus fc': 'juventus',
}

FEATURED_FAN_CLUB_ORDER = {
    'manchester united': 0,
    'real madrid': 1,
    'bayern munich': 2,
    'psg': 3,
    'juventus': 4,
}


def _is_featured_fan_club(club: Club) -> bool:
    return _normalise_club_name(club.name) in FEATURED_FAN_CLUB_KEYS


def apply_featured_fan_club_filter(queryset):
    selected_by_key = {}
    for club_id, club_name in queryset.order_by('id').values_list('id', 'name'):
        canonical_key = FEATURED_FAN_CLUB_CANONICAL_KEYS.get(_normalise_club_name(club_name))
        if canonical_key and canonical_key not in selected_by_key:
            selected_by_key[canonical_key] = club_id

    club_ids = [
        selected_by_key[key]
        for key, _order in sorted(FEATURED_FAN_CLUB_ORDER.items(), key=lambda item: item[1])
        if key in selected_by_key
    ]
    return queryset.filter(id__in=club_ids)


def _normalise_person_name(value: str) -> str:
    if not value:
        return ''

    normalised = unicodedata.normalize('NFKD', value)
    ascii_only = normalised.encode('ascii', 'ignore').decode('ascii')
    tokens = ''.join(ch if ch.isalnum() else ' ' for ch in ascii_only.lower()).split()
    return ' '.join(tokens)


def _current_playerdata_season_label() -> str:
    today = timezone.now().date()
    return str(today.year if today.month >= 7 else today.year - 1)


def get_understat_enrichment_prefetch():
    return Prefetch(
        'season_enrichments',
        queryset=ClubSeasonEnrichment.objects.filter(
            provider=ExternalProvider.UNDERSTAT
        ).order_by('-season_label', '-updated_at', '-id'),
        to_attr='prefetched_understat_enrichments',
    )


class ClubViewSet(viewsets.ModelViewSet):
    serializer_class = ClubSerializer
    pagination_class = None  # Disable pagination for club list

    def get_permissions(self):
        if self.action in ['create', 'duplicate']:
            return [IsAuthenticatedOrBypass(), CanCreateClub()]

        if self.action == 'follow':
            return [IsAuthenticatedOrBypass()]

        if self.action in ['trash', 'restore', 'permanent_delete', 'destroy']:
            return [IsAuthenticatedOrBypass(), CanManageOwnClubTrash()]

        if self.action == 'trash_items':
            return [IsAuthenticatedOrBypass()]

        return [IsAuthenticatedOrBypass(), IsClubMemberOrPublicRead()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubWriteSerializer
        return ClubSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        response_serializer = ClubSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        response_serializer = ClubSerializer(
            serializer.instance,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def _with_understat_summary(self, queryset):
        return queryset.prefetch_related(get_understat_enrichment_prefetch())

    def _get_trash_mode(self) -> str:
        value = (self.request.query_params.get('trash') or '').strip().lower()
        if value in {'only', 'include'}:
            return value
        return 'exclude'

    def _base_queryset(self):
        return self._with_understat_summary(
            Club.objects.select_related('creator')
        )

    def _build_queryset(self, *, scope_override=None, include_trashed=False):
        user = self.request.user
        scope = scope_override if scope_override is not None else self.request.query_params.get('scope')
        search = self.request.query_params.get('search')
        listed_filter = get_listed_directory_filter()
        base_queryset = self._base_queryset()

        if not user.is_authenticated:
            queryset = base_queryset.filter(
                listed_filter,
                is_trashed=False,
            )
            if scope == 'browse':
                queryset = apply_featured_fan_club_filter(queryset)
            return apply_club_search_filter(queryset, search)

        member_club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
        ).values_list('club_id', flat=True)

        if scope == 'mine':
            active_filter = Q(id__in=member_club_ids)
        elif scope == 'browse':
            active_filter = listed_filter & ~Q(id__in=member_club_ids)
        elif scope == 'followed':
            active_filter = Q(fans__user=user)
        else:
            active_filter = Q(id__in=member_club_ids) | listed_filter

        trash_mode = 'include' if include_trashed else self._get_trash_mode()

        if trash_mode == 'only':
            if scope in {'browse', 'followed'}:
                queryset = base_queryset.none()
            else:
                queryset = base_queryset.filter(
                    creator=user,
                    is_trashed=True,
                )
            return apply_club_search_filter(queryset, search)

        active_queryset = base_queryset.filter(
            active_filter,
            is_trashed=False,
        ).distinct()

        if scope == 'browse':
            active_queryset = apply_featured_fan_club_filter(active_queryset)

        if trash_mode == 'include' and scope not in {'browse', 'followed'}:
            queryset = base_queryset.filter(
                (active_filter & Q(is_trashed=False)) |
                Q(creator=user, is_trashed=True)
            ).distinct()
            return apply_club_search_filter(queryset, search)

        return apply_club_search_filter(active_queryset, search)

    def _get_club_for_action(self, pk, *, require_trashed=None):
        club = get_object_or_404(self._base_queryset(), pk=pk)
        self.check_object_permissions(self.request, club)

        if require_trashed is True and not club.is_trashed:
            raise ValidationError('This club is not in trash.')

        if require_trashed is False and club.is_trashed:
            raise ValidationError('This club is already in trash.')

        return club

    def _normalise_trash_section(self) -> str:
        value = (self.request.query_params.get('section') or 'all').strip().lower()
        allowed = {'all', 'clubs', 'teamsheets', 'tactics'}

        if value not in allowed:
            raise ValidationError({
                'section': 'section must be one of: all, clubs, teamsheets, tactics.'
            })

        return value

    def _build_shared_trash_items(self, user, section: str) -> list[dict]:
        items: list[dict] = []

        if section in {'all', 'clubs'}:
            clubs = self._base_queryset().filter(
                creator=user,
                is_trashed=True,
            ).order_by('-trashed_at', '-updated_at')

            for club in clubs:
                secondary_parts = [club.city, club.country, club.division]
                secondary_text = ' · '.join(part for part in secondary_parts if part)

                items.append({
                    'id': club.id,
                    'section': 'clubs',
                    'title': club.name,
                    'secondary_text': secondary_text or None,
                    'club_id': club.id,
                    'club_name': club.name,
                    'trashed_at': club.trashed_at,
                    'trash_expires_at': club.trash_expires_at,
                    'updated_at': club.updated_at,
                    'route_path': f'/clubs/{club.id}/?view=trash',
                })

        if section in {'all', 'teamsheets'}:
            teamsheets = Teamsheet.objects.filter(
                created_by=user,
                is_trashed=True,
            ).select_related(
                'club',
            ).order_by('-trashed_at', '-updated_at')

            for teamsheet in teamsheets:
                formation_display = teamsheet.get_formation_display()
                opponent_part = f' · vs {teamsheet.opponent}' if teamsheet.opponent else ''
                template_part = ' · Template' if teamsheet.is_template else ''

                items.append({
                    'id': teamsheet.id,
                    'section': 'teamsheets',
                    'title': teamsheet.title,
                    'secondary_text': f'{formation_display}{opponent_part}{template_part}',
                    'club_id': teamsheet.club_id,
                    'club_name': teamsheet.club.name,
                    'trashed_at': teamsheet.trashed_at,
                    'trash_expires_at': teamsheet.trash_expires_at,
                    'updated_at': teamsheet.updated_at,
                    'route_path': f'/clubs/{teamsheet.club_id}/teamsheets/{teamsheet.id}?view=trash',
                })

        if section in {'all', 'tactics'}:
            boards = TacticsBoard.objects.filter(
                created_by=user,
                is_trashed=True,
            ).select_related(
                'club',
            ).order_by('-trashed_at', '-updated_at')

            for board in boards:
                board_type_label = board.get_board_type_display()
                template_part = ' · Template' if board.is_template else ''
                linked_part = ' · Linked to teamsheet' if board.linked_teamsheet_id else ''

                items.append({
                    'id': board.id,
                    'section': 'tactics',
                    'title': board.title,
                    'secondary_text': f'{board_type_label}{template_part}{linked_part}',
                    'club_id': board.club_id,
                    'club_name': board.club.name,
                    'trashed_at': board.trashed_at,
                    'trash_expires_at': board.trash_expires_at,
                    'updated_at': board.updated_at,
                    'route_path': f'/clubs/{board.club_id}/tactics-boards/{board.id}?view=trash',
                })

        items.sort(
            key=lambda item: item['trashed_at'] or item['updated_at'],
            reverse=True,
        )

        return items

    def get_queryset(self):
        return self._build_queryset()

    def _find_source_system_club(self, source_name: str):
        source_key = _normalise_club_name(source_name)
        if not source_key:
            return None

        candidates = list(
            Club.objects.filter(club_type=Club.ClubType.SYSTEM_PROFESSIONAL)
            .only('id', 'name')
            .order_by('id')
        )

        exact_match = next(
            (club for club in candidates if _normalise_club_name(club.name) == source_key),
            None,
        )
        if exact_match is not None:
            return exact_match

        startswith_match = next(
            (
                club
                for club in candidates
                if _normalise_club_name(club.name).startswith(source_key)
                or source_key.startswith(_normalise_club_name(club.name))
            ),
            None,
        )
        if startswith_match is not None:
            return startswith_match

        return next(
            (
                club
                for club in candidates
                if source_key in _normalise_club_name(club.name)
                or _normalise_club_name(club.name) in source_key
            ),
            None,
        )

    def _player_profile_provider_set(self, player: Player | None, season_label: str) -> set[str]:
        if player is None:
            return set()

        return set(
            PlayerSeasonEnrichment.objects.filter(
                player=player,
                season_label=season_label,
                provider__in=[
                    ExternalProvider.UNDERSTAT,
                    ExternalProvider.SOFASCORE,
                ],
            ).values_list('provider', flat=True).distinct()
        )

    def _club_player_name_keys(self, club_player: ClubPlayer) -> set[str]:
        keys = {
            _normalise_person_name(club_player.display_name),
            _normalise_person_name(
                f'{club_player.first_name} {club_player.last_name}'.strip()
            ),
        }

        if club_player.player_id:
            keys.update({
                _normalise_person_name(club_player.player.display_name),
                _normalise_person_name(club_player.player.full_name),
            })

        keys.discard('')
        return keys

    def _matching_current_profile_club_players(
        self,
        *,
        source_club: Club,
        source_player: ClubPlayer,
        season_label: str,
    ):
        target_keys = self._club_player_name_keys(source_player)
        if not target_keys:
            return []

        enriched_club_players = (
            source_club.club_players
            .filter(
                player__season_enrichments__season_label=season_label,
                player__season_enrichments__provider__in=[
                    ExternalProvider.UNDERSTAT,
                    ExternalProvider.SOFASCORE,
                ],
            )
            .select_related('player')
            .distinct()
        )

        return [
            candidate
            for candidate in enriched_club_players
            if candidate.player_id
            and target_keys & self._club_player_name_keys(candidate)
        ]

    def _copy_missing_current_profile_data(
        self,
        *,
        target_player: Player,
        candidates: list[ClubPlayer],
        season_label: str,
    ) -> None:
        candidate_player_ids = {
            candidate.player_id
            for candidate in candidates
            if candidate.player_id and candidate.player_id != target_player.id
        }
        if not candidate_player_ids:
            return

        profile_providers = [
            ExternalProvider.UNDERSTAT,
            ExternalProvider.SOFASCORE,
        ]

        existing_providers = set(
            PlayerSeasonEnrichment.objects.filter(
                player=target_player,
                season_label=season_label,
                provider__in=profile_providers,
            ).values_list('provider', flat=True).distinct()
        )

        enrichments = (
            PlayerSeasonEnrichment.objects
            .filter(
                player_id__in=candidate_player_ids,
                season_label=season_label,
                provider__in=profile_providers,
            )
            .order_by('provider', '-matches_played', '-minutes_played', '-updated_at', '-id')
        )

        for enrichment in enrichments:
            if enrichment.provider in existing_providers:
                continue

            PlayerSeasonEnrichment.objects.update_or_create(
                player=target_player,
                provider=enrichment.provider,
                season_label=enrichment.season_label,
                competition_code=enrichment.competition_code,
                external_team_id=enrichment.external_team_id,
                defaults={
                    'club': enrichment.club,
                    'competition_name': enrichment.competition_name,
                    'external_player_id': enrichment.external_player_id,
                    'matches_played': enrichment.matches_played,
                    'minutes_played': enrichment.minutes_played,
                    'goals': enrichment.goals,
                    'assists': enrichment.assists,
                    'shots': enrichment.shots,
                    'xg': enrichment.xg,
                    'xa': enrichment.xa,
                    'npg': enrichment.npg,
                    'npxg': enrichment.npxg,
                    'xg_chain': enrichment.xg_chain,
                    'xg_buildup': enrichment.xg_buildup,
                    'yellow_cards': enrichment.yellow_cards,
                    'red_cards': enrichment.red_cards,
                    'key_passes': enrichment.key_passes,
                    'last_synced_at': enrichment.last_synced_at,
                    'metadata': enrichment.metadata,
                    'raw_snapshot': enrichment.raw_snapshot,
                },
            )
            existing_providers.add(enrichment.provider)

        existing_identity_providers = set(
            PlayerExternalIdentity.objects.filter(
                player=target_player,
                provider__in=profile_providers,
            ).values_list('provider', flat=True).distinct()
        )
        identities = (
            PlayerExternalIdentity.objects
            .filter(
                player_id__in=candidate_player_ids,
                provider__in=profile_providers,
            )
            .order_by('provider', '-is_primary', '-last_synced_at', '-updated_at', '-id')
        )
        for identity in identities:
            if identity.provider in existing_identity_providers:
                continue
            identity.player = target_player
            identity.last_synced_at = identity.last_synced_at or timezone.now()
            identity.save(update_fields=['player', 'last_synced_at', 'updated_at'])
            existing_identity_providers.add(identity.provider)

    def _resolve_profile_player_for_copy(
        self,
        *,
        source_club: Club,
        source_player: ClubPlayer,
    ) -> Player | None:
        target_keys = self._club_player_name_keys(source_player)
        if not target_keys:
            return source_player.player

        season_label = _current_playerdata_season_label()
        provider_order = {
            ExternalProvider.UNDERSTAT: 2,
            ExternalProvider.SOFASCORE: 1,
        }
        matching_candidates = self._matching_current_profile_club_players(
            source_club=source_club,
            source_player=source_player,
            season_label=season_label,
        )

        if source_player.player_id:
            self._copy_missing_current_profile_data(
                target_player=source_player.player,
                candidates=matching_candidates,
                season_label=season_label,
            )
            return source_player.player

        candidates: list[tuple[tuple[int, int, int, int], Player]] = []
        for candidate in matching_candidates:
            providers = self._player_profile_provider_set(candidate.player, season_label)
            if not providers:
                continue

            candidates.append((
                (
                    len(providers),
                    sum(provider_order.get(provider, 0) for provider in providers),
                    int(candidate.is_active),
                    -candidate.id,
                ),
                candidate.player,
            ))

        if not candidates:
            return source_player.player

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _bootstrap_real_club_copy(self, club: Club, owner):
        if club.club_type != Club.ClubType.USER_FICTIONAL:
            return

        if club.fictional_basis != Club.FictionalBasis.REAL_CLUB_COPY:
            return

        source_name = (club.source_real_club_name or '').strip()
        if not source_name:
            return

        source_club = self._find_source_system_club(source_name)
        if source_club is None:
            return

        source_players = source_club.club_players.filter(is_active=True).select_related('player')
        source_to_new_player_ids = {}
        used_numbers = set()

        for source_player in source_players:
            linked_player = self._resolve_profile_player_for_copy(
                source_club=source_club,
                source_player=source_player,
            )

            if linked_player is None:
                linked_player = Player(
                    first_name=source_player.first_name,
                    last_name=source_player.last_name,
                    display_name=source_player.display_name,
                    primary_position=source_player.primary_position,
                    preferred_foot=source_player.preferred_foot,
                    date_of_birth=source_player.date_of_birth,
                    height_cm=source_player.height_cm,
                )

                if hasattr(linked_player, 'secondary_positions'):
                    linked_player.secondary_positions = (
                        [source_player.secondary_position]
                        if source_player.secondary_position else []
                    )

                if hasattr(linked_player, 'photo'):
                    linked_player.photo = source_player.photo

                linked_player.save()

            squad_number = source_player.squad_number
            if squad_number in used_numbers:
                squad_number = None
            if squad_number is not None:
                used_numbers.add(squad_number)

            new_player = ClubPlayer.objects.create(
                club=club,
                player=linked_player,
                user=None,
                first_name=source_player.first_name,
                last_name=source_player.last_name,
                display_name=source_player.display_name,
                squad_number=squad_number,
                primary_position=source_player.primary_position,
                secondary_position=source_player.secondary_position,
                preferred_foot=source_player.preferred_foot,
                date_of_birth=source_player.date_of_birth,
                height_cm=source_player.height_cm,
                photo=source_player.photo,
                is_active=source_player.is_active,
                is_public=False,
                created_by=owner,
            )
            source_to_new_player_ids[source_player.id] = new_player.id

        current_injuries = ClubPlayerInjury.objects.filter(
            club_player__club=source_club,
            is_current=True,
        ).select_related('club_player')
        for injury in current_injuries:
            new_player_id = source_to_new_player_ids.get(injury.club_player_id)
            if not new_player_id:
                continue

            ClubPlayerInjury.objects.create(
                club_player_id=new_player_id,
                injury_type=injury.injury_type,
                severity=injury.severity,
                availability_status=injury.availability_status,
                injured_at=injury.injured_at,
                estimated_return=injury.estimated_return,
                notes=injury.notes,
                is_current=True,
                recorded_by=owner,
            )

        latest_understat = source_club.season_enrichments.filter(
            provider=ExternalProvider.UNDERSTAT,
        ).order_by('-season_label', '-updated_at', '-id').first()
        # Only use understat if it has actual data (non-zero values)
        if latest_understat is not None and (
            latest_understat.wins > 0 or
            latest_understat.draws > 0 or
            latest_understat.losses > 0 or
            latest_understat.goals_for > 0 or
            latest_understat.goals_against > 0
        ):
            ClubSeasonEnrichment.objects.update_or_create(
                club=club,
                provider=latest_understat.provider,
                season_label=latest_understat.season_label,
                competition_code=latest_understat.competition_code,
                defaults={
                    'competition_name': latest_understat.competition_name,
                    'external_team_id': latest_understat.external_team_id,
                    'matches_played': latest_understat.matches_played,
                    'wins': latest_understat.wins,
                    'draws': latest_understat.draws,
                    'losses': latest_understat.losses,
                    'goals_for': latest_understat.goals_for,
                    'goals_against': latest_understat.goals_against,
                    'xg': latest_understat.xg,
                    'xga': latest_understat.xga,
                    'npxg': latest_understat.npxg,
                    'ppda': latest_understat.ppda,
                    'last_synced_at': latest_understat.last_synced_at,
                    'metadata': latest_understat.metadata,
                    'raw_snapshot': latest_understat.raw_snapshot,
                },
            )
        else:
            # Try football_data enrichment first, then fall back to livefootball
            latest_football_data = source_club.season_enrichments.filter(
                provider=ExternalProvider.FOOTBALL_DATA,
            ).order_by('-season_label', '-updated_at', '-id').first()
            if latest_football_data is not None and (
                latest_football_data.wins > 0 or
                latest_football_data.draws > 0 or
                latest_football_data.losses > 0 or
                latest_football_data.goals_for > 0 or
                latest_football_data.goals_against > 0
            ):
                ClubSeasonEnrichment.objects.update_or_create(
                    club=club,
                    provider=latest_football_data.provider,
                    season_label=latest_football_data.season_label,
                    competition_code=latest_football_data.competition_code,
                    defaults={
                        'competition_name': latest_football_data.competition_name,
                        'external_team_id': latest_football_data.external_team_id,
                        'matches_played': latest_football_data.matches_played,
                        'wins': latest_football_data.wins,
                        'draws': latest_football_data.draws,
                        'losses': latest_football_data.losses,
                        'goals_for': latest_football_data.goals_for,
                        'goals_against': latest_football_data.goals_against,
                        'last_synced_at': latest_football_data.last_synced_at,
                    },
                )
            else:
                self._bootstrap_enrichment_from_livefootball(club, source_club)

        source_team = self._get_livefootball_team_entry(source_club)
        recent_results = list(source_club.season_results.order_by('-match_date', '-created_at')[:38])
        if recent_results:
            for result in recent_results:
                ClubSeasonResult.objects.create(
                    club=club,
                    opponent_name=result.opponent_name,
                    venue=result.venue,
                    competition=result.competition,
                    match_date=result.match_date,
                    goals_for=result.goals_for,
                    goals_against=result.goals_against,
                    fixture=None,
                    notes=result.notes,
                    created_by=owner,
                )
        else:
            for match in self._get_livefootball_fixtures_for_source(source_club).filter(
                status='FINISHED'
            ).order_by('-kickoff_at', '-id')[:38]:
                venue, opponent_name, goals_for, goals_against = self._map_livefootball_fixture(
                    source_team=source_team,
                    match=match,
                )
                if opponent_name is None or match.kickoff_at is None:
                    continue

                ClubSeasonResult.objects.create(
                    club=club,
                    opponent_name=opponent_name,
                    venue=venue,
                    competition=match.competition.name,
                    match_date=match.kickoff_at.date(),
                    goals_for=goals_for or 0,
                    goals_against=goals_against or 0,
                    fixture=None,
                    notes='Imported from livefootball fixture history.',
                    created_by=owner,
                )

        now = timezone.now()
        upcoming_fixtures = list(
            source_club.fixtures.filter(
                match_datetime__gte=now,
            ).order_by('match_datetime', 'id')[:30]
        )
        if upcoming_fixtures:
            for fixture in upcoming_fixtures:
                Fixture.objects.create(
                    club=club,
                    opponent_name=fixture.opponent_name,
                    venue=fixture.venue,
                    competition=fixture.competition,
                    match_datetime=fixture.match_datetime,
                    location=fixture.location,
                    fixture_status=fixture.fixture_status,
                    source_type=Fixture.SourceType.MANUAL,
                    external_fixture_id='',
                    created_by=owner,
                )
        else:
            for match in self._get_livefootball_fixtures_for_source(source_club).filter(
                Q(status__in=['TIMED', 'SCHEDULED']),
                kickoff_at__gte=now,
            ).order_by('kickoff_at', 'id')[:30]:
                venue, opponent_name, _, _ = self._map_livefootball_fixture(
                    source_team=source_team,
                    match=match,
                )
                if opponent_name is None or match.kickoff_at is None:
                    continue

                Fixture.objects.create(
                    club=club,
                    opponent_name=opponent_name,
                    venue=venue,
                    competition=match.competition.name,
                    match_datetime=match.kickoff_at,
                    location='',
                    fixture_status=Fixture.FixtureStatus.SCHEDULED,
                    source_type=Fixture.SourceType.MANUAL,
                    external_fixture_id='',
                    created_by=owner,
                )

    def _get_livefootball_team_entry(self, source_club: Club):
        source_key = _normalise_club_name(source_club.name)
        for entry in TeamDirectoryEntry.objects.select_related('competition').order_by('-season_label', '-id'):
            if _normalise_club_name(entry.name) == source_key:
                return entry
        return None

    def _bootstrap_enrichment_from_livefootball(self, club: Club, source_club: Club) -> bool:
        team_entry = self._get_livefootball_team_entry(source_club)
        if team_entry is None:
            return False

        table_row = (
            CompetitionTableRow.objects
            .filter(team=team_entry)
            .select_related('snapshot', 'snapshot__competition')
            .order_by('-snapshot__season_label', '-snapshot__synced_at', '-id')
            .first()
        )
        if table_row is None:
            return False

        snapshot = table_row.snapshot
        competition = snapshot.competition
        ClubSeasonEnrichment.objects.update_or_create(
            club=club,
            provider=team_entry.provider,
            season_label=snapshot.season_label,
            competition_code=competition.code or '',
            defaults={
                'competition_name': competition.name,
                'matches_played': table_row.played,
                'wins': table_row.won,
                'draws': table_row.drawn,
                'losses': table_row.lost,
                'goals_for': table_row.goals_for,
                'goals_against': table_row.goals_against,
            },
        )
        return True

    def _get_livefootball_fixtures_for_source(self, source_club: Club):
        team = self._get_livefootball_team_entry(source_club)
        if team is None:
            return CompetitionFixture.objects.none()

        return CompetitionFixture.objects.filter(
            Q(home_team=team) | Q(away_team=team)
        ).select_related('competition', 'home_team', 'away_team')

    def _map_livefootball_fixture(self, *, source_team: TeamDirectoryEntry | None, match: CompetitionFixture):
        if source_team is not None and match.home_team_id == source_team.id:
            return (
                ClubSeasonResult.Venue.HOME,
                match.away_team_name,
                match.home_score,
                match.away_score,
            )

        if source_team is not None and match.away_team_id == source_team.id:
            return (
                ClubSeasonResult.Venue.AWAY,
                match.home_team_name,
                match.away_score,
                match.home_score,
            )

        return (None, None, None, None)

    def perform_create(self, serializer):
        with transaction.atomic():
            club = serializer.save(creator=self.request.user)
            ClubMembership.objects.create(
                user=self.request.user,
                club=club,
                role=ClubMembership.Role.OWNER,
                is_active=True,
            )
            self._bootstrap_real_club_copy(club, self.request.user)

    def perform_destroy(self, instance):
        if not instance.can_be_trashed_by(self.request.user):
            raise PermissionDenied(
                'Only the club creator can move this club to trash.'
            )

        instance.move_to_trash(self.request.user)

    @action(detail=True, methods=['post', 'delete'], url_path='follow')
    def follow(self, request, pk=None):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied('You must be signed in to follow clubs.')

        club = self._get_club_for_action(pk, require_trashed=False)
        is_listed = Club.objects.filter(
            get_listed_directory_filter(),
            pk=club.pk,
        ).exists()

        if not is_listed or not _is_featured_fan_club(club):
            raise ValidationError('Only featured browse clubs can be followed.')

        if request.method == 'DELETE':
            ClubFan.objects.filter(user=user, club=club).delete()
        else:
            ClubFan.objects.get_or_create(user=user, club=club)

        serializer = ClubSerializer(
            club,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        source_club = self.get_object()
        serializer = ClubDuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_name = serializer.validated_data.get('name') or f'Copy of {source_club.name}'
        include_players = serializer.validated_data['include_players']
        visibility = serializer.validated_data['visibility']
        inferred_source_name = ''
        if source_club.club_type == Club.ClubType.SYSTEM_PROFESSIONAL:
            inferred_source_name = source_club.name
        elif (
            source_club.fictional_basis == Club.FictionalBasis.REAL_CLUB_COPY
            and (source_club.source_real_club_name or '').strip()
        ):
            inferred_source_name = source_club.source_real_club_name.strip()
        else:
            inferred_system_club = self._find_source_system_club(source_club.name)
            if inferred_system_club is not None:
                inferred_source_name = inferred_system_club.name

        is_real_copy_source = bool(inferred_source_name)

        user = request.user if request.user.is_authenticated else source_club.creator

        with transaction.atomic():
            new_club = Club.objects.create(
                name=new_name,
                description=source_club.description,
                creator=user,
                visibility=visibility,
                club_type=(
                    Club.ClubType.USER_FICTIONAL
                    if is_real_copy_source else source_club.club_type
                ),
                fictional_basis=(
                    Club.FictionalBasis.REAL_CLUB_COPY
                    if is_real_copy_source else source_club.fictional_basis
                ),
                source_real_club_name=(
                    inferred_source_name
                    if is_real_copy_source else source_club.source_real_club_name
                ),
                directory_visibility=source_club.directory_visibility,
                join_policy=(
                    Club.JoinPolicy.APPROVAL_REQUIRED
                    if is_real_copy_source else source_club.join_policy
                ),
                city=source_club.city,
                country=source_club.country,
                stadium=source_club.stadium,
                division=source_club.division,
                achievements='',
            )

            ClubMembership.objects.create(
                user=user,
                club=new_club,
                role=ClubMembership.Role.OWNER,
                is_active=True,
            )

            if include_players and not is_real_copy_source:
                source_players = source_club.club_players.filter(
                    is_active=True,
                ).select_related('player')

                for source_player in source_players:
                    linked_player = source_player.player

                    if linked_player is None:
                        linked_player = Player(
                            first_name=source_player.first_name,
                            last_name=source_player.last_name,
                            display_name=source_player.display_name,
                            primary_position=source_player.primary_position,
                            preferred_foot=source_player.preferred_foot,
                            date_of_birth=source_player.date_of_birth,
                            height_cm=source_player.height_cm,
                        )

                        if hasattr(linked_player, 'secondary_positions'):
                            linked_player.secondary_positions = (
                                [source_player.secondary_position]
                                if source_player.secondary_position else []
                            )

                        if hasattr(linked_player, 'photo'):
                            linked_player.photo = source_player.photo

                        linked_player.save()

                    ClubPlayer.objects.create(
                        club=new_club,
                        player=linked_player,
                        user=None,
                        first_name=source_player.first_name,
                        last_name=source_player.last_name,
                        display_name=source_player.display_name,
                        squad_number=source_player.squad_number,
                        primary_position=source_player.primary_position,
                        secondary_position=source_player.secondary_position,
                        preferred_foot=source_player.preferred_foot,
                        date_of_birth=source_player.date_of_birth,
                        height_cm=source_player.height_cm,
                        photo=source_player.photo,
                        is_active=source_player.is_active,
                        is_public=source_player.is_public,
                        created_by=user,
                    )

            if is_real_copy_source:
                self._bootstrap_real_club_copy(new_club, user)

        response_serializer = ClubSerializer(new_club)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='trash')
    def trash(self, request, pk=None):
        serializer = ClubTrashActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        club = self._get_club_for_action(pk, require_trashed=False)
        club.move_to_trash(request.user)

        response_serializer = ClubSerializer(
            self._base_queryset().get(pk=club.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='restore')
    def restore(self, request, pk=None):
        serializer = ClubTrashActionSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        club = self._get_club_for_action(pk, require_trashed=True)
        club.restore_from_trash(request.user)

        response_serializer = ClubSerializer(
            self._base_queryset().get(pk=club.pk),
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='permanent-delete')
    def permanent_delete(self, request, pk=None):
        club = self._get_club_for_action(pk, require_trashed=True)

        if not club.can_be_permanently_deleted_by(request.user):
            raise PermissionDenied(
                'Only the club creator can permanently delete this club.'
            )

        club.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def available_players(self, request, pk=None):
        club = self.get_object()
        position = request.query_params.get('position')
        search = request.query_params.get('search')

        queryset = ClubPlayer.objects.filter(
            club=club,
            is_active=True,
        )

        if club.visibility == Club.Visibility.PUBLIC:
            queryset = ClubPlayer.objects.filter(
                Q(club=club, is_active=True) |
                Q(is_public=True, is_active=True)
            ).exclude(
                Q(is_public=True, club=club, is_active=True) &
                ~Q(club=club)
            )

        queryset = queryset.select_related('club', 'user', 'player').prefetch_related(
            'player__external_identities'
        )

        queryset = apply_club_player_position_filter(queryset, position)
        queryset = apply_club_player_search_filter(queryset, search)

        queryset = queryset.annotate(
            club_priority=Case(
                When(club_id=club.id, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            sort_primary_position=Coalesce('player__primary_position', 'primary_position'),
            sort_last_name=Coalesce('player__last_name', 'last_name'),
        ).order_by(
            'club_priority',
            'sort_primary_position',
            'sort_last_name',
            'id',
        )

        serializer = AvailablePlayerSerializer(
            queryset,
            many=True,
            context={'club_id': club.id},
        )
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='calendar')
    def calendar(self, request, pk=None):
        club = self.get_object()

        include_past = str(
            request.query_params.get('include_past', 'false')
        ).strip().lower() in {'1', 'true', 'yes', 'y'}

        limit_param = request.query_params.get('limit')
        limit = None
        if limit_param not in (None, ''):
            try:
                limit = int(limit_param)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'limit must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if limit <= 0:
                return Response(
                    {'detail': 'limit must be greater than 0.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        events_qs = club.events.select_related(
            'club',
            'created_by',
        ).order_by('start_datetime', 'id')

        fixtures_qs = club.fixtures.select_related(
            'club',
            'created_by',
        ).order_by('match_datetime', 'id')

        if not include_past:
            now = timezone.now()
            events_qs = events_qs.filter(start_datetime__gte=now)
            fixtures_qs = fixtures_qs.filter(match_datetime__gte=now)

        combined_items = [
            {
                'item_type': 'event',
                'sort_datetime': event.start_datetime,
                'calendar_label': event.get_calendar_label(),
                'event': event,
                'fixture': None,
            }
            for event in events_qs
        ] + [
            {
                'item_type': 'fixture',
                'sort_datetime': fixture.match_datetime,
                'calendar_label': fixture.get_calendar_label(),
                'event': None,
                'fixture': fixture,
            }
            for fixture in fixtures_qs
        ]

        combined_items.sort(key=lambda item: (item['sort_datetime'], item['item_type']))

        if limit is not None:
            combined_items = combined_items[:limit]

        serializer = ClubCalendarFeedItemSerializer(
            combined_items,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def understat_season_summary(self, request, pk=None):
        club = self.get_object()

        season_label = (request.query_params.get('season') or '').strip()
        competition_code = (request.query_params.get('competition_code') or '').strip()

        queryset = club.season_enrichments.filter(
            provider=ExternalProvider.UNDERSTAT,
        )

        if season_label:
            queryset = queryset.filter(season_label=season_label)

        if competition_code:
            queryset = queryset.filter(competition_code=competition_code)

        enrichment = queryset.order_by(
            '-season_label',
            '-updated_at',
            '-id',
        ).first()

        if not enrichment:
            return Response(
                build_clubs_envelope({
                    'club_id': club.id,
                    'provider': ExternalProvider.UNDERSTAT,
                    'summary': None,
                }),
                status=status.HTTP_200_OK,
            )

        return Response(
            build_clubs_envelope({
                'club_id': club.id,
                'provider': enrichment.provider,
                'season_label': enrichment.season_label,
                'competition_code': enrichment.competition_code,
                'competition_name': enrichment.competition_name,
                'matches_played': enrichment.matches_played,
                'wins': enrichment.wins,
                'draws': enrichment.draws,
                'losses': enrichment.losses,
                'goals_for': enrichment.goals_for,
                'goals_against': enrichment.goals_against,
                'xg': enrichment.xg,
                'xga': enrichment.xga,
                'npxg': enrichment.npxg,
                'ppda': enrichment.ppda,
                'last_synced_at': (
                    enrichment.last_synced_at.isoformat()
                    if enrichment.last_synced_at else None
                ),
            }),
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrBypass])
    def sync_squad(self, request, pk=None):
        club = self.get_object()

        if not should_bypass_permissions():
            membership = ClubMembership.objects.filter(
                user=request.user,
                club=club,
                is_active=True,
            ).first()

            if membership is None or not membership.can_create_content():
                return Response(
                    {'detail': 'You do not have permission to sync this club squad.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        provider = request.data.get('provider', 'football_data')
        provider_team_id = request.data.get('provider_team_id')

        try:
            result = sync_club_team_squad(
                club=club,
                external_team_id=provider_team_id,
                provider=provider,
                triggered_by=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except FootballDataError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        summary = result['summary']
        metadata = summary.get('metadata', {})

        return Response(
            {
                'club_id': club.id,
                'provider': provider,
                'status': summary.get('status'),
                'records_processed': summary.get('records_processed', 0),
                'records_created': summary.get('records_created', 0),
                'records_updated': summary.get('records_updated', 0),
                'error_count': summary.get('error_count', 0),
                'players_created': metadata.get('players_created', 0),
                'players_updated': metadata.get('players_updated', 0),
                'player_external_identities_created': metadata.get(
                    'player_external_identities_created', 0
                ),
                'player_external_identities_updated': metadata.get(
                    'player_external_identities_updated', 0
                ),
                'club_players_created': metadata.get('club_players_created', 0),
                'club_players_updated': metadata.get('club_players_updated', 0),
                'raw_error_summary': summary.get('raw_error_summary', ''),
                'sync_job_id': result['job'].id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticatedOrBypass])
    def sync_understat_season(self, request, pk=None):
        club = self.get_object()

        if not should_bypass_permissions():
            membership = ClubMembership.objects.filter(
                user=request.user,
                club=club,
                is_active=True,
            ).first()

            if membership is None or not membership.can_create_content():
                return Response(
                    {'detail': 'You do not have permission to sync Understat data for this club.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        season_label = (request.data.get('season') or '').strip()
        competition_code = (request.data.get('competition_code') or '').strip()
        external_team_id = (request.data.get('external_team_id') or '').strip()

        if not season_label:
            return Response(
                {'detail': 'season is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = sync_understat_club_season(
                club=club,
                season_label=season_label,
                competition_code=competition_code or None,
                external_team_id=external_team_id or None,
                triggered_by=request.user if request.user.is_authenticated else None,
            )
        except ValueError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except UnderstatError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        summary = result.get('summary', {})
        enrichment = result.get('club_season_enrichment')

        return Response(
            {
                'club_id': club.id,
                'provider': ExternalProvider.UNDERSTAT,
                'status': summary.get('status'),
                'records_processed': summary.get('records_processed', 0),
                'records_created': summary.get('records_created', 0),
                'records_updated': summary.get('records_updated', 0),
                'error_count': summary.get('error_count', 0),
                'raw_error_summary': summary.get('raw_error_summary', ''),
                'sync_job_id': result['job'].id,
                'season_label': enrichment.season_label if enrichment else season_label,
                'competition_code': enrichment.competition_code if enrichment else competition_code,
                'matches_played': enrichment.matches_played if enrichment else 0,
                'xg': enrichment.xg if enrichment else None,
                'xga': enrichment.xga if enrichment else None,
                'npxg': enrichment.npxg if enrichment else None,
                'last_synced_at': (
                    enrichment.last_synced_at.isoformat()
                    if enrichment and enrichment.last_synced_at else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='trash')
    def trash_items(self, request):
        section = self._normalise_trash_section()
        items = self._build_shared_trash_items(request.user, section)

        serializer = TrashListItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def my_clubs(self, request):
        if not request.user.is_authenticated:
            return Response([], status=status.HTTP_200_OK)

        clubs = self._build_queryset(scope_override='mine')

        serializer = ClubSerializer(
            clubs.order_by('-updated_at'),
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='lookup-by-code')
    def lookup_by_code(self, request):
        code = (request.query_params.get('code') or '').strip().upper()

        if not code:
            return Response(
                {'detail': 'code query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self._with_understat_summary(
            Club.objects.filter(
                directory_visibility=Club.DirectoryVisibility.HIDDEN_CODE_ONLY,
                join_code__iexact=code,
                is_trashed=False,
            )
        )

        club = queryset.first()

        if club is None:
            return Response(
                {'detail': 'No hidden club found for that join code.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClubSerializer(
            club,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
