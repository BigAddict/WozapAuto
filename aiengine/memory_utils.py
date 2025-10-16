"""
Utility functions for memory management and maintenance.
"""
import logging
from typing import List, Dict, Any
from django.contrib.auth.models import User
from django.db.models import Count, Q

from .models import ConversationThread, ConversationMessage, Agent
from .memory_service import MemoryService

logger = logging.getLogger("aiengine.memory_utils")


def cleanup_old_conversations(days_old: int = 30, keep_recent_messages: int = 50) -> Dict[str, int]:
    """
    Clean up old conversations and messages.
    
    Args:
        days_old: Number of days after which to clean up conversations
        keep_recent_messages: Number of recent messages to keep per conversation
        
    Returns:
        Dictionary with cleanup statistics
    """
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    stats = {
        'conversations_cleaned': 0,
        'messages_cleaned': 0,
        'threads_updated': 0
    }
    
    try:
        # Get old inactive threads
        old_threads = ConversationThread.objects.filter(
            updated_at__lt=cutoff_date,
            is_active=False
        )
        
        for thread in old_threads:
            # Clean up messages in old threads
            messages_to_keep = ConversationMessage.objects.filter(
                thread=thread
            ).order_by('-created_at')[:keep_recent_messages]
            
            keep_ids = set(messages_to_keep.values_list('id', flat=True))
            deleted_count = ConversationMessage.objects.filter(
                thread=thread
            ).exclude(id__in=keep_ids).delete()[0]
            
            stats['messages_cleaned'] += deleted_count
            stats['threads_updated'] += 1
            
            # If no messages left, mark thread as inactive
            if not ConversationMessage.objects.filter(thread=thread).exists():
                thread.is_active = False
                thread.save()
                stats['conversations_cleaned'] += 1
        
        logger.info(f"Memory cleanup completed: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error during memory cleanup: {e}")
        return stats


def update_all_embeddings() -> Dict[str, int]:
    """
    Update embeddings for all messages that don't have them.
    
    Returns:
        Dictionary with update statistics
    """
    stats = {
        'threads_processed': 0,
        'messages_updated': 0,
        'errors': 0
    }
    
    try:
        # Get all threads with messages that need embeddings
        threads_with_missing_embeddings = ConversationThread.objects.filter(
            messages__embedding__isnull=True
        ).distinct()
        
        for thread in threads_with_missing_embeddings:
            try:
                memory_service = MemoryService(thread)
                updated_count = memory_service.update_message_embeddings()
                stats['messages_updated'] += updated_count
                stats['threads_processed'] += 1
            except Exception as e:
                logger.error(f"Error updating embeddings for thread {thread.thread_id}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Embedding update completed: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error during embedding update: {e}")
        return stats


def get_memory_statistics() -> Dict[str, Any]:
    """
    Get comprehensive memory statistics.
    
    Returns:
        Dictionary with memory statistics
    """
    try:
        stats = {
            'total_threads': ConversationThread.objects.count(),
            'active_threads': ConversationThread.objects.filter(is_active=True).count(),
            'total_messages': ConversationMessage.objects.count(),
            'messages_with_embeddings': ConversationMessage.objects.filter(
                embedding__isnull=False
            ).count(),
            'messages_without_embeddings': ConversationMessage.objects.filter(
                embedding__isnull=True
            ).count(),
            'users_with_conversations': User.objects.filter(
                conversation_threads__isnull=False
            ).distinct().count(),
            'agents_with_conversations': Agent.objects.filter(
                conversation_threads__isnull=False
            ).distinct().count(),
        }
        
        # Add message type breakdown
        message_types = ConversationMessage.objects.values('message_type').annotate(
            count=Count('id')
        )
        stats['message_types'] = {item['message_type']: item['count'] for item in message_types}
        
        # Add recent activity (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        stats['recent_messages'] = ConversationMessage.objects.filter(
            created_at__gte=week_ago
        ).count()
        
        stats['recent_threads'] = ConversationThread.objects.filter(
            updated_at__gte=week_ago
        ).count()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting memory statistics: {e}")
        return {}


def optimize_memory_usage() -> Dict[str, Any]:
    """
    Optimize memory usage by cleaning up and updating embeddings.
    
    Returns:
        Dictionary with optimization results
    """
    results = {
        'cleanup': cleanup_old_conversations(),
        'embeddings': update_all_embeddings(),
        'statistics': get_memory_statistics()
    }
    
    logger.info(f"Memory optimization completed: {results}")
    return results


def get_user_conversation_summary(user_id: int) -> Dict[str, Any]:
    """
    Get conversation summary for a specific user.
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with user's conversation summary
    """
    try:
        user = User.objects.get(id=user_id)
        
        threads = ConversationThread.objects.filter(user=user)
        total_messages = ConversationMessage.objects.filter(thread__user=user).count()
        
        # Get most active conversations
        active_conversations = threads.annotate(
            message_count=Count('messages')
        ).order_by('-message_count')[:5]
        
        summary = {
            'user_id': user_id,
            'username': user.username,
            'total_threads': threads.count(),
            'total_messages': total_messages,
            'active_conversations': [
                {
                    'thread_id': thread.thread_id,
                    'remote_jid': thread.remote_jid,
                    'message_count': thread.message_count,
                    'last_updated': thread.updated_at
                }
                for thread in active_conversations
            ]
        }
        
        return summary
        
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return {}
    except Exception as e:
        logger.error(f"Error getting user conversation summary: {e}")
        return {}
