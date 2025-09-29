from django import forms
from django.core.exceptions import ValidationError
from .models import Connection

class ConnectionForm(forms.Form):
    """Form for creating new WhatsApp connections"""
    
    CONNECTION_METHODS = [
        ('qr_code', 'QR Code'),
        ('pairing_code', 'Pairing Code'),
    ]
    
    instance_name = forms.CharField(
        max_length=255,
        label='Connection Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., My WhatsApp Bot',
            'maxlength': '50',
            'required': True
        }),
        help_text='Choose a name to identify this connection'
    )
    
    phone_number = forms.CharField(
        max_length=20,
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890',
            'pattern': '^\+[1-9]\d{1,14}$',
            'required': True
        }),
        help_text='Enter your WhatsApp phone number with country code'
    )
    
    connection_method = forms.ChoiceField(
        choices=CONNECTION_METHODS,
        label='Connection Method',
        widget=forms.RadioSelect(attrs={'class': 'radio-option__input'}),
        initial='qr_code'
    )
    
    def clean_instance_name(self):
        """Validate instance name"""
        instance_name = self.cleaned_data['instance_name']
        
        if len(instance_name.strip()) < 3:
            raise ValidationError('Connection name must be at least 3 characters long.')
        
        # Check if instance name already exists for this user
        if hasattr(self, 'user') and self.user.is_authenticated:
            if Connection.objects.filter(
                user=self.user, 
                instance_name__iexact=instance_name.strip()
            ).exists():
                raise ValidationError('A connection with this name already exists.')
        
        return instance_name.strip()
    
    def clean_phone_number(self):
        """Validate phone number format"""
        phone = self.cleaned_data['phone_number']
        
        # Remove any spaces or dashes
        phone = phone.replace(' ', '').replace('-', '')
        
        # Check if it starts with +
        if not phone.startswith('+'):
            raise ValidationError('Phone number must start with + (country code).')
        
        # Check if it's a valid international format
        if not phone[1:].isdigit() or len(phone) < 8 or len(phone) > 16:
            raise ValidationError('Please enter a valid phone number with country code.')
        
        return phone
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add user to form for validation
        if self.user:
            self.user = self.user


class ConnectionUpdateForm(forms.ModelForm):
    """Form for updating existing connections"""
    
    class Meta:
        model = Connection
        fields = ['instance_name', 'profileName']
        widgets = {
            'instance_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., My WhatsApp Bot'
            }),
            'profileName': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., My Business Name'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['instance_name'].help_text = 'Choose a name to identify this connection'
        self.fields['profileName'].help_text = 'Display name for your WhatsApp profile'
    
    def clean_instance_name(self):
        """Validate instance name uniqueness"""
        instance_name = self.cleaned_data['instance_name']
        
        if len(instance_name.strip()) < 3:
            raise ValidationError('Connection name must be at least 3 characters long.')
        
        # Check if instance name already exists for this user (excluding current instance)
        if self.user and self.user.is_authenticated:
            queryset = Connection.objects.filter(
                user=self.user, 
                instance_name__iexact=instance_name.strip()
            )
            
            # Exclude current instance if we're updating
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('A connection with this name already exists.')
        
        return instance_name.strip()
