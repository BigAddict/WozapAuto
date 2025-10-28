"""
Core app tests - Test discovery and organization.

This file serves as the main test discovery point for the core app.
All actual tests are organized in the tests/ directory with proper
separation of concerns.
"""

from django.test import TestCase

# This file is kept for Django's test discovery mechanism
# All actual tests are in the tests/ directory:
# - tests/test_models.py - Model tests
# - tests/test_forms.py - Form tests  
# - tests/test_views.py - View tests
# - tests/test_onboarding.py - Comprehensive onboarding tests

class CoreTestDiscovery(TestCase):
    """Test discovery placeholder for core app."""
    
    def test_core_app_imports(self):
        """Test that core app can be imported without errors."""
        try:
            from core import models, forms, views, onboarding_views
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Core app import failed: {e}")
    
    def test_core_app_configuration(self):
        """Test that core app is properly configured."""
        from django.apps import apps
        app_config = apps.get_app_config('core')
        self.assertEqual(app_config.name, 'core')
        self.assertEqual(app_config.label, 'core')