from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

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
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the in-app notification has been read"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the notification was read in-app"
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

    def mark_read(self, commit=True):
        """Mark notification as read in the UI."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            if commit:
                self.save(update_fields=['is_read', 'read_at', 'updated_at'])
        return self
    
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


class AIConversationLog(models.Model):
    """
    Model to track all AI conversation interactions for analytics and auditing.
    """
    
    MESSAGE_TYPES = [
        ('human', 'Human Message'),
        ('ai', 'AI Response'),
        ('system', 'System Message'),
    ]
    
    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_conversation_logs')
    agent = models.ForeignKey('aiengine.Agent', on_delete=models.SET_NULL, null=True, blank=True)
    thread_id = models.CharField(max_length=255, db_index=True, help_text="Conversation thread ID")
    remote_jid = models.CharField(max_length=255, help_text="WhatsApp contact/group ID")
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    
    # Token usage tracking
    input_tokens = models.IntegerField(null=True, blank=True, help_text="Number of input tokens used")
    output_tokens = models.IntegerField(null=True, blank=True, help_text="Number of output tokens generated")
    total_tokens = models.IntegerField(null=True, blank=True, help_text="Total tokens used (input + output)")
    model_name = models.CharField(max_length=100, null=True, blank=True, help_text="Model used for this message")
    
    # Performance metrics
    response_time_ms = models.IntegerField(null=True, blank=True, help_text="Response time in milliseconds")
    conversation_turn = models.IntegerField(default=1, help_text="Turn number in conversation")
    
    # Feature usage tracking
    search_performed = models.BooleanField(default=False, help_text="Whether knowledge base search was performed")
    knowledge_base_used = models.BooleanField(default=False, help_text="Whether knowledge base was used in response")
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "AI Conversation Log"
        verbose_name_plural = "AI Conversation Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['thread_id', 'created_at']),
            models.Index(fields=['message_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_message_type_display()} - {self.user.username} - {self.created_at}"
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Get conversation statistics for a user over the last N days"""
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            created_at__gte=start_date
        ).aggregate(
            total_conversations=models.Count('id'),
            total_tokens=models.Sum('total_tokens'),
            avg_response_time=models.Avg('response_time_ms'),
            knowledge_base_searches=models.Count('id', filter=models.Q(search_performed=True))
        )
    
    @classmethod
    def get_daily_stats(cls, user=None, days=30):
        """Get daily conversation statistics"""
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncDate
        
        start_date = timezone.now() - timedelta(days=days)
        queryset = cls.objects.filter(created_at__gte=start_date)
        
        if user:
            queryset = queryset.filter(user=user)
        
        return queryset.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            conversations=Count('id'),
            total_tokens=Sum('total_tokens'),
            avg_response_time=models.Avg('response_time_ms')
        ).order_by('date')


