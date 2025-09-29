# WozapAuto Implementation Plan - User Auth & Evolution API Integration

## Project Overview

This document outlines the implementation plan for WozapAuto's core features: **user authentication/profile management** and **Evolution API connection management**. This is a focused implementation that leverages the existing Bootstrap + Django Cotton architecture to create a professional whitelabel dashboard for Evolution API and n8n workflow management.

## Scope & Objectives

### Primary Goals
- ✅ **User Authentication & Profile Management**: Complete user registration, login, and profile management system
- ✅ **Evolution API Connection Management**: Create, manage, and monitor WhatsApp connections via Evolution API
- ✅ **Dashboard Integration**: Professional dashboard with connection statistics and quick actions
- ✅ **Whitelabel Experience**: Clean interface that hides Evolution API and n8n complexity from users

### Out of Scope (For This Phase)
- ❌ Real-time chat functionality
- ❌ AI agent management (will be handled by external system)
- ❌ Message processing (handled by n8n workflows)
- ❌ Advanced analytics and reporting

## Technical Architecture

### Current Tech Stack
- **Backend**: Django 5.2.6
- **Frontend**: Bootstrap 5.0.2 + Django Cotton components
- **Database**: SQLite (development)
- **WhatsApp Integration**: Evolution API
- **Workflow Engine**: n8n (external)

### Design System
- **CSS Framework**: Bootstrap 5.0.2 with custom WhatsApp theme
- **Component System**: Django Cotton for reusable UI components
- **Styling**: Custom CSS with WhatsApp-inspired design
- **Icons**: Bootstrap Icons
- **Responsive**: Mobile-first approach

## Implementation Phases

### Phase 1: User Profile Management (1-2 weeks)

#### 1.1 User Profile Model Extension
```python
# core/models.py
from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    company_name = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
```

#### 1.2 Profile Management Views
```python
# core/views.py - Add these views
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserProfile

@login_required
def profile_view(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'core/profile.html', {'profile': profile})

@login_required
def profile_edit(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user fields
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.save()
        
        # Update profile fields
        profile.phone_number = request.POST.get('phone_number')
        profile.company_name = request.POST.get('company_name')
        profile.timezone = request.POST.get('timezone')
        profile.language = request.POST.get('language')
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'core/profile_edit.html', {'profile': profile})
```

#### 1.3 Profile Templates Using Django Cotton
```html
<!-- core/templates/core/profile.html -->
{% extends 'core/base.html' %}
{% load static %}

{% block title %}Profile - WozapAuto{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-lg-3">
            <!-- Profile Sidebar -->
            <c-card title="Profile" subtitle="{{ user.get_full_name|default:user.username }}">
                <div class="text-center">
                    <div class="profile-avatar mb-3">
                        {% if profile.avatar %}
                            <img src="{{ profile.avatar.url }}" alt="Avatar" class="rounded-circle" width="100" height="100">
                        {% else %}
                            <div class="avatar-placeholder">
                                <i class="bi bi-person-circle" style="font-size: 100px; color: #25D366;"></i>
                            </div>
                        {% endif %}
                    </div>
                    <p class="text-muted mb-3">{{ user.email }}</p>
                    <c-button variant="outline-primary" size="sm" content="Edit Profile" onclick="window.location.href='{% url 'profile_edit' %}'" />
                </div>
            </c-card>
        </div>
        
        <div class="col-lg-9">
            <!-- Profile Information -->
            <c-card title="Profile Information">
                <div class="row">
                    <div class="col-md-6">
                        <h6>Personal Information</h6>
                        <p><strong>Name:</strong> {{ user.get_full_name|default:"Not set" }}</p>
                        <p><strong>Email:</strong> {{ user.email }}</p>
                        <p><strong>Username:</strong> {{ user.username }}</p>
                        <p><strong>Phone:</strong> {{ profile.phone_number|default:"Not set" }}</p>
                    </div>
                    <div class="col-md-6">
                        <h6>Account Settings</h6>
                        <p><strong>Company:</strong> {{ profile.company_name|default:"Not set" }}</p>
                        <p><strong>Timezone:</strong> {{ profile.timezone }}</p>
                        <p><strong>Language:</strong> {{ profile.language }}</p>
                        <p><strong>Member since:</strong> {{ user.date_joined|date:"F Y" }}</p>
                    </div>
                </div>
            </c-card>
        </div>
    </div>
</div>
{% endblock %}
```

