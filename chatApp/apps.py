# mentoshipApp/apps.py
from django.apps import AppConfig


class ChatappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatApp'
    verbose_name = 'Chat Application'

    def ready(self):
        import chatApp.signals