"""
Player sync helpers for the football-data sync service

Handles player matching, external identity updates, club roster updates, and canonical player resolution for directory data
"""

from datetime import date

from django.utils import timezone

from apps.clubs.models import ClubPlayer
from apps.players.models import Player, PlayerExternalIdentity


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

# Return the set of concrete field names for a Django model
def model_field_names(model_class):
    return {
        field.name
        for field in model_class._meta.get_fields()
        if getattr(field, "concrete", False)
    }


# Return first and last names from player data with fallback splitting
def resolved_player_names(player_data):
    first_name = (player_data.get("first_name") or "").strip()
    last_name = (player_data.get("last_name") or "").strip()

    if first_name or last_name:
        return first_name, last_name

    source_name = (player_data.get("full_name") or "").strip() or (
        player_data.get("display_name") or ""
    ).strip()

    if not source_name:
        return "Unknown", ""

    parts = source_name.split()
    if len(parts) == 1:
        return parts[0][:50], ""
    return parts[0][:50], " ".join(parts[1:])[:50]


# Format a player sync error string from raw player data and an exception
def format_player_error(raw_player, exc):
    raw_id = raw_player.get("id", "unknown")
    raw_name = raw_player.get("name") or raw_player.get("fullName") or "unknown"
    return f"player:{raw_id}:{raw_name} {exc}"


# ---------------------------------------------------------------------------
# Player record resolution
# ---------------------------------------------------------------------------

# Look up an existing player by first name last name and date of birth
def find_existing_player_match(player_data):
    first_name = player_data.get("first_name", "").strip()
    last_name = player_data.get("last_name", "").strip()
    date_of_birth = player_data.get("date_of_birth")

    if not first_name or not last_name or not date_of_birth:
        return None

    return Player.objects.filter(
        first_name__iexact=first_name,
        last_name__iexact=last_name,
        date_of_birth=date_of_birth,
    ).first()


# Build the create values for a new player from normalised player data
def build_player_create_values(player_data):
    first_name, last_name = resolved_player_names(player_data)

    values = {
        "first_name": first_name,
        "last_name": last_name,
        "display_name": player_data.get("display_name", "")[:50],
        "date_of_birth": player_data.get("date_of_birth"),
        "nationality": player_data.get("nationality", ""),
        "primary_position": player_data.get("primary_position", ""),
        "is_active": True,
    }

    fields = model_field_names(Player)
    return {k: v for k, v in values.items() if k in fields and v is not None}


# Apply safe updates to an existing player and return True if saved
def apply_player_updates(player, player_data):
    fields = model_field_names(Player)
    first_name, last_name = resolved_player_names(player_data)

    candidate_values = {
        "display_name": player_data.get("display_name", "")[:50],
        "date_of_birth": player_data.get("date_of_birth"),
        "nationality": player_data.get("nationality", ""),
        "primary_position": player_data.get("primary_position", ""),
    }

    if not getattr(player, "first_name", "") and first_name:
        candidate_values["first_name"] = first_name
    if not getattr(player, "last_name", "") and last_name:
        candidate_values["last_name"] = last_name

    changed = []
    for field_name, value in candidate_values.items():
        if field_name not in fields or value in (None, ""):
            continue
        if getattr(player, field_name) != value:
            setattr(player, field_name, value)
            changed.append(field_name)

    if changed:
        player.save(update_fields=changed)
        return True
    return False


# Resolve an existing player from provider data or create a new one
def resolve_or_create_player_from_provider(player_data, provider):
    identity = PlayerExternalIdentity.objects.select_related("player").filter(
        provider=provider,
        external_id=str(player_data["external_id"]),
    ).first()

    if identity:
        updated = apply_player_updates(identity.player, player_data)
        return identity.player, False, updated

    matched = find_existing_player_match(player_data)
    if matched:
        updated = apply_player_updates(matched, player_data)
        return matched, False, updated

    player = Player.objects.create(**build_player_create_values(player_data))
    return player, True, False


# ---------------------------------------------------------------------------
# Player external identity upsert
# ---------------------------------------------------------------------------

# Create or update a player external identity and keep only one primary record
def upsert_player_external_identity(player, player_data, provider):
    external_id = str(player_data["external_id"])
    now = timezone.now()

    identity = PlayerExternalIdentity.objects.filter(
        provider=provider,
        external_id=external_id,
    ).first()

    created = False
    updated = False

    if identity and identity.player_id != player.id:
        raise ValueError(
            f"{provider} player {external_id} is already linked to player {identity.player_id}."
        )

    if not identity:
        identity = PlayerExternalIdentity(player=player, provider=provider, external_id=external_id)
        created = True

    values = {
        "provider_display_name": player_data.get("display_name", ""),
        "provider_position": player_data.get("raw_provider_position", ""),
        "external_team_id": str(player_data.get("external_team_id", "") or ""),
        "is_primary": True,
        "last_synced_at": now,
        "metadata": player_data.get("metadata", {}) or {},
    }

    changed = [k for k, v in values.items() if getattr(identity, k) != v]
    for k in changed:
        setattr(identity, k, values[k])

    if created:
        identity.save()
    elif changed:
        identity.save(update_fields=changed)
        updated = True

    # Demote any other primary identities for this player+provider
    PlayerExternalIdentity.objects.filter(
        player=player,
        provider=provider,
        is_primary=True,
    ).exclude(pk=identity.pk).update(is_primary=False)

    return identity, created, updated