#### 1.4 URL Configuration
```python
# core/urls.py
from django.urls import path
from .views import HomePageView, signup, signin, signout, profile_view, profile_edit

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='signout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
]
```

### Phase 2: Evolution API Connection Management (2-3 weeks)

#### 2.1 Enhanced Connection Views
```python
# connections/views.py - Enhanced version
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Connection
from .services import evolution_api_service
from .forms import ConnectionForm

@login_required
def connection_list(request):
    """List all user's connections"""
    connections = Connection.objects.filter(user=request.user)
    return render(request, 'connections/connection_list.html', {
        'connections': connections
    })

@login_required
def connection_create(request):
    """Create new Evolution API connection"""
    if request.method == 'POST':
        form = ConnectionForm(request.POST)
        if form.is_valid():
            # Create Evolution API instance
            instance_data = form.cleaned_data
            success, result = evolution_api_service.create_instance(
                EvolutionInstanceCreate(
                    instance_name=instance_data['instance_name'],
                    phone_number=instance_data['phone_number'],
                    connect_now=instance_data['connection_method'] == 'qr_code'
                )
            )
            
            if success:
                # Save connection to database
                connection = Connection.objects.create(
                    user=request.user,
                    instance_id=result.instance.instance_id,
                    instance_name=result.instance.instance_name,
                    ownerPhone=instance_data['phone_number'],
                    profileName=instance_data['instance_name'],
                    connection_status='connecting',
                    instance_api_key=result.instance.access_token_wa_business
                )
                
                messages.success(request, 'Connection created successfully!')
                return redirect('connection_detail', connection_id=connection.id)
            else:
                messages.error(request, f'Failed to create connection: {result}')
    else:
        form = ConnectionForm()
    
    return render(request, 'connections/connection_create.html', {'form': form})

@login_required
def connection_detail(request, connection_id):
    """View connection details and status"""
    connection = get_object_or_404(Connection, id=connection_id, user=request.user)
    
    # Fetch latest instance data from Evolution API
    success, instance_data = evolution_api_service.get_instance(connection.instance_id)
    
    context = {
        'connection': connection,
        'instance_data': instance_data if success else None,
        'api_error': result if not success else None
    }
    
    return render(request, 'connections/connection_detail.html', context)

@login_required
def connection_status_api(request, connection_id):
    """API endpoint for connection status updates"""
    connection = get_object_or_404(Connection, id=connection_id, user=request.user)
    
    success, instance_data = evolution_api_service.get_instance(connection.instance_id)
    
    if success:
        # Update connection status in database
        connection.connection_status = instance_data.connection_status
        connection.save()
        
        return JsonResponse({
            'status': 'success',
            'connection_status': instance_data.connection_status,
            'profile_name': instance_data.profile_name,
            'phone_number': instance_data.phone_number
        })
    else:
        return JsonResponse({
            'status': 'error',
            'message': instance_data
        }, status=400)
```

#### 2.2 Connection Forms
```python
# connections/forms.py
from django import forms
from .models import Connection

class ConnectionForm(forms.Form):
    CONNECTION_METHODS = [
        ('qr_code', 'QR Code'),
        ('pairing_code', 'Pairing Code'),
    ]
    
    instance_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., My WhatsApp Bot'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890'
        })
    )
    
    connection_method = forms.ChoiceField(
        choices=CONNECTION_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        if not phone.startswith('+'):
            raise forms.ValidationError('Phone number must start with +')
        return phone
```

