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

# Confirms Celery is receiving and executing tasks
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")