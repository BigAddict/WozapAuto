"""
Tests for core models, particularly UserProfile and onboarding-related functionality.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from core.models import UserProfile
from business.models import BusinessProfile, BusinessType


class UserProfileModelTestCase(TestCase):
    """Test cases for UserProfile model."""
    
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
    
    def test_full_name_property(self):
        """Test full name property."""
        # Test with first and last name
        self.assertEqual(self.profile.full_name, 'Test User')
        
        # Test with only first name
        self.user.last_name = ''
        self.user.save()
        self.assertEqual(self.profile.full_name, 'Test')
        
        # Test with only username
        self.user.first_name = ''
        self.user.save()
        self.assertEqual(self.profile.full_name, 'testuser')
    
    def test_onboarding_completion_status(self):
        """Test onboarding completion status checks."""
        # Test incomplete onboarding
        self.assertFalse(self.profile.is_onboarding_complete())
        
        # Test completion via flag
        self.profile.onboarding_completed = True
        self.profile.save()
        self.assertTrue(self.profile.is_onboarding_complete())
        
        # Test completion via step
        self.profile.onboarding_completed = False
        self.profile.onboarding_step = 'complete'
        self.profile.save()
        self.assertTrue(self.profile.is_onboarding_complete())
    
    def test_onboarding_step_choices(self):
        """Test onboarding step choices."""
        valid_steps = ['welcome', 'profile', 'business', 'verify', 'complete']
        
        for step in valid_steps:
            self.profile.onboarding_step = step
            self.profile.save()
            self.profile.refresh_from_db()
            self.assertEqual(self.profile.onboarding_step, step)
    
    def test_profile_str_representation(self):
        """Test string representation of profile."""
        expected_str = f"{self.user.username}'s Profile"
        self.assertEqual(str(self.profile), expected_str)
    
    def test_profile_meta_options(self):
        """Test profile meta options."""
        self.assertEqual(UserProfile._meta.verbose_name, "User Profile")
        self.assertEqual(UserProfile._meta.verbose_name_plural, "User Profiles")


class BusinessProfileOTPTestCase(TestCase):
    """Test cases for BusinessProfile OTP functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create business type for testing
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
        
        self.business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD'
        )
    
    def test_otp_generation(self):
        """Test OTP generation for business profile."""
        # Generate OTP
        otp_code = self.business_profile.generate_otp()
        
        # Verify OTP properties
        self.assertEqual(len(otp_code), 6)
        self.assertTrue(otp_code.isdigit())
        self.assertIsNotNone(self.business_profile.otp_code)
        self.assertIsNotNone(self.business_profile.otp_created_at)
        self.assertEqual(self.business_profile.otp_attempts, 0)
    
    def test_otp_verification_success(self):
        """Test successful OTP verification."""
        # Generate OTP
        otp_code = self.business_profile.generate_otp()
        
        # Test successful verification
        success, message = self.business_profile.verify_otp(otp_code)
        self.assertTrue(success)
        self.assertEqual(message, "OTP verified successfully")
        self.assertTrue(self.business_profile.is_verified)
        self.assertIsNone(self.business_profile.otp_code)
        self.assertIsNone(self.business_profile.otp_created_at)
        self.assertEqual(self.business_profile.otp_attempts, 0)
    
    def test_otp_verification_invalid_code(self):
        """Test OTP verification with invalid code."""
        # Generate OTP
        self.business_profile.generate_otp()
        
        # Test invalid OTP
        success, message = self.business_profile.verify_otp('000000')
        self.assertFalse(success)
        self.assertEqual(message, "Invalid OTP code")
        self.assertEqual(self.business_profile.otp_attempts, 1)
        self.assertFalse(self.business_profile.is_verified)
    
    def test_otp_expiry(self):
        """Test OTP expiry functionality."""
        # Generate OTP
        otp_code = self.business_profile.generate_otp()
        
        # Simulate expired OTP by setting created_at to past
        self.business_profile.otp_created_at = timezone.now() - timedelta(minutes=11)
        self.business_profile.save()
        
        # Test expired OTP verification
        success, message = self.business_profile.verify_otp(otp_code)
        self.assertFalse(success)
        self.assertEqual(message, "OTP code has expired. Please request a new code.")
    
    def test_max_otp_attempts(self):
        """Test maximum OTP attempts limit."""
        # Generate OTP
        self.business_profile.generate_otp()
        
        # Test maximum attempts
        for i in range(3):
            success, message = self.business_profile.verify_otp('000000')
            self.assertFalse(success)
            self.assertEqual(message, "Invalid OTP code")
        
        # Fourth attempt should fail with max attempts message
        success, message = self.business_profile.verify_otp('000000')
        self.assertFalse(success)
        self.assertEqual(message, "Maximum OTP attempts exceeded. Please request a new code.")
    
    def test_otp_verification_no_otp(self):
        """Test OTP verification when no OTP exists."""
        # Test verification without OTP generated
        success, message = self.business_profile.verify_otp('123456')
        self.assertFalse(success)
        self.assertEqual(message, "No OTP code found")
    
    def test_multiple_otp_generations(self):
        """Test multiple OTP generations."""
        # Generate first OTP
        otp1 = self.business_profile.generate_otp()
        created_at1 = self.business_profile.otp_created_at
        
        # Generate second OTP
        otp2 = self.business_profile.generate_otp()
        created_at2 = self.business_profile.otp_created_at
        
        # Verify OTPs are different
        self.assertNotEqual(otp1, otp2)
        self.assertGreater(created_at2, created_at1)
        
        # Verify second OTP works
        success, message = self.business_profile.verify_otp(otp2)
        self.assertTrue(success)
        self.assertTrue(self.business_profile.is_verified)