class WebhookActivityLog(models.Model):
    """
    Model to track all webhook activity for analytics and auditing.
    """
    
    EVENT_TYPES = [
        ('message', 'Message Received'),
        ('status', 'Status Update'),
        ('connection', 'Connection Event'),
        ('error', 'Error Event'),
        ('other', 'Other'),
    ]
    
    # Core fields
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    instance = models.CharField(max_length=255, help_text="WhatsApp instance ID")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    message_id = models.CharField(max_length=255, null=True, blank=True)
    remote_jid = models.CharField(max_length=255, help_text="WhatsApp contact/group ID")
    is_group = models.BooleanField(default=False)
    
    # Processing metrics
    processing_time_ms = models.IntegerField(null=True, blank=True, help_text="Processing time in milliseconds")
    is_processed = models.BooleanField(default=False)
    response_sent = models.BooleanField(default=False, help_text="Whether a response was sent")
    error_message = models.TextField(blank=True, help_text="Error message if processing failed")
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional webhook metadata")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Webhook Activity Log"
        verbose_name_plural = "Webhook Activity Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['instance', 'created_at']),
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.instance} - {self.created_at}"
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Get webhook statistics for a user over the last N days"""
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            created_at__gte=start_date
        ).aggregate(
            total_webhooks=models.Count('id'),
            processed_webhooks=models.Count('id', filter=models.Q(is_processed=True)),
            failed_webhooks=models.Count('id', filter=models.Q(error_message__isnull=False)),
            avg_processing_time=models.Avg('processing_time_ms')
        )


class ConnectionActivityLog(models.Model):
    """
    Model to track connection lifecycle events for analytics and auditing.
    """
    
    EVENT_TYPES = [
        ('created', 'Connection Created'),
        ('connected', 'Connection Established'),
        ('disconnected', 'Connection Lost'),
        ('qr_requested', 'QR Code Requested'),
        ('retry_attempted', 'Retry Attempted'),
        ('status_changed', 'Status Changed'),
        ('deleted', 'Connection Deleted'),
    ]
    
    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connection_logs')
    connection = models.ForeignKey('connections.Connection', on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    connection_status = models.CharField(max_length=20, null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional event metadata")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Connection Activity Log"
        verbose_name_plural = "Connection Activity Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['connection', 'created_at']),
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.user.username} - {self.created_at}"
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Get connection activity statistics for a user over the last N days"""
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            created_at__gte=start_date
        ).values('event_type').annotate(
            count=models.Count('id')
        ).order_by('event_type')


class KnowledgeBaseActivityLog(models.Model):
    """
    Model to track knowledge base operations for analytics and auditing.
    """
    
    ACTION_TYPES = [
        ('upload', 'Document Uploaded'),
        ('delete', 'Document Deleted'),
        ('search', 'Knowledge Base Search'),
        ('chunk_created', 'Document Chunked'),
        ('embedding_created', 'Embedding Generated'),
    ]
    
    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_base_logs')
    document_id = models.CharField(max_length=255, null=True, blank=True, help_text="Document identifier")
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    chunks_count = models.IntegerField(null=True, blank=True, help_text="Number of chunks created")
    
    # Search-specific fields
    search_query = models.TextField(null=True, blank=True, help_text="Search query used")
    results_count = models.IntegerField(null=True, blank=True, help_text="Number of results returned")
    
    # Performance metrics
    processing_time_ms = models.IntegerField(null=True, blank=True, help_text="Processing time in milliseconds")
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Knowledge Base Activity Log"
        verbose_name_plural = "Knowledge Base Activity Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['document_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user.username} - {self.created_at}"
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Get knowledge base statistics for a user over the last N days"""
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            created_at__gte=start_date
        ).aggregate(
            total_uploads=models.Count('id', filter=models.Q(action='upload')),
            total_searches=models.Count('id', filter=models.Q(action='search')),
            total_documents=models.Count('document_id', distinct=True, filter=models.Q(action='upload')),
            total_storage=models.Sum('file_size', filter=models.Q(action='upload'))
        )


class UserActivityLog(models.Model):
    """
    Model to track general user activities for analytics and auditing.
    """
    
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('profile_update', 'Profile Updated'),
        ('password_change', 'Password Changed'),
        ('email_verification', 'Email Verified'),
        ('whatsapp_verification', 'WhatsApp Verified'),
        ('onboarding_completed', 'Onboarding Completed'),
        ('api_access', 'API Access'),
        ('other', 'Other'),
    ]
    
    # Core fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=25, choices=ACTION_TYPES)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional activity metadata")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "User Activity Log"
        verbose_name_plural = "User Activity Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user.username} - {self.created_at}"
    
    @classmethod
    def get_user_stats(cls, user, days=30):
        """Get user activity statistics over the last N days"""
        start_date = timezone.now() - timedelta(days=days)
        
        return cls.objects.filter(
            user=user,
            created_at__gte=start_date
        ).values('action').annotate(
            count=models.Count('id')
        ).order_by('action')