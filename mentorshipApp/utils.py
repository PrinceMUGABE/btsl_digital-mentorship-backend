# mentoshipApp/utils.py
from django.utils import timezone
from datetime import timedelta
from notificationApp.models import ChatNotification
from chatApp.models import ChatRoom
from userApp.models import CustomUser
import logging

logger = logging.getLogger(__name__)

def send_session_scheduled_notification(session):
    """Send notification about scheduled session"""
    try:
        # Create notification for mentee
        ChatNotification.objects.create(
            recipient=session.mentorship.mentee,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_scheduled',
            title='New Session Scheduled',
            message=f'Session {session.program_session_number}: {session.session_template.title} scheduled for {session.scheduled_date.strftime("%Y-%m-%d %H:%M")}',
            metadata={
                'session_id': session.id,
                'mentorship_id': session.mentorship.id,
                'scheduled_date': session.scheduled_date.isoformat(),
                'program_name': session.program.name if session.program else 'Unknown Program',
                'session_title': session.session_template.title if session.session_template else 'Session'
            }
        )
        
        # Also send to mentor for confirmation
        ChatNotification.objects.create(
            recipient=session.mentorship.mentor,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_scheduled',
            title='Session Scheduled',
            message=f'You scheduled Session {session.program_session_number} with {session.mentorship.mentee.full_name} for {session.scheduled_date.strftime("%Y-%m-%d %H:%M")}',
            metadata={
                'session_id': session.id,
                'mentee_name': session.mentorship.mentee.full_name,
                'scheduled_date': session.scheduled_date.isoformat(),
                'program_name': session.program.name if session.program else 'Unknown Program'
            }
        )
        
        logger.info(f"Session scheduled notification sent for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error sending session scheduled notification: {str(e)}")


def send_session_completed_notification(session):
    """Send notification about completed session"""
    try:
        # Notification for mentee
        ChatNotification.objects.create(
            recipient=session.mentorship.mentee,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_completed',
            title='Session Completed',
            message=f'Session {session.program_session_number}: {session.session_template.title} has been marked as completed',
            metadata={
                'session_id': session.id,
                'mentorship_id': session.mentorship.id,
                'completed_by': session.completed_by.full_name if session.completed_by else 'System',
                'program_name': session.program.name if session.program else 'Unknown Program',
                'program_progress': get_program_progress_percentage(session.mentorship, session.program)
            }
        )
        
        # Notification for mentor
        ChatNotification.objects.create(
            recipient=session.mentorship.mentor,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_completed',
            title='Session Completed',
            message=f'Session {session.program_session_number} with {session.mentorship.mentee.full_name} has been marked as completed',
            metadata={
                'session_id': session.id,
                'mentee_name': session.mentorship.mentee.full_name,
                'program_progress': get_program_progress_percentage(session.mentorship, session.program),
                'total_sessions_completed': get_total_sessions_completed(session.mentorship)
            }
        )
        
        logger.info(f"Session completed notification sent for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error sending session completed notification: {str(e)}")


def send_session_cancelled_notification(session, reason):
    """Send notification about cancelled session"""
    try:
        # Determine who cancelled
        cancelled_by = session.completed_by.full_name if session.completed_by else 'System'
        
        # Notification for mentee
        ChatNotification.objects.create(
            recipient=session.mentorship.mentee,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_cancelled',
            title='Session Cancelled',
            message=f'Session {session.program_session_number}: {session.session_template.title} has been cancelled by {cancelled_by}',
            metadata={
                'session_id': session.id,
                'mentorship_id': session.mentorship.id,
                'cancelled_by': cancelled_by,
                'reason': reason,
                'original_date': session.scheduled_date.isoformat(),
                'program_name': session.program.name if session.program else 'Unknown Program'
            }
        )
        
        # Notification for mentor
        ChatNotification.objects.create(
            recipient=session.mentorship.mentor,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_cancelled',
            title='Session Cancelled',
            message=f'Session {session.program_session_number} with {session.mentorship.mentee.full_name} has been cancelled',
            metadata={
                'session_id': session.id,
                'mentee_name': session.mentorship.mentee.full_name,
                'reason': reason,
                'cancelled_by': cancelled_by
            }
        )
        
        logger.info(f"Session cancelled notification sent for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error sending session cancelled notification: {str(e)}")


