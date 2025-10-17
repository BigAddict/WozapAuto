from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.utils.safestring import mark_safe
from .models import (
    NotificationLog, AIConversationLog, WebhookActivityLog, 
    ConnectionActivityLog, KnowledgeBaseActivityLog, UserActivityLog
)

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Admin interface for WhatsApp Notification Logs"""
    
    list_display = [
        'notification_type_display',
        'recipient_display',
        'recipient_user_link',
        'subject_short',
        'status_display',
        'created_at',
        'sent_at_display',
        'actions_column'
    ]
    
    list_filter = [
        'notification_type',
        'status',
        'created_at',
        'sent_at',
        'recipient_user',
    ]
    
    search_fields = [
        'recipient_phone',
        'subject',
        'recipient_user__username',
        'recipient_user__email',
        'error_message',
    ]
    
    readonly_fields = [
        'notification_type',
        'recipient_phone',
        'recipient_user',
        'subject',
        'template_used',
        'connection_used',
        'context_data_display',
        'ip_address',
        'user_agent',
        'created_at',
        'updated_at',
        'sent_at',
        'failed_at',
        'error_message',
    ]
    
    fieldsets = (
        ('Notification Details', {
            'fields': (
                'notification_type',
                'recipient_phone',
                'recipient_user',
                'subject',
                'template_used',
                'connection_used',
            )
        }),
        ('Status & Timing', {
            'fields': (
                'status',
                'created_at',
                'sent_at',
                'failed_at',
                'error_message',
            )
        }),
        ('Context & Metadata', {
            'fields': (
                'context_data_display',
                'ip_address',
                'user_agent',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def notification_type_display(self, obj):
        """Display notification type with colored badge"""
        colors = {
            'welcome': '#28a745',
            'password_reset': '#dc3545',
            'password_change': '#ffc107',
            'connection_success': '#17a2b8',
            'otp_verification': '#fd7e14',
            'system': '#6c757d',
            'other': '#6f42c1',
        }
        color = colors.get(obj.notification_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_notification_type_display()
        )
    notification_type_display.short_description = 'Type'
    notification_type_display.admin_order_field = 'notification_type'
    
    def recipient_display(self, obj):
        """Display recipient phone number"""
        if obj.recipient_phone:
            return obj.recipient_phone
        return '-'
    recipient_display.short_description = 'Recipient'
    recipient_display.admin_order_field = 'recipient_phone'
    
    def recipient_user_link(self, obj):
        """Display recipient user as a link to their admin page"""
        if obj.recipient_user:
            url = reverse('admin:auth_user_change', args=[obj.recipient_user.id])
            return format_html('<a href="{}">{}</a>', url, obj.recipient_user.username)
        return '-'
    recipient_user_link.short_description = 'User'
    recipient_user_link.admin_order_field = 'recipient_user__username'
    
    def subject_short(self, obj):
        """Display truncated subject"""
        if len(obj.subject) > 50:
            return obj.subject[:47] + '...'
        return obj.subject
    subject_short.short_description = 'Subject'
    subject_short.admin_order_field = 'subject'
    
    def status_display(self, obj):
        """Display status with colored badge"""
        colors = {
            'sent': '#28a745',
            'failed': '#dc3545',
            'pending': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def sent_at_display(self, obj):
        """Display sent time with relative time"""
        if obj.sent_at:
            return format_html(
                '<span title="{}">{}</span>',
                obj.sent_at.strftime('%Y-%m-%d %H:%M:%S'),
                obj.sent_at.strftime('%m/%d %H:%M')
            )
        return '-'
    sent_at_display.short_description = 'Sent At'
    sent_at_display.admin_order_field = 'sent_at'
    
    def context_data_display(self, obj):
        """Display context data in a readable format"""
        if obj.context_data:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.context_data, indent=2)
            )
        return '-'
    context_data_display.short_description = 'Context Data'
    
    def actions_column(self, obj):
        """Display action buttons"""
        actions = []
        
        if obj.status == 'failed' and obj.error_message:
            actions.append(
                format_html(
                    '<button type="button" class="btn btn-sm btn-outline-danger" title="View Error">'
                    '<i class="fa fa-exclamation-triangle"></i> Error</button>'
                )
            )
        
        if obj.recipient_user:
            url = reverse('admin:auth_user_change', args=[obj.recipient_user.id])
            actions.append(
                format_html(
                    '<a href="{}" class="btn btn-sm btn-outline-primary" title="View User">'
                    '<i class="fa fa-user"></i> User</a>',
                    url
                )
            )
        
        return format_html(' '.join(actions)) if actions else '-'
    actions_column.short_description = 'Actions'
    
    def has_add_permission(self, request):
        """Disable adding new notification logs through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing notification logs through admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of notification logs (for cleanup)"""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('recipient_user')
    
    class Media:
        css = {
            'all': ('admin/css/notification_log_admin.css',)
        }
        js = ('admin/js/notification_log_admin.js',)


@admin.register(AIConversationLog)
class AIConversationLogAdmin(admin.ModelAdmin):
    """Admin interface for AI Conversation Logs"""
    
    list_display = [
        'user_link', 'message_type_display', 'thread_id_short', 'model_name',
        'total_tokens', 'response_time_display', 'search_performed_display',
        'created_at'
    ]
    
    list_filter = [
        'message_type', 'model_name', 'search_performed', 'knowledge_base_used',
        'created_at', 'user'
    ]
    
    search_fields = [
        'user__username', 'user__email', 'thread_id', 'remote_jid'
    ]
    
    readonly_fields = [
        'user', 'agent', 'thread_id', 'remote_jid', 'message_type',
        'input_tokens', 'output_tokens', 'total_tokens', 'model_name',
        'response_time_ms', 'conversation_turn', 'search_performed',
        'knowledge_base_used', 'metadata_display', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'
    
    def message_type_display(self, obj):
        colors = {
            'human': '#28a745',
            'ai': '#007bff',
            'system': '#6c757d',
        }
        color = colors.get(obj.message_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_message_type_display()
        )
    message_type_display.short_description = 'Type'
    
    def thread_id_short(self, obj):
        return obj.thread_id[:20] + '...' if len(obj.thread_id) > 20 else obj.thread_id
    thread_id_short.short_description = 'Thread ID'
    
    def response_time_display(self, obj):
        if obj.response_time_ms:
            return f"{obj.response_time_ms}ms"
        return '-'
    response_time_display.short_description = 'Response Time'
    
    def search_performed_display(self, obj):
        if obj.search_performed:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    search_performed_display.short_description = 'Search'
    
    def metadata_display(self, obj):
        if obj.metadata:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return '-'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(WebhookActivityLog)
class WebhookActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for Webhook Activity Logs"""
    
    list_display = [
        'user_link', 'event_type_display', 'instance', 'remote_jid_short',
        'is_processed_display', 'response_sent_display', 'processing_time_display',
        'created_at'
    ]
    
    list_filter = [
        'event_type', 'is_processed', 'response_sent', 'is_group',
        'created_at', 'user'
    ]
    
    search_fields = [
        'user__username', 'instance', 'remote_jid', 'message_id'
    ]
    
    readonly_fields = [
        'user', 'instance', 'event_type', 'message_id', 'remote_jid',
        'is_group', 'processing_time_ms', 'is_processed', 'response_sent',
        'error_message', 'metadata_display', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def event_type_display(self, obj):
        colors = {
            'message': '#28a745',
            'status': '#007bff',
            'connection': '#ffc107',
            'error': '#dc3545',
            'other': '#6c757d',
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_event_type_display()
        )
    event_type_display.short_description = 'Event Type'
    
    def remote_jid_short(self, obj):
        return obj.remote_jid[:20] + '...' if len(obj.remote_jid) > 20 else obj.remote_jid
    remote_jid_short.short_description = 'Remote JID'
    
    def is_processed_display(self, obj):
        if obj.is_processed:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    is_processed_display.short_description = 'Processed'
    
    def response_sent_display(self, obj):
        if obj.response_sent:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    response_sent_display.short_description = 'Response Sent'
    
    def processing_time_display(self, obj):
        if obj.processing_time_ms:
            return f"{obj.processing_time_ms}ms"
        return '-'
    processing_time_display.short_description = 'Processing Time'
    
    def metadata_display(self, obj):
        if obj.metadata:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return '-'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConnectionActivityLog)
class ConnectionActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for Connection Activity Logs"""
    
    list_display = [
        'user_link', 'event_type_display', 'connection_status_display',
        'ip_address', 'created_at'
    ]
    
    list_filter = [
        'event_type', 'connection_status', 'created_at', 'user'
    ]
    
    search_fields = [
        'user__username', 'connection__instance_name', 'ip_address'
    ]
    
    readonly_fields = [
        'user', 'connection', 'event_type', 'connection_status',
        'metadata_display', 'ip_address', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def event_type_display(self, obj):
        colors = {
            'created': '#28a745',
            'connected': '#007bff',
            'disconnected': '#dc3545',
            'qr_requested': '#ffc107',
            'retry_attempted': '#fd7e14',
            'status_changed': '#6f42c1',
            'deleted': '#6c757d',
        }
        color = colors.get(obj.event_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_event_type_display()
        )
    event_type_display.short_description = 'Event Type'
    
    def connection_status_display(self, obj):
        if obj.connection_status:
            colors = {
                'open': '#28a745',
                'connecting': '#ffc107',
                'close': '#dc3545',
            }
            color = colors.get(obj.connection_status, '#6c757d')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                color, obj.connection_status.title()
            )
        return '-'
    connection_status_display.short_description = 'Status'
    
    def metadata_display(self, obj):
        if obj.metadata:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return '-'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(KnowledgeBaseActivityLog)
class KnowledgeBaseActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for Knowledge Base Activity Logs"""
    
    list_display = [
        'user_link', 'action_display', 'file_name_short', 'file_size_display',
        'processing_time_display', 'created_at'
    ]
    
    list_filter = [
        'action', 'created_at', 'user'
    ]
    
    search_fields = [
        'user__username', 'file_name', 'document_id', 'search_query'
    ]
    
    readonly_fields = [
        'user', 'document_id', 'action', 'file_name', 'file_size',
        'chunks_count', 'search_query', 'results_count', 'processing_time_ms',
        'metadata_display', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def action_display(self, obj):
        colors = {
            'upload': '#28a745',
            'delete': '#dc3545',
            'search': '#007bff',
            'chunk_created': '#ffc107',
            'embedding_created': '#6f42c1',
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_action_display()
        )
    action_display.short_description = 'Action'
    
    def file_name_short(self, obj):
        if obj.file_name:
            return obj.file_name[:30] + '...' if len(obj.file_name) > 30 else obj.file_name
        return '-'
    file_name_short.short_description = 'File Name'
    
    def file_size_display(self, obj):
        if obj.file_size:
            return self.format_file_size(obj.file_size)
        return '-'
    file_size_display.short_description = 'File Size'
    
    def processing_time_display(self, obj):
        if obj.processing_time_ms:
            return f"{obj.processing_time_ms}ms"
        return '-'
    processing_time_display.short_description = 'Processing Time'
    
    def format_file_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def metadata_display(self, obj):
        if obj.metadata:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return '-'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for User Activity Logs"""
    
    list_display = [
        'user_link', 'action_display', 'ip_address', 'created_at'
    ]
    
    list_filter = [
        'action', 'created_at', 'user'
    ]
    
    search_fields = [
        'user__username', 'ip_address', 'user_agent'
    ]
    
    readonly_fields = [
        'user', 'action', 'ip_address', 'user_agent', 'metadata_display', 'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def action_display(self, obj):
        colors = {
            'login': '#28a745',
            'logout': '#dc3545',
            'profile_update': '#007bff',
            'password_change': '#ffc107',
            'email_verification': '#17a2b8',
            'whatsapp_verification': '#28a745',
            'onboarding_completed': '#6f42c1',
            'api_access': '#fd7e14',
            'other': '#6c757d',
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_action_display()
        )
    action_display.short_description = 'Action'
    
    def metadata_display(self, obj):
        if obj.metadata:
            import json
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; font-size: 12px; max-height: 200px; overflow-y: auto;">{}</pre>',
                json.dumps(obj.metadata, indent=2)
            )
        return '-'
    metadata_display.short_description = 'Metadata'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False