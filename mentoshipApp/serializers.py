# mentorshipApp/serializers.py
from rest_framework import serializers
from django.utils.timezone import now
from datetime import timedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import (
    GroupChatMessage, ProgramSessionTemplate, MentorshipProgram,
    Mentorship, MentorshipSession, MentorshipMessage,
    MentorshipReview, ChatRoom, Message, ChatNotification
)
from userApp.models import CustomUser
from onboarding.models import MenteeOnboardingProgress, OnboardingModule

from .models import Mentorship, GroupChatRoom, GroupChatParticipant, ChatRoom


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


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for mentorship messages"""
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
    
    def validate_attachment(self, value):
        if value:
            max_size = 10 * 1024 * 1024  # 10MB
            if value.size > max_size:
                raise serializers.ValidationError("File size cannot exceed 10MB")
            
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif',
                'application/pdf', 'text/plain',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("File type not allowed")
        return value


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat rooms"""
    mentorship = MentorshipSerializer(read_only=True)
    mentee = UserBasicSerializer(read_only=True)
    mentor = UserBasicSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'mentorship', 'mentee', 'mentor', 'is_active',
            'created_at', 'updated_at', 'last_message', 'unread_count'
        ]
        read_only_fields = fields
    
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


class ChatNotificationSerializer(serializers.ModelSerializer):
    """Serializer for chat notifications"""
    sender = UserBasicSerializer(read_only=True)
    mentorship_id = serializers.IntegerField(source='chat_room.mentorship.id', read_only=True)
    program_name = serializers.CharField(source='chat_room.mentorship.program.name', read_only=True)
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'sender', 'notification_type', 'title', 'message',
            'is_read', 'created_at', 'mentorship_id', 'program_name'
        ]
        read_only_fields = fields





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
    participants = GroupChatParticipantSerializer(many=True, read_only=True, source='groupchatparticipant_set')
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


class GroupChatCreateSerializer(serializers.Serializer):
    """Serializer for creating group chats"""
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    chat_type = serializers.ChoiceField(choices=GroupChatRoom.chat_type.field.choices)
    department = serializers.CharField(required=False, allow_blank=True)
    mentorship_id = serializers.IntegerField(required=False)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[]
    )
    
    def validate(self, data):
        """Validate group chat creation"""
        request = self.context.get('request')
        if not request or request.user.role not in ['admin', 'hr']:
            raise serializers.ValidationError("Only admin and HR can create group chats")
        
        # Validate mentorship exists if provided
        mentorship_id = data.get('mentorship_id')
        if mentorship_id:
            try:
                mentorship = Mentorship.objects.get(id=mentorship_id)
                if mentorship.status != 'active':
                    raise serializers.ValidationError("Mentorship must be active")
            except Mentorship.DoesNotExist:
                raise serializers.ValidationError("Mentorship not found")
        
        return data


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


class GroupMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating group messages"""
    chat_room_id = serializers.IntegerField()
    message_type = serializers.ChoiceField(choices=GroupChatMessage.MESSAGE_TYPES, default='text')
    content = serializers.CharField()
    attachment = serializers.FileField(required=False)
    reply_to_id = serializers.IntegerField(required=False)
    
    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        if len(value) > 5000:
            raise serializers.ValidationError("Message is too long (max 5000 characters)")
        return value
    
    def validate(self, data):
        """Validate group message creation"""
        chat_room_id = data.get('chat_room_id')
        
        try:
            chat_room = GroupChatRoom.objects.get(id=chat_room_id)
        except GroupChatRoom.DoesNotExist:
            raise serializers.ValidationError("Chat room not found")
        
        # Check if user is a participant
        request = self.context.get('request')
        if request and request.user:
            if not chat_room.participants.filter(id=request.user.id).exists():
                raise serializers.ValidationError("You are not a participant in this chat room")
            
            # Check if participant can send messages
            participant = GroupChatParticipant.objects.filter(
                chat_room=chat_room,
                user=request.user
            ).first()
            
            if participant and not participant.can_send_messages():
                raise serializers.ValidationError("You are muted in this chat room")
        
        # Validate reply_to
        reply_to_id = data.get('reply_to_id')
        if reply_to_id:
            try:
                reply_to = GroupChatMessage.objects.get(id=reply_to_id)
                if reply_to.chat_room != chat_room:
                    raise serializers.ValidationError("Cannot reply to message from different chat room")
            except GroupChatMessage.DoesNotExist:
                raise serializers.ValidationError("Reply message not found")
        
        return data


class AddParticipantSerializer(serializers.Serializer):
    """Serializer for adding participants to group chat"""
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=GroupChatParticipant.ROLE_CHOICES, default='member')
    
    def validate_user_id(self, value):
        try:
            user = CustomUser.objects.get(id=value)
            if user.status != 'approved':
                raise serializers.ValidationError("User must be approved")
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value