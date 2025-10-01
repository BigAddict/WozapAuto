from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import EmailLog

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Admin interface for Email Logs"""
    
    list_display = [
        'email_type_display',
        'recipient_email',
        'recipient_user_link',
        'subject_short',
        'status_display',
        'created_at',
        'sent_at_display',
        'actions_column'
    ]
    
    list_filter = [
        'email_type',
        'status',
        'created_at',
        'sent_at',
        'recipient_user',
    ]
    
    search_fields = [
        'recipient_email',
        'subject',
        'recipient_user__username',
        'recipient_user__email',
        'error_message',
    ]
    
    readonly_fields = [
        'email_type',
        'recipient_email',
        'recipient_user',
        'subject',
        'template_used',
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
        ('Email Details', {
            'fields': (
                'email_type',
                'recipient_email',
                'recipient_user',
                'subject',
                'template_used',
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
    
    def email_type_display(self, obj):
        """Display email type with colored badge"""
        colors = {
            'welcome': '#28a745',
            'password_reset': '#dc3545',
            'password_change': '#ffc107',
            'connection_success': '#17a2b8',
            'system': '#6c757d',
            'other': '#6f42c1',
        }
        color = colors.get(obj.email_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_email_type_display()
        )
    email_type_display.short_description = 'Type'
    email_type_display.admin_order_field = 'email_type'
    
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
        """Disable adding new email logs through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing email logs through admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of email logs (for cleanup)"""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('recipient_user')
    
    class Media:
        css = {
            'all': ('admin/css/email_log_admin.css',)
        }
        js = ('admin/js/email_log_admin.js',)