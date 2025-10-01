"""
Custom logging filters for WozapAuto
"""
import logging
import uuid
from django.utils.deprecation import MiddlewareMixin


class UserInfoFilter(logging.Filter):
    """
    Add user information and request ID to log records
    """
    
    def filter(self, record):
        # Add user information if available
        if hasattr(record, 'request'):
            request = record.request
            record.user = getattr(request, 'user', None)
            if hasattr(record.user, 'username'):
                record.user = record.user.username
            else:
                record.user = 'anonymous'
            
            # Add request ID if available
            record.request_id = getattr(request, 'request_id', 'no-request-id')
        else:
            record.user = 'system'
            record.request_id = 'no-request-id'
        
        return True


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to add request ID and user info to all requests
    """
    
    def process_request(self, request):
        # Generate unique request ID
        request.request_id = str(uuid.uuid4())[:8]
        
        # Add request to thread local storage for logging
        import threading
        thread_local = threading.local()
        thread_local.request = request
        
        return None
    
    def process_response(self, request, response):
        # Clean up thread local storage
        import threading
        thread_local = threading.local()
        if hasattr(thread_local, 'request'):
            delattr(thread_local, 'request')
        
        return response
