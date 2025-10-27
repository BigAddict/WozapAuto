"""
Business app views.
"""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, CreateView, DetailView, UpdateView, DeleteView, View
)
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone

from core.mixins import ProfileRequiredMixin, AuditLogMixin
from .models import (
    BusinessProfile, Product, Service, Category, AppointmentSlot,
    BusinessHours, BusinessLocation, BusinessSettings, Cart, CartItem, AppointmentBooking
)
from .forms import (
    BusinessProfileForm, ProductForm, ServiceForm, CategoryForm,
    AppointmentSlotForm, BusinessHoursForm, BusinessLocationForm,
    CartForm, CartItemForm, AppointmentBookingForm
)

logger = logging.getLogger('business.views')

def get_user_business(user):
    """Helper function to get user's business profile."""
    try:
        return user.business_profile
    except:
        return None


# Business Profile Views
class BusinessListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List all businesses for the current user."""
    model = BusinessProfile
    template_name = 'business/business_list.html'
    context_object_name = 'businesses'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter businesses by user."""
        return BusinessProfile.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_businesses'] = self.get_queryset().count()
        return context


class BusinessCreateView(ProfileRequiredMixin, AuditLogMixin, CreateView):
    """Create a new business profile."""
    model = BusinessProfile
    form_class = BusinessProfileForm
    template_name = 'business/business_form.html'
    success_url = reverse_lazy('business:business_detail')
    
    def form_valid(self, form):
        """Save the business and log activity."""
        form.instance.user = self.request.user
        response = super().form_valid(form)
        self.log_activity('business_created', business_id=str(self.object.id))
        messages.success(self.request, f'Business "{self.object.name}" created successfully!')
        return response


