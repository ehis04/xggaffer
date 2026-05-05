from django.core.management.base import BaseCommand

from apps.clubs.models import Club, ClubExternalIdentity, ProClubProviderLink


class Command(BaseCommand):
    help = 'Backfill ProClubProviderLink for existing SYSTEM_PROFESSIONAL clubs.'

    def handle(self, *args, **options):
        pro_clubs = Club.objects.filter(club_type=Club.ClubType.SYSTEM_PROFESSIONAL)
        created_count = 0

        for club in pro_clubs:
            if hasattr(club, 'provider_link'):
                self.stdout.write(f'  Skip (link exists): {club.name}')
                continue

            identity = ClubExternalIdentity.objects.filter(
                club=club,
                provider='football_data',
                is_primary=True,
            ).first()

            if not identity:
                identity = ClubExternalIdentity.objects.filter(club=club).first()

            if not identity:
                self.stdout.write(self.style.WARNING(f'  No identity for: {club.name}'))
                continue

            ProClubProviderLink.objects.create(
                club=club,
                provider=identity.provider,
                provider_team_id=identity.external_id,
                last_provider_sync_at=identity.last_synced_at,
            )
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f'  Linked: {club.name}'))

        self.stdout.write(self.style.SUCCESS(f'Done. Created {created_count} links.'))