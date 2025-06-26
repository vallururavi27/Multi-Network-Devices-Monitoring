"""
Celery configuration for network_monitor project.
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'network_monitor.settings')

app = Celery('network_monitor')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    'monitor-all-devices': {
        'task': 'monitoring.tasks.monitor_all_devices',
        'schedule': 300.0,  # Every 5 minutes
    },
    'send-alert-emails': {
        'task': 'alerts.tasks.send_pending_alerts',
        'schedule': 120.0,  # Every 2 minutes
    },
    'cleanup-old-data': {
        'task': 'monitoring.tasks.cleanup_old_data',
        'schedule': 86400.0,  # Daily
    },
    'generate-daily-report': {
        'task': 'reports.tasks.generate_daily_report',
        'schedule': 86400.0,  # Daily
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
