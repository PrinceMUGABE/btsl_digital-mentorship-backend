# mentorshipApp/models.py (updated)
from django.db import models
from django.forms import ValidationError
from django.utils.timezone import now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q, Sum
from userApp.models import CustomUser
from departmentApp.models import Department
from django.db.models.functions import Lower


# ==================== SESSION TEMPLATES ====================
class ProgramSessionTemplate(models.Model):
    """Template for program sessions"""
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
    objectives = models.JSONField(default=list)
    requirements = models.JSONField(default=list)
    duration_minutes = models.IntegerField(
        validators=[MinValueValidator(15)],
        help_text="Duration in minutes (minimum 15)"
    )
    order = models.IntegerField(validators=[MinValueValidator(1)])
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Program Session Template'
        verbose_name_plural = 'Program Session Templates'
        constraints = [
            models.UniqueConstraint(
                Lower('title'), 'order',
                name='unique_title_order_case_insensitive'
            )
        ]
    
    def __str__(self):
        return f"{self.order}. {self.title}"


# ==================== MENTORSHIP PROGRAMS ====================
class MentorshipProgram(models.Model):
    """Mentorship programs organized by department"""
    PROGRAM_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='mentorship_programs'
    )
    description = models.TextField()
    status = models.CharField(max_length=20, choices=PROGRAM_STATUS, default='active')
    session_templates = models.ManyToManyField(
        ProgramSessionTemplate,
        related_name='programs'
    )
    total_days = models.IntegerField(default=0, editable=False)
    objectives = models.JSONField(default=list)
    prerequisites = models.JSONField(default=list)
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
        ordering = ['department__name', 'name']
        verbose_name = 'Mentorship Program'
        verbose_name_plural = 'Mentorship Programs'
        unique_together = [['name', 'department']]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.department.name})"
    
    def clean(self):
        """Validate program name uniqueness within department"""
        if MentorshipProgram.objects.filter(
            name__iexact=self.name,
            department=self.department
        ).exclude(id=self.id).exists():
            raise ValidationError(
                f"A program with name '{self.name}' already exists in {self.department.name} department."
            )
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self.calculate_total_days()
    
    def calculate_total_days(self):
        """Calculate total program days based on session durations"""
        total_minutes = self.session_templates.filter(is_active=True).aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        
        # Convert minutes to days (8-hour work days)
        self.total_days = round((total_minutes / 60) / 8)
        MentorshipProgram.objects.filter(id=self.id).update(total_days=self.total_days)
    
    def get_total_sessions(self):
        return self.session_templates.filter(is_active=True).count()
    
    def get_total_duration_hours(self):
        total_minutes = self.session_templates.filter(is_active=True).aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        return round(total_minutes / 60, 2)


# ==================== MENTORSHIPS ====================
class Mentorship(models.Model):
    """Mentorship relationships between mentor and mentee"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core relationships
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
        Department,
        on_delete=models.CASCADE,
        related_name='mentorships'
    )
    
    # Program relationships
    programs = models.ManyToManyField(
        MentorshipProgram,
        related_name='mentorships',
        blank=True
    )
    current_program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_mentorships'
    )
    
    # Status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Progress tracking
    rating = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    goals = models.JSONField(default=list)
    achievements = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
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
            models.Index(fields=['department']),
        ]
    
    def __str__(self):
        return f"{self.mentor.full_name} → {self.mentee.full_name} ({self.department.name})"
    
    def clean(self):
        """Validate mentorship consistency"""
        # Check if mentor has the selected department (ManyToMany relationship)
        if not self.mentor.departments.filter(id=self.department.id).exists():
            raise ValidationError(
                f"Mentor {self.mentor.full_name} must be in the {self.department.name} department"
            )
        
        # Check if mentee belongs to the selected department (ForeignKey relationship)
        if self.mentee.department != self.department:
            raise ValidationError(
                f"Mentee {self.mentee.full_name} must be in the {self.department.name} department"
            )
        
        # Check if current program belongs to the department
        if self.current_program and self.current_program.department != self.department:
            raise ValidationError("Current program must belong to the mentorship department")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_progress_percentage(self):
        """Calculate overall progress percentage"""
        if self.current_program:
            completed_sessions = self.sessions.filter(
                program=self.current_program,
                status='completed'
            ).count()
            total_sessions = self.current_program.get_total_sessions()
            
            if total_sessions > 0:
                return round((completed_sessions / total_sessions) * 100, 2)
        return 0
    
    def get_sessions_completed(self):
        """Get number of completed sessions"""
        if self.current_program:
            return self.sessions.filter(
                program=self.current_program,
                status='completed'
            ).count()
        return 0
    
    def get_total_sessions(self):
        """Get total sessions in current program"""
        if self.current_program:
            return self.current_program.get_total_sessions()
        return 0
# ==================== PROGRAM PROGRESS ====================
class MentorshipProgramProgress(models.Model):
    """Track progress for each program in a mentorship"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    
    mentorship = models.ForeignKey(
        Mentorship,
        on_delete=models.CASCADE,
        related_name='program_progress'
    )
    program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    sessions_completed = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    progress_percentage = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [['mentorship', 'program']]
        ordering = ['program__name']
        verbose_name = 'Program Progress'
        verbose_name_plural = 'Program Progress'
    
    def __str__(self):
        return f"{self.mentorship} - {self.program.name} ({self.progress_percentage}%)"
    
    def update_progress(self):
        """Update progress based on completed sessions"""
        completed = self.mentorship.sessions.filter(
            program=self.program,
            status='completed'
        ).count()
        
        self.sessions_completed = completed
        self.total_sessions = self.program.get_total_sessions()
        
        if self.total_sessions > 0:
            self.progress_percentage = round((completed / self.total_sessions) * 100)
        
        # Update status
        if completed == 0:
            self.status = 'not_started'
        elif completed == self.total_sessions:
            self.status = 'completed'
            self.completed_at = now()
        else:
            self.status = 'in_progress'
            if not self.started_at:
                self.started_at = now()
        
        self.save()


