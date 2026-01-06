# mentorshipApp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Department URLs
    path('departments/', views.list_departments, name='list_departments'),
    path('departments/<int:department_id>/programs/', views.get_department_programs, name='department_programs'),
    
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
    
    # Chat URLs
    path('chat/rooms/', views.list_chat_rooms, name='list_chat_rooms'),
    path('chat/rooms/<int:chat_room_id>/', views.get_chat_room, name='get_chat_room'),
    path('chat/rooms/mentorship/<int:mentorship_id>/', views.get_chat_room_by_mentorship, name='get_chat_room_by_mentorship'),
    path('chat/rooms/<int:chat_room_id>/messages/', views.list_messages, name='list_messages'),
    path('chat/messages/send/', views.send_message, name='send_message'),
    path('chat/rooms/<int:chat_room_id>/mark-read/', views.mark_messages_read, name='mark_messages_read'),
    
    # Notification URLs
    path('notifications/', views.list_notifications, name='list_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/<int:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    
    # Dashboard URLs
    path('dashboard/stats/', views.get_dashboard_stats, name='dashboard_stats'),





     # Group Chat URLs
    path('group-chats/', views.list_group_chats, name='list_group_chats'),
    path('group-chats/create/', views.create_group_chat, name='create_group_chat'),
    path('group-chats/<int:group_chat_id>/', views.get_group_chat, name='get_group_chat'),
    path('group-chats/<int:group_chat_id>/add-participant/', views.add_group_chat_participant, name='add_group_chat_participant'),
    path('group-chats/<int:group_chat_id>/remove-participant/<int:user_id>/', views.remove_group_chat_participant, name='remove_group_chat_participant'),
    path('group-chats/<int:group_chat_id>/messages/', views.list_group_messages, name='list_group_messages'),
    path('group-chats/messages/send/', views.send_group_message, name='send_group_message'),
    
    # Chat Dashboard URLs
    path('chats/available/', views.get_available_chats, name='get_available_chats'),
    path('chats/department-group-chats/', views.get_department_group_chats, name='get_department_group_chats'),
    
   
    # Cross-Department Chat URLs
    path('cross-department-chats/create/', views.create_cross_department_chat, name='create_cross_department_chat'),
    path('cross-department-chats/', views.list_cross_department_chats, name='list_cross_department_chats'),
    path('cross-department-chats/<int:chat_id>/', views.get_cross_department_chat, name='get_cross_department_chat'),
    path('cross-department-chats/<int:chat_id>/participants/', views.manage_cross_department_chat_participants, name='manage_cross_department_chat_participants'),
    path('cross-department-chats/<int:chat_id>/update/', views.update_cross_department_chat, name='update_cross_department_chat'),
    path('cross-department-chats/<int:chat_id>/archive/', views.archive_cross_department_chat, name='archive_cross_department_chat'),
    path('cross-department-chats/available-users/', views.get_available_users_for_cross_department, name='get_available_users_for_cross_department'),



    # User-specific chat endpoints
    path('chats/my-chats/', views.get_my_chats, name='get_my_chats'),
    path('chats/mentor-mentee/', views.get_mentor_mentee_chats, name='get_mentor_mentee_chats'),
    path('chats/mentee-staff/', views.get_mentee_chat_with_staff, name='get_mentee_chat_with_staff'),
    path('chats/department-groups/', views.get_department_group_chats_for_user, name='get_department_group_chats_for_user'),
    path('chats/summary/', views.get_chat_summary, name='get_chat_summary'),
    path('chats/search/', views.search_my_chats, name='search_my_chats'),
]