from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView
from django.contrib import messages
from django.shortcuts import render, redirect

from .models import Connection
from .services import evolution_api_service


class CreateConnectionView(TemplateView):
    template_name = "connections/connection_create.html"
    
    def get(self, request, *args, **kwargs):
        # Check if user already has a connection
        existing_connection = Connection.objects.filter(user=request.user).first()
        if existing_connection:
            messages.info(request, 'You already have a WhatsApp connection. You can only have one connection at a time.')
            return redirect('connections:manage')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ConnectionDetailView(TemplateView):
    template_name = "connections/connection_detail.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        # Check if user has a connection
        connection = Connection.objects.filter(user=request.user).first()
        if not connection:
            messages.info(request, 'No connection found. Please create a connection first.')
            return redirect('connections:create')
        
        self.user = request.user
        return super().get(request, *args, **kwargs)

    def get_user_instance(self):
        try:
            connection = Connection.objects.get(user_id=self.user.id)
            success, instance = evolution_api_service.get_instance(connection.instance_id)
            if not success:
                return None
            return instance
        except Connection.DoesNotExist:
            return None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['connection'] = self.get_user_instance()
        return context


class ConnectionManageView(TemplateView):
    """Manage existing connection - redirects to create if no connection exists"""
    template_name = "connections/connection_manage.html"
    
    def get(self, request, *args, **kwargs):
        connection = Connection.objects.filter(user=request.user).first()
        
        if not connection:
            # No connection exists, redirect to create
            return redirect('connections:create')
        
        # Get real-time data for the connection
        try:
            success, instance_data = evolution_api_service.get_instance(connection.instance_id)
            if success:
                connection.messages_count = instance_data.count.messages
                connection.contacts_count = instance_data.count.contacts
                connection.chats_count = instance_data.count.chat
                connection.real_status = instance_data.connection_status
            else:
                connection.messages_count = 0
                connection.contacts_count = 0
                connection.chats_count = 0
                connection.real_status = connection.connection_status
        except:
            connection.messages_count = 0
            connection.contacts_count = 0
            connection.chats_count = 0
            connection.real_status = connection.connection_status
        
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the connection with real-time data
        connection = Connection.objects.filter(user=self.request.user).first()
        if connection:
            try:
                success, instance_data = evolution_api_service.get_instance(connection.instance_id)
                if success:
                    connection.messages_count = instance_data.count.messages
                    connection.contacts_count = instance_data.count.contacts
                    connection.chats_count = instance_data.count.chat
                    connection.real_status = instance_data.connection_status
                else:
                    connection.messages_count = 0
                    connection.contacts_count = 0
                    connection.chats_count = 0
                    connection.real_status = connection.connection_status
            except:
                connection.messages_count = 0
                connection.contacts_count = 0
                connection.chats_count = 0
                connection.real_status = connection.connection_status
        
        context['connection'] = connection
        return context