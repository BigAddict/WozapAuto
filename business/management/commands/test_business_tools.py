"""
Management command to test business tools functionality.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from business.tools import BusinessTool
from business.models import BusinessProfile, BusinessType
from business.services import BusinessService
import json


class Command(BaseCommand):
    help = 'Test business tools functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username to test with (default: first superuser)',
        )
        parser.add_argument(
            '--business-id',
            type=str,
            help='Business ID to test with (default: first business)',
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='Run all tests',
        )

    def handle(self, *args, **options):
        # Get test user
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                raise CommandError(f"User '{options['user']}' does not exist")
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError("No superuser found. Create one first.")

        # Get test business
        business_id = options.get('business_id')
        if business_id:
            try:
                business = BusinessProfile.objects.get(id=business_id)
            except BusinessProfile.DoesNotExist:
                raise CommandError(f"Business with ID '{business_id}' does not exist")
        else:
            business = BusinessProfile.objects.first()
            if not business:
                self.stdout.write(
                    self.style.WARNING("No business profiles found. Creating a test business...")
                )
                business = self.create_test_business(user)

        self.stdout.write(f"Testing with user: {user.username}")
        self.stdout.write(f"Testing with business: {business.name} ({business.id})")

        # Initialize business tool
        business_tool = BusinessTool(user=user, business_id=str(business.id))

        if options['test_all']:
            self.run_all_tests(business_tool)
        else:
            self.run_basic_tests(business_tool)

    def create_test_business(self, user):
        """Create a test business profile."""
        # Get or create business type
        business_type, created = BusinessType.objects.get_or_create(
            name="Retail Store",
            defaults={'description': 'General retail business'}
        )

        # Create test business
        business = BusinessProfile.objects.create(
            user=user,
            name="Test Business",
            business_type=business_type,
            description="A test business for tool testing",
            phone="+1234567890",
            email="test@example.com",
            timezone="America/New_York"
        )

        self.stdout.write(
            self.style.SUCCESS(f"Created test business: {business.name}")
        )
        return business

    def run_basic_tests(self, business_tool):
        """Run basic tool tests."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("RUNNING BASIC BUSINESS TOOL TESTS")
        self.stdout.write("="*50)

        # Test 1: Get business info
        self.stdout.write("\n1. Testing get_business_info...")
        try:
            result = business_tool.get_business_info()
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ get_business_info test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ get_business_info test failed: {e}"))

        # Test 2: Check business hours
        self.stdout.write("\n2. Testing check_business_hours...")
        try:
            result = business_tool.check_business_hours()
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ check_business_hours test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ check_business_hours test failed: {e}"))

        # Test 3: Get business summary
        self.stdout.write("\n3. Testing get_business_summary...")
        try:
            result = business_tool.get_business_summary()
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ get_business_summary test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ get_business_summary test failed: {e}"))

    def run_all_tests(self, business_tool):
        """Run comprehensive tool tests."""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("RUNNING COMPREHENSIVE BUSINESS TOOL TESTS")
        self.stdout.write("="*50)

        # Test all basic functionality
        self.run_basic_tests(business_tool)

        # Test product search
        self.stdout.write("\n4. Testing search_products...")
        try:
            result = business_tool.search_products("test")
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ search_products test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ search_products test failed: {e}"))

        # Test service search
        self.stdout.write("\n5. Testing search_services...")
        try:
            result = business_tool.search_services("test")
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ search_services test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ search_services test failed: {e}"))

        # Test featured items
        self.stdout.write("\n6. Testing get_featured_items...")
        try:
            result = business_tool.get_featured_items()
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ get_featured_items test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ get_featured_items test failed: {e}"))

        # Test appointment availability
        self.stdout.write("\n7. Testing check_appointment_availability...")
        try:
            result = business_tool.check_appointment_availability("1")
            self.stdout.write(f"Result: {result[:200]}...")
            self.stdout.write(self.style.SUCCESS("✓ check_appointment_availability test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ check_appointment_availability test failed: {e}"))

        # Test tool list
        self.stdout.write("\n8. Testing get_tools...")
        try:
            tools = business_tool.get_tools()
            self.stdout.write(f"Found {len(tools)} tools")
            for i, tool in enumerate(tools, 1):
                self.stdout.write(f"  {i}. {tool.name}")
            self.stdout.write(self.style.SUCCESS("✓ get_tools test passed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ get_tools test failed: {e}"))

        self.stdout.write("\n" + "="*50)
        self.stdout.write("ALL TESTS COMPLETED")
        self.stdout.write("="*50)
