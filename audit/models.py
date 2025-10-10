from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class NotificationLog(models.Model):
    """
    Model to track all WhatsApp notifications sent through the system for auditing purposes.
    """
    
    NOTIFICATION_TYPES = [
        ('welcome', 'Welcome Message'),
        ('password_reset', 'Password Reset'),
        ('password_change', 'Password Change Confirmation'),
        ('connection_success', 'WhatsApp Connection Success'),
        ('otp_verification', 'OTP Verification'),
        ('system', 'System Notification'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent Successfully'),
        ('failed', 'Failed to Send'),
        ('pending', 'Pending'),
    ]
    
    # Message details
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        help_text="Type of notification sent"
    )
    recipient_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Phone number of the recipient"
    )
    connection_used = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="WhatsApp connection instance used to send message"
    )
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who received the notification (if applicable)"
    )
    subject = models.CharField(
        max_length=255,
        help_text="Message subject line"
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the notification"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was successfully sent"
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification failed to send"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if notification failed to send"
    )
    
    # Content tracking (for audit purposes)
    template_used = models.CharField(
        max_length=100,
        blank=True,
        help_text="Message template used"
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context data used in message template"
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request that triggered the notification"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent of the request that triggered the notification"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the notification log was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the notification log was last updated"
    )
    
    class Meta:
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_type']),
            models.Index(fields=['recipient_phone']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['recipient_user']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient_phone} - {self.get_status_display()}"
    
    def mark_sent(self):
        """Mark notification as successfully sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_failed(self, error_message=""):
        """Mark notification as failed to send"""
        self.status = 'failed'
        self.failed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'failed_at', 'error_message', 'updated_at'])
    
    @property
    def is_successful(self):
        """Check if notification was sent successfully"""
        return self.status == 'sent'
    
    @property
    def is_failed(self):
        """Check if notification failed to send"""
        return self.status == 'failed'
    
    @property
    def is_pending(self):
        """Check if notification is still pending"""
        return self.status == 'pending'
    
    @classmethod
    def get_stats_by_type(cls, days=30):
        """Get notification statistics by type for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            created_at__gte=start_date
        ).values('notification_type').annotate(
            total=models.Count('id'),
            sent=models.Count('id', filter=models.Q(status='sent')),
            failed=models.Count('id', filter=models.Q(status='failed')),
            pending=models.Count('id', filter=models.Q(status='pending'))
        ).order_by('notification_type')
    
    @classmethod
    def get_daily_stats(cls, days=30):
        """Get daily notification statistics for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            created_at__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Count('id'),
            sent=Count('id', filter=models.Q(status='sent')),
            failed=Count('id', filter=models.Q(status='failed'))
        ).order_by('date')