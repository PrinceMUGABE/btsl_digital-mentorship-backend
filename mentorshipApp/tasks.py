# mentorshipApp/tasks.py
from celery import shared_task
from .utils import send_all_upcoming_session_reminders
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_session_reminders():
    """Celery task to send session reminders"""
    try:
        logger.info("Starting session reminder task")
        send_all_upcoming_session_reminders()
        logger.info("Session reminder task completed")
    except Exception as e:
        logger.error(f"Error in session reminder task: {str(e)}")