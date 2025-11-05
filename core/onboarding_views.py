from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
import logging

from .models import UserProfile
from .forms import BusinessProfileForm, OTPVerificationForm
from business.models import BusinessProfile
from .whatsapp_service import whatsapp_service
from audit.services import AuditService

logger = logging.getLogger('core.onboarding')


@login_required
def onboarding_welcome(request):
    """Welcome page for onboarding process"""
    try:
        profile = request.user.profile
        
        # If already completed, redirect to home
        if profile.is_onboarding_complete():
            messages.info(request, 'You have already completed the onboarding process.')
            return redirect('home')
        
        # If not on welcome step, redirect to current step
        if profile.onboarding_step != 'welcome':
            return redirect(profile.get_onboarding_redirect_url())
        
        return render(request, 'core/onboarding/welcome.html')
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def onboarding_profile(request):
    """Legacy profile step - redirects to business onboarding"""
    try:
        profile = request.user.profile
        # Update step and redirect to business
        if profile.onboarding_step == 'profile':
            profile.onboarding_step = 'business'
            profile.save(update_fields=['onboarding_step'])
        return redirect('onboarding_business')
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def onboarding_business(request):
    """Step 2: Business profile creation"""
    try:
        profile = request.user.profile
        
        # If already completed, redirect to home
        if profile.is_onboarding_complete():
            messages.info(request, 'You have already completed the onboarding process.')
            return redirect('home')
        
        # Handle legacy 'profile' step by redirecting to business
        if profile.onboarding_step == 'profile':
            profile.onboarding_step = 'business'
            profile.save(update_fields=['onboarding_step'])
        
        # Redirect if not on business step
        if profile.onboarding_step not in ['welcome', 'business']:
            # If on verify step but no business profile exists, allow access
            if profile.onboarding_step == 'verify':
                try:
                    request.user.business_profile
                    # Business profile exists, redirect to verify
                    return redirect('onboarding_verify')
                except AttributeError:
                    # No business profile, allow access to business step
                    pass
            else:
                return redirect(profile.get_onboarding_redirect_url())
        
        # Check if business profile already exists
        try:
            business_profile = request.user.business_profile
            if business_profile.is_verified:
                # Already verified, mark complete
                profile.onboarding_step = 'complete'
                profile.onboarding_completed = True
                profile.save()
                messages.info(request, 'Your business profile is already verified.')
                return redirect('home')
            # If exists but not verified, redirect to verification
            return redirect('onboarding_verify')
        except AttributeError:
            # Business profile doesn't exist, continue with creation
            pass
        
        if request.method == 'POST':
            form = BusinessProfileForm(request.POST, user=request.user)
            if form.is_valid():
                # Create business profile
                business_profile = form.save(commit=False)
                business_profile.user = request.user
                # Auto-populate email from user if not provided
                if not business_profile.email:
                    business_profile.email = request.user.email
                business_profile.save()
                
                # Generate and send OTP for WhatsApp verification
                otp_code = business_profile.generate_otp()
                if whatsapp_service.send_otp_message(request.user, otp_code, request):
                    messages.success(request, 'Business profile created! Please check your WhatsApp for the verification code.')
                    return redirect('onboarding_verify')
                else:
                    messages.error(request, 'Profile created but failed to send verification code. Please contact support.')
                    return redirect('onboarding_verify')
        else:
            form = BusinessProfileForm(user=request.user)
        
        return render(request, 'core/onboarding/business.html', {'form': form})
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def onboarding_verify(request):
    """Step 3: WhatsApp verification"""
    try:
        profile = request.user.profile
        
        # If already completed, redirect to home
        if profile.is_onboarding_complete():
            messages.info(request, 'You have already completed the onboarding process.')
            return redirect('home')
        
        # Check if business profile exists first
        try:
            business_profile = request.user.business_profile
        except AttributeError:
            messages.error(request, 'Business profile not found. Please create your business profile first.')
            return redirect('onboarding_business')
        
        # Redirect if not on verify step
        if profile.onboarding_step not in ['business', 'verify']:
            return redirect(profile.get_onboarding_redirect_url())
        
        # Check if already verified
        if business_profile.is_verified:
            profile.advance_onboarding_step()
            messages.success(request, 'WhatsApp number verified successfully! Welcome to WozapAuto!')
            return redirect('home')
        
        if request.method == 'POST':
            form = OTPVerificationForm(request.POST)
            if form.is_valid():
                otp_code = form.cleaned_data['otp_code']
                success, message = business_profile.verify_otp(otp_code)
                
                if success:
                    # Advance to complete step
                    profile.advance_onboarding_step()
                    
                    # Log WhatsApp verification activity
                    try:
                        AuditService.log_user_activity(
                            user=request.user,
                            action='whatsapp_verification',
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                            metadata={'phone_number': business_profile.phone_number}
                        )
                    except Exception as e:
                        logger.error(f"Failed to log WhatsApp verification: {e}")
                    
                    messages.success(request, 'WhatsApp number verified successfully! Welcome to WozapAuto!')
                    return redirect('home')
                else:
                    messages.error(request, message)
            else:
                messages.error(request, 'Please enter a valid 6-digit code.')
        else:
            form = OTPVerificationForm()
        
        return render(request, 'core/onboarding/verify.html', {'form': form})
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def onboarding_complete(request):
    """Onboarding completion page"""
    try:
        profile = request.user.profile
        
        if not profile.is_onboarding_complete():
            return redirect(profile.get_onboarding_redirect_url())
        
        return render(request, 'core/onboarding/complete.html')
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


def redirect_to_onboarding(request):
    """Redirect legacy URLs to new onboarding system"""
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            return redirect(profile.get_onboarding_redirect_url())
        except UserProfile.DoesNotExist:
            pass
    
    # For unauthenticated users, redirect to signin with next parameter
    return redirect(f"{reverse('signin')}?next={reverse('onboarding_welcome')}")
