"""
Business app URL configuration.
"""
from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'business'

def business_redirect(request):
    """Redirect /business/ to /business/profile/"""
    return redirect('business:business_detail')

urlpatterns = [
    # Business Profile
    path('', business_redirect, name='business_list'),
    path('create/', views.BusinessCreateView.as_view(), name='business_create'),
    path('profile/', views.BusinessDetailView.as_view(), name='business_detail'),
    path('profile/edit/', views.BusinessUpdateView.as_view(), name='business_edit'),
    path('profile/delete/', views.BusinessDeleteView.as_view(), name='business_delete'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # Services
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('services/create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('services/<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('services/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    
    # Appointments
    path('appointments/', views.AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/create/', views.AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/<int:pk>/edit/', views.AppointmentUpdateView.as_view(), name='appointment_edit'),
    path('appointments/<int:pk>/delete/', views.AppointmentDeleteView.as_view(), name='appointment_delete'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Cart Management
    path('carts/', views.CartListView.as_view(), name='cart_list'),
    path('carts/<uuid:pk>/', views.CartDetailView.as_view(), name='cart_detail'),
    path('carts/<uuid:pk>/edit/', views.CartUpdateView.as_view(), name='cart_edit'),
    
    # Appointment Bookings
    path('bookings/', views.AppointmentBookingListView.as_view(), name='appointment_booking_list'),
    path('bookings/<uuid:pk>/', views.AppointmentBookingDetailView.as_view(), name='appointment_booking_detail'),
    path('bookings/<uuid:pk>/edit/', views.AppointmentBookingUpdateView.as_view(), name='appointment_booking_edit'),
    path('bookings/<uuid:pk>/status/', views.AppointmentBookingStatusUpdateView.as_view(), name='appointment_booking_status'),
    
    # Business Hours
    path('hours/', views.BusinessHoursListView.as_view(), name='business_hours_list'),
    path('hours/create/', views.BusinessHoursCreateView.as_view(), name='business_hours_create'),
    path('hours/<int:pk>/edit/', views.BusinessHoursUpdateView.as_view(), name='business_hours_edit'),
    path('hours/<int:pk>/delete/', views.BusinessHoursDeleteView.as_view(), name='business_hours_delete'),
]
