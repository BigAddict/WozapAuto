"""
Business app signals.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BusinessProfile, BusinessSettings


@receiver(post_save, sender=BusinessProfile)
def create_business_settings(sender, instance, created, **kwargs):
    """Create default business settings when a business profile is created."""
    if created:
        BusinessSettings.objects.get_or_create(business=instance)
