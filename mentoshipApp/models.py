from django.db import models
from django.forms import ValidationError
from django.utils.timezone import now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q, Sum
from userApp.models import CustomUser
from onboarding.models import OnboardingModule, MenteeOnboardingProgress


class ProgramSessionTemplate(models.Model):
    """Template for program sessions with detailed information"""
    SESSION_TYPE = [
        ('video', 'Video Call'),
        ('in_person', 'In Person'),
        ('phone', 'Phone Call'),
        ('chat', 'Chat'),
        ('workshop', 'Workshop'),
        ('training', 'Training'),
        ('assessment', 'Assessment'),
    ]
    
    title = models.CharField(max_length=200)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE, default='video')
    description = models.TextField()
    objectives = models.JSONField(default=list, help_text="Session objectives/learning outcomes")
    requirements = models.JSONField(default=list, help_text="Session requirements")
    duration_minutes = models.IntegerField(
        validators=[MinValueValidator(15)],
        help_text="Duration in minutes (minimum 15)"
    )
    order = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Session order in the program (1, 2, 3...)"
    )
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Program Session Template'
        verbose_name_plural = 'Program Session Templates'
        unique_together = [['title', 'order']]
    
    def __str__(self):
        return f"{self.order}. {self.title} ({self.duration_minutes} mins)"
    
    def clean(self):
        """Validate session order"""
        if self.order < 1:
            raise ValidationError("Session order must be at least 1")
        
        # Check for duplicate order in active sessions
        if self.is_active and ProgramSessionTemplate.objects.filter(
            order=self.order, is_active=True
        ).exclude(id=self.id).exists():
            raise ValidationError(f"Session with order {self.order} already exists")


