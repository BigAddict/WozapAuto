from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class EmailLog(models.Model):
    """
    Model to track all emails sent through the system for auditing purposes.
    """
    
    EMAIL_TYPES = [
        ('welcome', 'Welcome Email'),
        ('password_reset', 'Password Reset'),
        ('password_change', 'Password Change Confirmation'),
        ('connection_success', 'WhatsApp Connection Success'),
        ('system', 'System Notification'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent Successfully'),
        ('failed', 'Failed to Send'),
        ('pending', 'Pending'),
    ]
    
    # Email details
    email_type = models.CharField(
        max_length=20,
        choices=EMAIL_TYPES,
        help_text="Type of email sent"
    )
    recipient_email = models.EmailField(
        help_text="Email address of the recipient"
    )
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who received the email (if applicable)"
    )
    subject = models.CharField(
        max_length=255,
        help_text="Email subject line"
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the email"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email was successfully sent"
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email failed to send"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if email failed to send"
    )
    
    # Content tracking (for audit purposes)
    template_used = models.CharField(
        max_length=100,
        blank=True,
        help_text="Email template used"
    )
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context data used in email template"
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request that triggered the email"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent of the request that triggered the email"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the email log was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the email log was last updated"
    )
    
    class Meta:
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email_type']),
            models.Index(fields=['recipient_email']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['recipient_user']),
        ]
    
    def __str__(self):
        return f"{self.get_email_type_display()} to {self.recipient_email} - {self.get_status_display()}"
    
    def mark_sent(self):
        """Mark email as successfully sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_failed(self, error_message=""):
        """Mark email as failed to send"""
        self.status = 'failed'
        self.failed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'failed_at', 'error_message', 'updated_at'])
    
    @property
    def is_successful(self):
        """Check if email was sent successfully"""
        return self.status == 'sent'
    
    @property
    def is_failed(self):
        """Check if email failed to send"""
        return self.status == 'failed'
    
    @property
    def is_pending(self):
        """Check if email is still pending"""
        return self.status == 'pending'
    
    @classmethod
    def get_stats_by_type(cls, days=30):
        """Get email statistics by type for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            created_at__gte=start_date
        ).values('email_type').annotate(
            total=models.Count('id'),
            sent=models.Count('id', filter=models.Q(status='sent')),
            failed=models.Count('id', filter=models.Q(status='failed')),
            pending=models.Count('id', filter=models.Q(status='pending'))
        ).order_by('email_type')
    
    @classmethod
    def get_daily_stats(cls, days=30):
        """Get daily email statistics for the last N days"""
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