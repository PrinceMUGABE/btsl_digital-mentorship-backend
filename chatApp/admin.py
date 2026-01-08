# chatApp/admin.py

from django.contrib import admin
from .models import (
    GroupChatMessage, GroupChatParticipant, GroupChatRoom, GroupMessageReadStatus, 
     Mentorship, ChatRoom, Message, MessageReadStatus
)


# from django.contrib import admin
# from django.utils.html import format_html
# from mentoshipApp.models import (
#     ProgramSessionTemplate, MentorshipProgram, Mentorship, MentorshipSession,
#     MentorshipMessage, MentorshipReview
# )

from notificationApp.models import ChatNotification


# @admin.register(ProgramSessionTemplate)
# class ProgramSessionTemplateAdmin(admin.ModelAdmin):
#     list_display = [
#         'title',
#         'session_type',
#         'order',
#         'duration_minutes',
#         'is_required',
#         'is_active',
#         'created_at'
#     ]
#     list_filter = ['session_type', 'is_required', 'is_active', 'created_at']
#     search_fields = ['title', 'description']
#     readonly_fields = ['created_at', 'updated_at']
#     ordering = ['order']
    
#     fieldsets = (
#         ('Session Information', {
#             'fields': ('title', 'session_type', 'description')
#         }),
#         ('Session Details', {
#             'fields': ('order', 'duration_minutes', 'objectives', 'requirements')
#         }),
#         ('Status', {
#             'fields': ('is_required', 'is_active')
#         }),
#         ('Metadata', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )


# @admin.register(MentorshipProgram)
# class MentorshipProgramAdmin(admin.ModelAdmin):
#     list_display = [
#         'name',
#         'department',
#         'status',
#         'total_sessions_count',
#         'total_days',
#         'created_at_display',
#         'created_by_display'
#     ]
#     list_filter = ['status', 'department', 'created_at']
#     search_fields = ['name', 'description', 'department']
#     readonly_fields = ['created_at', 'updated_at', 'total_days', 'total_sessions_count']
#     filter_horizontal = ['session_templates']
    
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('name', 'department', 'description', 'status')
#         }),
#         ('Program Structure', {
#             'fields': ('session_templates', 'total_days', 'objectives', 'prerequisites')
#         }),
#         ('Metadata', {
#             'fields': ('created_by', 'created_at', 'updated_at'),
#             'classes': ('collapse',)
#         })
#     )
    
#     def total_sessions_count(self, obj):
#         return obj.get_total_sessions()
#     total_sessions_count.short_description = 'Total Sessions'
    
#     def created_at_display(self, obj):
#         return obj.created_at.strftime('%Y-%m-%d')
#     created_at_display.short_description = 'Created'
    
#     def created_by_display(self, obj):
#         if obj.created_by:
#             return obj.created_by.full_name
#         return '-'
#     created_by_display.short_description = 'Created By'


# class MentorshipSessionInline(admin.TabularInline):
#     model = MentorshipSession
#     extra = 0
#     fields = [
#         'session_number',
#         'session_template',
#         'status',
#         'scheduled_date',
#         'duration_minutes'
#     ]
#     readonly_fields = ['session_number']
#     can_delete = False
#     show_change_link = True


# @admin.register(Mentorship)
# class MentorshipAdmin(admin.ModelAdmin):
#     list_display = [
#         'id',
#         'mentor_info',
#         'mentee_info',
#         'program_display',
#         'status_display',
#         'start_date_display',
#         'sessions_completed',
#         'remaining_sessions_display',
#         'rating_display',
#         'created_at_display'
#     ]
#     list_filter = ['status', 'program__name', 'start_date']
#     search_fields = [
#         'mentor__full_name',
#         'mentee__full_name',
#         'program__name'
#     ]
#     readonly_fields = [
#         'sessions_completed',
#         'expected_end_date',
#         'progress_percentage',
#         'remaining_sessions',
#         'created_at_display',
#         'updated_at_display'
#     ]
#     inlines = [MentorshipSessionInline]
    
