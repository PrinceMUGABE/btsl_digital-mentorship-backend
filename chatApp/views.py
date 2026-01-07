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

from .models import (
    ChatType, GroupChatMessage, GroupChatParticipant, GroupChatRoom, Mentorship,
    ChatRoom, Message
)
from .serializers import (
    AddParticipantSerializer, GroupChatCreateSerializer, GroupChatMessageSerializer, GroupChatParticipantSerializer, GroupChatRoomSerializer, GroupMessageCreateSerializer,
    MessageSerializer, MessageCreateSerializer,
    ChatRoomSerializer
    
)
from userApp.models import CustomUser

# ==================== CHAT ROOM VIEWS ====================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_chat_rooms(request):
    """List all chat rooms for the authenticated user"""
    try:
        user = request.user
        
        if user.role == 'mentee':
            chat_rooms = ChatRoom.objects.filter(mentorship__mentee=user, is_active=True)
        elif user.role == 'mentor':
            chat_rooms = ChatRoom.objects.filter(mentorship__mentor=user, is_active=True)
        elif user.role in ['admin', 'hr']:
            chat_rooms = ChatRoom.objects.filter(is_active=True)
        else:
            return Response({
                'error': 'Invalid user role'
            }, status=status.HTTP_403_FORBIDDEN)
        
        chat_rooms = chat_rooms.select_related(
            'mentorship__mentor', 'mentorship__mentee', 'mentorship__program'
        )
        
        serializer = ChatRoomSerializer(chat_rooms, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': chat_rooms.count(),
            'chat_rooms': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching chat rooms',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_room(request, chat_room_id):
    """Get chat room details"""
    try:
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentee' and chat_room.mentorship.mentee != user:
            return Response({
                'error': 'Permission denied. You can only access your own chat rooms'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentor' and chat_room.mentorship.mentor != user:
            return Response({
                'error': 'Permission denied. You can only access your own chat rooms'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role not in ['admin', 'hr', 'mentor', 'mentee']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ChatRoomSerializer(chat_room, context={'request': request})
        return Response({
            'success': True,
            'chat_room': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Chat room not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_room_by_mentorship(request, mentorship_id):
    """Get chat room by mentorship ID"""
    try:
        mentorship = get_object_or_404(Mentorship, id=mentorship_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentee' and mentorship.mentee != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentor' and mentorship.mentor != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role not in ['admin', 'hr', 'mentor', 'mentee']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get or create chat room
        chat_room, created = ChatRoom.objects.get_or_create(
            mentorship=mentorship,
            defaults={'is_active': True}
        )
        
        if created:
            # Send notifications
            ChatNotification.objects.create(
                recipient=mentorship.mentee,
                chat_room=chat_room,
                notification_type='case_assigned',
                title='Chat Room Created',
                message=f'You can now chat with your mentor for {mentorship.program.name}'
            )
            
            ChatNotification.objects.create(
                recipient=mentorship.mentor,
                chat_room=chat_room,
                notification_type='case_assigned',
                title='Chat Room Created',
                message=f'You can now chat with your mentee for {mentorship.program.name}'
            )
        
        serializer = ChatRoomSerializer(chat_room, context={'request': request})
        return Response({
            'success': True,
            'chat_room': serializer.data,
            'created': created
        }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to get or create chat room',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== MESSAGE VIEWS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_messages(request, chat_room_id):
    """List messages in a chat room"""
    try:
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentee' and chat_room.mentorship.mentee != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentor' and chat_room.mentorship.mentor != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role not in ['admin', 'hr', 'mentor', 'mentee']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Mark unread messages as read
        unread_messages = chat_room.messages.filter(
            is_deleted=False,
            is_read=False
        ).exclude(sender=user)
        
        for message in unread_messages:
            message.mark_as_read()
        
        # Get messages with pagination
        limit = request.query_params.get('limit', 50)
        try:
            limit = int(limit)
            if limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 50
        
        messages = chat_room.messages.filter(is_deleted=False).order_by('-created_at')[:limit]
        messages = list(reversed(messages))
        
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': len(messages),
            'messages': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching messages',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, chat_room_id):
    """Send a message in a chat room"""
    try:
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentee' and chat_room.mentorship.mentee != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentor' and chat_room.mentorship.mentor != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role not in ['admin', 'hr', 'mentor', 'mentee']:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        content = request.data.get('content')
        message_type = request.data.get('message_type', 'text')
        attachment = request.FILES.get('attachment')
        
        if not content or not content.strip():
            return Response({
                'error': 'Message content cannot be empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(content) > 5000:
            return Response({
                'error': 'Message is too long (max 5000 characters)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if message_type not in dict(Message.MESSAGE_TYPES).keys():
            return Response({
                'error': f'Invalid message type. Must be one of: {", ".join(dict(Message.MESSAGE_TYPES).keys())}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate attachment if provided
        if attachment:
            max_size = 10 * 1024 * 1024  # 10MB
            if attachment.size > max_size:
                return Response({
                    'error': 'File size cannot exceed 10MB'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif',
                'application/pdf', 'text/plain',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
            if attachment.content_type not in allowed_types:
                return Response({
                    'error': 'File type not allowed'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create message
        message = Message.objects.create(
            chat_room=chat_room,
            sender=user,
            message_type=message_type,
            content=content,
            attachment=attachment
        )
        
        # Update chat room timestamp
        chat_room.updated_at = now()
        chat_room.save(update_fields=['updated_at'])
        
        # Send real-time notification via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat_room.id}",
            {
                'type': 'chat_message',
                'message': MessageSerializer(message, context={'request': request}).data
            }
        )
        
        # Create notification for recipient
        recipient = chat_room.mentorship.mentor if user == chat_room.mentorship.mentee else chat_room.mentorship.mentee
        ChatNotification.objects.create(
            recipient=recipient,
            sender=user,
            chat_room=chat_room,
            notification_type='new_message',
            title='New Message',
            message=f'{user.full_name} sent you a message'
        )
        
        return Response({
            'success': True,
            'message': 'Message sent successfully',
            'data': MessageSerializer(message, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to send message',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_messages_read(request, chat_room_id):
    """Mark all messages in a chat room as read"""
    try:
        chat_room = get_object_or_404(ChatRoom, id=chat_room_id)
        user = request.user
        
        # Check permissions
        if user.role == 'mentee' and chat_room.mentorship.mentee != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if user.role == 'mentor' and chat_room.mentorship.mentor != user:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Mark messages as read
        unread_messages = chat_room.messages.filter(
            is_deleted=False,
            is_read=False
        ).exclude(sender=user)
        
        count = unread_messages.count()
        for message in unread_messages:
            message.mark_as_read()
        
        return Response({
            'success': True,
            'message': f'{count} message(s) marked as read'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to mark messages as read',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== NOTIFICATION VIEWS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    """List all notifications for the authenticated user"""
    try:
        user = request.user
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        
        notifications = ChatNotification.objects.filter(recipient=user)
        
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        notifications = notifications.select_related('sender', 'chat_room__mentorship')
        
        # Pagination
        limit = request.query_params.get('limit', 20)
        try:
            limit = int(limit)
            if limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 20
        
        notifications = notifications[:limit]
        
        from .serializers import ChatNotificationSerializer
        serializer = ChatNotificationSerializer(notifications, many=True)
        
        return Response({
            'success': True,
            'count': notifications.count(),
            'unread_count': ChatNotification.objects.filter(recipient=user, is_read=False).count(),
            'notifications': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching notifications',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(
            ChatNotification, 
            id=notification_id, 
            recipient=request.user
        )
        
        if notification.is_read:
            return Response({
                'message': 'Notification is already marked as read'
            }, status=status.HTTP_200_OK)
        
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Notification not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read for the authenticated user"""
    try:
        count = ChatNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'success': True,
            'message': f'{count} notification(s) marked as read'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to mark notifications as read',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        notification = get_object_or_404(
            ChatNotification, 
            id=notification_id, 
            recipient=request.user
        )
        
        notification.delete()
        
        return Response({
            'success': True,
            'message': 'Notification deleted successfully'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Notification not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)



# ==================== GROUP CHAT VIEWS ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_group_chats(request):
    """List all group chats the user participates in"""
    try:
        user = request.user
        chat_type = request.query_params.get('type')
        department = request.query_params.get('department')
        
        # Get group chats where user is a participant
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        )
        
        # Apply filters
        if chat_type:
            if chat_type not in dict(ChatType.choices).keys():
                return Response({
                    'error': f'Invalid chat type. Must be one of: {", ".join(dict(ChatType.choices).keys())}'
                }, status=status.HTTP_400_BAD_REQUEST)
            group_chats = group_chats.filter(chat_type=chat_type)
        
        if department:
            group_chats = group_chats.filter(department=department)
        
        group_chats = group_chats.select_related('mentorship', 'created_by')
        
        serializer = GroupChatRoomSerializer(group_chats, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': group_chats.count(),
            'group_chats': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching group chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_group_chat(request):
    """Create a new group chat (Admin/HR only)"""
    try:
        if request.user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can create group chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = GroupChatCreateSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Create group chat
        group_chat = GroupChatRoom.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            chat_type=data['chat_type'],
            department=data.get('department', ''),
            mentorship_id=data.get('mentorship_id'),
            created_by=request.user
        )
        
        # Add creator as admin
        group_chat.add_participant(request.user, added_by=request.user, role='admin')
        
        # Add other participants
        participant_ids = data.get('participant_ids', [])
        for user_id in participant_ids:
            try:
                user = CustomUser.objects.get(id=user_id)
                group_chat.add_participant(user, added_by=request.user)
            except CustomUser.DoesNotExist:
                continue
        
        return Response({
            'success': True,
            'message': 'Group chat created successfully',
            'group_chat': GroupChatRoomSerializer(group_chat, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to create group chat',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_group_chat(request, group_chat_id):
    """Get group chat details"""
    try:
        group_chat = get_object_or_404(GroupChatRoom, id=group_chat_id)
        user = request.user
        
        # Check if user is participant
        if not group_chat.participants.filter(id=user.id).exists():
            if user.role not in ['admin', 'hr']:
                return Response({
                    'error': 'Permission denied. You are not a participant in this chat'
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = GroupChatRoomSerializer(group_chat, context={'request': request})
        return Response({
            'success': True,
            'group_chat': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Group chat not found',
            'detail': str(e)
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_group_chat_participant(request, group_chat_id):
    """Add participant to group chat"""
    try:
        group_chat = get_object_or_404(GroupChatRoom, id=group_chat_id)
        
        # Check if user can manage this chat
        if not group_chat.can_manage_chat(request.user):
            return Response({
                'error': 'Permission denied. You cannot manage this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = AddParticipantSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        user = get_object_or_404(CustomUser, id=data['user_id'])
        
        # Check if user is already a participant
        if group_chat.participants.filter(id=user.id).exists():
            return Response({
                'error': 'User is already a participant in this chat'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check department constraint for department chats
        if group_chat.chat_type == 'department_group' and group_chat.department:
            if user.department != group_chat.department:
                return Response({
                    'error': f'User must be in {group_chat.department} department to join this chat'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Add participant
        participant = group_chat.add_participant(
            user, 
            added_by=request.user,
            role=data['role']
        )
        
        return Response({
            'success': True,
            'message': f'Added {user.full_name} to the group chat',
            'participant': GroupChatParticipantSerializer(participant).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to add participant',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_group_chat_participant(request, group_chat_id, user_id):
    """Remove participant from group chat"""
    try:
        group_chat = get_object_or_404(GroupChatRoom, id=group_chat_id)
        
        # Check if user can manage this chat
        if not group_chat.can_manage_chat(request.user):
            return Response({
                'error': 'Permission denied. You cannot manage this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        user = get_object_or_404(CustomUser, id=user_id)
        
        # Check if user is a participant
        if not group_chat.participants.filter(id=user.id).exists():
            return Response({
                'error': 'User is not a participant in this chat'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cannot remove yourself if you're the only admin
        if user == request.user:
            admin_count = GroupChatParticipant.objects.filter(
                chat_room=group_chat,
                role='admin'
            ).count()
            if admin_count <= 1:
                return Response({
                    'error': 'Cannot remove yourself as the only admin. Transfer admin role first.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Remove participant
        group_chat.remove_participant(user)
        
        return Response({
            'success': True,
            'message': f'Removed {user.full_name} from the group chat'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to remove participant',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_group_message(request):
    """Send message to group chat"""
    try:
        serializer = GroupMessageCreateSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'error': 'Validation failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        group_chat = get_object_or_404(GroupChatRoom, id=data['chat_room_id'])
        
        # Check if user is a participant
        if not group_chat.participants.filter(id=request.user.id).exists():
            return Response({
                'error': 'You are not a participant in this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if participant can send messages
        participant = GroupChatParticipant.objects.filter(
            chat_room=group_chat,
            user=request.user
        ).first()
        
        if participant and not participant.can_send_messages():
            return Response({
                'error': 'You are muted in this chat room'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Create message
        message = GroupChatMessage.objects.create(
            chat_room=group_chat,
            sender=request.user,
            message_type=data['message_type'],
            content=data['content'],
            attachment=data.get('attachment'),
            reply_to_id=data.get('reply_to_id')
        )
        
        # Update participant's last read time
        if participant:
            participant.last_read_at = now()
            participant.save(update_fields=['last_read_at'])
        
        return Response({
            'success': True,
            'message': 'Message sent successfully',
            'group_message': GroupChatMessageSerializer(message, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to send message',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_group_messages(request, group_chat_id):
    """List messages in a group chat"""
    try:
        group_chat = get_object_or_404(GroupChatRoom, id=group_chat_id)
        user = request.user
        
        # Check if user is participant
        if not group_chat.participants.filter(id=user.id).exists():
            if user.role not in ['admin', 'hr']:
                return Response({
                    'error': 'Permission denied. You are not a participant in this chat'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Mark unread messages as read for this user
        unread_messages = group_chat.group_messages.filter(
            is_deleted=False
        ).exclude(
            read_statuses__user=user
        )
        
        for message in unread_messages:
            message.mark_as_read_by_user(user)
        
        # Update participant's last read time
        participant = GroupChatParticipant.objects.filter(
            chat_room=group_chat,
            user=user
        ).first()
        
        if participant:
            participant.last_read_at = now()
            participant.save(update_fields=['last_read_at'])
        
        # Get messages with pagination
        limit = request.query_params.get('limit', 50)
        try:
            limit = int(limit)
            if limit > 100:
                limit = 100
        except (ValueError, TypeError):
            limit = 50
        
        messages = group_chat.group_messages.filter(
            is_deleted=False
        ).order_by('-created_at')[:limit]
        messages = list(reversed(messages))
        
        serializer = GroupChatMessageSerializer(messages, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': len(messages),
            'messages': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'An error occurred while fetching messages',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_chats(request):
    """Get all available chats for a user (one-on-one and group)"""
    try:
        user = request.user
        
        # Get one-on-one chats
        one_on_one_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        ).select_related('user1', 'user2')
        
        # Get group chats
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        )
        
        # Get mentorship info for one-on-one chats
        one_on_one_data = []
        for chat in one_on_one_chats:
            other_user = chat.user2 if chat.user1 == user else chat.user1
            one_on_one_data.append({
                'id': f"one_on_one_{chat.id}",
                'type': 'one_on_one',
                'chat_id': chat.id,
                'other_user': {
                    'id': other_user.id,
                    'full_name': other_user.full_name,
                    'role': other_user.role,
                    'department': other_user.department
                },
                'chat_type': chat.chat_type,
                'last_message': getattr(chat.messages.filter(is_deleted=False).last(), 'content', ''),
                'unread_count': chat.messages.filter(is_deleted=False, is_read=False).exclude(sender=user).count(),
                'updated_at': chat.updated_at
            })
        
        # Get group chat info
        group_chat_data = []
        for chat in group_chats:
            group_chat_data.append({
                'id': f"group_{chat.id}",
                'type': 'group',
                'chat_id': chat.id,
                'name': chat.name,
                'chat_type': chat.chat_type,
                'department': chat.department,
                'participant_count': chat.participants.count(),
                'last_message': getattr(chat.group_messages.filter(is_deleted=False).last(), 'content', ''),
                'unread_count': get_group_chat_unread_count(chat, user),
                'updated_at': chat.updated_at,
                'can_manage': chat.can_manage_chat(user)
            })
        
        # Combine and sort by last activity
        all_chats = one_on_one_data + group_chat_data
        all_chats.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return Response({
            'success': True,
            'chats': all_chats
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch available chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_group_chat_unread_count(chat, user):
    """Helper function to get unread count for group chat"""
    try:
        participant = GroupChatParticipant.objects.filter(
            chat_room=chat,
            user=user
        ).first()
        
        if participant and participant.last_read_at:
            return chat.group_messages.filter(
                created_at__gt=participant.last_read_at,
                is_deleted=False
            ).exclude(sender=user).count()
        else:
            return chat.group_messages.filter(is_deleted=False).exclude(sender=user).count()
    except:
        return 0


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_group_chats(request):
    """Get all department-level group chats"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can access all department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        department = request.query_params.get('department')
        
        group_chats = GroupChatRoom.objects.filter(
            chat_type='department_group',
            is_active=True,
            is_archived=False
        )
        
        if department:
            group_chats = group_chats.filter(department=department)
        
        serializer = GroupChatRoomSerializer(group_chats, many=True, context={'request': request})
        return Response({
            'success': True,
            'count': group_chats.count(),
            'group_chats': serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch department group chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_chats(request):
    """Get all chats for the logged-in user (both one-on-one and group chats)"""
    try:
        user = request.user
        
        if user.role not in ['mentor', 'mentee']:
            return Response({
                'error': 'This endpoint is for mentors and mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get one-on-one chats where user is a participant
        one_on_one_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        ).select_related('user1', 'user2', 'mentorship')
        
        # Get group chats where user is a participant
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        ).select_related('mentorship', 'created_by')
        
        # Process one-on-one chats
        one_on_one_data = []
        for chat in one_on_one_chats:
            other_user = chat.user2 if chat.user1 == user else chat.user1
            mentorship_info = None
            
            if chat.mentorship:
                mentorship_info = {
                    'id': chat.mentorship.id,
                    'program_name': chat.mentorship.program.name,
                    'status': chat.mentorship.status
                }
            
            last_message = chat.messages.filter(is_deleted=False).last()
            unread_count = chat.messages.filter(
                is_deleted=False,
                is_read=False
            ).exclude(sender=user).count()
            
            one_on_one_data.append({
                'chat_type': 'one_on_one',
                'chat_id': chat.id,
                'chat_room_name': f"Chat with {other_user.full_name}",
                'other_user': {
                    'id': other_user.id,
                    'full_name': other_user.full_name,
                    'role': other_user.role,
                    'department': other_user.department,
                    'avatar': None  # Add if you have avatar field
                },
                'mentorship_info': mentorship_info,
                'last_message': {
                    'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'sender_id': last_message.sender.id if last_message else None,
                    'sender_name': last_message.sender.full_name if last_message else None,
                    'timestamp': last_message.created_at if last_message else None
                },
                'unread_count': unread_count,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at
            })
        
        # Process group chats
        group_chat_data = []
        for chat in group_chats:
            # Get participant info for this user
            participant = GroupChatParticipant.objects.filter(
                chat_room=chat,
                user=user
            ).first()
            
            last_message = chat.group_messages.filter(is_deleted=False).last()
            
            # Calculate unread messages
            unread_count = 0
            if participant and participant.last_read_at:
                unread_count = chat.group_messages.filter(
                    created_at__gt=participant.last_read_at,
                    is_deleted=False
                ).exclude(sender=user).count()
            else:
                unread_count = chat.group_messages.filter(
                    is_deleted=False
                ).exclude(sender=user).count()
            
            # Get other participants info
            other_participants = chat.participants.exclude(id=user.id)
            other_participants_data = []
            
            for participant_user in other_participants[:5]:  # Limit to 5
                other_participants_data.append({
                    'id': participant_user.id,
                    'full_name': participant_user.full_name,
                    'role': participant_user.role
                })
            
            group_chat_data.append({
                'chat_type': 'group',
                'chat_id': chat.id,
                'chat_room_name': chat.name,
                'description': chat.description,
                'chat_type_display': chat.get_chat_type_display(),
                'department': chat.department,
                'participant_role': participant.role if participant else 'member',
                'is_muted': participant.is_muted if participant else False,
                'other_participants': other_participants_data,
                'total_participants': chat.participants.count(),
                'mentorship_info': {
                    'id': chat.mentorship.id,
                    'program_name': chat.mentorship.program.name,
                    'mentor_name': chat.mentorship.mentor.full_name,
                    'mentee_name': chat.mentorship.mentee.full_name
                } if chat.mentorship else None,
                'last_message': {
                    'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'sender_id': last_message.sender.id if last_message else None,
                    'sender_name': last_message.sender.full_name if last_message else None,
                    'message_type': last_message.message_type if last_message else None,
                    'timestamp': last_message.created_at if last_message else None
                },
                'unread_count': unread_count,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at,
                'can_manage': chat.can_manage_chat(user)
            })
        
        # Combine and sort by last activity
        all_chats = one_on_one_data + group_chat_data
        all_chats.sort(key=lambda x: x['updated_at'], reverse=True)
        
        # Get statistics
        total_chats = len(all_chats)
        total_unread = sum(chat['unread_count'] for chat in all_chats)
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'role': user.role,
                'department': user.department
            },
            'stats': {
                'total_chats': total_chats,
                'total_unread': total_unread,
                'one_on_one_chats': len(one_on_one_data),
                'group_chats': len(group_chat_data)
            },
            'chats': all_chats
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch your chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentor_mentee_chats(request):
    """Get all chats specifically between mentor and mentee"""
    try:
        user = request.user
        
        if user.role not in ['mentor', 'mentee']:
            return Response({
                'error': 'This endpoint is for mentors and mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all active mentorships for this user
        if user.role == 'mentor':
            mentorships = Mentorship.objects.filter(
                mentor=user,
                status__in=['active', 'pending']
            ).select_related('mentee', 'program')
        else:  # mentee
            mentorships = Mentorship.objects.filter(
                mentee=user,
                status__in=['active', 'pending']
            ).select_related('mentor', 'program')
        
        chat_data = []
        
        for mentorship in mentorships:
            # Get one-on-one chat
            one_on_one_chat = ChatRoom.objects.filter(
                mentorship=mentorship,
                chat_type='mentor_mentee',
                is_active=True
            ).first()
            
            # Get mentorship group chat
            group_chat = GroupChatRoom.objects.filter(
                mentorship=mentorship,
                chat_type='mentorship_group',
                is_active=True,
                is_archived=False
            ).first()
            
            other_user = mentorship.mentor if user.role == 'mentee' else mentorship.mentee
            
            # One-on-one chat data
            if one_on_one_chat:
                last_message = one_on_one_chat.messages.filter(is_deleted=False).last()
                unread_count = one_on_one_chat.messages.filter(
                    is_deleted=False,
                    is_read=False
                ).exclude(sender=user).count()
                
                chat_data.append({
                    'chat_type': 'one_on_one',
                    'chat_id': one_on_one_chat.id,
                    'chat_name': f"Direct Chat with {other_user.full_name}",
                    'mentorship_id': mentorship.id,
                    'program_name': mentorship.program.name,
                    'program_id': mentorship.program.id,
                    'other_user': {
                        'id': other_user.id,
                        'full_name': other_user.full_name,
                        'role': other_user.role
                    },
                    'last_message': {
                        'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                        'timestamp': last_message.created_at if last_message else None
                    },
                    'unread_count': unread_count,
                    'updated_at': one_on_one_chat.updated_at
                })
            
            # Group chat data
            if group_chat:
                last_message = group_chat.group_messages.filter(is_deleted=False).last()
                
                # Calculate unread messages
                participant = GroupChatParticipant.objects.filter(
                    chat_room=group_chat,
                    user=user
                ).first()
                
                unread_count = 0
                if participant and participant.last_read_at:
                    unread_count = group_chat.group_messages.filter(
                        created_at__gt=participant.last_read_at,
                        is_deleted=False
                    ).exclude(sender=user).count()
                else:
                    unread_count = group_chat.group_messages.filter(
                        is_deleted=False
                    ).exclude(sender=user).count()
                
                # Get admin/HR participants
                admin_hr_participants = group_chat.participants.filter(
                    role__in=['admin', 'hr']
                ).values('id', 'full_name', 'role')[:3]  # Limit to 3
                
                chat_data.append({
                    'chat_type': 'group',
                    'chat_id': group_chat.id,
                    'chat_name': group_chat.name,
                    'description': group_chat.description,
                    'mentorship_id': mentorship.id,
                    'program_name': mentorship.program.name,
                    'program_id': mentorship.program.id,
                    'other_user': {
                        'id': other_user.id,
                        'full_name': other_user.full_name,
                        'role': other_user.user.role
                    },
                    'admin_hr_participants': list(admin_hr_participants),
                    'participant_count': group_chat.participants.count(),
                    'last_message': {
                        'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                        'sender': last_message.sender.full_name if last_message else None,
                        'timestamp': last_message.created_at if last_message else None
                    },
                    'unread_count': unread_count,
                    'updated_at': group_chat.updated_at
                })
        
        # Sort by last activity
        chat_data.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return Response({
            'success': True,
            'user_role': user.role,
            'total_mentorships': mentorships.count(),
            'total_chats': len(chat_data),
            'chats': chat_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch mentor-mentee chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mentee_chat_with_staff(request):
    """Get mentee's chats with admin/HR staff"""
    try:
        user = request.user
        
        if user.role != 'mentee':
            return Response({
                'error': 'This endpoint is for mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get one-on-one chats with admin/HR
        staff_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            chat_type__in=['mentee_admin', 'mentee_hr'],
            is_active=True
        ).select_related('user1', 'user2')
        
        chat_data = []
        
        for chat in staff_chats:
            staff_user = chat.user2 if chat.user1 == user else chat.user1
            
            last_message = chat.messages.filter(is_deleted=False).last()
            unread_count = chat.messages.filter(
                is_deleted=False,
                is_read=False
            ).exclude(sender=user).count()
            
            chat_data.append({
                'chat_id': chat.id,
                'staff_user': {
                    'id': staff_user.id,
                    'full_name': staff_user.full_name,
                    'role': staff_user.role,
                    'department': staff_user.department
                },
                'chat_type': chat.chat_type,
                'chat_type_display': chat.get_chat_type_display(),
                'last_message': {
                    'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'timestamp': last_message.created_at if last_message else None,
                    'is_own': last_message.sender == user if last_message else False
                },
                'unread_count': unread_count,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at
            })
        
        # Get group chats where mentee is participant and chat has admin/HR
        group_chats_with_staff = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        ).annotate(
            staff_count=Count('participants', filter=Q(participants__role__in=['admin', 'hr']))
        ).filter(staff_count__gt=0)
        
        for group_chat in group_chats_with_staff:
            # Get staff participants in this group
            staff_participants = group_chat.participants.filter(
                role__in=['admin', 'hr']
            ).values('id', 'full_name', 'role', 'department')[:5]
            
            last_message = group_chat.group_messages.filter(is_deleted=False).last()
            
            # Calculate unread messages
            participant = GroupChatParticipant.objects.filter(
                chat_room=group_chat,
                user=user
            ).first()
            
            unread_count = 0
            if participant and participant.last_read_at:
                unread_count = group_chat.group_messages.filter(
                    created_at__gt=participant.last_read_at,
                    is_deleted=False
                ).exclude(sender=user).count()
            else:
                unread_count = group_chat.group_messages.filter(
                    is_deleted=False
                ).exclude(sender=user).count()
            
            chat_data.append({
                'chat_id': group_chat.id,
                'chat_type': 'group_with_staff',
                'chat_name': group_chat.name,
                'description': group_chat.description,
                'staff_participants': list(staff_participants),
                'total_staff_count': len(staff_participants),
                'last_message': {
                    'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'sender': last_message.sender.full_name if last_message else None,
                    'timestamp': last_message.created_at if last_message else None,
                    'is_own': last_message.sender == user if last_message else False
                },
                'unread_count': unread_count,
                'updated_at': group_chat.updated_at,
                'created_at': group_chat.created_at
            })
        
        # Sort by last activity
        chat_data.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return Response({
            'success': True,
            'total_chats_with_staff': len(chat_data),
            'chats': chat_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch chats with staff',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_group_chats_for_user(request):
    """Get department-level group chats for the user"""
    try:
        user = request.user
        
        if user.role not in ['mentor', 'mentee']:
            return Response({
                'error': 'This endpoint is for mentors and mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get user's department
        user_department = user.department
        
        if not user_department:
            return Response({
                'success': True,
                'message': 'User has no department assigned',
                'chats': []
            }, status=status.HTTP_200_OK)
        
        # Get department group chats
        department_chats = GroupChatRoom.objects.filter(
            department=user_department,
            chat_type='department_group',
            is_active=True,
            is_archived=False,
            participants=user  # User must be a participant
        ).select_related('created_by')
        
        chat_data = []
        
        for chat in department_chats:
            # Get participant info for this user
            participant = GroupChatParticipant.objects.filter(
                chat_room=chat,
                user=user
            ).first()
            
            # Get last message
            last_message = chat.group_messages.filter(is_deleted=False).last()
            
            # Calculate unread messages
            unread_count = 0
            if participant and participant.last_read_at:
                unread_count = chat.group_messages.filter(
                    created_at__gt=participant.last_read_at,
                    is_deleted=False
                ).exclude(sender=user).count()
            else:
                unread_count = chat.group_messages.filter(
                    is_deleted=False
                ).exclude(sender=user).count()
            
            # Get participant count
            total_participants = chat.participants.count()
            
            # Get mentor/mentee breakdown
            mentors_count = chat.participants.filter(role='mentor').count()
            mentees_count = chat.participants.filter(role='mentee').count()
            staff_count = chat.participants.filter(role__in=['admin', 'hr']).count()
            
            chat_data.append({
                'chat_id': chat.id,
                'chat_name': chat.name,
                'description': chat.description,
                'department': chat.department,
                'participant_role': participant.role if participant else 'member',
                'is_muted': participant.is_muted if participant else False,
                'participant_stats': {
                    'total': total_participants,
                    'mentors': mentors_count,
                    'mentees': mentees_count,
                    'staff': staff_count
                },
                'last_message': {
                    'content': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'sender': last_message.sender.full_name if last_message else None,
                    'sender_role': last_message.sender.role if last_message else None,
                    'timestamp': last_message.created_at if last_message else None,
                    'is_own': last_message.sender == user if last_message else False
                },
                'unread_count': unread_count,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at,
                'created_by': {
                    'id': chat.created_by.id,
                    'full_name': chat.created_by.full_name,
                    'role': chat.created_by.role
                }
            })
        
        # Sort by last activity
        chat_data.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return Response({
            'success': True,
            'department': user_department,
            'total_chats': len(chat_data),
            'chats': chat_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch department group chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_summary(request):
    """Get summary of all chats for the user"""
    try:
        user = request.user
        
        if user.role not in ['mentor', 'mentee']:
            return Response({
                'error': 'This endpoint is for mentors and mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get active mentorships
        if user.role == 'mentor':
            active_mentorships = Mentorship.objects.filter(
                mentor=user,
                status='active'
            ).count()
        else:
            active_mentorships = Mentorship.objects.filter(
                mentee=user,
                status='active'
            ).count()
        
        # Get one-on-one chat count
        one_on_one_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        ).count()
        
        # Get group chat count
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        ).count()
        
        # Get total unread messages
        total_unread = 0
        
        # Unread in one-on-one chats
        one_on_one_unread = 0
        for chat in ChatRoom.objects.filter(Q(user1=user) | Q(user2=user), is_active=True):
            one_on_one_unread += chat.messages.filter(
                is_deleted=False,
                is_read=False
            ).exclude(sender=user).count()
        
        # Unread in group chats
        group_unread = 0
        for chat in GroupChatRoom.objects.filter(participants=user, is_active=True, is_archived=False):
            participant = GroupChatParticipant.objects.filter(
                chat_room=chat,
                user=user
            ).first()
            
            if participant and participant.last_read_at:
                group_unread += chat.group_messages.filter(
                    created_at__gt=participant.last_read_at,
                    is_deleted=False
                ).exclude(sender=user).count()
            else:
                group_unread += chat.group_messages.filter(
                    is_deleted=False
                ).exclude(sender=user).count()
        
        total_unread = one_on_one_unread + group_unread
        
        # Get recent activity
        recent_messages = []
        
        # Get recent one-on-one messages
        for chat in ChatRoom.objects.filter(Q(user1=user) | Q(user2=user), is_active=True):
            last_message = chat.messages.filter(is_deleted=False).last()
            if last_message:
                other_user = chat.user2 if chat.user1 == user else chat.user1
                recent_messages.append({
                    'chat_type': 'one_on_one',
                    'chat_id': chat.id,
                    'other_user': other_user.full_name,
                    'content': last_message.content[:50] + '...' if len(last_message.content) > 50 else last_message.content,
                    'timestamp': last_message.created_at,
                    'is_read': last_message.is_read if last_message.sender != user else True
                })
        
        # Get recent group messages
        for chat in GroupChatRoom.objects.filter(participants=user, is_active=True, is_archived=False):
            last_message = chat.group_messages.filter(is_deleted=False).last()
            if last_message:
                recent_messages.append({
                    'chat_type': 'group',
                    'chat_id': chat.id,
                    'chat_name': chat.name,
                    'sender': last_message.sender.full_name,
                    'content': last_message.content[:50] + '...' if len(last_message.content) > 50 else last_message.content,
                    'timestamp': last_message.created_at,
                    'is_read': last_message.get_read_by().filter(id=user.id).exists() if last_message.sender != user else True
                })
        
        # Sort recent messages by timestamp
        recent_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_messages = recent_messages[:10]  # Limit to 10 most recent
        
        return Response({
            'success': True,
            'summary': {
                'active_mentorships': active_mentorships,
                'one_on_one_chats': one_on_one_chats,
                'group_chats': group_chats,
                'total_chats': one_on_one_chats + group_chats,
                'unread_one_on_one': one_on_one_unread,
                'unread_group': group_unread,
                'total_unread': total_unread
            },
            'recent_activity': recent_messages,
            'last_updated': now()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch chat summary',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_my_chats(request):
    """Search through user's chats"""
    try:
        user = request.user
        
        if user.role not in ['mentor', 'mentee']:
            return Response({
                'error': 'This endpoint is for mentors and mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        search_query = request.query_params.get('q', '').strip()
        
        if not search_query:
            return Response({
                'error': 'Search query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Search in one-on-one chats
        one_on_one_results = []
        one_on_one_chats = ChatRoom.objects.filter(
            Q(user1=user) | Q(user2=user),
            is_active=True
        ).select_related('user1', 'user2')
        
        for chat in one_on_one_chats:
            other_user = chat.user2 if chat.user1 == user else chat.user1
            
            # Search in user name
            if search_query.lower() in other_user.full_name.lower():
                last_message = chat.messages.filter(is_deleted=False).last()
                one_on_one_results.append({
                    'type': 'one_on_one',
                    'chat_id': chat.id,
                    'name': other_user.full_name,
                    'role': other_user.role,
                    'last_message': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'timestamp': last_message.created_at if last_message else chat.updated_at
                })
        
        # Search in group chats
        group_results = []
        group_chats = GroupChatRoom.objects.filter(
            participants=user,
            is_active=True,
            is_archived=False
        )
        
        for chat in group_chats:
            # Search in chat name or description
            if (search_query.lower() in chat.name.lower() or 
                search_query.lower() in chat.description.lower()):
                
                last_message = chat.group_messages.filter(is_deleted=False).last()
                group_results.append({
                    'type': 'group',
                    'chat_id': chat.id,
                    'name': chat.name,
                    'description': chat.description,
                    'chat_type': chat.get_chat_type_display(),
                    'last_message': last_message.content[:100] + '...' if last_message and len(last_message.content) > 100 else (last_message.content if last_message else ''),
                    'timestamp': last_message.created_at if last_message else chat.updated_at
                })
        
        # Combine results
        all_results = one_on_one_results + group_results
        all_results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return Response({
            'success': True,
            'search_query': search_query,
            'one_on_one_results': len(one_on_one_results),
            'group_results': len(group_results),
            'total_results': len(all_results),
            'results': all_results
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to search chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_dashboard(request):
    """Get complete chat dashboard for the logged-in user"""
    try:
        user = request.user
        
        if user.role not in ['mentor', 'mentee']:
            return Response({
                'error': 'This endpoint is for mentors and mentees only'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get chat statistics
        from .utils import get_user_chat_statistics, get_recent_chat_activity
        stats = get_user_chat_statistics(user)
        
        # Get recent activity
        recent_activity = get_recent_chat_activity(user, limit=10)
        
        # Get active mentorships for chat categorization
        if user.role == 'mentor':
            active_mentorships = Mentorship.objects.filter(
                mentor=user,
                status='active'
            ).select_related('mentee', 'program')
        else:
            active_mentorships = Mentorship.objects.filter(
                mentee=user,
                status='active'
            ).select_related('mentor', 'program')
        
        # Categorize chats
        mentorship_chats = []
        department_chats = []
        staff_chats = []
        
        # Process each mentorship
        for mentorship in active_mentorships:
            # Get mentorship-specific chats
            mentorship_group = GroupChatRoom.objects.filter(
                mentorship=mentorship,
                chat_type='mentorship_group',
                is_active=True,
                is_archived=False
            ).first()
            
            one_on_one = ChatRoom.objects.filter(
                mentorship=mentorship,
                chat_type='mentor_mentee',
                is_active=True
            ).first()
            
            if mentorship_group:
                last_message = mentorship_group.group_messages.filter(is_deleted=False).last()
                mentorship_chats.append({
                    'type': 'group',
                    'id': mentorship_group.id,
                    'name': mentorship_group.name,
                    'description': f"Mentorship with {mentorship.mentee.full_name if user.role == 'mentor' else mentorship.mentor.full_name}",
                    'program': mentorship.program.name,
                    'last_activity': last_message.created_at if last_message else mentorship_group.updated_at,
                    'unread_count': calculate_group_unread(mentorship_group, user)
                })
            
            if one_on_one:
                last_message = one_on_one.messages.filter(is_deleted=False).last()
                other_user = mentorship.mentee if user.role == 'mentor' else mentorship.mentor
                mentorship_chats.append({
                    'type': 'one_on_one',
                    'id': one_on_one.id,
                    'name': f"Direct chat with {other_user.full_name}",
                    'description': f"One-on-one communication",
                    'program': mentorship.program.name,
                    'last_activity': last_message.created_at if last_message else one_on_one.updated_at,
                    'unread_count': one_on_one.messages.filter(
                        is_deleted=False,
                        is_read=False
                    ).exclude(sender=user).count()
                })
        
        # Get department chats
        if user.department:
            department_group_chats = GroupChatRoom.objects.filter(
                department=user.department,
                chat_type='department_group',
                is_active=True,
                is_archived=False,
                participants=user
            )
            
            for chat in department_group_chats:
                last_message = chat.group_messages.filter(is_deleted=False).last()
                department_chats.append({
                    'type': 'department_group',
                    'id': chat.id,
                    'name': chat.name,
                    'description': chat.description,
                    'participant_count': chat.participants.count(),
                    'last_activity': last_message.created_at if last_message else chat.updated_at,
                    'unread_count': calculate_group_unread(chat, user)
                })
        
        # Get staff chats (for mentees)
        if user.role == 'mentee':
            staff_contacts = ChatRoom.objects.filter(
                Q(user1=user) | Q(user2=user),
                chat_type__in=['mentee_admin', 'mentee_hr'],
                is_active=True
            ).select_related('user1', 'user2')
            
            for chat in staff_contacts:
                staff_user = chat.user2 if chat.user1 == user else chat.user1
                last_message = chat.messages.filter(is_deleted=False).last()
                staff_chats.append({
                    'type': 'staff_chat',
                    'id': chat.id,
                    'name': f"Chat with {staff_user.full_name} ({staff_user.role})",
                    'description': f"{staff_user.role.upper()} Support",
                    'staff_role': staff_user.role,
                    'last_activity': last_message.created_at if last_message else chat.updated_at,
                    'unread_count': chat.messages.filter(
                        is_deleted=False,
                        is_read=False
                    ).exclude(sender=user).count()
                })
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'role': user.role,
                'department': user.department
            },
            'statistics': stats,
            'recent_activity': recent_activity,
            'chats': {
                'mentorship_chats': sorted(mentorship_chats, key=lambda x: x['last_activity'], reverse=True),
                'department_chats': sorted(department_chats, key=lambda x: x['last_activity'], reverse=True),
                'staff_chats': sorted(staff_chats, key=lambda x: x['last_activity'], reverse=True) if user.role == 'mentee' else []
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to load chat dashboard',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def calculate_group_unread(group_chat, user):
    """Helper function to calculate unread messages in group chat"""
    try:
        participant = GroupChatParticipant.objects.filter(
            chat_room=group_chat,
            user=user
        ).first()
        
        if participant and participant.last_read_at:
            return group_chat.group_messages.filter(
                created_at__gt=participant.last_read_at,
                is_deleted=False
            ).exclude(sender=user).count()
        else:
            return group_chat.group_messages.filter(
                is_deleted=False
            ).exclude(sender=user).count()
    except:
        return 0




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_cross_department_chat(request):
    """Create a cross-department chat (Admin/HR only)"""
    try:
        user = request.user
        
        # Only admin and HR can create cross-department chats
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can create cross-department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Validate required data
        name = request.data.get('name')
        description = request.data.get('description', '')
        department_ids = request.data.get('departments', [])
        participant_ids = request.data.get('participant_ids', [])
        include_all_staff = request.data.get('include_all_staff', False)
        include_all_mentors = request.data.get('include_all_mentors', False)
        include_all_mentees = request.data.get('include_all_mentees', False)
        
        if not name:
            return Response({
                'error': 'Chat name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not department_ids or not isinstance(department_ids, list):
            return Response({
                'error': 'At least one department must be specified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate departments
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
        
        invalid_departments = [dept for dept in department_ids if dept not in valid_departments]
        if invalid_departments:
            return Response({
                'error': f'Invalid departments: {", ".join(invalid_departments)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if name already exists
        if GroupChatRoom.objects.filter(
            name__iexact=name,
            chat_type='cross_department'
        ).exists():
            return Response({
                'error': f'A cross-department chat with name "{name}" already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the cross-department chat
        cross_chat = GroupChatRoom.objects.create(
            name=name,
            description=description,
            chat_type='cross_department',
            department=None,  # Cross-department chats have no single department
            created_by=user
        )
        
        # Add creator as admin
        cross_chat.add_participant(user, added_by=user, role='admin')
        
        # Track added users to avoid duplicates
        added_user_ids = set([user.id])
        
        # Add specified participants
        for user_id in participant_ids:
            try:
                participant_user = CustomUser.objects.get(id=user_id)
                if participant_user.id not in added_user_ids:
                    cross_chat.add_participant(participant_user, added_by=user, role='member')
                    added_user_ids.add(participant_user.id)
            except CustomUser.DoesNotExist:
                continue
        
        # Include all staff if requested
        if include_all_staff:
            staff_users = CustomUser.objects.filter(
                role__in=['admin', 'hr'],
                status='approved'
            ).exclude(id__in=added_user_ids)
            
            for staff_user in staff_users:
                cross_chat.add_participant(staff_user, added_by=user, role='admin')
                added_user_ids.add(staff_user.id)
        
        # Include all mentors from selected departments
        if include_all_mentors:
            mentor_users = CustomUser.objects.filter(
                role='mentor',
                department__in=department_ids,
                status='approved',
                availability_status='active'
            ).exclude(id__in=added_user_ids)
            
            for mentor_user in mentor_users:
                cross_chat.add_participant(mentor_user, added_by=user, role='moderator')
                added_user_ids.add(mentor_user.id)
        
        # Include all mentees from selected departments
        if include_all_mentees:
            mentee_users = CustomUser.objects.filter(
                role='mentee',
                department__in=department_ids,
                status='approved'
            ).exclude(id__in=added_user_ids)
            
            for mentee_user in mentee_users:
                cross_chat.add_participant(mentee_user, added_by=user, role='member')
                added_user_ids.add(mentee_user.id)
        
        # Send notifications to all added participants
        for participant_id in added_user_ids:
            if participant_id != user.id:  # Don't notify creator
                try:
                    participant_user = CustomUser.objects.get(id=participant_id)
                    ChatNotification.objects.create(
                        recipient=participant_user,
                        sender=user,
                        chat_room=cross_chat,
                        notification_type='case_assigned',
                        title=f'Added to Cross-Department Chat',
                        message=f'You have been added to "{cross_chat.name}" by {user.full_name}'
                    )
                except CustomUser.DoesNotExist:
                    continue
        
        # Create system announcement in the chat
        system_message = f"""🚀 **Cross-Department Chat Created!**
        
**Chat Name:** {cross_chat.name}
**Created By:** {user.full_name} ({user.role})
**Departments Included:** {', '.join(department_ids)}
**Total Participants:** {len(added_user_ids)}

This chat is for cross-department collaboration and communication. Please be respectful and follow community guidelines.
"""
        
        # Create system user or use creator for system message
        try:
            system_user = CustomUser.objects.get(phone_number='system')
        except CustomUser.DoesNotExist:
            system_user = user
        
        GroupChatMessage.objects.create(
            chat_room=cross_chat,
            sender=system_user,
            message_type='system',
            content=system_message
        )
        
        return Response({
            'success': True,
            'message': 'Cross-department chat created successfully',
            'chat': {
                'id': cross_chat.id,
                'name': cross_chat.name,
                'description': cross_chat.description,
                'chat_type': cross_chat.chat_type,
                'departments': department_ids,
                'total_participants': len(added_user_ids),
                'created_by': {
                    'id': user.id,
                    'name': user.full_name,
                    'role': user.role
                },
                'created_at': cross_chat.created_at
            }
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'error': 'Failed to create cross-department chat',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_cross_department_chats(request):
    """List all cross-department chats"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can view cross-department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all cross-department chats
        cross_chats = GroupChatRoom.objects.filter(
            chat_type='cross_department',
            is_active=True,
            is_archived=False
        ).select_related('created_by')
        
        # Apply filters
        search_query = request.query_params.get('search', '')
        if search_query:
            cross_chats = cross_chats.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Prepare response data
        chat_data = []
        
        for chat in cross_chats:
            # Get participant statistics
            participants = chat.participants.all()
            participant_stats = {
                'total': participants.count(),
                'admins': participants.filter(role='admin').count(),
                'hr': participants.filter(role='hr').count(),
                'mentors': participants.filter(role='mentor').count(),
                'mentees': participants.filter(role='mentee').count()
            }
            
            # Get departments from participants
            departments = set(participants.exclude(department__isnull=True).values_list('department', flat=True))
            
            # Get last message
            last_message = chat.group_messages.filter(is_deleted=False).last()
            
            # Check if user is participant
            is_participant = chat.participants.filter(id=user.id).exists()
            
            chat_data.append({
                'id': chat.id,
                'name': chat.name,
                'description': chat.description,
                'departments': list(departments)[:5],  # Limit to 5 departments
                'total_departments': len(departments),
                'created_by': {
                    'id': chat.created_by.id,
                    'name': chat.created_by.full_name,
                    'role': chat.created_by.role
                },
                'participant_stats': participant_stats,
                'is_participant': is_participant,
                'last_activity': last_message.created_at if last_message else chat.updated_at,
                'created_at': chat.created_at,
                'updated_at': chat.updated_at
            })
        
        # Sort by last activity
        chat_data.sort(key=lambda x: x['last_activity'], reverse=True)
        
        return Response({
            'success': True,
            'count': len(chat_data),
            'chats': chat_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch cross-department chats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cross_department_chat(request, chat_id):
    """Get details of a specific cross-department chat"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can view cross-department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        cross_chat = get_object_or_404(
            GroupChatRoom, 
            id=chat_id,
            chat_type='cross_department'
        )
        
        # Check if user is participant
        if not cross_chat.participants.filter(id=user.id).exists():
            return Response({
                'error': 'You are not a participant in this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get participant details
        participants = cross_chat.participants.all().select_related('profile')
        participant_data = []
        
        for participant in participants:
            participant_role = GroupChatParticipant.objects.get(
                chat_room=cross_chat,
                user=participant
            ).role
            
            participant_data.append({
                'id': participant.id,
                'full_name': participant.full_name,
                'role': participant.role,
                'department': participant.department,
                'chat_role': participant_role,
                'joined_at': GroupChatParticipant.objects.get(
                    chat_room=cross_chat,
                    user=participant
                ).joined_at
            })
        
        # Get departments from participants
        departments = set(participants.exclude(department__isnull=True).values_list('department', flat=True))
        
        # Get message statistics
        total_messages = cross_chat.group_messages.filter(is_deleted=False).count()
        recent_messages = cross_chat.group_messages.filter(
            is_deleted=False,
            created_at__gte=now() - timedelta(days=7)
        ).count()
        
        # Get last few messages
        recent_messages_list = cross_chat.group_messages.filter(
            is_deleted=False
        ).order_by('-created_at')[:10]
        
        recent_messages_data = []
        for msg in recent_messages_list:
            recent_messages_data.append({
                'id': msg.id,
                'sender': {
                    'id': msg.sender.id,
                    'name': msg.sender.full_name,
                    'role': msg.sender.role
                },
                'content': msg.content[:200] + '...' if len(msg.content) > 200 else msg.content,
                'message_type': msg.message_type,
                'created_at': msg.created_at
            })
        
        # Get chat statistics
        stats = {
            'total_participants': len(participants),
            'total_messages': total_messages,
            'messages_last_7_days': recent_messages,
            'departments_count': len(departments),
            'admins_count': participants.filter(role='admin').count(),
            'hr_count': participants.filter(role='hr').count(),
            'mentors_count': participants.filter(role='mentor').count(),
            'mentees_count': participants.filter(role='mentee').count()
        }
        
        return Response({
            'success': True,
            'chat': {
                'id': cross_chat.id,
                'name': cross_chat.name,
                'description': cross_chat.description,
                'created_by': {
                    'id': cross_chat.created_by.id,
                    'name': cross_chat.created_by.full_name,
                    'role': cross_chat.created_by.role
                },
                'departments': list(departments),
                'stats': stats,
                'created_at': cross_chat.created_at,
                'updated_at': cross_chat.updated_at
            },
            'participants': participant_data,
            'recent_messages': recent_messages_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch cross-department chat details',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manage_cross_department_chat_participants(request, chat_id):
    """Add or remove participants from cross-department chat"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can manage cross-department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        cross_chat = get_object_or_404(
            GroupChatRoom, 
            id=chat_id,
            chat_type='cross_department'
        )
        
        # Check if user is admin in this chat
        try:
            user_participant = GroupChatParticipant.objects.get(
                chat_room=cross_chat,
                user=user
            )
            if user_participant.role != 'admin':
                return Response({
                    'error': 'Permission denied. You must be an admin to manage participants'
                }, status=status.HTTP_403_FORBIDDEN)
        except GroupChatParticipant.DoesNotExist:
            return Response({
                'error': 'You are not a participant in this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        action = request.data.get('action')  # 'add' or 'remove'
        user_ids = request.data.get('user_ids', [])
        role = request.data.get('role', 'member')
        
        if action not in ['add', 'remove']:
            return Response({
                'error': 'Action must be either "add" or "remove"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user_ids or not isinstance(user_ids, list):
            return Response({
                'error': 'User IDs must be provided as a list'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {
            'added': [],
            'removed': [],
            'failed': [],
            'already_exists': [],
            'not_found': []
        }
        
        if action == 'add':
            for user_id in user_ids:
                try:
                    target_user = CustomUser.objects.get(id=user_id)
                    
                    # Check if user is already a participant
                    if cross_chat.participants.filter(id=target_user.id).exists():
                        results['already_exists'].append({
                            'user_id': user_id,
                            'name': target_user.full_name
                        })
                        continue
                    
                    # Add user to chat
                    participant = cross_chat.add_participant(
                        target_user, 
                        added_by=user,
                        role=role
                    )
                    
                    results['added'].append({
                        'user_id': user_id,
                        'name': target_user.full_name,
                        'role': role
                    })
                    
                    # Send notification
                    ChatNotification.objects.create(
                        recipient=target_user,
                        sender=user,
                        chat_room=cross_chat,
                        notification_type='case_assigned',
                        title=f'Added to Cross-Department Chat',
                        message=f'You have been added to "{cross_chat.name}" by {user.full_name}'
                    )
                    
                except CustomUser.DoesNotExist:
                    results['not_found'].append(user_id)
                except Exception as e:
                    results['failed'].append({
                        'user_id': user_id,
                        'error': str(e)
                    })
        
        elif action == 'remove':
            for user_id in user_ids:
                try:
                    target_user = CustomUser.objects.get(id=user_id)
                    
                    # Check if user is a participant
                    if not cross_chat.participants.filter(id=target_user.id).exists():
                        results['not_found'].append(user_id)
                        continue
                    
                    # Cannot remove yourself if you're the only admin
                    if target_user == user:
                        admin_count = GroupChatParticipant.objects.filter(
                            chat_room=cross_chat,
                            role='admin'
                        ).count()
                        if admin_count <= 1:
                            results['failed'].append({
                                'user_id': user_id,
                                'error': 'Cannot remove yourself as the only admin'
                            })
                            continue
                    
                    # Remove user from chat
                    cross_chat.remove_participant(target_user)
                    
                    results['removed'].append({
                        'user_id': user_id,
                        'name': target_user.full_name
                    })
                    
                    # Send notification
                    ChatNotification.objects.create(
                        recipient=target_user,
                        sender=user,
                        chat_room=cross_chat,
                        notification_type='status_changed',
                        title=f'Removed from Cross-Department Chat',
                        message=f'You have been removed from "{cross_chat.name}" by {user.full_name}'
                    )
                    
                except CustomUser.DoesNotExist:
                    results['not_found'].append(user_id)
                except Exception as e:
                    results['failed'].append({
                        'user_id': user_id,
                        'error': str(e)
                    })
        
        # Create system message about the changes
        if results['added'] or results['removed']:
            system_message = f"""📢 **Participant Update**
            
**Action:** {action.capitalize()} Participants
**Performed By:** {user.full_name}
            
"""
            if results['added']:
                added_names = ', '.join([item['name'] for item in results['added']])
                system_message += f"**Added:** {added_names}\n"
            
            if results['removed']:
                removed_names = ', '.join([item['name'] for item in results['removed']])
                system_message += f"**Removed:** {removed_names}\n"
            
            # Create system user or use admin for system message
            try:
                system_user = CustomUser.objects.get(phone_number='system')
            except CustomUser.DoesNotExist:
                system_user = user
            
            GroupChatMessage.objects.create(
                chat_room=cross_chat,
                sender=system_user,
                message_type='system',
                content=system_message
            )
        
        return Response({
            'success': True,
            'message': f'Participant management completed',
            'results': results,
            'updated_participant_count': cross_chat.participants.count()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to manage participants',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_cross_department_chat(request, chat_id):
    """Update cross-department chat details"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can update cross-department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        cross_chat = get_object_or_404(
            GroupChatRoom, 
            id=chat_id,
            chat_type='cross_department'
        )
        
        # Check if user is admin in this chat
        try:
            user_participant = GroupChatParticipant.objects.get(
                chat_room=cross_chat,
                user=user
            )
            if user_participant.role != 'admin':
                return Response({
                    'error': 'Permission denied. You must be an admin to update chat details'
                }, status=status.HTTP_403_FORBIDDEN)
        except GroupChatParticipant.DoesNotExist:
            return Response({
                'error': 'You are not a participant in this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Update fields
        name = request.data.get('name')
        description = request.data.get('description')
        
        updates = {}
        
        if name and name != cross_chat.name:
            # Check if new name already exists
            if GroupChatRoom.objects.filter(
                name__iexact=name,
                chat_type='cross_department'
            ).exclude(id=cross_chat.id).exists():
                return Response({
                    'error': f'A cross-department chat with name "{name}" already exists'
                }, status=status.HTTP_400_BAD_REQUEST)
            updates['name'] = name
        
        if description is not None:
            updates['description'] = description
        
        if updates:
            for field, value in updates.items():
                setattr(cross_chat, field, value)
            cross_chat.save()
            
            # Create system message about the update
            update_details = []
            if 'name' in updates:
                update_details.append(f"name changed to '{updates['name']}'")
            if 'description' in updates:
                update_details.append("description updated")
            
            system_message = f"""🔄 **Chat Updated**
            
**Updated By:** {user.full_name}
**Changes:** {', '.join(update_details)}
**Updated At:** {now().strftime('%Y-%m-%d %H:%M')}
"""
            
            # Create system user or use admin for system message
            try:
                system_user = CustomUser.objects.get(phone_number='system')
            except CustomUser.DoesNotExist:
                system_user = user
            
            GroupChatMessage.objects.create(
                chat_room=cross_chat,
                sender=system_user,
                message_type='system',
                content=system_message
            )
        
        return Response({
            'success': True,
            'message': 'Chat updated successfully',
            'chat': GroupChatRoomSerializer(cross_chat, context={'request': request}).data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to update chat',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def archive_cross_department_chat(request, chat_id):
    """Archive a cross-department chat"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can archive cross-department chats'
            }, status=status.HTTP_403_FORBIDDEN)
        
        cross_chat = get_object_or_404(
            GroupChatRoom, 
            id=chat_id,
            chat_type='cross_department',
            is_archived=False
        )
        
        # Check if user is admin in this chat
        try:
            user_participant = GroupChatParticipant.objects.get(
                chat_room=cross_chat,
                user=user
            )
            if user_participant.role != 'admin':
                return Response({
                    'error': 'Permission denied. You must be an admin to archive this chat'
                }, status=status.HTTP_403_FORBIDDEN)
        except GroupChatParticipant.DoesNotExist:
            return Response({
                'error': 'You are not a participant in this chat'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Archive the chat
        cross_chat.is_archived = True
        cross_chat.is_active = False
        cross_chat.save()
        
        # Create system message
        system_message = f"""🔒 **Chat Archived**
        
This cross-department chat has been archived by {user.full_name}.

**Chat Name:** {cross_chat.name}
**Archived At:** {now().strftime('%Y-%m-%d %H:%M')}
**Reason:** Chat is no longer active

Participants can no longer send messages in this chat.
"""
        
        # Create system user or use admin for system message
        try:
            system_user = CustomUser.objects.get(phone_number='system')
        except CustomUser.DoesNotExist:
            system_user = user
        
        GroupChatMessage.objects.create(
            chat_room=cross_chat,
            sender=system_user,
            message_type='system',
            content=system_message
        )
        
        # Send notifications to all participants
        participants = cross_chat.participants.all()
        for participant in participants:
            if participant.id != user.id:
                ChatNotification.objects.create(
                    recipient=participant,
                    sender=user,
                    chat_room=cross_chat,
                    notification_type='status_changed',
                    title=f'Chat Archived',
                    message=f'The cross-department chat "{cross_chat.name}" has been archived'
                )
        
        return Response({
            'success': True,
            'message': 'Cross-department chat archived successfully',
            'chat_id': cross_chat.id,
            'archived_at': now()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to archive chat',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_users_for_cross_department(request):
    """Get users available to add to cross-department chats"""
    try:
        user = request.user
        
        if user.role not in ['admin', 'hr']:
            return Response({
                'error': 'Permission denied. Only Admin and HR can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get query parameters
        search = request.query_params.get('search', '')
        role = request.query_params.get('role')
        department = request.query_params.get('department')
        exclude_chat_id = request.query_params.get('exclude_chat_id')
        
        # Build queryset
        users = CustomUser.objects.filter(
            status='approved'
        ).exclude(id=user.id)  # Exclude self
        
        # Apply filters
        if search:
            users = users.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(work_mail_address__icontains=search)
            )
        
        if role:
            users = users.filter(role=role)
        
        if department:
            users = users.filter(department=department)
        
        # Exclude users already in specified chat
        if exclude_chat_id:
            try:
                chat = GroupChatRoom.objects.get(id=exclude_chat_id)
                existing_participant_ids = chat.participants.values_list('id', flat=True)
                users = users.exclude(id__in=existing_participant_ids)
            except GroupChatRoom.DoesNotExist:
                pass
        
        # Limit results
        limit = min(int(request.query_params.get('limit', 50)), 100)
        users = users[:limit]
        
        # Prepare response data
        user_data = []
        for user_obj in users:
            user_data.append({
                'id': user_obj.id,
                'full_name': user_obj.full_name,
                'role': user_obj.role,
                'department': user_obj.department,
                'email': user_obj.email,
                'work_mail_address': user_obj.work_mail_address,
                'status': user_obj.status,
                'availability_status': user_obj.availability_status if hasattr(user_obj, 'availability_status') else 'active'
            })
        
        return Response({
            'success': True,
            'count': len(user_data),
            'users': user_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': 'Failed to fetch available users',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)