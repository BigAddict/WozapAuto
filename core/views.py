from django.contrib.auth import authenticate, login, logout
import logging
import time
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.urls import reverse
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from .models import UserProfile
from .forms import CustomUserCreationForm, OnboardingForm, OTPVerificationForm
from .decorators import verified_email_required, onboarding_required
from .whatsapp_service import whatsapp_service

logger = logging.getLogger('core.views')

# Signup View
def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Create user
                user = form.save()
                
                # Skip email verification, go directly to onboarding
                messages.success(
                    request, 
                    'Account created successfully! Please complete your profile setup.'
                )
                return redirect('onboarding')
                
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
                return redirect('signup')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'core/signup.html', {'form': form})

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Please fill in all fields')
            return render(request, 'core/signin.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'core/signin.html')

    return render(request, 'core/signin.html')

def signout(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('home')

class HomePageView(TemplateView):
    template_name = 'core/home.html'
    
    def get(self, request, *args, **kwargs):
        # Check if user needs onboarding
        if request.user.is_authenticated:
            try:
                if not request.user.profile.onboarding_completed:
                    messages.info(request, 'Please complete your profile setup to continue.')
                    return redirect('welcome_onboarding')
            except AttributeError:
                # Profile doesn't exist, redirect to onboarding
                messages.info(request, 'Please complete your profile setup to continue.')
                return redirect('welcome_onboarding')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_authenticated'] = self.request.user.is_authenticated
        
        if self.request.user.is_authenticated:
            # Import here to avoid circular imports
            from connections.models import Connection
            
            # Get user's connections
            connections = Connection.objects.filter(user=self.request.user)
            active_connections = connections.filter(connection_status='open')
            
            # Get connection data for dashboard
            connection_data = {}
            if connections.exists():
                connection = connections.first()
                # Try to get real-time data from Evolution API
                try:
                    from connections.services import evolution_api_service
                    success, instance_data = evolution_api_service.get_instance(connection.instance_id)
                    if success:
                        connection_data = {
                            'connection_status': instance_data.connection_status,
                            'messages_count': instance_data.count.messages,
                            'contacts_count': instance_data.count.contacts,
                            'chats_count': instance_data.count.chat
                        }
                except:
                    # Fallback to database data
                    connection_data = {
                        'connection_status': connection.connection_status,
                        'messages_count': 0,
                        'contacts_count': 0,
                        'chats_count': 0
                    }
            
            # Dashboard stats
            context.update({
                'total_connections': connections.count(),
                'active_connections': active_connections.count(),
                'user_profile': getattr(self.request.user, 'profile', None),
                **connection_data  # Add connection data to context
            })
        
        return context




@login_required
def profile_view(request):
    """View user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'core/profile.html', {'profile': profile})


@login_required
def profile_edit(request):
    """Edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user fields
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.email = request.POST.get('email', '').strip()
        request.user.save()
        
        # Update profile fields
        profile.phone_number = request.POST.get('phone_number', '').strip()
        profile.company_name = request.POST.get('company_name', '').strip()
        profile.timezone = request.POST.get('timezone', 'UTC')
        profile.language = request.POST.get('language', 'en')
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'core/profile_edit.html', {'profile': profile})


@login_required
def profile_api(request):
    """API endpoint for profile data"""
    if request.method == 'GET':
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        return JsonResponse({
            'company_name': profile.company_name or '',
            'phone_number': profile.phone_number or '',
            'timezone': profile.timezone,
            'language': profile.language,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# Password Management Views

def forgot_password(request):
    """Handle forgot password requests via WhatsApp phone number"""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        
        if not phone_number:
            messages.error(request, 'Please enter your WhatsApp phone number.')
            return render(request, 'core/forgot_password.html')
        
        # Normalize just in case (keep + and digits)
        import re
        phone_number = '+' + ''.join(re.findall(r'\d+', phone_number)) if not phone_number.startswith('+') else phone_number
        
        try:
            profile = UserProfile.objects.get(phone_number=phone_number)
            user = profile.user
            
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Send password reset WhatsApp message
            if whatsapp_service.send_password_reset_message(user, reset_url, request):
                messages.success(request, 'Password reset instructions have been sent to your WhatsApp.')
            else:
                messages.error(request, 'Failed to send password reset message. Please contact support.')
        except UserProfile.DoesNotExist:
            # Don't reveal whether the number exists
            messages.success(request, 'If an account with that number exists, password reset instructions have been sent.')
        
        return render(request, 'core/forgot_password.html')
    
    return render(request, 'core/forgot_password.html')


def password_reset_confirm(request, uidb64, token):
    """Handle password reset confirmation"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
                return redirect('signin')
        else:
            form = SetPasswordForm(user)
        
        return render(request, 'core/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('forgot_password')


@login_required
def change_password(request):
    """Handle password change for authenticated users"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            
            # Send confirmation WhatsApp message
            whatsapp_service.send_password_change_confirmation_message(user, request)
            
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('profile')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'core/change_password.html', {'form': form})


# Email Verification Views
def verify_email_sent(request):
    """Show 'check your email' page after signup"""
    return render(request, 'core/verify_email_sent.html')


def verify_email(request, token):
    """Handle email verification"""
    try:
        # Find user with this verification token
        profile = UserProfile.objects.get(email_verification_token=token)
        
        # Check if token is not expired (24 hours)
        if profile.email_verification_sent_at:
            time_diff = timezone.now() - profile.email_verification_sent_at
            if time_diff.total_seconds() > 24 * 60 * 60:  # 24 hours
                messages.error(request, 'Verification link has expired. Please request a new one.')
                return redirect('verify_email_failed')
        
        # Mark email as verified
        profile.is_verified = True
        profile.email_verification_token = None  # Clear token
        profile.email_verification_sent_at = None
        profile.save()
        
        # Auto-login the user
        login(request, profile.user)
        
        messages.success(request, 'Email verified successfully! Welcome to WozapAuto.')
        return redirect('verify_email_success')
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('verify_email_failed')


def verify_email_success(request):
    """Show email verification success page"""
    return render(request, 'core/verify_email_success.html')


def verify_email_failed(request):
    """Show email verification failed page"""
    return render(request, 'core/verify_email_failed.html')


def verification_required_notice(request):
    """Show verification required notice page"""
    return render(request, 'core/verification_required.html')


def resend_verification(request):
    """Resend verification email with rate limiting"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please sign in to resend verification email.')
        return redirect('signin')
    
    try:
        logger.info(
            "resend_verification:start",
            extra={
                'user_id': getattr(request.user, 'id', None),
                'user_email': getattr(request.user, 'email', ''),
                'path': request.path,
                'ip': request.META.get('REMOTE_ADDR'),
            }
        )
        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        logger.info(
            "resend_verification:profile",
            extra={
                'profile_id': getattr(profile, 'id', None),
                'profile_created': created,
                'is_verified': profile.is_verified,
                'last_sent_at': getattr(profile.email_verification_sent_at, 'isoformat', lambda: None)(),
            }
        )
        
        # Check if already verified
        if profile.is_verified:
            logger.info("resend_verification:already_verified")
            messages.info(request, 'Your email is already verified.')
            return redirect('home')
        
        # Rate limiting: max 1 request per hour (more lenient)
        if profile.email_verification_sent_at:
            time_diff = timezone.now() - profile.email_verification_sent_at
            if time_diff.total_seconds() < 60 * 60:  # 1 hour
                wait_seconds = int(60 * 60 - time_diff.total_seconds())
                logger.info("resend_verification:rate_limited", extra={'wait_seconds': wait_seconds})
                messages.warning(request, 'Please wait before requesting another verification email.')
                return redirect('verification_required')
        
        # Send verification email
        t0 = time.monotonic()
        success = whatsapp_service.send_otp_message(request.user, request.user.profile.generate_otp(), request)
        duration_s = time.monotonic() - t0
        logger.info("resend_verification:send_completed", extra={'success': success, 'duration_s': round(duration_s, 3)})
        
        if success:
            messages.success(request, 'Verification code sent! Please check your WhatsApp.')
        else:
            messages.error(request, 'Failed to send verification code. Please try again later.')
        
        return redirect('verification_required')
        
    except Exception as e:
        logger.exception("resend_verification:error")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('verification_required')


# Welcome Onboarding View
@login_required
def welcome_onboarding(request):
    """Welcome onboarding flow for new users"""
    try:
        profile = request.user.profile
        
        # Check if already completed
        if profile.onboarding_completed:
            messages.info(request, 'You have already completed the onboarding process.')
            return redirect('home')
        
        if request.method == 'POST':
            form = OnboardingForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                # Save profile data
                profile = form.save()
                
                # Generate and send OTP for WhatsApp verification
                otp_code = profile.generate_otp()
                if whatsapp_service.send_otp_message(request.user, otp_code, request):
                    messages.success(request, 'Profile saved! Please check your WhatsApp for the verification code.')
                    return redirect('verify_whatsapp_otp')
                else:
                    messages.error(request, 'Profile saved but failed to send verification code. Please contact support.')
                    return redirect('verify_whatsapp_otp')
        else:
            form = OnboardingForm(instance=profile)
        
        return render(request, 'core/welcome_onboarding.html', {'form': form})
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def verify_whatsapp_otp(request):
    """Verify WhatsApp OTP code"""
    try:
        profile = request.user.profile
        
        # Check if already verified
        if profile.is_verified:
            messages.info(request, 'Your WhatsApp number is already verified.')
            return redirect('home')
        
        if request.method == 'POST':
            form = OTPVerificationForm(request.POST)
            if form.is_valid():
                otp_code = form.cleaned_data['otp_code']
                success, message = profile.verify_otp(otp_code)
                
                if success:
                    profile.onboarding_completed = True
                    profile.save()
                    messages.success(request, 'WhatsApp number verified successfully! Welcome to WozapAuto!')
                    return redirect('home')
                else:
                    messages.error(request, message)
            else:
                messages.error(request, 'Please enter a valid 6-digit code.')
        else:
            form = OTPVerificationForm()
        
        return render(request, 'core/verify_otp.html', {'form': form})
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')


@login_required
def resend_otp(request):
    """Resend OTP code"""
    try:
        profile = request.user.profile
        
        # Check if already verified
        if profile.is_verified:
            messages.info(request, 'Your WhatsApp number is already verified.')
            return redirect('home')
        
        # Generate and send new OTP
        otp_code = profile.generate_otp()
        if whatsapp_service.send_otp_message(request.user, otp_code, request):
            messages.success(request, 'New verification code sent to your WhatsApp.')
        else:
            messages.error(request, 'Failed to send verification code. Please contact support.')
        
        return redirect('verify_whatsapp_otp')
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profile not found. Please contact support.')
        return redirect('home')