import os

from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.open_page.settings')

app = Celery('open_page')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
