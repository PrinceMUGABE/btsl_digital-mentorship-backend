# chatApp/admin.py

from django.contrib import admin
from .models import (
    GroupChatMessage, GroupChatParticipant, GroupChatRoom, GroupMessageReadStatus, 
    ChatRoom, Message, MessageReadStatus
)


from notificationApp.models import ChatNotification

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'mentorship', 'chat_type', 'is_active', 'created_at', 'updated_at']
    list_filter = ['chat_type', 'is_active', 'created_at', 'updated_at']
    search_fields = [
        'user1__full_name', 
        'user2__full_name', 
        'mentorship__program__name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mentorship', 
            'user1', 
            'user2',
            'mentorship__mentor',
            'mentorship__mentee'
        )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('mentorship', 'chat_type', 'user1', 'user2')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat_room', 'sender', 'message_type', 'content_preview', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'is_deleted', 'created_at']
    search_fields = ['content', 'sender__full_name', 'chat_room__user1__full_name']
    readonly_fields = ['created_at', 'updated_at', 'read_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('chat_room', 'sender')


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'read_at']
    list_filter = ['read_at']
    search_fields = ['message__content', 'user__full_name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'user')


@admin.register(ChatNotification)
class ChatNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'sender', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'recipient__full_name', 'sender__full_name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient', 'sender', 'chat_room')


# Group Chat Admin Classes
class GroupChatParticipantInline(admin.TabularInline):
    """Inline for viewing participants in GroupChatRoom admin"""
    model = GroupChatParticipant
    extra = 0
    readonly_fields = ['joined_at', 'added_by']
    fields = ['user', 'role', 'added_by', 'joined_at', 'is_muted']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'added_by')


@admin.register(GroupChatRoom)
class GroupChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'chat_type', 'department', 'mentorship', 'is_active', 'created_by', 'created_at', 'participant_count']
    list_filter = ['chat_type', 'department', 'is_active', 'is_archived', 'created_at']
    search_fields = ['name', 'description', 'department', 'mentorship__program__name']
    readonly_fields = ['created_at', 'updated_at', 'participant_count_display']
    inlines = [GroupChatParticipantInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'chat_type', 'department', 'mentorship')
        }),
        ('Creator', {
            'fields': ('created_by',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_archived')
        }),
        ('Statistics', {
            'fields': ('participant_count_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def participant_count(self, obj):
        """Display participant count in list view"""
        return obj.chat_participants.count()
    participant_count.short_description = 'Participants'
    
    def participant_count_display(self, obj):
        """Display participant count in detail view"""
        return obj.chat_participants.count()
    participant_count_display.short_description = 'Total Participants'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('mentorship', 'created_by')


@admin.register(GroupChatParticipant)
class GroupChatParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'chat_room', 'role', 'added_by', 'joined_at', 'is_muted']
    list_filter = ['role', 'is_muted', 'joined_at', 'chat_room__chat_type']
    search_fields = ['user__full_name', 'chat_room__name', 'user__email']
    list_select_related = ['user', 'chat_room', 'added_by']
    
    fieldsets = (
        ('Participant Information', {
            'fields': ('user', 'chat_room', 'role')
        }),
        ('Management', {
            'fields': ('added_by', 'is_muted')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'last_read_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'chat_room', 'added_by')


@admin.register(GroupChatMessage)
class GroupChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'chat_room', 'message_type', 'content_preview', 'is_edited', 'is_deleted', 'created_at']
    list_filter = ['message_type', 'is_edited', 'is_deleted', 'created_at', 'chat_room__chat_type']
    search_fields = ['content', 'sender__full_name', 'chat_room__name', 'sender__email']
    readonly_fields = ['created_at', 'updated_at', 'edited_at', 'deleted_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'chat_room', 'reply_to')
    
    fieldsets = (
        ('Message Information', {
            'fields': ('sender', 'chat_room', 'message_type', 'content', 'reply_to')
        }),
        ('Attachments', {
            'fields': ('attachment',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_edited', 'edited_at', 'is_deleted', 'deleted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(GroupMessageReadStatus)
class GroupMessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'read_at']
    list_filter = ['read_at', 'message__chat_room__chat_type']
    search_fields = ['message__content', 'user__full_name', 'user__email']
    list_select_related = ['message', 'user']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'user')