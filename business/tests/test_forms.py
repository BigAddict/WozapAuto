"""
Tests for business forms and validation.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from business.models import BusinessProfile, BusinessType, Category, Product, Service
from business.forms import BusinessProfileForm


class BusinessFormTestCase(TestCase):
    """Test cases for business forms."""
    
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
        # Test missing country code
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
    
    def test_business_profile_form_required_fields(self):
        """Test BusinessProfileForm required fields."""
        form_data = {
            'name': 'Test Business',
            # Missing required fields
        }
        
        form = BusinessProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        
        required_fields = ['business_type', 'phone_number', 'timezone', 'language', 'currency']
        for field in required_fields:
            self.assertIn(field, form.errors)
    
    def test_business_profile_form_fields_present(self):
        """Test that all expected fields are present in the form."""
        form = BusinessProfileForm()
        expected_fields = [
            'name', 'business_type', 'phone_number', 'timezone', 'language', 
            'currency', 'description', 'email', 'website', 'address'
        ]
        
        for field in expected_fields:
            self.assertIn(field, form.fields)
    
    def test_business_profile_form_widgets(self):
        """Test form widgets are correctly configured."""
        form = BusinessProfileForm()
        
        # Test text input widgets
        text_fields = ['name', 'email', 'website', 'address']
        for field in text_fields:
            self.assertEqual(form.fields[field].widget.attrs['class'], 'form-control')
        
        # Test select widgets
        select_fields = ['business_type', 'timezone', 'language', 'currency']
        for field in select_fields:
            self.assertEqual(form.fields[field].widget.attrs['class'], 'form-control')
        
        # Test textarea widget
        self.assertEqual(form.fields['description'].widget.attrs['class'], 'form-control')
        self.assertEqual(form.fields['description'].widget.attrs['rows'], 3)
