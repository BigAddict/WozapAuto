#!/usr/bin/env python
"""
Test script for email functionality in WozapAuto.
Run this script to test the email features without going through the web interface.
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
from core.email_service import email_service
from connections.models import Connection

def test_welcome_email():
    """Test welcome email functionality"""
    print("Testing Welcome Email...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing test user: {user.username}")
    
    # Test welcome email
    try:
        success = email_service.send_welcome_email(user)
        if success:
            print("✅ Welcome email sent successfully!")
        else:
            print("❌ Failed to send welcome email")
    except Exception as e:
        print(f"❌ Error sending welcome email: {str(e)}")

def test_password_reset_email():
    """Test password reset email functionality"""
    print("\nTesting Password Reset Email...")
    
    # Get test user
    try:
        user = User.objects.get(username='test_user')
        
        # Create a mock request object
        class MockRequest:
            def build_absolute_uri(self, url):
                return f"http://localhost:8000{url}"
        
        mock_request = MockRequest()
        
        # Test password reset email
        success = email_service.send_password_reset_email(user, mock_request)
        if success:
            print("✅ Password reset email sent successfully!")
        else:
            print("❌ Failed to send password reset email")
    except User.DoesNotExist:
        print("❌ Test user not found. Please run test_welcome_email first.")
    except Exception as e:
        print(f"❌ Error sending password reset email: {str(e)}")

def test_password_change_email():
    """Test password change confirmation email functionality"""
    print("\nTesting Password Change Email...")
    
    # Get test user
    try:
        user = User.objects.get(username='test_user')
        
        # Test password change email
        success = email_service.send_password_change_confirmation_email(user)
        if success:
            print("✅ Password change email sent successfully!")
        else:
            print("❌ Failed to send password change email")
    except User.DoesNotExist:
        print("❌ Test user not found. Please run test_welcome_email first.")
    except Exception as e:
        print(f"❌ Error sending password change email: {str(e)}")

def test_connection_success_email():
    """Test connection success email functionality"""
    print("\nTesting Connection Success Email...")
    
    # Get test user
    try:
        user = User.objects.get(username='test_user')
        
        # Create a mock connection
        connection, created = Connection.objects.get_or_create(
            user=user,
            defaults={
                'instance_id': 'test_instance_123',
                'instance_name': 'Test Company',
                'ownerPhone': '+1234567890',
                'profileName': 'Test Company',
                'connection_status': 'open',
                'instance_api_key': 'test_api_key_123'
            }
        )
        
        if created:
            print(f"Created test connection: {connection.instance_name}")
        else:
            print(f"Using existing test connection: {connection.instance_name}")
        
        # Test connection success email
        success = email_service.send_connection_success_email(user, connection)
        if success:
            print("✅ Connection success email sent successfully!")
        else:
            print("❌ Failed to send connection success email")
    except User.DoesNotExist:
        print("❌ Test user not found. Please run test_welcome_email first.")
    except Exception as e:
        print(f"❌ Error sending connection success email: {str(e)}")

def main():
    """Run all email tests"""
    print("🚀 Starting WozapAuto Email Functionality Tests")
    print("=" * 50)
    
    # Check if email settings are configured
    if not settings.EMAIL_HOST:
        print("❌ Email settings not configured. Please check your .env file.")
        print("Required environment variables:")
        print("- SMTP_HOST")
        print("- SMTP_USERNAME") 
        print("- SMTP_PASSWORD")
        print("- SMTP_FROM_EMAIL")
        print("- SMTP_FROM_NAME")
        return
    
    print(f"📧 Using SMTP server: {settings.EMAIL_HOST}")
    print(f"📧 From email: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Run tests
    test_welcome_email()
    test_password_reset_email()
    test_password_change_email()
    test_connection_success_email()
    
    print("\n" + "=" * 50)
    print("🎉 Email functionality tests completed!")
    print("\nNote: Check your email inbox to verify the emails were sent successfully.")
    print("If you don't receive emails, check your SMTP settings and spam folder.")

if __name__ == '__main__':
    main()