#### 2.3 Connection Templates Using Django Cotton
```html
<!-- connections/templates/connections/connection_list.html -->
{% extends 'core/base.html' %}
{% load static %}

{% block title %}Connections - WozapAuto{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>WhatsApp Connections</h1>
        <c-button variant="primary" content="New Connection" onclick="window.location.href='{% url 'connections:create' %}'" icon="bi-plus-circle" />
    </div>
    
    {% if connections %}
        <div class="row">
            {% for connection in connections %}
            <div class="col-md-6 col-lg-4 mb-4">
                <c-connection-card 
                    instance_name="{{ connection.instance_name }}"
                    connection_status="{{ connection.connection_status }}"
                    messages_count="{{ connection.messages_count|default:0 }}"
                    last_activity="{{ connection.updated_at|timesince }} ago"
                    connection_id="{{ connection.id }}"
                    show_stats="true"
                    show_actions="true" />
            </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="text-center py-5">
            <div class="empty-state">
                <i class="bi bi-whatsapp" style="font-size: 4rem; color: #25D366; opacity: 0.5;"></i>
                <h3 class="mt-3">No Connections Yet</h3>
                <p class="text-muted">Create your first WhatsApp connection to get started</p>
                <c-button variant="primary" content="Create Connection" onclick="window.location.href='{% url 'connections:create' %}'" icon="bi-plus-circle" />
            </div>
        </div>
    {% endif %}
</div>
{% endblock %}
```

#### 2.4 Connection Creation Form Using Django Cotton
```html
<!-- connections/templates/connections/connection_create.html -->
{% extends 'core/base.html' %}
{% load static %}

{% block title %}Create Connection - WozapAuto{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <c-card title="Setup WhatsApp Connection" subtitle="Connect your WhatsApp account to start using AI agents">
                <form method="post" id="connectionForm">
                    {% csrf_token %}
                    
                    <c-form-field 
                        name="instance_name" 
                        label="Connection Name" 
                        type="text" 
                        placeholder="e.g., My WhatsApp Bot" 
                        required="true" 
                        help_text="Choose a unique name for your WhatsApp instance" />
                    
                    <c-input-group 
                        name="phone_number" 
                        label="Phone Number" 
                        type="tel" 
                        prefix="+" 
                        placeholder="1234567890" 
                        required="true" 
                        help_text="Enter your WhatsApp phone number with country code" />
                    
                    <div class="form-group">
                        <fieldset class="connection-method">
                            <legend class="form-label">Connection Method</legend>
                            <div class="radio-group">
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="connection_method" value="qr_code" id="qrMethod" checked>
                                    <label class="form-check-label" for="qrMethod">
                                        <i class="bi bi-qrcode me-2"></i>
                                        QR Code
                                        <small class="d-block text-muted">Scan QR code with your phone</small>
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="connection_method" value="pairing_code" id="pairingMethod">
                                    <label class="form-check-label" for="pairingMethod">
                                        <i class="bi bi-key me-2"></i>
                                        Pairing Code
                                        <small class="d-block text-muted">Enter 8-digit code</small>
                                    </label>
                                </div>
                            </div>
                        </fieldset>
                    </div>
                    
                    <div class="form-actions text-center">
                        <c-button type="submit" variant="primary" size="lg" content="Setup Connection" icon="bi-rocket-takeoff" />
                    </div>
                </form>
            </c-card>
        </div>
    </div>
</div>
{% endblock %}
```

#### 2.5 URL Configuration
```python
# connections/urls.py
from django.urls import path
from .views import connection_list, connection_create, connection_detail, connection_status_api

app_name = 'connections'
urlpatterns = [
    path('', connection_list, name='list'),
    path('create/', connection_create, name='create'),
    path('<int:connection_id>/', connection_detail, name='detail'),
    path('<int:connection_id>/status/', connection_status_api, name='status_api'),
]
```

### Phase 3: Dashboard Integration (1 week)

