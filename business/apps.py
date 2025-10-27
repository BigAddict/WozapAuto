from django.apps import AppConfig


class BusinessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'business'
    verbose_name = 'Business Profile'
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        try:
            import business.signals
        except ImportError:
            pass