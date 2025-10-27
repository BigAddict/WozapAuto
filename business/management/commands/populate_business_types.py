"""
Django management command to populate business types.
"""
from django.core.management.base import BaseCommand
from business.models import BusinessType


class Command(BaseCommand):
    help = 'Populate business types for the system'

    def handle(self, *args, **options):
        self.stdout.write('Populating business types...')
        
        business_types = [
            {
                'name': 'ecommerce',
                'display_name': 'E-commerce Store',
                'description': 'Online retail stores selling physical or digital products',
                'icon': '🛒'
            },
            {
                'name': 'restaurant',
                'display_name': 'Restaurant/Food Service',
                'description': 'Food service businesses including restaurants, cafes, and food delivery',
                'icon': '🍽️'
            },
            {
                'name': 'retail',
                'display_name': 'Retail Store',
                'description': 'Physical retail stores selling products to customers',
                'icon': '🏪'
            },
            {
                'name': 'service',
                'display_name': 'Professional Services',
                'description': 'Businesses providing professional services like consulting, legal, accounting',
                'icon': '💼'
            },
            {
                'name': 'appointment',
                'display_name': 'Appointment Booking',
                'description': 'Businesses that require appointment scheduling like salons, clinics, consultants',
                'icon': '📅'
            },
            {
                'name': 'subscription',
                'display_name': 'Subscription Service',
                'description': 'Businesses offering recurring subscription services',
                'icon': '🔄'
            },
            {
                'name': 'marketplace',
                'display_name': 'Marketplace',
                'description': 'Platforms connecting buyers and sellers',
                'icon': '🏬'
            },
            {
                'name': 'consultation',
                'display_name': 'Consultation Services',
                'description': 'Businesses offering consultation and advisory services',
                'icon': '💡'
            },
            {
                'name': 'education',
                'display_name': 'Education/Training',
                'description': 'Educational institutions and training providers',
                'icon': '🎓'
            },
            {
                'name': 'healthcare',
                'display_name': 'Healthcare Services',
                'description': 'Medical and healthcare service providers',
                'icon': '🏥'
            },
            {
                'name': 'beauty',
                'display_name': 'Beauty & Wellness',
                'description': 'Beauty salons, spas, wellness centers, and fitness studios',
                'icon': '💄'
            },
            {
                'name': 'automotive',
                'display_name': 'Automotive Services',
                'description': 'Auto repair shops, car dealerships, and automotive services',
                'icon': '🚗'
            },
            {
                'name': 'real_estate',
                'display_name': 'Real Estate',
                'description': 'Real estate agencies, property management, and real estate services',
                'icon': '🏠'
            },
            {
                'name': 'travel',
                'display_name': 'Travel & Tourism',
                'description': 'Travel agencies, tour operators, and tourism services',
                'icon': '✈️'
            },
            {
                'name': 'entertainment',
                'display_name': 'Entertainment',
                'description': 'Entertainment venues, event organizers, and entertainment services',
                'icon': '🎭'
            },
            {
                'name': 'fitness',
                'display_name': 'Fitness & Sports',
                'description': 'Gyms, sports clubs, personal trainers, and fitness services',
                'icon': '💪'
            },
            {
                'name': 'logistics',
                'display_name': 'Logistics & Delivery',
                'description': 'Delivery services, logistics companies, and shipping services',
                'icon': '📦'
            },
            {
                'name': 'financial',
                'display_name': 'Financial Services',
                'description': 'Banks, financial advisors, insurance, and financial services',
                'icon': '💰'
            },
            {
                'name': 'other',
                'display_name': 'Other',
                'description': 'Other business types not covered above',
                'icon': '🔧'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for bt_data in business_types:
            business_type, created = BusinessType.objects.get_or_create(
                name=bt_data['name'],
                defaults={
                    'display_name': bt_data['display_name'],
                    'description': bt_data['description'],
                    'icon': bt_data['icon']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {business_type.display_name}')
                )
            else:
                # Update existing if needed
                updated = False
                if business_type.display_name != bt_data['display_name']:
                    business_type.display_name = bt_data['display_name']
                    updated = True
                if business_type.description != bt_data['description']:
                    business_type.description = bt_data['description']
                    updated = True
                if business_type.icon != bt_data['icon']:
                    business_type.icon = bt_data['icon']
                    updated = True
                
                if updated:
                    business_type.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated: {business_type.display_name}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nBusiness types populated successfully!\n'
                f'Created: {created_count}\n'
                f'Updated: {updated_count}\n'
                f'Total: {BusinessType.objects.count()}'
            )
        )
