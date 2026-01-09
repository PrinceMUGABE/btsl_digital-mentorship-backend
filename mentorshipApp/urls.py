from django.urls import path
from . import views

urlpatterns = [
    # Department and Program related endpoints
    path('departments/', views.get_departments, name='get_departments'),
    path('departments/<int:department_id>/programs/', views.get_department_programs, name='get_department_programs'),
    
    # Mentor/Mentee availability endpoints
    path('available-mentors/', views.get_available_mentors, name='get_available_mentors'),
    path('ready-mentees/', views.get_ready_mentees, name='get_ready_mentees'),
    path('mentees-ready-for-mentorship/', views.get_mentees_ready_for_mentorship, name='get_mentees_ready_for_mentorship'),
    
    # Program CRUD endpoints
    path('programs/', views.get_programs, name='get_programs'),
    path('programs/create/', views.create_mentorship_program, name='create_mentorship_program'),
    path('programs/all/', views.list_mentorship_programs, name='list_mentorship_programs'),
    path('programs/<int:program_id>/', views.get_mentorship_program, name='get_mentorship_program'),
    path('programs/<int:program_id>/update/', views.update_mentorship_program, name='update_mentorship_program'),
    path('programs/<int:program_id>/delete/', views.delete_mentorship_program, name='delete_mentorship_program'),
    path('programs/<int:program_id>/sessions/', views.get_program_sessions, name='get_program_sessions'),
    
    # Session Template endpoints
    path('session-templates/', views.list_session_templates, name='list_session_templates'),
    path('session-templates/create/', views.create_session_template, name='create_session_template'),
    path('session-templates/<int:template_id>/', views.get_session_template, name='get_session_template'),
    
    # Mentorship CRUD endpoints
    path('mentorships/', views.list_mentorships, name='list_mentorships'),
    path('mentorships/create/', views.create_mentorship, name='create_mentorship'),
    path('mentorships/<int:mentorship_id>/', views.get_mentorship, name='get_mentorship'),
    path('mentorships/<int:mentorship_id>/update-status/', views.update_mentorship_status, name='update_mentorship_status'),
    path('mentorships/<int:mentorship_id>/goals/', views.add_mentorship_goals, name='add_mentorship_goals'),
    path('mentorships/<int:mentorship_id>/progress/', views.get_mentorship_progress, name='get_mentorship_progress'),
    path('mentorships/<int:mentorship_id>/switch-program/<int:program_id>/', views.switch_current_program, name='switch_current_program'),
    
    # Session endpoints
    path('sessions/', views.list_sessions, name='list_sessions'),
    path('sessions/create/', views.create_session, name='create_session'),
    path('sessions/<int:session_id>/', views.get_session, name='get_session'),
    path('sessions/<int:session_id>/complete/', views.mark_session_completed, name='mark_session_completed'),
    path('sessions/<int:session_id>/reschedule/', views.reschedule_session, name='reschedule_session'),
    path('sessions/<int:session_id>/cancel/', views.cancel_session, name='cancel_session'),
    
    # User-specific endpoints
    path('my-mentorships/', views.get_my_mentorships, name='get_my_mentorships'),
    path('my-active-mentorships/', views.get_my_active_mentorships, name='get_my_active_mentorships'),
    path('my-mentorships/<int:mentorship_id>/', views.get_my_mentorship_detail, name='get_my_mentorship_detail'),
    path('my-sessions/', views.get_my_sessions, name='get_my_sessions'),
    path('my-upcoming-sessions/', views.get_my_upcoming_sessions, name='get_my_upcoming_sessions'),
    path('my-dashboard/', views.get_my_dashboard, name='get_my_dashboard'),
    
    # Admin/HR specific endpoints
    path('all-mentorships/', views.get_all_mentorships, name='get_all_mentorships'),
    path('mentorships/bulk-actions/', views.bulk_mentorship_actions, name='bulk_mentorship_actions'),
    path('mentorships/<int:mentorship_id>/admin-update-status/', views.update_mentorship_status, name='admin_update_mentorship_status'),

    path('reviews/create/', views.create_mentorship_review, name='create_mentorship_review'),
    path('mentorships/<int:mentorship_id>/can-review/', views.check_can_review_mentorship, name='check_can_review_mentorship'),
    path('mentorships/<int:mentorship_id>/reviews/', views.get_mentorship_reviews, name='get_mentorship_reviews'),


    path('mentor-performance/', views.get_mentor_performance, name='get_mentor_performance'),
    path('mentor/reviews/', views.get_mentor_reviews, name='get_mentor_reviews'),
    path('mentor/dashboard/', views.get_my_dashboard, name='mentor_dashboard'),



    path('mentorships/<int:mentorship_id>/program-overview/', views.get_mentor_program_overview, name='mentor_program_overview'),
    path('mentorships/<int:mentorship_id>/programs/<int:program_id>/sessions/', views.get_mentorship_program_sessions, name='mentorship_program_sessions'),
    path('mentorships/<int:mentorship_id>/programs/<int:program_id>/schedule-session/', views.schedule_program_session, name='schedule_program_session'),
    path('sessions/<int:session_id>/update-progress/', views.update_session_progress, name='update_session_progress'),


    path('department-statistics/', views.get_department_statistics, name='department_statistics'),
    path('department/<int:department_id>/stats/', views.get_department_program_stats, name='department_program_stats'),
    path('top-performing-mentors/', views.get_top_performing_mentors, name='top_performing_mentors'),
    path('recent-activity/', views.get_recent_activity, name='recent_activity'),
    path('program/<int:program_id>/stats/', views.get_program_statistics, name='program_statistics'),
    path('mentorship/<int:mentorship_id>/detailed/', views.get_detailed_mentorship, name='detailed_mentorship'),
]
