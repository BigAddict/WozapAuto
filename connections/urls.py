from django.urls import path

from .views import (
    CreateConnectionView, 
    ConnectionDetailView,
    QRCodeDisplayView,
    connection_status_api,
    connection_retry_api,
    connection_help_api,
    connection_test_api,
    qr_request_api,
    disconnect_api
)

app_name = 'connections'

urlpatterns = [
    # Main views using class-based views
    path('', QRCodeDisplayView.as_view(), name='qr_display'),  # Default to QR display
    path('create/', CreateConnectionView.as_view(), name='create'),
    path('detail/', ConnectionDetailView.as_view(), name='detail'),
    
    # API endpoints for new connection flow
    path('api/status/', connection_status_api, name='status_api'),
    path('api/retry/', connection_retry_api, name='retry_api'),
    path('api/help/', connection_help_api, name='help_api'),
    path('api/test/', connection_test_api, name='test_api'),
    path('api/qr-request/', qr_request_api, name='qr_request_api'),
    path('api/disconnect/', disconnect_api, name='disconnect_api'),
]