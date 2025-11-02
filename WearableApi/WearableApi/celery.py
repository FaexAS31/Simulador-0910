import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WearableApi.settings')
app = Celery('WearableApi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configuración de Celery Beat - Tareas Periódicas
app.conf.beat_schedule = {
    'simulate-wearable-data-every-minute': {
        'task': 'api.tasks.simulate_wearable_cycle',
        'schedule': 60.0,  # Cada 60 segundos (1 minuto)
        'options': {
            'expires': 50.0,  # Expira si no se ejecuta en 50 segundos
        }
    },
}

app.conf.timezone = 'UTC'