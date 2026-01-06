import email
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count, Sum
from django.utils.timezone import now, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from .serializers import SendReminderSerializer

from .models import (
    OnboardingModule, 
    MenteeOnboardingProgress, 
    OnboardingChecklist,
    MenteeChecklistProgress,
    OnboardingNotification,
    OnboardingDeadline
)
from .serializers import (
    OnboardingModuleSerializer,
    OnboardingModuleCreateSerializer,
    MenteeOnboardingProgressSerializer,
    MenteeOnboardingProgressUpdateSerializer,
    MenteeSummarySerializer,
    MenteeChecklistProgressSerializer
)
from userApp.models import CustomUser




# views.py

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.db.utils import IntegrityError
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import CustomUser
import re
import random
import string
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)


# ================ HELPER FUNCTIONS ================

def calculate_overall_progress(mentee):
    """
    Calculate overall onboarding progress for a mentee
    """
    progress_records = MenteeOnboardingProgress.objects.filter(mentee=mentee)
    
    if not progress_records:
        return {
            'total_modules': 0,
            'completed_modules': 0,
            'in_progress_modules': 0,
            'not_started_modules': 0,
            'overall_percentage': 0,
            'average_progress': 0,
            'total_time_spent': 0,
            'estimated_time_remaining': 0
        }
    
    total_modules = progress_records.count()
    completed_modules = progress_records.filter(status='completed').count()
    in_progress_modules = progress_records.filter(status='in_progress').count()
    not_started_modules = progress_records.filter(status='not_started').count()
    
    # Calculate average progress percentage
    average_progress = progress_records.aggregate(
        avg=Avg('progress_percentage')
    )['avg'] or 0
    
    # Calculate overall percentage (weighted by module duration)
    total_duration = sum([p.module.duration_minutes for p in progress_records])
    if total_duration > 0:
        weighted_sum = sum([
            p.progress_percentage * p.module.duration_minutes 
            for p in progress_records
        ])
        overall_percentage = round((weighted_sum / total_duration), 2)
    else:
        overall_percentage = round(average_progress, 2)
    
    # Calculate total time spent
    total_time_spent = progress_records.aggregate(
        total=Sum('time_spent_minutes')
    )['total'] or 0
    
    # Calculate estimated time remaining
    remaining_time = 0
    for progress in progress_records.filter(status__in=['not_started', 'in_progress']):
        remaining_percentage = 100 - progress.progress_percentage
        module_remaining = (remaining_percentage / 100) * progress.module.duration_minutes
        remaining_time += module_remaining
    
    return {
        'total_modules': total_modules,
        'completed_modules': completed_modules,
        'in_progress_modules': in_progress_modules,
        'not_started_modules': not_started_modules,
        'overall_percentage': overall_percentage,
        'average_progress': round(average_progress, 2),
        'total_time_spent': total_time_spent,
        'estimated_time_remaining': round(remaining_time, 0)
    }


def send_onboarding_notification(recipient, notification_type, title, message, 
                                 related_module=None, related_progress=None):
    """
    Create and store an onboarding notification
    """
    notification = OnboardingNotification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_module=related_module,
        related_progress=related_progress
    )
    
    # Also send email notification
    try:
        send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True
        )
    except Exception as e:
        print(f"Failed to send email notification: {e}")
    
    return notification


def check_and_update_progress_status(progress):
    """
    Check and update progress status based on time and completion
    """
    old_status = progress.status
    new_status = progress.calculate_auto_status()
    
    if old_status != new_status:
        progress.status = new_status
        progress.save()
        
        # Send notification for status change
        if new_status in ['needs_attention', 'off_track', 'overdue']:
            send_status_change_notification(progress, old_status, new_status)
        
        return True
    return False


def send_status_change_notification(progress, old_status, new_status):
    """
    Send notification when progress status changes
    """
    mentee = progress.mentee
    module = progress.module
    
    # Status change mapping for email subjects
    status_titles = {
        'needs_attention': 'Needs Attention',
        'off_track': 'Off Track',
        'overdue': 'Overdue'
    }
    
    title = f"Onboarding Status Update: {module.title} - {status_titles.get(new_status, new_status)}"
    
    # Message to mentee
    mentee_message = f"""
    Hello {mentee.full_name},
    
    Your onboarding progress for "{module.title}" has been updated:
    
    Old Status: {old_status}
    New Status: {new_status}
    Current Progress: {progress.progress_percentage}%
    
    Please review your progress and take necessary action.
    
    Best regards,
    Mentorship Program Team
    """
    
    send_onboarding_notification(
        recipient=mentee,
        notification_type='status_changed',
        title=title,
        message=mentee_message,
        related_module=module,
        related_progress=progress
    )
    
    # Message to mentors in the department
    mentors = CustomUser.objects.filter(
        role='mentor',
        department=mentee.department,
        status='approved'
    )
    
    for mentor in mentors:
        mentor_title = f"Mentee Status Update: {mentee.full_name} - {module.title}"
        mentor_message = f"""
        Mentor Notification:
        
        Your mentee's onboarding status has changed:
        
        Mentee: {mentee.full_name}
        Module: {module.title}
        Old Status: {old_status}
        New Status: {new_status}
        Current Progress: {progress.progress_percentage}%
        
        Please provide guidance and support.
        
        Best regards,
        Mentorship Program Team
        """
        
        send_onboarding_notification(
            recipient=mentor,
            notification_type='status_changed',
            title=mentor_title,
            message=mentor_message,
            related_module=module,
            related_progress=progress
        )
    
    # Send to HR if progress is severely behind
    if progress.progress_percentage < 30 and new_status in ['overdue', 'off_track']:
        hr_users = CustomUser.objects.filter(role='hr', status='approved')
        for hr_user in hr_users:
            hr_title = f"Critical Onboarding Delay: {mentee.full_name}"
            hr_message = f"""
            HR Alert - Critical Onboarding Delay:
            
            Mentee: {mentee.full_name}
            Module: {module.title}
            Department: {mentee.department}
            Progress: {progress.progress_percentage}%
            Status: {new_status}
            
            This mentee is significantly behind schedule and may need intervention.
            
            Best regards,
            Mentorship Program System
            """
            
            send_onboarding_notification(
                recipient=hr_user,
                notification_type=new_status,
                title=hr_title,
                message=hr_message,
                related_module=module,
                related_progress=progress
            )