# ---------------------------------------------------------------------------
# Club player roster upsert
# ---------------------------------------------------------------------------

# Ensure a club player record exists and is up to date
def ensure_club_player_for_player(club, player, player_data, triggered_by=None):
    fields = model_field_names(ClubPlayer)

    if "player" not in fields:
        raise ValueError("ClubPlayer.player is required for provider sync.")

    club_player = ClubPlayer.objects.filter(club=club, player=player).order_by("id").first()

    created = False
    updated = False

    if not club_player:
        club_player = ClubPlayer(club=club, player=player)
        created = True

    first_name, last_name = resolved_player_names(player_data)

    candidate_values = {
        "first_name": first_name,
        "last_name": last_name,
        "display_name": player_data.get("display_name", "")[:50],
        "primary_position": player_data.get("primary_position", "") or getattr(player, "primary_position", ""),
        "date_of_birth": getattr(player, "date_of_birth", None),
        "height_cm": getattr(player, "height_cm", None),
        "squad_number": player_data.get("squad_number"),
        "is_active": True,
    }

    changed = []
    for field_name, value in candidate_values.items():
        if field_name not in fields or value is None:
            continue
        if getattr(club_player, field_name, None) != value:
            setattr(club_player, field_name, value)
            changed.append(field_name)

    if created and "created_by" in fields and getattr(club_player, "created_by_id", None) is None:
        creator = triggered_by or getattr(club, "creator", None)
        if creator is not None:
            club_player.created_by = creator
            changed.append("created_by")

    if created:
        club_player.save()
        return club_player, True, False

    if changed:
        club_player.save(update_fields=changed)
        updated = True

    return club_player, False, updated


# ---------------------------------------------------------------------------
# Canonical player resolution for directory entries
# ---------------------------------------------------------------------------

# Resolve a canonical player from an external identity or fallback identity fields
def resolve_canonical_player_by_external_id(provider, external_player_id, fallback_data=None):
    if not external_player_id:
        return None

    identity = PlayerExternalIdentity.objects.select_related("player").filter(
        provider=provider,
        external_id=str(external_player_id),
    ).first()

    if identity:
        return identity.player

    if not fallback_data:
        return None

    first_name = str(
        fallback_data.get("first_name")
        or fallback_data.get("metadata", {}).get("player_first_name")
        or ""
    ).strip()
    last_name = str(
        fallback_data.get("last_name")
        or fallback_data.get("metadata", {}).get("player_last_name")
        or ""
    ).strip()
    dob = fallback_data.get("date_of_birth")

    if not dob:
        dob_text = str(fallback_data.get("metadata", {}).get("player_date_of_birth") or "").strip()
        if dob_text:
            try:
                dob = date.fromisoformat(dob_text[:10])
            except ValueError:
                dob = None

    if first_name and last_name and dob:
        return Player.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=dob,
        ).first()

    return None


# Ensure an external identity exists for a player coming from directory data
def _ensure_player_external_identity_for_directory_player(player, player_data, provider):
    external_player_id = str(player_data.get("external_player_id") or "").strip()
    if not external_player_id:
        return

    payload = {
        "external_id": external_player_id,
        "display_name": str(player_data.get("player_name") or "").strip(),
        "raw_provider_position": str(player_data.get("raw_position") or "").strip(),
        "external_team_id": str(player_data.get("team_external_id") or "").strip(),
        "metadata": {
            "source": "livefootball_directory",
            "season_label": str(
                player_data.get("season_label")
                or player_data.get("metadata", {}).get("season_label")
                or ""
            ).strip(),
        },
    }

    upsert_player_external_identity(player=player, player_data=payload, provider=provider)


# Resolve the canonical player for a directory entry if one already exists
def resolve_canonical_player_for_directory_data(player_data, provider):
    external_player_id = str(player_data.get("external_player_id") or "")
    if external_player_id:
        player = resolve_canonical_player_by_external_id(
            provider=provider,
            external_player_id=external_player_id,
            fallback_data=player_data,
        )
        if player:
            return player

    match_data = {
        "first_name": player_data.get("first_name", ""),
        "last_name": player_data.get("last_name", ""),
        "date_of_birth": player_data.get("date_of_birth"),
    }
    return find_existing_player_match(match_data)


# Resolve or create a canonical player for a directory entry
def resolve_or_create_canonical_player_for_directory_data(player_data, provider):
    player = resolve_canonical_player_for_directory_data(player_data=player_data, provider=provider)

    if player is None:
        create_data = {
            "first_name": player_data.get("first_name", ""),
            "last_name": player_data.get("last_name", ""),
            "display_name": player_data.get("player_name", ""),
            "date_of_birth": player_data.get("date_of_birth"),
            "nationality": "",
            "primary_position": "",
        }
        player = Player.objects.create(**build_player_create_values(create_data))

    _ensure_player_external_identity_for_directory_player(
        player=player, player_data=player_data, provider=provider
    )

    return player