def send_session_rescheduled_notification(session, old_date):
    """Send notification about rescheduled session"""
    try:
        # Calculate time difference
        time_diff = session.scheduled_date - old_date
        days_diff = time_diff.days
        hours_diff = time_diff.seconds // 3600
        
        time_change_text = ""
        if days_diff != 0:
            time_change_text = f"{abs(days_diff)} day(s) {'later' if days_diff > 0 else 'earlier'}"
        elif hours_diff != 0:
            time_change_text = f"{abs(hours_diff)} hour(s) {'later' if hours_diff > 0 else 'earlier'}"
        else:
            time_change_text = "at the same time"
        
        # Notification for mentee
        ChatNotification.objects.create(
            recipient=session.mentorship.mentee,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_rescheduled',
            title='Session Rescheduled',
            message=f'Session {session.program_session_number}: {session.session_template.title} has been rescheduled to {session.scheduled_date.strftime("%Y-%m-%d %H:%M")}',
            metadata={
                'session_id': session.id,
                'mentorship_id': session.mentorship.id,
                'old_date': old_date.isoformat(),
                'new_date': session.scheduled_date.isoformat(),
                'time_change': time_change_text,
                'program_name': session.program.name if session.program else 'Unknown Program',
                'session_title': session.session_template.title if session.session_template else 'Session'
            }
        )
        
        # Notification for mentor
        ChatNotification.objects.create(
            recipient=session.mentorship.mentor,
            chat_room=get_chat_room(session.mentorship),
            notification_type='session_rescheduled',
            title='Session Rescheduled',
            message=f'Session {session.program_session_number} with {session.mentorship.mentee.full_name} has been rescheduled',
            metadata={
                'session_id': session.id,
                'mentee_name': session.mentorship.mentee.full_name,
                'old_date': old_date.strftime("%Y-%m-%d %H:%M"),
                'new_date': session.scheduled_date.strftime("%Y-%m-%d %H:%M"),
                'time_change': time_change_text
            }
        )
        
        logger.info(f"Session rescheduled notification sent for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error sending session rescheduled notification: {str(e)}")


def send_upcoming_session_reminder(session):
    """Send reminder for upcoming session (24 hours before)"""
    try:
        # Calculate time until session
        time_until = session.scheduled_date - timezone.now()
        hours_until = time_until.total_seconds() / 3600
        
        if 23 <= hours_until <= 25:  # Send 24 hour reminder
            # Notification for mentee
            ChatNotification.objects.create(
                recipient=session.mentorship.mentee,
                chat_room=get_chat_room(session.mentorship),
                notification_type='session_reminder',
                title='Session Reminder - Tomorrow',
                message=f'Reminder: Session {session.program_session_number}: {session.session_template.title} is scheduled for tomorrow at {session.scheduled_date.strftime("%H:%M")}',
                metadata={
                    'session_id': session.id,
                    'mentorship_id': session.mentorship.id,
                    'scheduled_date': session.scheduled_date.isoformat(),
                    'session_title': session.session_template.title if session.session_template else 'Session',
                    'meeting_link': session.meeting_link or '',
                    'location': session.location or ''
                }
            )
            
            # Notification for mentor
            ChatNotification.objects.create(
                recipient=session.mentorship.mentor,
                chat_room=get_chat_room(session.mentorship),
                notification_type='session_reminder',
                title='Session Reminder - Tomorrow',
                message=f'Reminder: Session {session.program_session_number} with {session.mentorship.mentee.full_name} is scheduled for tomorrow at {session.scheduled_date.strftime("%H:%M")}',
                metadata={
                    'session_id': session.id,
                    'mentee_name': session.mentorship.mentee.full_name,
                    'scheduled_date': session.scheduled_date.isoformat(),
                    'meeting_link': session.meeting_link or '',
                    'location': session.location or ''
                }
            )
            
            logger.info(f"24-hour reminder sent for session {session.id}")
            
        elif 0.5 <= hours_until <= 1.5:  # Send 1 hour reminder
            # Notification for mentee
            ChatNotification.objects.create(
                recipient=session.mentorship.mentee,
                chat_room=get_chat_room(session.mentorship),
                notification_type='session_reminder',
                title='Session Starting Soon',
                message=f'Session {session.program_session_number}: {session.session_template.title} starts in 1 hour',
                metadata={
                    'session_id': session.id,
                    'mentorship_id': session.mentorship.id,
                    'scheduled_date': session.scheduled_date.isoformat(),
                    'meeting_link': session.meeting_link or '',
                    'location': session.location or ''
                }
            )
            
            # Notification for mentor
            ChatNotification.objects.create(
                recipient=session.mentorship.mentor,
                chat_room=get_chat_room(session.mentorship),
                notification_type='session_reminder',
                title='Session Starting Soon',
                message=f'Session {session.program_session_number} with {session.mentorship.mentee.full_name} starts in 1 hour',
                metadata={
                    'session_id': session.id,
                    'mentee_name': session.mentorship.mentee.full_name,
                    'scheduled_date': session.scheduled_date.isoformat(),
                    'meeting_link': session.meeting_link or '',
                    'location': session.location or ''
                }
            )
            
            logger.info(f"1-hour reminder sent for session {session.id}")
        
    except Exception as e:
        logger.error(f"Error sending session reminder: {str(e)}")


