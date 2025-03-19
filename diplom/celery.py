from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diplom.settings')

celery_app = Celery('diplom')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()
