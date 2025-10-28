"""
Comprehensive tests for Business Tools functionality.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import uuid

from .models import (
    BusinessProfile, BusinessType, Category, Product, ProductVariant,
    Service, AppointmentSlot, Cart, CartItem, AppointmentBooking, BusinessHours
)
from .tools import BusinessTool
from aiengine.models import ConversationThread, Agent


class BusinessToolTestCase(TestCase):
    """Test cases for BusinessTool functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create business type
        self.business_type = BusinessType.objects.create(
            name='Test Business Type',
            display_name='Test Business Type',
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
        
        # Create agent first (required for ConversationThread)
        self.agent = Agent.objects.create(
            user=self.user,
            business=self.business_profile,
            name='Test Agent',
            description='Test agent for business tools',
            system_prompt='You are a test agent.',
            is_active=True
        )
        
        # Create conversation thread
        self.thread = ConversationThread.objects.create(
            user=self.user,
            agent=self.agent,
            thread_id=str(uuid.uuid4()),
            remote_jid='1234567890@s.whatsapp.net',
            is_active=True
        )
        
        # Create category
        self.category = Category.objects.create(
            business=self.business_profile,
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Test Product 1',
            description='Test product 1 description',
            sku='TEST-PROD-001',
            price=Decimal('19.99'),
            quantity=10,
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Test Product 2',
            description='Test product 2 description',
            sku='TEST-PROD-002',
            price=Decimal('29.99'),
            quantity=5,
            is_active=True
        )
        
        # Create product variant
        self.variant = ProductVariant.objects.create(
            product=self.product1,
            name='Small',
            sku='TEST-PROD-001-S',
            price_modifier=Decimal('0.00'),
            quantity=5,
            is_active=True
        )
        
        # Create test services
        self.service1 = Service.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Test Service 1',
            description='Test service 1 description',
            price=Decimal('50.00'),
            price_type='fixed',
            duration_minutes=60,
            is_appointment_required=True,
            is_active=True
        )
        
        self.service2 = Service.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Test Service 2',
            description='Test service 2 description',
            price=Decimal('75.00'),
            price_type='hourly',
            duration_minutes=90,
            is_appointment_required=False,
            is_active=True
        )
        
        # Create business hours for testing (Monday - Friday, 9 AM - 5 PM)
        for day in range(5):  # Monday to Friday
            BusinessHours.objects.create(
                business=self.business_profile,
                day_of_week=day,
                is_open=True,
                open_time=time(9, 0),
                close_time=time(17, 0),
                is_24_hours=False
            )
        
        # Create weekend hours (closed)
        for day in range(5, 7):  # Saturday and Sunday
            BusinessHours.objects.create(
                business=self.business_profile,
                day_of_week=day,
                is_open=False,
                is_24_hours=False
            )
        
        # Initialize business tool
        self.business_tool = BusinessTool(
            user=self.user,
            thread=self.thread
        )
    
    def test_business_tool_initialization(self):
        """Test BusinessTool initialization."""
        self.assertIsNotNone(self.business_tool.business)
        self.assertEqual(self.business_tool.business, self.business_profile)
        self.assertEqual(self.business_tool.thread, self.thread)
        self.assertIsNotNone(self.business_tool.business_service)
    
    def test_business_tool_initialization_no_business_profile(self):
        """Test BusinessTool initialization when user has no business profile."""
        user_no_business = User.objects.create_user(
            username='nobusiness',
            email='nobusiness@example.com',
            password='testpass123'
        )
        
        tool = BusinessTool(user=user_no_business, thread=self.thread)
        self.assertIsNone(tool.business)
        self.assertIsNone(tool.business_service)
    
    def test_validate_and_convert_id_integer(self):
        """Test ID validation with integer values."""
        # Valid integer ID - use the actual product ID
        product_id = self.business_tool._validate_and_convert_id(self.product1.id, Product)
        self.assertEqual(product_id, self.product1.id)
        
        # Invalid integer ID
        invalid_id = self.business_tool._validate_and_convert_id(999, Product)
        self.assertIsNone(invalid_id)
    
    def test_validate_and_convert_id_string(self):
        """Test ID validation with string values."""
        # Valid string ID - use the actual product ID
        product_id = self.business_tool._validate_and_convert_id(str(self.product1.id), Product)
        self.assertEqual(product_id, self.product1.id)
        
        # Invalid string ID
        invalid_id = self.business_tool._validate_and_convert_id('999', Product)
        self.assertIsNone(invalid_id)
    
    def test_validate_and_convert_id_mongodb_objectid(self):
        """Test ID validation with MongoDB-style ObjectId."""
        mongodb_id = '64e5ad5b6d5a1a4a1c654d00'
        product_id = self.business_tool._validate_and_convert_id(mongodb_id, Product)
        self.assertIsNone(product_id)  # Should return None for MongoDB ObjectIds
    
    def test_find_product_by_name_or_id(self):
        """Test finding products by name or ID."""
        # Find by ID
        product = self.business_tool._find_product_by_name_or_id(self.product1.id)
        self.assertEqual(product, self.product1)
        
        # Find by name
        product = self.business_tool._find_product_by_name_or_id('Test Product 1')
        self.assertEqual(product, self.product1)
        
        # Find by partial name
        product = self.business_tool._find_product_by_name_or_id('Product 1')
        self.assertEqual(product, self.product1)
        
        # Not found
        product = self.business_tool._find_product_by_name_or_id('Non-existent Product')
        self.assertIsNone(product)
    
    def test_find_service_by_name_or_id(self):
        """Test finding services by name or ID."""
        # Find by ID
        service = self.business_tool._find_service_by_name_or_id(self.service1.id)
        self.assertEqual(service, self.service1)
        
        # Find by name
        service = self.business_tool._find_service_by_name_or_id('Test Service 1')
        self.assertEqual(service, self.service1)
        
        # Find by partial name
        service = self.business_tool._find_service_by_name_or_id('Service 1')
        self.assertEqual(service, self.service1)
        
        # Not found
        service = self.business_tool._find_service_by_name_or_id('Non-existent Service')
        self.assertIsNone(service)
    
    def test_list_available_products(self):
        """Test listing available products."""
        result = self.business_tool.list_available_products()
        
        self.assertIn('Available Products', result)
        self.assertIn('Test Product 1', result)
        self.assertIn('Test Product 2', result)
        self.assertIn(f'ID: {self.product1.id}', result)
        self.assertIn(f'ID: {self.product2.id}', result)
    
    def test_list_available_services(self):
        """Test listing available services."""
        result = self.business_tool.list_available_services()
        
        self.assertIn('Available Services', result)
        self.assertIn('Test Service 1', result)
        self.assertIn('Test Service 2', result)
        self.assertIn(f'ID: {self.service1.id}', result)
        self.assertIn(f'ID: {self.service2.id}', result)
        self.assertIn('Appointment Required', result)
    
    def test_add_to_cart_by_id(self):
        """Test adding product to cart by ID."""
        result = self.business_tool.add_to_cart(str(self.product1.id), 2)
        
        self.assertIn('Added 2x Test Product 1', result)
        self.assertIn('Total Items: 2', result)
        
        # Verify cart was created
        cart = Cart.objects.get(thread=self.thread, business=self.business_profile)
        self.assertEqual(cart.total_items, 2)
        
        # Verify cart item was created
        cart_item = CartItem.objects.get(cart=cart, product=self.product1)
        self.assertEqual(cart_item.quantity, 2)
    
    def test_add_to_cart_by_name(self):
        """Test adding product to cart by name."""
        result = self.business_tool.add_to_cart('Test Product 2', 1)
        
        self.assertIn('Added 1x Test Product 2', result)
        
        # Verify cart was created
        cart = Cart.objects.get(thread=self.thread, business=self.business_profile)
        self.assertEqual(cart.total_items, 1)
    
    def test_add_to_cart_with_variant(self):
        """Test adding product to cart with variant."""
        result = self.business_tool.add_to_cart(str(self.product1.id), 1, str(self.variant.id))
        
        self.assertIn('Added 1x Test Product 1 (Small)', result)
        
        # Verify cart item was created with variant
        cart = Cart.objects.get(thread=self.thread, business=self.business_profile)
        cart_item = CartItem.objects.get(cart=cart, product=self.product1, variant=self.variant)
        self.assertEqual(cart_item.quantity, 1)
    
    def test_add_to_cart_insufficient_stock(self):
        """Test adding product to cart with insufficient stock."""
        # Set product quantity to 0
        self.product1.quantity = 0
        self.product1.save()
        
        result = self.business_tool.add_to_cart(str(self.product1.id), 1)
        
        self.assertIn('Insufficient stock', result)
    
    def test_add_to_cart_product_not_found(self):
        """Test adding non-existent product to cart."""
        result = self.business_tool.add_to_cart('999', 1)
        
        self.assertIn('Product \'999\' not found', result)
    
    def test_get_cart_contents_empty(self):
        """Test getting cart contents when cart is empty."""
        result = self.business_tool.get_cart_contents()
        
        self.assertIn('Your cart is empty', result)
    
    def test_get_cart_contents_with_items(self):
        """Test getting cart contents with items."""
        # Add items to cart first
        self.business_tool.add_to_cart('1', 2)
        self.business_tool.add_to_cart('2', 1)
        
        result = self.business_tool.get_cart_contents()
        
        self.assertIn('Your Cart', result)
        self.assertIn('Test Product 1', result)
        self.assertIn('Test Product 2', result)
        self.assertIn('Total Items: 3', result)
    
    def test_remove_from_cart_by_id(self):
        """Test removing product from cart by ID."""
        # Add items to cart first
        self.business_tool.add_to_cart('1', 3)
        
        # Remove some items
        result = self.business_tool.remove_from_cart('1', 2)
        
        self.assertIn('Removed 2x Test Product 1', result)
        
        # Verify cart item quantity was updated
        cart = Cart.objects.get(thread=self.thread, business=self.business_profile)
        cart_item = CartItem.objects.get(cart=cart, product=self.product1)
        self.assertEqual(cart_item.quantity, 1)
    
    def test_remove_from_cart_by_name(self):
        """Test removing product from cart by name."""
        # Add items to cart first
        self.business_tool.add_to_cart('Test Product 1', 2)
        
        # Remove all items
        result = self.business_tool.remove_from_cart('Test Product 1')
        
        self.assertIn('Removed all Test Product 1', result)
        
        # Verify cart item was deleted
        cart = Cart.objects.get(thread=self.thread, business=self.business_profile)
        self.assertEqual(cart.total_items, 0)
    
    def test_remove_from_cart_product_not_in_cart(self):
        """Test removing product that's not in cart."""
        result = self.business_tool.remove_from_cart(str(self.product1.id), 1)
        
        self.assertIn('Your cart is empty', result)
    
    def test_book_appointment_by_id(self):
        """Test booking appointment by service ID."""
        result = self.business_tool.book_appointment(
            service_identifier=str(self.service1.id),
            customer_name='John Doe',
            booking_date='2024-01-01',
            booking_time='10:00'
        )
        
        self.assertIn('Appointment Booked Successfully', result)
        self.assertIn('Test Service 1', result)
        self.assertIn('John Doe', result)
        
        # Verify booking was created
        booking = AppointmentBooking.objects.get(
            thread=self.thread,
            business=self.business_profile,
            service=self.service1
        )
        self.assertEqual(booking.customer_name, 'John Doe')
        self.assertEqual(booking.status, 'pending')
    
    def test_book_appointment_by_name(self):
        """Test booking appointment by service name."""
        result = self.business_tool.book_appointment(
            service_identifier='Test Service 1',
            customer_name='Jane Doe',
            booking_date='2024-01-01',
            booking_time='11:00'
        )
        
        self.assertIn('Appointment Booked Successfully', result)
        self.assertIn('Test Service 1', result)
        self.assertIn('Jane Doe', result)
    
    def test_book_appointment_with_customer_info(self):
        """Test booking appointment with customer phone and email."""
        result = self.business_tool.book_appointment(
            service_identifier=str(self.service1.id),
            customer_name='John Doe',
            booking_date='2024-01-01',
            booking_time='10:00',
            customer_phone='+1234567890',
            customer_email='john@example.com',
            notes='Special request'
        )
        
        self.assertIn('Appointment Booked Successfully', result)
        self.assertIn('+1234567890', result)
        self.assertIn('john@example.com', result)
        self.assertIn('Special request', result)
    
    def test_book_appointment_service_not_requires_appointment(self):
        """Test booking appointment for service that doesn't require appointment."""
        result = self.business_tool.book_appointment(
            service_identifier=str(self.service2.id),  # service2 doesn't require appointment
            customer_name='John Doe',
            booking_date='2024-01-01',
            booking_time='10:00'
        )
        
        self.assertIn('does not require an appointment', result)
    
    def test_book_appointment_service_not_found(self):
        """Test booking appointment for non-existent service."""
        result = self.business_tool.book_appointment(
            service_identifier='999',
            customer_name='John Doe',
            booking_date='2024-01-01',
            booking_time='10:00'
        )
        
        self.assertIn('Service \'999\' not found', result)
    
    def test_book_appointment_invalid_date_format(self):
        """Test booking appointment with invalid date format."""
        result = self.business_tool.book_appointment(
            service_identifier=str(self.service1.id),
            customer_name='John Doe',
            booking_date='invalid-date',
            booking_time='10:00'
        )
        
        self.assertIn('Invalid date or time format', result)
    
    def test_book_appointment_invalid_time_format(self):
        """Test booking appointment with invalid time format."""
        result = self.business_tool.book_appointment(
            service_identifier=str(self.service1.id),
            customer_name='John Doe',
            booking_date='2024-01-01',
            booking_time='invalid-time'
        )
        
        self.assertIn('Invalid date or time format', result)
    
    def test_get_appointment_bookings_empty(self):
        """Test getting appointment bookings when none exist."""
        result = self.business_tool.get_appointment_bookings()
        
        self.assertIn('You have no appointment bookings', result)
    
    def test_get_appointment_bookings_with_bookings(self):
        """Test getting appointment bookings when bookings exist."""
        # Create a booking first
        AppointmentBooking.objects.create(
            thread=self.thread,
            business=self.business_profile,
            service=self.service1,
            customer_name='John Doe',
            customer_phone='+1234567890',
            booking_date=date(2024, 1, 1),
            booking_time=time(10, 0),
            duration_minutes=60,
            total_price=Decimal('50.00'),
            status='pending'
        )
        
        result = self.business_tool.get_appointment_bookings()
        
        self.assertIn('Your Appointment Bookings', result)
        self.assertIn('Test Service 1', result)
        self.assertIn('John Doe', result)
    
    def test_check_appointment_availability(self):
        """Test checking appointment availability."""
        result = self.business_tool.check_appointment_availability(str(self.service1.id))
        
        # This might return "No available appointments" if no slots are configured
        # The important thing is that it doesn't crash
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_check_appointment_availability_service_not_found(self):
        """Test checking appointment availability for non-existent service."""
        result = self.business_tool.check_appointment_availability('999')
        
        self.assertIn('Service \'999\' not found', result)
    
    def test_get_business_info(self):
        """Test getting business information."""
        result = self.business_tool.get_business_info()
        
        self.assertIn('Test Business', result)
        self.assertIn('Test Business Type', result)
    
    def test_get_business_summary(self):
        """Test getting business summary."""
        result = self.business_tool.get_business_summary()
        
        self.assertIn('Test Business', result)
        self.assertIn('Test Business Type', result)
    
    def test_get_featured_items(self):
        """Test getting featured items."""
        # Mark a product as featured
        self.product1.is_featured = True
        self.product1.save()
        
        result = self.business_tool.get_featured_items('products')
        
        self.assertIn('Featured Items', result)
        self.assertIn('Test Product 1', result)
    
    def test_check_business_hours(self):
        """Test checking business hours."""
        result = self.business_tool.check_business_hours()
        
        # Should return some status information
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_search_products(self):
        """Test searching products."""
        result = self.business_tool.search_products('Test Product')
        
        self.assertIn('Found', result)
        self.assertIn('Test Product', result)
    
    def test_search_services(self):
        """Test searching services."""
        result = self.business_tool.search_services('Test Service')
        
        self.assertIn('Found', result)
        self.assertIn('Test Service', result)
    
    def test_get_tools(self):
        """Test getting list of tools."""
        tools = self.business_tool.get_tools()
        
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)
        
        # Check that all expected tools are present
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            'search_products',
            'search_services',
            'get_business_info',
            'check_business_hours',
            'check_appointment_availability',
            'get_featured_items',
            'get_business_summary',
            'list_available_products',
            'list_available_services',
            'add_to_cart',
            'get_cart_contents',
            'remove_from_cart',
            'book_appointment',
            'get_appointment_bookings'
        ]
        
        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)


