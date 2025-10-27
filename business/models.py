from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import zoneinfo
from django.contrib.auth.models import User

from core.timezone_utils import format_timezone_choices
from core.currency_utils import format_currency_choices

class BusinessType(models.Model):
    """Different types of businesses supported by the system"""
    BUSINESS_TYPES = [
        ('ecommerce', 'E-commerce Store'),
        ('restaurant', 'Restaurant/Food Service'),
        ('retail', 'Retail Store'),
        ('service', 'Professional Services'),
        ('appointment', 'Appointment Booking'),
        ('subscription', 'Subscription Service'),
        ('marketplace', 'Marketplace'),
        ('consultation', 'Consultation Services'),
        ('education', 'Education/Training'),
        ('healthcare', 'Healthcare Services'),
        ('beauty', 'Beauty & Wellness'),
        ('automotive', 'Automotive Services'),
        ('real_estate', 'Real Estate'),
        ('travel', 'Travel & Tourism'),
        ('entertainment', 'Entertainment'),
        ('fitness', 'Fitness & Sports'),
        ('logistics', 'Logistics & Delivery'),
        ('financial', 'Financial Services'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, choices=BUSINESS_TYPES, unique=True)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # For UI icons
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.display_name


class BusinessProfile(models.Model):
    """Main business profile that can be linked to WhatsApp bots"""

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_profile')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    business_type = models.ForeignKey(BusinessType, on_delete=models.CASCADE)
    
    # Contact Information
    phone_number = models.CharField(max_length=20, unique=True, help_text="Business WhatsApp number for OTP verification")
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Business Settings
    currency = models.CharField(max_length=3, choices=format_currency_choices())
    timezone = models.CharField(max_length=50, choices=format_timezone_choices())
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    
    # WhatsApp Bot Settings
    bot_active = models.BooleanField(default=True)
    auto_reply_enabled = models.BooleanField(default=True)
    
    # Phone Verification
    is_verified = models.BooleanField(default=False, help_text="WhatsApp phone verification status")
    
    # OTP fields for WhatsApp verification
    otp_code = models.CharField(max_length=6, blank=True, null=True, help_text="OTP code for WhatsApp verification")
    otp_created_at = models.DateTimeField(blank=True, null=True, help_text="When OTP was generated")
    otp_attempts = models.IntegerField(default=0, help_text="Number of OTP verification attempts")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.business_type.display_name})"
    
    def get_timezone(self):
        """Get timezone as zoneinfo.ZoneInfo object."""
        try:
            return zoneinfo.ZoneInfo(self.timezone)
        except Exception:
            return zoneinfo.ZoneInfo('UTC')
    
    def get_currency_info(self):
        """Get currency information."""
        from core.currency_utils import get_currency_info
        return get_currency_info(self.currency)
    
    def get_currency_symbol(self):
        """Get currency symbol."""
        from core.currency_utils import get_currency_symbol
        return get_currency_symbol(self.currency)
    
    def get_currency_name(self):
        """Get currency name."""
        from core.currency_utils import get_currency_name
        return get_currency_name(self.currency)
    
    def format_amount(self, amount):
        """Format amount with currency symbol."""
        from core.currency_utils import format_currency_amount
        return format_currency_amount(amount, self.currency)
    
    def generate_otp(self):
        """Generate a 6-digit OTP code and set timestamp"""
        import secrets
        from django.utils import timezone
        
        self.otp_code = f"{secrets.randbelow(1000000):06d}"
        self.otp_created_at = timezone.now()
        self.otp_attempts = 0
        self.save(update_fields=['otp_code', 'otp_created_at', 'otp_attempts'])
        return self.otp_code
    
    def verify_otp(self, code):
        """Verify OTP code with 10-minute expiry and attempt limit"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Check if OTP exists
        if not self.otp_code or not self.otp_created_at:
            return False, "No OTP code found"
        
        # Check attempt limit
        if self.otp_attempts >= 3:
            return False, "Maximum OTP attempts exceeded. Please request a new code."
        
        # Check expiry (10 minutes)
        expiry_time = self.otp_created_at + timedelta(minutes=10)
        if timezone.now() > expiry_time:
            return False, "OTP code has expired. Please request a new code."
        
        # Check code match
        if self.otp_code != code:
            self.otp_attempts += 1
            self.save(update_fields=['otp_attempts'])
            return False, "Invalid OTP code"
        
        # Success - mark as verified and clear OTP
        self.is_verified = True
        self.otp_code = None
        self.otp_created_at = None
        self.otp_attempts = 0
        self.save(update_fields=['is_verified', 'otp_code', 'otp_created_at', 'otp_attempts'])
        return True, "OTP verified successfully"


class Category(models.Model):
    """Generic category system for products/services"""
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Bootstrap icon class (e.g., bi-tag, bi-box)")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Enhanced product model for various business types"""
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    
    # Basic Information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Original price for discounts
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Cost to business
    
    # Inventory
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    track_inventory = models.BooleanField(default=True)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)  # For digital products
    
    # Media
    primary_image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    # SEO
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['sku']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def is_in_stock(self):
        return self.quantity > 0 if self.track_inventory else True
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold if self.track_inventory else False


