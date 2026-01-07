from django.urls import path
from . import views

urlpatterns = [
    # One-on-One Chat URLs
    path('rooms/', views.list_chat_rooms, name='list_chat_rooms'),
    path('rooms/<int:chat_room_id>/', views.get_chat_room, name='get_chat_room'),
    path('rooms/mentorship/<int:mentorship_id>/', views.get_chat_room_by_mentorship, name='get_chat_room_by_mentorship'),
    path('rooms/<int:chat_room_id>/messages/', views.list_messages, name='list_messages'),
    path('messages/send/', views.send_message, name='send_message'),
    path('rooms/<int:chat_room_id>/mark-read/', views.mark_messages_read, name='mark_messages_read'),
    
    # Group Chat URLs
    path('group-chats/', views.list_group_chats, name='list_group_chats'),
    path('group-chats/create/', views.create_group_chat, name='create_group_chat'),
    path('group-chats/<int:group_chat_id>/', views.get_group_chat, name='get_group_chat'),
    path('group-chats/<int:group_chat_id>/add-participant/', views.add_group_chat_participant, name='add_group_chat_participant'),
    path('group-chats/<int:group_chat_id>/remove-participant/<int:user_id>/', views.remove_group_chat_participant, name='remove_group_chat_participant'),
    path('group-chats/<int:group_chat_id>/messages/', views.list_group_messages, name='list_group_messages'),
    path('group-chats/messages/send/', views.send_group_message, name='send_group_message'),
    
    # Chat Dashboard URLs
    path('available/', views.get_available_chats, name='get_available_chats'),
    path('department-group-chats/', views.get_department_group_chats, name='get_department_group_chats'),
    
    # Cross-Department Chat URLs
    path('cross-department-chats/create/', views.create_cross_department_chat, name='create_cross_department_chat'),
    path('cross-department-chats/', views.list_cross_department_chats, name='list_cross_department_chats'),
    path('cross-department-chats/<int:chat_id>/', views.get_cross_department_chat, name='get_cross_department_chat'),
    path('cross-department-chats/<int:chat_id>/participants/', views.manage_cross_department_chat_participants, name='manage_cross_department_chat_participants'),
    path('cross-department-chats/<int:chat_id>/update/', views.update_cross_department_chat, name='update_cross_department_chat'),
    path('cross-department-chats/<int:chat_id>/archive/', views.archive_cross_department_chat, name='archive_cross_department_chat'),
    path('cross-department-chats/available-users/', views.get_available_users_for_cross_department, name='get_available_users_for_cross_department'),
    
    # User-specific chat endpoints
    path('my-chats/', views.get_my_chats, name='get_my_chats'),
    path('mentor-mentee/', views.get_mentor_mentee_chats, name='get_mentor_mentee_chats'),
    path('mentee-staff/', views.get_mentee_chat_with_staff, name='get_mentee_chat_with_staff'),
    path('department-groups/', views.get_department_group_chats_for_user, name='get_department_group_chats_for_user'),
    path('summary/', views.get_chat_summary, name='get_chat_summary'),
    path('search/', views.search_my_chats, name='search_my_chats'),
    path('dashboard/', views.get_chat_dashboard, name='get_chat_dashboard'),
    
   
    
]