from django.contrib import admin
from django.contrib import messages as django_messages
from django.db import transaction
from django.utils.html import format_html

from .models import WebhookData, Agent, ConversationThread, ConversationMessage

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


@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    """Admin interface for conversation threads with bulk actions"""
    
    list_display = [
        'thread_id_short',
        'user',
        'agent',
        'remote_jid_short',
        'message_count',
        'is_active',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'is_active',
        'created_at',
        'updated_at',
        'user',
        'agent'
    ]
    
    search_fields = [
        'thread_id',
        'remote_jid',
        'user__username',
        'user__email'
    ]
    
    readonly_fields = [
        'thread_id',
        'created_at',
        'updated_at',
        'message_count_detail'
    ]
    
    ordering = ['-updated_at']
    
    actions = [
        'delete_selected_threads',
        'clear_all_messages',
        'clear_keep_10_recent',
        'clear_keep_50_recent',
        'mark_inactive',
        'mark_active'
    ]
    
    def thread_id_short(self, obj):
        """Display shortened thread ID"""
        return f"{obj.thread_id[:20]}..." if len(obj.thread_id) > 20 else obj.thread_id
    thread_id_short.short_description = 'Thread ID'
    
    def remote_jid_short(self, obj):
        """Display shortened remote JID"""
        return f"{obj.remote_jid[:30]}..." if len(obj.remote_jid) > 30 else obj.remote_jid
    remote_jid_short.short_description = 'Remote JID'
    
    def message_count(self, obj):
        """Display message count"""
        count = ConversationMessage.objects.filter(thread=obj).count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    message_count.short_description = 'Messages'
    
    def message_count_detail(self, obj):
        """Display detailed message breakdown"""
        human = ConversationMessage.objects.filter(thread=obj, message_type='human').count()
        ai = ConversationMessage.objects.filter(thread=obj, message_type='ai').count()
        system = ConversationMessage.objects.filter(thread=obj, message_type='system').count()
        total = human + ai + system
        
        return format_html(
            '<div>'
            '<strong>Total:</strong> {} messages<br>'
            '<strong>Human:</strong> {} | <strong>AI:</strong> {} | <strong>System:</strong> {}'
            '</div>',
            total, human, ai, system
        )
    message_count_detail.short_description = 'Message Breakdown'
    
    @admin.action(description='🗑️ Delete selected threads (with all messages)')
    def delete_selected_threads(self, request, queryset):
        """Delete selected threads and all their messages"""
        thread_count = queryset.count()
        total_messages = sum(
            ConversationMessage.objects.filter(thread=thread).count() 
            for thread in queryset
        )
        
        with transaction.atomic():
            queryset.delete()
        
        self.message_user(
            request,
            f'Successfully deleted {thread_count} thread(s) with {total_messages} total messages.',
            django_messages.SUCCESS
        )
    
    @admin.action(description='🧹 Clear ALL messages from selected threads')
    def clear_all_messages(self, request, queryset):
        """Delete all messages from selected threads"""
        total_deleted = 0
        
        with transaction.atomic():
            for thread in queryset:
                deleted = ConversationMessage.objects.filter(thread=thread).delete()[0]
                total_deleted += deleted
        
        self.message_user(
            request,
            f'Cleared {total_deleted} messages from {queryset.count()} thread(s).',
            django_messages.SUCCESS
        )
    
    @admin.action(description='🧹 Clear messages (keep 10 most recent)')
    def clear_keep_10_recent(self, request, queryset):
        """Clear messages keeping 10 most recent per thread"""
        total_deleted = self._clear_messages_keep_recent(queryset, 10)
        
        self.message_user(
            request,
            f'Cleared {total_deleted} messages from {queryset.count()} thread(s) (kept 10 most recent per thread).',
            django_messages.SUCCESS
        )
    
    @admin.action(description='🧹 Clear messages (keep 50 most recent)')
    def clear_keep_50_recent(self, request, queryset):
        """Clear messages keeping 50 most recent per thread"""
        total_deleted = self._clear_messages_keep_recent(queryset, 50)
        
        self.message_user(
            request,
            f'Cleared {total_deleted} messages from {queryset.count()} thread(s) (kept 50 most recent per thread).',
            django_messages.SUCCESS
        )
    
    def _clear_messages_keep_recent(self, queryset, keep_count):
        """Helper method to clear messages keeping N most recent"""
        total_deleted = 0
        
        with transaction.atomic():
            for thread in queryset:
                messages = ConversationMessage.objects.filter(thread=thread).order_by('-created_at')
                total = messages.count()
                
                if total > keep_count:
                    # Get IDs of messages to keep
                    keep_ids = list(messages[:keep_count].values_list('id', flat=True))
                    # Delete messages not in keep list
                    deleted = ConversationMessage.objects.filter(thread=thread).exclude(id__in=keep_ids).delete()[0]
                    total_deleted += deleted
        
        return total_deleted
    
    @admin.action(description='⏸️ Mark as inactive')
    def mark_inactive(self, request, queryset):
        """Mark selected threads as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Marked {updated} thread(s) as inactive.',
            django_messages.SUCCESS
        )
    
    @admin.action(description='▶️ Mark as active')
    def mark_active(self, request, queryset):
        """Mark selected threads as active"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Marked {updated} thread(s) as active.',
            django_messages.SUCCESS
        )


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    """Admin interface for conversation messages with filtering and actions"""
    
    list_display = [
        'id',
        'thread_info',
        'message_type',
        'content_preview',
        'has_embedding',
        'token_info',
        'created_at'
    ]
    
    list_filter = [
        'message_type',
        'created_at',
        'model_name',
        'thread__user'
    ]
    
    search_fields = [
        'content',
        'thread__thread_id',
        'thread__remote_jid',
        'thread__user__username'
    ]
    
    readonly_fields = [
        'thread',
        'message_type',
        'content',
        'embedding',
        'metadata',
        'created_at',
        'token_details'
    ]
    
    ordering = ['-created_at']
    
    actions = [
        'delete_selected_messages',
        'delete_human_messages',
        'delete_ai_messages',
        'delete_system_messages'
    ]
    
    def thread_info(self, obj):
        """Display thread information"""
        return format_html(
            '<div><strong>User:</strong> {}<br><strong>JID:</strong> {}</div>',
            obj.thread.user.username,
            obj.thread.remote_jid[:30] + '...' if len(obj.thread.remote_jid) > 30 else obj.thread.remote_jid
        )
    thread_info.short_description = 'Thread'
    
    def content_preview(self, obj):
        """Display content preview"""
        preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        return format_html('<div style="max-width: 300px; white-space: pre-wrap;">{}</div>', preview)
    content_preview.short_description = 'Content'
    
    def has_embedding(self, obj):
        """Check if message has embedding"""
        if obj.embedding and len(obj.embedding) > 0:
            return format_html('<span style="color: green;">✓ ({} dims)</span>', len(obj.embedding))
        return format_html('<span style="color: red;">✗</span>')
    has_embedding.short_description = 'Embedding'
    
    def token_info(self, obj):
        """Display token usage"""
        if obj.total_tokens:
            return format_html(
                '<div><strong>{}</strong> tokens<br>({} in / {} out)</div>',
                obj.total_tokens,
                obj.input_tokens or 0,
                obj.output_tokens or 0
            )
        return '-'
    token_info.short_description = 'Tokens'
    
    def token_details(self, obj):
        """Display detailed token information"""
        if not obj.total_tokens:
            return 'No token data'
        
        return format_html(
            '<div>'
            '<strong>Model:</strong> {}<br>'
            '<strong>Input tokens:</strong> {}<br>'
            '<strong>Output tokens:</strong> {}<br>'
            '<strong>Total tokens:</strong> {}'
            '</div>',
            obj.model_name or 'Unknown',
            obj.input_tokens or 0,
            obj.output_tokens or 0,
            obj.total_tokens
        )
    token_details.short_description = 'Token Details'
    
    @admin.action(description='🗑️ Delete selected messages')
    def delete_selected_messages(self, request, queryset):
        """Delete selected messages"""
        count = queryset.count()
        
        with transaction.atomic():
            queryset.delete()
        
        self.message_user(
            request,
            f'Successfully deleted {count} message(s).',
            django_messages.SUCCESS
        )
    
    @admin.action(description='🗑️ Delete human messages from selected')
    def delete_human_messages(self, request, queryset):
        """Delete only human messages from selection"""
        human_messages = queryset.filter(message_type='human')
        count = human_messages.count()
        
        with transaction.atomic():
            human_messages.delete()
        
        self.message_user(
            request,
            f'Deleted {count} human message(s).',
            django_messages.SUCCESS
        )
    
    @admin.action(description='🗑️ Delete AI messages from selected')
    def delete_ai_messages(self, request, queryset):
        """Delete only AI messages from selection"""
        ai_messages = queryset.filter(message_type='ai')
        count = ai_messages.count()
        
        with transaction.atomic():
            ai_messages.delete()
        
        self.message_user(
            request,
            f'Deleted {count} AI message(s).',
            django_messages.SUCCESS
        )
    
    @admin.action(description='🗑️ Delete system messages from selected')
    def delete_system_messages(self, request, queryset):
        """Delete only system messages from selection"""
        system_messages = queryset.filter(message_type='system')
        count = system_messages.count()
        
        with transaction.atomic():
            system_messages.delete()
        
        self.message_user(
            request,
            f'Deleted {count} system message(s).',
            django_messages.SUCCESS
        )
    
    def has_add_permission(self, request):
        """Prevent adding messages through admin"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Make messages read-only"""
        return False


admin.site.register(Agent)