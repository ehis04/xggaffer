from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from predictions.models import ScrapedMatch, ScrapeLog
from predictions.scrapers.understat import UnderstatScraper
from predictions.utils.data_validation import DataValidator
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrape match data from Understat'
    
    def add_arguments(self, parser):

        parser.add_argument(
            '--league',
            type=str,
            help='League code (e.g., EPL, La_Liga, Serie_A)',
        )
        parser.add_argument(
            '--season',
            type=str,
            help='Season year (e.g., 2024)',
        )

        parser.add_argument(
            '--all-leagues',
            action='store_true',
            help='Scrape all major leagues for current season',
        )
        parser.add_argument(
            '--backfill',
            action='store_true',
            help='Backfill last 3 seasons for all leagues',
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test scraping without saving to database',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-scrape even if data already exists',
        )
    
    def handle(self, *args, **options):
        if not any([options['league'], options['all_leagues'], options['backfill']]):
            raise CommandError('Must specify --league, --all-leagues, or --backfill')
        
        if options['league'] and not options['season']:
            raise CommandError('--league requires --season')

        scraper = UnderstatScraper()

        if options['all_leagues']:
            targets = self._get_all_leagues_current_season()
        elif options['backfill']:
            targets = self._get_backfill_targets()
        else:
            targets = [(options['league'], options['season'])]

        self.stdout.write(self.style.SUCCESS(f'Starting scrape for {len(targets)} league/season combinations'))
        
        total_created = 0
        total_updated = 0
        total_failed = 0
        
        for league, season in targets:
            self.stdout.write(f'\n📊 Scraping {league} {season}...')
            
            created, updated, failed = self._scrape_league_season(
                scraper, 
                league, 
                season,
                dry_run=options['dry_run'],
                force=options['force']
            )
            
            total_created += created
            total_updated += updated
            total_failed += failed
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {league} {season}: {created} created, {updated} updated, {failed} failed'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Complete! Total: {total_created} created, {total_updated} updated, {total_failed} failed'
            )
        )
    
    def _scrape_league_season(self, scraper, league, season, dry_run=False, force=False):
        scrape_log = ScrapeLog.objects.create(
            scraper_name='understat',
            target=f'{league} {season}',
            status='running',
            metadata={'league': league, 'season': season, 'dry_run': dry_run}
        )
        
        try:
            matches = scraper.scrape_league_season(league, season)
            scrape_log.matches_found = len(matches)
            scrape_log.save()
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'DRY RUN: Would save {len(matches)} matches'))
                scrape_log.status = 'success'
                scrape_log.completed_at = timezone.now()
                scrape_log.save()
                return 0, 0, 0

            created_count = 0
            updated_count = 0
            failed_count = 0
            
            for match_data in matches:
                try:
                    created, updated = self._save_match(match_data, force)
                    if created:
                        created_count += 1
                    elif updated:
                        updated_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to save match {match_data.get('external_id')}: {e}")
            
            scrape_log.matches_created = created_count
            scrape_log.matches_updated = updated_count
            scrape_log.matches_failed = failed_count
            scrape_log.status = 'success' if failed_count == 0 else 'partial'
            scrape_log.completed_at = timezone.now()
            scrape_log.duration_seconds = (scrape_log.completed_at - scrape_log.started_at).seconds
            scrape_log.save()
            
            return created_count, updated_count, failed_count
            
        except Exception as e:
            scrape_log.status = 'failed'
            scrape_log.error_message = str(e)
            scrape_log.completed_at = timezone.now()
            scrape_log.save()
            
            logger.exception(f"Scraping failed for {league} {season}")
            raise CommandError(f'Scraping failed: {e}')
    
    @transaction.atomic
    def _save_match(self, match_data, force=False):
        is_valid, errors = DataValidator.validate_match_dict(match_data)
        if not is_valid:
            raise ValueError(f"Invalid match data: {errors}")
        
        external_id = match_data['external_id']
        
        if force:
            match, created = ScrapedMatch.objects.update_or_create(
                external_id=external_id,
                defaults=match_data
            )
            return created, not created
        else:
            match, created = ScrapedMatch.objects.get_or_create(
                external_id=external_id,
                defaults=match_data
            )
            return created, False
    
    def _get_all_leagues_current_season(self):
        current_year = timezone.now().year
        return [
            ('EPL', str(current_year)),         
            ('La_Liga', str(current_year)),    
            ('Serie_A', str(current_year)),     
            ('Bundesliga', str(current_year)), 
            ('Ligue_1', str(current_year)),     
        ]
    
    def _get_backfill_targets(self):

        current_year = timezone.now().year
        leagues = ['EPL', 'La_Liga', 'Serie_A', 'Bundesliga', 'Ligue_1']
        seasons = [current_year - 2, current_year - 1, current_year]
        
        return [(league, str(season)) for league in leagues for season in seasons]