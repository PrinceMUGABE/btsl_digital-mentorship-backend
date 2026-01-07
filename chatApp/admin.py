# mentorshipApp/admin.py - Complete corrected version

from django.contrib import admin
from .models import (
    GroupChatMessage, GroupChatParticipant, GroupChatRoom, GroupMessageReadStatus, 
     Mentorship, ChatRoom, Message, MessageReadStatus
)

from mentoshipApp.models import (
    ProgramSessionTemplate, MentorshipProgram, Mentorship, MentorshipSession,
    MentorshipMessage, MentorshipReview
)

from notificationApp.models import ChatNotification

@admin.register(ProgramSessionTemplate)
class ProgramSessionTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'session_type',
        'order',
        'duration_minutes',
        'is_required',
        'is_active',
        'created_at'
    ]
    list_filter = ['session_type', 'is_required', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['order']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('title', 'session_type', 'description')
        }),
        ('Session Details', {
            'fields': ('order', 'duration_minutes', 'objectives', 'requirements')
        }),
        ('Status', {
            'fields': ('is_required', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(MentorshipProgram)
class MentorshipProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'department',
        'status',
        'get_total_sessions',
        'total_days',
        'created_at',
        'created_by'
    ]
    list_filter = ['status', 'department', 'created_at']
    search_fields = ['name', 'description', 'department__name']
    readonly_fields = ['created_at', 'updated_at', 'total_days']
    filter_horizontal = ['session_templates']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'department', 'description', 'status')
        }),
        ('Program Structure', {
            'fields': ('session_templates', 'total_days', 'objectives', 'prerequisites')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_total_sessions(self, obj):
        return obj.get_total_sessions()
    get_total_sessions.short_description = 'Total Sessions'


class MentorshipSessionInline(admin.TabularInline):
    model = MentorshipSession
    extra = 0
    fields = [
        'session_number',
        'session_template',
        'status',
        'scheduled_date',
        'duration_minutes'
    ]
    readonly_fields = ['session_number']


@admin.register(Mentorship)
class MentorshipAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'mentor',
        'mentee',
        'program',
        'status',
        'start_date',
        'sessions_completed',
        'get_remaining_sessions',
        'rating',
        'created_at'
    ]
    list_filter = ['status', 'program', 'start_date', 'created_at']
    search_fields = [
        'mentor__full_name',
        'mentee__full_name',
        'program__name'
    ]
    readonly_fields = [
        'sessions_completed',
        'expected_end_date',
        'created_at',
        'updated_at',
        'get_progress_percentage',
        'get_remaining_sessions'
    ]
    inlines = [MentorshipSessionInline]
    
    fieldsets = (
        ('Participants', {
            'fields': ('mentor', 'mentee', 'program')
        }),
        ('Status & Progress', {
            'fields': (
                'status',
                'start_date',
                'expected_end_date',
                'actual_end_date',
                'sessions_completed',
                'get_progress_percentage',
                'get_remaining_sessions',
                'rating'
            )
        }),
        ('Goals & Feedback', {
            'fields': ('goals', 'achievements', 'feedback', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_progress_percentage(self, obj):
        return f"{obj.get_progress_percentage()}%"
    get_progress_percentage.short_description = 'Progress'
    
    def get_remaining_sessions(self, obj):
        return obj.get_remaining_sessions()
    get_remaining_sessions.short_description = 'Remaining Sessions'


@admin.register(MentorshipSession)
class MentorshipSessionAdmin(admin.ModelAdmin):
    list_display = [
        'mentorship',
        'session_number',
        'session_template',
        'status',
        'scheduled_date',
        'duration_minutes',
        'mentor_rating',
        'completed_by'
    ]
    list_filter = ['status', 'session_template__session_type', 'scheduled_date']
    search_fields = [
        'mentorship__mentor__full_name',
        'mentorship__mentee__full_name',
        'session_template__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'actual_date', 'completed_by']
    autocomplete_fields = ['session_template']
    
    fieldsets = (
        ('Session Information', {
            'fields': (
                'mentorship',
                'session_number',
                'session_template',
                'status'
            )
        }),
        ('Schedule', {
            'fields': (
                'scheduled_date',
                'actual_date',
                'duration_minutes',
                'meeting_link',
                'location'
            )
        }),
        ('Session Details', {
            'fields': ('agenda', 'objectives', 'requirements', 'notes', 'action_items')
        }),
        ('Feedback & Completion', {
            'fields': (
                'mentor_rating',
                'mentor_feedback',
                'mentee_feedback',
                'completed_by'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(MentorshipMessage)
class MentorshipMessageAdmin(admin.ModelAdmin):
    list_display = [
        'mentorship',
        'sender',
        'created_at',
        'is_read',
        'read_at'
    ]
    list_filter = ['is_read', 'created_at']
    search_fields = [
        'mentorship__mentor__full_name',
        'mentorship__mentee__full_name',
        'sender__full_name',
        'message'
    ]
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('Message Details', {
            'fields': ('mentorship', 'sender', 'message', 'attachments')
        }),
        ('Read Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(MentorshipReview)
class MentorshipReviewAdmin(admin.ModelAdmin):
    list_display = [
        'mentorship',
        'reviewer',
        'reviewer_type',
        'rating',
        'would_recommend',
        'created_at'
    ]
    list_filter = ['reviewer_type', 'rating', 'would_recommend', 'created_at']
    search_fields = [
        'mentorship__mentor__full_name',
        'mentorship__mentee__full_name',
        'reviewer__full_name',
        'review_text'
    ]
    readonly_fields = ['created_at', 'updated_at', 'get_average_rating']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('mentorship', 'reviewer', 'reviewer_type')
        }),
        ('Ratings', {
            'fields': (
                'rating',
                'communication_rating',
                'knowledge_rating',
                'helpfulness_rating',
                'get_average_rating'
            )
        }),
        ('Feedback', {
            'fields': ('review_text', 'would_recommend')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()
    get_average_rating.short_description = 'Average Rating'


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