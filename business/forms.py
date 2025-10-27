"""
Business app forms.
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    BusinessProfile, BusinessType, Product, Service, Category, 
    AppointmentSlot, BusinessHours, BusinessLocation, BusinessSettings,
    Cart, CartItem, AppointmentBooking
)
from core.timezone_utils import format_timezone_choices
from core.currency_utils import format_currency_choices
from core.utils import normalize_string_field
import re


class BusinessProfileForm(forms.ModelForm):
    """Form for creating/editing business profiles."""
    
    class Meta:
        model = BusinessProfile
        fields = [
            'name', 'description', 'business_type', 'phone_number', 'email', 
            'website', 'address', 'currency', 'timezone', 'language',
            'bot_active', 'auto_reply_enabled'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter business name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe your business'
            }),
            'business_type': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'business@example.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Business address'
            }),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
            'bot_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_reply_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['timezone'].choices = format_timezone_choices()
        self.fields['currency'].choices = format_currency_choices()
    
    def clean_name(self):
        """Normalize business name."""
        return normalize_string_field(self.cleaned_data.get('name'))
    
    def clean_phone_number(self):
        """Validate phone number format."""
        phone_number = normalize_string_field(self.cleaned_data.get('phone_number'))
        if phone_number and not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
            raise ValidationError('Please enter a valid phone number with country code.')
        return phone_number
    


class ProductForm(forms.ModelForm):
    """Form for creating/editing products."""
    
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'short_description', 'category',
            'price', 'compare_price', 'cost_price', 'sku', 'barcode',
            'track_inventory', 'quantity', 'low_stock_threshold',
            'is_active', 'is_featured', 'is_digital', 'primary_image',
            'meta_title', 'meta_description', 'slug'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'compare_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'track_inventory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_digital': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_name(self):
        """Normalize product name."""
        return normalize_string_field(self.cleaned_data.get('name'))
    
    def clean_sku(self):
        """Normalize SKU."""
        return normalize_string_field(self.cleaned_data.get('sku'))


class ServiceForm(forms.ModelForm):
    """Form for creating/editing services."""
    
    class Meta:
        model = Service
        fields = [
            'name', 'description', 'short_description', 'category',
            'price', 'price_type', 'duration_minutes',
            'is_appointment_required', 'is_online_service',
            'is_active', 'is_featured', 'primary_image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'price_type': forms.Select(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_appointment_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_online_service': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        
        # Set default values for fields with defaults
        if not self.instance.pk:  # Only for new instances
            self.fields['is_active'].initial = True
        
        # Filter category choices to only show categories from the same business
        if self.business:
            self.fields['category'].queryset = Category.objects.filter(business=self.business)
        else:
            self.fields['category'].queryset = Category.objects.none()
    
    def clean_name(self):
        """Normalize service name."""
        return normalize_string_field(self.cleaned_data.get('name'))


class CategoryForm(forms.ModelForm):
    """Form for creating/editing categories."""
    
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon', 'parent', 'image', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'icon': forms.HiddenInput(),  # We'll handle this with JavaScript
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop('business', None)
        super().__init__(*args, **kwargs)
        
        # Set default values for fields with defaults
        if not self.instance.pk:  # Only for new instances
            self.fields['is_active'].initial = True
        
        # Filter parent choices to only show categories from the same business
        if 'instance' in kwargs and kwargs['instance'] and kwargs['instance'].business:
            business = kwargs['instance'].business
            self.fields['parent'].queryset = Category.objects.filter(
                business=business
            ).exclude(id=kwargs['instance'].id if kwargs['instance'].id else None)
        elif self.business:
            self.fields['parent'].queryset = Category.objects.filter(business=self.business)
        else:
            self.fields['parent'].queryset = Category.objects.none()
    
    def clean_name(self):
        """Normalize category name."""
        return normalize_string_field(self.cleaned_data.get('name'))


class AppointmentSlotForm(forms.ModelForm):
    """Form for creating/editing appointment slots."""
    
    class Meta:
        model = AppointmentSlot
        fields = ['service', 'date', 'start_time', 'end_time', 'is_available', 'max_bookings']
        widgets = {
            'service': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_bookings': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class BusinessHoursForm(forms.ModelForm):
    """Form for business hours."""
    
    class Meta:
        model = BusinessHours
        fields = ['day_of_week', 'is_open', 'open_time', 'close_time', 'is_24_hours']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'is_open': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'open_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'close_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'is_24_hours': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BusinessLocationForm(forms.ModelForm):
    """Form for business locations."""
    
    class Meta:
        model = BusinessLocation
        fields = [
            'name', 'address', 'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude', 'phone', 'email', 'is_primary', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_name(self):
        """Normalize location name."""
        return normalize_string_field(self.cleaned_data.get('name'))


class CartForm(forms.ModelForm):
    """Form for managing cart information."""
    
    class Meta:
        model = Cart
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Customer name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'customer@example.com'
            }),
        }
    
    def clean_name(self):
        """Normalize customer name."""
        return normalize_string_field(self.cleaned_data.get('name'))


class CartItemForm(forms.ModelForm):
    """Form for managing cart items."""
    
    class Meta:
        model = CartItem
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '999'
            })
        }


class AppointmentBookingForm(forms.ModelForm):
    """Form for booking appointments."""
    
    class Meta:
        model = AppointmentBooking
        fields = [
            'customer_name', 'customer_phone', 'customer_email', 
            'booking_date', 'booking_time', 'status', 'notes'
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name'
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1234567890'
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'booking_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'booking_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Special requests or notes'
            })
        }
    
    def clean_customer_name(self):
        """Normalize customer name."""
        return normalize_string_field(self.cleaned_data.get('customer_name'))
    
    def clean_customer_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('customer_phone')
        if phone:
            # Basic phone number validation
            phone = re.sub(r'[^\d+]', '', phone)
            if not phone.startswith('+'):
                phone = '+' + phone
        return phone
    
    def clean_booking_date(self):
        """Validate booking date is not in the past."""
        from django.utils import timezone
        booking_date = self.cleaned_data.get('booking_date')
        if booking_date and booking_date < timezone.now().date():
            raise ValidationError("Booking date cannot be in the past.")
        return booking_date
