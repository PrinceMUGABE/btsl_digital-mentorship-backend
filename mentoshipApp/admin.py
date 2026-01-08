# mentorshipApp/admin.py - Complete corrected version

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ProgramSessionTemplate, MentorshipProgram, Mentorship, MentorshipSession,
    MentorshipMessage, MentorshipReview
)


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
        'total_sessions_count',
        'total_days',
        'created_at_display',
        'created_by_display'
    ]
    list_filter = ['status', 'department', 'created_at']
    search_fields = ['name', 'description', 'department']
    readonly_fields = ['created_at', 'updated_at', 'total_days', 'total_sessions_count']
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
    
    def total_sessions_count(self, obj):
        return obj.get_total_sessions()
    total_sessions_count.short_description = 'Total Sessions'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d')
    created_at_display.short_description = 'Created'
    
    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.full_name
        return '-'
    created_by_display.short_description = 'Created By'


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
    can_delete = False
    show_change_link = True

@admin.register(Mentorship)
class MentorshipAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'mentor_info',
        'mentee_info',
        'program_display',
        'status_display',
        'start_date_display',
        'sessions_completed',
        'remaining_sessions_display',
        'rating_display',
        'created_at_display'
    ]
    # FIX: Changed 'program__name' to 'current_program__name'
    list_filter = ['status', 'current_program__name', 'start_date']
    search_fields = [
        'mentor__full_name',
        'mentee__full_name',
        'current_program__name'  # Also fix this search field
    ]
    readonly_fields = [
        'sessions_completed',
        'expected_end_date',
        'progress_percentage',
        'remaining_sessions',
        'created_at_display',
        'updated_at_display'
    ]
    inlines = [MentorshipSessionInline]
    
    fieldsets = (
        ('Participants', {
            'fields': ('mentor', 'mentee', 'current_program')  # Changed 'program' to 'current_program'
        }),
        ('Status & Progress', {
            'fields': (
                'status',
                'start_date',
                'expected_end_date',
                'actual_end_date',
                'sessions_completed',
                'progress_percentage',
                'remaining_sessions',
                'rating'
            )
        }),
        ('Goals & Feedback', {
            'fields': ('goals', 'achievements', 'feedback', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at_display', 'updated_at_display'),
            'classes': ('collapse',)
        })
    )
    
    # Custom display methods for list view
    def mentor_info(self, obj):
        return obj.mentor.full_name if obj.mentor else '-'
    mentor_info.short_description = 'Mentor'
    
    def mentee_info(self, obj):
        return obj.mentee.full_name if obj.mentee else '-'
    mentee_info.short_description = 'Mentee'
    
    def program_display(self, obj):
        # FIX: Changed to current_program
        return obj.current_program.name if obj.current_program else '-'
    program_display.short_description = 'Current Program'
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'active': 'green',
            'completed': 'blue',
            'paused': 'yellow',
            'cancelled': 'red'
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def start_date_display(self, obj):
        return obj.start_date.strftime('%Y-%m-%d') if obj.start_date else '-'
    start_date_display.short_description = 'Start Date'
    
    def remaining_sessions_display(self, obj):
        remaining = obj.get_remaining_sessions()
        color = 'red' if remaining > 0 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            remaining
        )
    remaining_sessions_display.short_description = 'Remaining'
    
    def rating_display(self, obj):
        if obj.rating:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}/5</span>',
                obj.rating
            )
        return '-'
    rating_display.short_description = 'Rating'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
    created_at_display.short_description = 'Created'
    
    def updated_at_display(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '-'
    updated_at_display.short_description = 'Updated'
    
    # Custom calculated fields for readonly fields
    def progress_percentage(self, obj):
        return f"{obj.get_progress_percentage()}%"
    progress_percentage.short_description = 'Progress %'
    
    def remaining_sessions(self, obj):
        return obj.get_remaining_sessions()
    remaining_sessions.short_description = 'Remaining Sessions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mentor', 'mentee', 'current_program', 'created_by'  # Changed 'program' to 'current_program'
        )

