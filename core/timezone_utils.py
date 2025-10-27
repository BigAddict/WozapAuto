"""
Timezone utilities using zoneinfo (Python 3.9+ standard library).
"""
import zoneinfo
from typing import List, Tuple, Optional
from django.contrib.auth.models import User
from django.utils import timezone as django_timezone

# Common timezones for better UX
COMMON_TIMEZONES = [
    # Africa
    'Africa/Cairo',
    'Africa/Johannesburg', 
    'Africa/Lagos',
    'Africa/Nairobi',
    
    # Americas
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Toronto',
    'America/Sao_Paulo',
    'America/Mexico_City',
    
    # Asia
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Asia/Kolkata',
    'Asia/Dubai',
    'Asia/Singapore',
    'Asia/Seoul',
    
    # Europe
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Europe/Rome',
    'Europe/Madrid',
    'Europe/Moscow',
    
    # Oceania
    'Australia/Sydney',
    'Australia/Melbourne',
    'Pacific/Auckland',
    
    # UTC
    'UTC',
]


def get_all_timezones() -> List[str]:
    """
    Get all available timezones.
    
    Returns:
        List of timezone strings
    """
    return sorted(zoneinfo.available_timezones())


def get_common_timezones() -> List[str]:
    """
    Get curated list of common timezones.
    
    Returns:
        List of common timezone strings
    """
    return COMMON_TIMEZONES


def format_timezone_choices() -> List[Tuple[str, str]]:
    """
    Format timezones for Django form choices.
    
    Returns:
        List of (timezone, display_name) tuples
    """
    choices = []
    
    # Add common timezones first
    for tz in COMMON_TIMEZONES:
        try:
            zone = zoneinfo.ZoneInfo(tz)
            display_name = f"{tz} ({zone.tzname(django_timezone.now())})"
            choices.append((tz, display_name))
        except Exception:
            # Skip invalid timezones
            continue
    
    # Add separator
    choices.append(('', '──────────────'))
    
    # Add all other timezones
    all_timezones = get_all_timezones()
    for tz in all_timezones:
        if tz not in COMMON_TIMEZONES:
            try:
                zone = zoneinfo.ZoneInfo(tz)
                display_name = f"{tz} ({zone.tzname(django_timezone.now())})"
                choices.append((tz, display_name))
            except Exception:
                # Skip invalid timezones
                continue
    
    return choices


def get_user_timezone(user: User) -> Optional[zoneinfo.ZoneInfo]:
    """
    Get user's timezone as zoneinfo.ZoneInfo object.
    
    Args:
        user: Django User instance
        
    Returns:
        ZoneInfo object or None
    """
    try:
        profile = user.profile
        if profile.timezone:
            return zoneinfo.ZoneInfo(profile.timezone)
    except Exception as e:
        print(f"Error getting user timezone: {e}")
    
    return None


def get_timezone_display_name(timezone_str: str) -> str:
    """
    Get display name for a timezone.
    
    Args:
        timezone_str: Timezone string
        
    Returns:
        Display name string
    """
    try:
        zone = zoneinfo.ZoneInfo(timezone_str)
        return f"{timezone_str} ({zone.tzname(django_timezone.now())})"
    except Exception:
        return timezone_str


def is_valid_timezone(timezone_str: str) -> bool:
    """
    Check if timezone string is valid.
    
    Args:
        timezone_str: Timezone string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        zoneinfo.ZoneInfo(timezone_str)
        return True
    except Exception:
        return False