# ================ ONBOARDING MODULE VIEWS ================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_onboarding_modules(request):
    """
    Get all active onboarding modules with filters
    """
    user = request.user
    queryset = OnboardingModule.objects.filter(is_active=True)
    
    # Filter by department if specified
    department = request.query_params.get('department', None)
    if department:
        queryset = queryset.filter(
            Q(module_type='core') | Q(department=department)
        )
    
    # Filter by module type
    module_type = request.query_params.get('module_type', None)
    if module_type:
        queryset = queryset.filter(module_type=module_type)
    
    # For mentors, show only modules relevant to their department
    if user.role == 'mentor':
        queryset = queryset.filter(
            Q(module_type='core') | Q(department=user.department)
        )
    
    serializer = OnboardingModuleSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_onboarding_module_detail(request, pk):
    """
    Get details of a specific onboarding module
    """
    module = get_object_or_404(OnboardingModule, pk=pk, is_active=True)
    
    # Check if user has access
    if request.user.role == 'mentor' and module.module_type == 'department':
        if module.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to view this module'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    serializer = OnboardingModuleSerializer(module)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_onboarding_module(request):
    """
    Create a new onboarding module (Admin/HR only)
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can create onboarding modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = OnboardingModuleCreateSerializer(data=request.data)
    if serializer.is_valid():
        module = serializer.save(created_by=request.user)
        return Response(
            OnboardingModuleSerializer(module).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_onboarding_module(request, pk):
    """
    Update an onboarding module (Admin/HR only)
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can update onboarding modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    module = get_object_or_404(OnboardingModule, pk=pk)
    serializer = OnboardingModuleCreateSerializer(
        module, 
        data=request.data, 
        partial=True if request.method == 'PATCH' else False
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(OnboardingModuleSerializer(module).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_onboarding_module(request, pk):
    """
    Soft delete an onboarding module (Admin/HR only)
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can delete onboarding modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    module = get_object_or_404(OnboardingModule, pk=pk)
    module.is_active = False
    module.save()
    
    return Response(
        {'message': 'Module deactivated successfully'},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_onboarding_statistics(request):
    """
    Get overall onboarding statistics
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can view statistics'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    total_modules = OnboardingModule.objects.filter(is_active=True).count()
    core_modules = OnboardingModule.objects.filter(
        is_active=True, 
        module_type='core'
    ).count()
    department_modules = OnboardingModule.objects.filter(
        is_active=True, 
        module_type='department'
    ).count()
    
    # Get completion statistics
    total_progress_records = MenteeOnboardingProgress.objects.count()
    completed_records = MenteeOnboardingProgress.objects.filter(
        status='completed'
    ).count()
    
    completion_rate = 0
    if total_progress_records > 0:
        completion_rate = round((completed_records / total_progress_records) * 100, 2)
    
    # Get mentee statistics
    total_mentees = CustomUser.objects.filter(role='mentee', status='approved').count()
    mentees_with_modules = CustomUser.objects.filter(
        role='mentee', 
        status='approved',
        onboarding_progress__isnull=False
    ).distinct().count()
    
    # Calculate average progress per mentee
    if mentees_with_modules > 0:
        avg_progress = MenteeOnboardingProgress.objects.aggregate(
            avg_progress=Avg('progress_percentage')
        )['avg_progress'] or 0
    else:
        avg_progress = 0
    
    return Response({
        'total_modules': total_modules,
        'core_modules': core_modules,
        'department_modules': department_modules,
        'total_progress_records': total_progress_records,
        'completed_records': completed_records,
        'completion_rate': completion_rate,
        'total_mentees': total_mentees,
        'mentees_with_modules': mentees_with_modules,
        'average_mentee_progress': round(avg_progress, 2)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_module_to_mentees(request, pk):
    """
    Assign a module to specific mentees
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can assign modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    module = get_object_or_404(OnboardingModule, pk=pk, is_active=True)
    mentee_ids = request.data.get('mentee_ids', [])
    
    if not mentee_ids:
        return Response(
            {'error': 'No mentee IDs provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    assigned_count = 0
    already_assigned = 0
    errors = []
    
    with transaction.atomic():
        for mentee_id in mentee_ids:
            try:
                mentee = CustomUser.objects.get(id=mentee_id, role='mentee', status='approved')
                
                # Check if already assigned
                if MenteeOnboardingProgress.objects.filter(
                    mentee=mentee, 
                    module=module
                ).exists():
                    already_assigned += 1
                    continue
                
                # Create progress record
                progress = MenteeOnboardingProgress.objects.create(
                    mentee=mentee,
                    module=module,
                    status='not_started',
                    progress_percentage=0,
                    assigned_by=request.user
                )
                assigned_count += 1
                
                # Create deadline record
                if progress.started_at:
                    due_date = progress.started_at + timedelta(days=14)
                else:
                    due_date = now() + timedelta(days=14)
                
                OnboardingDeadline.objects.create(
                    module=module,
                    mentee=mentee,
                    due_date=due_date,
                    original_due_date=due_date
                )
                
                # Send notification to mentee
                title = f"New Onboarding Module Assigned: {module.title}"
                message = f"""
                Hello {mentee.full_name},
                
                A new onboarding module has been assigned to you:
                
                Module: {module.title}
                Type: {module.get_module_type_display()}
                Description: {module.description[:200]}...
                
                Please log in to the mentorship portal to start this module.
                
                Best regards,
                Mentorship Program Team
                """
                
                send_onboarding_notification(
                    recipient=mentee,
                    notification_type='module_assigned',
                    title=title,
                    message=message,
                    related_module=module,
                    related_progress=progress
                )
                
                # Send notification to mentors in the same department
                mentors = CustomUser.objects.filter(
                    role='mentor',
                    department=mentee.department,
                    status='approved'
                )
                
                for mentor in mentors:
                    mentor_title = f"New Module Assigned to Mentee: {mentee.full_name}"
                    mentor_message = f"""
                    Mentor Notification:
                    
                    A new onboarding module has been assigned to your mentee:
                    
                    Mentee: {mentee.full_name}
                    Module: {module.title}
                    Department: {mentee.department}
                    
                    Please check on their progress and provide support as needed.
                    
                    Best regards,
                    Mentorship Program Team
                    """
                    
                    send_onboarding_notification(
                        recipient=mentor,
                        notification_type='module_assigned',
                        title=mentor_title,
                        message=mentor_message,
                        related_module=module,
                        related_progress=progress
                    )
                
            except CustomUser.DoesNotExist:
                errors.append(f'Mentee with ID {mentee_id} not found or not approved')
                continue
    
    return Response({
        'message': f'Module assigned to {assigned_count} mentees',
        'assigned_count': assigned_count,
        'already_assigned': already_assigned,
        'errors': errors if errors else None
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_module_mentee_progress(request, pk):
    """
    Get all mentees' progress for a specific module
    """
    module = get_object_or_404(OnboardingModule, pk=pk, is_active=True)
    
    # Check permissions
    if request.user.role == 'mentor' and module.module_type == 'department':
        if module.department != request.user.department:
            return Response(
                {'error': 'You do not have permission to view this module progress'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Filter based on user role
    if request.user.role in ['admin', 'hr']:
        progress_records = MenteeOnboardingProgress.objects.filter(module=module)
    elif request.user.role == 'mentor':
        # Mentor can only see mentees in their department
        progress_records = MenteeOnboardingProgress.objects.filter(
            module=module,
            mentee__department=request.user.department
        )
    else:
        return Response(
            {'error': 'You do not have permission to view this data'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = MenteeOnboardingProgressSerializer(progress_records, many=True)
    return Response(serializer.data)


# ================ MENTEE PROGRESS VIEWS ================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentee_progress(request):
    """
    Get onboarding progress based on user role
    """
    user = request.user
    
    if user.role in ['admin', 'hr']:
        # Admins and HR can see all progress
        queryset = MenteeOnboardingProgress.objects.all()
        
        # Apply filters if provided
        mentee_id = request.query_params.get('mentee_id')
        if mentee_id:
            queryset = queryset.filter(mentee_id=mentee_id)
    
    elif user.role == 'mentor':
        # Mentors can see progress of mentees in their department
        queryset = MenteeOnboardingProgress.objects.filter(
            mentee__department=user.department
        )
        
        # Filter by specific mentee if provided
        mentee_id = request.query_params.get('mentee_id')
        if mentee_id:
            queryset = queryset.filter(mentee_id=mentee_id)
    
    elif user.role == 'mentee':
        # Mentees can only see their own progress
        queryset = MenteeOnboardingProgress.objects.filter(mentee=user)
    
    else:
        return Response(
            {'error': 'Invalid user role'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Apply additional filters
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    module_id = request.query_params.get('module_id')
    if module_id:
        queryset = queryset.filter(module_id=module_id)
    
    queryset = queryset.select_related('mentee', 'module')
    serializer = MenteeOnboardingProgressSerializer(queryset, many=True)
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentee_progress_detail(request, pk):
    """
    Get detailed progress for a specific progress record
    """
    progress = get_object_or_404(MenteeOnboardingProgress, pk=pk)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr']:
        if request.user.role == 'mentor':
            if progress.mentee.department != request.user.department:
                return Response(
                    {'error': 'You can only view progress of mentees in your department'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.role == 'mentee':
            if progress.mentee != request.user:
                return Response(
                    {'error': 'You can only view your own progress'},
                    status=status.HTTP_403_FORBIDDEN
                )
    
    serializer = MenteeOnboardingProgressSerializer(progress)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_onboarding_module(request, pk):
    """
    Mark an onboarding module as started
    """
    progress = get_object_or_404(MenteeOnboardingProgress, pk=pk)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr'] and progress.mentee != request.user:
        return Response(
            {'error': 'You can only start your own modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    progress.mark_as_started()
    
    # Update deadline with actual start date
    try:
        deadline = OnboardingDeadline.objects.get(
            module=progress.module,
            mentee=progress.mentee
        )
        deadline.due_date = progress.started_at + timedelta(days=14)
        deadline.save()
    except OnboardingDeadline.DoesNotExist:
        # Create deadline if it doesn't exist
        OnboardingDeadline.objects.create(
            module=progress.module,
            mentee=progress.mentee,
            due_date=progress.started_at + timedelta(days=14),
            original_due_date=progress.started_at + timedelta(days=14)
        )
    
    # Send notification to mentors
    mentors = CustomUser.objects.filter(
        role='mentor',
        department=progress.mentee.department,
        status='approved'
    )
    
    title = f"Mentee Started Module: {progress.mentee.full_name}"
    message = f"""
    Mentor Notification:
    
    Your mentee has started a new onboarding module:
    
    Mentee: {progress.mentee.full_name}
    Module: {progress.module.title}
    Started: {progress.started_at.strftime('%Y-%m-%d %H:%M')}
    
    Please check in with them if they need any assistance.
    
    Best regards,
    Mentorship Program Team
    """
    
    for mentor in mentors:
        send_onboarding_notification(
            recipient=mentor,
            notification_type='module_started',
            title=title,
            message=message,
            related_module=progress.module,
            related_progress=progress
        )
    
    serializer = MenteeOnboardingProgressSerializer(progress)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_onboarding_module(request, pk):
    """
    Mark an onboarding module as completed
    """
    progress = get_object_or_404(MenteeOnboardingProgress, pk=pk)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr'] and progress.mentee != request.user:
        return Response(
            {'error': 'You can only complete your own modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    progress.mark_as_completed()
    
    # Send notification to mentee
    title = f"Onboarding Module Completed: {progress.module.title}"
    message = f"""
    Congratulations {progress.mentee.full_name}!
    
    You have successfully completed the onboarding module: {progress.module.title}
    
    Great job on completing this module! You're one step closer to completing your onboarding process.
    
    Continue to the next module to keep progressing.
    
    Best regards,
    Mentorship Program Team
    """
    
    send_onboarding_notification(
        recipient=progress.mentee,
        notification_type='module_completed',
        title=title,
        message=message,
        related_module=progress.module,
        related_progress=progress
    )
    
    # Send notification to mentors
    mentors = CustomUser.objects.filter(
        role='mentor',
        department=progress.mentee.department,
        status='approved'
    )
    
    mentor_title = f"Mentee Completed Module: {progress.mentee.full_name}"
    mentor_message = f"""
    Mentor Notification:
    
    Your mentee has successfully completed an onboarding module:
    
    Mentee: {progress.mentee.full_name}
    Module: {progress.module.title}
    Completed: {progress.completed_at.strftime('%Y-%m-%d %H:%M')}
    
    Please acknowledge their achievement and encourage them to continue.
    
    Best regards,
    Mentorship Program Team
    """
    
    for mentor in mentors:
        send_onboarding_notification(
            recipient=mentor,
            notification_type='module_completed',
            title=mentor_title,
            message=mentor_message,
            related_module=progress.module,
            related_progress=progress
        )
    
    serializer = MenteeOnboardingProgressSerializer(progress)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_progress_percentage(request, pk):
    """
    Update progress percentage for a module
    """
    progress = get_object_or_404(MenteeOnboardingProgress, pk=pk)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr'] and progress.mentee != request.user:
        return Response(
            {'error': 'You can only update your own progress'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    percentage = request.data.get('progress_percentage')
    if percentage is None:
        return Response(
            {'error': 'progress_percentage is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        percentage = int(percentage)
        if not 0 <= percentage <= 100:
            return Response(
                {'error': 'Progress percentage must be between 0 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        time_spent = request.data.get('time_spent_minutes')
        if time_spent:
            try:
                time_spent = int(time_spent)
                if time_spent > 0:
                    progress.add_time_spent(time_spent)
            except ValueError:
                pass
        
        progress.update_progress(percentage)
        
        # Check and update status based on new progress
        check_and_update_progress_status(progress)
        
        serializer = MenteeOnboardingProgressSerializer(progress)
        return Response(serializer.data)
        
    except ValueError:
        return Response(
            {'error': 'Invalid progress percentage'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_progress_details(request, pk):
    """
    Update progress details (notes, time spent, status)
    """
    progress = get_object_or_404(MenteeOnboardingProgress, pk=pk)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can update progress details'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = MenteeOnboardingProgressUpdateSerializer(
        progress, 
        data=request.data, 
        partial=True if request.method == 'PATCH' else False
    )
    
    if serializer.is_valid():
        old_status = progress.status
        serializer.save()
        
        # Send notification if status changed to 'needs_attention'
        new_status = progress.status
        if old_status != new_status and new_status in ['needs_attention', 'off_track', 'overdue']:
            send_status_change_notification(progress, old_status, new_status)
        
        return Response(MenteeOnboardingProgressSerializer(progress).data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_checklist_item(request, pk):
    """
    Update checklist item completion status
    """
    progress = get_object_or_404(MenteeOnboardingProgress, pk=pk)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr'] and progress.mentee != request.user:
        return Response(
            {'error': 'You can only update your own checklist'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    checklist_item_id = request.data.get('checklist_item_id')
    is_completed = request.data.get('is_completed', True)
    
    if not checklist_item_id:
        return Response(
            {'error': 'checklist_item_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        checklist_item = OnboardingChecklist.objects.get(
            id=checklist_item_id,
            module=progress.module
        )
        
        # Get or create checklist progress
        checklist_progress, created = MenteeChecklistProgress.objects.get_or_create(
            mentee=progress.mentee,
            checklist_item=checklist_item
        )
        
        time_spent = request.data.get('time_spent_minutes')
        if time_spent:
            try:
                time_spent = int(time_spent)
                if time_spent > 0:
                    checklist_progress.add_time_spent(time_spent)
            except ValueError:
                pass
        
        if is_completed:
            checklist_progress.mark_completed()
        else:
            checklist_progress.mark_incomplete()
        
        # Update overall module progress based on checklist completion
        total_items = progress.module.checklist_items.count()
        if total_items > 0:
            completed_items = MenteeChecklistProgress.objects.filter(
                mentee=progress.mentee,
                checklist_item__module=progress.module,
                is_completed=True
            ).count()
            
            new_percentage = round((completed_items / total_items) * 100)
            progress.update_progress(new_percentage)
            
            # Check if needs attention
            check_and_update_progress_status(progress)
        
        serializer = MenteeOnboardingProgressSerializer(progress)
        return Response(serializer.data)
        
    except OnboardingChecklist.DoesNotExist:
        return Response(
            {'error': 'Checklist item not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_progress_summary(request):
    """
    Get current user's onboarding progress summary
    """
    if request.user.role != 'mentee':
        return Response(
            {'error': 'Only mentees have onboarding progress'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Calculate overall progress
    overall_progress = calculate_overall_progress(request.user)
    
    # Get detailed progress
    progress_records = MenteeOnboardingProgress.objects.filter(
        mentee=request.user
    ).select_related('module')
    
    # Get upcoming deadlines
    deadlines = OnboardingDeadline.objects.filter(
        mentee=request.user
    ).select_related('module')
    
    upcoming_deadlines = []
    for deadline in deadlines:
        if deadline.is_overdue():
            status = 'overdue'
        elif deadline.get_days_remaining() <= 3:
            status = 'urgent'
        elif deadline.get_days_remaining() <= 7:
            status = 'warning'
        else:
            status = 'normal'
        
        # Get corresponding progress
        progress = progress_records.filter(module=deadline.module).first()
        
        upcoming_deadlines.append({
            'module_id': deadline.module.id,
            'module_title': deadline.module.title,
            'due_date': deadline.due_date,
            'days_remaining': deadline.get_days_remaining(),
            'status': status,
            'progress_percentage': progress.progress_percentage if progress else 0
        })
    
    # Sort by urgency (overdue first, then by days remaining)
    upcoming_deadlines.sort(key=lambda x: (
        0 if x['status'] == 'overdue' else 
        1 if x['status'] == 'urgent' else 
        2 if x['status'] == 'warning' else 3,
        x['days_remaining']
    ))
    
    serializer = MenteeSummarySerializer(request.user)
    response_data = serializer.data
    response_data.update(overall_progress)
    response_data['upcoming_deadlines'] = upcoming_deadlines[:5]  # Top 5 most urgent
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_mentees_summary(request):
    """
    Get summary of all mentees' progress (admin/HR only)
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can view all mentees summary'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    mentees = CustomUser.objects.filter(role='mentee', status='approved')
    
    # Filter by department if specified
    department = request.query_params.get('department', None)
    if department:
        mentees = mentees.filter(department=department)
    
    # Get mentee IDs who are behind schedule
    behind_schedule_ids = []
    for mentee in mentees:
        progress_records = MenteeOnboardingProgress.objects.filter(
            mentee=mentee,
            status__in=['overdue', 'off_track', 'needs_attention']
        )
        if progress_records.exists():
            behind_schedule_ids.append(mentee.id)
    
    serializer = MenteeSummarySerializer(mentees, many=True)
    
    # Add additional statistics
    total_mentees = mentees.count()
    mentees_with_progress = mentees.filter(onboarding_progress__isnull=False).distinct().count()
    
    return Response({
        'mentees': serializer.data,
        'statistics': {
            'total_mentees': total_mentees,
            'mentees_with_progress': mentees_with_progress,
            'mentees_behind_schedule': len(behind_schedule_ids),
            'behind_schedule_percentage': round((len(behind_schedule_ids) / total_mentees * 100), 2) if total_mentees > 0 else 0
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_assign_modules(request):
    """
    Automatically assign appropriate modules to a mentee
    """
    if request.user.role not in ['admin', 'hr']:
        return Response(
            {'error': 'Only admins and HR can auto-assign modules'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    mentee_id = request.data.get('mentee_id')
    if not mentee_id:
        return Response(
            {'error': 'mentee_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        mentee = CustomUser.objects.get(id=mentee_id, role='mentee', status='approved')
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'Mentee not found or not approved'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get core modules and department-specific modules
    modules = OnboardingModule.objects.filter(
        Q(module_type='core') | Q(department=mentee.department),
        is_active=True
    )
    
    assigned_count = 0
    assigned_modules = []
    
    with transaction.atomic():
        for module in modules:
            # Check if already assigned
            if not MenteeOnboardingProgress.objects.filter(
                mentee=mentee,
                module=module
            ).exists():
                progress = MenteeOnboardingProgress.objects.create(
                    mentee=mentee,
                    module=module,
                    status='not_started',
                    progress_percentage=0,
                    assigned_by=request.user
                )
                
                # Create deadline
                due_date = now() + timedelta(days=14)
                OnboardingDeadline.objects.create(
                    module=module,
                    mentee=mentee,
                    due_date=due_date,
                    original_due_date=due_date
                )
                
                assigned_count += 1
                assigned_modules.append({
                    'id': module.id,
                    'title': module.title,
                    'type': module.module_type
                })
    
    # Send notification to mentee
    if assigned_count > 0:
        title = "Onboarding Modules Assigned"
        module_list = "\n".join([f"- {module['title']}" for module in assigned_modules])
        
        message = f"""
        Hello {mentee.full_name},
        
        {assigned_count} onboarding modules have been automatically assigned to you:
        
        {module_list}
        
        Please log in to the mentorship portal to start your onboarding journey.
        
        Best regards,
        Mentorship Program Team
        """
        
        send_onboarding_notification(
            recipient=mentee,
            notification_type='module_assigned',
            title=title,
            message=message,
            related_module=None
        )
        
        # Send notification to mentors
        mentors = CustomUser.objects.filter(
            role='mentor',
            department=mentee.department,
            status='approved'
        )
        
        for mentor in mentors:
            mentor_title = f"New Mentee Assigned: {mentee.full_name}"
            mentor_message = f"""
            Mentor Notification:
            
            {assigned_count} onboarding modules have been automatically assigned to your new mentee:
            
            Mentee: {mentee.full_name}
            Department: {mentee.department}
            
            Please welcome them and guide them through the onboarding process.
            
            Best regards,
            Mentorship Program Team
            """
            
            send_onboarding_notification(
                recipient=mentor,
                notification_type='module_assigned',
                title=mentor_title,
                message=mentor_message
            )
    
    return Response({
        'message': f'Auto-assigned {assigned_count} modules to {mentee.full_name}',
        'assigned_count': assigned_count,
        'assigned_modules': assigned_modules,
        'mentee': {
            'id': mentee.id,
            'name': mentee.full_name,
            'department': mentee.department
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_upcoming_deadlines(request):
    """
    Get modules that are close to deadline
    """
    user = request.user
    
    if user.role == 'mentee':
        # Get mentee's deadlines
        deadlines = OnboardingDeadline.objects.filter(mentee=user)
        
        upcoming_deadlines = []
        for deadline in deadlines:
            days_remaining = deadline.get_days_remaining()
            
            if days_remaining <= 7:  # Show deadlines within 7 days
                # Get progress for this module
                progress = MenteeOnboardingProgress.objects.filter(
                    mentee=user,
                    module=deadline.module
                ).first()
                
                status = 'overdue' if deadline.is_overdue() else 'urgent' if days_remaining <= 1 else 'warning'
                
                upcoming_deadlines.append({
                    'module_id': deadline.module.id,
                    'module_title': deadline.module.title,
                    'due_date': deadline.due_date,
                    'days_remaining': days_remaining,
                    'status': status,
                    'progress_percentage': progress.progress_percentage if progress else 0,
                    'is_extended': deadline.is_extended
                })
        
        return Response(upcoming_deadlines)
    
    elif user.role == 'mentor':
        # Get deadlines for mentees in mentor's department
        mentees = CustomUser.objects.filter(
            role='mentee',
            department=user.department,
            status='approved'
        )
        
        upcoming_deadlines = []
        for mentee in mentees:
            deadlines = OnboardingDeadline.objects.filter(mentee=mentee)
            
            for deadline in deadlines:
                days_remaining = deadline.get_days_remaining()
                
                if days_remaining <= 7:
                    progress = MenteeOnboardingProgress.objects.filter(
                        mentee=mentee,
                        module=deadline.module
                    ).first()
                    
                    status = 'overdue' if deadline.is_overdue() else 'urgent' if days_remaining <= 1 else 'warning'
                    
                    upcoming_deadlines.append({
                        'mentee_id': mentee.id,
                        'mentee_name': mentee.full_name,
                        'module_id': deadline.module.id,
                        'module_title': deadline.module.title,
                        'due_date': deadline.due_date,
                        'days_remaining': days_remaining,
                        'status': status,
                        'progress_percentage': progress.progress_percentage if progress else 0,
                        'is_extended': deadline.is_extended
                    })
        
        # Sort by urgency
        upcoming_deadlines.sort(key=lambda x: (
            0 if x['status'] == 'overdue' else 
            1 if x['status'] == 'urgent' else 
            2 if x['status'] == 'warning' else 3,
            x['days_remaining']
        ))
        
        return Response(upcoming_deadlines)
    
    elif user.role in ['admin', 'hr']:
        # Get all deadlines
        deadlines = OnboardingDeadline.objects.all()
        
        upcoming_deadlines = []
        for deadline in deadlines:
            days_remaining = deadline.get_days_remaining()
            
            if days_remaining <= 7 or deadline.is_overdue():
                progress = MenteeOnboardingProgress.objects.filter(
                    mentee=deadline.mentee,
                    module=deadline.module
                ).first()
                
                status = 'overdue' if deadline.is_overdue() else 'urgent' if days_remaining <= 1 else 'warning'
                
                upcoming_deadlines.append({
                    'mentee_id': deadline.mentee.id,
                    'mentee_name': deadline.mentee.full_name,
                    'mentee_department': deadline.mentee.department,
                    'module_id': deadline.module.id,
                    'module_title': deadline.module.title,
                    'due_date': deadline.due_date,
                    'days_remaining': days_remaining,
                    'status': status,
                    'progress_percentage': progress.progress_percentage if progress else 0,
                    'is_extended': deadline.is_extended
                })
        
        # Sort by urgency
        upcoming_deadlines.sort(key=lambda x: (
            0 if x['status'] == 'overdue' else 
            1 if x['status'] == 'urgent' else 
            2 if x['status'] == 'warning' else 3,
            x['days_remaining']
        ))
        
        return Response(upcoming_deadlines)
    
    return Response([])


# ================ ADDITIONAL VIEWS ================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_notifications(request):
    """
    Get current user's onboarding notifications
    """
    notifications = OnboardingNotification.objects.filter(
        recipient=request.user
    ).order_by('-sent_at')[:50]  # Last 50 notifications
    
    # Mark as read if specified
    mark_read = request.query_params.get('mark_read', 'false').lower() == 'true'
    if mark_read:
        unread_notifications = notifications.filter(is_read=False)
        unread_notifications.update(is_read=True, read_at=now())
    
    notification_data = []
    for notification in notifications:
        notification_data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'sent_at': notification.sent_at,
            'is_read': notification.is_read,
            'read_at': notification.read_at,
            'module_id': notification.related_module.id if notification.related_module else None,
            'module_title': notification.related_module.title if notification.related_module else None,
            'progress_id': notification.related_progress.id if notification.related_progress else None
        })
    
    # Count unread notifications
    unread_count = OnboardingNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return Response({
        'notifications': notification_data,
        'unread_count': unread_count,
        'total_count': notifications.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    notification = get_object_or_404(OnboardingNotification, id=notification_id, recipient=request.user)
    
    if not notification.is_read:
        notification.mark_as_read()
    
    return Response({
        'message': 'Notification marked as read',
        'notification_id': notification.id
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """
    Mark all notifications as read for current user
    """
    unread_notifications = OnboardingNotification.objects.filter(
        recipient=request.user,
        is_read=False
    )
    
    updated_count = unread_notifications.update(is_read=True, read_at=now())
    
    return Response({
        'message': f'Marked {updated_count} notifications as read'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extend_deadline(request, progress_id):
    """
    Extend the deadline for a module (Admin/HR/Mentor only)
    """
    progress = get_object_or_404(MenteeOnboardingProgress, id=progress_id)
    
    # Check permissions
    if request.user.role not in ['admin', 'hr', 'mentor']:
        return Response(
            {'error': 'You do not have permission to extend deadlines'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Mentors can only extend for mentees in their department
    if request.user.role == 'mentor' and progress.mentee.department != request.user.department:
        return Response(
            {'error': 'You can only extend deadlines for mentees in your department'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    new_due_date_str = request.data.get('new_due_date')
    reason = request.data.get('reason', '')
    
    if not new_due_date_str:
        return Response(
            {'error': 'new_due_date is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from datetime import datetime
        new_due_date = datetime.fromisoformat(new_due_date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get or create deadline
    deadline, created = OnboardingDeadline.objects.get_or_create(
        module=progress.module,
        mentee=progress.mentee,
        defaults={
            'due_date': new_due_date,
            'original_due_date': new_due_date
        }
    )
    
    if not created:
        deadline.extend_deadline(new_due_date, reason, request.user)
    
    # Update progress due date
    progress.due_date = new_due_date
    progress.save()
    
    # Send notification
    title = f"Deadline Extended: {progress.module.title}"
    message = f"""
    Hello {progress.mentee.full_name},
    
    The deadline for your onboarding module "{progress.module.title}" has been extended.
    
    New Due Date: {new_due_date.strftime('%Y-%m-%d')}
    Reason: {reason if reason else 'No reason provided'}
    
    Please continue working on the module and aim to complete it by the new deadline.
    
    Best regards,
    Mentorship Program Team
    """
    
    send_onboarding_notification(
        recipient=progress.mentee,
        notification_type='deadline_approaching',
        title=title,
        message=message,
        related_module=progress.module,
        related_progress=progress
    )
    
    return Response({
        'message': 'Deadline extended successfully',
        'new_due_date': new_due_date,
        'reason': reason,
        'extended_by': request.user.full_name
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_modules(request):
    """
    Get modules for current user's department
    """
    user = request.user
    
    if user.role == 'mentee':
        department = user.department
    elif user.role == 'mentor':
        department = user.department
    else:
        # Admin/HR can specify department
        department = request.query_params.get('department')
    
    if not department:
        return Response(
            {'error': 'Department is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get core modules and department-specific modules
    modules = OnboardingModule.objects.filter(
        Q(module_type='core') | Q(department=department),
        is_active=True
    ).order_by('order')
    
    serializer = OnboardingModuleSerializer(modules, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_progress_health(request):
    """
    Check the health of mentee's onboarding progress
    Returns warnings and suggestions
    """
    if request.user.role != 'mentee':
        return Response(
            {'error': 'Only mentees can check progress health'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    progress_records = MenteeOnboardingProgress.objects.filter(
        mentee=request.user
    ).select_related('module')
    
    warnings = []
    suggestions = []
    
    for progress in progress_records:
        # Check for overdue modules
        if progress.is_overdue():
            warnings.append({
                'type': 'overdue',
                'module_id': progress.module.id,
                'module_title': progress.module.title,
                'message': f'Module "{progress.module.title}" is overdue. Please complete it as soon as possible.'
            })
        
        # Check for slow progress
        speed = progress.get_progress_speed()
        if speed > 0 and speed < 10:  # Less than 10% per day
            warnings.append({
                'type': 'slow_progress',
                'module_id': progress.module.id,
                'module_title': progress.module.title,
                'message': f'Progress on "{progress.module.title}" is slower than expected. Consider increasing your pace.'
            })
        
        # Check for modules not started but assigned a while ago
        if progress.status == 'not_started':
            assigned_days = (now() - progress.assigned_at).days
            if assigned_days >= 3:
                suggestions.append({
                    'type': 'not_started',
                    'module_id': progress.module.id,
                    'module_title': progress.module.title,
                    'message': f'Consider starting "{progress.module.title}" soon.'
                })
    
    # Calculate overall progress
    overall_progress = calculate_overall_progress(request.user)
    
    # Generate overall suggestions
    if overall_progress['overall_percentage'] < 30 and len(warnings) > 2:
        suggestions.append({
            'type': 'overall_slow',
            'message': 'Your overall onboarding progress is slow. Consider focusing more time on onboarding.'
        })
    
    return Response({
        'warnings': warnings,
        'suggestions': suggestions,
        'overall_progress': overall_progress['overall_percentage'],
        'total_modules': overall_progress['total_modules'],
        'completed_modules': overall_progress['completed_modules']
    })





@api_view(['POST'])
@permission_classes([AllowAny])
def send_reminder(request):
    """Send reminder email to mentee about onboarding progress."""
    logger.info("Received reminder request with data: %s", request.data)
    
    serializer = SendReminderSerializer(data=request.data)
    
    if serializer.is_valid():
        # FIXED: Changed from 'recepient_id' to 'recipient_id'
        recipient_id = serializer.validated_data['recipient_id']
        notification_type = serializer.validated_data['notification_type']
        title = serializer.validated_data['title']
        message = serializer.validated_data['message']
        
        # Validate inputs
        if not recipient_id:
            logger.error("Recipient ID is empty.")
            return Response(
                {"error": "Recipient ID field cannot be empty."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not notification_type.strip():
            logger.error("Notification type field is empty.")
            return Response(
                {"error": "Notification type field cannot be empty."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not title.strip():
            logger.error("Title field is empty.")
            return Response(
                {"error": "Title field cannot be empty."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not message.strip():
            logger.error("Message field is empty.")
            return Response(
                {"error": "Message field cannot be empty."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # FIXED: Get mentee directly from CustomUser, not MenteeOnboardingProgress
        try:
            mentee = CustomUser.objects.get(id=recipient_id, role='mentee')
            email = mentee.email
            logger.info(f"Found mentee: {mentee.full_name} ({email})")
        except CustomUser.DoesNotExist:
            logger.error("Mentee not found for recipient ID: %s", recipient_id)
            return Response(
                {"error": "Mentee not found for the given recipient ID."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Get mentee's progress summary for context
        try:
            progress_summary = MenteeOnboardingProgress.objects.filter(mentee=mentee)
            total_modules = progress_summary.count()
            completed_modules = progress_summary.filter(status='completed').count()
            in_progress_modules = progress_summary.filter(status='in_progress').count()
        except Exception as e:
            logger.warning(f"Could not fetch progress summary: {e}")
            total_modules = 0
            completed_modules = 0
            in_progress_modules = 0

        # Create onboarding notification record
        try:
            OnboardingNotification.objects.create(
                recipient=mentee,
                notification_type=notification_type,
                title=title,
                message=message
            )
            logger.info("Notification record created successfully")
        except Exception as e:
            logger.warning(f"Failed to create notification record: {e}")

        # Prepare and send email
        try:
            full_message = f"""
Hello {mentee.full_name},

{message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your Current Onboarding Progress:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Total Modules: {total_modules}
- Completed: {completed_modules}
- In Progress: {in_progress_modules}
- Not Started: {total_modules - completed_modules - in_progress_modules}
- Department: {mentee.department}

Please log in to the mentorship portal to continue your onboarding journey.

Best regards,
Onboarding Team

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated message. Please do not reply to this email.
            """
            
            send_mail(
                subject=title,
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"Reminder email sent successfully to {email}")
            
            return Response({
                "message": f"Reminder sent successfully to {mentee.full_name}",
                "mentee_name": mentee.full_name,
                "mentee_email": email,
                "modules_completed": completed_modules,
                "total_modules": total_modules
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"An error occurred while sending email: {e}")
            return Response({
                "error": "Failed to send email. Please try again later.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    logger.error(f"Invalid serializer data: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)