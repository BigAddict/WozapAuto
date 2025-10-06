import json
import logging
import requests
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.views.generic import TemplateView
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Connection
from .services import evolution_api_service
from core.models import UserProfile
from core.email_service import email_service
from core.decorators import verified_email_required

# Set up logging
logger = logging.getLogger('connections.views')

@method_decorator([login_required, verified_email_required], name='dispatch')
class CreateConnectionView(TemplateView):
    template_name = "connections/connection_create.html"
    
    def get(self, request, *args, **kwargs):
        # Check for existing connection
        existing_connection = Connection.objects.filter(user=request.user).first()
        if existing_connection:
            if existing_connection.max_retries_reached:
                # Check if 2 hours have passed since last retry
                if existing_connection.can_retry():
                    # Reset retry status and allow new attempt
                    existing_connection.reset_retry_status()
                    messages.info(request, 'You can now try connecting again.')
                else:
                    messages.info(request, 'Please wait 2 hours before trying again.')
                    return redirect('connections:qr_display')
            else:
                messages.info(request, 'You already have a WhatsApp connection.')
                return redirect('connections:qr_display')
        
        return super().get(request, *args, **kwargs)
    
    def post(self, request: HttpRequest, *args, **kwargs):
        """Handle connection creation form submission with new flow"""
        logger.info(f"Connection creation attempt started for user: {request.user.username}")
        
        # Check for existing connection
        existing_connection = Connection.objects.filter(user=request.user).first()
        if existing_connection:
            if existing_connection.max_retries_reached and not existing_connection.can_retry():
                logger.warning(f"User {request.user.username} attempted connection during cooldown period")
                messages.info(request, 'Please wait 2 hours before trying again.')
                return redirect('connections:qr_display')
            elif not existing_connection.max_retries_reached:
                logger.info(f"User {request.user.username} already has existing connection")
                messages.info(request, 'You already have a WhatsApp connection.')
                return redirect('connections:qr_display')
        
        # Get form data
        company_name = request.POST.get('instance_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        
        logger.info(f"Connection creation form data - Company: {company_name}, Phone: {phone_number[:3]}***")
        
        # Validate required fields
        if not company_name or not phone_number:
            logger.warning(f"Missing required fields for user {request.user.username}")
            messages.error(request, 'Company name and WhatsApp number are required.')
            return redirect('connections:create')
        
        # Validate WhatsApp number format
        if not phone_number.startswith('+') or not phone_number[1:].isdigit():
            messages.error(request, 'Please enter a valid WhatsApp number with country code (e.g., +1234567890).')
            return redirect('connections:create')
        
        try:
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Update profile with company name and WhatsApp number
            profile.company_name = company_name
            profile.phone_number = phone_number
            profile.save()
            
            logger.info(f"User profile updated for {request.user.username}")
            
            # Create Evolution API instance (always with QR code)
            from .models import EvolutionInstanceCreate
            # Remove + sign for Evolution API (it requires format without +)
            evolution_phone = phone_number[1:] if phone_number.startswith('+') else phone_number
            instance_create = EvolutionInstanceCreate(
                instance_name=company_name,
                phone_number=evolution_phone,
                connect_now=True  # Always use QR code method
            )
            
            logger.info(f"Calling Evolution API to create instance: {company_name}")
            success, result = evolution_api_service.create_instance(instance_create, user_id=request.user.id)
            
            if success:
                # Save connection to database (NO QR code storage)
                connection = Connection.objects.create(
                    user=request.user,
                    instance_id=result.instance.instance_id,
                    instance_name=company_name,
                    ownerPhone=phone_number,
                    profileName=company_name,
                    connection_status='connecting',
                    instance_api_key=result.instance.access_token_wa_business,
                    connection_phase='waiting'  # Set initial phase
                )
                
                logger.info(f"Connection created successfully for user {request.user.username}, instance_id: {result.instance.instance_id}")
                messages.success(request, 'WhatsApp connection created! Please scan the QR code.')
                return redirect('connections:qr_display')
            else:
                logger.error(f"Evolution API failed to create instance for user {request.user.username}: {result}")
                messages.error(request, f'Failed to create connection: {result}')
                return redirect('connections:create')
                
        except Exception as e:
            logger.error(f"Unexpected error during connection creation for user {request.user.username}: {str(e)}", exc_info=True)
            messages.error(request, 'An unexpected error occurred. Please try again.')
            return redirect('connections:create')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user profile data to pre-populate form
        try:
            profile = UserProfile.objects.get(user=self.request.user)
            context['profile'] = profile
        except UserProfile.DoesNotExist:
            context['profile'] = None
        return context


@method_decorator([login_required, verified_email_required], name='dispatch')
class QRCodeDisplayView(TemplateView):
    """Dedicated page for QR code and pairing code display"""
    template_name = "connections/qr_display.html"
    
    def get(self, request, *args, **kwargs):
        # Check if user has a connection
        connection = Connection.objects.filter(user=request.user).first()
        if not connection:
            messages.info(request, 'No connection found. Please create a connection first.')
            return redirect('connections:create')
        
        # Check if connection is already connected
        if connection.is_connected():
            messages.info(request, 'Your WhatsApp is already connected!')
            return redirect('connections:detail')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        connection = Connection.objects.filter(user=self.request.user).first()
        
        if connection:
            # Always fetch fresh QR code data from Evolution API
            try:
                success, qr_data = evolution_api_service.get_instance_qrcode(connection.instance_name)
                if success:
                    context['qr_code_data'] = {
                        'pairing_code': qr_data.pairing_code or 'N/A',
                        'base64': qr_data.base64,
                        'count': qr_data.count
                    }
                else:
                    context['qr_error'] = qr_data
            except Exception as e:
                context['qr_error'] = f"Error fetching QR code: {str(e)}"
            
            # Add connection and retry info
            context['connection'] = connection
            context['retry_info'] = {
                'retry_count': connection.retry_count,
                'max_retries_reached': connection.max_retries_reached,
                'last_retry_at': connection.last_retry_at,
                'connection_phase': connection.connection_phase,
                'can_retry': connection.can_retry(),
                'qr_code_requests': connection.qr_code_requests,
                'max_qr_requests_reached': connection.max_qr_requests_reached,
                'can_request_qr_code': connection.can_request_qr_code()
            }
        
        return context


@method_decorator([login_required, verified_email_required], name='dispatch')
class ConnectionDetailView(TemplateView):
    """Connection detail page - only accessible when connected"""
    template_name = "connections/connection_detail.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        # Check if user has a connection
        connection = Connection.objects.filter(user=request.user).first()
        if not connection:
            messages.info(request, 'No connection found. Please create a connection first.')
            return redirect('connections:create')
        
        # Check if connection is connected - if not, redirect to QR display
        if not connection.is_connected():
            messages.info(request, 'Please complete the connection process first.')
            return redirect('connections:qr_display')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        connection = Connection.objects.filter(user=self.request.user).first()
        
        if connection:
            # Get real-time instance data from Evolution API
            try:
                success, instance_data = evolution_api_service.get_instance(connection.instance_id)
                if success:
                    context['instance_data'] = instance_data
                    # Update connection status in database
                    connection.connection_status = instance_data.connection_status
                    if instance_data.connection_status == 'open':
                        connection.connection_phase = 'connected'
                    connection.save()
                else:
                    context['api_error'] = instance_data
            except Exception as e:
                context['api_error'] = f"Error fetching instance data: {str(e)}"
            
            context['connection'] = connection
        
        return context




# API Endpoints for new connection flow

@login_required
def connection_status_api(request):
    """API endpoint for checking connection status"""
    if request.method != 'GET':
        logger.warning(f"Invalid method {request.method} for status API by user {request.user.username}")
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    connection = Connection.objects.filter(user=request.user).first()
    if not connection:
        logger.warning(f"Status API called but no connection found for user {request.user.username}")
        return JsonResponse({'error': 'No connection found'}, status=404)
    
    try:
        logger.debug(f"Checking connection status for user {request.user.username}, instance: {connection.instance_id}")
        success, instance_data = evolution_api_service.get_instance(connection.instance_id)
        if success:
            # Update connection status in database
            old_status = connection.connection_status
            connection.connection_status = instance_data.connection_status
            if instance_data.connection_status == 'open':
                connection.connection_phase = 'connected'
            connection.save()
            
            if old_status != instance_data.connection_status:
                logger.info(f"Connection status changed for user {request.user.username}: {old_status} -> {instance_data.connection_status}")
                
                # Send connection success email if status changed to 'open'
                if old_status != 'open' and instance_data.connection_status == 'open':
                    try:
                        email_service.send_connection_success_email(request.user, connection, request)
                        logger.info(f"Connection success email sent to {request.user.email}")
                    except Exception as e:
                        logger.error(f"Failed to send connection success email to {request.user.email}: {str(e)}")
            
            return JsonResponse({
                'status': 'success',
                'connection_status': instance_data.connection_status,
                'connection_phase': connection.connection_phase,
                'profile_name': instance_data.profile_name or 'N/A',
                'phone_number': instance_data.phone_number or 'N/A',
                'messages_count': instance_data.count.messages,
                'contacts_count': instance_data.count.contacts,
                'chats_count': instance_data.count.chat
            })
        else:
            logger.error(f"Failed to get instance data for user {request.user.username}: {instance_data}")
            return JsonResponse({
                'status': 'error',
                'message': instance_data
            }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in status API for user {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)


@login_required
def connection_retry_api(request):
    """API endpoint for handling retry logic"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    connection = Connection.objects.filter(user=request.user).first()
    if not connection:
        return JsonResponse({'error': 'No connection found'}, status=404)
    
    # Check if max retries reached
    if connection.max_retries_reached and not connection.can_retry():
        return JsonResponse({
            'status': 'error',
            'message': 'Maximum retries reached. Please wait 2 hours or contact support.'
        }, status=400)
    
    try:
        # Disconnect current instance
        success, disconnect_result = evolution_api_service.disconnect_instance(connection.instance_name)
        
        if success:
            # Get new QR code (always fetch fresh from Evolution API)
            success, qr_data = evolution_api_service.get_instance_qrcode(connection.instance_name)
            
            if success:
                # Update connection with retry count
                connection.increment_retry()
                
                return JsonResponse({
                    'status': 'success',
                    'qr_code_data': {
                        'pairing_code': qr_data.pairing_code or 'N/A',
                        'base64': qr_data.base64,
                        'count': qr_data.count
                    },
                    'retry_count': connection.retry_count,
                    'max_retries_reached': connection.max_retries_reached,
                    'connection_phase': connection.connection_phase
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Failed to get new QR code: {qr_data}'
                }, status=400)
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to disconnect: {disconnect_result}'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
    
def qr_request_api(request):
    """API endpoint to request a new QR code with rate limiting"""
    logger.info(f"QR code request API called by user: {request.user.username}")
    
    connection = Connection.objects.filter(user=request.user).first()
    if not connection:
        return JsonResponse({'error': 'No connection found'}, status=404)
    
    # Check if user can request a new QR code
    if not connection.can_request_qr_code():
        if connection.max_qr_requests_reached:
            return JsonResponse({
                'status': 'error',
                'message': 'Maximum QR code requests reached. Please wait 2 hours before requesting again.'
            }, status=429)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Cannot request QR code at this time.'
            }, status=400)
    
    try:
        # Increment QR code request count
        connection.increment_qr_request()
        
        # Get new QR code from Evolution API
        success, qr_data = evolution_api_service.get_instance_qrcode(connection.instance_name)
        
        if success:
            logger.info(f"New QR code generated for user {request.user.username}, request count: {connection.qr_code_requests}")
            return JsonResponse({
                'status': 'success',
                'qr_code_data': {
                    'pairing_code': qr_data.pairing_code or 'N/A',
                    'base64': qr_data.base64,
                    'count': qr_data.count
                },
                'qr_code_requests': connection.qr_code_requests
            })
        else:
            logger.error(f"Failed to get QR code for user {request.user.username}: {qr_data}")
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to generate QR code: {qr_data}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error requesting QR code for user {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while requesting QR code.'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def disconnect_api(request):
    """API endpoint to disconnect instance when user leaves the page"""
    logger.info(f"Disconnect API called by user: {request.user.username}")
    
    connection = Connection.objects.filter(user=request.user).first()
    if not connection:
        return JsonResponse({'error': 'No connection found'}, status=404)
    
    try:
        # Disconnect the instance in Evolution API
        success, result = evolution_api_service.disconnect_instance(connection.instance_name)
        
        if success:
            # Update connection status
            connection.connection_status = 'close'
            connection.connection_phase = 'failed'
            connection.save()
            
            logger.info(f"Instance disconnected for user {request.user.username}")
            return JsonResponse({
                'status': 'success',
                'message': 'Instance disconnected successfully'
            })
        else:
            logger.error(f"Failed to disconnect instance for user {request.user.username}: {result}")
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to disconnect: {result}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error disconnecting instance for user {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while disconnecting.'
        }, status=500)


@login_required
def connection_help_api(request):
    """API endpoint for sending help request"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    connection = Connection.objects.filter(user=request.user).first()
    if not connection:
        return JsonResponse({'error': 'No connection found'}, status=404)
    
    try:
        # Send help request to n8n webhook
        help_data = {
            'phone_number': connection.ownerPhone,
            'username': request.user.username,
            'message': f'Connection help needed for {connection.instance_name}. Retry count: {connection.retry_count}'
        }
        
        response = requests.post(
            'https://n8n.bigaddict.shop/webhook-test/wozapauto/help',
            json=help_data,
            timeout=10
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'status': 'success',
                'message': 'Help request sent successfully. Our team will contact you soon.'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to send help request. Please try again later.'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def connection_test_api(request):
    """API endpoint for testing connection by sending test message"""
    logger.info(f"Connection test API called by user: {request.user.username}")
    
    connection = Connection.objects.filter(user=request.user).first()
    if not connection:
        return JsonResponse({'error': 'No connection found'}, status=404)
    
    # Check if connection is connected
    if not connection.is_connected():
        return JsonResponse({
            'status': 'error',
            'message': 'Connection is not active. Please ensure your WhatsApp is connected first.'
        }, status=400)
    
    try:
        # Get data from request body
        import json
        data = json.loads(request.body)
        instance_name = data.get('instance_name', connection.instance_name)
        phone_number = data.get('phone_number', connection.ownerPhone)
        
        # Send test request to n8n webhook
        test_data = {
            'instance_name': instance_name,
            'phone_number': phone_number
        }
        
        logger.info(f"Sending test request for user {request.user.username}: {test_data}")
        
        response = requests.post(
            'https://n8n.bigaddict.shop/webhook-test/wozapauto/test-message',
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json() if response.content else {}
            logger.info(f"Test request successful for user {request.user.username}")
            return JsonResponse({
                'status': 'success',
                'message': response_data.get('message', 'Test message sent successfully! Check your WhatsApp for the test message.'),
                'response_data': response_data
            })
        else:
            logger.error(f"Test request failed for user {request.user.username}: HTTP {response.status_code}")
            return JsonResponse({
                'status': 'error',
                'message': f'Test request failed with status {response.status_code}. Please try again later.'
            }, status=400)
            
    except requests.exceptions.Timeout:
        logger.error(f"Test request timeout for user {request.user.username}")
        return JsonResponse({
            'status': 'error',
            'message': 'Test request timed out. Please try again later.'
        }, status=408)
    except requests.exceptions.RequestException as e:
        logger.error(f"Test request error for user {request.user.username}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to send test request. Please check your connection and try again.'
        }, status=500)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in test request for user {request.user.username}")
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request data. Please try again.'
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in test API for user {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred. Please try again later.'
        }, status=500)