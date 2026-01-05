from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from django.core.mail import mail_admins
from .models import ScrapeLog
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,         
    max_retries=3,     
    default_retry_delay=300  
)
def scrape_all_leagues(self):
    try:
        logger.info("Starting scheduled scrape of all leagues")
        
        call_command('scrape_understat', '--all-leagues')
        
        logger.info("Scheduled scrape completed successfully")
        
        _check_recent_scrapes_and_alert()
        
    except Exception as exc:
        logger.error(f"Scraping task failed: {exc}", exc_info=True)
        
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def scrape_specific_league(league, season):
    try:
        logger.info(f"Scraping {league} {season}")
        call_command('scrape_understat', '--league', league, '--season', season)
        logger.info(f"Successfully scraped {league} {season}")
    except Exception as e:
        logger.error(f"Failed to scrape {league} {season}: {e}", exc_info=True)
        raise


@shared_task
def backfill_historical_data():
    try:
        logger.info("Starting historical data backfill")
        call_command('scrape_understat', '--backfill')
        logger.info("Historical data backfill completed")
    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        raise


def _check_recent_scrapes_and_alert():
    recent_logs = ScrapeLog.objects.order_by('-started_at')[:3]
    
    if len(recent_logs) < 3:
        return
    
    failed_count = sum(1 for log in recent_logs if log.status == 'failed')
    
    if failed_count >= 3:
        subject = '⚠️ Multiple scraping failures detected'
        message = f"""
        The last 3 scraping attempts have failed.
        
        Latest failures:
        {chr(10).join(f"- {log.started_at}: {log.error_message}" for log in recent_logs)}
        
        Please investigate immediately.
        """
        
        mail_admins(subject, message, fail_silently=True)
        logger.critical("Multiple scraping failures - admins notified")