#     fieldsets = (
#         ('Participants', {
#             'fields': ('mentor', 'mentee', 'program')
#         }),
#         ('Status & Progress', {
#             'fields': (
#                 'status',
#                 'start_date',
#                 'expected_end_date',
#                 'actual_end_date',
#                 'sessions_completed',
#                 'progress_percentage',
#                 'remaining_sessions',
#                 'rating'
#             )
#         }),
#         ('Goals & Feedback', {
#             'fields': ('goals', 'achievements', 'feedback', 'notes'),
#             'classes': ('collapse',)
#         }),
#         ('Metadata', {
#             'fields': ('created_by', 'created_at_display', 'updated_at_display'),
#             'classes': ('collapse',)
#         })
#     )
    
#     # Custom display methods for list view
#     def mentor_info(self, obj):
#         return obj.mentor.full_name if obj.mentor else '-'
#     mentor_info.short_description = 'Mentor'
    
#     def mentee_info(self, obj):
#         return obj.mentee.full_name if obj.mentee else '-'
#     mentee_info.short_description = 'Mentee'
    
#     def program_display(self, obj):
#         return obj.program.name if obj.program else '-'
#     program_display.short_description = 'Program'
    
#     def status_display(self, obj):
#         status_colors = {
#             'pending': 'orange',
#             'active': 'green',
#             'completed': 'blue',
#             'paused': 'yellow',
#             'cancelled': 'red'
#         }
#         color = status_colors.get(obj.status, 'gray')
#         return format_html(
#             '<span style="color: {}; font-weight: bold;">{}</span>',
#             color,
#             obj.get_status_display()
#         )
#     status_display.short_description = 'Status'
    
#     def start_date_display(self, obj):
#         return obj.start_date.strftime('%Y-%m-%d') if obj.start_date else '-'
#     start_date_display.short_description = 'Start Date'
    
#     def remaining_sessions_display(self, obj):
#         remaining = obj.get_remaining_sessions()
#         color = 'red' if remaining > 0 else 'green'
#         return format_html(
#             '<span style="color: {}; font-weight: bold;">{}</span>',
#             color,
#             remaining
#         )
#     remaining_sessions_display.short_description = 'Remaining'
    
#     def rating_display(self, obj):
#         if obj.rating:
#             return format_html(
#                 '<span style="color: green; font-weight: bold;">{}/5</span>',
#                 obj.rating
#             )
#         return '-'
#     rating_display.short_description = 'Rating'
    
#     def created_at_display(self, obj):
#         return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
#     created_at_display.short_description = 'Created'
    
#     def updated_at_display(self, obj):
#         return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '-'
#     updated_at_display.short_description = 'Updated'
    
#     # Custom calculated fields for readonly fields
#     def progress_percentage(self, obj):
#         return f"{obj.get_progress_percentage()}%"
#     progress_percentage.short_description = 'Progress %'
    
#     def remaining_sessions(self, obj):
#         return obj.get_remaining_sessions()
#     remaining_sessions.short_description = 'Remaining Sessions'
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'mentor', 'mentee', 'program', 'created_by'
#         )


# @admin.register(MentorshipSession)
# class MentorshipSessionAdmin(admin.ModelAdmin):
#     list_display = [
#         'mentorship_display',
#         'session_number',
#         'session_template_display',
#         'status_display',
#         'scheduled_date_display',
#         'duration_minutes',
#         'mentor_rating_display',
#         'completed_by_display'
#     ]
#     list_filter = ['status', 'scheduled_date']
#     search_fields = [
#         'mentorship__mentor__full_name',
#         'mentorship__mentee__full_name',
#         'session_template__title'
#     ]
#     readonly_fields = [
#         'created_at_display', 
#         'updated_at_display', 
#         'actual_date_display',
#         'completed_by_display'
#     ]
#     autocomplete_fields = ['session_template', 'mentorship']
    
