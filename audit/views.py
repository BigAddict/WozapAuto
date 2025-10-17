from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import NotificationLog
from .services import AuditService


@login_required
def notifications_list(request):
    """List notifications for the logged-in user.
    Admin users see all notifications; others see only their own.
    """
    if request.user.is_superuser:
        notifications_qs = NotificationLog.objects.all()
    else:
        notifications_qs = NotificationLog.objects.filter(
            Q(recipient_user=request.user) | Q(recipient_phone=getattr(request.user.profile, 'phone_number', None))
        )

    notifications = notifications_qs.order_by('-created_at')

    context = {
        'notifications': notifications,
        'is_admin': request.user.is_superuser,
    }
    return render(request, 'audit/notifications.html', context)


@login_required
def analytics_dashboard(request):
    """User analytics dashboard with time-based filtering."""
    # Get time range from request
    days = int(request.GET.get('days', 30))
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Convert to timezone-aware datetime
            start_date = timezone.make_aware(start_date)
            end_date = timezone.make_aware(end_date)
        except ValueError:
            # Fallback to default range
            time_range = AuditService.get_time_range_data(days)
            start_date = time_range['start_date']
            end_date = time_range['end_date']
    else:
        time_range = AuditService.get_time_range_data(days)
        start_date = time_range['start_date']
        end_date = time_range['end_date']
    
    # Get user analytics
    analytics_data = AuditService.get_user_analytics(request.user, start_date, end_date)
    
    # Prepare context for template
    context = {
        'analytics': analytics_data,
        'selected_days': days,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'is_admin': request.user.is_superuser,
    }
    
    return render(request, 'audit/analytics_dashboard.html', context)


@login_required
def analytics_api(request):
    """API endpoint for analytics data (for AJAX requests)."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Get time range from request
    days = int(request.GET.get('days', 30))
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            start_date = timezone.make_aware(start_date)
            end_date = timezone.make_aware(end_date)
        except ValueError:
            time_range = AuditService.get_time_range_data(days)
            start_date = time_range['start_date']
            end_date = time_range['end_date']
    else:
        time_range = AuditService.get_time_range_data(days)
        start_date = time_range['start_date']
        end_date = time_range['end_date']
    
    # Get analytics data
    if request.user.is_superuser:
        # Admin gets business analytics
        analytics_data = AuditService.get_business_analytics(start_date, end_date)
    else:
        # Regular users get their personal analytics
        analytics_data = AuditService.get_user_analytics(request.user, start_date, end_date)
    
    return JsonResponse(analytics_data, safe=False)

# Create your views here.