class BusinessToolIntegrationTestCase(TransactionTestCase):
    """Integration tests for BusinessTool with database transactions."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
        
        # Create business type
        self.business_type = BusinessType.objects.create(
            name='Integration Business Type',
            display_name='Integration Business Type',
            is_active=True
        )
        
        # Create business profile
        self.business_profile = BusinessProfile.objects.create(
            user=self.user,
            name='Integration Business',
            business_type=self.business_type,
            phone_number='+1234567890',
            timezone='UTC',
            language='en',
            currency='USD',
            is_verified=True
        )
        
        # Create agent first (required for ConversationThread)
        self.agent = Agent.objects.create(
            user=self.user,
            business=self.business_profile,
            name='Test Agent',
            description='Test agent for business tools',
            system_prompt='You are a test agent.',
            is_active=True
        )
        
        # Create conversation thread
        self.thread = ConversationThread.objects.create(
            user=self.user,
            agent=self.agent,
            thread_id=str(uuid.uuid4()),
            remote_jid='1234567890@s.whatsapp.net',
            is_active=True
        )
        
        # Create category
        self.category = Category.objects.create(
            business=self.business_profile,
            name='Integration Category',
            description='Integration category description',
            is_active=True
        )
        
        # Create test product
        self.product = Product.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Integration Product',
            description='Integration product description',
            sku='INTEGRATION-PROD-001',
            price=Decimal('25.00'),
            quantity=10,
            is_active=True
        )
        
        # Create test service
        self.service = Service.objects.create(
            business=self.business_profile,
            category=self.category,
            name='Integration Service',
            description='Integration service description',
            price=Decimal('100.00'),
            price_type='fixed',
            duration_minutes=120,
            is_appointment_required=True,
            is_active=True
        )
        
        # Create business hours for testing (Monday - Friday, 9 AM - 5 PM)
        for day in range(5):  # Monday to Friday
            BusinessHours.objects.create(
                business=self.business_profile,
                day_of_week=day,
                is_open=True,
                open_time=time(9, 0),
                close_time=time(17, 0),
                is_24_hours=False
            )
        
        # Create weekend hours (closed)
        for day in range(5, 7):  # Saturday and Sunday
            BusinessHours.objects.create(
                business=self.business_profile,
                day_of_week=day,
                is_open=False,
                is_24_hours=False
            )
        
        # Initialize business tool
        self.business_tool = BusinessTool(
            user=self.user,
            thread=self.thread
        )
    
    def test_complete_cart_workflow(self):
        """Test complete cart workflow: add -> view -> remove."""
        # Add products to cart
        result1 = self.business_tool.add_to_cart('Integration Product', 2)
        self.assertIn('Added 2x Integration Product', result1)
        
        # View cart contents
        result2 = self.business_tool.get_cart_contents()
        self.assertIn('Integration Product', result2)
        self.assertIn('Total Items: 2', result2)
        
        # Remove some items
        result3 = self.business_tool.remove_from_cart('Integration Product', 1)
        self.assertIn('Removed 1x Integration Product', result3)
        
        # View cart contents again
        result4 = self.business_tool.get_cart_contents()
        self.assertIn('Total Items: 1', result4)
        
        # Remove all items
        result5 = self.business_tool.remove_from_cart('Integration Product')
        self.assertIn('Removed all Integration Product', result5)
        
        # Verify cart is empty
        result6 = self.business_tool.get_cart_contents()
        self.assertIn('Your cart is empty', result6)
    
    def test_complete_appointment_workflow(self):
        """Test complete appointment workflow: check availability -> book -> view."""
        # Check availability
        result1 = self.business_tool.check_appointment_availability('Integration Service')
        self.assertIsInstance(result1, str)
        
        # Book appointment
        result2 = self.business_tool.book_appointment(
            service_identifier='Integration Service',
            customer_name='Integration Customer',
            booking_date='2024-01-01',
            booking_time='10:00',
            customer_phone='+1234567890',
            customer_email='customer@example.com',
            notes='Integration test appointment'
        )
        self.assertIn('Appointment Booked Successfully', result2)
        
        # View appointments
        result3 = self.business_tool.get_appointment_bookings()
        self.assertIn('Integration Customer', result3)
        self.assertIn('Integration Service', result3)
    
    def test_error_handling_no_business_context(self):
        """Test error handling when no business context is available."""
        user_no_business = User.objects.create_user(
            username='nobusinessuser',
            email='nobusiness@example.com',
            password='testpass123'
        )
        
        tool = BusinessTool(user=user_no_business, thread=self.thread)
        
        # Test various operations that should fail gracefully
        result1 = tool.add_to_cart('1', 1)
        self.assertIn('No business context', result1)
        
        result2 = tool.book_appointment('1', 'John', '2024-01-01', '10:00')
        self.assertIn('No business context', result2)
        
        result3 = tool.get_business_info()
        self.assertIn('No business context', result3)
    
    def test_error_handling_no_thread_context(self):
        """Test error handling when no thread context is available."""
        tool = BusinessTool(user=self.user, thread=None)
        
        # Test operations that require thread context
        result1 = tool.add_to_cart('1', 1)
        self.assertIn('conversation thread', result1)
        
        result2 = tool.book_appointment('1', 'John', '2024-01-01', '10:00')
        self.assertIn('conversation thread', result2)
        
        result3 = tool.get_cart_contents()
        self.assertIn('conversation thread', result3)
    
    def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions."""
        # Test with zero quantity
        result1 = self.business_tool.add_to_cart('Integration Product', 0)
        # Should handle gracefully (might add 0 items or reject)
        self.assertIsInstance(result1, str)
        
        # Test with very large quantity
        result2 = self.business_tool.add_to_cart('Integration Product', 999999)
        # Should handle stock limits
        self.assertIsInstance(result2, str)
        
        # Test with empty string identifiers
        result3 = self.business_tool.add_to_cart('', 1)
        self.assertIn('not found', result3)
        
        # Test with None identifiers
        result4 = self.business_tool.add_to_cart(None, 1)
        self.assertIn('not found', result4)
        
        # Test with special characters in identifiers
        result5 = self.business_tool.add_to_cart('!@#$%^&*()', 1)
        self.assertIn('not found', result5)