#     fieldsets = (
#         ('Session Information', {
#             'fields': (
#                 'mentorship',
#                 'session_number',
#                 'session_template',
#                 'status'
#             )
#         }),
#         ('Schedule', {
#             'fields': (
#                 'scheduled_date',
#                 'actual_date',
#                 'duration_minutes',
#                 'meeting_link',
#                 'location'
#             )
#         }),
#         ('Session Details', {
#             'fields': ('agenda', 'objectives', 'requirements', 'notes', 'action_items')
#         }),
#         ('Feedback & Completion', {
#             'fields': (
#                 'mentor_rating',
#                 'mentor_feedback',
#                 'mentee_feedback',
#                 'completed_by'
#             ),
#             'classes': ('collapse',)
#         }),
#         ('Metadata', {
#             'fields': ('created_at_display', 'updated_at_display'),
#             'classes': ('collapse',)
#         })
#     )
    
#     # Custom display methods
#     def mentorship_display(self, obj):
#         if obj.mentorship:
#             return f"{obj.mentorship.mentor.full_name} → {obj.mentorship.mentee.full_name}"
#         return '-'
#     mentorship_display.short_description = 'Mentorship'
    
#     def session_template_display(self, obj):
#         return obj.session_template.title if obj.session_template else '-'
#     session_template_display.short_description = 'Template'
    
#     def status_display(self, obj):
#         status_colors = {
#             'scheduled': 'blue',
#             'completed': 'green',
#             'cancelled': 'red',
#             'rescheduled': 'orange',
#             'no_show': 'darkred'
#         }
#         color = status_colors.get(obj.status, 'gray')
#         return format_html(
#             '<span style="color: {}; font-weight: bold;">{}</span>',
#             color,
#             obj.get_status_display()
#         )
#     status_display.short_description = 'Status'
    
#     def scheduled_date_display(self, obj):
#         return obj.scheduled_date.strftime('%Y-%m-%d %H:%M') if obj.scheduled_date else '-'
#     scheduled_date_display.short_description = 'Scheduled'
    
#     def mentor_rating_display(self, obj):
#         if obj.mentor_rating:
#             return format_html(
#                 '<span style="color: green;">{}/5</span>',
#                 obj.mentor_rating
#             )
#         return '-'
#     mentor_rating_display.short_description = 'Rating'
    
#     def completed_by_display(self, obj):
#         return obj.completed_by.full_name if obj.completed_by else '-'
#     completed_by_display.short_description = 'Completed By'
    
#     def created_at_display(self, obj):
#         return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
#     created_at_display.short_description = 'Created'
    
#     def updated_at_display(self, obj):
#         return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '-'
#     updated_at_display.short_description = 'Updated'
    
#     def actual_date_display(self, obj):
#         return obj.actual_date.strftime('%Y-%m-%d %H:%M') if obj.actual_date else '-'
#     actual_date_display.short_description = 'Actual Date'
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'mentorship__mentor',
#             'mentorship__mentee',
#             'session_template',
#             'completed_by'
#         )


# @admin.register(MentorshipMessage)
# class MentorshipMessageAdmin(admin.ModelAdmin):
#     list_display = [
#         'mentorship_display',
#         'sender_display',
#         'message_preview',
#         'created_at_display',
#         'is_read_display',
#         'read_at_display'
#     ]
#     list_filter = ['is_read', 'message_type', 'created_at']
#     search_fields = [
#         'mentorship__mentor__full_name',
#         'mentorship__mentee__full_name',
#         'sender__full_name',
#         'message'
#     ]
#     readonly_fields = ['created_at_display', 'read_at_display']
    
#     fieldsets = (
#         ('Message Details', {
#             'fields': ('mentorship', 'sender', 'message', 'message_type', 'attachments')
#         }),
#         ('Read Status', {
#             'fields': ('is_read', 'read_at')
#         }),
#         ('Metadata', {
#             'fields': ('created_at_display',),
#             'classes': ('collapse',)
#         })
#     )
    
#     # Custom display methods
#     def mentorship_display(self, obj):
#         if obj.mentorship:
#             return f"{obj.mentorship.mentor.full_name} → {obj.mentorship.mentee.full_name}"
#         return '-'
#     mentorship_display.short_description = 'Mentorship'
    
#     def sender_display(self, obj):
#         return obj.sender.full_name if obj.sender else '-'
#     sender_display.short_description = 'Sender'
    
#     def message_preview(self, obj):
#         preview = obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
#         return format_html('<span title="{}">{}</span>', obj.message, preview)
#     message_preview.short_description = 'Message'
    
