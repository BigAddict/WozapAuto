"""
Token usage utilities for admin dashboard.
"""
from django.db.models import Sum, Count, Avg, Q
from django.contrib.auth.models import User
from .models import ConversationMessage, ConversationThread, Agent
from datetime import datetime, timedelta
from django.utils import timezone
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def get_token_statistics(user: User = None, days: int = 30) -> Dict[str, Any]:
    """
    Get comprehensive token usage statistics.
    
    Args:
        user: Specific user to get stats for (None for all users)
        days: Number of days to look back
        
    Returns:
        Dictionary with token statistics
    """
    try:
        # Date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Base queryset
        base_query = ConversationMessage.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            message_type='ai'  # Only AI messages have token usage
        )
        
        if user:
            base_query = base_query.filter(thread__user=user)
        
        # Aggregate statistics
        stats = base_query.aggregate(
            total_messages=Count('id'),
            total_input_tokens=Sum('input_tokens'),
            total_output_tokens=Sum('output_tokens'),
            total_tokens=Sum('total_tokens'),
            avg_input_tokens=Avg('input_tokens'),
            avg_output_tokens=Avg('output_tokens')
        )
        
        # Calculate average total tokens separately
        total_messages = stats['total_messages'] or 0
        total_tokens = stats['total_tokens'] or 0
        avg_total_tokens = total_tokens / total_messages if total_messages > 0 else 0
        stats['avg_total_tokens'] = avg_total_tokens
        
        # Daily breakdown
        daily_stats = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_query = base_query.filter(created_at__gte=day_start, created_at__lt=day_end)
            day_stats = day_query.aggregate(
                messages=Count('id'),
                input_tokens=Sum('input_tokens'),
                output_tokens=Sum('output_tokens'),
                total_tokens=Sum('total_tokens')
            )
            
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'messages': day_stats['messages'] or 0,
                'input_tokens': day_stats['input_tokens'] or 0,
                'output_tokens': day_stats['output_tokens'] or 0,
                'total_tokens': day_stats['total_tokens'] or 0
            })
        
        # Model breakdown
        model_stats = base_query.values('model_name').annotate(
            messages=Count('id'),
            input_tokens=Sum('input_tokens'),
            output_tokens=Sum('output_tokens'),
            total_tokens=Sum('total_tokens')
        ).order_by('-total_tokens')
        
        # User breakdown (if not filtering by specific user)
        user_stats = []
        if not user:
            user_stats = base_query.values('thread__user__username').annotate(
                messages=Count('id'),
                input_tokens=Sum('input_tokens'),
                output_tokens=Sum('output_tokens'),
                total_tokens=Sum('total_tokens')
            ).order_by('-total_tokens')[:10]  # Top 10 users
        
        return {
            'period': f'Last {days} days',
            'summary': {
                'total_messages': stats['total_messages'] or 0,
                'total_input_tokens': stats['total_input_tokens'] or 0,
                'total_output_tokens': stats['total_output_tokens'] or 0,
                'total_tokens': stats['total_tokens'] or 0,
                'avg_input_tokens': round(stats['avg_input_tokens'] or 0, 2),
                'avg_output_tokens': round(stats['avg_output_tokens'] or 0, 2),
                'avg_total_tokens': round(stats['avg_total_tokens'] or 0, 2)
            },
            'daily_breakdown': daily_stats,
            'model_breakdown': list(model_stats),
            'user_breakdown': list(user_stats)
        }
        
    except Exception as e:
        logger.error(f"Error getting token statistics: {e}")
        return {
            'error': str(e),
            'summary': {
                'total_messages': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_tokens': 0,
                'avg_input_tokens': 0,
                'avg_output_tokens': 0,
                'avg_total_tokens': 0
            },
            'daily_breakdown': [],
            'model_breakdown': [],
            'user_breakdown': []
        }

def get_user_token_summary(user: User) -> Dict[str, Any]:
    """
    Get token usage summary for a specific user.
    
    Args:
        user: User to get summary for
        
    Returns:
        Dictionary with user's token usage
    """
    try:
        # Get user's threads
        threads = ConversationThread.objects.filter(user=user)
        
        # Get all AI messages from user's threads
        messages = ConversationMessage.objects.filter(
            thread__in=threads,
            message_type='ai'
        )
        
        # Aggregate statistics
        stats = messages.aggregate(
            total_messages=Count('id'),
            total_input_tokens=Sum('input_tokens'),
            total_output_tokens=Sum('output_tokens'),
            total_tokens=Sum('total_tokens'),
            avg_input_tokens=Avg('input_tokens'),
            avg_output_tokens=Avg('output_tokens')
        )
        
        # Calculate average total tokens separately
        total_messages = stats['total_messages'] or 0
        total_tokens = stats['total_tokens'] or 0
        avg_total_tokens = total_tokens / total_messages if total_messages > 0 else 0
        stats['avg_total_tokens'] = avg_total_tokens
        
        # Recent activity (last 7 days)
        recent_date = timezone.now() - timedelta(days=7)
        recent_messages = messages.filter(created_at__gte=recent_date)
        recent_stats = recent_messages.aggregate(
            messages=Count('id'),
            tokens=Sum('total_tokens')
        )
        
        return {
            'user': user.username,
            'total': {
                'messages': stats['total_messages'] or 0,
                'input_tokens': stats['total_input_tokens'] or 0,
                'output_tokens': stats['total_output_tokens'] or 0,
                'total_tokens': stats['total_tokens'] or 0,
                'avg_input_tokens': round(stats['avg_input_tokens'] or 0, 2),
                'avg_output_tokens': round(stats['avg_output_tokens'] or 0, 2),
                'avg_total_tokens': round(stats['avg_total_tokens'] or 0, 2)
            },
            'recent': {
                'messages': recent_stats['messages'] or 0,
                'tokens': recent_stats['tokens'] or 0
            },
            'threads_count': threads.count()
        }
        
    except Exception as e:
        logger.error(f"Error getting user token summary: {e}")
        return {
            'user': user.username,
            'error': str(e),
            'total': {
                'messages': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'avg_input_tokens': 0,
                'avg_output_tokens': 0,
                'avg_total_tokens': 0
            },
            'recent': {
                'messages': 0,
                'tokens': 0
            },
            'threads_count': 0
        }

def get_top_token_users(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top users by token usage.
    
    Args:
        limit: Number of top users to return
        
    Returns:
        List of user token summaries
    """
    try:
        # Get users with their token usage
        users_with_tokens = User.objects.annotate(
            total_tokens=Sum('conversation_threads__messages__total_tokens', 
                           filter=Q(conversation_threads__messages__message_type='ai'))
        ).filter(total_tokens__gt=0).order_by('-total_tokens')[:limit]
        
        result = []
        for user in users_with_tokens:
            summary = get_user_token_summary(user)
            result.append(summary)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting top token users: {e}")
        return []
