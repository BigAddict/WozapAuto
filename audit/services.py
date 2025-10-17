"""
Audit service for centralized logging and analytics across the platform.
"""
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate

from .models import (
    AIConversationLog, WebhookActivityLog, ConnectionActivityLog,
    KnowledgeBaseActivityLog, UserActivityLog
)

User = get_user_model()


class AuditService:
    """
    Centralized service for audit logging and analytics.
    """
    
    @staticmethod
    def log_ai_conversation(
        user: User,
        agent_id: Optional[int] = None,
        thread_id: str = "",
        remote_jid: str = "",
        message_type: str = "ai",
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        conversation_turn: int = 1,
        search_performed: bool = False,
        knowledge_base_used: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AIConversationLog:
        """Log an AI conversation interaction."""
        return AIConversationLog.objects.create(
            user=user,
            agent_id=agent_id,
            thread_id=thread_id,
            remote_jid=remote_jid,
            message_type=message_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
            response_time_ms=response_time_ms,
            conversation_turn=conversation_turn,
            search_performed=search_performed,
            knowledge_base_used=knowledge_base_used,
            metadata=metadata or {}
        )
    
    @staticmethod
    def log_webhook_activity(
        user: Optional[User] = None,
        instance: str = "",
        event_type: str = "message",
        message_id: Optional[str] = None,
        remote_jid: str = "",
        is_group: bool = False,
        processing_time_ms: Optional[int] = None,
        is_processed: bool = False,
        response_sent: bool = False,
        error_message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebhookActivityLog:
        """Log webhook activity."""
        return WebhookActivityLog.objects.create(
            user=user,
            instance=instance,
            event_type=event_type,
            message_id=message_id,
            remote_jid=remote_jid,
            is_group=is_group,
            processing_time_ms=processing_time_ms,
            is_processed=is_processed,
            response_sent=response_sent,
            error_message=error_message,
            metadata=metadata or {}
        )
    
    @staticmethod
    def log_connection_event(
        user: User,
        connection_id: Optional[int] = None,
        event_type: str = "created",
        connection_status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> ConnectionActivityLog:
        """Log a connection lifecycle event."""
        return ConnectionActivityLog.objects.create(
            user=user,
            connection_id=connection_id,
            event_type=event_type,
            connection_status=connection_status,
            metadata=metadata or {},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_knowledge_base_action(
        user: User,
        action: str = "upload",
        document_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        chunks_count: Optional[int] = None,
        search_query: Optional[str] = None,
        results_count: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeBaseActivityLog:
        """Log a knowledge base operation."""
        return KnowledgeBaseActivityLog.objects.create(
            user=user,
            document_id=document_id,
            action=action,
            file_name=file_name,
            file_size=file_size,
            chunks_count=chunks_count,
            search_query=search_query,
            results_count=results_count,
            processing_time_ms=processing_time_ms,
            metadata=metadata or {}
        )
    
    @staticmethod
    def log_user_activity(
        user: User,
        action: str = "login",
        ip_address: Optional[str] = None,
        user_agent: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> UserActivityLog:
        """Log a user activity."""
        return UserActivityLog.objects.create(
            user=user,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
    
    @staticmethod
    def get_user_analytics(user: User, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get comprehensive analytics for a user within a date range."""
        # AI Conversation Analytics
        ai_stats = AIConversationLog.get_user_stats(user, days=(end_date - start_date).days)
        ai_daily = list(AIConversationLog.get_daily_stats(user=user, days=(end_date - start_date).days))
        
        # Webhook Analytics
        webhook_stats = WebhookActivityLog.get_user_stats(user, days=(end_date - start_date).days)
        
        # Connection Analytics
        connection_stats = list(ConnectionActivityLog.get_user_stats(user, days=(end_date - start_date).days))
        
        # Knowledge Base Analytics
        kb_stats = KnowledgeBaseActivityLog.get_user_stats(user, days=(end_date - start_date).days)
        
        # User Activity Analytics
        activity_stats = list(UserActivityLog.get_user_stats(user, days=(end_date - start_date).days))
        
        return {
            'ai_conversations': {
                'stats': ai_stats,
                'daily_trends': ai_daily
            },
            'webhook_activity': {
                'stats': webhook_stats
            },
            'connection_activity': {
                'events': connection_stats
            },
            'knowledge_base': {
                'stats': kb_stats
            },
            'user_activity': {
                'events': activity_stats
            },
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }
    
    @staticmethod
    def get_business_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get business analytics for admin dashboard."""
        from django.contrib.auth.models import User
        from connections.models import Connection
        from knowledgebase.models import KnowledgeBase
        
        # User metrics
        total_users = User.objects.count()
        active_users = User.objects.filter(
            last_login__gte=start_date
        ).count()
        new_users = User.objects.filter(
            date_joined__gte=start_date
        ).count()
        
        # Connection metrics
        total_connections = Connection.objects.count()
        active_connections = Connection.objects.filter(
            connection_status='open'
        ).count()
        new_connections = Connection.objects.filter(
            created_at__gte=start_date
        ).count()
        
        # AI usage metrics
        ai_stats = AIConversationLog.objects.filter(
            created_at__gte=start_date
        ).aggregate(
            total_conversations=Count('id'),
            total_tokens=Sum('total_tokens'),
            avg_response_time=Avg('response_time_ms'),
            unique_users=Count('user', distinct=True)
        )
        
        # Knowledge base metrics
        kb_stats = KnowledgeBaseActivityLog.objects.filter(
            created_at__gte=start_date
        ).aggregate(
            total_uploads=Count('id', filter=Q(action='upload')),
            total_searches=Count('id', filter=Q(action='search')),
            total_storage=Sum('file_size', filter=Q(action='upload'))
        )
        
        # Webhook metrics
        webhook_stats = WebhookActivityLog.objects.filter(
            created_at__gte=start_date
        ).aggregate(
            total_webhooks=Count('id'),
            processed_webhooks=Count('id', filter=Q(is_processed=True)),
            failed_webhooks=Count('id', filter=Q(error_message__isnull=False))
        )
        
        # Daily trends
        daily_ai = list(AIConversationLog.get_daily_stats(days=(end_date - start_date).days))
        daily_users = list(User.objects.filter(
            date_joined__gte=start_date
        ).annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            new_users=Count('id')
        ).order_by('date'))
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'new': new_users,
                'daily_growth': daily_users
            },
            'connections': {
                'total': total_connections,
                'active': active_connections,
                'new': new_connections
            },
            'ai_usage': {
                'stats': ai_stats,
                'daily_trends': daily_ai
            },
            'knowledge_base': {
                'stats': kb_stats
            },
            'webhooks': {
                'stats': webhook_stats
            },
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }
    
    @staticmethod
    def get_time_range_data(days: int = 30) -> Dict[str, datetime]:
        """Get standardized time range data."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'days': days
        }
