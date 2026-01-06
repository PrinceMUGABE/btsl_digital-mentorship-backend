from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now
import random
import string


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, email=None, full_name=None, role=None, department=None, 
                    status='pending', availability_status='inactive', 
                    work_mail_address=None, password=None, created_by=None):
        if not phone_number:
            raise ValueError("The phone number must be provided")
        if not full_name:
            raise ValueError("The full name must be provided")
        if not role:
            raise ValueError("The role must be provided")
        if role not in [choice[0] for choice in CustomUser.ROLE_CHOICES]:
            raise ValueError("Invalid role selected")
        
        # Department is required for non-admin users
        if role != 'admin' and not department:
            raise ValueError("The department must be provided for non-admin users")

        user = self.model(
            phone_number=phone_number,
            full_name=full_name,
            role=role,
            department=department,
            status=status,
            availability_status=availability_status
        )
        
        if email:
            email = self.normalize_email(email)
            user.email = email
        
        if work_mail_address:
            user.work_mail_address = work_mail_address
        else:
            # Generate work mail if not provided
            user.work_mail_address = self.generate_work_mail(full_name, role)
        
        if created_by:
            user.created_by = created_by
            
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, full_name, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number must be provided for superuser")
        if not email:
            raise ValueError("The email must be provided for superuser")
        if not full_name:
            raise ValueError("The full name must be provided for superuser")
        if not password:
            raise ValueError("The password must be provided for superuser")
        
        # For admin/superuser, department can be None or empty
        department = extra_fields.get('department', 'Administration')
        
        # Generate work mail address with role
        work_mail = self.generate_work_mail(full_name, 'admin')
        
        user = self.create_user(
            phone_number=phone_number,
            email=email,
            full_name=full_name,
            role='admin',
            department=department,
            status='approved',
            availability_status='active',
            work_mail_address=work_mail,
            password=password
        )
        # For Django's PermissionsMixin, we need to set these fields
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

    @staticmethod
    def generate_work_mail(full_name, role):
        """
        Generate work mail address from full name with role prefix.
        If duplicate exists, append random numbers.
        """
        # Clean the full name
        full_name = full_name.strip()
        names = full_name.split()
        
        # Map role to domain prefix
        role_prefixes = {
            'admin': 'admin',
            'hr': 'hr',
            'mentor': 'mentor',
            'mentee': 'mentee'
        }
        role_prefix = role_prefixes.get(role, 'user')
        
        # Take first name initial and last name
        if len(names) >= 2:
            first_initial = names[0][0].lower()
            last_name = names[-1].lower().replace(' ', '')
            base_mail = f"{first_initial}.{last_name}@{role_prefix}_btsl_mentorship.com"
        else:
            # If only one name
            base_mail = f"{full_name.lower().replace(' ', '')}@{role_prefix}_btsl_mentorship.com"
        
        # Check if this mail already exists
        from .models import CustomUser
        mail_exists = CustomUser.objects.filter(work_mail_address=base_mail).exists()
        
        if not mail_exists:
            return base_mail
        
        # If exists, append random numbers
        random_num = random.randint(100, 999)
        if len(names) >= 2:
            return f"{first_initial}.{last_name}{random_num}@{role_prefix}_btsl_mentorship.com"
        else:
            return f"{full_name.lower().replace(' ', '')}{random_num}@{role_prefix}_btsl_mentorship.com"


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('mentor', 'Mentor'),
        ('mentee', 'Mentee'),
        ('hr', 'HR'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    AVAILABILITY_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    work_mail_address = models.EmailField(unique=True)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='mentee')
    department = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='inactive')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email', 'full_name']

    objects = CustomUserManager()

    def __str__(self):
        return self.work_mail_address

    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_hr(self):
        return self.role == 'hr'
    
    @property
    def is_mentor(self):
        return self.role == 'mentor'
    
    @property
    def is_mentee(self):
        return self.role == 'mentee'