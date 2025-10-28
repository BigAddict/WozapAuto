"""
Test configuration and utilities for WozapAuto.

This module provides test configuration, fixtures, and utilities
for running comprehensive tests across the application.
"""

import os
import tempfile
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import datetime, timedelta

from core.models import UserProfile
from business.models import BusinessProfile, BusinessType, Category, Product, Service


class WozapAutoTestCase(TestCase):
    """Base test case for WozapAuto with common setup."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media_dir = tempfile.mkdtemp()
    
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Clean up temp media directory
        import shutil
        shutil.rmtree(cls.temp_media_dir, ignore_errors=True)
    
    def create_test_user(self, username='testuser', email='test@example.com', **kwargs):
        """Create a test user with profile."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123',
            **kwargs
        )
        return user
    
    def create_test_business_type(self, name='ecommerce', **kwargs):
        """Create a test business type."""
        return BusinessType.objects.create(
            name=name,
            display_name=f'{name.title()} Store',
            is_active=True,
            **kwargs
        )
    
    def create_test_business_profile(self, user=None, business_type=None, **kwargs):
        """Create a test business profile."""
        if user is None:
            user = self.create_test_user()
        if business_type is None:
            business_type = self.create_test_business_type()
        
        return BusinessProfile.objects.create(
            user=user,
            name='Test Business',
            business_type=business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True,
            **kwargs
        )
    
    def create_test_category(self, business_profile=None, **kwargs):
        """Create a test category."""
        if business_profile is None:
            business_profile = self.create_test_business_profile()
        
        return Category.objects.create(
            business=business_profile,
            name='Test Category',
            description='Test category description',
            is_active=True,
            **kwargs
        )
    
    def create_test_product(self, business_profile=None, category=None, **kwargs):
        """Create a test product."""
        if business_profile is None:
            business_profile = self.create_test_business_profile()
        if category is None:
            category = self.create_test_category(business_profile)
        
        return Product.objects.create(
            business=business_profile,
            category=category,
            name='Test Product',
            description='Test product description',
            sku='TEST-PROD-001',
            price=19.99,
            quantity=10,
            is_active=True,
            **kwargs
        )
    
    def create_test_service(self, business_profile=None, category=None, **kwargs):
        """Create a test service."""
        if business_profile is None:
            business_profile = self.create_test_business_profile()
        if category is None:
            category = self.create_test_category(business_profile)
        
        return Service.objects.create(
            business=business_profile,
            category=category,
            name='Test Service',
            description='Test service description',
            price=50.00,
            price_type='fixed',
            duration_minutes=60,
            is_appointment_required=True,
            is_active=True,
            **kwargs
        )
    
    def create_test_image_file(self, filename='test.png', content_type='image/png'):
        """Create a test image file."""
        # Create a minimal PNG image
        image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        return SimpleUploadedFile(filename, image_content, content_type=content_type)


class WozapAutoTransactionTestCase(TransactionTestCase):
    """Base transaction test case for WozapAuto."""
    
    def create_test_user(self, username='testuser', email='test@example.com', **kwargs):
        """Create a test user with profile."""
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123',
            **kwargs
        )
        return user
    
    def create_test_business_type(self, name='ecommerce', **kwargs):
        """Create a test business type."""
        return BusinessType.objects.create(
            name=name,
            display_name=f'{name.title()} Store',
            is_active=True,
            **kwargs
        )
    
    def create_test_business_profile(self, user=None, business_type=None, **kwargs):
        """Create a test business profile."""
        if user is None:
            user = self.create_test_user()
        if business_type is None:
            business_type = self.create_test_business_type()
        
        return BusinessProfile.objects.create(
            user=user,
            name='Test Business',
            business_type=business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True,
            **kwargs
        )


class OnboardingTestMixin:
    """Mixin for onboarding-specific test utilities."""
    
    def setup_onboarding_user(self, step='welcome'):
        """Set up a user in a specific onboarding step."""
        user = self.create_test_user()
        profile = user.profile
        profile.onboarding_step = step
        profile.onboarding_completed = False
        profile.save()
        return user, profile
    
    def setup_completed_onboarding_user(self):
        """Set up a user with completed onboarding."""
        user = self.create_test_user()
        profile = user.profile
        profile.onboarding_step = 'complete'
        profile.onboarding_completed = True
        profile.save()
        
        # Create business profile
        business_profile = self.create_test_business_profile(user=user)
        business_profile.is_verified = True
        business_profile.save()
        
        return user, profile, business_profile
    
    def advance_onboarding_step(self, profile, steps=1):
        """Advance onboarding step by specified number of steps."""
        step_order = ['welcome', 'profile', 'business', 'verify', 'complete']
        current_index = step_order.index(profile.onboarding_step)
        new_index = min(current_index + steps, len(step_order) - 1)
        profile.onboarding_step = step_order[new_index]
        
        if profile.onboarding_step == 'complete':
            profile.onboarding_completed = True
        
        profile.save()
        return profile


class BusinessTestMixin:
    """Mixin for business-specific test utilities."""
    
    def setup_business_with_products(self, product_count=3):
        """Set up a business with products."""
        business_profile = self.create_test_business_profile()
        category = self.create_test_category(business_profile)
        
        products = []
        for i in range(product_count):
            product = self.create_test_product(
                business_profile=business_profile,
                category=category,
                name=f'Product {i+1}',
                sku=f'PROD-{i+1:03d}',
                price=10.00 + (i * 5.00)
            )
            products.append(product)
        
        return business_profile, category, products
    
    def setup_business_with_services(self, service_count=2):
        """Set up a business with services."""
        business_profile = self.create_test_business_profile()
        category = self.create_test_category(business_profile)
        
        services = []
        for i in range(service_count):
            service = self.create_test_service(
                business_profile=business_profile,
                category=category,
                name=f'Service {i+1}',
                price=50.00 + (i * 25.00),
                duration_minutes=60 + (i * 30)
            )
            services.append(service)
        
        return business_profile, category, services
    
    def create_otp_for_business(self, business_profile):
        """Create and return OTP for business profile."""
        return business_profile.generate_otp()


class TestDataFactory:
    """Factory class for creating test data."""
    
    @staticmethod
    def create_user_data(**overrides):
        """Create user data for forms."""
        data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'terms_agreement': True,
            'newsletter': False
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_business_data(**overrides):
        """Create business profile data for forms."""
        data = {
            'name': 'Test Business',
            'phone_number': '+1234567890',
            'timezone': 'UTC',
            'language': 'en',
            'currency': 'USD',
            'description': 'Test business description',
            'email': 'business@example.com',
            'website': 'https://example.com',
            'address': '123 Test Street'
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_product_data(**overrides):
        """Create product data for forms."""
        data = {
            'name': 'Test Product',
            'description': 'Test product description',
            'sku': 'TEST-PROD-001',
            'price': '19.99',
            'quantity': '10',
            'is_active': True
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_service_data(**overrides):
        """Create service data for forms."""
        data = {
            'name': 'Test Service',
            'description': 'Test service description',
            'price': '50.00',
            'price_type': 'fixed',
            'duration_minutes': '60',
            'is_appointment_required': True,
            'is_active': True
        }
        data.update(overrides)
        return data
