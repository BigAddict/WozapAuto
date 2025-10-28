"""
Tests for core views, particularly onboarding views and authentication.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages
from unittest.mock import patch, MagicMock

from core.models import UserProfile
from business.models import BusinessProfile, BusinessType


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
        messages_list = list(response.wsgi_request._messages)
        self.assertTrue(any('already completed' in str(msg) for msg in messages_list))
    
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
        # Set user to a step that should NOT allow access to profile step
        self.profile.onboarding_step = 'business'  # User is ahead of profile step
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('onboarding_profile'))
        self.assertRedirects(response, reverse('onboarding_business'))
    
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
        # Unauthenticated users should be redirected to signin with next parameter
        expected_url = f"{reverse('signin')}?next={reverse('onboarding_welcome')}"
        self.assertRedirects(response, expected_url)


class AuthenticationViewTestCase(TestCase):
    """Test cases for authentication views."""
    
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
    
    def test_signup_get(self):
        """Test signup page GET request."""
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign Up')
    
    def test_signup_post_valid(self):
        """Test signup page POST with valid data."""
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
    
    def test_signup_post_invalid(self):
        """Test signup page POST with invalid data."""
        signup_data = {
            'username': 'testuser',  # Duplicate username
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
    
    def test_signin_get(self):
        """Test signin page GET request."""
        response = self.client.get(reverse('signin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
    
    def test_signin_post_valid(self):
        """Test signin page POST with valid credentials."""
        signin_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(reverse('signin'), signin_data)
        # Signin redirects to home, but home redirects to onboarding for incomplete users
        self.assertRedirects(response, reverse('home'), target_status_code=302)
        
        # Verify user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_signin_post_invalid(self):
        """Test signin page POST with invalid credentials."""
        signin_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(reverse('signin'), signin_data)
        self.assertEqual(response.status_code, 200)  # Should stay on signin page
        self.assertContains(response, 'Invalid username or password')
    
    def test_signin_post_empty_fields(self):
        """Test signin page POST with empty fields."""
        signin_data = {
            'username': '',
            'password': ''
        }
        
        response = self.client.post(reverse('signin'), signin_data)
        self.assertEqual(response.status_code, 200)  # Should stay on signin page
        self.assertContains(response, 'Please fill in all fields')
    
    def test_signout(self):
        """Test signout functionality."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('signout'))
        # Signout redirects to home, but home requires login so redirects to signin
        self.assertRedirects(response, reverse('home'), target_status_code=302)
        
        # Verify user is logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_signin_with_next_parameter(self):
        """Test signin with next parameter redirect."""
        signin_data = {
            'username': 'testuser',
            'password': 'testpass123',
            'next': reverse('profile')
        }
        
        response = self.client.post(reverse('signin'), signin_data)
        self.assertRedirects(response, reverse('profile'))


class HomePageViewTestCase(TestCase):
    """Test cases for HomePageView."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
    
    def test_home_page_unauthenticated(self):
        """Test home page for unauthenticated user."""
        response = self.client.get(reverse('home'))
        # HomePageView requires login, so unauthenticated users get redirected to login
        self.assertRedirects(response, f"{reverse('signin')}?next={reverse('home')}")
    
    def test_home_page_authenticated_incomplete_onboarding(self):
        """Test home page for authenticated user with incomplete onboarding."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('onboarding_welcome'))
    
    def test_home_page_authenticated_complete_onboarding(self):
        """Test home page for authenticated user with complete onboarding."""
        self.profile.onboarding_completed = True
        self.profile.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_authenticated'])
        self.assertEqual(response.context['user_profile'], self.profile)
    
    def test_home_page_user_without_profile(self):
        """Test home page for user without profile (edge case)."""
        # Delete the profile to simulate edge case
        self.profile.delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('home'))
        # User without profile should be redirected to onboarding
        self.assertRedirects(response, reverse('onboarding_welcome'))


class ProfileViewTestCase(TestCase):
    """Test cases for profile views."""
    
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
    
    def test_profile_view_get(self):
        """Test profile view GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['profile'], self.profile)
    
    def test_profile_edit_get(self):
        """Test profile edit GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['profile'], self.profile)
    
    def test_profile_edit_post_valid(self):
        """Test profile edit POST with valid data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'newsletter_subscribed': 'on'
        }
        
        response = self.client.post(reverse('profile_edit'), form_data)
        self.assertRedirects(response, reverse('profile'))
        
        # Check user fields were updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'updated@example.com')
        
        # Check profile fields were updated
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.newsletter_subscribed)
    
    def test_profile_api_get(self):
        """Test profile API GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('profile_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['last_name'], 'User')
        self.assertEqual(data['email'], 'test@example.com')
        # Note: phone_number is now in BusinessProfile, not UserProfile
    
    def test_profile_api_post(self):
        """Test profile API POST request (should return 405)."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('profile_api'))
        self.assertEqual(response.status_code, 405)
        
        data = response.json()
        self.assertEqual(data['error'], 'Method not allowed')
