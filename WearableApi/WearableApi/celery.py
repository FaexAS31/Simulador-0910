# Updated WearableApi/WearableApi/celery.py
# Adds periodic tasks for ventana calculations

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
app = Celery('WearableApi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule
app.conf.beat_schedule = {
    # Original simulation task (if you want to keep it)
   #     'simulate-wearable-data-every-minute': {
   #    'task': 'api.tasks.simulate_wearable_cycle',
   #     'schedule': 60.0,  # Every 60 seconds
   #     'options': {
   #         'expires': 50.0,
   #     }
   # },
    
    # NEW: Calculate statistics for ventanas every 5 minutes
    'calculate-ventana-statistics': {
        'task': 'api.tasks.periodic_ventana_calculation',
        'schedule': 300.0,  # Every 5 minutes (300 seconds)
        'options': {
            'expires': 250.0,
        }
    },
    
    # Optional: Daily cleanup of old ventanas without data
    'cleanup-empty-ventanas': {
        'task': 'api.tasks.cleanup_empty_ventanas',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}

app.conf.timezone = 'America/Tijuana'  # Match your settings.py timezone

# Task result expiration
app.conf.result_expires = 3600  # Results expire after 1 hour

# Task time limit
app.conf.task_time_limit = 300  # 5 minutes max per task

# Task soft time limit (sends warning)
app.conf.task_soft_time_limit = 240  # 4 minutes warning

# Enable task events for monitoring
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# Concurrency settings
app.conf.worker_prefetch_multiplier = 4
app.conf.worker_max_tasks_per_child = 1000

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'