def send_program_completed_notification(mentorship, program):
    """Send notification when a program is completed"""
    try:
        # Get program progress
        from mentorshipApp.models import MentorshipProgramProgress
        progress = MentorshipProgramProgress.objects.filter(
            mentorship=mentorship,
            program=program
        ).first()
        
        if not progress:
            return
        
        # Notification for mentee
        ChatNotification.objects.create(
            recipient=mentorship.mentee,
            chat_room=get_chat_room(mentorship),
            notification_type='program_completed',
            title='Program Completed! 🎉',
            message=f'Congratulations! You have completed the {program.name} program',
            metadata={
                'program_id': program.id,
                'program_name': program.name,
                'mentorship_id': mentorship.id,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else timezone.now().isoformat(),
                'sessions_completed': progress.sessions_completed,
                'total_sessions': progress.total_sessions
            }
        )
        
        # Notification for mentor
        ChatNotification.objects.create(
            recipient=mentorship.mentor,
            chat_room=get_chat_room(mentorship),
            notification_type='program_completed',
            title='Program Completed',
            message=f'{mentorship.mentee.full_name} has completed the {program.name} program',
            metadata={
                'program_id': program.id,
                'program_name': program.name,
                'mentee_name': mentorship.mentee.full_name,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else timezone.now().isoformat(),
                'progress_percentage': progress.progress_percentage
            }
        )
        
        logger.info(f"Program completed notification sent for program {program.id}")
        
    except Exception as e:
        logger.error(f"Error sending program completed notification: {str(e)}")