# ==================== MENTORSHIP SESSIONS ====================
class MentorshipSession(models.Model):
    """Individual mentorship sessions"""
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
    program = models.ForeignKey(
        MentorshipProgram,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )
    program_progress = models.ForeignKey(
        MentorshipProgramProgress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions'
    )
    session_template = models.ForeignKey(
        ProgramSessionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mentorship_sessions'
    )
    
    # Session numbers
    program_session_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Session number within this program",
        default=1
    )
    overall_session_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Overall session number across all programs",
        default=1
    )
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='scheduled')
    scheduled_date = models.DateTimeField()
    actual_date = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(
        default=60,
        validators=[MinValueValidator(15)]
    )
    
    # Content
    agenda = models.TextField(blank=True)
    objectives = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    action_items = models.JSONField(default=list)
    
    # Feedback
    mentor_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    mentor_feedback = models.TextField(blank=True)
    mentee_feedback = models.TextField(blank=True)
    
    # Logistics
    meeting_link = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    
    # Metadata
    completed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_sessions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['program_session_number']
        unique_together = [['mentorship', 'program', 'program_session_number']]
        verbose_name = 'Mentorship Session'
        verbose_name_plural = 'Mentorship Sessions'
        indexes = [
            models.Index(fields=['mentorship', 'program', 'status']),
            models.Index(fields=['scheduled_date']),
        ]
    
    def __str__(self):
        return f"Session {self.program_session_number} - {self.program.name if self.program else 'No Program'}"
    
    def save(self, *args, **kwargs):
        """Set program and calculate session numbers"""
        if not self.program and self.mentorship.current_program:
            self.program = self.mentorship.current_program
        
        if not self.program_session_number and self.program:
            # Get next session number for this program
            last_session = MentorshipSession.objects.filter(
                mentorship=self.mentorship,
                program=self.program
            ).order_by('-program_session_number').first()
            
            self.program_session_number = (last_session.program_session_number + 1) if last_session else 1
        
        if not self.overall_session_number:
            # Get overall session number
            last_overall_session = MentorshipSession.objects.filter(
                mentorship=self.mentorship
            ).order_by('-overall_session_number').first()
            
            self.overall_session_number = (last_overall_session.overall_session_number + 1) if last_overall_session else 1
        
        super().save(*args, **kwargs)
    
    
    def mark_completed(self, user, notes="", mentor_feedback="", mentee_feedback=""):
        """Mark session as completed"""
        self.status = 'completed'
        self.actual_date = now()
        self.completed_by = user
        self.notes = notes
        self.mentor_feedback = mentor_feedback
        self.mentee_feedback = mentee_feedback
        self.save()
        
        # Update program progress
        if self.program_progress:
            self.program_progress.update_progress()
    
    def is_upcoming(self):
        """Check if session is upcoming"""
        return self.status == 'scheduled' and self.scheduled_date > now()
    
    def is_past_due(self):
        """Check if session is past due"""
        return self.status == 'scheduled' and self.scheduled_date < now()


# ==================== MENTORSHIP MESSAGES ====================
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


# ==================== MENTORSHIP REVIEWS ====================
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