from django.contrib import admin

from .models import WebhookData, Agent

@admin.register(WebhookData)
class WebhookDataAdmin(admin.ModelAdmin):
    """Read-only admin for WebhookData"""
    
    list_display = [
        'message_id',
        'instance',
        'push_name',
        'remote_jid',
        'message_type',
        'from_me',
        'is_group',
        'needs_reply',
        'date_time',
        'is_processed'
    ]
    
    list_filter = [
        'instance',
        'message_type',
        'from_me',
        'is_group',
        'is_processed',
        'date_time'
    ]
    
    search_fields = [
        'message_id',
        'push_name',
        'remote_jid',
        'conversation'
    ]
    
    readonly_fields = [
        'message_id',
        'instance',
        'push_name',
        'remote_jid',
        'conversation',
        'message_type',
        'from_me',
        'is_group',
        'needs_reply',
        'quoted_message',
        'date_time',
        'is_processed',
        'response_text'
    ]
    
    ordering = ['-date_time']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(Agent)