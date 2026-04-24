import os

from celery import Celery

# Django settings module set to default 
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Main Celery aoolication for backend project
app = Celery("backend")

# Settings w/ CELERY preix loaded in
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto discover tasks in installed apps
app.autodiscover_tasks()

app.conf.task_routes = {
    'apps.sync_pipeline.tasks.refresh_football_data_metadata_task':       {'queue': 'queue_football_data'},
    'apps.sync_pipeline.tasks.refresh_football_data_fixtures_task':       {'queue': 'queue_football_data'},
    'apps.sync_pipeline.tasks.refresh_football_data_scorers_squads_task': {'queue': 'queue_football_data'},
    'apps.livefootball.tasks.refresh_livefootball_from_football_data':    {'queue': 'queue_football_data'},
    'apps.sync_pipeline.tasks.refresh_understat_cycle_task':              {'queue': 'queue_understat'},
    'apps.playerdata.tasks.refresh_understat_all_leagues_task':           {'queue': 'queue_understat'},
    'apps.sync_pipeline.tasks.refresh_sofascore_cycle_task':              {'queue': 'queue_sofascore'},
    'apps.sync_pipeline.tasks.refresh_whoscored_cycle_task':              {'queue': 'queue_whoscored'},
    'apps.sync_pipeline.tasks.refresh_transfermarkt_cycle_task':          {'queue': 'queue_transfermarkt'},
    'apps.sync_pipeline.tasks.refresh_native_stats_cycle_task':           {'queue': 'queue_native_stats'},
    'apps.sync_pipeline.tasks.aggregate_sync_health_task':                {'queue': 'queue_native_stats'},
    'apps.clubs.tasks.refresh_pro_club_squads_task':                      {'queue': 'queue_football_data'},
    'apps.clubs.tasks.rebuild_club_publication_task':                     {'queue': 'queue_publication'},
    'apps.clubs.tasks.purge_expired_trash':                               {'queue': 'queue_publication'},
    'apps.sync_pipeline.tasks.refresh_odds_snapshots_task':               {'queue': 'queue_publication'},
    'apps.livefootball.tasks.rebuild_livefootball_publication':           {'queue': 'queue_publication'},
    'apps.playerdata.tasks.rebuild_playerdata_publication_task':          {'queue': 'queue_publication'},
    'apps.predictions.tasks.rebuild_predictions_publication_task':        {'queue': 'queue_publication'},
}

# Confirms Celery is receiving and executing tasks
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

