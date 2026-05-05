from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.clubs.models import Club, ClubMembership, ClubPlayer

User = get_user_model()

PREBUILT_CLUBS = [
    {
        'name': 'Shelbourne FC',
        'description': 'League of Ireland Premier Division club based in Dublin.',
        'city': 'Dublin',
        'country': 'IE',
        'stadium': 'Tolka Park',
        'division': 'League of Ireland Premier Division',
        'players': [
            {'first_name': 'Leon', 'last_name': 'Pohls', 'squad_number': 1, 'position': 'GK'},
            {'first_name': 'John', 'last_name': 'Ross Wilson', 'squad_number': 2, 'position': 'RB'},
            {'first_name': 'Paddy', 'last_name': 'Barrett', 'squad_number': 4, 'position': 'CB'},
            {'first_name': 'Luke', 'last_name': 'Byrne', 'squad_number': 5, 'position': 'CB'},
            {'first_name': 'Kameron', 'last_name': 'Ledwidge', 'squad_number': 3, 'position': 'LB'},
            {'first_name': 'Matty', 'last_name': 'Smith', 'squad_number': 8, 'position': 'CM'},
            {'first_name': 'Aidan', 'last_name': 'Keena', 'squad_number': 9, 'position': 'CM'},
            {'first_name': 'Sean', 'last_name': 'Boyd', 'squad_number': 11, 'position': 'CM'},
            {'first_name': 'Mark', 'last_name': 'Coyle', 'squad_number': 7, 'position': 'RM'},
            {'first_name': 'Sean', 'last_name': 'Gannon', 'squad_number': 6, 'position': 'LM'},
            {'first_name': 'Liam', 'last_name': 'Burt', 'squad_number': 10, 'position': 'ST'},
            {'first_name': 'Conor', 'last_name': 'Kearns', 'squad_number': 12, 'position': 'GK'},
            {'first_name': 'Shane', 'last_name': 'Farrell', 'squad_number': 14, 'position': 'LW'},
            {'first_name': 'Gavin', 'last_name': 'Molloy', 'squad_number': 15, 'position': 'RW'},
        ],
    },
    {
        'name': 'Shamrock Rovers',
        'description': 'Most successful League of Ireland club, based in Tallaght, Dublin.',
        'city': 'Dublin',
        'country': 'IE',
        'stadium': 'Tallaght Stadium',
        'division': 'League of Ireland Premier Division',
        'players': [
            {'first_name': 'Alan', 'last_name': 'Mannus', 'squad_number': 1, 'position': 'GK'},
            {'first_name': 'Sean', 'last_name': 'Hoare', 'squad_number': 4, 'position': 'RB'},
            {'first_name': 'Roberto', 'last_name': 'Lopes', 'squad_number': 5, 'position': 'CB'},
            {'first_name': 'Sean', 'last_name': 'Kavanagh', 'squad_number': 3, 'position': 'CB'},
            {'first_name': 'Ronan', 'last_name': 'Finn', 'squad_number': 7, 'position': 'LB'},
            {'first_name': 'Gary', 'last_name': "O'Neill", 'squad_number': 8, 'position': 'CM'},
            {'first_name': 'Jack', 'last_name': 'Byrne', 'squad_number': 10, 'position': 'CM'},
            {'first_name': 'Rory', 'last_name': 'Gaffney', 'squad_number': 9, 'position': 'CM'},
            {'first_name': 'Graham', 'last_name': 'Burke', 'squad_number': 11, 'position': 'RM'},
            {'first_name': 'Neil', 'last_name': 'Farrugia', 'squad_number': 17, 'position': 'LM'},
            {'first_name': 'Lee', 'last_name': 'Grace', 'squad_number': 6, 'position': 'ST'},
            {'first_name': 'Dylan', 'last_name': 'Watts', 'squad_number': 14, 'position': 'CM'},
            {'first_name': 'Simon', 'last_name': 'Power', 'squad_number': 20, 'position': 'RW'},
        ],
    },
    {
        'name': 'Dublin Demo FC',
        'description': 'A demonstration club showing how iFoot works. Clone this club to get started.',
        'city': 'Dublin',
        'country': 'IE',
        'stadium': 'iFoot Arena',
        'division': 'Demo League',
        'players': [
            {'first_name': 'Gavin', 'last_name': 'Bazunu', 'squad_number': 1, 'position': 'GK'},
            {'first_name': 'Seamus', 'last_name': 'Coleman', 'squad_number': 2, 'position': 'RB'},
            {'first_name': 'John', 'last_name': 'Egan', 'squad_number': 5, 'position': 'CB'},
            {'first_name': 'Nathan', 'last_name': 'Collins', 'squad_number': 4, 'position': 'CB'},
            {'first_name': 'Enda', 'last_name': 'Stevens', 'squad_number': 3, 'position': 'LB'},
            {'first_name': 'Josh', 'last_name': 'Cullen', 'squad_number': 8, 'position': 'CM'},
            {'first_name': 'Jason', 'last_name': 'Knight', 'squad_number': 6, 'position': 'CM'},
            {'first_name': 'Matt', 'last_name': 'Doherty', 'squad_number': 7, 'position': 'CM'},
            {'first_name': 'Chiedozie', 'last_name': 'Ogbene', 'squad_number': 11, 'position': 'RM'},
            {'first_name': 'Adam', 'last_name': 'Idah', 'squad_number': 9, 'position': 'LM'},
            {'first_name': 'Evan', 'last_name': 'Ferguson', 'squad_number': 10, 'position': 'ST'},
            {'first_name': 'Caoimhin', 'last_name': 'Kelleher', 'squad_number': 12, 'position': 'GK'},
            {'first_name': 'Dara', 'last_name': "O'Shea", 'squad_number': 14, 'position': 'RB'},
            {'first_name': 'Jayson', 'last_name': 'Molumby', 'squad_number': 16, 'position': 'CM'},
            {'first_name': 'Troy', 'last_name': 'Parrott', 'squad_number': 20, 'position': 'ST'},
        ],
    },
]


