from django.contrib import admin
from django.utils.html import format_html
from .models import (
    BusinessType, BusinessProfile, Category, Product, ProductVariant, 
    ProductImage, Service, AppointmentSlot, BusinessHours, BusinessLocation, 
    BusinessSettings, Cart, CartItem, AppointmentBooking
)


@admin.register(BusinessType)
class BusinessTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['display_name', 'name']


class BusinessSettingsInline(admin.StackedInline):
    model = BusinessSettings
    extra = 0


class BusinessHoursInline(admin.TabularInline):
    model = BusinessHours
    extra = 7  # One for each day of the week
    max_num = 7


class BusinessLocationInline(admin.TabularInline):
    model = BusinessLocation
    extra = 1


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'business_type', 'phone_number', 'bot_active', 'created_at']
    list_filter = ['business_type', 'bot_active', 'created_at']
    search_fields = ['name', 'phone_number', 'email']
    inlines = [BusinessSettingsInline, BusinessHoursInline, BusinessLocationInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'business_type')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email', 'website', 'address')
        }),
        ('Business Settings', {
            'fields': ('currency', 'timezone', 'language')
        }),
        ('WhatsApp Bot Settings', {
            'fields': ('bot_active', 'auto_reply_enabled')
        }),
    )


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 1
    fk_name = 'parent'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'parent', 'sort_order', 'is_active']
    list_filter = ['business', 'is_active', 'parent']
    search_fields = ['name', 'description']
    inlines = [CategoryInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'parent')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'category', 'price', 'quantity', 'is_active', 'is_featured']
    list_filter = ['business', 'category', 'is_active', 'is_featured', 'is_digital', 'track_inventory']
    search_fields = ['name', 'sku', 'description']
    inlines = [ProductVariantInline, ProductImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('business', 'category', 'name', 'description', 'short_description')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_price', 'cost_price')
        }),
        ('Inventory', {
            'fields': ('sku', 'barcode', 'track_inventory', 'quantity', 'low_stock_threshold')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_digital')
        }),
        ('Media & SEO', {
            'fields': ('primary_image', 'meta_title', 'meta_description', 'slug'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'category')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'sku', 'price_modifier', 'quantity', 'is_active']
    list_filter = ['is_active', 'product__business']
    search_fields = ['name', 'sku', 'product__name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'sort_order', 'is_primary']
    list_filter = ['is_primary', 'product__business']
    search_fields = ['product__name', 'alt_text']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'category', 'price', 'price_type', 'is_active', 'is_featured']
    list_filter = ['business', 'category', 'price_type', 'is_active', 'is_featured', 'is_appointment_required']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('business', 'category', 'name', 'description', 'short_description')
        }),
        ('Pricing', {
            'fields': ('price', 'price_type')
        }),
        ('Service Details', {
            'fields': ('duration_minutes', 'is_appointment_required', 'is_online_service')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Media', {
            'fields': ('primary_image',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'category')


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ['service', 'date', 'start_time', 'end_time', 'is_available', 'current_bookings', 'max_bookings']
    list_filter = ['service__business', 'date', 'is_available']
    search_fields = ['service__name']
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service__business')


@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ['business', 'get_day_display', 'is_open', 'open_time', 'close_time', 'is_24_hours']
    list_filter = ['business', 'day_of_week', 'is_open', 'is_24_hours']
    
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Day'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business')


@admin.register(BusinessLocation)
class BusinessLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'city', 'state', 'country', 'is_primary', 'is_active']
    list_filter = ['business', 'country', 'state', 'is_primary', 'is_active']
    search_fields = ['name', 'address', 'city', 'state', 'country']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business')


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = ['business', 'require_customer_info', 'allow_guest_orders', 'minimum_order_amount']
    list_filter = ['require_customer_info', 'allow_guest_orders', 'email_notifications', 'sms_notifications']
    search_fields = ['business__name']
    
    fieldsets = (
        ('WhatsApp Bot Messages', {
            'fields': ('welcome_message', 'auto_reply_message', 'business_hours_message')
        }),
        ('Order/Booking Settings', {
            'fields': ('require_customer_info', 'allow_guest_orders', 'minimum_order_amount')
        }),
        ('Payment Settings', {
            'fields': ('accepted_payment_methods', 'payment_instructions')
        }),
        ('Notification Settings', {
            'fields': ('email_notifications', 'sms_notifications')
        }),
        ('Custom Fields', {
            'fields': ('custom_fields',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business')


class CartItemInline(admin.TabularInline):
    """Inline admin for cart items."""
    model = CartItem
    extra = 0
    readonly_fields = ['added_at', 'updated_at']
    fields = ['product', 'variant', 'quantity', 'unit_price', 'total_price', 'added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin for shopping carts."""
    list_display = ['id', 'business', 'thread', 'name', 'status', 'total_items', 'total_amount', 'created_at']
    list_filter = ['status', 'business', 'thread__user', 'created_at']
    search_fields = ['thread__thread_id', 'thread__remote_jid', 'name', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'total_items', 'total_amount']
    inlines = [CartItemInline]
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('id', 'thread', 'business', 'status')
        }),
        ('Customer Information', {
            'fields': ('name', 'email')
        }),
        ('Cart Details', {
            'fields': ('expires_at',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'thread', 'thread__user')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin for cart items."""
    list_display = ['id', 'cart', 'product', 'variant', 'quantity', 'unit_price', 'total_price', 'added_at']
    list_filter = ['cart__business', 'added_at']
    search_fields = ['cart__thread_id', 'product__name', 'variant__name']
    readonly_fields = ['added_at', 'updated_at', 'total_price']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cart', 'product', 'variant')


@admin.register(AppointmentBooking)
class AppointmentBookingAdmin(admin.ModelAdmin):
    """Admin for appointment bookings."""
    list_display = ['id', 'business', 'thread', 'customer_name', 'service', 'booking_date', 'booking_time', 'status', 'total_price']
    list_filter = ['status', 'business', 'thread__user', 'booking_date', 'created_at']
    search_fields = ['thread__thread_id', 'thread__remote_jid', 'customer_name', 'customer_phone', 'customer_email', 'service__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('id', 'thread', 'business', 'service', 'appointment_slot', 'status')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('Appointment Details', {
            'fields': ('booking_date', 'booking_time', 'duration_minutes', 'total_price')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business', 'service', 'appointment_slot', 'thread', 'thread__user')