class MentorshipProgram(models.Model):
    """Defines different mentorship programs organized by department"""
    PROGRAM_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    department = models.CharField(max_length=100, help_text="Department this program belongs to")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=PROGRAM_STATUS, default='active')
    session_templates = models.ManyToManyField(
        ProgramSessionTemplate,
        related_name='programs',
        help_text="Sessions included in this program"
    )
    total_days = models.IntegerField(
        default=0,
        editable=False,
        help_text="Auto-calculated total days based on session durations"
    )
    objectives = models.JSONField(
        default=list,
        help_text="Overall program objectives"
    )
    prerequisites = models.JSONField(
        default=list,
        help_text="Prerequisites for joining this program"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_programs'
    )
    
    class Meta:
        ordering = ['department', 'name']
        verbose_name = 'Mentorship Program'
        verbose_name_plural = 'Mentorship Programs'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.department.name})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate total_days and validate program name"""
        # Check for duplicate program name
        if MentorshipProgram.objects.filter(
            name__iexact=self.name
        ).exclude(id=self.id).exists():
            raise ValidationError(f"A program with name '{self.name}' already exists.")
        
        super().save(*args, **kwargs)
        self.calculate_total_days()
    
    def calculate_total_days(self):
        """Calculate total days based on session durations"""
        total_minutes = self.session_templates.filter(is_active=True).aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        
        # Convert minutes to days (assuming 8-hour work days)
        # You can adjust this conversion factor as needed
        self.total_days = round((total_minutes / 60) / 8)
        MentorshipProgram.objects.filter(id=self.id).update(total_days=self.total_days)
    
    def get_total_sessions(self):
        """Get total number of active sessions"""
        return self.session_templates.filter(is_active=True).count()
    
    def get_total_duration_hours(self):
        """Get total duration in hours"""
        total_minutes = self.session_templates.filter(is_active=True).aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        return round(total_minutes / 60, 2)
    
    def get_active_mentorships_count(self):
        """Get count of active mentorships in this program"""
        return self.mentorships.filter(status='active').count()
    
    def get_completion_rate(self):
        """Calculate completion rate for this program"""
        total = self.mentorships.count()
        if total == 0:
            return 0
        completed = self.mentorships.filter(status='completed').count()
        return round((completed / total) * 100, 2)
    
    def get_average_rating(self):
        """Get average rating for this program"""
        avg_rating = self.mentorships.filter(
            rating__isnull=False
        ).aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg_rating, 2) if avg_rating else 0


class Mentorship(models.Model):
    """Main mentorship relationship model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    mentor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'mentor'},
        related_name='mentorships_as_mentor'
    )
    mentee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'mentee'},
        related_name='mentorships_as_mentee'
    )
    program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.CASCADE,
        related_name='mentorships'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    start_date = models.DateField()
    expected_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Auto-calculated based on program duration"
    )
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )
    sessions_completed = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Overall mentorship rating (0-5)"
    )
    feedback = models.TextField(
        blank=True,
        null=True,
        help_text="Overall feedback about the mentorship"
    )
    goals = models.JSONField(
        default=list,
        help_text="Mentorship goals set at the beginning"
    )
    achievements = models.JSONField(
        default=list,
        help_text="Goals achieved during mentorship"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal notes about the mentorship"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_mentorships',
        help_text="User who created this mentorship"
    )
    
    class Meta:
        unique_together = [['mentor', 'mentee', 'program']]
        ordering = ['-created_at']
        verbose_name = 'Mentorship'
        verbose_name_plural = 'Mentorships'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['mentor', 'status']),
            models.Index(fields=['mentee', 'status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['program']),
        ]
    
    def __str__(self):
        return f"{self.mentor.full_name} → {self.mentee.full_name} ({self.program.name})"
    
    def save(self, *args, **kwargs):
        """Auto-calculate expected_end_date and auto-complete if all sessions done"""
        from datetime import timedelta
        
        # Calculate expected end date
        if self.start_date and self.program.total_days > 0 and not self.expected_end_date:
            self.expected_end_date = self.start_date + timedelta(days=self.program.total_days)
        
        # Auto-complete if all sessions are done
        total_sessions = self.program.get_total_sessions()
        if self.sessions_completed >= total_sessions and self.status == 'active':
            self.status = 'completed'
            if not self.actual_end_date:
                self.actual_end_date = now().date()
        
        super().save(*args, **kwargs)
    
    def get_progress_percentage(self):
        """Calculate progress percentage based on sessions"""
        total_sessions = self.program.get_total_sessions()
        if total_sessions == 0:
            return 0
        return round((self.sessions_completed / total_sessions) * 100, 2)
    
    def get_remaining_sessions(self):
        """Get number of remaining sessions"""
        total_sessions = self.program.get_total_sessions()
        return max(0, total_sessions - self.sessions_completed)
    
    def mark_session_completed(self):
        """Increment completed sessions and check for completion"""
        self.sessions_completed += 1
        self.save()
    
    def can_schedule_session(self):
        """Check if more sessions can be scheduled"""
        total_sessions = self.program.get_total_sessions()
        return (
            self.status in ['active', 'pending'] and 
            self.sessions_completed < total_sessions
        )
    
    def get_duration_days(self):
        """Get mentorship duration in days"""
        if self.actual_end_date:
            return (self.actual_end_date - self.start_date).days
        return (now().date() - self.start_date).days
    
    def is_overdue(self):
        """Check if mentorship is overdue based on expected end date"""
        if self.expected_end_date and self.status == 'active':
            return now().date() > self.expected_end_date
        return False
    
    def is_completed(self):
        """Check if mentorship is completed (all sessions marked as completed)"""
        total_sessions = self.program.get_total_sessions()
        return self.status == 'completed' or self.sessions_completed >= total_sessions


class MentorshipSession(models.Model):
    """Individual mentorship session based on program session template"""
    SESSION_STATUS = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
        ('no_show', 'No Show'),
    ]
    
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_template = models.ForeignKey(
        ProgramSessionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mentorship_sessions',
        help_text="Session template this session is based on"
    )
    session_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Sequential session number in this mentorship"
    )
    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS,
        default='scheduled'
    )
    scheduled_date = models.DateTimeField()
    actual_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual session date if different from scheduled"
    )
    duration_minutes = models.IntegerField(
        default=60,
        validators=[MinValueValidator(15)],
        help_text="Duration in minutes"
    )
    agenda = models.TextField(
        blank=True,
        help_text="Specific agenda for this session"
    )
    objectives = models.JSONField(
        default=list,
        help_text="Session objectives to cover"
    )
    requirements = models.JSONField(
        default=list,
        help_text="Requirements for this session"
    )
    notes = models.TextField(
        blank=True,
        help_text="Session notes and discussion points"
    )
    action_items = models.JSONField(
        default=list,
        help_text="Action items from the session"
    )
    mentor_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Mentee's rating of the session (1-5)"
    )
    mentor_feedback = models.TextField(
        blank=True,
        help_text="Mentor's feedback about the session"
    )
    mentee_feedback = models.TextField(
        blank=True,
        help_text="Mentee's feedback about the session"
    )
    meeting_link = models.URLField(
        blank=True,
        null=True,
        help_text="Video call link if applicable"
    )
    location = models.CharField(
        max_length=200,
        blank=True,
        help_text="Location for in-person meetings"
    )
    completed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_sessions',
        help_text="User who marked this session as completed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['mentorship', 'session_number']]
        ordering = ['scheduled_date']
        verbose_name = 'Mentorship Session'
        verbose_name_plural = 'Mentorship Sessions'
        indexes = [
            models.Index(fields=['mentorship', 'status']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['status']),
            models.Index(fields=['session_template']),
        ]
    
    def __str__(self):
        template_name = self.session_template.title if self.session_template else "Custom"
        return f"Session {self.session_number}: {template_name} - {self.mentorship}"
    
    def save(self, *args, **kwargs):
        """Auto-update mentorship sessions_completed when marked completed"""
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            old_instance = MentorshipSession.objects.get(pk=self.pk)
            old_status = old_instance.status
        
        # Set duration from template if not specified
        if self.session_template and not self.duration_minutes:
            self.duration_minutes = self.session_template.duration_minutes
        
        # Set objectives and requirements from template if not specified
        if self.session_template and not self.objectives:
            self.objectives = self.session_template.objectives
        
        if self.session_template and not self.requirements:
            self.requirements = self.session_template.requirements
        
        super().save(*args, **kwargs)
        
        # Update mentorship completed sessions count
        if self.status == 'completed' and old_status != 'completed':
            self.mentorship.mark_session_completed()
    
    def mark_completed(self, user, notes='', mentor_feedback='', mentee_feedback=''):
        """Mark session as completed by authorized user"""
        if user.role == 'mentee':
            raise ValidationError("Mentees are not authorized to mark sessions as completed.")
        
        if user.role not in ['admin', 'hr', 'mentor']:
            raise ValidationError("You are not authorized to mark sessions as completed.")
        
        self.status = 'completed'
        self.actual_date = now()
        self.completed_by = user
        
        if notes:
            self.notes = notes
        if mentor_feedback:
            self.mentor_feedback = mentor_feedback
        if mentee_feedback:
            self.mentee_feedback = mentee_feedback
        
        self.save()
    
    def mark_cancelled(self, reason=''):
        """Mark session as cancelled"""
        self.status = 'cancelled'
        if reason:
            self.notes = f"Cancellation reason: {reason}"
        self.save()
    
    def reschedule(self, new_date):
        """Reschedule the session"""
        self.scheduled_date = new_date
        self.status = 'rescheduled'
        self.save()
    
    def is_upcoming(self):
        """Check if session is upcoming"""
        return self.status == 'scheduled' and self.scheduled_date > now()
    
    def is_past_due(self):
        """Check if scheduled session is past due"""
        return self.status == 'scheduled' and self.scheduled_date < now()
    
    def clean(self):
        """Validate session data"""
        super().clean()
        
        # Validate session number doesn't exceed total sessions
        total_sessions = self.mentorship.program.get_total_sessions()
        if self.session_number > total_sessions:
            raise ValidationError(
                f"Session number {self.session_number} exceeds total sessions ({total_sessions}) in program."
            )
        
        if self.status == 'scheduled':
            # Check mentor conflicts
            mentor_conflicts = MentorshipSession.objects.filter(
                Q(mentorship__mentor=self.mentorship.mentor) |
                Q(mentorship__mentee=self.mentorship.mentee),
                status='scheduled',
                scheduled_date__date=self.scheduled_date.date()
            ).exclude(id=self.pk)
            
            # Check for overlapping time
            for conflict in mentor_conflicts:
                time_diff = abs((conflict.scheduled_date - self.scheduled_date).total_seconds() / 3600)
                if time_diff < (self.duration_minutes / 60):  # Sessions overlap
                    raise ValidationError(
                        f"Schedule conflict with existing session at {conflict.scheduled_date}"
                    )
            
            # Check session limit
            completed_sessions = self.mentorship.sessions_completed
            if completed_sessions >= total_sessions:
                raise ValidationError("Maximum sessions reached for this mentorship")


