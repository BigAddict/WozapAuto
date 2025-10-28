"""
Comprehensive tests for the onboarding process in WozapAuto.

This test suite covers:
1. Onboarding flow progression and step validation
2. Form validation and error handling
3. WhatsApp OTP verification process
4. Edge cases and error scenarios
5. Integration between different onboarding steps
6. Business profile creation and validation
7. User profile management during onboarding
"""

from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import json

from core.models import UserProfile
from core.forms import PersonalProfileForm, BusinessProfileForm, OTPVerificationForm, CustomUserCreationForm
from business.models import BusinessProfile, BusinessType
from audit.models import UserActivityLog


class OnboardingModelTestCase(TestCase):
    """Test cases for onboarding-related models and methods."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.profile = self.user.profile
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
    
    def test_user_profile_creation(self):
        """Test that UserProfile is automatically created when User is created."""
        self.assertIsInstance(self.profile, UserProfile)
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.onboarding_step, 'welcome')
        self.assertFalse(self.profile.onboarding_completed)
    
    def test_onboarding_step_progression(self):
        """Test onboarding step progression."""
        # Test initial state
        self.assertEqual(self.profile.onboarding_step, 'welcome')
        self.assertFalse(self.profile.is_onboarding_complete())
        
        # Test step advancement
        self.profile.advance_onboarding_step()
        self.assertEqual(self.profile.onboarding_step, 'profile')
        
        self.profile.advance_onboarding_step()
        self.assertEqual(self.profile.onboarding_step, 'business')
        
        self.profile.advance_onboarding_step()
        self.assertEqual(self.profile.onboarding_step, 'verify')
        
        self.profile.advance_onboarding_step()
        self.assertEqual(self.profile.onboarding_step, 'complete')
        self.assertTrue(self.profile.onboarding_completed)
    
    def test_get_onboarding_redirect_url(self):
        """Test onboarding redirect URL generation."""
        # Test welcome step
        self.profile.onboarding_step = 'welcome'
        url = self.profile.get_onboarding_redirect_url()
        self.assertEqual(url, reverse('onboarding_welcome'))
        
        # Test profile step
        self.profile.onboarding_step = 'profile'
        url = self.profile.get_onboarding_redirect_url()
        self.assertEqual(url, reverse('onboarding_profile'))
        
        # Test business step
        self.profile.onboarding_step = 'business'
        url = self.profile.get_onboarding_redirect_url()
        self.assertEqual(url, reverse('onboarding_business'))
        
        # Test verify step
        self.profile.onboarding_step = 'verify'
        url = self.profile.get_onboarding_redirect_url()
        self.assertEqual(url, reverse('onboarding_verify'))
        
        # Test complete step
        self.profile.onboarding_step = 'complete'
        url = self.profile.get_onboarding_redirect_url()
        self.assertEqual(url, reverse('home'))
        
        # Test completed profile
        self.profile.onboarding_completed = True
        url = self.profile.get_onboarding_redirect_url()
        self.assertEqual(url, reverse('home'))
    
    def test_display_name_property(self):
        """Test display name property."""
        # Test with first and last name
        self.assertEqual(self.profile.display_name, 'Test User')
        
        # Test with only first name
        self.user.last_name = ''
        self.user.save()
        self.assertEqual(self.profile.display_name, 'Test')
        
        # Test with only username
        self.user.first_name = ''
        self.user.save()
        self.assertEqual(self.profile.display_name, 'testuser')
    
    def test_business_profile_otp_generation(self):
        """Test OTP generation for business profile."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        # Generate OTP
        otp_code = business_profile.generate_otp()
        
        # Verify OTP properties
        self.assertEqual(len(otp_code), 6)
        self.assertTrue(otp_code.isdigit())
        self.assertIsNotNone(business_profile.otp_code)
        self.assertIsNotNone(business_profile.otp_created_at)
        self.assertEqual(business_profile.otp_attempts, 0)
    
    def test_business_profile_otp_verification(self):
        """Test OTP verification for business profile."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        # Generate OTP
        otp_code = business_profile.generate_otp()
        
        # Test successful verification
        success, message = business_profile.verify_otp(otp_code)
        self.assertTrue(success)
        self.assertEqual(message, "OTP verified successfully")
        self.assertTrue(business_profile.is_verified)
        self.assertIsNone(business_profile.otp_code)
        self.assertIsNone(business_profile.otp_created_at)
        self.assertEqual(business_profile.otp_attempts, 0)
        
        # Test invalid OTP
        business_profile.generate_otp()
        success, message = business_profile.verify_otp('000000')
        self.assertFalse(success)
        self.assertEqual(message, "Invalid OTP code")
        self.assertEqual(business_profile.otp_attempts, 1)
    
    def test_business_profile_otp_expiry(self):
        """Test OTP expiry functionality."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        # Generate OTP
        otp_code = business_profile.generate_otp()
        
        # Simulate expired OTP by setting created_at to past
        business_profile.otp_created_at = timezone.now() - timedelta(minutes=11)
        business_profile.save()
        
        # Test expired OTP verification
        success, message = business_profile.verify_otp(otp_code)
        self.assertFalse(success)
        self.assertEqual(message, "OTP code has expired. Please request a new code.")
    
    def test_business_profile_max_attempts(self):
        """Test maximum OTP attempts limit."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        # Generate OTP
        otp_code = business_profile.generate_otp()
        
        # Test maximum attempts
        for i in range(3):
            success, message = business_profile.verify_otp('000000')
            self.assertFalse(success)
            self.assertEqual(message, "Invalid OTP code")
        
        # Fourth attempt should fail with max attempts message
        success, message = business_profile.verify_otp('000000')
        self.assertFalse(success)
        self.assertEqual(message, "Maximum OTP attempts exceeded. Please request a new code.")


class OnboardingFormTestCase(TestCase):
    """Test cases for onboarding forms."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
    
    def test_personal_profile_form_valid_data(self):
        """Test PersonalProfileForm with valid data."""
        form_data = {
            'newsletter_subscribed': True
        }
        
        form = PersonalProfileForm(data=form_data, instance=self.profile)
        self.assertTrue(form.is_valid())
        
        # Test form save
        form.save()
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.newsletter_subscribed)
    
    def test_personal_profile_form_avatar_validation(self):
        """Test PersonalProfileForm avatar validation."""
        # Test valid image file
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        image_file = SimpleUploadedFile('test.png', image_content, content_type='image/png')
        
        form_data = {
            'newsletter_subscribed': False
        }
        files_data = {
            'avatar': image_file
        }
        
        form = PersonalProfileForm(data=form_data, files=files_data, instance=self.profile)
        self.assertTrue(form.is_valid())
        
        # Test invalid file type
        text_file = SimpleUploadedFile('test.txt', b'Hello World', content_type='text/plain')
        files_data = {
            'avatar': text_file
        }
        
        form = PersonalProfileForm(data=form_data, files=files_data, instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('Please upload a valid image file', str(form.errors))
    
    def test_business_profile_form_valid_data(self):
        """Test BusinessProfileForm with valid data."""
        form_data = {
            'name': 'Test Business',
            'business_type': self.business_type.id,
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD',
            'description': 'Test business description',
            'email': 'business@example.com',
            'website': 'https://example.com',
            'address': '123 Test Street'
        }
        
        form = BusinessProfileForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test form save
        business_profile = form.save(commit=False)
        business_profile.user = self.user
        business_profile.save()
        
        self.assertEqual(business_profile.name, 'Test Business')
        self.assertEqual(business_profile.phone_number, '+1234567890')
    
    def test_business_profile_form_phone_validation(self):
        """Test BusinessProfileForm phone number validation."""
        form_data = {
            'name': 'Test Business',
            'business_type': self.business_type.id,
            'phone_number': '1234567890',  # Missing country code
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD'
        }
        
        form = BusinessProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a valid phone number with country code', str(form.errors))
        
        # Test valid phone number
        form_data['phone_number'] = '+1234567890'
        form = BusinessProfileForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_otp_verification_form_valid_data(self):
        """Test OTPVerificationForm with valid data."""
        form_data = {
            'otp_code': '123456'
        }
        
        form = OTPVerificationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['otp_code'], '123456')
    
    def test_otp_verification_form_invalid_data(self):
        """Test OTPVerificationForm with invalid data."""
        # Test non-numeric OTP
        form_data = {
            'otp_code': 'abc123'
        }
        
        form = OTPVerificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a valid 6-digit code', str(form.errors))
        
        # Test wrong length OTP
        form_data = {
            'otp_code': '12345'
        }
        
        form = OTPVerificationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please enter a valid 6-digit code', str(form.errors))
    
    def test_custom_user_creation_form_valid_data(self):
        """Test CustomUserCreationForm with valid data."""
        form_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_agreement': True,
            'newsletter': False
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Test form save
        user = form.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertTrue(user.profile.newsletter_subscribed == False)
    
    def test_custom_user_creation_form_password_validation(self):
        """Test CustomUserCreationForm password validation."""
        form_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'weak',  # Weak password
            'password2': 'weak',
            'terms_agreement': True,
            'newsletter': False
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Password must be at least 8 characters long', str(form.errors))
        
        # Test password without uppercase
        form_data['password1'] = 'testpass123!'
        form_data['password2'] = 'testpass123!'
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Password must contain at least one uppercase letter', str(form.errors))
    
    def test_custom_user_creation_form_email_uniqueness(self):
        """Test CustomUserCreationForm email uniqueness validation."""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )
        
        form_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'existing@example.com',  # Duplicate email
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_agreement': True,
            'newsletter': False
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('An account with this email address already exists', str(form.errors))