@admin.register(MentorshipSession)
class MentorshipSessionAdmin(admin.ModelAdmin):
    list_display = [
        'mentorship_display',
        'session_number',
        'session_template_display',
        'status_display',
        'scheduled_date_display',
        'duration_minutes',
        'mentor_rating_display',
        'completed_by_display'
    ]
    list_filter = ['status', 'scheduled_date']
    search_fields = [
        'mentorship__mentor__full_name',
        'mentorship__mentee__full_name',
        'session_template__title'
    ]
    readonly_fields = [
        'created_at_display', 
        'updated_at_display', 
        'actual_date_display',
        'completed_by_display'
    ]
    autocomplete_fields = ['session_template', 'mentorship']
    
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
            'fields': ('created_at_display', 'updated_at_display'),
            'classes': ('collapse',)
        })
    )
    
    # Custom display methods
    def mentorship_display(self, obj):
        if obj.mentorship:
            return f"{obj.mentorship.mentor.full_name} → {obj.mentorship.mentee.full_name}"
        return '-'
    mentorship_display.short_description = 'Mentorship'
    
    def session_template_display(self, obj):
        return obj.session_template.title if obj.session_template else '-'
    session_template_display.short_description = 'Template'
    
    def status_display(self, obj):
        status_colors = {
            'scheduled': 'blue',
            'completed': 'green',
            'cancelled': 'red',
            'rescheduled': 'orange',
            'no_show': 'darkred'
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def scheduled_date_display(self, obj):
        return obj.scheduled_date.strftime('%Y-%m-%d %H:%M') if obj.scheduled_date else '-'
    scheduled_date_display.short_description = 'Scheduled'
    
    def mentor_rating_display(self, obj):
        if obj.mentor_rating:
            return format_html(
                '<span style="color: green;">{}/5</span>',
                obj.mentor_rating
            )
        return '-'
    mentor_rating_display.short_description = 'Rating'
    
    def completed_by_display(self, obj):
        return obj.completed_by.full_name if obj.completed_by else '-'
    completed_by_display.short_description = 'Completed By'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
    created_at_display.short_description = 'Created'
    
    def updated_at_display(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '-'
    updated_at_display.short_description = 'Updated'
    
    def actual_date_display(self, obj):
        return obj.actual_date.strftime('%Y-%m-%d %H:%M') if obj.actual_date else '-'
    actual_date_display.short_description = 'Actual Date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mentorship__mentor',
            'mentorship__mentee',
            'session_template',
            'completed_by'
        )


@admin.register(MentorshipMessage)
class MentorshipMessageAdmin(admin.ModelAdmin):
    list_display = [
        'mentorship_display',
        'sender_display',
        'message_preview',
        'created_at_display',
        'is_read_display',
        'read_at_display'
    ]
    list_filter = ['is_read', 'message_type', 'created_at']
    search_fields = [
        'mentorship__mentor__full_name',
        'mentorship__mentee__full_name',
        'sender__full_name',
        'message'
    ]
    readonly_fields = ['created_at_display', 'read_at_display']
    
    fieldsets = (
        ('Message Details', {
            'fields': ('mentorship', 'sender', 'message', 'message_type', 'attachments')
        }),
        ('Read Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Metadata', {
            'fields': ('created_at_display',),
            'classes': ('collapse',)
        })
    )
    
    # Custom display methods
    def mentorship_display(self, obj):
        if obj.mentorship:
            return f"{obj.mentorship.mentor.full_name} → {obj.mentorship.mentee.full_name}"
        return '-'
    mentorship_display.short_description = 'Mentorship'
    
    def sender_display(self, obj):
        return obj.sender.full_name if obj.sender else '-'
    sender_display.short_description = 'Sender'
    
    def message_preview(self, obj):
        preview = obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
        return format_html('<span title="{}">{}</span>', obj.message, preview)
    message_preview.short_description = 'Message'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
    created_at_display.short_description = 'Created'
    
    def is_read_display(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗</span>'
        )
    is_read_display.short_description = 'Read'
    
    def read_at_display(self, obj):
        return obj.read_at.strftime('%Y-%m-%d %H:%M') if obj.read_at else '-'
    read_at_display.short_description = 'Read At'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mentorship__mentor',
            'mentorship__mentee',
            'sender'
        )


@admin.register(MentorshipReview)
class MentorshipReviewAdmin(admin.ModelAdmin):
    list_display = [
        'mentorship_display',
        'reviewer_display',
        'reviewer_type_display',
        'rating_display',
        'average_rating_display',
        'would_recommend_display',
        'created_at_display'
    ]
    list_filter = ['reviewer_type', 'rating', 'would_recommend', 'created_at']
    search_fields = [
        'mentorship__mentor__full_name',
        'mentorship__mentee__full_name',
        'reviewer__full_name',
        'review_text'
    ]
    readonly_fields = [
        'created_at_display', 
        'updated_at_display', 
        'average_rating_display'
    ]
    
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
                'average_rating_display'
            )
        }),
        ('Feedback', {
            'fields': ('review_text', 'would_recommend')
        }),
        ('Metadata', {
            'fields': ('created_at_display', 'updated_at_display'),
            'classes': ('collapse',)
        })
    )
    
    # Custom display methods
    def mentorship_display(self, obj):
        if obj.mentorship:
            return f"{obj.mentorship.mentor.full_name} → {obj.mentorship.mentee.full_name}"
        return '-'
    mentorship_display.short_description = 'Mentorship'
    
    def reviewer_display(self, obj):
        return obj.reviewer.full_name if obj.reviewer else '-'
    reviewer_display.short_description = 'Reviewer'
    
    def reviewer_type_display(self, obj):
        colors = {
            'mentor': 'blue',
            'mentee': 'green'
        }
        color = colors.get(obj.reviewer_type, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_reviewer_type_display()
        )
    reviewer_type_display.short_description = 'Type'
    
    def rating_display(self, obj):
        if obj.rating:
            stars = '★' * obj.rating + '☆' * (5 - obj.rating)
            return format_html(
                '<span style="color: gold; font-size: 14px;">{}</span>',
                stars
            )
        return '-'
    rating_display.short_description = 'Rating'
    
    def average_rating_display(self, obj):
        avg = obj.get_average_rating()
        if avg:
            return format_html(
                '<span style="color: green; font-weight: bold;">{:.1f}/5</span>',
                avg
            )
        return '-'
    average_rating_display.short_description = 'Avg Rating'
    
    def would_recommend_display(self, obj):
        if obj.would_recommend:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Yes</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ No</span>'
        )
    would_recommend_display.short_description = 'Recommend'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else '-'
    created_at_display.short_description = 'Created'
    
    def updated_at_display(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M') if obj.updated_at else '-'
    updated_at_display.short_description = 'Updated'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mentorship__mentor',
            'mentorship__mentee',
            'reviewer'
        )