#     def created_at_display(self, obj):
#         return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
#     created_at_display.short_description = 'Created'
    
#     def is_read_display(self, obj):
#         if obj.is_read:
#             return format_html(
#                 '<span style="color: green; font-weight: bold;">✓</span>'
#             )
#         return format_html(
#             '<span style="color: red; font-weight: bold;">✗</span>'
#         )
#     is_read_display.short_description = 'Read'
    
#     def read_at_display(self, obj):
#         return obj.read_at.strftime('%Y-%m-%d %H:%M') if obj.read_at else '-'
#     read_at_display.short_description = 'Read At'
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'mentorship__mentor',
#             'mentorship__mentee',
#             'sender'
#         )


# @admin.register(MentorshipReview)
# class MentorshipReviewAdmin(admin.ModelAdmin):
#     list_display = [
#         'mentorship_display',
#         'reviewer_display',
#         'reviewer_type_display',
#         'rating_display',
#         'average_rating_display',
#         'would_recommend_display',
#         'created_at_display'
#     ]
#     list_filter = ['reviewer_type', 'rating', 'would_recommend', 'created_at']
#     search_fields = [
#         'mentorship__mentor__full_name',
#         'mentorship__mentee__full_name',
#         'reviewer__full_name',
#         'review_text'
#     ]
#     readonly_fields = [
#         'created_at_display', 
#         'updated_at_display', 
#         'average_rating_display'
#     ]
    
#     fieldsets = (
#         ('Review Information', {
#             'fields': ('mentorship', 'reviewer', 'reviewer_type')
#         }),
#         ('Ratings', {
#             'fields': (
#                 'rating',
#                 'communication_rating',
#                 'knowledge_rating',
#                 'helpfulness_rating',
#                 'average_rating_display'
#             )
#         }),
#         ('Feedback', {
#             'fields': ('review_text', 'would_recommend')
#         }),
#         ('Metadata', {
#             'fields': ('created_at_display', 'updated_at_display'),
#             'classes': ('collapse',)
#         })
#     )
    
#     # Custom display methods
#     def mentorship_display(self, obj):
#         if obj.mentorship:
#             return f"{obj.mentorship.mentor.full_name} → {obj.mentorship.mentee.full_name}"
#         return '-'
#     mentorship_display.short_description = 'Mentorship'
    
#     def reviewer_display(self, obj):
#         return obj.reviewer.full_name if obj.reviewer else '-'
#     reviewer_display.short_description = 'Reviewer'
    
#     def reviewer_type_display(self, obj):
#         colors = {
#             'mentor': 'blue',
#             'mentee': 'green'
#         }
#         color = colors.get(obj.reviewer_type, 'gray')
#         return format_html(
#             '<span style="color: {}; font-weight: bold;">{}</span>',
#             color,
#             obj.get_reviewer_type_display()
#         )
#     reviewer_type_display.short_description = 'Type'
    
#     def rating_display(self, obj):
#         if obj.rating:
#             stars = '★' * obj.rating + '☆' * (5 - obj.rating)
#             return format_html(
#                 '<span style="color: gold; font-size: 14px;">{}</span>',
#                 stars
#             )
#         return '-'
#     rating_display.short_description = 'Rating'
    
#     def average_rating_display(self, obj):
#         avg = obj.get_average_rating()
#         if avg:
#             return format_html(
#                 '<span style="color: green; font-weight: bold;">{:.1f}/5</span>',
#                 avg
#             )
#         return '-'
#     average_rating_display.short_description = 'Avg Rating'
    
#     def would_recommend_display(self, obj):
#         if obj.would_recommend:
#             return format_html(
#                 '<span style="color: green; font-weight: bold;">✓ Yes</span>'
#             )
#         return format_html(
#             '<span style="color: red; font-weight: bold;">✗ No</span>'
#         )
#     would_recommend_display.short_description = 'Recommend'
    
#     def created_at_display(self, obj):
#         return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
#     created_at_display.short_description = 'Created'
    
#     def updated_at_display(self, obj):
#         return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '-'
#     updated_at_display.short_description = 'Updated'
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related(
#             'mentorship__mentor',
#             'mentorship__mentee',
#             'reviewer'
#         )
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