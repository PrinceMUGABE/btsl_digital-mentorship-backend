# mentorshipApp/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Mentorship
from .models import ChatRoom
from notificationApp.models import ChatNotification
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Mentorship, GroupChatRoom, GroupChatParticipant, ChatRoom
from userApp.models import CustomUser


@receiver(post_save, sender=Mentorship)
def create_chat_room_on_mentorship(sender, instance, created, **kwargs):
    """
    Automatically create a chat room when a mentorship is created with an assigned mentor
    """
    if not created and instance.mentor and instance.status == 'assigned':
        # Check if chat room already exists
        if not hasattr(instance, 'chat_room'):
            # Create chat room
            chat_room = ChatRoom.objects.create(
                case=instance,
                mentor=instance.mentor,
                mentee=instance.mentee
            )
            
            # Create notifications for both parties
            ChatNotification.objects.create(
                recipient=instance.mentee.user,
                chat_room=chat_room,
                notification_type='case_assigned',
                title=f'Chat room created for case {instance.mentorship}',
                message=f'You can now chat with your assigned mentor'
            )
            
            ChatNotification.objects.create(
                recipient=instance.mentor.user,
                chat_room=chat_room,
                notification_type='case_assigned',
                title=f'Chat room created for case {instance.mentorship}',
                message=f'You can now chat with your client'
            )


@receiver(post_save, sender=Mentorship)
def notify_case_status_change(sender, instance, created, **kwargs):
    """
    Send notification when case status changes
    """
    if not created and hasattr(instance, 'chat_room'):
        chat_room = instance.chat_room
        
        # Create notifications for both parties about status change
        status_display = dict(Mentorship.STATUS_CHOICES).get(instance.status, instance.status)
        
        ChatNotification.objects.create(
            recipient=instance.mentee.user,
            chat_room=chat_room,
            notification_type='',
            title=f'Case {instance.mentorship} status updated',
            message=f'Your case status has been changed to: {status_display}'
        )
        
        if instance.mentor:
            ChatNotification.objects.create(
                recipient=instance.mentor.user,
                chat_room=chat_room,
                notification_type='case_status_changed',
                title=f'Case {instance.mentorship} status updated',
                message=f'Case status has been changed to: {status_display}'
            )


@receiver(post_save, sender=ChatNotification)
def send_realtime_notification(sender, instance, created, **kwargs):
    """
    Send real-time notification via WebSocket when a new notification is created
    """
    if created:
        channel_layer = get_channel_layer()
        
        # Send to user's notification channel
        async_to_sync(channel_layer.group_send)(
            f"user_{instance.recipient.id}",
            {
                'type': 'notification_message',
                'notification': {
                    'id': instance.id,
                    'title': instance.title,
                    'message': instance.message,
                    'notification_type': instance.notification_type,
                    'created_at': instance.created_at.isoformat(),
                    'case_number': instance.chat_room.case.case_number if instance.chat_room else None,
                    'sender': {
                        'id': instance.sender.id,
                        'phone_number': instance.sender.phone_number
                    } if instance.sender else None
                }
            }
        )





@receiver(post_save, sender=Mentorship)
def create_mentorship_chats(sender, instance, created, **kwargs):
    """Create chats when mentorship is created"""
    if created and instance.status == 'active':
        # Create one-on-one mentor-mentee chat
        ChatRoom.objects.create(
            mentorship=instance,
            chat_type='mentor_mentee',
            user1=instance.mentor,
            user2=instance.mentee
        )
        
        # Create mentorship group chat with all participants
        department = instance.program.department
        
        # Generate group chat name
        chat_name = f"{instance.mentee.full_name}'s Mentorship Group - {instance.program.name}"
        
        # Get admin and HR users in the department
        admin_hr_users = CustomUser.objects.filter(
            department=department,
            role__in=['admin', 'hr'],
            status='approved'
        )
        
        # Create group chat
        group_chat = GroupChatRoom.objects.create(
            name=chat_name,
            description=f"Mentorship group for {instance.mentee.full_name} in {instance.program.name}",
            chat_type='mentorship_group',
            department=department,
            mentorship=instance,
            created_by=instance.created_by if instance.created_by else instance.mentor
        )
        
        # Add participants
        # Add mentor
        group_chat.add_participant(instance.mentor, added_by=group_chat.created_by, role='moderator')
        
        # Add mentee
        group_chat.add_participant(instance.mentee, added_by=group_chat.created_by, role='member')
        
        # Add admin and HR users
        for user in admin_hr_users:
            group_chat.add_participant(user, added_by=group_chat.created_by, role='admin')
        
        # Create department-wide group chat if it doesn't exist
        dept_group_chat, dept_created = GroupChatRoom.objects.get_or_create(
            name=f"{department} Department Chat",
            chat_type='department_group',
            department=department,
            defaults={
                'description': f"Global chat for all mentorship participants in {department}",
                'created_by': group_chat.created_by
            }
        )
        
        # Add mentee to department chat
        dept_group_chat.add_participant(instance.mentee, added_by=group_chat.created_by, role='member')
        
        # Add mentor to department chat
        dept_group_chat.add_participant(instance.mentor, added_by=group_chat.created_by, role='moderator')