class ProductVariant(models.Model):
    """Product variants (size, color, etc.)"""
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Variant attributes (JSON field for flexibility)
    attributes = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"
    
    @property
    def final_price(self):
        return self.product.price + self.price_modifier


class ProductImage(models.Model):
    """Multiple images for products"""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['sort_order']


class Service(models.Model):
    """Services offered by businesses"""
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services')
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    short_description = models.CharField(max_length=500, blank=True, null=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    price_type = models.CharField(max_length=20, choices=[
        ('fixed', 'Fixed Price'),
        ('hourly', 'Per Hour'),
        ('per_person', 'Per Person'),
        ('custom', 'Custom Quote'),
    ], default='fixed')
    
    # Service Details
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)  # Service duration
    buffer_minutes = models.PositiveIntegerField(default=15, help_text="Buffer time in minutes between appointments")
    is_appointment_required = models.BooleanField(default=False)
    is_online_service = models.BooleanField(default=False)  # Can be delivered online
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Media
    primary_image = models.ImageField(upload_to='services/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_duration_display(self):
        """Format duration in a human-readable way."""
        if not self.duration_minutes:
            return "Not specified"
        
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"


class AppointmentSlot(models.Model):
    """Available appointment slots for services"""
    service = models.ForeignKey(Service, related_name='appointment_slots', on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_bookings = models.PositiveIntegerField(default=1)
    current_bookings = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['service', 'date', 'start_time']
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.service.name} - {self.date} {self.start_time}"


class BusinessHours(models.Model):
    """Business operating hours"""
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='business_hours')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    is_open = models.BooleanField(default=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_24_hours = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['business', 'day_of_week']
        ordering = ['day_of_week']
    
    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK)[self.day_of_week]
        if self.is_24_hours:
            return f"{day_name}: 24 Hours"
        elif self.is_open:
            return f"{day_name}: {self.open_time} - {self.close_time}"
        else:
            return f"{day_name}: Closed"


class BusinessLocation(models.Model):
    """Multiple locations for businesses"""
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.business.name} - {self.name}"


class BusinessSettings(models.Model):
    """Business-specific settings and configurations"""
    business = models.OneToOneField(BusinessProfile, on_delete=models.CASCADE, related_name='settings')
    
    # WhatsApp Bot Settings
    welcome_message = models.TextField(blank=True, null=True)
    auto_reply_message = models.TextField(blank=True, null=True)
    business_hours_message = models.TextField(blank=True, null=True)
    
    # Order/Booking Settings
    require_customer_info = models.BooleanField(default=True)
    allow_guest_orders = models.BooleanField(default=False)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Payment Settings
    accepted_payment_methods = models.JSONField(default=list, blank=True)
    payment_instructions = models.TextField(blank=True, null=True)
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Custom Fields
    custom_fields = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Settings for {self.business.name}"