class Command(BaseCommand):
    help = 'Seeds the database with pre-built clubs that users can browse and duplicate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing pre-built clubs before re-creating them',
        )

    def handle(self, *args, **options):
        system_user = self._get_or_create_system_user()

        if options['reset']:
            deleted_count, _ = Club.objects.filter(creator=system_user).delete()
            self.stdout.write(f'Deleted {deleted_count} existing pre-built club records')

        for club_data in PREBUILT_CLUBS:
            self._create_club(system_user, club_data)

        total = Club.objects.filter(creator=system_user).count()
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. {total} pre-built clubs available.'
        ))

    def _get_or_create_system_user(self):
        user, created = User.objects.get_or_create(
            email='system@ifoot.app',
            defaults={
                'first_name': 'iFoot',
                'last_name': 'System',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS('Created system user: system@ifoot.app'))
        return user

    def _create_club(self, system_user, club_data):
        players_data = club_data.pop('players', [])

        existing = Club.objects.filter(
            name=club_data['name'],
            creator=system_user
        ).first()

        if existing:
            self.stdout.write(f'  Club "{existing.name}" already exists, skipping')
            return

        with transaction.atomic():
            club = Club.objects.create(
                creator=system_user,
                visibility=Club.Visibility.PUBLIC,
                **club_data,
            )

            ClubMembership.objects.create(
                user=system_user,
                club=club,
                role=ClubMembership.Role.OWNER,
                is_active=True,
            )

            for p_data in players_data:
                # Transform 'position' to 'primary_position' for the new model structure
                player_kwargs = p_data.copy()
                if 'position' in player_kwargs:
                    player_kwargs['primary_position'] = player_kwargs.pop('position')

                ClubPlayer.objects.create(
                    club=club,
                    is_active=True,
                    created_by=system_user,
                    **player_kwargs,
                )

            self.stdout.write(self.style.SUCCESS(
                f'  Created "{club.name}" with {len(players_data)} players'
            ))