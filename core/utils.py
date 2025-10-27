"""
Core utility functions for common operations.
"""
import logging
from typing import Optional, Dict, Any
from django.contrib.auth.models import User
from django.http import HttpRequest
from audit.services import AuditService
from .models import UserProfile

logger = logging.getLogger('core.utils')


def get_or_create_profile(user: User) -> UserProfile:
    """
    Get or create user profile - replaces repeated UserProfile.objects.get_or_create pattern.
    
    Args:
        user: Django User instance
        
    Returns:
        UserProfile instance
    """
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created:
        logger.info(f"Created new profile for user: {user.username}")
    return profile


def log_user_activity(user: User, action: str, request: HttpRequest, **metadata) -> None:
    """
    Simplified wrapper around AuditService.log_user_activity().
    
    Args:
        user: Django User instance
        action: Action being performed
        request: HttpRequest instance
        **metadata: Additional metadata to log
    """
    try:
        AuditService.log_user_activity(
            user=user,
            action=action,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata=metadata
        )
        logger.debug(f"Logged activity: {action} for user {user.username}")
    except Exception as e:
        logger.error(f"Failed to log user activity: {e}")


def normalize_string_field(value: Optional[str]) -> Optional[str]:
    """
    Normalize string field by stripping whitespace.
    
    Args:
        value: String value to normalize
        
    Returns:
        Normalized string or None
    """
    if value:
        return value.strip()
    return value


def get_user_display_name(user: User) -> str:
    """
    Get user's display name (full name or username).
    
    Args:
        user: Django User instance
        
    Returns:
        Display name string
    """
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    else:
        return user.username
