from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile

# Signup View
def signup(request):
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            login(request, user)
            messages.success(request, 'Account created successfully')
            return redirect('home')

        except IntegrityError:
            messages.error(request, 'Username already exists')
            return redirect('signup')

    return render(request, 'core/signup.html')

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