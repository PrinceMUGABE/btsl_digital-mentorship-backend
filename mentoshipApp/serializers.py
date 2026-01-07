# mentorshipApp/serializers.py
from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import (
    ProgramSessionTemplate, MentorshipProgram,
    Mentorship, MentorshipSession, MentorshipMessage,
    MentorshipReview
)
from userApp.models import CustomUser
from onboarding.models import MenteeOnboardingProgress, OnboardingModule


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for mentorship"""
    class Meta:
        model = CustomUser
        fields = ['id', 'phone_number', 'email', 'work_mail_address', 
                 'full_name', 'role', 'department', 'status', 'availability_status']
        read_only_fields = fields



class ProgramSessionTemplateSerializer(serializers.ModelSerializer):
    """Serializer for program session templates"""
    class Meta:
        model = ProgramSessionTemplate
        fields = [
            'id', 'title', 'session_type', 'description', 'objectives',
            'requirements', 'duration_minutes', 'order', 'is_required',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MentorshipProgramSerializer(serializers.ModelSerializer):
    """Serializer for mentorship programs"""
    # REMOVED: department field (using CharField now)
    session_templates = ProgramSessionTemplateSerializer(many=True, read_only=True)
    session_template_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    created_by = UserBasicSerializer(read_only=True)
    total_sessions = serializers.SerializerMethodField()
    total_duration_hours = serializers.SerializerMethodField()
    total_days = serializers.SerializerMethodField()
    active_mentorships = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = MentorshipProgram
        fields = [
            'id', 'name', 'department', 'description',
            'status', 'session_templates', 'session_template_ids',
            'total_days', 'objectives', 'prerequisites', 'created_at',
            'updated_at', 'created_by', 'total_sessions', 'total_duration_hours',
            'active_mentorships', 'completion_rate', 'average_rating'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_days']
    
    def get_total_sessions(self, obj):
        return obj.get_total_sessions()
    
    def get_total_duration_hours(self, obj):
        return obj.get_total_duration_hours()
    
    def get_total_days(self, obj):
        return obj.total_days
    
    def get_active_mentorships(self, obj):
        return obj.get_active_mentorships_count()
    
    def get_completion_rate(self, obj):
        return obj.get_completion_rate()
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()
    
    def validate_name(self, value):
        """Validate program name uniqueness within department"""
        department = self.initial_data.get('department')
        
        if not department:
            raise serializers.ValidationError("Department is required")
        
        # Check if department is valid (from predefined list)
        valid_departments = [
            "Software Development",
            "Frontend Development",
            "Backend Development",
            "Mobile Development",
            "Data Science",
            "Cybersecurity",
            "Cloud & DevOps",
            "UI/UX Design",
            "Project Management",
            "Business Development",
            "HR & Recruitment",
            "Digital Marketing",
            "IT Support",
            "Quality Assurance",
            "Product Management"
        ]
        
        if department not in valid_departments:
            raise serializers.ValidationError(f"Invalid department. Must be one of: {', '.join(valid_departments)}")
        
        # Check for duplicate name in same department
        qs = MentorshipProgram.objects.filter(
            name__iexact=value,
            department=department
        )
        
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        
        if qs.exists():
            raise serializers.ValidationError(
                f"A program with name '{value}' already exists in {department} department."
            )
        
        return value
    
    def validate(self, data):
        """Validate program data"""
        department = data.get('department')
        
        if not department:
            raise serializers.ValidationError("Department is required")
        
        return data


class MentorshipCreateSerializer(serializers.Serializer):
    """Serializer for creating mentorships"""
    mentor_id = serializers.IntegerField()
    mentee_id = serializers.IntegerField()
    program_id = serializers.IntegerField()
    start_date = serializers.DateField()
    goals = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_mentor_id(self, value):
        try:
            mentor = CustomUser.objects.get(id=value, role='mentor')
            if mentor.availability_status != 'active':
                raise serializers.ValidationError("Selected mentor is not available")
            if mentor.status != 'approved':
                raise serializers.ValidationError("Selected mentor is not approved")
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Mentor not found")
        return value
    
    def validate_mentee_id(self, value):
        try:
            mentee = CustomUser.objects.get(id=value, role='mentee')
            if mentee.status != 'approved':
                raise serializers.ValidationError("Selected mentee is not approved")
            
            # Check onboarding completion
            from onboarding.models import OnboardingModule, MenteeOnboardingProgress
            
            # Get all required core modules
            required_core_modules = OnboardingModule.objects.filter(
                module_type='core', 
                is_required=True, 
                is_active=True
            )
            
            incomplete_modules = []
            for module in required_core_modules:
                progress = MenteeOnboardingProgress.objects.filter(
                    mentee=mentee, 
                    module=module
                ).first()
                
                if not progress or progress.status != 'completed':
                    incomplete_modules.append(module.title)
            
            if incomplete_modules:
                raise serializers.ValidationError(
                    f"Mentee must complete onboarding: {', '.join(incomplete_modules)}"
                )
            
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Mentee not found")
        return value
    
    def validate_program_id(self, value):
        try:
            program = MentorshipProgram.objects.get(id=value)
            if program.status != 'active':
                raise serializers.ValidationError("Selected program is not active")
        except MentorshipProgram.DoesNotExist:
            raise serializers.ValidationError("Program not found")
        return value
    
    def validate(self, data):
        """Validate mentorship creation data"""
        program = MentorshipProgram.objects.get(id=data['program_id'])
        mentor = CustomUser.objects.get(id=data['mentor_id'])
        mentee = CustomUser.objects.get(id=data['mentee_id'])
        
        # Check if mentor and mentee are in the same department as program
        if mentor.department != program.department:
            raise serializers.ValidationError(
                f"Mentor must be in the {program.department} department"
            )
        
        if mentee.department != program.department:
            raise serializers.ValidationError(
                f"Mentee must be in the {program.department} department"
            )
        
        # Check for duplicate active mentorship
        if Mentorship.objects.filter(
            mentor_id=data['mentor_id'],
            mentee_id=data['mentee_id'],
            program_id=data['program_id'],
            status__in=['pending', 'active']
        ).exists():
            raise serializers.ValidationError(
                "Active mentorship already exists for this mentor-mentee-program combination"
            )
        
        return data

class MentorshipSerializer(serializers.ModelSerializer):
    """Serializer for mentorships"""
    mentor = UserBasicSerializer(read_only=True)
    mentee = UserBasicSerializer(read_only=True)
    program = MentorshipProgramSerializer(read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    remaining_sessions = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    can_schedule = serializers.SerializerMethodField()
    expected_end_date = serializers.DateField(read_only=True)
    
    class Meta:
        model = Mentorship
        fields = [
            'id', 'mentor', 'mentee', 'program', 'status',
            'start_date', 'expected_end_date', 'actual_end_date',
            'sessions_completed', 'rating', 'feedback', 'goals',
            'achievements', 'notes', 'created_at', 'updated_at',
            'created_by', 'progress_percentage', 'remaining_sessions',
            'duration_days', 'is_overdue', 'can_schedule'
        ]
        read_only_fields = [
            'id', 'sessions_completed', 'created_at', 'updated_at',
            'expected_end_date', 'actual_end_date'
        ]
    
    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()
    
    def get_remaining_sessions(self, obj):
        return obj.get_remaining_sessions()
    
    def get_duration_days(self, obj):
        return obj.get_duration_days()
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()
    
    def get_can_schedule(self, obj):
        return obj.can_schedule_session()


class MentorshipSessionSerializer(serializers.ModelSerializer):
    """Serializer for mentorship sessions"""
    mentorship = MentorshipSerializer(read_only=True)
    session_template = ProgramSessionTemplateSerializer(read_only=True)
    session_template_id = serializers.IntegerField(write_only=True, required=False)
    completed_by = UserBasicSerializer(read_only=True)
    is_upcoming = serializers.SerializerMethodField()
    is_past_due = serializers.SerializerMethodField()
    
    class Meta:
        model = MentorshipSession
        fields = [
            'id', 'mentorship', 'session_template', 'session_template_id',
            'session_number', 'status', 'scheduled_date', 'actual_date',
            'duration_minutes', 'agenda', 'objectives', 'requirements',
            'notes', 'action_items', 'mentor_rating', 'mentor_feedback',
            'mentee_feedback', 'meeting_link', 'location', 'completed_by',
            'created_at', 'updated_at', 'is_upcoming', 'is_past_due'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_by']
    
    def get_is_upcoming(self, obj):
        return obj.is_upcoming()
    
    def get_is_past_due(self, obj):
        return obj.is_past_due()
    
    def validate_session_template_id(self, value):
        """Validate session template exists and is active"""
        try:
            template = ProgramSessionTemplate.objects.get(id=value, is_active=True)
        except ProgramSessionTemplate.DoesNotExist:
            raise serializers.ValidationError("Session template not found or is inactive")
        return value
    
    def validate(self, data):
        """Validate session data"""
        mentorship_id = self.initial_data.get('mentorship_id')
        if not mentorship_id:
            raise serializers.ValidationError("mentorship_id is required")
        
        try:
            mentorship = Mentorship.objects.get(id=mentorship_id)
        except Mentorship.DoesNotExist:
            raise serializers.ValidationError("Mentorship not found")
        
        # Check if user is authorized to create/update session
        request = self.context.get('request')
        if request and request.user:
            if request.user.role == 'mentee':
                raise serializers.ValidationError("Mentees are not authorized to manage sessions")
        
        # Validate session number
        session_number = data.get('session_number')
        total_sessions = mentorship.program.get_total_sessions()
        
        if session_number > total_sessions:
            raise serializers.ValidationError(
                f"Session number exceeds total sessions in program ({total_sessions})"
            )
        
        # Check for duplicate session number
        qs = MentorshipSession.objects.filter(
            mentorship=mentorship,
            session_number=session_number
        )
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(
                f"Session number {session_number} already exists for this mentorship"
            )
        
        return data


class SessionCreateSerializer(serializers.Serializer):
    """Serializer for creating sessions"""
    mentorship_id = serializers.IntegerField()
    session_template_id = serializers.IntegerField(required=False)
    session_number = serializers.IntegerField()
    session_type = serializers.ChoiceField(
        choices=ProgramSessionTemplate.SESSION_TYPE,
        required=False
    )
    scheduled_date = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(required=False)
    agenda = serializers.CharField(required=False, allow_blank=True)
    meeting_link = serializers.URLField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    
    def validate_mentorship_id(self, value):
        try:
            mentorship = Mentorship.objects.get(id=value)
            if not mentorship.can_schedule_session():
                raise serializers.ValidationError(
                    "Cannot schedule more sessions for this mentorship"
                )
        except Mentorship.DoesNotExist:
            raise serializers.ValidationError("Mentorship not found")
        return value
    
    def validate_scheduled_date(self, value):
        if value < now():
            raise serializers.ValidationError("Cannot schedule session in the past")
        return value
    
    def validate_duration_minutes(self, value):
        if value < 15:
            raise serializers.ValidationError("Session must be at least 15 minutes")
        if value > 240:
            raise serializers.ValidationError("Session cannot exceed 4 hours")
        return value
    
    def validate(self, data):
        """Validate session creation data"""
        mentorship = Mentorship.objects.get(id=data['mentorship_id'])
        
        # Check if session template belongs to program
        session_template_id = data.get('session_template_id')
        if session_template_id:
            try:
                template = ProgramSessionTemplate.objects.get(id=session_template_id)
                if not mentorship.program.session_templates.filter(id=template.id).exists():
                    raise serializers.ValidationError(
                        "Session template does not belong to this program"
                    )
            except ProgramSessionTemplate.DoesNotExist:
                raise serializers.ValidationError("Session template not found")
        
        # Validate session number doesn't exceed total sessions
        session_number = data.get('session_number')
        total_sessions = mentorship.program.get_total_sessions()
        
        if session_number > total_sessions:
            raise serializers.ValidationError(
                f"Session number exceeds total sessions in program ({total_sessions})"
            )
        
        # Check for duplicate session number
        if MentorshipSession.objects.filter(
            mentorship=mentorship,
            session_number=session_number
        ).exists():
            raise serializers.ValidationError(
                f"Session number {session_number} already exists for this mentorship"
            )
        
        return data


class SessionCompletionSerializer(serializers.Serializer):
    """Serializer for completing a session"""
    notes = serializers.CharField(required=False, allow_blank=True)
    mentor_feedback = serializers.CharField(required=False, allow_blank=True)
    mentee_feedback = serializers.CharField(required=False, allow_blank=True)
    action_items = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    mentor_rating = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5
    )
    
    def validate(self, data):
        """Validate completion data"""
        # Check if user is authorized
        request = self.context.get('request')
        if not request or request.user.role == 'mentee':
            raise serializers.ValidationError("You are not authorized to mark sessions as completed")
        
        return data


class MentorshipReviewSerializer(serializers.ModelSerializer):
    """Serializer for mentorship reviews"""
    reviewer = UserBasicSerializer(read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = MentorshipReview
        fields = [
            'id', 'mentorship', 'reviewer', 'reviewer_type', 'rating',
            'communication_rating', 'knowledge_rating', 'helpfulness_rating',
            'review_text', 'would_recommend', 'created_at', 'updated_at',
            'average_rating'
        ]
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at']
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()
    
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate(self, data):
        for field in ['communication_rating', 'knowledge_rating', 'helpfulness_rating']:
            if field in data and (data[field] < 1 or data[field] > 5):
                raise serializers.ValidationError(f"{field} must be between 1 and 5")
        return data