#### 3.1 Enhanced Dashboard Using Django Cotton
```html
<!-- Update core/templates/core/home.html -->
{% if user.is_authenticated %}
<!-- Enhanced Dashboard for authenticated users -->
<div class="dashboard-header">
    <h1 class="dashboard-title">
        Welcome back, {{ user.first_name|default:user.username }}!
    </h1>
    <p class="dashboard-subtitle">Manage your WhatsApp AI agents and connections</p>
</div>

<!-- Connection Stats -->
<div class="row g-3 mb-4">
    <div class="col-md-3">
        <c-stat-card title="Total Connections" value="{{ total_connections }}" change="0" icon="bi-whatsapp" color="primary" />
    </div>
    <div class="col-md-3">
        <c-stat-card title="Active Connections" value="{{ active_connections }}" change="0" icon="bi-check-circle" color="success" />
    </div>
    <div class="col-md-3">
        <c-stat-card title="AI Agents" value="0" change="0" icon="bi-robot" color="info" />
    </div>
    <div class="col-md-3">
        <c-stat-card title="Messages Processed" value="0" change="0" icon="bi-chat-dots" color="warning" />
    </div>
</div>

<!-- Quick Actions -->
<div class="row g-3 mb-4">
    <div class="col-md-4">
        <c-card title="Setup Connection" subtitle="Connect your WhatsApp account">
            <p>Connect your WhatsApp account to start using AI agents</p>
            <c-button variant="primary" content="Setup Connection" onclick="window.location.href='{% url 'connections:create' %}'" icon="bi-plus-circle" />
        </c-card>
    </div>
    <div class="col-md-4">
        <c-card title="Manage Connections" subtitle="View existing connections">
            <p>View and manage your existing WhatsApp connections</p>
            <c-button variant="outline-primary" content="Manage Connections" onclick="window.location.href='{% url 'connections:list' %}'" icon="bi-gear" />
        </c-card>
    </div>
    <div class="col-md-4">
        <c-card title="Profile Settings" subtitle="Update your profile">
            <p>Update your profile and account settings</p>
            <c-button variant="outline-secondary" content="Profile Settings" onclick="window.location.href='{% url 'profile' %}'" icon="bi-person-circle" />
        </c-card>
    </div>
</div>

<!-- Recent Connections -->
{% if recent_connections %}
<div class="row">
    <div class="col-12">
        <c-card title="Recent Connections">
            {% for connection in recent_connections %}
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                <div>
                    <h6 class="mb-1">{{ connection.instance_name }}</h6>
                    <small class="text-muted">{{ connection.ownerPhone }} - {{ connection.connection_status|title }}</small>
                </div>
                <small class="text-muted">{{ connection.created_at|timesince }} ago</small>
            </div>
            {% endfor %}
        </c-card>
    </div>
</div>
{% endif %}
{% endif %}
```

#### 3.2 Enhanced Dashboard View
```python
# core/views.py - Enhanced HomePageView
class HomePageView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            # Get user's connections
            connections = Connection.objects.filter(user=self.request.user)
            active_connections = connections.filter(connection_status='open')
            
            # Dashboard stats
            context.update({
                'total_connections': connections.count(),
                'active_connections': active_connections.count(),
                'recent_connections': connections.order_by('-created_at')[:5],
                'user_profile': getattr(self.request.user, 'profile', None)
            })
        
        return context
```

### Phase 4: Navigation & Polish (0.5 weeks)

#### 4.1 Navigation Updates
```html
<!-- Update core/templates/core/base.html sidebar -->
{% if user.is_authenticated %}
<div class="col-lg-2 col-md-3 p-0">
    <div class="sidebar">
        <nav class="nav flex-column">
            <a class="nav-link active" href="{% url 'home' %}">
                <i class="bi bi-speedometer2 me-2"></i>Dashboard
            </a>
            <a class="nav-link" href="{% url 'connections:list' %}">
                <i class="bi bi-whatsapp me-2"></i>Connections
                <span class="notification-badge ms-auto">{{ user.connection_set.count }}</span>
            </a>
            <a class="nav-link" href="{% url 'profile' %}">
                <i class="bi bi-person-circle me-2"></i>Profile
            </a>
            <a class="nav-link" href="#">
                <i class="bi bi-robot me-2"></i>AI Agents
                <span class="notification-badge ms-auto">0</span>
            </a>
            <a class="nav-link" href="#">
                <i class="bi bi-graph-up me-2"></i>Analytics
            </a>
            <a class="nav-link" href="#">
                <i class="bi bi-gear me-2"></i>Settings
            </a>
        </nav>
    </div>
</div>
{% endif %}
```

