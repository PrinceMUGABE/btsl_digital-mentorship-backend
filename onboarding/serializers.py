from rest_framework import serializers
from .models import (
    OnboardingModule, 
    MenteeOnboardingProgress, 
    OnboardingChecklist,
    MenteeChecklistProgress
)
from userApp.models import CustomUser


class OnboardingChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingChecklist
        fields = [
            'id', 
            'title', 
            'description', 
            'order', 
            'is_required'
        ]


class OnboardingModuleSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    applicable_departments = serializers.SerializerMethodField()
    checklist_items = OnboardingChecklistSerializer(many=True, read_only=True)
    total_mentees_assigned = serializers.SerializerMethodField()
    total_completed = serializers.SerializerMethodField()
    
    class Meta:
        model = OnboardingModule
        fields = [
            'id',
            'title',
            'description',
            'module_type',
            'department',
            'order',
            'is_required',
            'duration_minutes',
            'content',
            'resources',
            'is_active',
            'created_at',
            'updated_at',
            'created_by',
            'created_by_name',
            'applicable_departments',
            'checklist_items',
            'total_mentees_assigned',
            'total_completed'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def get_applicable_departments(self, obj):
        return obj.get_applicable_departments()
    
    def get_total_mentees_assigned(self, obj):
        return obj.mentee_progress.count()
    
    def get_total_completed(self, obj):
        return obj.mentee_progress.filter(status='completed').count()
    
    def validate(self, data):
        """Validate that department-specific modules have a department"""
        if data.get('module_type') == 'department' and not data.get('department'):
            raise serializers.ValidationError({
                'department': 'Department is required for department-specific modules'
            })
        
        # Clear department for core modules
        if data.get('module_type') == 'core':
            data['department'] = None
        
        return data


class OnboardingModuleCreateSerializer(serializers.ModelSerializer):
    checklist_items = OnboardingChecklistSerializer(many=True, required=False)
    
    class Meta:
        model = OnboardingModule
        fields = [
            'title',
            'description',
            'module_type',
            'department',
            'order',
            'is_required',
            'duration_minutes',
            'content',
            'resources',
            'is_active',
            'checklist_items'
        ]
    
    def create(self, validated_data):
        checklist_items_data = validated_data.pop('checklist_items', [])
        module = OnboardingModule.objects.create(**validated_data)
        
        # Create checklist items
        for item_data in checklist_items_data:
            OnboardingChecklist.objects.create(module=module, **item_data)
        
        return module
    
    def update(self, instance, validated_data):
        checklist_items_data = validated_data.pop('checklist_items', None)
        
        # Update module fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update checklist items if provided
        if checklist_items_data is not None:
            # Remove existing checklist items
            instance.checklist_items.all().delete()
            
            # Create new checklist items
            for item_data in checklist_items_data:
                OnboardingChecklist.objects.create(module=instance, **item_data)
        
        return instance


class MenteeChecklistProgressSerializer(serializers.ModelSerializer):
    checklist_item_title = serializers.CharField(source='checklist_item.title', read_only=True)
    checklist_item_description = serializers.CharField(source='checklist_item.description', read_only=True)
    
    class Meta:
        model = MenteeChecklistProgress
        fields = [
            'id',
            'checklist_item',
            'checklist_item_title',
            'checklist_item_description',
            'is_completed',
            'completed_at'
        ]


class MenteeOnboardingProgressSerializer(serializers.ModelSerializer):
    mentee_name = serializers.CharField(source='mentee.full_name', read_only=True)
    mentee_email = serializers.CharField(source='mentee.email', read_only=True)
    mentee_department = serializers.CharField(source='mentee.department', read_only=True)
    module_title = serializers.CharField(source='module.title', read_only=True)
    module_description = serializers.CharField(source='module.description', read_only=True)
    module_type = serializers.CharField(source='module.module_type', read_only=True)
    module_duration = serializers.IntegerField(source='module.duration_minutes', read_only=True)
    module_content = serializers.JSONField(source='module.content', read_only=True)
    module_resources = serializers.JSONField(source='module.resources', read_only=True)
    checklist_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = MenteeOnboardingProgress
        fields = [
            'id',
            'mentee',
            'mentee_name',
            'mentee_email',
            'mentee_department',
            'module',
            'module_title',
            'module_description',
            'module_type',
            'module_duration',
            'module_content',
            'module_resources',
            'status',
            'progress_percentage',
            'started_at',
            'completed_at',
            'notes',
            'time_spent_minutes',
            'checklist_progress'
        ]
        read_only_fields = ['started_at', 'completed_at']
    
    def get_checklist_progress(self, obj):
        checklist_items = obj.module.checklist_items.all()
        progress_items = MenteeChecklistProgress.objects.filter(
            mentee=obj.mentee,
            checklist_item__module=obj.module
        )
        
        result = []
        for item in checklist_items:
            progress = progress_items.filter(checklist_item=item).first()
            result.append({
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'is_required': item.is_required,
                'is_completed': progress.is_completed if progress else False,
                'completed_at': progress.completed_at if progress else None
            })
        
        return result


class MenteeOnboardingProgressUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenteeOnboardingProgress
        fields = [
            'status',
            'progress_percentage',
            'notes',
            'time_spent_minutes'
        ]
    
    def validate_progress_percentage(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Progress percentage must be between 0 and 100")
        return value


class MenteeSummarySerializer(serializers.ModelSerializer):
    """Summary of mentee's overall onboarding progress"""
    total_modules = serializers.SerializerMethodField()
    completed_modules = serializers.SerializerMethodField()
    in_progress_modules = serializers.SerializerMethodField()
    not_started_modules = serializers.SerializerMethodField()
    overall_progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'full_name',
            'email',
            'department',
            'total_modules',
            'completed_modules',
            'in_progress_modules',
            'not_started_modules',
            'overall_progress_percentage'
        ]
    
    def get_total_modules(self, obj):
        return obj.onboarding_progress.count()
    
    def get_completed_modules(self, obj):
        return obj.onboarding_progress.filter(status='completed').count()
    
    def get_in_progress_modules(self, obj):
        return obj.onboarding_progress.filter(status='in_progress').count()
    
    def get_not_started_modules(self, obj):
        return obj.onboarding_progress.filter(status='not_started').count()
    
    def get_overall_progress_percentage(self, obj):
        progress_records = obj.onboarding_progress.all()
        if not progress_records:
            return 0
        
        total_progress = sum(p.progress_percentage for p in progress_records)
        return round(total_progress / progress_records.count(), 2)
    






class SendReminderSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(required=True)
    notification_type = serializers.CharField(max_length=100, required=True)
    title = serializers.CharField(max_length=255, required=True)
    message = serializers.CharField(required=True)