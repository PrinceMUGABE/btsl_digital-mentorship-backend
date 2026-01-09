# mentorshipApp/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from mentorshipApp.utils import send_all_upcoming_session_reminders

class Command(BaseCommand):
    help = 'Send reminders for upcoming sessions'
    
    def handle(self, *args, **kwargs):
        self.stdout.write("Starting to send session reminders...")
        send_all_upcoming_session_reminders()
        self.stdout.write(self.style.SUCCESS("Session reminders sent successfully"))