## Django Cotton Components

### Existing Components (Keep & Enhance)
- ✅ `button.html` - Bootstrap-styled buttons with variants
- ✅ `card.html` - Basic card component
- ✅ `connection_card.html` - WhatsApp connection card
- ✅ `form_field.html` - Form input fields
- ✅ `input_group.html` - Input groups with prefixes/suffixes
- ✅ `stat_card.html` - Statistics display cards

### New Components Needed
- 🔄 `profile_card.html` - User profile display component
- 🔄 `dashboard_stats.html` - Dashboard statistics component
- 🔄 `connection_wizard.html` - Connection setup wizard
- 🔄 `status_indicator.html` - Connection status indicator

## Database Migrations

### Required Migrations
```python
# Create migration for UserProfile model
python manage.py makemigrations core

# Create migration for Connection model updates (if needed)
python manage.py makemigrations connections

# Apply migrations
python manage.py migrate
```

## Testing Strategy

### Unit Tests
- User profile creation and updates
- Connection creation and management
- Evolution API service integration
- Django Cotton component rendering

### Integration Tests
- Complete user registration flow
- Connection creation and status updates
- Dashboard data loading
- Navigation and routing

### Manual Testing
- Cross-browser compatibility
- Mobile responsiveness
- Form validation
- Error handling

## Deployment Considerations

### Environment Variables
```bash
# Evolution API Configuration
EVOLUTION_API_KEY=your_evolution_api_key
EVOLUTION_HOST_URL=https://your-evolution-api-host.com

# Django Configuration
SECRET_KEY=your_secret_key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
```

### Static Files
- Ensure all static files are collected
- Configure CDN for Bootstrap and custom CSS
- Optimize images and assets

### Database
- Configure production database (PostgreSQL recommended)
- Set up database backups
- Configure connection pooling

## Success Metrics

### Development Metrics
- ✅ User registration and login functionality
- ✅ Profile management with avatar upload
- ✅ Connection creation via Evolution API
- ✅ Connection status monitoring
- ✅ Dashboard with statistics
- ✅ Mobile-responsive design

### User Experience Metrics
- ✅ Intuitive navigation
- ✅ Clear connection status indicators
- ✅ Professional WhatsApp-inspired design
- ✅ Fast page load times
- ✅ Accessible interface

### Business Metrics
- ✅ Whitelabel experience (no mention of Evolution API/n8n)
- ✅ Professional appearance
- ✅ Easy connection management
- ✅ Scalable architecture for future features

## Risk Mitigation

### Technical Risks
- **Evolution API Integration**: Test thoroughly with Evolution API documentation
- **Database Performance**: Monitor query performance with user growth
- **Static File Serving**: Ensure proper CDN configuration

### User Experience Risks
- **Connection Failures**: Provide clear error messages and retry options
- **Mobile Experience**: Test extensively on various devices
- **Loading States**: Implement proper loading indicators

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1** | 1-2 weeks | User profile management system |
| **Phase 2** | 2-3 weeks | Evolution API connection management |
| **Phase 3** | 1 week | Dashboard integration |
| **Phase 4** | 0.5 weeks | Navigation and polish |
| **Total** | **4.5-6.5 weeks** | Complete implementation |

## Next Steps

1. **Start with Phase 1**: Implement user profile management
2. **Set up development environment**: Ensure Evolution API access
3. **Create database migrations**: Set up UserProfile model
4. **Build and test components**: Use Django Cotton for consistent UI
5. **Integrate Evolution API**: Test connection creation and management
6. **Polish and deploy**: Final testing and deployment

## Conclusion

This implementation plan provides a focused, achievable roadmap for building WozapAuto's core functionality. By leveraging the existing Bootstrap + Django Cotton architecture, we can deliver a professional whitelabel dashboard that effectively manages Evolution API connections while providing an excellent user experience.

The phased approach ensures steady progress while maintaining code quality and user experience standards. The final result will be a scalable foundation for future enhancements while delivering immediate value to users.