class OnboardingViewTestCase(TestCase):
    """Test cases for onboarding views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.profile = self.user.profile
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
    
    def test_onboarding_welcome_get(self):
        """Test onboarding welcome page GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_welcome'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome')
    
    def test_onboarding_welcome_already_completed(self):
        """Test onboarding welcome when already completed."""
        self.profile.onboarding_completed = True
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_welcome'))
        self.assertRedirects(response, reverse('home'))
        
        # Check for info message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('already completed' in str(msg) for msg in messages))
    
    def test_onboarding_welcome_wrong_step(self):
        """Test onboarding welcome when on wrong step."""
        self.profile.onboarding_step = 'profile'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_welcome'))
        self.assertRedirects(response, reverse('onboarding_profile'))
    
    def test_onboarding_profile_get(self):
        """Test onboarding profile page GET request."""
        self.profile.onboarding_step = 'profile'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Personal Profile')
    
    def test_onboarding_profile_post_valid(self):
        """Test onboarding profile page POST with valid data."""
        self.profile.onboarding_step = 'profile'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'newsletter_subscribed': True
        }
        
        response = self.client.post(reverse('onboarding_profile'), form_data)
        self.assertRedirects(response, reverse('onboarding_business'))
        
        # Check profile was updated
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.newsletter_subscribed)
        self.assertEqual(self.profile.onboarding_step, 'business')
    
    def test_onboarding_profile_wrong_step(self):
        """Test onboarding profile when on wrong step."""
        self.profile.onboarding_step = 'welcome'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_profile'))
        self.assertRedirects(response, reverse('onboarding_welcome'))
    
    @patch('core.onboarding_views.whatsapp_service.send_otp_message')
    def test_onboarding_business_post_valid(self, mock_send_otp):
        """Test onboarding business page POST with valid data."""
        self.profile.onboarding_step = 'business'
        self.profile.save()
        
        mock_send_otp.return_value = True
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'Test Business',
            'business_type': self.business_type.id,
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD',
            'description': 'Test business description'
        }
        
        response = self.client.post(reverse('onboarding_business'), form_data)
        self.assertRedirects(response, reverse('onboarding_verify'))
        
        # Check business profile was created
        business_profile = BusinessProfile.objects.get(user=self.user)
        self.assertEqual(business_profile.name, 'Test Business')
        self.assertEqual(business_profile.phone_number, '+1234567890')
        
        # Check OTP was generated
        self.assertIsNotNone(business_profile.otp_code)
        self.assertIsNotNone(business_profile.otp_created_at)
        
        # Check WhatsApp service was called
        mock_send_otp.assert_called_once()
    
    @patch('core.onboarding_views.whatsapp_service.send_otp_message')
    def test_onboarding_business_whatsapp_failure(self, mock_send_otp):
        """Test onboarding business when WhatsApp service fails."""
        self.profile.onboarding_step = 'business'
        self.profile.save()
        
        mock_send_otp.return_value = False
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'Test Business',
            'business_type': self.business_type.id,
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD'
        }
        
        response = self.client.post(reverse('onboarding_business'), form_data)
        self.assertRedirects(response, reverse('onboarding_verify'))
        
        # Check business profile was still created
        business_profile = BusinessProfile.objects.get(user=self.user)
        self.assertEqual(business_profile.name, 'Test Business')
    
    def test_onboarding_business_already_exists_verified(self):
        """Test onboarding business when business profile already exists and is verified."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Existing Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True
        )
        
        self.profile.onboarding_step = 'business'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_business'))
        self.assertRedirects(response, reverse('home'))
        
        # Check profile was marked as completed
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.onboarding_completed)
        self.assertEqual(self.profile.onboarding_step, 'complete')
    
    def test_onboarding_business_already_exists_unverified(self):
        """Test onboarding business when business profile exists but is not verified."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Existing Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=False
        )
        
        self.profile.onboarding_step = 'business'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_business'))
        self.assertRedirects(response, reverse('onboarding_verify'))
    
    def test_onboarding_verify_get(self):
        """Test onboarding verify page GET request."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        self.profile.onboarding_step = 'verify'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_verify'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verification')
    
    def test_onboarding_verify_post_valid(self):
        """Test onboarding verify page POST with valid OTP."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        # Generate OTP
        otp_code = business_profile.generate_otp()
        
        self.profile.onboarding_step = 'verify'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'otp_code': otp_code
        }
        
        response = self.client.post(reverse('onboarding_verify'), form_data)
        self.assertRedirects(response, reverse('home'))
        
        # Check business profile was verified
        business_profile.refresh_from_db()
        self.assertTrue(business_profile.is_verified)
        
        # Check profile was advanced
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.onboarding_completed)
        self.assertEqual(self.profile.onboarding_step, 'complete')
    
    def test_onboarding_verify_post_invalid(self):
        """Test onboarding verify page POST with invalid OTP."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        business_profile.generate_otp()
        
        self.profile.onboarding_step = 'verify'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'otp_code': '000000'  # Invalid OTP
        }
        
        response = self.client.post(reverse('onboarding_verify'), form_data)
        self.assertEqual(response.status_code, 200)
        
        # Check business profile was not verified
        business_profile.refresh_from_db()
        self.assertFalse(business_profile.is_verified)
        self.assertEqual(business_profile.otp_attempts, 1)
    
    def test_onboarding_verify_already_verified(self):
        """Test onboarding verify when already verified."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True
        )
        
        self.profile.onboarding_step = 'verify'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_verify'))
        self.assertRedirects(response, reverse('home'))
        
        # Check profile was advanced
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.onboarding_completed)
    
    def test_onboarding_verify_no_business_profile(self):
        """Test onboarding verify when no business profile exists."""
        self.profile.onboarding_step = 'verify'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_verify'))
        self.assertRedirects(response, reverse('onboarding_business'))
    
    def test_onboarding_complete_get(self):
        """Test onboarding complete page GET request."""
        self.profile.onboarding_completed = True
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_complete'))
        self.assertEqual(response.status_code, 200)
    
    def test_onboarding_complete_not_completed(self):
        """Test onboarding complete when not completed."""
        self.profile.onboarding_step = 'profile'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_complete'))
        self.assertRedirects(response, reverse('onboarding_profile'))
    
    def test_redirect_to_onboarding_authenticated(self):
        """Test redirect to onboarding for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('welcome_onboarding'))
        self.assertRedirects(response, reverse('onboarding_welcome'))
    
    def test_redirect_to_onboarding_unauthenticated(self):
        """Test redirect to onboarding for unauthenticated user."""
        response = self.client.get(reverse('welcome_onboarding'))
        self.assertRedirects(response, reverse('onboarding_welcome'))


class OnboardingIntegrationTestCase(TransactionTestCase):
    """Integration tests for the complete onboarding flow."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
    
    @patch('core.onboarding_views.whatsapp_service.send_otp_message')
    def test_complete_onboarding_flow(self, mock_send_otp):
        """Test the complete onboarding flow from start to finish."""
        mock_send_otp.return_value = True
        
        # Step 1: Sign up
        signup_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_agreement': True,
            'newsletter': False
        }
        
        response = self.client.post(reverse('signup'), signup_data)
        self.assertRedirects(response, reverse('onboarding_welcome'))
        
        # Verify user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        
        # Verify profile was created
        profile = user.profile
        self.assertEqual(profile.onboarding_step, 'welcome')
        self.assertFalse(profile.onboarding_completed)
        
        # Step 2: Welcome page
        self.client.login(username='newuser', password='TestPass123!')
        
        response = self.client.get(reverse('onboarding_welcome'))
        self.assertEqual(response.status_code, 200)
        
        # Step 3: Profile completion
        profile_data = {
            'newsletter_subscribed': True
        }
        
        response = self.client.post(reverse('onboarding_profile'), profile_data)
        self.assertRedirects(response, reverse('onboarding_business'))
        
        # Verify profile was updated
        profile.refresh_from_db()
        self.assertEqual(profile.onboarding_step, 'business')
        self.assertTrue(profile.newsletter_subscribed)
        
        # Step 4: Business profile creation
        business_data = {
            'name': 'New Business',
            'business_type': self.business_type.id,
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD',
            'description': 'New business description'
        }
        
        response = self.client.post(reverse('onboarding_business'), business_data)
        self.assertRedirects(response, reverse('onboarding_verify'))
        
        # Verify business profile was created
        business_profile = BusinessProfile.objects.get(user=user)
        self.assertEqual(business_profile.name, 'New Business')
        self.assertEqual(business_profile.phone_number, '+1234567890')
        self.assertIsNotNone(business_profile.otp_code)
        
        # Step 5: OTP verification
        otp_code = business_profile.otp_code
        
        verify_data = {
            'otp_code': otp_code
        }
        
        response = self.client.post(reverse('onboarding_verify'), verify_data)
        self.assertRedirects(response, reverse('home'))
        
        # Verify business profile was verified
        business_profile.refresh_from_db()
        self.assertTrue(business_profile.is_verified)
        
        # Verify profile was completed
        profile.refresh_from_db()
        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(profile.onboarding_step, 'complete')
    
    def test_onboarding_flow_with_errors(self):
        """Test onboarding flow with various error scenarios."""
        # Test signup with invalid data
        signup_data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'invalid-email',  # Invalid email
            'password1': 'weak',  # Weak password
            'password2': 'weak',
            'terms_agreement': False,  # Not agreed to terms
            'newsletter': False
        }
        
        response = self.client.post(reverse('signup'), signup_data)
        self.assertEqual(response.status_code, 200)  # Should stay on signup page
        self.assertContains(response, 'error')  # Should contain error messages
        
        # Test business profile creation with invalid phone
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        business_data = {
            'name': 'Test Business',
            'business_type': self.business_type.id,
            'phone_number': '1234567890',  # Invalid phone format
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD'
        }
        
        response = self.client.post(reverse('onboarding_business'), business_data)
        self.assertEqual(response.status_code, 200)  # Should stay on business page
        self.assertContains(response, 'error')  # Should contain error messages
    
    def test_onboarding_step_validation(self):
        """Test that users cannot skip onboarding steps."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Try to access business step without completing profile
        response = self.client.get(reverse('onboarding_business'))
        self.assertRedirects(response, reverse('onboarding_welcome'))
        
        # Try to access verify step without completing business
        response = self.client.get(reverse('onboarding_verify'))
        self.assertRedirects(response, reverse('onboarding_welcome'))
        
        # Try to access complete step without completing verify
        response = self.client.get(reverse('onboarding_complete'))
        self.assertRedirects(response, reverse('onboarding_welcome'))


class OnboardingEdgeCaseTestCase(TestCase):
    """Test cases for edge cases and error scenarios in onboarding."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
    
    def test_user_without_profile(self):
        """Test handling of user without profile (edge case)."""
        # Delete the profile to simulate edge case
        self.profile.delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_welcome'))
        self.assertRedirects(response, reverse('home'))
        
        # Check for error message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('Profile not found' in str(msg) for msg in messages))
    
    def test_business_profile_phone_uniqueness(self):
        """Test business profile phone number uniqueness constraint."""
        # Create first business profile
        BusinessProfile.objects.create(
            user=self.user,
            name='First Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        # Try to create second business profile with same phone
        another_user = User.objects.create_user(
            username='anotheruser',
            email='another@example.com',
            password='testpass123'
        )
        
        self.client.login(username='anotheruser', password='testpass123')
        
        business_data = {
            'name': 'Second Business',
            'business_type': self.business_type.id,
            'phone_number': '+1234567890',  # Same phone number
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD'
        }
        
        response = self.client.post(reverse('onboarding_business'), business_data)
        self.assertEqual(response.status_code, 200)  # Should stay on business page
        self.assertContains(response, 'error')  # Should contain error messages
    
    def test_otp_verification_edge_cases(self):
        """Test OTP verification edge cases."""
        business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test verification without OTP generated
        verify_data = {
            'otp_code': '123456'
        }
        
        response = self.client.post(reverse('onboarding_verify'), verify_data)
        self.assertEqual(response.status_code, 200)
        
        # Test verification with expired OTP
        business_profile.generate_otp()
        business_profile.otp_created_at = timezone.now() - timedelta(minutes=11)
        business_profile.save()
        
        response = self.client.post(reverse('onboarding_verify'), verify_data)
        self.assertEqual(response.status_code, 200)
        
        # Test verification with max attempts exceeded
        business_profile.generate_otp()
        business_profile.otp_attempts = 3
        business_profile.save()
        
        response = self.client.post(reverse('onboarding_verify'), verify_data)
        self.assertEqual(response.status_code, 200)
    
    def test_onboarding_step_advancement_edge_cases(self):
        """Test edge cases in onboarding step advancement."""
        # Test advancement from complete step
        self.profile.onboarding_step = 'complete'
        self.profile.onboarding_completed = True
        self.profile.save()
        
        # Should not advance further
        original_step = self.profile.onboarding_step
        self.profile.advance_onboarding_step()
        self.assertEqual(self.profile.onboarding_step, original_step)
    
    def test_form_validation_edge_cases(self):
        """Test form validation edge cases."""
        # Test PersonalProfileForm with empty data
        form = PersonalProfileForm(data={})
        self.assertTrue(form.is_valid())  # Should be valid with empty data
        
        # Test BusinessProfileForm with empty required fields
        form = BusinessProfileForm(data={})
        self.assertFalse(form.is_valid())
        
        # Test OTPVerificationForm with empty data
        form = OTPVerificationForm(data={})
        self.assertFalse(form.is_valid())
    
    def test_whatsapp_service_failure_handling(self):
        """Test handling of WhatsApp service failures."""
        self.profile.onboarding_step = 'business'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        business_data = {
            'name': 'Test Business',
            'business_type': self.business_type.id,
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD'
        }
        
        # Mock WhatsApp service failure
        with patch('core.onboarding_views.whatsapp_service.send_otp_message', return_value=False):
            response = self.client.post(reverse('onboarding_business'), business_data)
            self.assertRedirects(response, reverse('onboarding_verify'))
            
            # Check for error message
            messages = list(response.wsgi_request._messages)
            self.assertTrue(any('failed to send verification code' in str(msg) for msg in messages))
    
    def test_concurrent_onboarding_attempts(self):
        """Test handling of concurrent onboarding attempts."""
        # Simulate multiple requests to the same onboarding step
        self.profile.onboarding_step = 'profile'
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        # First request
        response1 = self.client.get(reverse('onboarding_profile'))
        self.assertEqual(response1.status_code, 200)
        
        # Second request (should still work)
        response2 = self.client.get(reverse('onboarding_profile'))
        self.assertEqual(response2.status_code, 200)
    
    def test_onboarding_with_inactive_business_type(self):
        """Test onboarding with inactive business type."""
        # Create inactive business type
        inactive_type = BusinessType.objects.create(
            name='inactive',
            display_name='Inactive Business Type',
            is_active=False
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        business_data = {
            'name': 'Test Business',
            'business_type': inactive_type.id,  # Inactive business type
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD'
        }
        
        response = self.client.post(reverse('onboarding_business'), business_data)
        self.assertEqual(response.status_code, 200)  # Should stay on business page
        self.assertContains(response, 'error')  # Should contain error messages


class OnboardingPerformanceTestCase(TestCase):
    """Test cases for onboarding performance and optimization."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
    
    def test_onboarding_page_load_performance(self):
        """Test that onboarding pages load quickly."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test welcome page load time
        import time
        start_time = time.time()
        response = self.client.get(reverse('onboarding_welcome'))
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 1.0)  # Should load in less than 1 second
    
    def test_onboarding_form_submission_performance(self):
        """Test that onboarding form submissions are fast."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test profile form submission
        profile_data = {
            'newsletter_subscribed': True
        }
        
        import time
        start_time = time.time()
        response = self.client.post(reverse('onboarding_profile'), profile_data)
        end_time = time.time()
        
        self.assertRedirects(response, reverse('onboarding_business'))
        self.assertLess(end_time - start_time, 2.0)  # Should process in less than 2 seconds
    
    def test_onboarding_database_queries_optimization(self):
        """Test that onboarding views don't make excessive database queries."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test database query count for welcome page
        from django.test.utils import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            connection.queries_log.clear()
            response = self.client.get(reverse('onboarding_welcome'))
            query_count = len(connection.queries)
            
            self.assertEqual(response.status_code, 200)
            self.assertLess(query_count, 10)  # Should not make more than 10 queries
