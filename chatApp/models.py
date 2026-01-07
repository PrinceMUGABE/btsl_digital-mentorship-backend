from django.db import models
from django.utils.timezone import now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Count, Q
from userApp.models import CustomUser
from mentoshipApp.models import Mentorship


class ChatType(models.TextChoices):
    ONE_ON_ONE = 'one_on_one', 'One-on-One Chat'
    MENTORSHIP_GROUP = 'mentorship_group', 'Mentorship Group Chat'
    DEPARTMENT_GROUP = 'department_group', 'Department Group Chat'
    CROSS_DEPARTMENT = 'cross_department', 'Cross-Department Chat'


class ChatRoom(models.Model):
    """One-on-one chat room model"""
    CHAT_TYPES = [
        ('mentor_mentee', 'Mentor-Mentee'),
        ('mentee_admin', 'Mentee-Admin'),
        ('mentee_hr', 'Mentee-HR'),
        ('mentor_admin', 'Mentor-Admin'),
        ('mentor_hr', 'Mentor-HR'),
        ('admin_hr', 'Admin-HR'),
    ]
    
    mentorship = models.OneToOneField(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='one_on_one_chat',
        null=True,
        blank=True
    )
    chat_type = models.CharField(
        max_length=20, 
        choices=CHAT_TYPES, 
        default='mentor_mentee'
    )
    user1 = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='chats_as_user1',
        default=None
    )
    user2 = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='chats_as_user2',
        default=None
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user1', 'user2']
        ordering = ['-updated_at']
        verbose_name = 'Chat Room'
        verbose_name_plural = 'Chat Rooms'
    
    def __str__(self):
        return f"Chat between {self.user1.full_name} and {self.user2.full_name}"
    
    @property
    def participants(self):
        """Get both participants"""
        return [self.user1, self.user2]
    
    def get_other_user(self, user):
        """Get the other user in the chat"""
        if user == self.user1:
            return self.user2
        return self.user1


class Message(models.Model):
    """Individual messages in chat rooms"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('system', 'System'),
    ]
    
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    
    # Message status
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [
            models.Index(fields=['chat_room', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.full_name} in ChatRoom {self.chat_room.id}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = now()
            self.save(update_fields=['is_read', 'read_at'])


class MessageReadStatus(models.Model):
    """Track read status of messages by users"""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='message_read_statuses'
    )
    read_at = models.DateTimeField(default=now)
    
    class Meta:
        unique_together = ['message', 'user']
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'
        indexes = [
            models.Index(fields=['user', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} read message at {self.read_at}"


class GroupChatRoom(models.Model):
    """Group chat room model"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    chat_type = models.CharField(max_length=50, choices=ChatType.choices, default=ChatType.MENTORSHIP_GROUP)
    department = models.CharField(max_length=100, blank=True, null=True)
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='group_chats',
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_group_chats'
    )
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Group Chat Room'
        verbose_name_plural = 'Group Chat Rooms'
        indexes = [
            models.Index(fields=['chat_type']),
            models.Index(fields=['department']),
            models.Index(fields=['is_active', 'is_archived']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_chat_type_display()})"
    
    @property
    def participants(self):
        """Get all participants for this chat room"""
        return CustomUser.objects.filter(groupchatparticipant__chat_room=self)
    
    def add_participant(self, user, added_by=None, role='member'):
        """Add a participant to the group chat"""
        participant, created = GroupChatParticipant.objects.get_or_create(
            chat_room=self,
            user=user,
            defaults={
                'added_by': added_by,
                'role': role,
                'joined_at': now()
            }
        )
        return participant
    
    def remove_participant(self, user):
        """Remove a participant from the group chat"""
        GroupChatParticipant.objects.filter(chat_room=self, user=user).delete()
    
    def get_admin_hr_participants(self):
        """Get all admin and HR participants"""
        return self.participants.filter(role__in=['admin', 'hr'])
    
    def can_manage_chat(self, user):
        """Check if user can manage this chat"""
        if user.role in ['admin', 'hr']:
            return True
        try:
            participant = GroupChatParticipant.objects.get(chat_room=self, user=user)
            return participant.role in ['admin', 'moderator']
        except GroupChatParticipant.DoesNotExist:
            return False


class GroupChatParticipant(models.Model):
    """Track participants in group chats with roles"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
        ('guest', 'Guest'),
    ]
    
    chat_room = models.ForeignKey(
        GroupChatRoom, 
        on_delete=models.CASCADE,
        related_name='chat_participants'
    )
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='group_chat_participations'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    added_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_group_participants'
    )
    joined_at = models.DateTimeField(default=now)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['chat_room', 'user']
        verbose_name = 'Group Chat Participant'
        verbose_name_plural = 'Group Chat Participants'
        indexes = [
            models.Index(fields=['chat_room', 'user']),
            models.Index(fields=['role']),
            models.Index(fields=['is_muted']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} in {self.chat_room.name} ({self.role})"
    
    def can_send_messages(self):
        """Check if participant can send messages"""
        if self.is_muted:
            return False
        return self.role in ['admin', 'moderator', 'member']
    
    def can_manage_participants(self):
        """Check if participant can manage other participants"""
        return self.role in ['admin', 'moderator']


class GroupChatMessage(models.Model):
    """Messages in group chats"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('system', 'System'),
        ('announcement', 'Announcement'),
    ]
    
    chat_room = models.ForeignKey(
        GroupChatRoom,
        on_delete=models.CASCADE,
        related_name='group_messages'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_group_messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    attachment = models.FileField(upload_to='group_chat_attachments/', blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Group Chat Message'
        verbose_name_plural = 'Group Chat Messages'
        indexes = [
            models.Index(fields=['chat_room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.full_name} in {self.chat_room.name}"
    
    def mark_as_read_by_user(self, user):
        """Mark message as read by specific user"""
        GroupMessageReadStatus.objects.get_or_create(
            message=self,
            user=user,
            defaults={'read_at': now()}
        )
    
    def get_read_by(self):
        """Get users who have read this message"""
        return CustomUser.objects.filter(
            group_message_read_statuses__message=self
        )
    
    def get_unread_by(self):
        """Get users who haven't read this message"""
        all_participants = self.chat_room.participants.all()
        read_users = self.get_read_by()
        return all_participants.exclude(id__in=read_users.values_list('id', flat=True))


class GroupMessageReadStatus(models.Model):
    """Track read status of group messages"""
    message = models.ForeignKey(
        GroupChatMessage,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='group_message_read_statuses'
    )
    read_at = models.DateTimeField(default=now)
    
    class Meta:
        unique_together = ['message', 'user']
        verbose_name = 'Group Message Read Status'
        verbose_name_plural = 'Group Message Read Statuses'
        indexes = [
            models.Index(fields=['user', 'read_at']),
        ]