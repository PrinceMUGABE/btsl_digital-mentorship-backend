from rest_framework import serializers
from .models import CustomUser
from django.core.mail import send_mail
from django.contrib.auth import authenticate


class CustomUserSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'phone_number', 'email', 'work_mail_address',
            'full_name', 'role', 'department', 'status',
            'availability_status', 'created_at', 'created_by',
            'created_by_name'
        ]
        read_only_fields = ['work_mail_address', 'created_at', 'created_by']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name
        return None


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=True)
    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(max_length=100, required=True)
    department = serializers.CharField(max_length=100, required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)  # Can be phone, email, or work mail
    password = serializers.CharField(write_only=True, required=True)


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['phone_number', 'email', 'full_name', 'department', 'availability_status', 'status']



class ContactUsSerializer(serializers.Serializer):
    names = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    subject = serializers.CharField(max_length=255, required=True)
    description = serializers.CharField(required=True)