@receiver(post_save, sender=CustomUser)
def create_one_on_one_chats_for_new_user(sender, instance, created, **kwargs):
    """Create one-on-one chats for new users with admin/HR"""
    if created and instance.role == 'mentee':
        # Get all admin and HR users
        admin_hr_users = CustomUser.objects.filter(
            role__in=['admin', 'hr'],
            status='approved'
        )
        
        # Create one-on-one chats with each admin/HR
        for admin_hr_user in admin_hr_users:
            # Determine chat type based on admin_hr_user role
            if admin_hr_user.role == 'admin':
                chat_type = 'mentee_admin'
            else:
                chat_type = 'mentee_hr'
            
            ChatRoom.objects.get_or_create(
                user1=instance,
                user2=admin_hr_user,
                defaults={'chat_type': chat_type}
            )





@receiver(post_save, sender=Mentorship)
def ensure_user_chats_exist(sender, instance, created, **kwargs):
    """Ensure all required chats exist for mentorship participants"""
    if instance.status == 'active':
        # Ensure one-on-one mentor-mentee chat exists
        ChatRoom.objects.get_or_create(
            mentorship=instance,
            chat_type='mentor_mentee',
            defaults={
                'user1': instance.mentor,
                'user2': instance.mentee,
                'is_active': True
            }
        )
        
        # Ensure mentee has one-on-one chats with admin/HR
        admin_hr_users = CustomUser.objects.filter(
            role__in=['admin', 'hr'],
            status='approved'
        )
        
        for staff_user in admin_hr_users:
            chat_type = 'mentee_admin' if staff_user.role == 'admin' else 'mentee_hr'
            ChatRoom.objects.get_or_create(
                user1=instance.mentee,
                user2=staff_user,
                defaults={
                    'chat_type': chat_type,
                    'is_active': True
                }
            )
        
        # Ensure mentorship group chat exists
        group_chat, group_created = GroupChatRoom.objects.get_or_create(
            mentorship=instance,
            chat_type='mentorship_group',
            defaults={
                'name': f"{instance.mentee.full_name}'s Mentorship - {instance.program.name}",
                'description': f"Mentorship group for {instance.mentee.full_name} with {instance.mentor.full_name}",
                'department': instance.program.department,
                'created_by': instance.created_by if instance.created_by else instance.mentor,
                'is_active': True
            }
        )
        
        # Ensure all participants are added
        if group_created or not group_chat.participants.filter(id=instance.mentor.id).exists():
            group_chat.add_participant(instance.mentor, added_by=group_chat.created_by, role='moderator')
        
        if group_created or not group_chat.participants.filter(id=instance.mentee.id).exists():
            group_chat.add_participant(instance.mentee, added_by=group_chat.created_by, role='member')
        
        # Add relevant admin/HR users from the same department
        department_staff = CustomUser.objects.filter(
            department=instance.program.department,
            role__in=['admin', 'hr'],
            status='approved'
        )
        
        for staff_user in department_staff:
            if not group_chat.participants.filter(id=staff_user.id).exists():
                group_chat.add_participant(staff_user, added_by=group_chat.created_by, role='admin')
        
        # Ensure department group chat exists and mentee is added
        dept_group_chat, dept_created = GroupChatRoom.objects.get_or_create(
            name=f"{instance.program.department} Department Chat",
            chat_type='department_group',
            department=instance.program.department,
            defaults={
                'description': f"Department-wide chat for all {instance.program.department} participants",
                'created_by': group_chat.created_by,
                'is_active': True
            }
        )
        
        # Add mentee to department chat
        if not dept_group_chat.participants.filter(id=instance.mentee.id).exists():
            dept_group_chat.add_participant(instance.mentee, added_by=dept_group_chat.created_by, role='member')
        
        # Add mentor to department chat
        if not dept_group_chat.participants.filter(id=instance.mentor.id).exists():
            dept_group_chat.add_participant(instance.mentor, added_by=dept_group_chat.created_by, role='moderator')