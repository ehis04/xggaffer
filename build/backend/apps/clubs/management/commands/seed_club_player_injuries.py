from __future__ import annotations

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.clubs.models import Club, ClubPlayer, ClubPlayerInjury

# Realistic distribution: per squad of ~30 players
# ~8% injured (IN), ~10% in doubt (DO), ~2% suspended (SU), rest available (no record)
INJURY_RATE = 0.08
DOUBT_RATE = 0.10
SUSPENSION_RATE = 0.02

INJURY_TYPES = [
    (ClubPlayerInjury.InjuryType.MUSCLE, 0.35),
    (ClubPlayerInjury.InjuryType.LIGAMENT, 0.20),
    (ClubPlayerInjury.InjuryType.TENDON, 0.15),
    (ClubPlayerInjury.InjuryType.ILLNESS, 0.10),
    (ClubPlayerInjury.InjuryType.BONE, 0.08),
    (ClubPlayerInjury.InjuryType.CARTILAGE, 0.06),
    (ClubPlayerInjury.InjuryType.HEAD, 0.04),
    (ClubPlayerInjury.InjuryType.OTHER, 0.02),
]

SEVERITY_BY_STATUS = {
    ClubPlayerInjury.AvailabilityStatus.INJURED: [
        (ClubPlayerInjury.Severity.MINOR, 0.3),
        (ClubPlayerInjury.Severity.MODERATE, 0.5),
        (ClubPlayerInjury.Severity.SEVERE, 0.2),
    ],
    ClubPlayerInjury.AvailabilityStatus.IN_DOUBT: [
        (ClubPlayerInjury.Severity.MINOR, 0.7),
        (ClubPlayerInjury.Severity.MODERATE, 0.3),
    ],
    ClubPlayerInjury.AvailabilityStatus.SUSPENDED: [
        (ClubPlayerInjury.Severity.MINOR, 1.0),
    ],
}

RETURN_DAYS_BY_SEVERITY = {
    ClubPlayerInjury.Severity.MINOR: (3, 14),
    ClubPlayerInjury.Severity.MODERATE: (14, 42),
    ClubPlayerInjury.Severity.SEVERE: (42, 120),
}


def _weighted_choice(choices):
    """Choose a value from a list of (value, weight) pairs."""
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    cumulative = 0
    for value, weight in choices:
        cumulative += weight
        if r <= cumulative:
            return value
    return choices[-1][0]


def _random_injury_date(return_range_days: tuple[int, int]) -> tuple[date, date | None]:
    """Generate an injured_at date and estimated return date."""
    today = timezone.now().date()
    max_days_ago, min_days_ago = return_range_days
    # Player was injured somewhere within their recovery window
    days_into_recovery = random.randint(1, max(1, min_days_ago // 2))
    injured_at = today - timedelta(days=days_into_recovery)
    remaining = random.randint(return_range_days[0] - days_into_recovery,
                               return_range_days[1] - days_into_recovery)
    remaining = max(1, remaining)
    estimated_return = today + timedelta(days=remaining)
    return injured_at, estimated_return


class Command(BaseCommand):
    help = (
        "Seed realistic injury and availability records for club squad players. "
        "Generates ~8%% injured, ~10%% in doubt, ~2%% suspended per squad."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--club-id",
            action="append",
            type=int,
            dest="club_ids",
            help="Target one or more club IDs (repeat flag for multiple). Defaults to all user clubs.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            dest="seed",
            help="Random seed for reproducible output.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Persist changes. Without this flag, runs in dry-run mode.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Replace existing injury records. Without this flag, players with existing records are skipped.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]
        club_ids = options.get("club_ids") or []
        seed = options.get("seed")
        overwrite = options.get("overwrite", False)

        if seed is not None:
            random.seed(seed)

        if club_ids:
            queryset = Club.objects.filter(id__in=club_ids).order_by("id")
        else:
            queryset = Club.objects.exclude(
                club_type=Club.ClubType.SYSTEM_PROFESSIONAL
            ).order_by("id")

        clubs = list(queryset)
        if not clubs:
            self.stdout.write(self.style.WARNING("No target clubs found."))
            return

        mode = "COMMIT" if commit else "DRY-RUN"
        self.stdout.write(f"Seeding club player injuries in {mode} mode")

        total_created = 0
        total_skipped = 0

        for club in clubs:
            players = list(club.club_players.filter(is_active=True).order_by("id"))
            n = len(players)
            if n == 0:
                self.stdout.write(f"[{club.id}] {club.name}: no active players, skipping")
                continue

            n_injured = max(0, round(n * INJURY_RATE))
            n_doubt = max(0, round(n * DOUBT_RATE))
            n_suspended = max(0, round(n * SUSPENSION_RATE))

            random.shuffle(players)
            injured_players = players[:n_injured]
            doubt_players = players[n_injured:n_injured + n_doubt]
            suspended_players = players[n_injured + n_doubt:n_injured + n_doubt + n_suspended]

            created = 0
            skipped = 0
            records = []

            for player, av_status in (
                [(p, ClubPlayerInjury.AvailabilityStatus.INJURED) for p in injured_players]
                + [(p, ClubPlayerInjury.AvailabilityStatus.IN_DOUBT) for p in doubt_players]
                + [(p, ClubPlayerInjury.AvailabilityStatus.SUSPENDED) for p in suspended_players]
            ):
                existing = ClubPlayerInjury.objects.filter(
                    club_player=player, is_current=True
                ).exists()

                if existing:
                    if not overwrite:
                        skipped += 1
                        continue
                    if commit:
                        ClubPlayerInjury.objects.filter(
                            club_player=player, is_current=True
                        ).update(is_current=False)

                if av_status == ClubPlayerInjury.AvailabilityStatus.SUSPENDED:
                    injury_type = ClubPlayerInjury.InjuryType.SUSPENSION
                else:
                    injury_type = _weighted_choice(INJURY_TYPES)

                severity = _weighted_choice(SEVERITY_BY_STATUS[av_status])
                return_range = RETURN_DAYS_BY_SEVERITY[severity]
                injured_at, estimated_return = _random_injury_date(return_range)

                records.append(ClubPlayerInjury(
                    club_player=player,
                    injury_type=injury_type,
                    severity=severity,
                    availability_status=av_status,
                    injured_at=injured_at,
                    estimated_return=estimated_return,
                    notes="Seeded baseline record.",
                    is_current=True,
                    recorded_by=None,
                ))
                created += 1

            if commit and records:
                with transaction.atomic():
                    ClubPlayerInjury.objects.bulk_create(records)

            total_created += created
            total_skipped += skipped
            self.stdout.write(
                f"[{club.id}] {club.name}: {n} players → "
                f"injured={n_injured}, doubt={n_doubt}, suspended={n_suspended} "
                f"(created={created}, skipped={skipped})"
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done: total_created={total_created}, total_skipped={total_skipped}"
        ))
        if not commit:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --commit to persist."))
