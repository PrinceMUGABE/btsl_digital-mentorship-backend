# mentorshipApp/views.py
from django.forms import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg
from django.utils.timezone import now
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import timedelta
from notificationApp.models import ChatNotification
from chatApp.models import ChatRoom

from .models import (
    MentorshipProgram, Mentorship, MentorshipSession,
    MentorshipMessage, MentorshipReview,
    ProgramSessionTemplate
)
from .serializers import (
     MentorshipProgramSerializer, MentorshipSerializer,
    MentorshipSessionSerializer,
    SessionCreateSerializer,
    MentorshipReviewSerializer, ProgramSessionTemplateSerializer,
      SessionCompletionSerializer, MentorshipSessionSerializer, MentorshipCreateSerializer
    
)
from userApp.models import CustomUser



DEPARTMENTS = [
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_departments(request):
    """Get list of all departments"""
    try:
        return Response({
            'success': True,
            'departments': DEPARTMENTS
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Failed to fetch departments',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_programs(request, department):
    """Get all programs for a specific department"""
    try:
        if department not in DEPARTMENTS:
            return Response({
                'error': f'Invalid department. Must be one of: {", ".join(DEPARTMENTS)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        # Check if user has access to this department
        if user.role in ['mentor', 'mentee'] and user.department != department:
            return Response({
                'error': 'Permission denied. You can only view programs in your department'
            }, status=status.HTTP_403_FORBIDDEN)
        
        programs = MentorshipProgram.objects.filter(
            department=department,
            status='active'
        )
        
        serializer = MentorshipProgramSerializer(programs, many=True)
        
        return Response({
            'success': True,
            'department': department,
            'count': programs.count(),
            'programs': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Failed to fetch department programs',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_mentors(request):
    """Get available mentors for a department"""
    try:
        department = request.query_params.get('department')
        program_id = request.query_params.get('program_id')
        
        if not department:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if department not in DEPARTMENTS:
            return Response({
                'error': f'Invalid department. Must be one of: {", ".join(DEPARTMENTS)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get available mentors in the department
        mentors = CustomUser.objects.filter(
            role='mentor',
            department=department,
            status='approved',
            availability_status='active'
        ).select_related('profile')
        
        mentor_data = []
        for mentor in mentors:
            # Get mentor's current workload
            active_mentorships = Mentorship.objects.filter(
                mentor=mentor,
                status='active'
            ).count()
            
            # Get mentor's specialization programs
            if program_id:
                try:
                    program = MentorshipProgram.objects.get(id=program_id)
                    # Check if mentor is already assigned to this program
                    has_program = Mentorship.objects.filter(
                        mentor=mentor,
                        program=program,
                        status='active'
                    ).exists()
                except MentorshipProgram.DoesNotExist:
                    has_program = False
            else:
                has_program = None
            
            mentor_data.append({
                'id': mentor.id,
                'full_name': mentor.full_name,
                'email': mentor.email,
                'department': mentor.department,
                'availability_status': mentor.availability_status,
                'active_mentorships': active_mentorships,
                'has_program': has_program if program_id else None,
                'expertise': mentor.profile.expertise if hasattr(mentor, 'profile') else []
            })
        
        return Response({
            'success': True,
            'department': department,
            'mentors': mentor_data,
            'count': len(mentor_data)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Failed to fetch available mentors',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentees_ready_for_mentorship(request):
    """Get mentees who have completed onboarding and are ready for mentorship"""
    try:
        department = request.query_params.get('department')
        
        if not department:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if department not in DEPARTMENTS:
            return Response({
                'error': f'Invalid department. Must be one of: {", ".join(DEPARTMENTS)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from onboarding.models import OnboardingModule, MenteeOnboardingProgress
        
        # Get all mentees in the department
        mentees = CustomUser.objects.filter(
            role='mentee',
            department=department,
            status='approved'
        )
        
        ready_mentees = []
        for mentee in mentees:
            # Check if mentee has completed all required core modules
            required_core_modules = OnboardingModule.objects.filter(
                module_type='core',
                is_required=True,
                is_active=True
            )
            
            completed_all = True
            for module in required_core_modules:
                progress = MenteeOnboardingProgress.objects.filter(
                    mentee=mentee,
                    module=module
                ).first()
                
                if not progress or progress.status != 'completed':
                    completed_all = False
                    break
            
            if completed_all:
                # Check if mentee already has active mentorship
                has_active_mentorship = Mentorship.objects.filter(
                    mentee=mentee,
                    status__in=['pending', 'active']
                ).exists()
                
                ready_mentees.append({
                    'id': mentee.id,
                    'full_name': mentee.full_name,
                    'email': mentee.email,
                    'department': mentee.department,
                    'onboarding_completed': completed_all,
                    'has_active_mentorship': has_active_mentorship,
                    'last_active': mentee.last_login
                })
        
        return Response({
            'success': True,
            'department': department,
            'mentees': ready_mentees,
            'count': len(ready_mentees)
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Failed to fetch mentees ready for mentorship',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_mentorship_program(request):
    """Create a new mentorship program (Admin/HR only)"""
    try:
        if request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can create programs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = MentorshipProgramSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        program = serializer.save(created_by=request.user)
        
        return Response({
            'success': True,
            'message': 'Mentorship program created successfully',
            'program': MentorshipProgramSerializer(program).data
        }, status=status.HTTP_201_CREATED)
    
    except ValidationError as e:
        return Response({
            'error': 'Validation failed',
            'detail': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Failed to create program',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_mentorship(request):
    """Create a new mentorship (Admin/HR only)"""
    try:
        if request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can create mentorships'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = MentorshipCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Create mentorship
        mentorship = Mentorship.objects.create(
            mentor_id=data['mentor_id'],
            mentee_id=data['mentee_id'],
            program_id=data['program_id'],
            start_date=data['start_date'],
            goals=data.get('goals', []),
            notes=data.get('notes', ''),
            status='active',  # Start immediately
            created_by=request.user
        )
        
        # Create chat room automatically
        chat_room = ChatRoom.objects.create(
            mentorship=mentorship,
            is_active=True
        )
        
        # Send email notifications
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Email to mentee
        mentee_subject = f"You have been assigned a mentor for {mentorship.program.name}"
        mentee_message = f"""
        Hello {mentorship.mentee.full_name},
        
        You have been assigned a mentor for the {mentorship.program.name} program.
        
        Your Mentor: {mentorship.mentor.full_name}
        Program: {mentorship.program.name}
        Department: {mentorship.program.department}
        Start Date: {mentorship.start_date}
        
        You can now communicate with your mentor through the mentorship portal.
        
        Best regards,
        Mentorship Program Team
        """
        
        send_mail(
            subject=mentee_subject,
            message=mentee_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[mentorship.mentee.email],
            fail_silently=True,
        )
        
        # Email to mentor
        mentor_subject = f"New mentee assigned: {mentorship.mentee.full_name}"
        mentor_message = f"""
        Hello {mentorship.mentor.full_name},
        
        A new mentee has been assigned to you.
        
        Mentee: {mentorship.mentee.full_name}
        Program: {mentorship.program.name}
        Department: {mentorship.program.department}
        Start Date: {mentorship.start_date}
        Mentee's Goals: {', '.join(mentorship.goals) if mentorship.goals else 'Not specified'}
        
        Please connect with your mentee and start the mentorship program.
        
        Best regards,
        Mentorship Program Team
        """
        
        send_mail(
            subject=mentor_subject,
            message=mentor_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[mentorship.mentor.email],
            fail_silently=True,
        )
        
        # Create chat notifications
        ChatNotification.objects.create(
            recipient=mentorship.mentee,
            chat_room=chat_room,
            notification_type='case_assigned',
            title='New Mentor Assigned',
            message=f'You have been assigned {mentorship.mentor.full_name} as your mentor'
        )
        
        ChatNotification.objects.create(
            recipient=mentorship.mentor,
            chat_room=chat_room,
            notification_type='case_assigned',
            title='New Mentee Assigned',
            message=f'You have been assigned {mentorship.mentee.full_name} as your mentee'
        )
        
        return Response({
            'success': True,
            'message': 'Mentorship created successfully',
            'mentorship': MentorshipSerializer(mentorship).data,
            'chat_room_id': chat_room.id
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to create mentorship',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_session_templates(request):
    """List all session templates"""
    try:
        templates = ProgramSessionTemplate.objects.filter(is_active=True)
        serializer = ProgramSessionTemplateSerializer(templates, many=True)
        return Response({
            'success': True,
            'count': templates.count(),
            'templates': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Failed to fetch session templates',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_template(request, template_id):
    """Get single session template details"""
    try:
        template = get_object_or_404(ProgramSessionTemplate, id=template_id, is_active=True)
        serializer = ProgramSessionTemplateSerializer(template)
        return Response({
            'success': True,
            'template': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Session template not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)
    



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_session(request):
    """Create a new session"""
    try:
        serializer = MentorshipSessionSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        mentorship = get_object_or_404(Mentorship, id=request.data.get('mentorship_id'))
        
        # Check permissions
        if request.user not in [mentorship.mentor, mentorship.mentee] and request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only participants, Admin, or HR can schedule sessions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check for scheduling conflicts
        conflicts = MentorshipSession.objects.filter(
            Q(mentorship__mentor=mentorship.mentor) | Q(mentorship__mentee=mentorship.mentee),
            status='scheduled',
            scheduled_date__date=data['scheduled_date'].date()
        )
        
        for conflict in conflicts:
            time_diff = abs((conflict.scheduled_date - data['scheduled_date']).total_seconds() / 3600)
            if time_diff < (data.get('duration_minutes', 60) / 60):
                return Response({
                    'error': 'Scheduling conflict detected',
                    'message': f'There is another session scheduled at {conflict.scheduled_date}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create session
        session = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Session created successfully',
            'session': MentorshipSessionSerializer(session).data
        }, status=status.HTTP_201_CREATED)
    
    except ValidationError as e:
        return Response({
            'error': 'Validation failed',
            'detail': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Failed to create session',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_session_completed(request, session_id):
    """Mark a session as completed"""
    try:
        session = get_object_or_404(MentorshipSession, id=session_id)
        
        # Check if user is authorized (mentee cannot mark as completed)
        if request.user.role == 'mentee':
            return Response({
                'error': 'Permission denied. Mentees cannot mark sessions as completed'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SessionCompletionSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Mark session as completed
        session.mark_completed(
            user=request.user,
            notes=data.get('notes', ''),
            mentor_feedback=data.get('mentor_feedback', ''),
            mentee_feedback=data.get('mentee_feedback', '')
        )
        
        # Update additional fields
        if 'action_items' in data:
            session.action_items = data['action_items']
        if 'mentor_rating' in data:
            session.mentor_rating = data['mentor_rating']
        
        session.save()
        
        # Check if mentorship is now completed
        if session.mentorship.is_completed():
            session.mentorship.status = 'completed'
            session.mentorship.actual_end_date = now().date()
            session.mentorship.save()
            
            # Send notification
            if hasattr(session.mentorship, 'chat_room'):
                ChatNotification.objects.create(
                    recipient=session.mentorship.mentee,
                    chat_room=session.mentorship.chat_room,
                    notification_type='case_status_changed',
                    title='Mentorship Completed',
                    message=f'Congratulations! You have completed the {session.mentorship.program.name} program'
                )
                
                ChatNotification.objects.create(
                    recipient=session.mentorship.mentor,
                    chat_room=session.mentorship.chat_room,
                    notification_type='case_status_changed',
                    title='Mentorship Completed',
                    message=f'You have successfully completed mentoring {session.mentorship.mentee.full_name}'
                )
        
        return Response({
            'success': True,
            'message': 'Session marked as completed',
            'session': MentorshipSessionSerializer(session).data
        }, status=status.HTTP_200_OK)
    
    except ValidationError as e:
        return Response({
            'error': str(e),
            'detail': 'Failed to mark session as completed'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Failed to mark session as completed',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_program_sessions(request, program_id):
    """Get all session templates for a program"""
    try:
        program = get_object_or_404(MentorshipProgram, id=program_id)
        
        # Check permissions based on user role
        user = request.user
        if user.role == 'mentee':
            # Mentees can only see programs in their department
            if user.department != program.department:
                return Response({
                    'error': 'Permission denied. You can only view programs in your department'
                }, status=status.HTTP_403_FORBIDDEN)
        
        session_templates = program.session_templates.filter(is_active=True).order_by('order')
        serializer = ProgramSessionTemplateSerializer(session_templates, many=True)
        
        program_data = {
            'id': program.id,
            'name': program.name,
            'department': program.department.name,
            'total_sessions': program.get_total_sessions(),
            'total_duration_hours': program.get_total_duration_hours(),
            'total_days': program.total_days,
            'sessions': serializer.data
        }
        
        return Response({
            'success': True,
            'program': program_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch program sessions',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_session_template(request):
    """Create a new session template (Admin/HR only)"""
    try:
        if request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can create session templates'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProgramSessionTemplateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session_template = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Session template created successfully',
            'session_template': ProgramSessionTemplateSerializer(session_template).data
        }, status=status.HTTP_201_CREATED)
    
    except ValidationError as e:
        return Response({
            'error': 'Validation failed',
            'detail': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': 'Failed to create session template',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentorship_progress(request, mentorship_id):
    """Get detailed progress of a mentorship"""
    try:
        mentorship = get_object_or_404(Mentorship, id=mentorship_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentor' and mentorship.mentor != user:
            return Response({
                'error': 'Permission denied. You can only view your own mentorships'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentee' and mentorship.mentee != user:
            return Response({
                'error': 'Permission denied. You can only view your own mentorships'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all session templates for the program
        session_templates = mentorship.program.session_templates.filter(is_active=True).order_by('order')
        
        # Get completed sessions
        completed_sessions = mentorship.sessions.filter(status='completed')
        completed_session_numbers = [s.session_number for s in completed_sessions]
        
        progress_data = []
        for template in session_templates:
            session = mentorship.sessions.filter(session_template=template).first()
            
            progress_data.append({
                'session_number': template.order,
                'template_id': template.id,
                'title': template.title,
                'description': template.description,
                'objectives': template.objectives,
                'requirements': template.requirements,
                'duration_minutes': template.duration_minutes,
                'is_required': template.is_required,
                'status': 'completed' if template.order in completed_session_numbers else 'pending',
                'scheduled_date': session.scheduled_date if session else None,
                'completed_date': session.actual_date if session and session.status == 'completed' else None,
                'completed_by': {
                    'id': session.completed_by.id,
                    'name': session.completed_by.full_name
                } if session and session.completed_by else None
            })
        
        return Response({
            'success': True,
            'mentorship': {
                'id': mentorship.id,
                'program': mentorship.program.name,
                'mentor': mentorship.mentor.full_name,
                'mentee': mentorship.mentee.full_name,
                'status': mentorship.status,
                'progress_percentage': mentorship.get_progress_percentage(),
                'sessions_completed': mentorship.sessions_completed,
                'total_sessions': mentorship.program.get_total_sessions(),
                'remaining_sessions': mentorship.get_remaining_sessions(),
                'start_date': mentorship.start_date,
                'expected_end_date': mentorship.expected_end_date,
                'actual_end_date': mentorship.actual_end_date,
                'is_overdue': mentorship.is_overdue(),
                'can_schedule': mentorship.can_schedule_session()
            },
            'sessions': progress_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch mentorship progress',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_mentorship_programs(request):
    """List all mentorship programs"""
    try:
        status_filter = request.query_params.get('status', None)
        
        programs = MentorshipProgram.objects.all()
        
        if status_filter:
            if status_filter not in ['active', 'inactive', 'archived']:
                return Response({
                    'error': 'Invalid status filter. Must be: active, inactive, or archived'
                }, status=status.HTTP_400_BAD_REQUEST)
            programs = programs.filter(status=status_filter)
        
        # Admin and HR see all, others see only active
        if request.user.role not in ['admin', 'hr']:
            programs = programs.filter(status='active')
        
        serializer = MentorshipProgramSerializer(programs, many=True)
        return Response({
            'success': True,
            'count': programs.count(),
            'programs': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching programs',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentorship_program(request, program_id):
    """Get single mentorship program details"""
    try:
        program = get_object_or_404(MentorshipProgram, id=program_id)
        
        serializer = MentorshipProgramSerializer(program)
        return Response({
            'success': True,
            'program': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Program not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)



@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_mentorship_program(request, program_id):
    """Update mentorship program (Admin/HR only)"""
    try:
        if request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can update programs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        program = get_object_or_404(MentorshipProgram, id=program_id)
        
        partial = request.method == 'PATCH'
        serializer = MentorshipProgramSerializer(
            program, data=request.data, partial=partial
        )
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        program = serializer.save()
        
        return Response({
            'success': True,
            'message': 'Program updated successfully',
            'program': MentorshipProgramSerializer(program).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to update program',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_mentorship_program(request, program_id):
    """Archive mentorship program (Admin only)"""
    try:
        if request.user.role != 'admin':
            return Response({
                'error': 'Permission denied. Only Admin can archive programs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        program = get_object_or_404(MentorshipProgram, id=program_id)
        
        # Check if program has active mentorships
        if program.mentorships.filter(status='active').exists():
            return Response({
                'error': 'Cannot archive program with active mentorships',
                'message': 'Please complete or cancel all active mentorships first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        program.status = 'archived'
        program.save()
        
        return Response({
            'success': True,
            'message': 'Program archived successfully'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to archive program',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== MENTORSHIP VIEWS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_mentorships(request):
    """List mentorships based on user role"""
    try:
        user = request.user
        status_filter = request.query_params.get('status', None)
        program_filter = request.query_params.get('program', None)
        
        # Base queryset based on role
        if user.role == 'mentor':
            mentorships = Mentorship.objects.filter(mentor=user)
        elif user.role == 'mentee':
            mentorships = Mentorship.objects.filter(mentee=user)
        elif user.role in ['admin', 'hr']:
            mentorships = Mentorship.objects.all()
        else:
            return Response({
                'error': 'Invalid user role'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Apply filters
        if status_filter:
            if status_filter not in dict(Mentorship.STATUS_CHOICES).keys():
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(dict(Mentorship.STATUS_CHOICES).keys())}'
                }, status=status.HTTP_400_BAD_REQUEST)
            mentorships = mentorships.filter(status=status_filter)
        
        if program_filter:
            try:
                mentorships = mentorships.filter(program_id=int(program_filter))
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid program ID'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        mentorships = mentorships.select_related('mentor', 'mentee', 'program', 'created_by')
        
        serializer = MentorshipSerializer(mentorships, many=True)
        return Response({
            'success': True,
            'count': mentorships.count(),
            'mentorships': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching mentorships',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentorship(request, mentorship_id):
    """Get single mentorship details"""
    try:
        mentorship = get_object_or_404(Mentorship, id=mentorship_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentor' and mentorship.mentor != user:
            return Response({
                'error': 'Permission denied. You can only view your own mentorships'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentee' and mentorship.mentee != user:
            return Response({
                'error': 'Permission denied. You can only view your own mentorships'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role not in ['admin', 'hr', 'mentor', 'mentee']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = MentorshipSerializer(mentorship)
        return Response({
            'success': True,
            'mentorship': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Mentorship not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)




@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_mentorship_status(request, mentorship_id):
    """Update mentorship status"""
    try:
        mentorship = get_object_or_404(Mentorship, id=mentorship_id)
        user = request.user
        
        # Check permissions
        if user.role not in ['admin', 'hr'] and mentorship.mentor != user:
            return Response({
                'error': 'Permission denied. Only Admin, HR, or assigned mentor can update status'
            }, status=status.HTTP_403_FORBIDDEN)
        
        new_status = request.data.get('status')
        if not new_status:
            return Response({
                'error': 'Status is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in dict(Mentorship.STATUS_CHOICES).keys():
            return Response({
                'error': f'Invalid status. Must be one of: {", ".join(dict(Mentorship.STATUS_CHOICES).keys())}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = mentorship.status
        mentorship.status = new_status
        
        if new_status == 'active' and old_status == 'pending':
            mentorship.start_date = now().date()
        
        if new_status == 'completed':
            mentorship.end_date = now().date()
        
        mentorship.save()
        
        # Send notification
        if hasattr(mentorship, 'chat_room'):
            status_display = dict(Mentorship.STATUS_CHOICES).get(new_status, new_status)
            ChatNotification.objects.create(
                recipient=mentorship.mentee,
                chat_room=mentorship.chat_room,
                notification_type='case_status_changed',
                title='Mentorship Status Updated',
                message=f'Your mentorship status has been changed to: {status_display}'
            )
        
        return Response({
            'success': True,
            'message': 'Status updated successfully',
            'mentorship': MentorshipSerializer(mentorship).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to update status',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def add_mentorship_goals(request, mentorship_id):
    """Add or update mentorship goals"""
    try:
        mentorship = get_object_or_404(Mentorship, id=mentorship_id)
        user = request.user
        
        # Only mentor, mentee, admin, or HR can update goals
        if user not in [mentorship.mentor, mentorship.mentee] and user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        goals = request.data.get('goals')
        if not goals or not isinstance(goals, list):
            return Response({
                'error': 'Goals must be provided as a list'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        mentorship.goals = goals
        mentorship.save()
        
        return Response({
            'success': True,
            'message': 'Goals updated successfully',
            'goals': mentorship.goals
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to update goals',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== SESSION VIEWS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """List sessions based on filters"""
    try:
        user = request.user
        mentorship_id = request.query_params.get('mentorship')
        status_filter = request.query_params.get('status')
        
        # Base queryset based on role
        if user.role == 'mentor':
            sessions = MentorshipSession.objects.filter(mentorship__mentor=user)
        elif user.role == 'mentee':
            sessions = MentorshipSession.objects.filter(mentorship__mentee=user)
        elif user.role in ['admin', 'hr']:
            sessions = MentorshipSession.objects.all()
        else:
            return Response({
                'error': 'Invalid user role'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Apply filters
        if mentorship_id:
            try:
                sessions = sessions.filter(mentorship_id=int(mentorship_id))
            except (ValueError, TypeError):
                return Response({
                    'error': 'Invalid mentorship ID'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if status_filter:
            if status_filter not in dict(MentorshipSession.SESSION_STATUS).keys():
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(dict(MentorshipSession.SESSION_STATUS).keys())}'
                }, status=status.HTTP_400_BAD_REQUEST)
            sessions = sessions.filter(status=status_filter)
        
        sessions = sessions.select_related('mentorship__mentor', 'mentorship__mentee', 'mentorship__program')
        serializer = MentorshipSessionSerializer(sessions, many=True)
        
        return Response({
            'success': True,
            'count': sessions.count(),
            'sessions': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching sessions',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session(request, session_id):
    """Get single session details"""
    try:
        session = get_object_or_404(MentorshipSession, id=session_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentor' and session.mentorship.mentor != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentee' and session.mentorship.mentee != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role not in ['admin', 'hr', 'mentor', 'mentee']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = MentorshipSessionSerializer(session)
        return Response({
            'success': True,
            'session': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Session not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_session(request):
    """Create a new session"""
    try:
        serializer = SessionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        mentorship = get_object_or_404(Mentorship, id=data['mentorship_id'])
        user = request.user
        
        # Check permissions
        if user not in [mentorship.mentor, mentorship.mentee] and user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only participants, Admin, or HR can schedule sessions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get next session number
        last_session = mentorship.sessions.order_by('-session_number').first()
        session_number = (last_session.session_number + 1) if last_session else 1
        
        # Check for scheduling conflicts
        conflicts = MentorshipSession.objects.filter(
            Q(mentorship__mentor=mentorship.mentor) | Q(mentorship__mentee=mentorship.mentee),
            status='scheduled',
            scheduled_date__date=data['scheduled_date'].date()
        )
        
        for conflict in conflicts:
            time_diff = abs((conflict.scheduled_date - data['scheduled_date']).total_seconds() / 3600)
            if time_diff < 1:
                return Response({
                    'error': 'Scheduling conflict detected',
                    'message': f'There is another session scheduled at {conflict.scheduled_date}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create session
        session = MentorshipSession.objects.create(
            mentorship=mentorship,
            session_number=session_number,
            session_type=data['session_type'],
            scheduled_date=data['scheduled_date'],
            duration_minutes=data['duration_minutes'],
            agenda=data.get('agenda', ''),
            meeting_link=data.get('meeting_link', ''),
            location=data.get('location', ''),
            status='scheduled'
        )
        
        # Send notifications
        if hasattr(mentorship, 'chat_room'):
            ChatNotification.objects.create(
                recipient=mentorship.mentee,
                chat_room=mentorship.chat_room,
                notification_type='module_assigned',
                title='New Session Scheduled',
                message=f'Session {session_number} has been scheduled for {data["scheduled_date"].strftime("%Y-%m-%d %H:%M")}'
            )
            
            ChatNotification.objects.create(
                recipient=mentorship.mentor,
                chat_room=mentorship.chat_room,
                notification_type='module_assigned',
                title='New Session Scheduled',
                message=f'Session {session_number} has been scheduled for {data["scheduled_date"].strftime("%Y-%m-%d %H:%M")}'
            )
        
        return Response({
            'success': True,
            'message': 'Session created successfully',
            'session': MentorshipSessionSerializer(session).data
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to create session',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mark_session_completed(request, session_id):
    """Mark a session as completed"""
    try:
        session = get_object_or_404(MentorshipSession, id=session_id)
        user = request.user
        
        # Check permissions
        if user not in [session.mentorship.mentor, session.mentorship.mentee] and user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if session.status == 'completed':
            return Response({
                'error': 'Session is already marked as completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        notes = request.data.get('notes', '')
        mentor_feedback = request.data.get('mentor_feedback', '')
        mentee_feedback = request.data.get('mentee_feedback', '')
        action_items = request.data.get('action_items', [])
        
        session.mark_completed(notes, mentor_feedback, mentee_feedback)
        
        if action_items:
            session.action_items = action_items
            session.save()
        
        return Response({
            'success': True,
            'message': 'Session marked as completed',
            'session': MentorshipSessionSerializer(session).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to mark session as completed',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def reschedule_session(request, session_id):
    """Reschedule a session"""
    try:
        session = get_object_or_404(MentorshipSession, id=session_id)
        user = request.user
        
        # Check permissions
        if user not in [session.mentorship.mentor, session.mentorship.mentee] and user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if session.status != 'scheduled':
            return Response({
                'error': 'Can only reschedule sessions with scheduled status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        new_date = request.data.get('new_date')
        if not new_date:
            return Response({
                'error': 'New date is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from datetime import datetime
        try:
            new_date = datetime.fromisoformat(new_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return Response({
                'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_date < now():
            return Response({
                'error': 'Cannot reschedule to a past date'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session.reschedule(new_date)
        
        # Send notifications
        if hasattr(session.mentorship, 'chat_room'):
            ChatNotification.objects.create(
                recipient=session.mentorship.mentee,
                chat_room=session.mentorship.chat_room,
                notification_type='status_changed',
                title='Session Rescheduled',
                message=f'Session {session.session_number} has been rescheduled to {new_date.strftime("%Y-%m-%d %H:%M")}'
            )
            
            ChatNotification.objects.create(
                recipient=session.mentorship.mentor,
                chat_room=session.mentorship.chat_room,
                notification_type='status_changed',
                title='Session Rescheduled',
                message=f'Session {session.session_number} has been rescheduled to {new_date.strftime("%Y-%m-%d %H:%M")}'
            )
        
        return Response({
            'success': True,
            'message': 'Session rescheduled successfully',
            'session': MentorshipSessionSerializer(session).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to reschedule session',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_session(request, session_id):
    """Cancel a session"""
    try:
        session = get_object_or_404(MentorshipSession, id=session_id)
        user = request.user
        
        # Check permissions
        if user not in [session.mentorship.mentor, session.mentorship.mentee] and user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if session.status == 'completed':
            return Response({
                'error': 'Cannot cancel a completed session'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('reason', 'No reason provided')
        session.mark_cancelled(reason)
        
        # Send notifications
        if hasattr(session.mentorship, 'chat_room'):
            ChatNotification.objects.create(
                recipient=session.mentorship.mentee,
                chat_room=session.mentorship.chat_room,
                notification_type='status_changed',
                title='Session Cancelled',
                message=f'Session {session.session_number} has been cancelled. Reason: {reason}'
            )
            
            ChatNotification.objects.create(
                recipient=session.mentorship.mentor,
                chat_room=session.mentorship.chat_room,
                notification_type='status_changed',
                title='Session Cancelled',
                message=f'Session {session.session_number} has been cancelled. Reason: {reason}'
            )
        
        return Response({
            'success': True,
            'message': 'Session cancelled successfully'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to cancel session',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




