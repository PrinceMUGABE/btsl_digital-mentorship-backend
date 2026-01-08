from django.db import models
from django.forms import ValidationError
from django.utils.timezone import now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q, Sum
from userApp.models import CustomUser


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
        return f"{self.name} ({self.department})"
    
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
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Relationships
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
    department = models.ForeignKey(
        'departmentApp.Department',
        on_delete=models.CASCADE,
        related_name='mentorships',
        default=None
    )
    programs = models.ManyToManyField(
        MentorshipProgram,
        related_name='active_mentorships',
        blank=True
    )
    current_program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_mentorships',
        help_text="Current program being worked on"
    )
    completed_programs = models.ManyToManyField(
        MentorshipProgram,
        related_name='completed_by_mentorships',
        blank=True
    )
    
    # Status and Dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Progress Tracking
    total_sessions_required = models.IntegerField(default=0, editable=False)
    sessions_completed = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Rating and Feedback
    rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    goals = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    feedback = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_mentorships'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['mentor', 'mentee', 'department']]
        ordering = ['-created_at']
        verbose_name = 'Mentorship'
        verbose_name_plural = 'Mentorships'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.mentor.full_name} → {self.mentee.full_name} ({self.department.name})"
    
    # Keep all your existing methods...
    def get_remaining_sessions(self):
        """Get number of remaining sessions"""
        return max(0, self.total_sessions_required - self.sessions_completed)
    
    def get_progress_percentage(self):
        """Calculate overall progress percentage"""
        if self.total_sessions_required == 0:
            return 0
        return round((self.sessions_completed / self.total_sessions_required) * 100, 2)

class MentorshipProgramProgress(models.Model):
    """Track mentee's progress in each program within the department"""
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='program_progress'
    )
    program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.CASCADE,
        related_name='mentee_progress'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('paused', 'Paused'),
        ],
        default='not_started'
    )
    sessions_completed = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    progress_percentage = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [['mentorship', 'program']]
        # FIX: Remove 'program__order' from ordering since we don't know if it exists
        # Use program's natural ordering instead
        ordering = ['program']  # FIXED
        verbose_name = 'Mentorship Program Progress'
        verbose_name_plural = 'Mentorship Program Progress'
        
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
    # Link to the specific program this session belongs to
    program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.CASCADE,
        related_name='sessions',
        default=None
    )
    program_progress = models.ForeignKey(
        MentorshipProgramProgress,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )
    # Keep session template for structure
    session_template = models.ForeignKey(
        ProgramSessionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mentorship_sessions'
    )
    
    # Add program-specific session number
    program_session_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Session number within this program",
        default=1
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


class MentorshipMessage(models.Model):
    """Messages between mentor and mentee (for internal communication, not chat)"""
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='internal_messages'
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_mentorship_messages'
    )
    message = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('note', 'Note'),
            ('update', 'Update'),
            ('reminder', 'Reminder'),
        ],
        default='note'
    )
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