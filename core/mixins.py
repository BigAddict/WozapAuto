"""
Django mixins for common view functionality.
"""
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile
from .utils import log_user_activity

logger = logging.getLogger('core.mixins')


class ProfileRequiredMixin(LoginRequiredMixin):
    """
    Mixin that ensures user has a profile and has completed onboarding.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has profile and completed onboarding."""
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        try:
            profile = request.user.profile
            if not profile.is_onboarding_complete():
                messages.info(request, 'Please complete your profile setup to continue.')
                return redirect(profile.get_onboarding_redirect_url())
        except UserProfile.DoesNotExist:
            messages.info(request, 'Please complete your profile setup to continue.')
            return redirect('onboarding_welcome')
        
        return super().dispatch(request, *args, **kwargs)


class BusinessProfileRequiredMixin(ProfileRequiredMixin):
    """
    Mixin that ensures user has a business profile.
    Extends ProfileRequiredMixin to also check for business profile.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has business profile before proceeding."""
        # First check profile and onboarding (from ProfileRequiredMixin)
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(response, 'status_code') and response.status_code in [301, 302]:
            return response
        
        # Then check for business profile
        try:
            business_profile = request.user.business_profile
        except AttributeError:
            # Business profile doesn't exist
            messages.info(request, 'Please create your business profile to continue.')
            return redirect('onboarding_business')
        
        # If we get here, both profile and business profile exist, proceed with the view
        return super(ProfileRequiredMixin, self).dispatch(request, *args, **kwargs)


class AuditLogMixin:
    """
    Mixin that automatically logs user activities.
    """
    
    def log_activity(self, action: str, **metadata):
        """
        Log user activity with automatic request context.
        
        Args:
            action: Action being performed
            **metadata: Additional metadata to log
        """
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            log_user_activity(
                user=self.request.user,
                action=action,
                request=self.request,
                **metadata
            )
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add request to instance."""
        self.request = request
        return super().dispatch(request, *args, **kwargs)
