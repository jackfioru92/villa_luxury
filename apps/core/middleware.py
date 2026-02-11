"""Middleware for maintenance mode."""
from django.shortcuts import render
from django.conf import settings
import os


class MaintenanceMiddleware:
    """
    Middleware to enable maintenance mode.
    Set MAINTENANCE_MODE=True in .env to activate.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if maintenance mode is enabled via environment variable
        maintenance_mode = os.environ.get('MAINTENANCE_MODE', 'False').lower() == 'true'
        
        # Allow admins to bypass maintenance mode
        if maintenance_mode and not request.user.is_staff:
            # Allow access to admin and static/media files
            if not request.path.startswith('/admin/') and \
               not request.path.startswith('/static/') and \
               not request.path.startswith('/media/'):
                return render(request, 'maintenance.html', status=503)
        
        response = self.get_response(request)
        return response
