"""
Management command to seed mentorship data
Save this file as: mentorshipApp/management/commands/seed_mentorship_data.py

Run with: python manage.py seed_mentorship_data
"""

from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from userApp.models import CustomUser
from mentoshipApp.models import (
    MentorshipProgram,
    Mentorship,
    MentorshipSession
)
import random


class Command(BaseCommand):
    help = 'Seeds the database with sample mentorship data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding mentorship data...')
        
        # Create mentors and mentees if they don't exist
        self.create_users()
        
        # Create programs
        self.create_programs()
        
        # Create mentorships
        self.create_mentorships()
        
        # Create sessions
        self.create_sessions()
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded mentorship data!'))
    
    def create_users(self):
        """Create sample mentors and mentees"""
        # Create mentors
        mentors_data = [
            {
                'phone_number': '+250781234501',
                'email': 'amanda.foster@example.com',
                'full_name': 'Dr. Amanda Foster',
                'department': 'Leadership'
            },
            {
                'phone_number': '+250781234502',
                'email': 'robert.martinez@example.com',
                'full_name': 'Robert Martinez',
                'department': 'Engineering'
            },
            {
                'phone_number': '+250781234503',
                'email': 'jennifer.lee@example.com',
                'full_name': 'Jennifer Lee',
                'department': 'Human Resources'
            },
            {
                'phone_number': '+250781234504',
                'email': 'david.kim@example.com',
                'full_name': 'David Kim',
                'department': 'Product'
            }
        ]
        
        for data in mentors_data:
            if not CustomUser.objects.filter(phone_number=data['phone_number']).exists():
                CustomUser.objects.create_user(
                    phone_number=data['phone_number'],
                    email=data['email'],
                    full_name=data['full_name'],
                    role='mentor',
                    department=data['department'],
                    status='approved',
                    availability_status='active',
                    password='password123'
                )
                self.stdout.write(f"Created mentor: {data['full_name']}")
        
        # Create mentees
        mentees_data = [
            {
                'phone_number': '+250781234505',
                'email': 'sarah.johnson@example.com',
                'full_name': 'Sarah Johnson',
                'department': 'Marketing'
            },
            {
                'phone_number': '+250781234506',
                'email': 'michael.chen@example.com',
                'full_name': 'Michael Chen',
                'department': 'Engineering'
            },
            {
                'phone_number': '+250781234507',
                'email': 'emily.rodriguez@example.com',
                'full_name': 'Emily Rodriguez',
                'department': 'Sales'
            },
            {
                'phone_number': '+250781234508',
                'email': 'lisa.anderson@example.com',
                'full_name': 'Lisa Anderson',
                'department': 'Product'
            },
            {
                'phone_number': '+250781234509',
                'email': 'james.wilson@example.com',
                'full_name': 'James Wilson',
                'department': 'Operations'
            },
            {
                'phone_number': '+250781234510',
                'email': 'emma.taylor@example.com',
                'full_name': 'Emma Taylor',
                'department': 'Engineering'
            }
        ]
        
        for data in mentees_data:
            if not CustomUser.objects.filter(phone_number=data['phone_number']).exists():
                CustomUser.objects.create_user(
                    phone_number=data['phone_number'],
                    email=data['email'],
                    full_name=data['full_name'],
                    role='mentee',
                    department=data['department'],
                    status='approved',
                    availability_status='active',
                    password='password123'
                )
                self.stdout.write(f"Created mentee: {data['full_name']}")
    
    def create_programs(self):
        """Create mentorship programs"""
        programs_data = [
            {
                'name': 'Leadership Development',
                'description': 'Develop leadership skills and executive presence',
                'total_sessions': 12,
                'duration_weeks': 12,
                'objectives': [
                    'Develop strategic thinking',
                    'Improve communication skills',
                    'Build executive presence'
                ]
            },
            {
                'name': 'Technical Skills',
                'description': 'Enhance technical expertise and problem-solving',
                'total_sessions': 10,
                'duration_weeks': 10,
                'objectives': [
                    'Master new technologies',
                    'Improve coding practices',
                    'Learn system design'
                ]
            },
            {
                'name': 'Career Growth',
                'description': 'Navigate career progression and opportunities',
                'total_sessions': 12,
                'duration_weeks': 12,
                'objectives': [
                    'Define career goals',
                    'Build professional network',
                    'Develop soft skills'
                ]
            },
            {
                'name': 'Product Management',
                'description': 'Learn product management best practices',
                'total_sessions': 8,
                'duration_weeks': 8,
                'objectives': [
                    'Understand product lifecycle',
                    'Learn user research',
                    'Develop product strategy'
                ]
            }
        ]
        
        for data in programs_data:
            program, created = MentorshipProgram.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['description'],
                    'total_sessions': data['total_sessions'],
                    'duration_weeks': data['duration_weeks'],
                    'objectives': data['objectives'],
                    'status': 'active'
                }
            )
            if created:
                self.stdout.write(f"Created program: {data['name']}")
    
    def create_mentorships(self):
        """Create sample mentorships"""
        mentors = list(CustomUser.objects.filter(role='mentor'))
        mentees = list(CustomUser.objects.filter(role='mentee'))
        programs = list(MentorshipProgram.objects.all())
        
        if not mentors or not mentees or not programs:
            self.stdout.write(self.style.WARNING('Not enough users or programs to create mentorships'))
            return
        
        mentorships_data = [
            {
                'mentor': mentors[0],
                'mentee': mentees[0],
                'program': programs[0],
                'status': 'active',
                'sessions_completed': 8,
                'rating': 4.8
            },
            {
                'mentor': mentors[1],
                'mentee': mentees[1],
                'program': programs[1],
                'status': 'active',
                'sessions_completed': 6,
                'rating': 4.9
            },
            {
                'mentor': mentors[2],
                'mentee': mentees[2],
                'program': programs[2],
                'status': 'completed',
                'sessions_completed': 12,
                'rating': 5.0
            },
            {
                'mentor': mentors[3],
                'mentee': mentees[3],
                'program': programs[3],
                'status': 'pending',
                'sessions_completed': 0,
                'rating': None
            },
            {
                'mentor': mentors[0],
                'mentee': mentees[4],
                'program': programs[0],
                'status': 'active',
                'sessions_completed': 5,
                'rating': 4.7
            },
            {
                'mentor': mentors[1],
                'mentee': mentees[5],
                'program': programs[1],
                'status': 'active',
                'sessions_completed': 7,
                'rating': 4.6
            }
        ]
        
        for data in mentorships_data:
            mentorship, created = Mentorship.objects.get_or_create(
                mentor=data['mentor'],
                mentee=data['mentee'],
                program=data['program'],
                defaults={
                    'status': data['status'],
                    'start_date': now().date() - timedelta(days=random.randint(30, 90)),
                    'sessions_completed': data['sessions_completed'],
                    'rating': data['rating'],
                    'goals': [
                        'Goal 1: Improve specific skill',
                        'Goal 2: Build confidence',
                        'Goal 3: Expand network'
                    ]
                }
            )
            if created:
                self.stdout.write(
                    f"Created mentorship: {data['mentor'].full_name} → {data['mentee'].full_name}"
                )
    
    def create_sessions(self):
        """Create sample sessions"""
        mentorships = Mentorship.objects.filter(status__in=['active', 'completed'])
        
        for mentorship in mentorships:
            # Create completed sessions
            for i in range(1, mentorship.sessions_completed + 1):
                session_date = mentorship.start_date + timedelta(weeks=i)
                MentorshipSession.objects.get_or_create(
                    mentorship=mentorship,
                    session_number=i,
                    defaults={
                        'session_type': 'video',
                        'status': 'completed',
                        'scheduled_date': now() - timedelta(weeks=mentorship.sessions_completed - i),
                        'actual_date': now() - timedelta(weeks=mentorship.sessions_completed - i),
                        'duration_minutes': 60,
                        'agenda': f'Session {i} agenda',
                        'notes': f'Session {i} completed successfully',
                        'mentor_rating': random.randint(4, 5)
                    }
                )
            
            # Create upcoming session if not completed
            if mentorship.status == 'active':
                next_session = mentorship.sessions_completed + 1
                if next_session <= mentorship.program.total_sessions:
                    MentorshipSession.objects.get_or_create(
                        mentorship=mentorship,
                        session_number=next_session,
                        defaults={
                            'session_type': 'video',
                            'status': 'scheduled',
                            'scheduled_date': now() + timedelta(days=7),
                            'duration_minutes': 60,
                            'agenda': f'Session {next_session} agenda'
                        }
                    )
        
        self.stdout.write(f"Created sessions for mentorships")