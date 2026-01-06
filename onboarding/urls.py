from django.urls import path
from . import views

urlpatterns = [
    # Onboarding Modules
    path('modules/', views.get_onboarding_modules, name='get-onboarding-modules'),
    path('modules/create/', views.create_onboarding_module, name='create-onboarding-module'),
    path('modules/<int:pk>/', views.get_onboarding_module_detail, name='get-onboarding-module-detail'),
    path('modules/<int:pk>/update/', views.update_onboarding_module, name='update-onboarding-module'),
    path('modules/<int:pk>/delete/', views.delete_onboarding_module, name='delete-onboarding-module'),
    path('modules/statistics/', views.get_onboarding_statistics, name='get-onboarding-statistics'),
    path('modules/<int:pk>/assign/', views.assign_module_to_mentees, name='assign-module-to-mentees'),
    path('modules/<int:pk>/mentee-progress/', views.get_module_mentee_progress, name='get-module-mentee-progress'),
    path('modules/department/', views.get_department_modules, name='get-department-modules'),
    
    # Mentee Progress
    path('progress/', views.get_mentee_progress, name='get-mentee-progress'),
    path('progress/<int:pk>/', views.get_mentee_progress_detail, name='get-mentee-progress-detail'),
    path('progress/<int:pk>/start/', views.start_onboarding_module, name='start-onboarding-module'),
    path('progress/<int:pk>/complete/', views.complete_onboarding_module, name='complete-onboarding-module'),
    path('progress/<int:pk>/update-percentage/', views.update_progress_percentage, name='update-progress-percentage'),
    path('progress/<int:pk>/update-details/', views.update_progress_details, name='update-progress-details'),
    path('progress/<int:pk>/update-checklist/', views.update_checklist_item, name='update-checklist-item'),
    
    # Progress Summary
    path('progress/my-summary/', views.get_my_progress_summary, name='get-my-progress-summary'),
    path('progress/all-summary/', views.get_all_mentees_summary, name='get-all-mentees-summary'),
    path('progress/auto-assign/', views.auto_assign_modules, name='auto-assign-modules'),
    path('progress/upcoming-deadlines/', views.get_upcoming_deadlines, name='get-upcoming-deadlines'),
    path('progress/health/', views.check_progress_health, name='check-progress-health'),
    
    # Deadline Management
    path('progress/<int:progress_id>/extend-deadline/', views.extend_deadline, name='extend-deadline'),
    
    # Notifications
    path('notifications/', views.get_my_notifications, name='get-my-notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark-all-notifications-read'),

    path('reminder/send/', views.send_reminder, name='send-reminder'),
]