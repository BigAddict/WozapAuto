"""
Business services for WhatsApp bot integration.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta, time

from .models import (
    BusinessProfile, Product, Service, Category, BusinessHours, 
    BusinessLocation, AppointmentSlot, BusinessSettings, AppointmentBooking
)

logger = logging.getLogger("business.services")


def add_minutes_to_time(time_obj: time, minutes: int) -> time:
    """Add minutes to a time object and return a new time object."""
    if not isinstance(time_obj, time):
        return time_obj
    
    # Convert to datetime for calculation
    dt = datetime.combine(datetime.today(), time_obj)
    new_dt = dt + timedelta(minutes=minutes)
    return new_dt.time()


def subtract_minutes_from_time(time_obj: time, minutes: int) -> time:
    """Subtract minutes from a time object and return a new time object."""
    if not isinstance(time_obj, time):
        return time_obj
    
    # Convert to datetime for calculation
    dt = datetime.combine(datetime.today(), time_obj)
    new_dt = dt - timedelta(minutes=minutes)
    return new_dt.time()


def time_to_minutes(time_obj: time) -> int:
    """Convert time object to total minutes since midnight."""
    if not isinstance(time_obj, time):
        return 0
    return time_obj.hour * 60 + time_obj.minute


def minutes_to_time(minutes: int) -> time:
    """Convert total minutes since midnight to time object."""
    hours = minutes // 60
    mins = minutes % 60
    return time(hours, mins)


class BusinessService:
    """Service class for business operations and WhatsApp bot integration"""
    
    def __init__(self, business_id: str = None):
        self.business_id = business_id
        self.business = None
        if business_id:
            try:
                self.business = BusinessProfile.objects.select_related('business_type').get(id=business_id)
            except BusinessProfile.DoesNotExist:
                logger.error(f"Business with ID {business_id} not found")
    
    def get_business_info(self) -> Dict[str, Any]:
        """Get comprehensive business information for WhatsApp bot"""
        if not self.business:
            return {}
        
        # Get business hours
        business_hours = self.business.business_hours.all().order_by('day_of_week')
        hours_dict = {}
        for hour in business_hours:
            day_name = hour.get_day_of_week_display()
            if hour.is_24_hours:
                hours_dict[day_name] = "24 Hours"
            elif hour.is_open:
                hours_dict[day_name] = f"{hour.open_time} - {hour.close_time}"
            else:
                hours_dict[day_name] = "Closed"
        
        # Get locations
        locations = self.business.locations.filter(is_active=True)
        locations_data = []
        for location in locations:
            locations_data.append({
                'name': location.name,
                'address': location.address,
                'city': location.city,
                'phone': location.phone,
                'is_primary': location.is_primary
            })
        
        # Get settings
        settings = getattr(self.business, 'settings', None)
        
        return {
            'id': str(self.business.id),
            'name': self.business.name,
            'description': self.business.description,
            'business_type': self.business.business_type.display_name,
            'contact': {
                'phone': self.business.phone_number,
                'email': self.business.email,
                'website': self.business.website,
                'whatsapp': self.business.phone_number  # Use phone_number field for WhatsApp
            },
            'address': self.business.address,
            'business_hours': hours_dict,
            'locations': locations_data,
            'settings': {
                'welcome_message': settings.welcome_message if settings else None,
                'auto_reply_message': settings.auto_reply_message if settings else None,
                'business_hours_message': settings.business_hours_message if settings else None,
                'currency': self.business.currency,
                'language': self.business.language
            } if settings else None,
            'bot_active': self.business.bot_active
        }
    
    def search_products(self, query: str, category_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search products for WhatsApp bot responses"""
        if not self.business:
            return []
        
        products = Product.objects.filter(
            business=self.business,
            is_active=True
        ).select_related('category', 'business')
        
        if category_id:
            products = products.filter(category_id=category_id)
        
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(short_description__icontains=query) |
                Q(sku__icontains=query)
            )
        
        products = products[:limit]
        
        results = []
        for product in products:
            # Get primary image
            primary_image = None
            if product.primary_image:
                primary_image = product.primary_image.url
            
            # Check stock status
            stock_status = "In Stock"
            if product.track_inventory:
                if product.quantity <= 0:
                    stock_status = "Out of Stock"
                elif product.is_low_stock:
                    stock_status = f"Low Stock ({product.quantity} left)"
            
            results.append({
                'id': str(product.id),
                'name': product.name,
                'description': product.short_description or product.description,
                'price': float(product.price),
                'currency': self.business.currency,
                'sku': product.sku,
                'category': product.category.name,
                'stock_status': stock_status,
                'is_featured': product.is_featured,
                'image': primary_image,
                'variants': [
                    {
                        'name': variant.name,
                        'price_modifier': float(variant.price_modifier),
                        'final_price': float(variant.final_price),
                        'in_stock': variant.quantity > 0 if product.track_inventory else True
                    }
                    for variant in product.variants.filter(is_active=True)
                ]
            })
        
        return results
    
    def search_services(self, query: str, category_id: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search services for WhatsApp bot responses"""
        if not self.business:
            return []
        
        services = Service.objects.filter(
            business=self.business,
            is_active=True
        ).select_related('category', 'business')
        
        if category_id:
            services = services.filter(category_id=category_id)
        
        if query:
            services = services.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(short_description__icontains=query)
            )
        
        services = services[:limit]
        
        results = []
        for service in services:
            # Get primary image
            primary_image = None
            if service.primary_image:
                primary_image = service.primary_image.url
            
            # Format duration
            duration_text = ""
            if service.duration_minutes:
                hours = service.duration_minutes // 60
                minutes = service.duration_minutes % 60
                if hours > 0:
                    duration_text = f"{hours}h"
                    if minutes > 0:
                        duration_text += f" {minutes}m"
                else:
                    duration_text = f"{minutes}m"
            
            results.append({
                'id': str(service.id),
                'name': service.name,
                'description': service.short_description or service.description,
                'price': float(service.price),
                'price_type': service.get_price_type_display(),
                'currency': self.business.currency,
                'category': service.category.name,
                'duration': duration_text,
                'requires_appointment': service.is_appointment_required,
                'is_online': service.is_online_service,
                'is_featured': service.is_featured,
                'image': primary_image
            })
        
        return results
    
    def get_categories(self, parent_id: str = None) -> List[Dict[str, Any]]:
        """Get categories for navigation"""
        if not self.business:
            return []
        
        categories = Category.objects.filter(
            business=self.business,
            is_active=True
        ).select_related('business')
        
        if parent_id:
            categories = categories.filter(parent_id=parent_id)
        else:
            categories = categories.filter(parent__isnull=True)
        
        results = []
        for category in categories:
            # Count products and services in this category
            product_count = Product.objects.filter(
                category=category,
                is_active=True
            ).count()
            
            service_count = Service.objects.filter(
                category=category,
                is_active=True
            ).count()
            
            results.append({
                'id': str(category.id),
                'name': category.name,
                'description': category.description,
                'product_count': product_count,
                'service_count': service_count,
                'image': category.image.url if category.image else None,
                'children': self.get_categories(parent_id=str(category.id))
            })
        
        return results
    
    def get_featured_items(self, item_type: str = 'both', limit: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get featured products and/or services"""
        if not self.business:
            return {'products': [], 'services': []}
        
        result = {'products': [], 'services': []}
        
        if item_type in ['both', 'products']:
            featured_products = Product.objects.filter(
                business=self.business,
                is_active=True,
                is_featured=True
            ).select_related('category')[:limit]
            
            for product in featured_products:
                result['products'].append({
                    'id': str(product.id),
                    'name': product.name,
                    'price': float(product.price),
                    'currency': self.business.currency,
                    'category': product.category.name,
                    'image': product.primary_image.url if product.primary_image else None
                })
        
        if item_type in ['both', 'services']:
            featured_services = Service.objects.filter(
                business=self.business,
                is_active=True,
                is_featured=True
            ).select_related('category')[:limit]
            
            for service in featured_services:
                result['services'].append({
                    'id': str(service.id),
                    'name': service.name,
                    'price': float(service.price),
                    'currency': self.business.currency,
                    'category': service.category.name,
                    'image': service.primary_image.url if service.primary_image else None
                })
        
        return result
    
    def get_available_appointments(self, service_id: str, date: datetime = None) -> List[Dict[str, Any]]:
        """Get available appointment slots for a service"""
        if not self.business:
            return []
        
        try:
            service = Service.objects.get(id=service_id, business=self.business)
        except Service.DoesNotExist:
            return []
        
        if not service.is_appointment_required:
            return []
        
        # Default to today if no date provided
        if not date:
            date = timezone.now().date()
        
        # Get available slots for the next 30 days
        end_date = date + timedelta(days=30)
        
        slots = AppointmentSlot.objects.filter(
            service=service,
            date__gte=date,
            date__lte=end_date,
            is_available=True
        ).order_by('date', 'start_time')
        
        results = []
        for slot in slots:
            results.append({
                'id': str(slot.id),
                'date': slot.date.isoformat(),
                'start_time': slot.start_time.isoformat(),
                'end_time': slot.end_time.isoformat(),
                'available_spots': slot.max_bookings - slot.current_bookings,
                'max_bookings': slot.max_bookings
            })
        
        return results
    
    def get_available_time_slots(self, service_id: str, date: datetime = None) -> List[Dict[str, Any]]:
        """
        Generate available time slots dynamically based on:
        - Business hours for the requested date
        - Service duration
        - Existing bookings (to avoid overlaps)
        - Buffer time between appointments
        """
        if not self.business:
            return []
        
        try:
            service = Service.objects.get(id=service_id, business=self.business)
        except Service.DoesNotExist:
            return []
        
        if not service.is_appointment_required:
            return []
        
        # Default to today if no date provided
        if not date:
            date = timezone.now().date()
        
        # Get business hours for the target date
        day_of_week = date.weekday()
        try:
            business_hours = BusinessHours.objects.get(
                business=self.business,
                day_of_week=day_of_week
            )
        except BusinessHours.DoesNotExist:
            return []
        
        if not business_hours.is_open:
            return []
        
        # Get existing bookings for the date
        existing_bookings = AppointmentBooking.objects.filter(
            business=self.business,
            booking_date=date,
            status__in=['pending', 'confirmed']
        ).order_by('booking_time')
        
        # Generate time slots
        slots = []
        slot_duration = service.duration_minutes or 60  # Default 1 hour
        buffer_time = service.buffer_minutes or 15  # Buffer between appointments
        
        if business_hours.is_24_hours:
            start_time = time(0, 0)
            end_time = time(23, 59)
        else:
            start_time = business_hours.open_time
            end_time = business_hours.close_time
        
        # Generate slots every 15-30 minutes
        current_time = start_time
        slot_interval = 15  # 15-minute intervals
        
        while current_time < end_time:
            slot_end_time = add_minutes_to_time(current_time, slot_duration)
            
            if slot_end_time <= end_time:
                # Check for conflicts
                if not self._has_booking_conflict(existing_bookings, current_time, slot_end_time, buffer_time):
                    slots.append({
                        'start_time': current_time.strftime('%H:%M'),
                        'end_time': slot_end_time.strftime('%H:%M'),
                        'date': date.isoformat(),
                        'available': True,
                        'duration_minutes': slot_duration
                    })
            
            # Move to next slot
            current_time = add_minutes_to_time(current_time, slot_interval)
        
        return slots
    
    def _has_booking_conflict(self, existing_bookings, start_time: time, end_time: time, buffer_time: int) -> bool:
        """Check if a time slot conflicts with existing bookings."""
        for booking in existing_bookings:
            booking_start = booking.booking_time
            booking_end = booking.end_time or add_minutes_to_time(booking_start, booking.duration_minutes)
            
            # Check for overlap with buffer time
            if (start_time < add_minutes_to_time(booking_end, buffer_time) and 
                end_time > subtract_minutes_from_time(booking_start, buffer_time)):
                return True
        
        return False
    
    def is_business_open(self) -> Tuple[bool, str]:
        """Check if business is currently open"""
        if not self.business:
            return False, "Business not found"
        
        # Get current time in business timezone
        business_tz = self.business.get_timezone()
        now = timezone.now().astimezone(business_tz)
        current_day = now.weekday()
        current_time = now.time()
        
        try:
            business_hours = BusinessHours.objects.get(
                business=self.business,
                day_of_week=current_day
            )
            
            if not business_hours.is_open:
                return False, "Business is closed today"
            
            if business_hours.is_24_hours:
                return True, "Business is open 24 hours"
            
            if business_hours.open_time <= current_time <= business_hours.close_time:
                return True, f"Business is open until {business_hours.close_time}"
            else:
                return False, f"Business hours: {business_hours.open_time} - {business_hours.close_time}"
        
        except BusinessHours.DoesNotExist:
            return False, "Business hours not set"
    
    def get_business_summary(self) -> Dict[str, Any]:
        """Get a summary of business for WhatsApp bot"""
        if not self.business:
            return {}
        
        # Get counts
        product_count = Product.objects.filter(business=self.business, is_active=True).count()
        service_count = Service.objects.filter(business=self.business, is_active=True).count()
        category_count = Category.objects.filter(business=self.business, is_active=True).count()
        
        # Check if open
        is_open, hours_message = self.is_business_open()
        
        # Get featured items
        featured = self.get_featured_items(limit=3)
        
        return {
            'name': self.business.name,
            'type': self.business.business_type.display_name,
            'is_open': is_open,
            'hours_message': hours_message,
            'stats': {
                'products': product_count,
                'services': service_count,
                'categories': category_count
            },
            'featured': featured,
            'contact': {
                'phone': self.business.phone_number,
                'whatsapp': self.business.phone_number  # Use phone_number field for WhatsApp
            }
        }
