# mentoshipApp/apps.py
from django.apps import AppConfig


class MentorshipAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mentoshipApp'
    verbose_name = 'Mentorship Application'

    def ready(self):
        import mentoshipApp.signals