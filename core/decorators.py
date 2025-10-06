from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def verified_email_required(view_func):
    """
    Decorator that requires user to be authenticated and have verified email.
    Redirects to verification notice page if email is not verified.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('signin')
        
        # Check if email is verified
        try:
            if not request.user.profile.is_verified:
                messages.warning(
                    request, 
                    'Please verify your email address to access this feature.'
                )
                return redirect('verification_required')
        except AttributeError:
            # Profile doesn't exist, redirect to verification
            messages.warning(
                request, 
                'Please verify your email address to access this feature.'
            )
            return redirect('verification_required')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def onboarding_required(view_func):
    """
    Decorator that requires user to complete onboarding.
    Redirects to welcome onboarding if not completed.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('signin')
        
        # Check if onboarding is completed
        try:
            if not request.user.profile.onboarding_completed:
                messages.info(
                    request, 
                    'Please complete your profile setup to continue.'
                )
                return redirect('welcome_onboarding')
        except AttributeError:
            # Profile doesn't exist, redirect to onboarding
            messages.info(
                request, 
                'Please complete your profile setup to continue.'
            )
            return redirect('welcome_onboarding')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
