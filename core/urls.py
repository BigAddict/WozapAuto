from django.urls import path

from .views import (
    HomePageView, signup, signin, signout, profile_view, profile_edit, profile_api,
    forgot_password, password_reset_confirm, change_password,
    verification_required_notice, resend_verification, welcome_onboarding,
    verify_whatsapp_otp, resend_otp
)

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='signout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/change-password/', change_password, name='change_password'),
    path('api/profile/', profile_api, name='profile_api'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
    
    # WhatsApp verification URLs
    path('verification-required/', verification_required_notice, name='verification_required'),
    path('resend-verification/', resend_verification, name='resend_verification'),
    
    # Welcome onboarding
    path('welcome/', welcome_onboarding, name='welcome_onboarding'),
    path('onboarding/', welcome_onboarding, name='onboarding'),
    
    # WhatsApp OTP verification
    path('verify-whatsapp-otp/', verify_whatsapp_otp, name='verify_whatsapp_otp'),
    path('resend-otp/', resend_otp, name='resend_otp'),
]