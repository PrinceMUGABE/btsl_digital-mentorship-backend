# your_project/celery.py
from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-session-reminders': {
        'task': 'mentorshipApp.tasks.send_session_reminders',
        'schedule': crontab(hour='*/1'),  # Run every hour
    },
}