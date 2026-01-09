# chatApp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from mentorshipApp.models import Mentorship
from .models import ChatRoom, GroupChatRoom
from notificationApp.models import ChatNotification
from userApp.models import CustomUser


@receiver(post_save, sender=Mentorship)
def create_mentorship_chats(sender, instance, created, **kwargs):
    """Create chats when mentorship is created"""
    if created and instance.status == 'active':
        # Create one-on-one mentor-mentee chat
        ChatRoom.objects.get_or_create(
            mentorship=instance,
            chat_type='mentor_mentee',
            defaults={
                'user1': instance.mentor,
                'user2': instance.mentee,
                'is_active': True
            }
        )
        
        # Get the department from the mentorship
        department = instance.department
        
        # Generate group chat name
        chat_name = f"{instance.mentee.full_name}'s Mentorship Group - {department.name}"
        
        # Get admin and HR users in the department
        admin_hr_users = CustomUser.objects.filter(
            departments=department,
            role__in=['admin', 'hr'],
            status='approved'
        )
        
        # Create mentorship group chat
        group_chat = GroupChatRoom.objects.create(
            name=chat_name,
            description=f"Mentorship group for {instance.mentee.full_name} in {department.name}",
            chat_type='mentorship_group',
            department=department.name,
            mentorship=instance,
            created_by=instance.created_by if instance.created_by else instance.mentor,
            is_active=True
        )
        
        # Add participants to mentorship group
        # Add mentor
        group_chat.add_participant(
            instance.mentor, 
            added_by=group_chat.created_by, 
            role='moderator'
        )
        
        # Add mentee
        group_chat.add_participant(
            instance.mentee, 
            added_by=group_chat.created_by, 
            role='member'
        )
        
        # Add admin and HR users
        for user in admin_hr_users:
            group_chat.add_participant(
                user, 
                added_by=group_chat.created_by, 
                role='admin'
            )
        
        # Create or get department-wide group chat
        dept_chat_name = f"{department.name} Department Chat"
        dept_group_chat, dept_created = GroupChatRoom.objects.get_or_create(
            name=dept_chat_name,
            chat_type='department_group',
            department=department.name,
            defaults={
                'description': f"Global chat for all mentorship participants in {department.name}",
                'created_by': group_chat.created_by,
                'is_active': True
            }
        )
        
        # Add mentee to department chat if not already a participant
        if not dept_group_chat.has_participant(instance.mentee):
            dept_group_chat.add_participant(
                instance.mentee, 
                added_by=group_chat.created_by, 
                role='member'
            )
        
        # Add mentor to department chat if not already a participant
        if not dept_group_chat.has_participant(instance.mentor):
            dept_group_chat.add_participant(
                instance.mentor, 
                added_by=group_chat.created_by, 
                role='moderator'
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
        department = instance.department
        
        group_chat, group_created = GroupChatRoom.objects.get_or_create(
            mentorship=instance,
            chat_type='mentorship_group',
            defaults={
                'name': f"{instance.mentee.full_name}'s Mentorship - {department.name}",
                'description': f"Mentorship group for {instance.mentee.full_name} with {instance.mentor.full_name}",
                'department': department.name,
                'created_by': instance.created_by if instance.created_by else instance.mentor,
                'is_active': True
            }
        )
        
        # Ensure mentor is in the group chat
        if not group_chat.has_participant(instance.mentor):
            group_chat.add_participant(
                instance.mentor, 
                added_by=group_chat.created_by, 
                role='moderator'
            )
        
        # Ensure mentee is in the group chat
        if not group_chat.has_participant(instance.mentee):
            group_chat.add_participant(
                instance.mentee, 
                added_by=group_chat.created_by, 
                role='member'
            )
        
        # Add relevant admin/HR users from the same department
        department_staff = CustomUser.objects.filter(
            departments=department,
            role__in=['admin', 'hr'],
            status='approved'
        )
        
        for staff_user in department_staff:
            if not group_chat.has_participant(staff_user):
                group_chat.add_participant(
                    staff_user, 
                    added_by=group_chat.created_by, 
                    role='admin'
                )
        
        # Ensure department group chat exists
        dept_chat_name = f"{department.name} Department Chat"
        dept_group_chat, dept_created = GroupChatRoom.objects.get_or_create(
            name=dept_chat_name,
            chat_type='department_group',
            department=department.name,
            defaults={
                'description': f"Department-wide chat for all {department.name} participants",
                'created_by': group_chat.created_by,
                'is_active': True
            }
        )
        
        # Add mentee to department chat if not already a participant
        if not dept_group_chat.has_participant(instance.mentee):
            dept_group_chat.add_participant(
                instance.mentee, 
                added_by=dept_group_chat.created_by, 
                role='member'
            )
        
        # Add mentor to department chat if not already a participant
        if not dept_group_chat.has_participant(instance.mentor):
            dept_group_chat.add_participant(
                instance.mentor, 
                added_by=dept_group_chat.created_by, 
                role='moderator'
            )


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
            chat_type = 'mentee_admin' if admin_hr_user.role == 'admin' else 'mentee_hr'
            
            ChatRoom.objects.get_or_create(
                user1=instance,
                user2=admin_hr_user,
                defaults={
                    'chat_type': chat_type,
                    'is_active': True
                }
            )


@receiver(post_save, sender=ChatNotification)
def send_realtime_notification(sender, instance, created, **kwargs):
    """Send real-time notification via WebSocket when a new notification is created"""
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
                    'sender': {
                        'id': instance.sender.id,
                        'full_name': instance.sender.full_name
                    } if instance.sender else None
                }
            }
        )