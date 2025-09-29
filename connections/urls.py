from django.urls import path

from .views import (
    CreateConnectionView, 
    ConnectionDetailView,
    ConnectionManageView
)

app_name = 'connections'

urlpatterns = [
    # Main views using class-based views
    path('', ConnectionManageView.as_view(), name='manage'),
    path('create/', CreateConnectionView.as_view(), name='create'),
    path('detail/', ConnectionDetailView.as_view(), name='detail'),
]