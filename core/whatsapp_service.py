"""
WhatsApp service utility for WozapAuto.
Handles sending various types of WhatsApp messages including welcome, OTP verification, and notifications.
"""

import logging
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from .models import UserProfile
from connections.services import evolution_api_service
from connections.models import Connection

logger = logging.getLogger('core.whatsapp_service')

class WhatsAppService:
    """Service class for sending various types of WhatsApp messages"""
    
    @staticmethod
    def _log_whatsapp_message(message_type, recipient_phone, subject, template_used, context_data=None, 
                             recipient_user=None, request=None, status='pending', connection_used=None):
        """Log WhatsApp message to audit system"""
        try:
            from audit.models import NotificationLog
            
            # Extract request metadata if available
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Create message log entry
            message_log = NotificationLog.objects.create(
                notification_type=message_type,
                recipient_phone=recipient_phone,
                recipient_user=recipient_user,
                subject=subject,
                template_used=template_used,
                context_data=context_data or {},
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                connection_used=connection_used
            )
            
            return message_log
            
        except Exception as e:
            logger.error(f"Failed to log WhatsApp message: {str(e)}")
            return None
    
    @staticmethod
    def _get_admin_connection():
        """Get an active admin connection to send messages"""
        try:
            admin_connection = Connection.objects.filter(
                user__is_superuser=True, 
                connection_status='open'
            ).first()
            
            if not admin_connection:
                logger.error("No admin WhatsApp connection available. At least one admin must have an active connection.")
                return None, "No admin WhatsApp connection available. Please contact system administrator."
            
            return admin_connection, None
            
        except Exception as e:
            logger.error(f"Error getting admin connection: {str(e)}")
            return None, f"Error getting admin connection: {str(e)}"
    
    @staticmethod
    def _format_phone_number(phone_number):
        """Format phone number for WhatsApp (remove + and any non-digits)"""
        if not phone_number:
            return None
        # Remove + and any non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        return cleaned
    
    @staticmethod
    def send_welcome_message(user, request=None):
        """
        Send welcome WhatsApp message to newly registered user
        
        Args:
            user: User instance
            request: HttpRequest instance (optional, for logging)
        """
        if not user.profile.phone_number:
            logger.error(f"No phone number found for user {user.id}")
            return False
        
        subject = f"Welcome to WozapAuto, {user.first_name or user.username}!"
        template_used = 'whatsapp/welcome_message'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.profile.phone_number,
            'site_name': 'WozapAuto',
        }
        
        # Log message attempt
        message_log = WhatsAppService._log_whatsapp_message(
            message_type='welcome',
            recipient_phone=user.profile.phone_number,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Get admin connection
            admin_connection, error = WhatsAppService._get_admin_connection()
            if not admin_connection:
                if message_log:
                    message_log.mark_failed(error)
                return False
            
            # Format message content
            message_content = f"""*Welcome to WozapAuto!* 👋

Hi {user.first_name or user.username},

Your account has been created successfully.

To get started, please complete your profile setup.

Need help? Reply to this message."""
            
            # Send WhatsApp message
            success, response = evolution_api_service.send_text_message(
                instance_name=admin_connection.instance_name,
                number=WhatsAppService._format_phone_number(user.profile.phone_number),
                message=message_content
            )
            
            if success:
                # Mark as sent in audit log
                if message_log:
                    message_log.mark_sent()
                
                logger.info(f"Welcome WhatsApp message sent successfully to {user.profile.phone_number}")
                return True
            else:
                # Mark as failed in audit log
                if message_log:
                    message_log.mark_failed(response)
                
                logger.error(f"Failed to send welcome WhatsApp message to {user.profile.phone_number}: {response}")
                return False
                
        except Exception as e:
            # Mark as failed in audit log
            if message_log:
                message_log.mark_failed(str(e))
            
            logger.error(f"Failed to send welcome WhatsApp message to {user.profile.phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_otp_message(user, otp_code, request=None):
        """
        Send OTP verification WhatsApp message to user
        
        Args:
            user: User instance
            otp_code: OTP code to send
            request: HttpRequest instance (optional, for logging)
        """
        if not user.profile.phone_number:
            logger.error(f"No phone number found for user {user.id}")
            return False
        
        subject = "Verify Your WhatsApp Number - WozapAuto"
        template_used = 'whatsapp/otp_message'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'phone_number': user.profile.phone_number,
            'otp_code': otp_code,
            'site_name': 'WozapAuto',
        }
        
        # Log message attempt
        message_log = WhatsAppService._log_whatsapp_message(
            message_type='otp_verification',
            recipient_phone=user.profile.phone_number,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Get admin connection
            admin_connection, error = WhatsAppService._get_admin_connection()
            if not admin_connection:
                if message_log:
                    message_log.mark_failed(error)
                return False
            
            # Format message content
            message_content = f"""*WozapAuto Verification* 🔐

Hi {user.first_name or user.username},

To verify your WhatsApp number, use this code:
*{otp_code}*

This code expires in 10 minutes.

Need help? Reply to this message."""
            
            # Send WhatsApp message
            success, response = evolution_api_service.send_text_message(
                instance_name=admin_connection.instance_name,
                number=WhatsAppService._format_phone_number(user.profile.phone_number),
                message=message_content
            )
            
            if success:
                # Mark as sent in audit log
                if message_log:
                    message_log.mark_sent()
                
                logger.info(f"OTP WhatsApp message sent successfully to {user.profile.phone_number}")
                return True
            else:
                # Mark as failed in audit log
                if message_log:
                    message_log.mark_failed(response)
                
                logger.error(f"Failed to send OTP WhatsApp message to {user.profile.phone_number}: {response}")
                return False
                
        except Exception as e:
            # Mark as failed in audit log
            if message_log:
                message_log.mark_failed(str(e))
            
            logger.error(f"Failed to send OTP WhatsApp message to {user.profile.phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_message(user, reset_url, request=None):
        """
        Send password reset WhatsApp message to user
        
        Args:
            user: User instance
            reset_url: Password reset URL
            request: HttpRequest instance (optional, for logging)
        """
        if not user.profile.phone_number:
            logger.error(f"No phone number found for user {user.id}")
            return False
        
        subject = "Reset Your WozapAuto Password"
        template_used = 'whatsapp/password_reset_message'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'phone_number': user.profile.phone_number,
            'reset_url': reset_url,
            'site_name': 'WozapAuto',
        }
        
        # Log message attempt
        message_log = WhatsAppService._log_whatsapp_message(
            message_type='password_reset',
            recipient_phone=user.profile.phone_number,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Get admin connection
            admin_connection, error = WhatsAppService._get_admin_connection()
            if not admin_connection:
                if message_log:
                    message_log.mark_failed(error)
                return False
            
            # Format message content
            message_content = f"""*Password Reset Request* 🔑

Hi {user.first_name or user.username},

You requested to reset your password.

Click here to reset: {reset_url}

This link expires in 24 hours.

If you didn't request this, please ignore this message."""
            
            # Send WhatsApp message
            success, response = evolution_api_service.send_text_message(
                instance_name=admin_connection.instance_name,
                number=WhatsAppService._format_phone_number(user.profile.phone_number),
                message=message_content
            )
            
            if success:
                # Mark as sent in audit log
                if message_log:
                    message_log.mark_sent()
                
                logger.info(f"Password reset WhatsApp message sent successfully to {user.profile.phone_number}")
                return True
            else:
                # Mark as failed in audit log
                if message_log:
                    message_log.mark_failed(response)
                
                logger.error(f"Failed to send password reset WhatsApp message to {user.profile.phone_number}: {response}")
                return False
                
        except Exception as e:
            # Mark as failed in audit log
            if message_log:
                message_log.mark_failed(str(e))
            
            logger.error(f"Failed to send password reset WhatsApp message to {user.profile.phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_connection_success_message(user, connection, request=None):
        """
        Send WhatsApp connection success message to user
        
        Args:
            user: User instance
            connection: Connection instance
            request: HttpRequest instance (optional, for logging)
        """
        if not user.profile.phone_number:
            logger.error(f"No phone number found for user {user.id}")
            return False
        
        subject = f"WhatsApp Connection Successful - {connection.instance_name}"
        template_used = 'whatsapp/connection_success_message'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'phone_number': user.profile.phone_number,
            'connection_id': connection.id,
            'instance_name': connection.instance_name,
            'instance_id': connection.instance_id,
            'owner_phone': connection.ownerPhone,
            'connection_status': connection.connection_status,
            'site_name': 'WozapAuto',
        }
        
        # Log message attempt
        message_log = WhatsAppService._log_whatsapp_message(
            message_type='connection_success',
            recipient_phone=user.profile.phone_number,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Get admin connection
            admin_connection, error = WhatsAppService._get_admin_connection()
            if not admin_connection:
                if message_log:
                    message_log.mark_failed(error)
                return False
            
            # Format message content
            message_content = f"""*WhatsApp Connection Successful!* ✅

Hi {user.first_name or user.username},

Your WhatsApp connection "{connection.instance_name}" is now active.

You can now start using your WhatsApp automation features.

Dashboard: {settings.SITE_URL + reverse('home') if hasattr(settings, 'SITE_URL') else 'http://localhost:8000/'}

Need help? Reply to this message."""
            
            # Send WhatsApp message
            success, response = evolution_api_service.send_text_message(
                instance_name=admin_connection.instance_name,
                number=WhatsAppService._format_phone_number(user.profile.phone_number),
                message=message_content
            )
            
            if success:
                # Mark as sent in audit log
                if message_log:
                    message_log.mark_sent()
                
                logger.info(f"Connection success WhatsApp message sent successfully to {user.profile.phone_number}")
                return True
            else:
                # Mark as failed in audit log
                if message_log:
                    message_log.mark_failed(response)
                
                logger.error(f"Failed to send connection success WhatsApp message to {user.profile.phone_number}: {response}")
                return False
                
        except Exception as e:
            # Mark as failed in audit log
            if message_log:
                message_log.mark_failed(str(e))
            
            logger.error(f"Failed to send connection success WhatsApp message to {user.profile.phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_change_confirmation_message(user, request=None):
        """
        Send password change confirmation WhatsApp message to user
        
        Args:
            user: User instance
            request: HttpRequest instance (optional, for logging)
        """
        if not user.profile.phone_number:
            logger.error(f"No phone number found for user {user.id}")
            return False
        
        subject = "Password Changed Successfully - WozapAuto"
        template_used = 'whatsapp/password_change_message'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'phone_number': user.profile.phone_number,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'site_name': 'WozapAuto',
            'change_timestamp': timezone.now().isoformat(),
        }
        
        # Log message attempt
        message_log = WhatsAppService._log_whatsapp_message(
            message_type='password_change',
            recipient_phone=user.profile.phone_number,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Get admin connection
            admin_connection, error = WhatsAppService._get_admin_connection()
            if not admin_connection:
                if message_log:
                    message_log.mark_failed(error)
                return False
            
            # Format message content
            message_content = f"""*Password Changed Successfully* 🔐

Hi {user.first_name or user.username},

Your password has been changed successfully.

If you didn't make this change, please contact support immediately.

Login: {settings.SITE_URL + reverse('signin') if hasattr(settings, 'SITE_URL') else 'http://localhost:8000/signin/'}

Need help? Reply to this message."""
            
            # Send WhatsApp message
            success, response = evolution_api_service.send_text_message(
                instance_name=admin_connection.instance_name,
                number=WhatsAppService._format_phone_number(user.profile.phone_number),
                message=message_content
            )
            
            if success:
                # Mark as sent in audit log
                if message_log:
                    message_log.mark_sent()
                
                logger.info(f"Password change confirmation WhatsApp message sent successfully to {user.profile.phone_number}")
                return True
            else:
                # Mark as failed in audit log
                if message_log:
                    message_log.mark_failed(response)
                
                logger.error(f"Failed to send password change confirmation WhatsApp message to {user.profile.phone_number}: {response}")
                return False
                
        except Exception as e:
            # Mark as failed in audit log
            if message_log:
                message_log.mark_failed(str(e))
            
            logger.error(f"Failed to send password change confirmation WhatsApp message to {user.profile.phone_number}: {str(e)}")
            return False


# Create a singleton instance
whatsapp_service = WhatsAppService()
