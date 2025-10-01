"""
Email service utility for WozapAuto.
Handles sending various types of emails including welcome, password reset, and connection notifications.
"""

import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger('core.email_service')

class EmailService:
    """Service class for sending various types of emails"""
    
    @staticmethod
    def _log_email(email_type, recipient_email, subject, template_used, context_data=None, 
                   recipient_user=None, request=None, status='pending'):
        """Log email to audit system"""
        try:
            from audit.models import EmailLog
            
            # Extract request metadata if available
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                email_type=email_type,
                recipient_email=recipient_email,
                recipient_user=recipient_user,
                subject=subject,
                template_used=template_used,
                context_data=context_data or {},
                ip_address=ip_address,
                user_agent=user_agent,
                status=status
            )
            
            return email_log
            
        except Exception as e:
            logger.error(f"Failed to log email: {str(e)}")
            return None
    
    @staticmethod
    def send_welcome_email(user, request=None):
        """
        Send welcome email to newly registered user
        
        Args:
            user: User instance
            request: HttpRequest instance (optional, for logging)
        """
        subject = f"Welcome to WozapAuto, {user.first_name or user.username}!"
        template_used = 'core/emails/welcome_email.html'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'site_name': 'WozapAuto',
        }
        
        # Log email attempt
        email_log = EmailService._log_email(
            email_type='welcome',
            recipient_email=user.email,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Render HTML template
            html_content = render_to_string(template_used, {
                'user': user,
                'site_name': 'WozapAuto',
                'login_url': settings.SITE_URL + reverse('signin') if hasattr(settings, 'SITE_URL') else 'http://localhost:8000/signin/'
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            # Mark as sent in audit log
            if email_log:
                email_log.mark_sent()
            
            logger.info(f"Welcome email sent successfully to {user.email}")
            return True
            
        except Exception as e:
            # Mark as failed in audit log
            if email_log:
                email_log.mark_failed(str(e))
            
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user, request):
        """
        Send password reset email to user
        
        Args:
            user: User instance
            request: HttpRequest instance
        """
        subject = "Reset Your WozapAuto Password"
        template_used = 'core/emails/password_reset_email.html'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'site_name': 'WozapAuto',
            'request_ip': request.META.get('REMOTE_ADDR'),
        }
        
        # Log email attempt
        email_log = EmailService._log_email(
            email_type='password_reset',
            recipient_email=user.email,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            
            # Update context data with reset URL for logging
            context_data['reset_url'] = reset_url
            context_data['token_generated'] = True
            
            # Render HTML template
            html_content = render_to_string(template_used, {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'WozapAuto'
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            # Mark as sent in audit log
            if email_log:
                email_log.mark_sent()
            
            logger.info(f"Password reset email sent successfully to {user.email}")
            return True
            
        except Exception as e:
            # Mark as failed in audit log
            if email_log:
                email_log.mark_failed(str(e))
            
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_connection_success_email(user, connection, request=None):
        """
        Send WhatsApp connection success email to user
        
        Args:
            user: User instance
            connection: Connection instance
            request: HttpRequest instance (optional, for logging)
        """
        subject = f"WhatsApp Connection Successful - {connection.instance_name}"
        template_used = 'core/emails/connection_success_email.html'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'connection_id': connection.id,
            'instance_name': connection.instance_name,
            'instance_id': connection.instance_id,
            'owner_phone': connection.ownerPhone,
            'connection_status': connection.connection_status,
            'site_name': 'WozapAuto',
        }
        
        # Log email attempt
        email_log = EmailService._log_email(
            email_type='connection_success',
            recipient_email=user.email,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Render HTML template
            html_content = render_to_string(template_used, {
                'user': user,
                'connection': connection,
                'site_name': 'WozapAuto',
                'dashboard_url': settings.SITE_URL + reverse('home') if hasattr(settings, 'SITE_URL') else 'http://localhost:8000/'
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            # Mark as sent in audit log
            if email_log:
                email_log.mark_sent()
            
            logger.info(f"Connection success email sent successfully to {user.email}")
            return True
            
        except Exception as e:
            # Mark as failed in audit log
            if email_log:
                email_log.mark_failed(str(e))
            
            logger.error(f"Failed to send connection success email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_change_confirmation_email(user, request=None):
        """
        Send password change confirmation email to user
        
        Args:
            user: User instance
            request: HttpRequest instance (optional, for logging)
        """
        subject = "Password Changed Successfully - WozapAuto"
        template_used = 'core/emails/password_change_email.html'
        
        # Prepare context data for logging
        context_data = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'site_name': 'WozapAuto',
            'change_timestamp': timezone.now().isoformat(),
        }
        
        # Log email attempt
        email_log = EmailService._log_email(
            email_type='password_change',
            recipient_email=user.email,
            subject=subject,
            template_used=template_used,
            context_data=context_data,
            recipient_user=user,
            request=request
        )
        
        try:
            # Render HTML template
            html_content = render_to_string(template_used, {
                'user': user,
                'site_name': 'WozapAuto',
                'login_url': settings.SITE_URL + reverse('signin') if hasattr(settings, 'SITE_URL') else 'http://localhost:8000/signin/'
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            # Mark as sent in audit log
            if email_log:
                email_log.mark_sent()
            
            logger.info(f"Password change confirmation email sent successfully to {user.email}")
            return True
            
        except Exception as e:
            # Mark as failed in audit log
            if email_log:
                email_log.mark_failed(str(e))
            
            logger.error(f"Failed to send password change confirmation email to {user.email}: {str(e)}")
            return False

# Create a singleton instance
email_service = EmailService()