class MentorshipMessage(models.Model):
    """Messages between mentor and mentee"""
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_mentorship_messages'
    )
    message = models.TextField()
    attachments = models.JSONField(
        default=list,
        help_text="List of attachment URLs"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mentorship Message'
        verbose_name_plural = 'Mentorship Messages'
        indexes = [
            models.Index(fields=['mentorship', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.full_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = now()
            self.save()


class MentorshipReview(models.Model):
    """Reviews and ratings for completed mentorships"""
    REVIEWER_TYPE = [
        ('mentor', 'Mentor'),
        ('mentee', 'Mentee'),
    ]
    
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='mentorship_reviews'
    )
    reviewer_type = models.CharField(max_length=10, choices=REVIEWER_TYPE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall rating (1-5)"
    )
    communication_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Communication rating (1-5)"
    )
    knowledge_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Knowledge/expertise rating (1-5)"
    )
    helpfulness_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Helpfulness rating (1-5)"
    )
    review_text = models.TextField()
    would_recommend = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['mentorship', 'reviewer']]
        ordering = ['-created_at']
        verbose_name = 'Mentorship Review'
        verbose_name_plural = 'Mentorship Reviews'
        indexes = [
            models.Index(fields=['mentorship']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"Review by {self.reviewer.full_name} - {self.rating}/5"
    
    def save(self, *args, **kwargs):
        """Update mentorship rating when review is saved"""
        super().save(*args, **kwargs)
        
        # Calculate average rating for the mentorship
        avg_rating = self.mentorship.reviews.aggregate(
            avg_rating=Avg('rating')
        )['avg_rating']
        
        if avg_rating:
            self.mentorship.rating = round(avg_rating, 2)
            self.mentorship.save()
    
    def get_average_rating(self):
        """Calculate average of all rating categories"""
        return round((
            self.rating + 
            self.communication_rating + 
            self.knowledge_rating + 
            self.helpfulness_rating
        ) / 4, 2)
    

class ChatType(models.TextChoices):
    ONE_ON_ONE = 'one_on_one', 'One-on-One Chat'
    MENTORSHIP_GROUP = 'mentorship_group', 'Mentorship Group Chat'
    DEPARTMENT_GROUP = 'department_group', 'Department Group Chat'
    CROSS_DEPARTMENT = 'cross_department', 'Cross-Department Chat'



class GroupChatRoom(models.Model):
    """Group chat room model"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    chat_type = models.CharField(max_length=50, choices=ChatType.choices, default=ChatType.MENTORSHIP_GROUP)
    department = models.CharField(max_length=100, blank=True, null=True)
    mentorship = models.ForeignKey(
        'Mentorship',
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
    # Remove the participants field from here
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Group Chat Room'
        verbose_name_plural = 'Group Chat Rooms'
    
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
        related_name='chat_participants'  # Add related_name
    )
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='group_chat_participations'  # Add related_name
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
        default='mentor_mentee'  # Add default value here
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
    """
    Individual messages in chat rooms
    """
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
    
    def __str__(self):
        return f"Message from {self.sender.full_name} in ChatRoom {self.chat_room.id}"  # Fixed this line
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = now()
            self.save(update_fields=['is_read', 'read_at'])



class MessageReadStatus(models.Model):
    """
    Track read status of messages by users
    """
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
    
    def __str__(self):
        return f"{self.user.full_name} read message at {self.read_at}"  # Fixed this line
    


class ChatNotification(models.Model):
    """
    Notifications for chat events
    """
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('case_assigned', 'Case Assigned'),
        ('case_status_changed', 'Case Status Changed'),
    ]
    
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='chat_notifications'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_chat_notifications',
        null=True,
        blank=True
    )
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chat Notification'
        verbose_name_plural = 'Chat Notifications'
    
    def __str__(self):
        return f"Notification for {self.recipient.full_name}: {self.title}"  # Fixed this line   