def send_mentorship_completed_notification(mentorship):
    """Send notification when mentorship is completed"""
    try:
        # Notification for mentee
        ChatNotification.objects.create(
            recipient=mentorship.mentee,
            chat_room=get_chat_room(mentorship),
            notification_type='mentorship_completed',
            title='Mentorship Completed! 🎓',
            message=f'Congratulations on completing your mentorship journey!',
            metadata={
                'mentorship_id': mentorship.id,
                'completed_at': mentorship.actual_end_date.isoformat() if mentorship.actual_end_date else timezone.now().isoformat(),
                'start_date': mentorship.start_date.isoformat() if mentorship.start_date else '',
                'duration_days': (mentorship.actual_end_date - mentorship.start_date).days if mentorship.actual_end_date and mentorship.start_date else 0,
                'total_programs': mentorship.programs.count(),
                'rating': mentorship.rating or 0
            }
        )
        
        # Notification for mentor
        ChatNotification.objects.create(
            recipient=mentorship.mentor,
            chat_room=get_chat_room(mentorship),
            notification_type='mentorship_completed',
            title='Mentorship Completed',
            message=f'Your mentorship with {mentorship.mentee.full_name} has been completed',
            metadata={
                'mentorship_id': mentorship.id,
                'mentee_name': mentorship.mentee.full_name,
                'completed_at': mentorship.actual_end_date.isoformat() if mentorship.actual_end_date else timezone.now().isoformat(),
                'duration_days': (mentorship.actual_end_date - mentorship.start_date).days if mentorship.actual_end_date and mentorship.start_date else 0,
                'rating': mentorship.rating or 0
            }
        )
        
        # Notification for admin/HR if mentorship has high rating
        if mentorship.rating and mentorship.rating >= 4.5:
            admins = CustomUser.objects.filter(
                role__in=['admin', 'hr'],
                is_active=True
            )
            
            for admin in admins:
                ChatNotification.objects.create(
                    recipient=admin,
                    notification_type='mentorship_success',
                    title='High-Rated Mentorship Completed',
                    message=f'Mentorship between {mentorship.mentor.full_name} and {mentorship.mentee.full_name} completed with rating: {mentorship.rating}/5',
                    metadata={
                        'mentorship_id': mentorship.id,
                        'mentor_name': mentorship.mentor.full_name,
                        'mentee_name': mentorship.mentee.full_name,
                        'rating': mentorship.rating,
                        'department': mentorship.department.name if mentorship.department else 'Unknown'
                    }
                )
        
        logger.info(f"Mentorship completed notification sent for mentorship {mentorship.id}")
        
    except Exception as e:
        logger.error(f"Error sending mentorship completed notification: {str(e)}")


# Helper functions
def get_chat_room(mentorship):
    """Get or create chat room for mentorship"""
    try:
        if hasattr(mentorship, 'chat_room') and mentorship.chat_room:
            return mentorship.chat_room
        
        # Try to find existing chat room
        chat_room = ChatRoom.objects.filter(
            participants=mentorship.mentor
        ).filter(
            participants=mentorship.mentee
        ).first()
        
        if chat_room:
            return chat_room
        
        # Create new chat room
        chat_room = ChatRoom.objects.create(
            name=f'Mentorship: {mentorship.mentor.full_name} - {mentorship.mentee.full_name}',
            room_type='mentorship'
        )
        chat_room.participants.add(mentorship.mentor, mentorship.mentee)
        chat_room.save()
        
        return chat_room
        
    except Exception as e:
        logger.error(f"Error getting chat room: {str(e)}")
        return None


def get_program_progress_percentage(mentorship, program):
    """Get program progress percentage"""
    try:
        from mentorshipApp.models import MentorshipProgramProgress
        progress = MentorshipProgramProgress.objects.filter(
            mentorship=mentorship,
            program=program
        ).first()
        
        return progress.progress_percentage if progress else 0
        
    except Exception as e:
        logger.error(f"Error getting program progress: {str(e)}")
        return 0


def get_total_sessions_completed(mentorship):
    """Get total sessions completed in mentorship"""
    try:
        from mentorshipApp.models import MentorshipSession
        return MentorshipSession.objects.filter(
            mentorship=mentorship,
            status='completed'
        ).count()
        
    except Exception as e:
        logger.error(f"Error getting total sessions completed: {str(e)}")
        return 0


# Background task to send session reminders
def send_all_upcoming_session_reminders():
    """Send reminders for all upcoming sessions"""
    try:
        from mentorshipApp.models import MentorshipSession
        
        # Get all scheduled sessions in the next 25 hours
        time_threshold = timezone.now() + timedelta(hours=25)
        
        upcoming_sessions = MentorshipSession.objects.filter(
            status='scheduled',
            scheduled_date__gte=timezone.now(),
            scheduled_date__lte=time_threshold
        ).select_related('mentorship', 'mentorship__mentor', 'mentorship__mentee', 'session_template')
        
        logger.info(f"Checking {upcoming_sessions.count()} upcoming sessions for reminders")
        
        for session in upcoming_sessions:
            send_upcoming_session_reminder(session)
        
        logger.info("Session reminder check completed")
        
    except Exception as e:
        logger.error(f"Error sending session reminders: {str(e)}")






























