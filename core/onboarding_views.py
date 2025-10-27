from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
import logging

from .models import UserProfile
from .forms import PersonalProfileForm, BusinessProfileForm, OTPVerificationForm
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
    """Step 1: Personal profile completion"""
    try:
        profile = request.user.profile
        
        # If already completed, redirect to home
        if profile.is_onboarding_complete():
            messages.info(request, 'You have already completed the onboarding process.')
            return redirect('home')
        
        # If not on profile step, redirect to current step
        if profile.onboarding_step not in ['welcome', 'profile']:
            return redirect(profile.get_onboarding_redirect_url())
        
        if request.method == 'POST':
            form = PersonalProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                
                # Advance to next step
                profile.advance_onboarding_step()
                
                messages.success(request, 'Personal profile updated successfully!')
                return redirect('onboarding_business')
        else:
            form = PersonalProfileForm(instance=profile)
        
        return render(request, 'core/onboarding/profile.html', {'form': form})
        
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
        
        # If not on business step, redirect to current step
        if profile.onboarding_step not in ['profile', 'business']:
            return redirect(profile.get_onboarding_redirect_url())
        
        # Check if business profile already exists
        try:
            business_profile = request.user.business_profile
            if business_profile.is_verified:
                # Already verified, advance to complete
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
            form = BusinessProfileForm(request.POST)
            if form.is_valid():
                # Create business profile
                business_profile = form.save(commit=False)
                business_profile.user = request.user
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
            form = BusinessProfileForm()
        
        return render(request, 'core/onboarding/business.html', {'form': form})
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def onboarding_verify(request):
    """Step 3: WhatsApp verification"""
    try:
        profile = request.user.profile
        business_profile = request.user.business_profile
        
        # If already completed, redirect to home
        if profile.is_onboarding_complete():
            messages.info(request, 'You have already completed the onboarding process.')
            return redirect('home')
        
        # If not on verify step, redirect to current step
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
    except AttributeError:
        messages.error(request, 'Business profile not found. Please create your business profile first.')
        return redirect('onboarding_business')


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
    
    return redirect('onboarding_welcome')
