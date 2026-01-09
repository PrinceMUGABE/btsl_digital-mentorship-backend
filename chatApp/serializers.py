from rest_framework import serializers
from django.utils.timezone import now
from .models import (
    ChatRoom, ChatType, Message, MessageReadStatus,
    GroupChatRoom, GroupChatParticipant, GroupChatMessage,
    GroupMessageReadStatus
)
from userApp.models import CustomUser
from mentorshipApp.models import Mentorship


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for chat"""
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'work_mail_address', 
                 'full_name', 'role', 'department', 'status', 'availability_status']
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    sender = UserBasicSerializer(read_only=True)
    is_own_message = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'message_type', 'content', 'attachment',
            'is_read', 'created_at', 'updated_at', 'is_own_message',
            'formatted_time', 'read_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at', 'is_read', 'read_at']
    
    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False
    
    def get_formatted_time(self, obj):
        return obj.created_at.strftime('%H:%M')


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating messages"""
    chat_room_id = serializers.IntegerField()
    message_type = serializers.ChoiceField(choices=Message.MESSAGE_TYPES, default='text')
    content = serializers.CharField()
    attachment = serializers.FileField(required=False)
    
    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        if len(value) > 5000:
            raise serializers.ValidationError("Message is too long (max 5000 characters)")
        return value


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat rooms"""
    mentorship = serializers.SerializerMethodField()
    mentee = serializers.SerializerMethodField()
    mentor = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'mentorship', 'chat_type', 'user1', 'user2',
            'mentee', 'mentor', 'other_user', 'is_active',
            'created_at', 'updated_at', 'last_message', 'unread_count'
        ]
        read_only_fields = fields
    
    def get_mentorship(self, obj):
        from mentoshipApp.serializers import MentorshipSerializer
        if obj.mentorship:
            return MentorshipSerializer(obj.mentorship).data
        return None
    
    def get_mentee(self, obj):
        if obj.mentorship:
            return UserBasicSerializer(obj.mentorship.mentee).data
        return None
    
    def get_mentor(self, obj):
        if obj.mentorship:
            return UserBasicSerializer(obj.mentorship.mentor).data
        return None
    
    def get_other_user(self, obj):
        request = self.context.get('request')
        if request and request.user:
            if request.user == obj.user1:
                return UserBasicSerializer(obj.user2).data
            else:
                return UserBasicSerializer(obj.user1).data
        return None
    
    def get_last_message(self, obj):
        last_message = obj.messages.filter(is_deleted=False).last()
        if last_message:
            return {
                'content': last_message.content[:50] + '...' if len(last_message.content) > 50 else last_message.content,
                'sender': last_message.sender.full_name,
                'sender_id': last_message.sender.id,
                'created_at': last_message.created_at,
                'message_type': last_message.message_type
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(
                is_deleted=False,
                is_read=False
            ).exclude(sender=request.user).count()
        return 0


class GroupChatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for group chat participants"""
    user = UserBasicSerializer(read_only=True)
    added_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = GroupChatParticipant
        fields = [
            'id', 'user', 'role', 'added_by', 'joined_at', 
            'last_read_at', 'is_muted'
        ]
        read_only_fields = ['id', 'user', 'added_by', 'joined_at', 'last_read_at']


class GroupChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for group chat rooms"""
    created_by = UserBasicSerializer(read_only=True)
    participants = GroupChatParticipantSerializer(many=True, read_only=True, source='chat_participants')
    mentorship_info = serializers.SerializerMethodField()
    department_display = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupChatRoom
        fields = [
            'id', 'name', 'description', 'chat_type', 'department', 'department_display',
            'mentorship', 'mentorship_info', 'created_by', 'participants', 'is_active',
            'is_archived', 'created_at', 'updated_at', 'last_message', 'unread_count',
            'can_manage'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']
    
    def get_mentorship_info(self, obj):
        if obj.mentorship:
            return {
                'id': obj.mentorship.id,
                'program': obj.mentorship.program.name,
                'mentor': obj.mentorship.mentor.full_name,
                'mentee': obj.mentorship.mentee.full_name
            }
        return None
    
    def get_department_display(self, obj):
        return obj.department
    
    def get_last_message(self, obj):
        last_message = obj.group_messages.filter(is_deleted=False).last()
        if last_message:
            return {
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'sender': last_message.sender.full_name,
                'sender_id': last_message.sender.id,
                'created_at': last_message.created_at,
                'message_type': last_message.message_type
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            last_read_status = GroupChatParticipant.objects.filter(
                chat_room=obj,
                user=request.user
            ).first()
            
            if last_read_status and last_read_status.last_read_at:
                return obj.group_messages.filter(
                    created_at__gt=last_read_status.last_read_at,
                    is_deleted=False
                ).exclude(sender=request.user).count()
            else:
                return obj.group_messages.filter(is_deleted=False).exclude(sender=request.user).count()
        return 0
    
    def get_can_manage(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.can_manage_chat(request.user)
        return False


class GroupChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for group chat messages"""
    sender = UserBasicSerializer(read_only=True)
    reply_to = serializers.PrimaryKeyRelatedField(read_only=True)
    reply_to_info = serializers.SerializerMethodField()
    is_own_message = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    read_by = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupChatMessage
        fields = [
            'id', 'sender', 'message_type', 'content', 'attachment',
            'is_edited', 'edited_at', 'is_deleted', 'reply_to', 'reply_to_info',
            'created_at', 'updated_at', 'is_own_message', 'formatted_time',
            'read_by'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']
    
    def get_reply_to_info(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender': obj.reply_to.sender.full_name,
                'content': obj.reply_to.content[:100],
                'message_type': obj.reply_to.message_type
            }
        return None
    
    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False
    
    def get_formatted_time(self, obj):
        return obj.created_at.strftime('%H:%M')
    
    def get_read_by(self, obj):
        return obj.get_read_by().values_list('id', flat=True)


# Additional serializers for chat management
class GroupChatCreateSerializer(serializers.Serializer):
    """Serializer for creating group chats"""
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    chat_type = serializers.ChoiceField(choices=ChatType.choices)
    department = serializers.CharField(required=False, allow_blank=True)
    mentorship_id = serializers.IntegerField(required=False)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[]
    )


class GroupMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating group messages"""
    chat_room_id = serializers.IntegerField()
    message_type = serializers.ChoiceField(choices=GroupChatMessage.MESSAGE_TYPES, default='text')
    content = serializers.CharField()
    attachment = serializers.FileField(required=False)
    reply_to_id = serializers.IntegerField(required=False)


class AddParticipantSerializer(serializers.Serializer):
    """Serializer for adding participants to group chat"""
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=GroupChatParticipant.ROLE_CHOICES, default='member')