from xmlrpc import client
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from notificationApp.models import ChatNotification, ChatRoom, GroupChatRoom
from userApp.models import CustomUser
from chatApp.models import GroupChatParticipant


def send_notification_to_user(user_id, notification_data):
    """
    Send real-time notification to a specific user via WebSocket
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )


def send_email_notification(recipient_email, subject, template_name, context):
    """
    Send email notification
    """
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def create_system_message(chat_room, content):
    """
    Create a system message in a chat room
    """
    from .models import Message
    
    # Get or create a system user (you might want to create a dedicated system user)
    try:
        system_user = CustomUser.objects.get(phone_number='system')
    except CustomUser.DoesNotExist:
        # Create system user if it doesn't exist
        system_user = CustomUser.objects.create_user(
            phone_number='system',
            role='admin',
            email='system@example.com'
        )
    
    message = Message.objects.create(
        chat_room=chat_room,
        sender=system_user,
        content=content,
        message_type='system'
    )
    
    # Send real-time update
    from .serializers import MessageSerializer
    channel_layer = get_channel_layer()
    
    # Create mock request for serializer
    class MockRequest:
        def __init__(self):
            self.user = system_user
    
    serializer = MessageSerializer(message, context={'request': MockRequest()})
    
    async_to_sync(channel_layer.group_send)(
        f"chat_{chat_room.id}",
        {
            'type': 'chat_message',
            'message': serializer.data
        }
    )
    
    return message


def get_user_chat_stats(user):
    """
    Get chat statistics for a user
    """
    from .models import ChatRoom, Message
    from userApp.models import CustomUser
 
    
    stats = {
        'total_chat_rooms': 0,
        'active_chat_rooms': 0,
        'total_messages_sent': 0,
        'unread_messages': 0,
        'unread_notifications': 0
    }
    
    try:
        if user.role == 'mentee':
            mentee = CustomUser.objects.get(user=user)
            chat_rooms = ChatRoom.objects.filter(mentee=mentee)
        elif user.role == 'mentor':
            mentor = CustomUser.objects.get(user=user)
            chat_rooms = ChatRoom.objects.filter(mentor=mentor)
        else:
            return stats
        
        stats['total_chat_rooms'] = chat_rooms.count()
        stats['active_chat_rooms'] = chat_rooms.filter(is_active=True).count()
        stats['total_messages_sent'] = Message.objects.filter(
            chat_room__in=chat_rooms,
            sender=user,
            is_deleted=False
        ).count()
        stats['unread_messages'] = Message.objects.filter(
            chat_room__in=chat_rooms,
            is_deleted=False,
            is_read=False
        ).exclude(sender=user).count()
        stats['unread_notifications'] = ChatNotification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
        
    except Exception as e:
        print(f"Error getting chat stats: {e}")
    
    return stats


def validate_file_upload(file):
    """
    Validate file uploads for chat attachments
    """
    max_size = 10 * 1024 * 1024  # 10MB
    allowed_types = [
        'image/jpeg', 'image/png', 'image/gif',
        'application/pdf', 'text/plain',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    if file.size > max_size:
        return False, "File size too large. Maximum size is 10MB."
    
    if file.content_type not in allowed_types:
        return False, "File type not allowed."
    
    return True, "File is valid."


def format_chat_room_name(mentorship):
    """
    Generate a formatted name for chat room
    """
    return f"Case {mentorship.case_number} - {mentorship.title[:30]}{'...' if len(mentorship.title) > 30 else ''}"

def get_online_users(chat_room_id):
    """
    Get list of online users in a chat room
    This would require implementing user presence tracking
    """
    # This is a placeholder - you'd need to implement Redis-based presence tracking
    # or use Django Channels' group management features
    return []











# Add to mentorshipApp/utils.py (create if it doesn't exist)

from django.db.models import Count, Q, Max
from django.utils import timezone
from datetime import timedelta

def get_user_chat_statistics(user):
    """Get comprehensive chat statistics for a user"""
    stats = {
        'total_chats': 0,
        'unread_messages': 0,
        'active_conversations': 0,
        'mentorship_chats': 0,
        'department_chats': 0,
        'staff_chats': 0
    }
    
    try:
        if user.role not in ['mentor', 'mentee']:
            return stats
        
        # One-on-one chat stats
        one_on_one_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        )
        
        # Group chat stats
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        )
        
        stats['total_chats'] = one_on_one_chats.count() + group_chats.count()
        
        # Calculate unread messages
        total_unread = 0
        
        # Unread in one-on-one chats
        for chat in one_on_one_chats:
            total_unread += chat.messages.filter(
                is_deleted=False,
                is_read=False
            ).exclude(sender=user).count()
        
        # Unread in group chats
        for chat in group_chats:
            participant = GroupChatParticipant.objects.filter(
                chat_room=chat,
                user=user
            ).first()
            
            if participant and participant.last_read_at:
                total_unread += chat.group_messages.filter(
                    created_at__gt=participant.last_read_at,
                    is_deleted=False
                ).exclude(sender=user).count()
            else:
                total_unread += chat.group_messages.filter(
                    is_deleted=False
                ).exclude(sender=user).count()
        
        stats['unread_messages'] = total_unread
        
        # Active conversations (chats with activity in last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        
        active_one_on_one = one_on_one_chats.filter(
            messages__created_at__gte=week_ago
        ).distinct().count()
        
        active_group = group_chats.filter(
            group_messages__created_at__gte=week_ago
        ).distinct().count()
        
        stats['active_conversations'] = active_one_on_one + active_group
        
        # Mentorship chats
        if user.role == 'mentor':
            mentorship_chats = GroupChatRoom.objects.filter(
                participants=user,
                chat_type='mentorship_group',
                is_active=True,
                is_archived=False
            ).count()
        else:
            mentorship_chats = GroupChatRoom.objects.filter(
                participants=user,
                chat_type__in=['mentorship_group', 'department_group'],
                is_active=True,
                is_archived=False
            ).count()
        
        stats['mentorship_chats'] = mentorship_chats
        
        # Department chats
        department_chats = GroupChatRoom.objects.filter(
            participants=user,
            chat_type='department_group',
            is_active=True,
            is_archived=False
        ).count()
        
        stats['department_chats'] = department_chats
        
        # Staff chats (for mentees)
        if user.role == 'mentee':
            staff_chats = ChatRoom.objects.filter(
                Q(user1=user) | Q(user2=user),
                chat_type__in=['mentee_admin', 'mentee_hr'],
                is_active=True
            ).count()
            
            stats['staff_chats'] = staff_chats
        
    except Exception as e:
        print(f"Error getting chat statistics: {e}")
    
    return stats


def get_recent_chat_activity(user, limit=5):
    """Get recent chat activity for a user"""
    recent_activity = []
    
    try:
        # Get recent one-on-one messages
        one_on_one_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        )
        
        for chat in one_on_one_chats:
            recent_messages = chat.messages.filter(
                is_deleted=False
            ).order_by('-created_at')[:3]
            
            for message in recent_messages:
                other_user = chat.user2 if chat.user1 == user else chat.user1
                recent_activity.append({
                    'type': 'one_on_one',
                    'chat_id': chat.id,
                    'other_user': other_user.full_name,
                    'message': message.content[:100],
                    'timestamp': message.created_at,
                    'sender': message.sender.full_name,
                    'is_own': message.sender == user,
                    'is_read': message.is_read if message.sender != user else True
                })
        
        # Get recent group messages
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        )
        
        for chat in group_chats:
            recent_messages = chat.group_messages.filter(
                is_deleted=False
            ).order_by('-created_at')[:3]
            
            for message in recent_messages:
                recent_activity.append({
                    'type': 'group',
                    'chat_id': chat.id,
                    'chat_name': chat.name,
                    'message': message.content[:100],
                    'timestamp': message.created_at,
                    'sender': message.sender.full_name,
                    'is_own': message.sender == user,
                    'is_read': message.get_read_by().filter(id=user.id).exists() if message.sender != user else True
                })
        
        # Sort by timestamp and limit
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        return recent_activity[:limit]
        
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return []