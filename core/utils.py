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


def sanitize_business_name_to_username(business_name: str) -> str:
    """
    Sanitize business name to a valid username format.
    Converts "Binary Craft Technologies" to "binary-craft-technologies"
    
    Args:
        business_name: Business name string
        
    Returns:
        Sanitized username string
    """
    if not business_name:
        return ""
    
    # Convert to lowercase, replace spaces and special chars with hyphens
    username = business_name.lower().strip()
    # Remove special characters except spaces and hyphens
    username = ''.join(c if c.isalnum() or c in [' ', '-'] else '' for c in username)
    # Replace spaces with hyphens
    username = username.replace(' ', '-')
    # Replace multiple hyphens with single hyphen
    while '--' in username:
        username = username.replace('--', '-')
    # Remove leading/trailing hyphens
    username = username.strip('-')
    
    return username


def get_user_display_name(user: User) -> str:
    """
    Get user's display name (business name or username).
    
    Args:
        user: Django User instance
        
    Returns:
        Display name string
    """
    # Try to get business name from business profile
    try:
        business_profile = user.business_profile
        if business_profile and business_profile.name:
            return business_profile.name
    except AttributeError:
        pass
    
    # Fallback to username
    return user.username


def get_onboarding_progress(user: User) -> Dict[str, Any]:
    """
    Get onboarding progress information for a user.
    
    Args:
        user: Django User instance
        
    Returns:
        Dictionary with onboarding progress information
    """
    try:
        profile = user.profile
        # Handle legacy 'profile' step
        current_step = 'profile' if profile.onboarding_step == 'profile' else profile.onboarding_step
        return {
            'is_complete': profile.is_onboarding_complete(),
            'current_step': current_step,
            'next_url': profile.get_onboarding_redirect_url(),
            'steps': {
                'welcome': profile.onboarding_step == 'welcome',
                'business': profile.onboarding_step in ['business', 'verify', 'complete'] or profile.onboarding_step == 'profile',
                'verify': profile.onboarding_step in ['verify', 'complete'],
                'complete': profile.onboarding_step == 'complete'
            }
        }
    except UserProfile.DoesNotExist:
        return {
            'is_complete': False,
            'current_step': 'welcome',
            'next_url': '/onboarding/',
            'steps': {
                'welcome': True,
                'business': False,
                'verify': False,
                'complete': False
            }
        }


def reset_user_onboarding(user: User) -> None:
    """
    Reset user's onboarding progress to start from the beginning.
    
    Args:
        user: Django User instance
    """
    try:
        profile = user.profile
        profile.onboarding_step = 'welcome'
        profile.onboarding_completed = False
        profile.save()
        logger.info(f"Reset onboarding for user: {user.username}")
    except UserProfile.DoesNotExist:
        logger.warning(f"Profile not found for user: {user.username}")


def complete_user_onboarding(user: User) -> None:
    """
    Mark user's onboarding as complete.
    
    Args:
        user: Django User instance
    """
    try:
        profile = user.profile
        profile.onboarding_step = 'complete'
        profile.onboarding_completed = True
        profile.save()
        logger.info(f"Completed onboarding for user: {user.username}")
    except UserProfile.DoesNotExist:
        logger.warning(f"Profile not found for user: {user.username}")


def get_onboarding_step_display(step: str) -> str:
    """
    Get human-readable display name for onboarding step.
    
    Args:
        step: Onboarding step code
        
    Returns:
        Human-readable step name
    """
    step_names = {
        'welcome': 'Welcome',
        'profile': 'Personal Profile',
        'business': 'Business Profile',
        'verify': 'WhatsApp Verification',
        'complete': 'Completed'
    }
    return step_names.get(step, 'Unknown')
