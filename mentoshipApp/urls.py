# mentorshipApp/urls.py
from django.urls import path
from . import views

urlpatterns = [

    path('available-mentors/', views.get_available_mentors, name='available-mentors'),
    path('ready-mentees/', views.get_ready_mentees, name='ready-mentees'),
    path('check-eligibility/<int:mentee_id>/', views.check_mentee_eligibility, name='check-eligibility'),
    path('bulk-actions/', views.bulk_mentorship_actions, name='bulk-actions'),

    # Department URLs
    path('departments/', views.list_departments, name='list_departments'),
    path('departments/<int:department>/programs/', views.get_department_programs, name='department_programs'),
    
    # Session Template URLs
    path('session-templates/', views.list_session_templates, name='list_session_templates'),
    path('session-templates/create/', views.create_session_template, name='create_session_template'),
    path('session-templates/<int:template_id>/', views.get_session_template, name='get_session_template'),
    
    # Program URLs
    path('programs/', views.list_mentorship_programs, name='list_programs'),
    path('programs/create/', views.create_mentorship_program, name='create_program'),
    path('programs/<int:program_id>/', views.get_mentorship_program, name='get_program'),
    path('programs/<int:program_id>/sessions/', views.get_program_sessions, name='program_sessions'),
    path('programs/<int:program_id>/update/', views.update_mentorship_program, name='update_program'),
    path('programs/<int:program_id>/delete/', views.delete_mentorship_program, name='delete_program'),
    
    # Mentorship URLs
    path('mentorships/', views.list_mentorships, name='list_mentorships'),
    path('mentorships/create/', views.create_mentorship, name='create_mentorship'),
    path('mentorships/<int:mentorship_id>/', views.get_mentorship, name='get_mentorship'),
    path('mentorships/<int:mentorship_id>/progress/', views.get_mentorship_progress, name='mentorship_progress'),
    path('mentorships/<int:mentorship_id>/status/', views.update_mentorship_status, name='update_mentorship_status'),
    path('mentorships/<int:mentorship_id>/goals/', views.add_mentorship_goals, name='add_mentorship_goals'),
    
    # Session URLs
    path('sessions/', views.list_sessions, name='list_sessions'),
    path('sessions/create/', views.create_session, name='create_session'),
    path('sessions/<int:session_id>/', views.get_session, name='get_session'),
    path('sessions/<int:session_id>/complete/', views.mark_session_completed, name='complete_session'),
    path('sessions/<int:session_id>/reschedule/', views.reschedule_session, name='reschedule_session'),
    path('sessions/<int:session_id>/cancel/', views.cancel_session, name='cancel_session'),
    


]