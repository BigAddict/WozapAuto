from django.apps import AppConfig


class AiengineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aiengine'
    
    def ready(self):
        """Import signals when the app is ready."""
        import aiengine.signals  # noqa