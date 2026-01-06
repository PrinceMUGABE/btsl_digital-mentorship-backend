# mentorshipApp/permissions.py
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from .models import ChatRoom, GroupChatParticipant
from userApp.models import CustomUser



class IsMentorshipParticipantOrAdmin(permissions.BasePermission):
    """Allow participants, admin, and HR to access"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin and HR can access everything
        if request.user.role in ['admin', 'hr']:
            return True
        
        # Mentors and mentees can access their own mentorships
        return request.user.role in ['mentor', 'mentee']
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin and HR have full access
        if user.role in ['admin', 'hr']:
            return True
        
        # Mentor can access if they're the mentor
        if user.role == 'mentor' and hasattr(obj, 'mentor'):
            return obj.mentor == user
        
        # Mentee can access if they're the mentee
        if user.role == 'mentee' and hasattr(obj, 'mentee'):
            return obj.mentee == user
        
        return False
    






class IsGroupChatParticipant(permissions.BasePermission):
    """Allow only participants to access group chat"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['admin', 'hr']:
            return True
        
        return obj.participants.filter(id=request.user.id).exists()


class CanManageGroupChat(permissions.BasePermission):
    """Allow only admin/moderators to manage group chat"""
    
    def has_object_permission(self, request, view, obj):
        return obj.can_manage_chat(request.user)


class CanSendGroupMessages(permissions.BasePermission):
    """Allow only participants who can send messages"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['admin', 'hr']:
            return True
        
        try:
            participant = GroupChatParticipant.objects.get(
                chat_room=obj,
                user=request.user
            )
            return participant.can_send_messages()
        except GroupChatParticipant.DoesNotExist:
            return False