class Cart(models.Model):
    """Shopping cart linked to conversation thread."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey('aiengine.ConversationThread', on_delete=models.CASCADE, related_name='carts')
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='carts')
    email = models.EmailField(blank=True, null=True, help_text="Customer email")
    name = models.CharField(max_length=255, blank=True, null=True, help_text="Customer name")
    
    # Cart status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('abandoned', 'Abandoned'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Cart expiration time")
    
    # Notes
    notes = models.TextField(blank=True, null=True, help_text="Special instructions or notes")
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['thread', 'business']
        indexes = [
            models.Index(fields=['thread']),
            models.Index(fields=['business', 'status']),
        ]
    
    def __str__(self):
        customer = self.name or f"Thread {self.thread.thread_id[:8]}"
        return f"Cart for {customer} - {self.business.name}"
    
    @property
    def total_items(self):
        """Total number of items in cart."""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_amount(self):
        """Total amount of all items in cart."""
        return sum(item.total_price for item in self.items.all())
    
    @property
    def is_empty(self):
        """Check if cart is empty."""
        return self.items.count() == 0
    
    def get_customer_info(self):
        """Get customer information for display."""
        info = []
        if self.name:
            info.append(f"Name: {self.name}")
        if self.email:
            info.append(f"Email: {self.email}")
        if self.thread and self.thread.remote_jid:
            # Extract phone number from WhatsApp JID
            phone = self.thread.remote_jid.split('@')[0] if '@' in self.thread.remote_jid else self.thread.remote_jid
            info.append(f"Phone: {phone}")
        return " | ".join(info) if info else "Anonymous"


class CartItem(models.Model):
    """Individual item in shopping cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    
    # Pricing (snapshot at time of adding to cart)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit when added to cart")
    
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['added_at']
        unique_together = ['cart', 'product', 'variant']
        indexes = [
            models.Index(fields=['cart', 'product']),
        ]
    
    def __str__(self):
        variant_info = f" ({self.variant.name})" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{variant_info}"
    
    @property
    def total_price(self):
        """Total price for this cart item."""
        return self.unit_price * self.quantity
    
    @property
    def product_display_name(self):
        """Display name with variant if applicable."""
        if self.variant:
            return f"{self.product.name} - {self.variant.name}"
        return self.product.name


class AppointmentBooking(models.Model):
    """Appointment booking linked to conversation thread."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey('aiengine.ConversationThread', on_delete=models.CASCADE, related_name='appointment_bookings')
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='appointment_bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    appointment_slot = models.ForeignKey(AppointmentSlot, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True, help_text="Optional appointment slot (deprecated with dynamic scheduling)")
    
    # Customer information
    customer_name = models.CharField(max_length=255, help_text="Customer name")
    customer_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Customer phone number")
    customer_email = models.EmailField(blank=True, null=True, help_text="Customer email")
    
    # Booking details
    booking_date = models.DateField(help_text="Date of appointment")
    booking_time = models.TimeField(help_text="Time of appointment")
    end_time = models.TimeField(help_text="End time of appointment", null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(help_text="Duration in minutes")
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Additional information
    notes = models.TextField(blank=True, null=True, help_text="Special requests or notes")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total price for the service")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['booking_date', 'booking_time']
        indexes = [
            models.Index(fields=['thread']),
            models.Index(fields=['business', 'status']),
            models.Index(fields=['booking_date', 'booking_time']),
            models.Index(fields=['customer_phone']),
        ]
    
    def __str__(self):
        return f"{self.customer_name} - {self.service.name} on {self.booking_date} at {self.booking_time}"
    
    @property
    def is_confirmed(self):
        """Check if appointment is confirmed."""
        return self.status == 'confirmed'
    
    @property
    def is_pending(self):
        """Check if appointment is pending."""
        return self.status == 'pending'
    
    @property
    def is_cancelled(self):
        """Check if appointment is cancelled."""
        return self.status == 'cancelled'
    
    def calculate_end_time(self):
        """Calculate end time based on start time and duration."""
        if not self.booking_time or not self.duration_minutes:
            return None
        
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(self.booking_date, self.booking_time)
        end_datetime = start_datetime + timedelta(minutes=self.duration_minutes)
        return end_datetime.time()
    
    def save(self, *args, **kwargs):
        """Override save to automatically calculate end_time."""
        if not self.end_time and self.booking_time and self.duration_minutes:
            self.end_time = self.calculate_end_time()
        super().save(*args, **kwargs)
    
    @property
    def booking_datetime(self):
        """Get booking as datetime object."""
        from django.utils import timezone
        return timezone.datetime.combine(self.booking_date, self.booking_time)
    
    def get_customer_info(self):
        """Get customer information for display."""
        info = [f"Name: {self.customer_name}", f"Phone: {self.customer_phone}"]
        if self.customer_email:
            info.append(f"Email: {self.customer_email}")
        return " | ".join(info)