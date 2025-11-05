from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.

class UserProfile(models.Model):
    """Extended user profile with additional fields for WozapAuto"""
    
    ONBOARDING_STEP_CHOICES = [
        ('welcome', 'Welcome'),
        ('business', 'Business Profile'),
        ('verify', 'WhatsApp Verification'),
        ('complete', 'Completed'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text="User profile picture")
    newsletter_subscribed = models.BooleanField(default=False, help_text="Newsletter subscription status")
    onboarding_completed = models.BooleanField(default=False, help_text="Whether user completed welcome onboarding")
    onboarding_step = models.CharField(
        max_length=20,
        choices=ONBOARDING_STEP_CHOICES,
        default='welcome',
        help_text="Current step in the onboarding process"
    )
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def full_name(self):
        """Return business name or username if not available"""
        # Try to get business name from business profile
        try:
            business_profile = self.user.business_profile
            if business_profile and business_profile.name:
                return business_profile.name
        except AttributeError:
            pass
        
        # Fallback to username
        return self.user.username
    
    @property
    def display_name(self):
        """Return display name for UI"""
        return self.full_name or self.user.username
    
    def get_onboarding_redirect_url(self):
        """Get the URL for the next onboarding step"""
        from django.urls import reverse
        
        if self.onboarding_completed:
            return reverse('home')
        
        step_urls = {
            'welcome': reverse('onboarding_welcome'),
            'business': reverse('onboarding_business'),
            'verify': reverse('onboarding_verify'),
            'complete': reverse('home'),
        }
        
        # Handle legacy 'profile' step by redirecting to business
        if self.onboarding_step == 'profile':
            return step_urls.get('business', reverse('onboarding_welcome'))
        
        return step_urls.get(self.onboarding_step, reverse('onboarding_welcome'))
    
    def advance_onboarding_step(self):
        """Advance to the next onboarding step"""
        step_order = ['welcome', 'business', 'verify', 'complete']
        
        # Handle legacy 'profile' step
        if self.onboarding_step == 'profile':
            self.onboarding_step = 'business'
        elif self.onboarding_step in step_order:
            current_index = step_order.index(self.onboarding_step)
            if current_index < len(step_order) - 1:
                self.onboarding_step = step_order[current_index + 1]
        else:
            # Unknown step, default to welcome
            self.onboarding_step = 'welcome'
        
        # Mark as completed when reaching the final step
        if self.onboarding_step == 'complete':
            self.onboarding_completed = True
        
        self.save()
    
    def is_onboarding_complete(self):
        """Check if onboarding is complete"""
        # Must have completed onboarding AND have a business profile
        if self.onboarding_completed or self.onboarding_step == 'complete':
            try:
                # Check if business profile exists and is verified
                business_profile = self.user.business_profile
                return business_profile.is_verified
            except AttributeError:
                # No business profile means onboarding is not complete
                return False
        return False
    

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
