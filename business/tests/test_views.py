"""
Tests for business views and API endpoints.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from business.models import BusinessProfile, BusinessType, Category, Product, Service, Cart, AppointmentBooking
from core.models import UserProfile


class BusinessViewTestCase(TestCase):
    """Test cases for business views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        
        # Create business type
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
        
        # Create business profile
        self.business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True
        )
        
        # Create category
        self.category = Category.objects.create(
            business=self.business_profile,
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        
        # Create products
        self.product = Product.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Test Product',
            description='Test product description',
            sku='TEST-PROD-001',
            price=Decimal('19.99'),
            quantity=10,
            is_active=True
        )
        
        # Create services
        self.service = Service.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Test Service',
            description='Test service description',
            price=Decimal('50.00'),
            price_type='fixed',
            duration_minutes=60,
            is_appointment_required=True,
            is_active=True
        )
    
    def test_business_dashboard_get(self):
        """Test business dashboard GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Business')
    
    def test_business_dashboard_unauthenticated(self):
        """Test business dashboard for unauthenticated user."""
        response = self.client.get(reverse('business_dashboard'))
        self.assertRedirects(response, f"{reverse('signin')}?next={reverse('business_dashboard')}")
    
    def test_business_dashboard_no_business_profile(self):
        """Test business dashboard for user without business profile."""
        # Delete business profile
        self.business_profile.delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_dashboard'))
        self.assertRedirects(response, reverse('onboarding_business'))
    
    def test_products_list_get(self):
        """Test products list GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_products'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
    
    def test_products_create_get(self):
        """Test product creation GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_product_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Product')
    
    def test_products_create_post_valid(self):
        """Test product creation POST with valid data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'New Product',
            'category': self.category.id,
            'description': 'New product description',
            'sku': 'NEW-PROD-001',
            'price': '29.99',
            'quantity': '5',
            'is_active': True
        }
        
        response = self.client.post(reverse('business_product_create'), form_data)
        self.assertRedirects(response, reverse('business_products'))
        
        # Verify product was created
        product = Product.objects.get(sku='NEW-PROD-001')
        self.assertEqual(product.name, 'New Product')
        self.assertEqual(product.business, self.business_profile)
    
    def test_services_list_get(self):
        """Test services list GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_services'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Service')
    
    def test_services_create_get(self):
        """Test service creation GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_service_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Service')
    
    def test_services_create_post_valid(self):
        """Test service creation POST with valid data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'New Service',
            'category': self.category.id,
            'description': 'New service description',
            'price': '75.00',
            'price_type': 'hourly',
            'duration_minutes': '90',
            'is_appointment_required': True,
            'is_active': True
        }
        
        response = self.client.post(reverse('business_service_create'), form_data)
        self.assertRedirects(response, reverse('business_services'))
        
        # Verify service was created
        service = Service.objects.get(name='New Service')
        self.assertEqual(service.business, self.business_profile)
        self.assertEqual(service.price_type, 'hourly')
    
    def test_categories_list_get(self):
        """Test categories list GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_categories'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Category')
    
    def test_categories_create_get(self):
        """Test category creation GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_category_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Category')
    
    def test_categories_create_post_valid(self):
        """Test category creation POST with valid data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'New Category',
            'description': 'New category description',
            'is_active': True
        }
        
        response = self.client.post(reverse('business_category_create'), form_data)
        self.assertRedirects(response, reverse('business_categories'))
        
        # Verify category was created
        category = Category.objects.get(name='New Category')
        self.assertEqual(category.business, self.business_profile)
    
    def test_appointments_list_get(self):
        """Test appointments list GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_appointments'))
        self.assertEqual(response.status_code, 200)
    
    def test_appointments_create_get(self):
        """Test appointment creation GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_appointment_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Appointment')
    
    def test_business_settings_get(self):
        """Test business settings GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Business Settings')
    
    def test_business_settings_post_valid(self):
        """Test business settings POST with valid data."""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'Updated Business Name',
            'description': 'Updated business description',
            'email': 'updated@example.com',
            'website': 'https://updated.com',
            'address': '456 Updated Street'
        }
        
        response = self.client.post(reverse('business_settings'), form_data)
        self.assertRedirects(response, reverse('business_settings'))
        
        # Verify business profile was updated
        self.business_profile.refresh_from_db()
        self.assertEqual(self.business_profile.name, 'Updated Business Name')
        self.assertEqual(self.business_profile.email, 'updated@example.com')


class BusinessAPITestCase(TestCase):
    """Test cases for business API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create business type
        self.business_type = BusinessType.objects.create(
            name='ecommerce',
            display_name='E-commerce Store',
            is_active=True
        )
        
        # Create business profile
        self.business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Test Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True
        )
    
    def test_business_api_get(self):
        """Test business API GET request."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['name'], 'Test Business')
        self.assertEqual(data['phone_number'], '+1234567890')
    
    def test_business_api_post(self):
        """Test business API POST request."""
        self.client.login(username='testuser', password='testpass123')
        
        api_data = {
            'name': 'Updated Business',
            'description': 'Updated description'
        }
        
        response = self.client.post(reverse('business_api'), api_data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # Verify business profile was updated
        self.business_profile.refresh_from_db()
        self.assertEqual(self.business_profile.name, 'Updated Business')
    
    def test_business_api_unauthenticated(self):
        """Test business API for unauthenticated user."""
        response = self.client.get(reverse('business_api'))
        self.assertEqual(response.status_code, 401)
    
    def test_business_api_no_business_profile(self):
        """Test business API for user without business profile."""
        # Delete business profile
        self.business_profile.delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_api'))
        self.assertEqual(response.status_code, 404)
    
    def test_business_stats_api(self):
        """Test business stats API endpoint."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('business_stats_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('total_products', data)
        self.assertIn('total_services', data)
        self.assertIn('total_categories', data)
        self.assertIn('total_appointments', data)
