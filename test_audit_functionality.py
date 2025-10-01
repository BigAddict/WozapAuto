#!/usr/bin/env python
"""
Test script for email audit functionality in WozapAuto.
Run this script to test the email logging features.
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append('/home/bigaddict/Projects/Codebases/WozapAuto')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import models
from audit.models import EmailLog
from core.email_service import email_service
from connections.models import Connection

def test_email_logging():
    """Test email logging functionality"""
    print("🧪 Testing Email Audit Functionality")
    print("=" * 50)
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='audit_test_user',
        defaults={
            'email': 'audit.test@example.com',
            'first_name': 'Audit',
            'last_name': 'Test'
        }
    )
    
    if created:
        print(f"✅ Created test user: {user.username}")
    else:
        print(f"✅ Using existing test user: {user.username}")
    
    # Test 1: Check initial email log count
    initial_count = EmailLog.objects.count()
    print(f"📊 Initial email log count: {initial_count}")
    
    # Test 2: Send welcome email and check logging
    print("\n📧 Testing Welcome Email Logging...")
    try:
        success = email_service.send_welcome_email(user)
        if success:
            print("✅ Welcome email sent successfully!")
        else:
            print("❌ Failed to send welcome email")
        
        # Check if email was logged
        welcome_logs = EmailLog.objects.filter(
            email_type='welcome',
            recipient_user=user
        ).order_by('-created_at')
        
        if welcome_logs.exists():
            log = welcome_logs.first()
            print(f"✅ Email logged successfully:")
            print(f"   - Type: {log.get_email_type_display()}")
            print(f"   - Status: {log.get_status_display()}")
            print(f"   - Template: {log.template_used}")
            print(f"   - Created: {log.created_at}")
        else:
            print("❌ Email was not logged!")
            
    except Exception as e:
        print(f"❌ Error testing welcome email: {str(e)}")
    
    # Test 3: Test password reset email logging
    print("\n🔐 Testing Password Reset Email Logging...")
    try:
        # Create a mock request object
        class MockRequest:
            def build_absolute_uri(self, url):
                return f"http://localhost:8000{url}"
            META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'Test Browser'}
        
        mock_request = MockRequest()
        
        success = email_service.send_password_reset_email(user, mock_request)
        if success:
            print("✅ Password reset email sent successfully!")
        else:
            print("❌ Failed to send password reset email")
        
        # Check if email was logged
        reset_logs = EmailLog.objects.filter(
            email_type='password_reset',
            recipient_user=user
        ).order_by('-created_at')
        
        if reset_logs.exists():
            log = reset_logs.first()
            print(f"✅ Email logged successfully:")
            print(f"   - Type: {log.get_email_type_display()}")
            print(f"   - Status: {log.get_status_display()}")
            print(f"   - IP Address: {log.ip_address}")
            print(f"   - User Agent: {log.user_agent[:50]}...")
        else:
            print("❌ Email was not logged!")
            
    except Exception as e:
        print(f"❌ Error testing password reset email: {str(e)}")
    
    # Test 4: Test connection success email logging
    print("\n📱 Testing Connection Success Email Logging...")
    try:
        # Create a mock connection
        connection, created = Connection.objects.get_or_create(
            user=user,
            defaults={
                'instance_id': 'audit_test_instance_123',
                'instance_name': 'Audit Test Company',
                'ownerPhone': '+1234567890',
                'profileName': 'Audit Test Company',
                'connection_status': 'open',
                'instance_api_key': 'audit_test_api_key_123'
            }
        )
        
        if created:
            print(f"✅ Created test connection: {connection.instance_name}")
        else:
            print(f"✅ Using existing test connection: {connection.instance_name}")
        
        success = email_service.send_connection_success_email(user, connection)
        if success:
            print("✅ Connection success email sent successfully!")
        else:
            print("❌ Failed to send connection success email")
        
        # Check if email was logged
        connection_logs = EmailLog.objects.filter(
            email_type='connection_success',
            recipient_user=user
        ).order_by('-created_at')
        
        if connection_logs.exists():
            log = connection_logs.first()
            print(f"✅ Email logged successfully:")
            print(f"   - Type: {log.get_email_type_display()}")
            print(f"   - Status: {log.get_status_display()}")
            print(f"   - Context Data: {log.context_data}")
        else:
            print("❌ Email was not logged!")
            
    except Exception as e:
        print(f"❌ Error testing connection success email: {str(e)}")
    
    # Test 5: Check final email log count and statistics
    final_count = EmailLog.objects.count()
    print(f"\n📊 Final email log count: {final_count}")
    print(f"📈 New logs created: {final_count - initial_count}")
    
    # Show statistics by type
    print("\n📈 Email Log Statistics by Type:")
    stats = EmailLog.objects.values('email_type').annotate(
        count=models.Count('id'),
        sent=models.Count('id', filter=models.Q(status='sent')),
        failed=models.Count('id', filter=models.Q(status='failed')),
        pending=models.Count('id', filter=models.Q(status='pending'))
    ).order_by('email_type')
    
    for stat in stats:
        print(f"   - {stat['email_type']}: {stat['count']} total "
              f"({stat['sent']} sent, {stat['failed']} failed, {stat['pending']} pending)")
    
    # Test 6: Test admin interface accessibility
    print("\n🔧 Testing Admin Interface...")
    try:
        from django.contrib.admin.sites import site
        from audit.admin import EmailLogAdmin
        
        if site.is_registered(EmailLog):
            print("✅ EmailLog model is registered in admin")
        else:
            print("❌ EmailLog model is not registered in admin")
            
    except Exception as e:
        print(f"❌ Error checking admin registration: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Email audit functionality tests completed!")
    print("\n📋 Next Steps:")
    print("1. Check the Django admin panel at /admin/audit/emaillog/")
    print("2. View the email logs and their details")
    print("3. Test filtering and searching functionality")
    print("4. Run cleanup command: python manage.py cleanup_email_logs --dry-run")

if __name__ == '__main__':
    test_email_logging()
