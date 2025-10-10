from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q

from .models import NotificationLog


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

# Create your views here.
