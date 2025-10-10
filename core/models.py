from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class UserProfile(models.Model):
    """Extended user profile with additional fields for WozapAuto"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="WhatsApp number with country code (e.g., +1234567890)")
    company_name = models.CharField(max_length=100, blank=True, null=True, help_text="Company or organization name")
    timezone = models.CharField(max_length=50, default='UTC', help_text="User's timezone")
    language = models.CharField(max_length=10, default='en', help_text="Preferred language code")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text="User profile picture")
    is_verified = models.BooleanField(default=False, help_text="WhatsApp verification status")
    newsletter_subscribed = models.BooleanField(default=False, help_text="Newsletter subscription status")
    onboarding_completed = models.BooleanField(default=False, help_text="Whether user completed welcome onboarding")
    
    # OTP fields for WhatsApp verification
    otp_code = models.CharField(max_length=6, blank=True, null=True, help_text="OTP code for WhatsApp verification")
    otp_created_at = models.DateTimeField(blank=True, null=True, help_text="When OTP was generated")
    otp_attempts = models.IntegerField(default=0, help_text="Number of OTP verification attempts")
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        """Return user's full name or username if not available"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        elif self.user.first_name:
            return self.user.first_name
        else:
            return self.user.username
    
    @property
    def display_name(self):
        """Return display name for UI"""
        return self.full_name or self.user.username
    
    def generate_otp(self):
        """Generate a 6-digit OTP code and set timestamp"""
        import secrets
        from django.utils import timezone
        
        self.otp_code = f"{secrets.randbelow(1000000):06d}"
        self.otp_created_at = timezone.now()
        self.otp_attempts = 0
        self.save(update_fields=['otp_code', 'otp_created_at', 'otp_attempts'])
        return self.otp_code
    
    def verify_otp(self, code):
        """Verify OTP code with 10-minute expiry and attempt limit"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Check if OTP exists
        if not self.otp_code or not self.otp_created_at:
            return False, "No OTP code found"
        
        # Check attempt limit
        if self.otp_attempts >= 3:
            return False, "Maximum OTP attempts exceeded. Please request a new code."
        
        # Check expiry (10 minutes)
        expiry_time = self.otp_created_at + timedelta(minutes=10)
        if timezone.now() > expiry_time:
            return False, "OTP code has expired. Please request a new code."
        
        # Check code match
        if self.otp_code != code:
            self.otp_attempts += 1
            self.save(update_fields=['otp_attempts'])
            return False, "Invalid OTP code"
        
        # Success - mark as verified and clear OTP
        self.is_verified = True
        self.otp_code = None
        self.otp_created_at = None
        self.otp_attempts = 0
        self.save(update_fields=['is_verified', 'otp_code', 'otp_created_at', 'otp_attempts'])
        return True, "OTP verified successfully"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Automatically save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
