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
from departmentApp.models import Department

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
    """
    Get all programs for a specific department.
    Note: 'department' parameter can be either department ID or department name
    """
    try:
        from departmentApp.models import Department
        
        # Try to get department by ID first (department parameter might already be an int)
        try:
            # Check if it's a string that can be converted to int
            if isinstance(department, str) and department.isdigit():
                department_id = int(department)
                department_obj = Department.objects.get(id=department_id)
            elif isinstance(department, int):
                department_obj = Department.objects.get(id=department)
            else:
                # If not a number, treat it as a department name
                department_obj = Department.objects.get(name=department)
        except Department.DoesNotExist:
            return Response({
                'error': f'Department "{department}" not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get programs for this department
        programs = MentorshipProgram.objects.filter(
            department=department_obj.name,
            status='active'
        )
        
        serializer = MentorshipProgramSerializer(programs, many=True)
        
        return Response({
            'success': True,
            'department': {
                'id': department_obj.id,
                'name': department_obj.name,
                'description': department_obj.description
            },
            'count': programs.count(),
            'programs': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_department_programs: {str(e)}")
        return Response({
            'error': 'Failed to fetch department programs',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_mentors(request):
    """Get available mentors for a specific department"""
    try:
        department_param = request.query_params.get('department')
        
        if not department_param:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the Department object
        try:
            # Check if it's a department ID (number)
            if department_param.isdigit():
                department_obj = Department.objects.get(id=int(department_param))
            else:
                # Treat it as a department name
                department_obj = Department.objects.get(name=department_param)
        except Department.DoesNotExist:
            return Response({
                'error': f'Department "{department_param}" not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get active mentors in the specified department
        available_mentors = CustomUser.objects.filter(
            role='mentor',
            department=department_obj,  # Use the Department object
            status='approved',
            availability_status='active'
        )
        
        # For mentors, we also need to check if they have this department in their M2M relationship
        mentors_in_department = CustomUser.objects.filter(
            role='mentor',
            departments=department_obj,  # Check M2M relationship
            status='approved',
            availability_status='active'
        )
        
        # Combine both querysets and remove duplicates
        all_mentors = (available_mentors | mentors_in_department).distinct()
        
        # Check current workload
        mentors_data = []
        for mentor in all_mentors:
            # Count active mentorships
            active_mentorships = Mentorship.objects.filter(
                mentor=mentor,
                status='active'
            ).count()
            
            # Calculate workload percentage
            workload_percentage = min(active_mentorships * 20, 100)  # 5 mentees max = 100%
            
            mentors_data.append({
                'id': mentor.id,
                'full_name': mentor.full_name,
                'email': mentor.email,
                'work_mail_address': mentor.work_mail_address,
                'department': mentor.department.name if mentor.department else department_obj.name,
                'department_id': department_obj.id,
                'phone_number': mentor.phone_number,
                'availability_status': mentor.availability_status,
                'active_mentorships': active_mentorships,
                'workload_percentage': workload_percentage,
                'is_available': active_mentorships < 5,  # Max 5 mentees per mentor
                'assigned_departments': [
                    {'id': dept.id, 'name': dept.name} 
                    for dept in mentor.departments.all()
                ]
            })
        
        # Sort by availability (more available first)
        mentors_data.sort(key=lambda x: (x['active_mentorships'], x['full_name']))
        
        return Response({
            'success': True,
            'department': department_obj.name,
            'department_id': department_obj.id,
            'count': len(mentors_data),
            'available_count': len([m for m in mentors_data if m['is_available']]),
            'mentors': mentors_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_available_mentors: {str(e)}")
        return Response({
            'error': 'Failed to fetch available mentors',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ready_mentees(request):
    """Get mentees who have completed onboarding and are ready for mentorship"""
    try:
        department_param = request.query_params.get('department')
        
        if not department_param:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the Department object
        try:
            # Check if it's a department ID (number)
            if department_param.isdigit():
                department_obj = Department.objects.get(id=int(department_param))
            else:
                # Treat it as a department name
                department_obj = Department.objects.get(name=department_param)
        except Department.DoesNotExist:
            return Response({
                'error': f'Department "{department_param}" not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        from onboarding.models import OnboardingModule, MenteeOnboardingProgress
        
        # Get all mentees in the department (using ForeignKey)
        mentees = CustomUser.objects.filter(
            role='mentee',
            department=department_obj,  # Use the Department object
            status='approved'
        )
        
        ready_mentees_data = []
        for mentee in mentees:
            # Check if mentee has completed all required core modules
            required_core_modules = OnboardingModule.objects.filter(
                module_type='core',
                is_required=True,
                is_active=True
            )
            
            # Check if mentee has completed all required department-specific modules
            required_department_modules = OnboardingModule.objects.filter(
                module_type='department',
                departments=department_obj,  # Use M2M relationship
                is_required=True,
                is_active=True
            )
            
            all_required_modules = list(required_core_modules) + list(required_department_modules)
            
            # Check completion status for each module
            incomplete_modules = []
            completed_modules = []
            
            for module in all_required_modules:
                progress = MenteeOnboardingProgress.objects.filter(
                    mentee=mentee,
                    module=module
                ).first()
                
                if progress and progress.status == 'completed':
                    completed_modules.append({
                        'id': module.id,
                        'title': module.title,
                        'type': module.module_type
                    })
                else:
                    incomplete_modules.append({
                        'id': module.id,
                        'title': module.title,
                        'type': module.module_type,
                        'progress': progress.progress_percentage if progress else 0
                    })
            
            # Check if mentee already has active mentorship in this department
            has_active_mentorship = Mentorship.objects.filter(
                mentee=mentee,
                status__in=['pending', 'active'],
                program__department=department_obj.name
            ).exists()
            
            # Calculate overall onboarding progress
            total_modules = len(all_required_modules)
            completed_count = len(completed_modules)
            onboarding_progress = round((completed_count / total_modules * 100), 2) if total_modules > 0 else 0
            
            # Determine eligibility
            is_eligible = (
                len(incomplete_modules) == 0 and  # All modules completed
                not has_active_mentorship and      # No active mentorship in this department
                total_modules > 0                  # Has required modules
            )
            
            ready_mentees_data.append({
                'id': mentee.id,
                'full_name': mentee.full_name,
                'email': mentee.email,
                'work_mail_address': mentee.work_mail_address,
                'department': mentee.department.name if mentee.department else department_obj.name,
                'department_id': department_obj.id,
                'phone_number': mentee.phone_number,
                'status': mentee.status,
                'availability_status': mentee.availability_status,
                'onboarding_completed': len(incomplete_modules) == 0,
                'onboarding_progress': onboarding_progress,
                'completed_modules_count': completed_count,
                'total_modules_required': total_modules,
                'has_active_mentorship': has_active_mentorship,
                'last_active': mentee.last_login,
                'created_at': mentee.created_at,
                'is_eligible': is_eligible,
                'incomplete_modules': incomplete_modules,
                'completed_modules': completed_modules
            })
        
        # Sort by eligibility and onboarding completion
        ready_mentees_data.sort(key=lambda x: (
            not x['is_eligible'],  # Eligible first
            -x['onboarding_progress'],  # Higher progress first
            x['full_name']  # Alphabetical
        ))
        
        return Response({
            'success': True,
            'department': department_obj.name,
            'department_id': department_obj.id,
            'total_mentees': mentees.count(),
            'eligible_count': len([m for m in ready_mentees_data if m['is_eligible']]),
            'ready_count': len([m for m in ready_mentees_data if m['onboarding_completed']]),
            'mentees': ready_mentees_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_ready_mentees: {str(e)}")
        return Response({
            'error': 'Failed to fetch ready mentees',
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
    """Create a new department-based mentorship"""
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
        
        # Get department
        department_id = data.get('department_id')
        try:
            department = Department.objects.get(id=department_id, status='active')
        except Department.DoesNotExist:
            return Response({
                'error': 'Department not found or inactive'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create mentorship
        mentorship = Mentorship.objects.create(
            mentor_id=data['mentor_id'],
            mentee_id=data['mentee_id'],
            department=department,
            start_date=data['start_date'],
            goals=data.get('goals', []),
            notes=data.get('notes', ''),
            status='active',
            created_by=request.user
        )
        
        # Initialize program progress for all active programs in department
        programs_in_department = MentorshipProgram.objects.filter(
            department=department.name,
            status='active'
        )
        
        # Set current program to the first one
        if programs_in_department.exists():
            mentorship.current_program = programs_in_department.first()
            mentorship.save()
        
        # Create chat room automatically
        chat_room = ChatRoom.objects.create(
            mentorship=mentorship,
            is_active=True
        )
        
        # Send notifications...
        
        return Response({
            'success': True,
            'message': 'Department-based mentorship created successfully',
            'mentorship': MentorshipSerializer(mentorship).data
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

    """Create a session for the current program in mentorship"""
    try:
        serializer = SessionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        mentorship = get_object_or_404(Mentorship, id=data['mentorship_id'])
        
        # Check if mentorship has a current program
        if not mentorship.current_program:
            return Response({
                'error': 'No current program assigned to this mentorship'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create session for current program
        program_progress = mentorship.program_progress.filter(
            program=mentorship.current_program
        ).first()
        
        if not program_progress:
            return Response({
                'error': 'Program progress not found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get next session number for this program
        last_session = MentorshipSession.objects.filter(
            mentorship=mentorship,
            program=mentorship.current_program
        ).order_by('-program_session_number').first()
        
        program_session_number = (last_session.program_session_number + 1) if last_session else 1
        
        # Create session
        session = MentorshipSession.objects.create(
            mentorship=mentorship,
            program=mentorship.current_program,
            program_progress=program_progress,
            session_template_id=data.get('session_template_id'),
            program_session_number=program_session_number,
            session_type=data.get('session_type', 'video'),
            scheduled_date=data['scheduled_date'],
            duration_minutes=data.get('duration_minutes', 60),
            agenda=data.get('agenda', ''),
            meeting_link=data.get('meeting_link', ''),
            location=data.get('location', ''),
            status='scheduled'
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
                print(f"Invalid status filter received: {status_filter}")
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
        print(f"Error in list_mentorship_programs: {str(e)}")
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
            print(f"Invalid user role encountered: {user.role}")
            return Response({
                'error': 'Invalid user role'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Apply filters
        if status_filter:
            if status_filter not in dict(Mentorship.STATUS_CHOICES).keys():
                print(f"Invalid status filter received: {status_filter}")
                return Response({
                    'error': f'Invalid status. Must be one of: {", ".join(dict(Mentorship.STATUS_CHOICES).keys())}'
                }, status=status.HTTP_400_BAD_REQUEST)
            mentorships = mentorships.filter(status=status_filter)
        
        if program_filter:
            try:
                mentorships = mentorships.filter(program_id=int(program_filter))
            except (ValueError, TypeError):
                print(f"Invalid program filter received: {program_filter}")
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
        print(f"Error in list_mentorships: {str(e)}")
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




# Add these views to your mentorshipApp/views.py

# Update the get_available_mentors view in mentorshipApp/views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_mentors(request):
    """Get available mentors for a specific department"""
    try:
        department_name = request.query_params.get('department')
        
        if not department_name:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # First, get the Department object by name
        try:
            department_obj = Department.objects.get(name=department_name)
        except Department.DoesNotExist:
            return Response({
                'error': f'Department "{department_name}" not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get active mentors in the specified department
        available_mentors = CustomUser.objects.filter(
            role='mentor',
            department=department_obj,  # Use the Department object
            status='approved',
            availability_status='active'
        )
        
        # For mentors, we also need to check if they have this department in their M2M relationship
        mentors_in_department = CustomUser.objects.filter(
            role='mentor',
            departments=department_obj,  # Check M2M relationship
            status='approved',
            availability_status='active'
        )
        
        # Combine both querysets and remove duplicates
        all_mentors = (available_mentors | mentors_in_department).distinct()
        
        # Check current workload
        mentors_data = []
        for mentor in all_mentors:
            # Count active mentorships
            active_mentorships = Mentorship.objects.filter(
                mentor=mentor,
                status='active'
            ).count()
            
            # Calculate workload percentage
            workload_percentage = min(active_mentorships * 20, 100)  # 5 mentees max = 100%
            
            mentors_data.append({
                'id': mentor.id,
                'full_name': mentor.full_name,
                'email': mentor.email,
                'work_mail_address': mentor.work_mail_address,
                'department': mentor.department.name if mentor.department else department_name,
                'phone_number': mentor.phone_number,
                'availability_status': mentor.availability_status,
                'active_mentorships': active_mentorships,
                'workload_percentage': workload_percentage,
                'is_available': active_mentorships < 5,  # Max 5 mentees per mentor
                'assigned_departments': [
                    {'id': dept.id, 'name': dept.name} 
                    for dept in mentor.departments.all()
                ]
            })
        
        # Sort by availability (more available first)
        mentors_data.sort(key=lambda x: (x['active_mentorships'], x['full_name']))
        
        return Response({
            'success': True,
            'department': department_name,
            'department_id': department_obj.id,
            'count': len(mentors_data),
            'available_count': len([m for m in mentors_data if m['is_available']]),
            'mentors': mentors_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_available_mentors: {str(e)}")
        return Response({
            'error': 'Failed to fetch available mentors',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ready_mentees(request):
    """Get mentees who have completed onboarding and are ready for mentorship"""
    try:
        department_name = request.query_params.get('department')
        
        if not department_name:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # First, get the Department object by name
        try:
            department_obj = Department.objects.get(name=department_name)
        except Department.DoesNotExist:
            return Response({
                'error': f'Department "{department_name}" not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        from onboarding.models import OnboardingModule, MenteeOnboardingProgress
        
        # Get all mentees in the department (using ForeignKey)
        mentees = CustomUser.objects.filter(
            role='mentee',
            department=department_obj,  # Use the Department object
            status='approved'
        )
        
        ready_mentees_data = []
        for mentee in mentees:
            # Check if mentee has completed all required core modules
            required_core_modules = OnboardingModule.objects.filter(
                module_type='core',
                is_required=True,
                is_active=True
            )
            
            # Check if mentee has completed all required department-specific modules
            required_department_modules = OnboardingModule.objects.filter(
                module_type='department',
                departments=department_obj,  # Use M2M relationship
                is_required=True,
                is_active=True
            )
            
            all_required_modules = list(required_core_modules) + list(required_department_modules)
            
            # Check completion status for each module
            incomplete_modules = []
            completed_modules = []
            
            for module in all_required_modules:
                progress = MenteeOnboardingProgress.objects.filter(
                    mentee=mentee,
                    module=module
                ).first()
                
                if progress and progress.status == 'completed':
                    completed_modules.append({
                        'id': module.id,
                        'title': module.title,
                        'type': module.module_type
                    })
                else:
                    incomplete_modules.append({
                        'id': module.id,
                        'title': module.title,
                        'type': module.module_type,
                        'progress': progress.progress_percentage if progress else 0
                    })
            
            # Check if mentee already has active mentorship in this department
            has_active_mentorship = Mentorship.objects.filter(
                mentee=mentee,
                status__in=['pending', 'active'],
                program__department=department_name
            ).exists()
            
            # Calculate overall onboarding progress
            total_modules = len(all_required_modules)
            completed_count = len(completed_modules)
            onboarding_progress = round((completed_count / total_modules * 100), 2) if total_modules > 0 else 0
            
            # Determine eligibility
            is_eligible = (
                len(incomplete_modules) == 0 and  # All modules completed
                not has_active_mentorship and      # No active mentorship in this department
                total_modules > 0                  # Has required modules
            )
            
            ready_mentees_data.append({
                'id': mentee.id,
                'full_name': mentee.full_name,
                'email': mentee.email,
                'work_mail_address': mentee.work_mail_address,
                'department': mentee.department.name if mentee.department else department_name,
                'department_id': department_obj.id,
                'phone_number': mentee.phone_number,
                'status': mentee.status,
                'availability_status': mentee.availability_status,
                'onboarding_completed': len(incomplete_modules) == 0,
                'onboarding_progress': onboarding_progress,
                'completed_modules_count': completed_count,
                'total_modules_required': total_modules,
                'has_active_mentorship': has_active_mentorship,
                'last_active': mentee.last_login,
                'created_at': mentee.created_at,
                'is_eligible': is_eligible,
                'incomplete_modules': incomplete_modules,
                'completed_modules': completed_modules
            })
        
        # Sort by eligibility and onboarding completion
        ready_mentees_data.sort(key=lambda x: (
            not x['is_eligible'],  # Eligible first
            -x['onboarding_progress'],  # Higher progress first
            x['full_name']  # Alphabetical
        ))
        
        return Response({
            'success': True,
            'department': department_name,
            'department_id': department_obj.id,
            'total_mentees': mentees.count(),
            'eligible_count': len([m for m in ready_mentees_data if m['is_eligible']]),
            'ready_count': len([m for m in ready_mentees_data if m['onboarding_completed']]),
            'mentees': ready_mentees_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in get_ready_mentees: {str(e)}")
        return Response({
            'error': 'Failed to fetch ready mentees',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_mentee_eligibility(request, mentee_id):
    """Check if a mentee is eligible for mentorship in a specific department"""
    try:
        department_param = request.query_params.get('department')
        
        if not department_param:
            return Response({
                'error': 'Department parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the Department object
        try:
            # Check if it's a department ID (number)
            if department_param.isdigit():
                department_obj = Department.objects.get(id=int(department_param))
            else:
                # Treat it as a department name
                department_obj = Department.objects.get(name=department_param)
        except Department.DoesNotExist:
            return Response({
                'eligible': False,
                'message': f'Department "{department_param}" not found'
            }, status=status.HTTP_200_OK)
        
        # Get the mentee
        try:
            mentee = CustomUser.objects.get(id=mentee_id, role='mentee')
        except CustomUser.DoesNotExist:
            return Response({
                'eligible': False,
                'message': 'Mentee not found'
            }, status=status.HTTP_200_OK)
        
        from onboarding.models import OnboardingModule, MenteeOnboardingProgress
        
        # Check 1: Is mentee in the specified department?
        if mentee.department != department_obj:
            return Response({
                'eligible': False,
                'message': f'Mentee is not in the {department_obj.name} department'
            }, status=status.HTTP_200_OK)
        
        # Check 2: Has mentee completed all required core modules?
        required_core_modules = OnboardingModule.objects.filter(
            module_type='core',
            is_required=True,
            is_active=True
        )
        
        incomplete_core_modules = []
        for module in required_core_modules:
            progress = MenteeOnboardingProgress.objects.filter(
                mentee=mentee,
                module=module
            ).first()
            
            if not progress or progress.status != 'completed':
                incomplete_core_modules.append(module.title)
        
        if incomplete_core_modules:
            return Response({
                'eligible': False,
                'message': f'Mentee must complete core modules: {", ".join(incomplete_core_modules)}',
                'incomplete_core_modules': incomplete_core_modules
            }, status=status.HTTP_200_OK)
        
        # Check 3: Has mentee completed department-specific modules?
        required_department_modules = OnboardingModule.objects.filter(
            module_type='department',
            departments=department_obj,
            is_required=True,
            is_active=True
        )
        
        incomplete_department_modules = []
        for module in required_department_modules:
            progress = MenteeOnboardingProgress.objects.filter(
                mentee=mentee,
                module=module
            ).first()
            
            if not progress or progress.status != 'completed':
                incomplete_department_modules.append(module.title)
        
        if incomplete_department_modules:
            return Response({
                'eligible': False,
                'message': f'Mentee must complete department modules: {", ".join(incomplete_department_modules)}',
                'incomplete_department_modules': incomplete_department_modules
            }, status=status.HTTP_200_OK)
        
        # Check 4: Does mentee already have active mentorship in this department?
        existing_mentorship = Mentorship.objects.filter(
            mentee=mentee,
            status__in=['pending', 'active'],
            program__department=department_obj.name
        ).first()
        
        if existing_mentorship:
            return Response({
                'eligible': False,
                'message': f'Mentee already has an active mentorship with {existing_mentorship.mentor.full_name}',
                'existing_mentorship': {
                    'id': existing_mentorship.id,
                    'mentor': existing_mentorship.mentor.full_name,
                    'program': existing_mentorship.program.name,
                    'status': existing_mentorship.status
                }
            }, status=status.HTTP_200_OK)
        
        # Check 5: Is mentee approved?
        if mentee.status != 'approved':
            return Response({
                'eligible': False,
                'message': f'Mentee account is {mentee.status}'
            }, status=status.HTTP_200_OK)
        
        # All checks passed
        return Response({
            'eligible': True,
            'message': 'Mentee is eligible for mentorship',
            'mentee': {
                'id': mentee.id,
                'full_name': mentee.full_name,
                'email': mentee.email,
                'department': mentee.department.name if mentee.department else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error in check_mentee_eligibility: {str(e)}")
        return Response({
            'error': 'Failed to check eligibility',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_mentorship_actions(request):
    """Handle bulk actions on multiple mentorships"""
    try:
        if request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can perform bulk actions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        mentorship_ids = request.data.get('mentorshipIds', [])
        action = request.data.get('action')
        
        if not mentorship_ids:
            return Response({
                'error': 'No mentorships selected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not action:
            return Response({
                'error': 'Action is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        valid_actions = ['activate', 'complete', 'pause', 'cancel', 'delete']
        if action not in valid_actions:
            return Response({
                'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the mentorships
        mentorships = Mentorship.objects.filter(id__in=mentorship_ids)
        
        if mentorships.count() != len(mentorship_ids):
            return Response({
                'error': 'Some mentorships were not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for mentorship in mentorships:
                try:
                    if action == 'activate':
                        if mentorship.status != 'active':
                            mentorship.status = 'active'
                            if not mentorship.start_date:
                                mentorship.start_date = now().date()
                            mentorship.save()
                            updated_count += 1
                            
                    elif action == 'complete':
                        if mentorship.status != 'completed':
                            mentorship.status = 'completed'
                            mentorship.actual_end_date = now().date()
                            mentorship.save()
                            updated_count += 1
                            
                    elif action == 'pause':
                        if mentorship.status == 'active':
                            mentorship.status = 'paused'
                            mentorship.save()
                            updated_count += 1
                            
                    elif action == 'cancel':
                        if mentorship.status not in ['completed', 'cancelled']:
                            mentorship.status = 'cancelled'
                            mentorship.save()
                            updated_count += 1
                            
                    elif action == 'delete':
                        # Check if mentorship can be deleted
                        if mentorship.status in ['completed', 'cancelled']:
                            mentorship.delete()
                            updated_count += 1
                        else:
                            errors.append(f'Mentorship {mentorship.id} cannot be deleted because it is {mentorship.status}')
                    
                except Exception as e:
                    errors.append(f'Error processing mentorship {mentorship.id}: {str(e)}')
                    continue
        
        response_data = {
            'success': True,
            'message': f'Bulk action completed. Processed {updated_count} mentorships.',
            'updated_count': updated_count,
            'total_selected': len(mentorship_ids)
        }
        
        if errors:
            response_data['errors'] = errors
            response_data['has_errors'] = True
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to perform bulk action',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    






@api_view(['POST'])
@permission_classes([IsAuthenticated])
def switch_current_program(request, mentorship_id, program_id):
    """Switch to a different program within the department"""
    try:
        mentorship = get_object_or_404(Mentorship, id=mentorship_id)
        new_program = get_object_or_404(MentorshipProgram, id=program_id)
        
        # Check if program belongs to mentorship's department
        if new_program.department != mentorship.department.name:
            return Response({
                'error': 'Program does not belong to mentorship department'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if program is in mentorship's programs list
        if not mentorship.programs.filter(id=program_id).exists():
            return Response({
                'error': 'Program not assigned to this mentorship'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Switch current program
        mentorship.current_program = new_program
        mentorship.save()
        
        return Response({
            'success': True,
            'message': f'Switched to program: {new_program.name}',
            'current_program': MentorshipProgramSerializer(new_program).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to switch program',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




        