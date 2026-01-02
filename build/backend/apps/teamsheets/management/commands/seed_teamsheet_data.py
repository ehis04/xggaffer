from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.clubs.models import Club, ClubMembership, PlayerProfile
from apps.teamsheets.models import Teamsheet, TeamsheetPlayer
from apps.teamsheets.formations import get_formation_template


User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with sample club, players, and teamsheet data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...\n')

        user, created = User.objects.get_or_create(
            email='coach@example.com',
            defaults={
                'first_name': 'Coach',
                'is_staff': True,
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: coach@example.com / password123'))
        else:
            self.stdout.write(f'User "coach@example.com" already exists')

        club, created = Club.objects.get_or_create(
            name='Dublin FC',
            defaults={
                'description': 'Sample football club for testing',
                'creator': user,
                'visibility': Club.Visibility.PUBLIC,
                'city': 'Dublin',
                'country': 'IE',
                'stadium': 'iFoot Arena',
                'division': 'Premier Division',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created club: {club.name}'))
        else:
            self.stdout.write(f'Club "{club.name}" already exists')

        membership, created = ClubMembership.objects.get_or_create(
            user=user,
            club=club,
            defaults={
                'role': ClubMembership.Role.OWNER,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created membership: {user.email} -> {club.name}'))

        players_data = [
            {'first_name': 'Gavin', 'last_name': 'Bazunu', 'squad_number': 1, 'position': 'GK'},
            {'first_name': 'Seamus', 'last_name': 'Coleman', 'squad_number': 2, 'position': 'DEF'},
            {'first_name': 'John', 'last_name': 'Egan', 'squad_number': 5, 'position': 'DEF'},
            {'first_name': 'Nathan', 'last_name': 'Collins', 'squad_number': 4, 'position': 'DEF'},
            {'first_name': 'Enda', 'last_name': 'Stevens', 'squad_number': 3, 'position': 'DEF'},
            {'first_name': 'Josh', 'last_name': 'Cullen', 'squad_number': 8, 'position': 'MID'},
            {'first_name': 'Jason', 'last_name': 'Knight', 'squad_number': 6, 'position': 'MID'},
            {'first_name': 'Matt', 'last_name': 'Doherty', 'squad_number': 7, 'position': 'MID'},
            {'first_name': 'Chiedozie', 'last_name': 'Ogbene', 'squad_number': 11, 'position': 'FWD'},
            {'first_name': 'Adam', 'last_name': 'Idah', 'squad_number': 9, 'position': 'FWD'},
            {'first_name': 'Evan', 'last_name': 'Ferguson', 'squad_number': 10, 'position': 'FWD'},
            {'first_name': 'Caoimhin', 'last_name': 'Kelleher', 'squad_number': 12, 'position': 'GK'},
            {'first_name': 'Dara', 'last_name': "O'Shea", 'squad_number': 14, 'position': 'DEF'},
            {'first_name': 'Jayson', 'last_name': 'Molumby', 'squad_number': 16, 'position': 'MID'},
            {'first_name': 'Troy', 'last_name': 'Parrott', 'squad_number': 20, 'position': 'FWD'},
        ]

        player_profiles = []
        for p_data in players_data:
            player, created = PlayerProfile.objects.get_or_create(
                club=club,
                first_name=p_data['first_name'],
                last_name=p_data['last_name'],
                defaults={
                    'squad_number': p_data['squad_number'],
                    'position': p_data['position'],
                    'is_active': True,
                    'created_by': user,
                }
            )
            player_profiles.append(player)
            if created:
                self.stdout.write(f'  Created player: {player.full_name}')

        self.stdout.write(self.style.SUCCESS(f'Created {len(players_data)} players'))

        teamsheet, created = Teamsheet.objects.get_or_create(
            club=club,
            title='vs England - Home',
            defaults={
                'formation': '433',
                'created_by': user,
                'opponent': 'England',
                'match_date': '2025-02-01',
                'notes': 'Big match! High pressing, quick transitions.',
                'is_template': False,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created teamsheet: {teamsheet.title}'))
            
            template = get_formation_template('433')
            
            position_to_player = {
                'GK': 0,
                'RB': 1,
                'CB': 2,
                'LB': 4,
                'CM': 5,
                'CDM': 6,
                'RW': 8,
                'ST': 9,
                'LW': 10,
            }
            
            cb_count = 0
            cm_count = 0
            
            for slot_data in template:
                pos = slot_data['position']
                
                if pos == 'CB':
                    player_idx = 2 if cb_count == 0 else 3
                    cb_count += 1
                elif pos == 'CM' and pos != 'CDM':
                    player_idx = 5 if cm_count == 0 else 7
                    cm_count += 1
                else:
                    player_idx = position_to_player.get(pos, 0)
                
                player_profile = player_profiles[player_idx] if player_idx < len(player_profiles) else None
                
                TeamsheetPlayer.objects.create(
                    teamsheet=teamsheet,
                    player_profile=player_profile,
                    slot_number=slot_data['slot'],
                    position_label=slot_data['position'],
                    position_x=slot_data['x'],
                    position_y=slot_data['y'],
                    is_substitute=False,
                )
            
            for i, sub_idx in enumerate([11, 12, 13, 14], start=12):
                if sub_idx < len(player_profiles):
                    TeamsheetPlayer.objects.create(
                        teamsheet=teamsheet,
                        player_profile=player_profiles[sub_idx],
                        slot_number=i,
                        position_label='GK' if sub_idx == 11 else 'DEF',
                        position_x=50,
                        position_y=50,
                        is_substitute=True,
                    )
            
            self.stdout.write(self.style.SUCCESS(f'Added {teamsheet.players.count()} players to teamsheet'))
        else:
            self.stdout.write(f'Teamsheet "{teamsheet.title}" already exists')

        template_sheet, created = Teamsheet.objects.get_or_create(
            club=club,
            title='Default 4-4-2',
            is_template=True,
            defaults={
                'formation': '442',
                'created_by': user,
                'notes': 'Standard 4-4-2 template',
            }
        )
        
        if created:
            template_sheet.initialize_from_template()
            self.stdout.write(self.style.SUCCESS(f'Created template: {template_sheet.title}'))

        self.stdout.write(self.style.SUCCESS('\n✓ Sample data created successfully!'))
        self.stdout.write(f'\nLogin credentials:')
        self.stdout.write(f'  Email: coach@example.com')
        self.stdout.write(f'  Password: password123')
        self.stdout.write(f'\nAPI endpoints:')
        self.stdout.write(f'  GET /api/clubs/')
        self.stdout.write(f'  GET /api/clubs/{club.id}/teamsheets/')
        self.stdout.write(f'  GET /api/clubs/{club.id}/teamsheets/{teamsheet.id}/')