class BusinessDetailView(ProfileRequiredMixin, AuditLogMixin, DetailView):
    """View business details with stats."""
    model = BusinessProfile
    template_name = 'business/business_detail.html'
    context_object_name = 'business'
    
    def get_object(self, queryset=None):
        """Get the user's business profile."""
        return get_user_business(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        business = self.object
        
        # Get business stats
        context.update({
            'products_count': business.products.filter(is_active=True).count(),
            'services_count': business.services.filter(is_active=True).count(),
            'categories_count': business.categories.filter(is_active=True).count(),
            'appointments_count': AppointmentSlot.objects.filter(
                service__business=business
            ).count(),
            'recent_products': business.products.filter(is_active=True)[:5],
            'recent_services': business.services.filter(is_active=True)[:5],
        })
        
        return context


class BusinessUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update business profile."""
    model = BusinessProfile
    form_class = BusinessProfileForm
    template_name = 'business/business_form.html'
    
    def get_object(self, queryset=None):
        """Get the user's business profile."""
        return get_user_business(self.request.user)
    
    def get_success_url(self):
        return reverse('business:business_detail')
    
    def form_valid(self, form):
        """Save changes and log activity."""
        response = super().form_valid(form)
        self.log_activity('business_updated', business_id=str(self.object.id))
        messages.success(self.request, f'Business "{self.object.name}" updated successfully!')
        return response


class BusinessDeleteView(ProfileRequiredMixin, AuditLogMixin, DeleteView):
    """Delete business profile."""
    model = BusinessProfile
    template_name = 'business/business_confirm_delete.html'
    success_url = reverse_lazy('business:business_detail')
    
    def get_object(self, queryset=None):
        """Get the user's business profile."""
        return get_user_business(self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Delete business and log activity."""
        business = self.get_object()
        business_name = business.name
        self.log_activity('business_deleted', business_id=str(business.id))
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Business "{business_name}" deleted successfully!')
        return response


# Product Views
class ProductListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List products for a business."""
    model = Product
    template_name = 'business/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter products by user's business."""
        try:
            self.business = self.request.user.business_profile
            return Product.objects.filter(business=self.business).order_by('-created_at')
        except:
            return Product.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = getattr(self, 'business', None)
        return context


class ProductCreateView(ProfileRequiredMixin, AuditLogMixin, CreateView):
    """Create a new product."""
    model = Product
    form_class = ProductForm
    template_name = 'business/product_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        try:
            self.business = request.user.business_profile
        except:
            self.business = None
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('business:product_list')
    
    def form_valid(self, form):
        """Set business and save product."""
        if not self.business:
            messages.error(self.request, 'No business profile found. Please create one first.')
            return self.form_invalid(form)
        form.instance.business = self.business
        response = super().form_valid(form)
        self.log_activity('product_created', business_id=str(self.business.id), product_id=self.object.id)
        messages.success(self.request, f'Product "{self.object.name}" created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.business
        return context


class ProductUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update product."""
    model = Product
    form_class = ProductForm
    template_name = 'business/product_form.html'
    
    def get_success_url(self):
        return reverse('business:product_list')
    
    def form_valid(self, form):
        """Save changes and log activity."""
        response = super().form_valid(form)
        self.log_activity('product_updated', business_id=str(self.object.business.id), product_id=self.object.id)
        messages.success(self.request, f'Product "{self.object.name}" updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.object.business
        return context


class ProductDeleteView(ProfileRequiredMixin, AuditLogMixin, DeleteView):
    """Delete product."""
    model = Product
    template_name = 'business/product_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('business:product_list')
    
    def delete(self, request, *args, **kwargs):
        """Delete product and log activity."""
        product = self.get_object()
        product_name = product.name
        business_id = product.business.id
        self.log_activity('product_deleted', business_id=str(business_id), product_id=product.id)
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return response


# Service Views
class ServiceListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List services for a business."""
    model = Service
    template_name = 'business/service_list.html'
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter services by user's business."""
        try:
            self.business = self.request.user.business_profile
            return Service.objects.filter(business=self.business).order_by('-created_at')
        except:
            return Service.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = getattr(self, 'business', None)
        return context


class ServiceCreateView(ProfileRequiredMixin, AuditLogMixin, CreateView):
    """Create a new service."""
    model = Service
    form_class = ServiceForm
    template_name = 'business/service_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('business:service_list')
    
    def get_form_kwargs(self):
        """Pass business context to form."""
        kwargs = super().get_form_kwargs()
        kwargs['business'] = self.business
        return kwargs
    
    def form_valid(self, form):
        """Set business and save service."""
        if not self.business:
            messages.error(self.request, 'No business profile found. Please create one first.')
            return self.form_invalid(form)
        form.instance.business = self.business
        response = super().form_valid(form)
        self.log_activity('service_created', business_id=str(self.business.id), service_id=self.object.id)
        messages.success(self.request, f'Service "{self.object.name}" created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.business
        return context


class ServiceUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update service."""
    model = Service
    form_class = ServiceForm
    template_name = 'business/service_form.html'
    
    def get_success_url(self):
        return reverse('business:service_list')
    
    def form_valid(self, form):
        """Save changes and log activity."""
        response = super().form_valid(form)
        self.log_activity('service_updated', business_id=str(self.object.business.id), service_id=self.object.id)
        messages.success(self.request, f'Service "{self.object.name}" updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.object.business
        return context


class ServiceDeleteView(ProfileRequiredMixin, AuditLogMixin, DeleteView):
    """Delete service."""
    model = Service
    template_name = 'business/service_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('business:service_list')
    
    def delete(self, request, *args, **kwargs):
        """Delete service and log activity."""
        service = self.get_object()
        service_name = service.name
        business_id = service.business.id
        self.log_activity('service_deleted', business_id=str(business_id), service_id=service.id)
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Service "{service_name}" deleted successfully!')
        return response


# Appointment Views
class AppointmentListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List appointment bookings for a business."""
    model = AppointmentBooking
    template_name = 'business/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter appointment bookings by user's business."""
        try:
            self.business = self.request.user.business_profile
            return AppointmentBooking.objects.filter(
                business=self.business
            ).order_by('-booking_date', '-booking_time')
        except:
            return AppointmentBooking.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = getattr(self, 'business', None)
        return context


class AppointmentCreateView(ProfileRequiredMixin, AuditLogMixin, CreateView):
    """Create a new appointment slot."""
    model = AppointmentSlot
    form_class = AppointmentSlotForm
    template_name = 'business/appointment_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('business:appointment_list')
    
    def form_valid(self, form):
        """Save appointment and log activity."""
        if not self.business:
            messages.error(self.request, 'No business profile found. Please create one first.')
            return self.form_invalid(form)
        form.instance.business = self.business
        response = super().form_valid(form)
        self.log_activity('appointment_created', business_id=str(self.business.id), appointment_id=self.object.id)
        messages.success(self.request, 'Appointment slot created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.business
        return context


class AppointmentUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update appointment slot."""
    model = AppointmentSlot
    form_class = AppointmentSlotForm
    template_name = 'business/appointment_form.html'
    
    def get_success_url(self):
        return reverse('business:appointment_list')
    
    def form_valid(self, form):
        """Save changes and log activity."""
        response = super().form_valid(form)
        self.log_activity('appointment_updated', business_id=str(self.object.service.business.id), appointment_id=self.object.id)
        messages.success(self.request, 'Appointment slot updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.object.service.business
        return context


class AppointmentDeleteView(ProfileRequiredMixin, AuditLogMixin, DeleteView):
    """Delete appointment slot."""
    model = AppointmentSlot
    template_name = 'business/appointment_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('business:appointment_list')
    
    def delete(self, request, *args, **kwargs):
        """Delete appointment and log activity."""
        appointment = self.get_object()
        business_id = appointment.service.business.id
        self.log_activity('appointment_deleted', business_id=str(business_id), appointment_id=appointment.id)
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Appointment slot deleted successfully!')
        return response


# Category Views
class CategoryListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List categories for a business."""
    model = Category
    template_name = 'business/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter categories by user's business."""
        try:
            self.business = self.request.user.business_profile
            return Category.objects.filter(business=self.business).order_by('sort_order', 'name')
        except:
            return Category.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = getattr(self, 'business', None)
        return context


class CategoryCreateView(ProfileRequiredMixin, AuditLogMixin, CreateView):
    """Create a new category."""
    model = Category
    form_class = CategoryForm
    template_name = 'business/category_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('business:category_list')
    
    def get_form_kwargs(self):
        """Pass business context to form."""
        kwargs = super().get_form_kwargs()
        kwargs['business'] = self.business
        return kwargs
    
    def form_valid(self, form):
        """Set business and save category."""
        if not self.business:
            messages.error(self.request, 'No business profile found. Please create one first.')
            return self.form_invalid(form)
        form.instance.business = self.business
        response = super().form_valid(form)
        self.log_activity('category_created', business_id=str(self.business.id), category_id=self.object.id)
        messages.success(self.request, f'Category "{self.object.name}" created successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.business
        return context


class CategoryUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update category."""
    model = Category
    form_class = CategoryForm
    template_name = 'business/category_form.html'
    
    def get_object(self, queryset=None):
        """Get the category and set business context."""
        obj = super().get_object(queryset)
        self.business = obj.business
        return obj
    
    def get_form_kwargs(self):
        """Pass business context to form."""
        kwargs = super().get_form_kwargs()
        kwargs['business'] = self.business
        return kwargs
    
    def get_success_url(self):
        return reverse('business:category_list')
    
    def form_valid(self, form):
        """Save changes and log activity."""
        response = super().form_valid(form)
        self.log_activity('category_updated', business_id=str(self.object.business.id), category_id=self.object.id)
        messages.success(self.request, f'Category "{self.object.name}" updated successfully!')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['business'] = self.object.business
        return context


class CategoryDeleteView(ProfileRequiredMixin, AuditLogMixin, DeleteView):
    """Delete category."""
    model = Category
    template_name = 'business/category_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('business:category_list')
    
    def delete(self, request, *args, **kwargs):
        """Delete category and log activity."""
        category = self.get_object()
        category_name = category.name
        business_id = category.business.id
        self.log_activity('category_deleted', business_id=str(business_id), category_id=category.id)
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Category "{category_name}" deleted successfully!')
        return response


# Cart Views

class CartListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List all carts for a business."""
    model = Cart
    template_name = 'business/cart_list.html'
    context_object_name = 'carts'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter carts by user's business."""
        try:
            business = self.request.user.business_profile
            return Cart.objects.filter(
                business=business,
                thread__user=self.request.user
            ).order_by('-created_at')
        except:
            return Cart.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add business context."""
        context = super().get_context_data(**kwargs)
        try:
            context['business'] = self.request.user.business_profile
        except:
            context['business'] = None
        return context


class CartDetailView(ProfileRequiredMixin, AuditLogMixin, DetailView):
    """View cart details and items."""
    model = Cart
    template_name = 'business/cart_detail.html'
    context_object_name = 'cart'
    
    def get_queryset(self):
        """Filter by user's business."""
        try:
            business = self.request.user.business_profile
            return Cart.objects.filter(
                business=business,
                thread__user=self.request.user
            )
        except:
            return Cart.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add business context."""
        context = super().get_context_data(**kwargs)
        try:
            context['business'] = self.request.user.business_profile
        except:
            context['business'] = None
        return context


class CartUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update cart information."""
    model = Cart
    form_class = CartForm
    template_name = 'business/cart_form.html'
    
    def get_queryset(self):
        """Filter by user's business."""
        try:
            business = self.request.user.business_profile
            return Cart.objects.filter(
                business=business,
                thread__user=self.request.user
            )
        except:
            return Cart.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add business context."""
        context = super().get_context_data(**kwargs)
        try:
            context['business'] = self.request.user.business_profile
        except:
            context['business'] = None
        return context
    
    def get_success_url(self):
        """Redirect to cart detail."""
        return reverse('business:cart_detail', kwargs={
            'pk': self.object.id
        })


# Appointment Booking Views

class AppointmentBookingListView(ProfileRequiredMixin, AuditLogMixin, ListView):
    """List all appointment bookings for a business."""
    model = AppointmentBooking
    template_name = 'business/appointment_booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter bookings by user's business."""
        try:
            business = self.request.user.business_profile
            return AppointmentBooking.objects.filter(
                business=business,
                thread__user=self.request.user
            ).order_by('-created_at')
        except:
            return AppointmentBooking.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add business context."""
        context = super().get_context_data(**kwargs)
        try:
            context['business'] = self.request.user.business_profile
        except:
            context['business'] = None
        return context


class AppointmentBookingDetailView(ProfileRequiredMixin, AuditLogMixin, DetailView):
    """View appointment booking details."""
    model = AppointmentBooking
    template_name = 'business/appointment_booking_detail.html'
    context_object_name = 'booking'
    
    def get_queryset(self):
        """Filter by user's business."""
        try:
            business = self.request.user.business_profile
            return AppointmentBooking.objects.filter(
                business=business,
                thread__user=self.request.user
            )
        except:
            return AppointmentBooking.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add business context."""
        context = super().get_context_data(**kwargs)
        try:
            context['business'] = self.request.user.business_profile
        except:
            context['business'] = None
        return context


class AppointmentBookingUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update appointment booking."""
    model = AppointmentBooking
    form_class = AppointmentBookingForm
    template_name = 'business/appointment_booking_form.html'
    
    def get_queryset(self):
        """Filter by user's business."""
        try:
            business = self.request.user.business_profile
            return AppointmentBooking.objects.filter(
                business=business,
                thread__user=self.request.user
            )
        except:
            return AppointmentBooking.objects.none()
    
    def get_context_data(self, **kwargs):
        """Add business context."""
        context = super().get_context_data(**kwargs)
        try:
            context['business'] = self.request.user.business_profile
        except:
            context['business'] = None
        return context
    
    def get_success_url(self):
        """Redirect to booking detail."""
        return reverse('business:appointment_booking_detail', kwargs={
            'pk': self.object.id
        })


class AppointmentBookingStatusUpdateView(ProfileRequiredMixin, AuditLogMixin, View):
    """Update appointment booking status."""
    
    def post(self, request, pk):
        """Update booking status."""
        try:
            business = request.user.business_profile
            booking = get_object_or_404(
                AppointmentBooking, 
                id=pk, 
                business=business,
                thread__user=request.user
            )
        except:
            messages.error(request, 'No business profile found.')
            return redirect('business:appointment_booking_list')
        
        new_status = request.POST.get('status')
        if new_status in ['pending', 'confirmed', 'completed', 'cancelled', 'no_show']:
            old_status = booking.status
            booking.status = new_status
            
            if new_status == 'confirmed' and old_status != 'confirmed':
                booking.confirmed_at = timezone.now()
            elif new_status == 'cancelled' and old_status != 'cancelled':
                booking.cancelled_at = timezone.now()
            
            booking.save()
            
            self.log_activity(
                'appointment_status_updated',
                business_id=str(business.id),
                booking_id=booking.id,
                old_status=old_status,
                new_status=new_status
            )
            
            messages.success(request, f'Appointment status updated to {new_status.title()}.')
        else:
            messages.error(request, 'Invalid status.')
        
        return redirect('business:appointment_booking_detail', pk=pk)


# Business Hours Management Views
class BusinessHoursListView(ProfileRequiredMixin, ListView):
    """List all business hours."""
    model = BusinessHours
    template_name = 'business/business_hours_list.html'
    context_object_name = 'business_hours'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Get business hours for the current business."""
        return BusinessHours.objects.filter(business=self.business).order_by('day_of_week')


class BusinessHoursCreateView(ProfileRequiredMixin, AuditLogMixin, CreateView):
    """Create a new business hours entry."""
    model = BusinessHours
    form_class = BusinessHoursForm
    template_name = 'business/business_hours_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Set business and save."""
        form.instance.business = self.business
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to business hours list."""
        return reverse('business:business_hours_list')


class BusinessHoursUpdateView(ProfileRequiredMixin, AuditLogMixin, UpdateView):
    """Update business hours."""
    model = BusinessHours
    form_class = BusinessHoursForm
    template_name = 'business/business_hours_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        """Get business hours object for current business."""
        return get_object_or_404(BusinessHours, pk=self.kwargs['pk'], business=self.business)
    
    def get_success_url(self):
        """Redirect to business hours list."""
        return reverse('business:business_hours_list')


class BusinessHoursDeleteView(ProfileRequiredMixin, AuditLogMixin, DeleteView):
    """Delete business hours."""
    model = BusinessHours
    template_name = 'business/business_hours_confirm_delete.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Set business context."""
        self.business = get_user_business(request.user)
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        """Get business hours object for current business."""
        return get_object_or_404(BusinessHours, pk=self.kwargs['pk'], business=self.business)
    
    def get_success_url(self):
        """Redirect to business hours list."""
        return reverse('business:business_hours_list')