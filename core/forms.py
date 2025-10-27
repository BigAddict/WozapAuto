from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import UserProfile
from .utils import normalize_string_field
from .timezone_utils import format_timezone_choices
from core.currency_utils import format_currency_choices
from business.models import BusinessProfile, BusinessType
import re


class CustomUserCreationForm(UserCreationForm):
    """Custom user creation form with additional fields and validation"""
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    
    terms_agreement = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        error_messages={
            'required': 'You must agree to the Terms of Service and Privacy Policy.'
        }
    )
    
    newsletter = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'autocomplete': 'username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
    
    def clean_email(self):
        """Validate email uniqueness (case-insensitive)"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError('An account with this email address already exists.')
        return email
    
    def clean_username(self):
        """Normalize username"""
        return normalize_string_field(self.cleaned_data.get('username'))
    
    def clean_first_name(self):
        """Normalize first name"""
        return normalize_string_field(self.cleaned_data.get('first_name'))
    
    def clean_last_name(self):
        """Normalize last name"""
        return normalize_string_field(self.cleaned_data.get('last_name'))
    
    def clean_password1(self):
        """Enhanced password validation"""
        password1 = self.cleaned_data.get('password1')
        if password1:
            # Check minimum length
            if len(password1) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            
            # Check for uppercase letter
            if not re.search(r'[A-Z]', password1):
                raise ValidationError('Password must contain at least one uppercase letter.')
            
            # Check for lowercase letter
            if not re.search(r'[a-z]', password1):
                raise ValidationError('Password must contain at least one lowercase letter.')
            
            # Check for number
            if not re.search(r'\d', password1):
                raise ValidationError('Password must contain at least one number.')
            
            # Check for special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password1):
                raise ValidationError('Password must contain at least one special character.')
        
        return password1
    
    def save(self, commit=True):
        """Save user and create profile with newsletter preference"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create or update profile with newsletter preference
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.newsletter_subscribed = self.cleaned_data.get('newsletter', False)
            profile.save()
        
        return user


class BusinessProfileForm(forms.ModelForm):
    """Form for business profile creation during onboarding"""
    
    TIMEZONE_CHOICES = format_timezone_choices()
    CURRENCY_CHOICES = format_currency_choices()
    
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili'),
    ]
    
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890',
            'pattern': r'\+[1-9]\d{1,14}'
        }),
        help_text='WhatsApp number with country code (e.g., +1234567890) - Required for verification'
    )
    
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    language = forms.ChoiceField(
        choices=LANGUAGE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    currency = forms.ChoiceField(
        choices=CURRENCY_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    business_type = forms.ModelChoiceField(
        queryset=BusinessType.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = BusinessProfile
        fields = ['name', 'business_type', 'phone_number', 'timezone', 'language', 'currency', 
                 'description', 'email', 'website', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your business name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of your business'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'business@example.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yourwebsite.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Business address'
            }),
        }
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone_number = normalize_string_field(self.cleaned_data.get('phone_number'))
        if phone_number:
            # Check if it starts with + and has valid format
            if not re.match(r'^\+[1-9]\d{1,14}$', phone_number):
                raise ValidationError(
                    'Please enter a valid phone number with country code (e.g., +1234567890)'
                )
        return phone_number
    


class OTPVerificationForm(forms.Form):
    """Form for OTP verification"""
    
    otp_code = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '123456',
            'maxlength': '6',
            'pattern': r'\d{6}',
            'autocomplete': 'one-time-code'
        }),
        help_text='Enter the 6-digit code sent to your WhatsApp'
    )
    
    def clean_otp_code(self):
        """Validate OTP code format"""
        otp_code = normalize_string_field(self.cleaned_data.get('otp_code'))
        if otp_code:
            # Check if it's exactly 6 digits
            if not re.match(r'^\d{6}$', otp_code):
                raise ValidationError('Please enter a valid 6-digit code.')
        return otp_code


class PersonalProfileForm(forms.ModelForm):
    """Form for personal profile completion during onboarding"""
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'newsletter_subscribed']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'newsletter_subscribed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['avatar'].help_text = 'Upload a profile picture (optional)'
        self.fields['newsletter_subscribed'].help_text = 'Subscribe to our newsletter for updates and tips'
        
        # Make newsletter field more prominent
        self.fields['newsletter_subscribed'].label = 'Subscribe to Newsletter'
    
    def clean_avatar(self):
        """Validate avatar file"""
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError('Avatar file size must be less than 5MB.')
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if avatar.content_type not in allowed_types:
                raise ValidationError('Please upload a valid image file (JPEG, PNG, GIF, or WebP).')
        
        return avatar
